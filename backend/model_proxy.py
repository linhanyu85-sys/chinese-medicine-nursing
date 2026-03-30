from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
DEFAULT_MODEL = "qwen3.5-plus"


class ModelProxy:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY") or os.getenv("CODING_PLAN_API_KEY")
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
            return self._fallback_answer(analysis, retrieval)

        hits = retrieval.get("hits", [])[:4]
        evidence_lines: list[str] = []
        for idx, item in enumerate(hits, start=1):
            evidence_lines.append(
                "\n".join(
                    [
                        f"{idx}. 标题: {item.get('title', '')}",
                        f"文件标签: {item.get('fileLabel', '')}",
                        f"命中依据: {'、'.join(item.get('basis', []))}",
                        f"证据片段: {item.get('snippet', '')}",
                        f"章节上下文: {item.get('context', '')}",
                    ]
                )
            )

        chapter_context = retrieval.get("chapterContext") or {}
        chapter_line = ""
        if chapter_context:
            chapter_line = (
                f"相关章节: {chapter_context.get('title', '')}\n"
                f"章节摘要: {chapter_context.get('summary', '')}"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是临床护士使用的中医适宜技术助手。"
                    "你必须优先依据给定的知识库证据回答。"
                    "当直接证据不足时，可以基于最相关章节进行类比推断，但要明确写出“推断依据不足”提示，"
                    "不得编造超出中医护理常识和给定证据的结论。"
                    "回答用中文，结构固定为：护理判断、护理建议、观察与风险、依据条目。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"临床问题: {question}\n"
                    f"检索意图: {analysis.get('intent', '')}\n"
                    f"护理焦点: {analysis.get('focus', '')}\n"
                    f"匹配标签: {'、'.join(analysis.get('matchedTags', [])) or '无'}\n"
                    f"会话记忆标签: {'、'.join(memory.get('memoryTags', [])) or '无'}\n"
                    f"{chapter_line}\n"
                    f"命中证据:\n{chr(10).join(evidence_lines) or '无'}\n"
                    "请给出可执行、可观察、可追溯的护理意见。"
                ),
            },
        ]

        try:
            return self._chat(messages)
        except Exception:
            return self._fallback_answer(analysis, retrieval)

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
            with urllib.request.urlopen(request, timeout=60) as response:
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

    def _fallback_answer(self, analysis: dict[str, Any], retrieval: dict[str, Any]) -> str:
        hits = retrieval.get("hits", [])
        if not hits:
            return (
                "护理判断：当前问题在知识库中没有直接条目，但已定位到相关章节方向。\n"
                "护理建议：请补充疾病诊断、症状阶段、已实施技术及患者反应后再检索，以便给出更精准意见。\n"
                "观察与风险：未提供明确适应证和禁忌证前，不建议直接实施操作。\n"
                "依据条目：暂无直接命中。"
            )

        lead = hits[0]
        titles = "；".join(item.get("title", "") for item in hits[:3] if item.get("title"))
        return (
            f"护理判断：当前问题与《{lead.get('title', '')}》相关度最高，可作为首要参考。\n"
            "护理建议：先核对适应证/禁忌证，再执行对应技术，并记录疗效与不良反应。\n"
            f"观察与风险：重点关注{analysis.get('focus', '病情变化')}及并发症风险，必要时及时上报。\n"
            f"依据条目：{titles or '暂无'}。"
        )
