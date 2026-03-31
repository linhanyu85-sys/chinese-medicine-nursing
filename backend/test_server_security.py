from __future__ import annotations

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import server  # noqa: E402


class ServerSecurityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
        cls.port = cls.httpd.server_port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def request(self, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, str, str]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, body, resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return exc.code, body, exc.headers.get("Content-Type", "")

    def test_empty_question_returns_400(self) -> None:
        status, body, content_type = self.request("/api/assistant/query", method="POST", payload={})
        self.assertEqual(status, 400)
        self.assertIn("application/json", content_type)
        self.assertEqual(json.loads(body)["error"], "问题不能为空")

    def test_unknown_route_returns_404(self) -> None:
        status, body, content_type = self.request("/api/not-found")
        self.assertEqual(status, 404)
        self.assertIn("application/json", content_type)
        self.assertEqual(json.loads(body)["error"], "接口不存在")

    def test_asset_path_traversal_returns_403_json(self) -> None:
        traversal_paths = (
            "/assets/..%2FREADME.md",
            "/assets/..%2F..%2FWindows/win.ini",
            "/assets/%2E%2E/%2E%2E/Windows/win.ini",
            "/assets/C:%5CWindows%5Cwin.ini",
        )
        for path in traversal_paths:
            with self.subTest(path=path):
                status, body, content_type = self.request(path)
                self.assertEqual(status, 403)
                self.assertIn("application/json", content_type)
                self.assertEqual(json.loads(body)["error"], "禁止访问")

    def test_missing_asset_returns_404_json(self) -> None:
        status, body, content_type = self.request("/assets/not-exists.txt")
        self.assertEqual(status, 404)
        self.assertIn("application/json", content_type)
        self.assertEqual(json.loads(body)["error"], "资源不存在")


if __name__ == "__main__":
    unittest.main()
