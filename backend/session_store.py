from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def empty_session() -> dict[str, Any]:
    timestamp = now_string()
    return {
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

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {"sessions": {}}

    def _write(self, payload: dict[str, Any]) -> None:
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create_session(self) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            session_id = uuid.uuid4().hex
            session = empty_session()
            payload.setdefault("sessions", {})[session_id] = session
            self._write(payload)
            return {
                "sessionId": session_id,
                "createdAt": session["createdAt"],
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
            merged_tags = list(dict.fromkeys((analysis.get("matchedTags") or []) + (session.get("memoryTags") or [])))

            focus = str(analysis.get("focus") or "")
            if focus:
                session["recentFocus"] = focus

            session["memoryTags"] = merged_tags[:10]
            session["recentHits"] = list(dict.fromkeys(hit_titles + (session.get("recentHits") or [])))[:10]
            session.setdefault("turns", []).append(
                {
                    "time": now_string(),
                    "question": question,
                    "tags": analysis.get("matchedTags", []),
                    "focus": analysis.get("focus", ""),
                    "hitTitles": hit_titles,
                    "answerSummary": answer[:180],
                }
            )
            session["turns"] = session["turns"][-8:]
            session["updatedAt"] = now_string()
            self._write(payload)

    def get_memory_payload(self, session_id: str | None) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "recentFocus": session.get("recentFocus", ""),
            "memoryTags": session.get("memoryTags", []),
            "recentHits": session.get("recentHits", []),
            "recentTurns": (session.get("turns") or [])[-3:],
        }
