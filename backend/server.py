from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from knowledge_service import KnowledgeService
from model_proxy import ModelProxy
from session_store import SessionStore


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parent
DATA_ROOT = BACKEND_ROOT / "data"
SESSION_FILE = DATA_ROOT / "session_memory.json"
HOST = os.getenv("APP_HOST", "0.0.0.0")
PORT = int(os.getenv("APP_PORT", "18791"))

knowledge_service = KnowledgeService(WORKSPACE_ROOT)
session_store = SessionStore(SESSION_FILE)
model_proxy = ModelProxy()


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "TCMAppBackend/3.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/api/health":
                self._json_response(
                    {
                        "status": "正常",
                        "articleCount": len(knowledge_service.articles),
                    }
                )
                return

            if path == "/api/home":
                self._json_response(knowledge_service.get_home_payload())
                return

            if path == "/api/knowledge/tree":
                self._json_response({"tree": knowledge_service.get_tree()})
                return

            if path == "/api/knowledge/articles":
                query_text = (query.get("query") or [""])[0]
                tag = (query.get("tag") or [""])[0]
                limit = int((query.get("limit") or ["60"])[0])
                self._json_response({"items": knowledge_service.list_articles(query_text, tag, limit)})
                return

            if path.startswith("/api/knowledge/article/"):
                article_id = unquote(path.split("/api/knowledge/article/", 1)[1])
                article = knowledge_service.get_article(article_id)
                if not article:
                    self._json_error(HTTPStatus.NOT_FOUND, "未找到对应条目")
                    return
                self._json_response(article)
                return

            if path.startswith("/api/assistant/memory/"):
                session_id = unquote(path.split("/api/assistant/memory/", 1)[1])
                self._json_response(session_store.get_memory_payload(session_id))
                return

            if path == "/api/assistant/sessions":
                limit = int((query.get("limit") or ["30"])[0])
                self._json_response({"items": session_store.list_sessions(limit=limit)})
                return

            if path.startswith("/api/assistant/session/"):
                session_id = unquote(path.split("/api/assistant/session/", 1)[1])
                self._json_response(session_store.get_session_detail(session_id))
                return

            if path == "/api/management/overview":
                self._json_response(self._management_payload())
                return

            if path.startswith("/assets/"):
                relative = unquote(path.split("/assets/", 1)[1])
                self._serve_asset(relative)
                return

            self._json_error(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as exc:
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务异常: {exc}")

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            body = self._read_json_body()

            if parsed.path == "/api/assistant/session":
                title = str(body.get("title") or "").strip() or "新对话"
                self._json_response(session_store.create_session(title=title), status=HTTPStatus.CREATED)
                return

            if parsed.path == "/api/assistant/query":
                question = (body.get("question") or "").strip()
                if not question:
                    self._json_error(HTTPStatus.BAD_REQUEST, "问题不能为空")
                    return

                session_id = (body.get("sessionId") or "").strip()
                if not session_id:
                    session = session_store.create_session()
                    session_id = session["sessionId"]

                memory = session_store.get_memory_payload(session_id)
                analysis = knowledge_service.analyze_query(question, memory)
                retrieval = knowledge_service.search(question, analysis, top_k=6)
                answer = model_proxy.generate_answer(question, analysis, retrieval, memory)
                session_store.append_turn(session_id, question, analysis, retrieval, answer)

                self._json_response(
                    {
                        "sessionId": session_id,
                        "analysis": analysis,
                        "retrieval": retrieval,
                        "answer": answer,
                        "memory": session_store.get_memory_payload(session_id),
                        "session": session_store.get_session_detail(session_id),
                    }
                )
                return

            if parsed.path == "/api/management/reload":
                knowledge_service.load()
                self._json_response(
                    {
                        "result": "知识库已重新加载",
                        "articleCount": len(knowledge_service.articles),
                    }
                )
                return

            self._json_error(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as exc:
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务异常: {exc}")

    def _management_payload(self) -> dict[str, Any]:
        return {
            "articleCount": len(knowledge_service.articles),
            "partCount": len(knowledge_service.tree),
            "lastExport": knowledge_service.data.get("stats", {}).get("lastExport", ""),
            "sessionFile": str(SESSION_FILE),
            "knowledgeSource": str(knowledge_service.docx_path or ""),
        }

    def _serve_asset(self, relative_path: str) -> None:
        try:
            candidate = (WORKSPACE_ROOT / relative_path).resolve()
        except (OSError, RuntimeError, ValueError):
            self._json_error(HTTPStatus.BAD_REQUEST, "路径参数无效")
            return

        workspace_resolved = WORKSPACE_ROOT.resolve()
        if workspace_resolved not in candidate.parents and candidate != workspace_resolved:
            self._json_error(HTTPStatus.FORBIDDEN, "禁止访问")
            return
        if not candidate.exists() or not candidate.is_file():
            self._json_error(HTTPStatus.NOT_FOUND, "资源不存在")
            return

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        data = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._write_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        text = raw.decode("utf-8-sig")
        if not text.strip():
            return {}
        return json.loads(text)

    def _json_response(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_error(self, status: HTTPStatus, message: str) -> None:
        self._json_response({"error": message}, status=status)

    def _write_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"中医适宜技术后端已启动: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
