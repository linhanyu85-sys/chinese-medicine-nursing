from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def excerpt(text: str, limit: int = 180) -> str:
    source = " ".join(str(text or "").split()).strip()
    if len(source) <= limit:
        return source
    return f"{source[:limit].rstrip()}..."


def dedup_keep_order(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def empty_session(title: str = "新对话") -> dict[str, Any]:
    timestamp = now_string()
    return {
        "title": title,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "recentFocus": "",
        "memoryTags": [],
        "recentHits": [],
        "turns": [],
    }


class SessionStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.file_path.exists():
            self._write({"sessions": {}})
        else:
            self._normalize_store()

    def _normalize_store(self) -> None:
        payload = self._read_raw()
        normalized = self._normalize_payload(payload)
        if normalized != payload:
            self._write(normalized)

    def _read_raw(self) -> dict[str, Any]:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {"sessions": {}}

    def _read(self) -> dict[str, Any]:
        return self._normalize_payload(self._read_raw())

    def _write(self, payload: dict[str, Any]) -> None:
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        sessions = payload.get("sessions", {})
        if not isinstance(sessions, dict):
            sessions = {}

        normalized_sessions: dict[str, Any] = {}
        for session_id, raw_session in sessions.items():
            normalized_sessions[str(session_id)] = self._normalize_session(raw_session)

        return {"sessions": normalized_sessions}

    def _normalize_session(self, raw_session: Any) -> dict[str, Any]:
        session = raw_session if isinstance(raw_session, dict) else {}
        turns = [self._normalize_turn(turn) for turn in (session.get("turns") or session.get("对话") or [])]
        turns = [turn for turn in turns if turn["question"] or turn["answer"]]
        recent_focus = str(session.get("recentFocus") or session.get("最近焦点") or "").strip()
        memory_tags = dedup_keep_order(
            list(session.get("memoryTags") or session.get("记忆标签") or [])
            + [recent_focus] * (1 if recent_focus else 0)
        )[:10]
        recent_hits = dedup_keep_order(list(session.get("recentHits") or session.get("最近条目") or []))[:10]
        created_at = str(session.get("createdAt") or session.get("创建时间") or now_string())
        updated_at = str(session.get("updatedAt") or session.get("更新时间") or created_at)
        title = str(session.get("title") or session.get("标题") or "").strip()

        if not title:
            first_question = next((turn["question"] for turn in turns if turn["question"]), "")
            title = excerpt(first_question, 20) or (f"{recent_focus}病例" if recent_focus else "新对话")

        normalized = {
            "title": title,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "recentFocus": recent_focus,
            "memoryTags": memory_tags,
            "recentHits": recent_hits,
            "turns": turns[-20:],
        }

        if turns:
            normalized["updatedAt"] = turns[-1]["time"] or updated_at

        return normalized

    def _normalize_turn(self, raw_turn: Any) -> dict[str, Any]:
        turn = raw_turn if isinstance(raw_turn, dict) else {}
        answer = str(turn.get("answer") or turn.get("回答") or turn.get("answerSummary") or turn.get("回答摘要") or "")
        references = []
        for item in (turn.get("references") or turn.get("依据条目") or []):
            if not isinstance(item, dict):
                continue
            references.append(
                {
                    "fileLabel": str(item.get("fileLabel") or item.get("文件标签") or ""),
                    "title": str(item.get("title") or item.get("标题") or ""),
                }
            )

        analysis = turn.get("analysis") or {}
        if not isinstance(analysis, dict):
            analysis = {}

        return {
            "time": str(turn.get("time") or turn.get("时间") or now_string()),
            "question": str(turn.get("question") or turn.get("问题") or ""),
            "tags": dedup_keep_order(list(turn.get("tags") or turn.get("标签") or []))[:10],
            "focus": str(turn.get("focus") or turn.get("焦点") or ""),
            "hitTitles": dedup_keep_order(list(turn.get("hitTitles") or turn.get("命中条目") or []))[:6],
            "answerSummary": excerpt(turn.get("answerSummary") or turn.get("回答摘要") or answer, 180),
            "answer": answer,
            "analysis": {
                "intent": str(analysis.get("intent") or turn.get("intent") or ""),
                "focus": str(analysis.get("focus") or turn.get("focus") or turn.get("焦点") or ""),
                "matchedTags": dedup_keep_order(
                    list(analysis.get("matchedTags") or turn.get("tags") or turn.get("标签") or [])
                )[:10],
            },
            "references": references[:6],
        }

    def create_session(self, title: str = "新对话") -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            session_id = uuid.uuid4().hex
            session = empty_session(title=title)
            payload.setdefault("sessions", {})[session_id] = session
            self._write(payload)
            return {
                "sessionId": session_id,
                "createdAt": session["createdAt"],
                "title": session["title"],
            }

    def get_session(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return empty_session()

        with self._lock:
            payload = self._read()
            session = payload.get("sessions", {}).get(session_id)
            if not session:
                return empty_session()
            return session

    def list_sessions(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            payload = self._read()
            items: list[dict[str, Any]] = []
            for session_id, session in payload.get("sessions", {}).items():
                turns = session.get("turns") or []
                latest_turn = turns[-1] if turns else {}
                items.append(
                    {
                        "sessionId": session_id,
                        "title": session.get("title", "新对话"),
                        "createdAt": session.get("createdAt", ""),
                        "updatedAt": session.get("updatedAt", ""),
                        "recentFocus": session.get("recentFocus", ""),
                        "turnCount": len(turns),
                        "preview": latest_turn.get("question") or latest_turn.get("answerSummary") or "",
                    }
                )

            items.sort(key=lambda item: item.get("updatedAt", ""), reverse=True)
            return items[: max(1, min(limit, 100))]

    def get_session_detail(self, session_id: str | None) -> dict[str, Any]:
        session = self.get_session(session_id)
        turns = session.get("turns") or []
        latest_turn = turns[-1] if turns else None
        return {
            "sessionId": session_id or "",
            "title": session.get("title", "新对话"),
            "createdAt": session.get("createdAt", ""),
            "updatedAt": session.get("updatedAt", ""),
            "recentFocus": session.get("recentFocus", ""),
            "memoryTags": session.get("memoryTags", []),
            "recentHits": session.get("recentHits", []),
            "turnCount": len(turns),
            "latestTurn": latest_turn,
            "turns": turns,
        }

    def append_turn(
        self,
        session_id: str,
        question: str,
        analysis: dict[str, Any],
        retrieval: dict[str, Any],
        answer: str,
    ) -> None:
        with self._lock:
            payload = self._read()
            sessions = payload.setdefault("sessions", {})
            session = sessions.get(session_id)
            if not session:
                session = empty_session()
                sessions[session_id] = session

            hit_titles = [
                str(item.get("title") or "")
                for item in (retrieval.get("hits") or [])[:4]
                if item.get("title")
            ]
            merged_tags = dedup_keep_order((analysis.get("matchedTags") or []) + (session.get("memoryTags") or []))[:10]
            focus = str(analysis.get("focus") or "")
            case_profile = analysis.get("caseProfile") or {}
            first_turn = not bool(session.get("turns"))

            if focus:
                session["recentFocus"] = focus

            if first_turn:
                derived_title = (
                    f"{case_profile.get('mainComplaint', '')}病例".strip()
                    if case_profile.get("isCase") and case_profile.get("mainComplaint")
                    else excerpt(question, 20)
                )
                session["title"] = derived_title or session.get("title") or "新对话"

            references = [
                {
                    "fileLabel": str(item.get("fileLabel") or ""),
                    "title": str(item.get("title") or ""),
                }
                for item in (retrieval.get("hits") or [])[:4]
            ]

            session["memoryTags"] = merged_tags
            session["recentHits"] = dedup_keep_order(hit_titles + (session.get("recentHits") or []))[:10]
            session.setdefault("turns", []).append(
                {
                    "time": now_string(),
                    "question": question,
                    "tags": analysis.get("matchedTags", []),
                    "focus": focus,
                    "hitTitles": hit_titles,
                    "answerSummary": excerpt(answer, 180),
                    "answer": answer,
                    "analysis": {
                        "intent": analysis.get("intent", ""),
                        "focus": focus,
                        "matchedTags": analysis.get("matchedTags", []),
                    },
                    "references": references,
                }
            )
            session["turns"] = session["turns"][-20:]
            session["updatedAt"] = now_string()
            self._write(payload)

    def get_memory_payload(self, session_id: str | None) -> dict[str, Any]:
        session = self.get_session(session_id)
        turns = session.get("turns") or []
        return {
            "sessionTitle": session.get("title", "新对话"),
            "recentFocus": session.get("recentFocus", ""),
            "memoryTags": session.get("memoryTags", []),
            "recentHits": session.get("recentHits", []),
            "turnCount": len(turns),
            "recentTurns": turns[-3:],
        }
