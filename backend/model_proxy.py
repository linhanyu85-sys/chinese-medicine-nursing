from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


# 统一走 OpenAI 兼容协议，默认使用 Kimi 2.5。
DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"


def _compact(text: str, limit: int) -> str:
    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(source) <= limit:
        return source
    return f"{source[:limit].rstrip()}..."


class ModelProxy:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = (
            api_key
            or os.getenv("MOONSHOT_API_KEY")
            or os.getenv("ALIYUN_API_KEY")
            or os.getenv("CODING_PLAN_API_KEY")
        )
        self.base_url = (base_url or os.getenv("ALIYUN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("ALIYUN_MODEL") or DEFAULT_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def generate_answer(
        self,
        question: str,
        analysis: dict[str, Any],
        retrieval: dict[str, Any],
        memory: dict[str, Any],
    ) -> str:
        if not self.available():
            return self._append_citations(self._fallback_answer(question, analysis, retrieval), retrieval)

        evidence_lines = self._evidence_lines(retrieval)
        chapter = retrieval.get("chapterContext") or {}
        chapter_text = ""
        if chapter.get("title"):
            chapter_text = f"相关章节：{chapter.get('title', '')}\n章节摘要：{_compact(chapter.get('summary', ''), 240)}"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是面向临床护士的中医护理问答助手。"
                    "只能依据给定知识库证据回答，不得泄露或讨论底层模型信息。"
                    "即使问题较泛化，也要先回溯最相关章节，再给出可执行建议。"
                    "回答必须使用中文，且固定包含四部分：护理判断、护理建议、观察与风险、依据条目。"
                    "若证据不足，要明确写“推断依据不足”，但仍给出安全、审慎、可落地的护理建议。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"问题：{question}\n"
                    f"检索意图：{analysis.get('intent', '')}\n"
                    f"护理焦点：{analysis.get('focus', '')}\n"
                    f"匹配标签：{'、'.join(analysis.get('matchedTags', [])) or '无'}\n"
                    f"会话记忆标签：{'、'.join(memory.get('memoryTags', [])) or '无'}\n"
                    f"{chapter_text}\n"
                    f"命中证据：\n{chr(10).join(evidence_lines) or '无'}\n"
                    "请输出专业、简洁、可执行的护理建议，并在“依据条目”中引用文件标签。"
                ),
            },
        ]

        try:
            answer = self._chat(messages)
        except Exception:
            answer = self._fallback_answer(question, analysis, retrieval)

        answer = self._ensure_core_sections(answer, question, analysis, retrieval)
        if self._is_weak_retrieval(retrieval) and "推断依据不足" not in answer:
            answer = (
                f"{answer}\n"
                "提示：当前问题未命中高置信条目，以上建议基于知识库相关章节回溯，请结合科室规范与医师意见执行。"
            )
        return self._append_citations(answer, retrieval)

    def _chat(self, messages: list[dict[str, Any]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            # 超时后自动走本地兜底，避免前端长时间等待。
            with urllib.request.urlopen(request, timeout=22) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"模型调用失败: {error.code} {body}") from error

        data = json.loads(raw)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("模型返回为空")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            content = "\n".join(part for part in text_parts if part)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("模型未返回可用文本")
        return content.strip()

    def _evidence_lines(self, retrieval: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for idx, item in enumerate((retrieval.get("hits") or [])[:4], start=1):
            lines.append(
                "\n".join(
                    [
                        f"{idx}. 标题: {item.get('title', '')}",
                        f"文件标签: {item.get('fileLabel', '')}",
                        f"命中依据: {'、'.join(item.get('basis', [])) or '语义相关'}",
                        f"证据片段: {_compact(item.get('snippet', ''), 180)}",
                        f"章节上下文: {_compact(item.get('context', ''), 240)}",
                    ]
                )
            )
        return lines

    def _fallback_answer(self, question: str, analysis: dict[str, Any], retrieval: dict[str, Any]) -> str:
        hits = retrieval.get("hits", []) or []
        chapter = retrieval.get("chapterContext") or {}
        focus = analysis.get("focus") or "临床护理"

        strong_hits = []
        for item in hits:
            score = float(item.get("score") or 0.0)
            basis = item.get("basis") or []
            if score >= 60 and "章节回溯" not in basis:
                strong_hits.append(item)

        if strong_hits:
            title_refs = "、".join(item.get("title", "") for item in strong_hits[:3] if item.get("title")) or "相关条目"
            return (
                f"护理判断：当前问题与“{strong_hits[0].get('title', '')}”相关度最高，可按相近病证场景处理。\n"
                "护理建议：先做症状评估（主诉、体征、病程、既往史），再按条目中的适应证与禁忌证实施护理技术；"
                "同时同步健康教育与随访记录。\n"
                f"观察与风险：重点观察{focus}、生命体征变化及不良反应；若出现持续加重或危险信号，应立即上报医师。\n"
                f"依据条目：{title_refs}。"
            )

        chapter_title = chapter.get("title") or "相关章节"
        chapter_summary = _compact(chapter.get("summary", ""), 120) or "已按最相关章节回溯。"
        return (
            f"护理判断：当前问题“{question}”未命中同名条目，系统已按知识库最相关章节回溯。\n"
            "护理建议：可先采用基础护理路径（评估-干预-观察-记录-宣教），并结合患者主要症状选择对应中医护理技术；"
            "若问题并非护理场景，请补充临床症状或护理目标后再问。\n"
            "观察与风险：重点监测症状变化、生命体征和潜在并发风险，异常时及时报告。\n"
            f"依据条目：{chapter_title}（摘要：{chapter_summary}）。"
        )

    def _ensure_core_sections(
        self,
        answer: str,
        question: str,
        analysis: dict[str, Any],
        retrieval: dict[str, Any],
    ) -> str:
        text = (answer or "").strip()
        required = ("护理判断", "护理建议", "观察与风险", "依据条目")
        if text and all(key in text for key in required):
            return text

        # 保障输出格式稳定，不让模型自由发挥导致答复不可用。
        fallback = self._fallback_answer(question, analysis, retrieval)
        if not text:
            return fallback

        extra = _compact(text, 360)
        return f"{fallback}\n补充说明：{extra}"

    def _is_weak_retrieval(self, retrieval: dict[str, Any]) -> bool:
        hits = retrieval.get("hits", []) or []
        if not hits:
            return True

        for hit in hits:
            score = float(hit.get("score") or 0.0)
            basis = hit.get("basis") or []
            if score >= 60 and "章节回溯" not in basis:
                return False
        return True

    def _citation_items(self, retrieval: dict[str, Any]) -> list[dict[str, str]]:
        hits = retrieval.get("hits", []) or []
        items: list[dict[str, str]] = []
        for hit in hits[:4]:
            items.append(
                {
                    "fileLabel": str(hit.get("fileLabel") or ""),
                    "title": str(hit.get("title") or ""),
                    "snippet": _compact(str(hit.get("snippet") or ""), 140),
                }
            )

        chapter = retrieval.get("chapterContext") or {}
        if not items and chapter.get("title"):
            items.append(
                {
                    "fileLabel": "章节回溯",
                    "title": str(chapter.get("title") or ""),
                    "snippet": _compact(str(chapter.get("summary") or ""), 140),
                }
            )
        return items

    def _append_citations(self, answer: str, retrieval: dict[str, Any]) -> str:
        text = (answer or "").strip()
        if not text:
            text = "护理判断：已完成知识库回溯。\n护理建议：请补充临床问题后继续提问。\n观察与风险：暂无。\n依据条目：章节回溯。"

        marker = "引用依据"
        items = self._citation_items(retrieval)
        if not items:
            return text

        if marker in text:
            return text

        lines = []
        for idx, item in enumerate(items, start=1):
            file_label = item.get("fileLabel") or "未标注"
            title = item.get("title") or "未命名条目"
            snippet = item.get("snippet") or "无摘要"
            lines.append(f"{idx}. [{file_label}] {title}：{snippet}")

        return f"{text}\n\n{marker}\n" + "\n".join(lines)
