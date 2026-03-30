from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


# 采用 OpenAI 兼容协议，可切换阿里百炼、Moonshot(Kimi)等模型网关
DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"


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
            return self._append_citations(self._fallback_answer(analysis, retrieval), retrieval)

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
                    "无论问题是否精确命中，都要给出可执行的护理建议，并且必须包含出处。"
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
            answer = self._chat(messages)
        except Exception:
            answer = self._fallback_answer(analysis, retrieval)
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
            # 移动端问答优先稳定返回，超时后退回本地增强回答，避免前端长时间“网络失败”
            with urllib.request.urlopen(request, timeout=20) as response:
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
                "护理判断：当前问题未检索到完全同名条目，已按相近病证与护理场景回溯相关章节。\n"
                "护理建议：可先采用基础护理路径（症状评估、体征监测、风险分层、宣教随访），并结合知识库相关技术条目选择适宜技术。\n"
                "观察与风险：重点观察体温、疼痛程度、精神状态及不良反应；若出现持续高热、抽搐、意识改变等应立即上报医生。\n"
                "依据条目：已按相关章节回溯。"
            )

        lead = hits[0]
        titles = "；".join(item.get("title", "") for item in hits[:3] if item.get("title"))
        return (
            f"护理判断：当前问题与《{lead.get('title', '')}》相关度最高，可作为首要参考。\n"
            "护理建议：先核对适应证/禁忌证，再执行对应技术，并记录疗效与不良反应。\n"
            f"观察与风险：重点关注{analysis.get('focus', '病情变化')}及并发症风险，必要时及时上报。\n"
            f"依据条目：{titles or '暂无'}。"
        )

    def _citation_lines(self, retrieval: dict[str, Any]) -> list[str]:
        hits = retrieval.get("hits", []) or []
        lines: list[str] = []
        for idx, item in enumerate(hits[:4], start=1):
            title = item.get("title", "")
            file_label = item.get("fileLabel", "")
            snippet = item.get("snippet", "")
            lines.append(f"{idx}. [{file_label}] {title}：{snippet}")

        if not lines:
            chapter = retrieval.get("chapterContext") or {}
            chapter_title = chapter.get("title", "")
            chapter_summary = chapter.get("summary", "")
            if chapter_title:
                lines.append(f"1. [章节回溯] {chapter_title}：{chapter_summary}")
        return lines

    def _append_citations(self, answer: str, retrieval: dict[str, Any]) -> str:
        text = (answer or "").strip()
        if not text:
            text = "护理判断：已完成知识库回溯。"

        citation_lines = self._citation_lines(retrieval)
        if not citation_lines:
            return text

        marker = "引用依据"
        if marker in text:
            return text

        return f"{text}\n\n{marker}\n" + "\n".join(citation_lines)
