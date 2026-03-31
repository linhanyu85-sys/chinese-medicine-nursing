from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"
SECTION_TITLES = ("病情摘要", "护理判断", "护理建议", "观察与上报", "护理记录", "依据条目")


def _compact(text: str, limit: int) -> str:
    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(source) <= limit:
        return source
    return f"{source[:limit].rstrip()}..."


def _dedup_keep_order(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


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
        fallback_sections = self._build_fallback_sections(question, analysis, retrieval)
        model_sections: dict[str, str] = {}

        if self.available():
            try:
                raw_answer = self._chat(self._build_messages(question, analysis, retrieval, memory))
                model_sections = self._extract_sections(raw_answer)
            except Exception:
                model_sections = {}

        merged = self._merge_sections(fallback_sections, model_sections)
        return self._render_sections(merged)

    def _build_messages(
        self,
        question: str,
        analysis: dict[str, Any],
        retrieval: dict[str, Any],
        memory: dict[str, Any],
    ) -> list[dict[str, Any]]:
        case_profile = analysis.get("caseProfile") or {}
        pattern_names = "、".join(item.get("name", "") for item in (case_profile.get("patternCandidates") or [])) or "无"
        danger_absent = "、".join(case_profile.get("dangerSignsAbsent") or []) or "无"
        danger_present = "、".join(case_profile.get("dangerSignsPresent") or []) or "无"
        chapter = retrieval.get("chapterContext") or {}
        chapter_text = ""
        if chapter.get("title"):
            chapter_text = f"相关章节: {chapter.get('title', '')}\n章节摘要: {_compact(chapter.get('summary', ''), 220)}"

        return [
            {
                "role": "system",
                "content": (
                    "你是面向临床护士的中医护理问答助手。"
                    "只能依据给定知识库证据回答，不得编造未提供的疗程、禁忌证或操作标准。"
                    "输出必须为纯文本，不要使用 Markdown，不要出现 #、*、|、表格、代码块。"
                    "必须严格按以下六个标题原样输出：病情摘要、护理判断、护理建议、观察与上报、护理记录、依据条目。"
                    "每个标题下使用阿拉伯数字分行。"
                    "若证候判断来自症状归纳而非条文原句，要写“更偏向”或“倾向于”，不要写成确诊。"
                    "护理建议必须包含 0-30 分钟处置、30-120 分钟复评、适宜技术选择或暂缓理由。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"问题: {question}\n"
                    f"检索意图: {analysis.get('intent', '')}\n"
                    f"护理焦点: {analysis.get('focus', '')}\n"
                    f"匹配标签: {'、'.join(analysis.get('matchedTags', [])) or '无'}\n"
                    f"病例摘要: {case_profile.get('summary', '') or '未提供完整病例'}\n"
                    f"主诉线索: {case_profile.get('mainComplaint', '') or '未识别'}\n"
                    f"证候候选: {pattern_names}\n"
                    f"危险征象阳性: {danger_present}\n"
                    f"危险征象阴性: {danger_absent}\n"
                    f"会话记忆标签: {'、'.join(memory.get('memoryTags', [])) or '无'}\n"
                    f"{chapter_text}\n"
                    f"命中证据:\n{chr(10).join(self._evidence_lines(retrieval)) or '无'}\n"
                    "请按护士当班执行视角作答。"
                ),
            },
        ]

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

    def _sanitize_plain_text(self, text: str) -> str:
        cleaned = str(text or "").replace("\r", "")
        cleaned = cleaned.replace("**", "").replace("__", "")
        cleaned = cleaned.replace("```", "")
        cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*•]+\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\|.*\|\s*$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _extract_sections(self, text: str) -> dict[str, str]:
        cleaned = self._sanitize_plain_text(text)
        lines = [line.strip() for line in cleaned.splitlines()]
        sections: dict[str, list[str]] = {}
        current_title = ""

        for line in lines:
            if not line:
                continue
            matched_title = next(
                (
                    title
                    for title in SECTION_TITLES
                    if re.fullmatch(rf"{title}[：:]?", line) or line.startswith(f"{title}:") or line.startswith(f"{title}：")
                ),
                "",
            )
            if matched_title:
                current_title = matched_title
                sections.setdefault(current_title, [])
                remainder = re.sub(rf"^{matched_title}[：:]?", "", line).strip()
                if remainder:
                    sections[current_title].append(remainder)
                continue

            if current_title:
                sections.setdefault(current_title, []).append(line)

        return {title: "\n".join(values).strip() for title, values in sections.items() if values}

    def _merge_sections(self, fallback: dict[str, str], model_sections: dict[str, str]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for title in SECTION_TITLES:
            model_text = self._sanitize_plain_text(model_sections.get(title, ""))
            fallback_text = self._sanitize_plain_text(fallback.get(title, ""))
            if title == "依据条目":
                merged[title] = fallback_text
                continue
            merged[title] = model_text if len(model_text) >= 20 else fallback_text

        return merged

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

    def _evidence_lines(self, retrieval: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for idx, item in enumerate((retrieval.get("hits") or [])[:4], start=1):
            lines.append(
                "\n".join(
                    [
                        f"{idx}. 标题: {item.get('title', '')}",
                        f"类型: {item.get('kind', '') or '相关条目'}",
                        f"文件标签: {item.get('fileLabel', '')}",
                        f"命中依据: {'、'.join(item.get('basis', [])) or '语义相关'}",
                        f"证据片段: {_compact(item.get('snippet', ''), 180)}",
                    ]
                )
            )
        return lines

    def _build_case_summary_lines(self, analysis: dict[str, Any]) -> list[str]:
        case_profile = analysis.get("caseProfile") or {}
        if not case_profile.get("isCase"):
            return [
                "1. 本次问题未提供完整病例，系统按护理咨询问题处理。",
                f"2. 当前检索焦点为 {analysis.get('focus', '') or '未识别'}。",
            ]

        summary_bits: list[str] = []
        sex = str(case_profile.get("sex") or "")
        age = str(case_profile.get("age") or "")
        if sex or age:
            summary_bits.append(f"{sex}{age}".strip())
        if case_profile.get("department"):
            summary_bits.append(str(case_profile.get("department")))
        if case_profile.get("mainComplaint"):
            summary_bits.append(f"主诉以{case_profile.get('mainComplaint')}为主")

        vitals = case_profile.get("vitals") or {}
        vitals_text = "，".join(f"{key} {value}" for key, value in vitals.items())
        symptoms = "、".join(case_profile.get("symptoms") or []) or "未提取"
        tcm_findings = "、".join(case_profile.get("tcmFindings") or []) or "未提取"

        lines = [f"1. {'，'.join(summary_bits) or '已识别为病例输入'}。"]
        lines.append(f"2. 伴随症状: {symptoms}。")
        if vitals_text or case_profile.get("painScore"):
            lines.append(
                f"3. 生命体征与评分: {vitals_text or '未提供'}"
                f"{'；' if vitals_text and case_profile.get('painScore') else ''}"
                f"{case_profile.get('painScore') or ''}。"
            )
        lines.append(f"4. 中医线索: {tcm_findings}。")
        return lines[:4]

    def _build_judgement_lines(self, question: str, analysis: dict[str, Any], retrieval: dict[str, Any]) -> list[str]:
        case_profile = analysis.get("caseProfile") or {}
        hits = retrieval.get("hits") or []
        top_hit = hits[0] if hits else {}
        lines: list[str] = []

        if case_profile.get("isCase") and case_profile.get("mainComplaint"):
            pattern = (case_profile.get("patternCandidates") or [{}])[0]
            if pattern.get("name"):
                reason_text = "、".join(pattern.get("reasons") or []) or "症状与舌脉线索"
                lines.append(
                    f"1. 当前以 {case_profile.get('mainComplaint')} 为主要护理问题，结合 {reason_text}，证候更偏向 {pattern.get('name')}。"
                )
            else:
                lines.append(f"1. 当前以 {case_profile.get('mainComplaint')} 为主要护理问题，应先按病例路径完成分层评估。")

            danger_absent = "、".join(case_profile.get("dangerSignsAbsent") or [])
            danger_present = "、".join(case_profile.get("dangerSignsPresent") or [])
            if danger_present:
                lines.append(f"2. 已出现 {danger_present} 等危险征象，应立即升级上报并暂停常规适宜技术。")
            elif danger_absent:
                lines.append(f"2. 目前未见 {danger_absent} 等明显危险征象，但仍需持续复评。")

            if top_hit:
                lines.append(f"3. 知识库当前最相关证据为 {top_hit.get('title', '')}（{top_hit.get('fileLabel', '')}）。")
            return lines[:3]

        focus = analysis.get("focus") or "当前主诉"
        if top_hit:
            lines.append(f"1. 当前问题与 {top_hit.get('title', '')} 相关度最高，可围绕 {focus} 组织护理。")
        else:
            lines.append(f"1. 当前问题未命中高置信条目，系统已按相关章节回溯后生成保守建议。")
        lines.append("2. 护理重点仍应按 评估-干预-复评-记录 的顺序执行。")
        return lines

    def _build_headache_action_lines(self, case_profile: dict[str, Any], retrieval: dict[str, Any]) -> list[str]:
        pattern_name = ""
        if case_profile.get("patternCandidates"):
            pattern_name = str(case_profile["patternCandidates"][0].get("name") or "")

        avoid_moxa = pattern_name in {"肝阳上扰", "风热上扰", "痰浊阻络"}
        lines = [
            "1. 0-30分钟: 复测 T/P/R/BP/SpO2 与疼痛评分，补齐头痛部位、性质、持续时间、诱因、伴随症状和神经系统筛查。",
            "2. 0-30分钟: 立即落实安静、弱光、减少噪音与强光刺激，协助舒适卧位，避免继续低头、屏气和情绪刺激。",
            "3. 技术选择: 经评估且无禁忌后，可优先考虑经穴推拿，围绕 百会、风池、太阳、合谷 开展首轮干预；若偏向肝阳上扰，可酌加 太冲、行间。",
            "4. 联合技术: 若科室常规允许，可与医师沟通联合耳穴贴压，常用 神门、皮质下、枕、颞、额；患者每日可按压 3到5次，每次 30秒到2分钟。",
        ]

        if avoid_moxa:
            lines.append("5. 暂缓建议: 若证候更偏向肝阳上扰、风热上扰或痰浊阻络，本轮不首选悬灸。")
        else:
            lines.append("5. 其他技术: 若偏寒或偏虚证且已核对禁忌，可再考虑悬灸；单穴温热感明显即可，避免烫伤。")

        lines.append("6. 30-120分钟: 每30到60分钟复评一次疼痛评分、血压和伴随症状；首轮干预后疼痛下降至少2分，可视为初步有效。")
        return lines

    def _build_generic_action_lines(self, analysis: dict[str, Any], retrieval: dict[str, Any]) -> list[str]:
        focus = str(analysis.get("focus") or "当前主诉")
        top_titles = "、".join(str(item.get("title") or "") for item in (retrieval.get("hits") or [])[:3] if item.get("title"))
        top_titles = top_titles or "相关章节回溯条目"
        return [
            "1. 0-30分钟: 先补齐主诉、生命体征、疼痛/不适评分、伴随症状、既往史和危险征象筛查。",
            "2. 0-30分钟: 优先处理当前不适，落实安静环境、舒适体位和基础安全护理，必要时同步核对医嘱与既往用药效果。",
            f"3. 技术选择: 在核对适应证和禁忌证后，优先从 {top_titles} 中选择与 {focus} 最贴近的技术路径。",
            "4. 30-120分钟: 至少完成2次复评，观察症状强度、生命体征和患者耐受，决定是否继续同类干预或升级上报。",
        ]

    def _build_observation_lines(self, analysis: dict[str, Any], retrieval: dict[str, Any]) -> list[str]:
        case_profile = analysis.get("caseProfile") or {}
        if case_profile.get("isCase") and case_profile.get("mainComplaint") == "头痛":
            lines = [
                "1. 重点观察头痛部位、性质、频次、持续时间，以及恶心、呕吐、畏光、睡眠和血压变化。",
                "2. 若出现肢体无力、言语不清、意识改变、抽搐、喷射性呕吐、视力骤降或头痛突发明显加剧，应立即上报医师。",
                "3. 对血压偏高者，应同步观察血压与头痛变化的关联，防止血压继续升高诱发风险。",
            ]
            return lines

        focus = str(analysis.get("focus") or "当前主诉")
        return [
            f"1. 重点观察 {focus} 的强度变化、持续时间、诱发因素和伴随症状。",
            "2. 复评生命体征、患者耐受及不良反应，必要时暂停干预并立即上报。",
            "3. 若出现进行性加重、意识改变、明显呼吸循环异常或新的神经系统体征，应走升级处置路径。",
        ]

    def _build_record_lines(self, analysis: dict[str, Any]) -> list[str]:
        case_profile = analysis.get("caseProfile") or {}
        tcm_findings = "、".join(case_profile.get("tcmFindings") or [])
        return [
            "1. 记录评估: 时间、主诉、生命体征、疼痛/症状评分、伴随症状、危险征象筛查结果。",
            "2. 记录干预: 技术名称、穴位或部位、单次时长、频次、患者耐受和操作后即刻反应。",
            f"3. 记录复评: 症状变化、生命体征变化、不良反应、是否上报。{' 舌脉线索为 ' + tcm_findings + '。' if tcm_findings else ''}",
        ]

    def _citation_items(self, retrieval: dict[str, Any]) -> list[dict[str, str]]:
        hits = retrieval.get("hits", []) or []
        items: list[dict[str, str]] = []
        for hit in hits[:4]:
            items.append(
                {
                    "fileLabel": str(hit.get("fileLabel") or ""),
                    "title": str(hit.get("title") or ""),
                    "kind": str(hit.get("kind") or ""),
                    "snippet": _compact(str(hit.get("snippet") or ""), 120),
                }
            )

        chapter = retrieval.get("chapterContext") or {}
        if not items and chapter.get("title"):
            items.append(
                {
                    "fileLabel": "章节回溯",
                    "title": str(chapter.get("title") or ""),
                    "kind": "章节回溯",
                    "snippet": _compact(str(chapter.get("summary") or ""), 120),
                }
            )
        return items

    def _build_reference_lines(self, retrieval: dict[str, Any]) -> list[str]:
        items = self._citation_items(retrieval)
        if not items:
            return ["1. 当前未命中具体条目，已按相关章节回溯。"]

        lines: list[str] = []
        for idx, item in enumerate(items, start=1):
            kind = f"{item.get('kind', '')} / " if item.get("kind") else ""
            lines.append(
                f"{idx}. [{item.get('fileLabel', '') or '未标注'}] {kind}{item.get('title', '') or '未命名条目'}：{item.get('snippet', '') or '无摘要'}。"
            )
        return lines

    def _build_fallback_sections(
        self,
        question: str,
        analysis: dict[str, Any],
        retrieval: dict[str, Any],
    ) -> dict[str, str]:
        case_profile = analysis.get("caseProfile") or {}
        sections = {
            "病情摘要": "\n".join(self._build_case_summary_lines(analysis)),
            "护理判断": "\n".join(self._build_judgement_lines(question, analysis, retrieval)),
            "护理建议": "\n".join(
                self._build_headache_action_lines(case_profile, retrieval)
                if case_profile.get("mainComplaint") == "头痛"
                else self._build_generic_action_lines(analysis, retrieval)
            ),
            "观察与上报": "\n".join(self._build_observation_lines(analysis, retrieval)),
            "护理记录": "\n".join(self._build_record_lines(analysis)),
            "依据条目": "\n".join(self._build_reference_lines(retrieval)),
        }

        if self._is_weak_retrieval(retrieval):
            sections["护理判断"] = (
                f"{sections['护理判断']}\n"
                "4. 当前高置信直接证据有限，以下建议按知识库相近病证和相关技术条目进行保守整合。"
            ).strip()

        return sections

    def _render_sections(self, sections: dict[str, str]) -> str:
        blocks: list[str] = []
        for title in SECTION_TITLES:
            body = self._sanitize_plain_text(sections.get(title, "")) or "1. 暂无。"
            normalized_lines = [line.strip() for line in body.splitlines() if line.strip()]
            rendered_lines: list[str] = []
            for idx, line in enumerate(normalized_lines, start=1):
                if re.match(r"^\d+[.、]", line):
                    rendered_lines.append(line)
                else:
                    rendered_lines.append(f"{idx}. {line}")
            blocks.append(f"{title}\n" + "\n".join(rendered_lines))
        return "\n\n".join(blocks).strip()
