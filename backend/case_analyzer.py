from __future__ import annotations

import re
from typing import Any


FIELD_ALIASES: dict[str, str] = {
    "患者": "patient",
    "基本信息": "patient",
    "主诉": "chief_complaint",
    "现病史": "history",
    "病史": "history",
    "生命体征": "vitals",
    "疼痛评分": "pain_score",
    "评分": "pain_score",
    "既往史": "past_history",
    "危险征象": "danger_signs",
    "危险信号": "danger_signs",
    "中医信息": "tcm_findings",
    "舌脉": "tcm_findings",
    "当前用药": "medication",
    "处理目标": "goal",
    "护理目标": "goal",
}

SYMPTOM_ALIASES: dict[str, list[str]] = {
    "头痛": ["头痛", "头疼", "头部疼痛", "偏头痛", "头胀", "头部胀痛"],
    "恶心": ["恶心", "呕恶"],
    "呕吐": ["呕吐"],
    "畏光": ["畏光", "怕光"],
    "烦躁": ["烦躁", "心烦", "易怒"],
    "失眠": ["失眠", "睡眠差", "夜寐不宁", "寐差", "夜间睡眠差"],
    "头晕": ["头晕", "头昏", "目眩"],
    "眩晕": ["眩晕"],
    "胸闷": ["胸闷"],
    "发热": ["发热", "高热", "低热", "体温高", "身热"],
    "畏寒": ["畏寒", "恶寒", "怕冷"],
    "无汗": ["无汗", "少汗"],
    "口苦": ["口苦"],
    "面红": ["面红", "脸红", "目赤"],
    "视力模糊": ["视力模糊", "视物模糊"],
    "项背痛": ["项背痛", "颈项痛", "后颈痛"],
    "乏力": ["乏力", "神疲", "疲乏"],
}

DANGER_ALIASES: dict[str, list[str]] = {
    "肢体无力": ["肢体无力", "偏瘫", "肢体乏力"],
    "言语不清": ["言语不清", "说话含糊", "失语"],
    "意识障碍": ["意识障碍", "意识改变", "意识不清", "昏迷"],
    "抽搐": ["抽搐", "惊厥"],
    "喷射性呕吐": ["喷射性呕吐"],
    "视力骤降": ["视力骤降", "视力下降"],
}

HEADACHE_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "肝阳上扰",
        "cues": [
            ["两侧", "太阳穴", "颞部"],
            ["胀痛", "抽掣", "跳痛"],
            ["烦躁", "易怒", "心烦"],
            ["失眠", "睡眠差", "夜寐不宁", "寐差"],
            ["舌红", "舌偏红"],
            ["苔黄", "苔薄黄"],
            ["脉弦", "脉弦数"],
            ["面红", "血压高", "偏头痛"],
        ],
    },
    {
        "name": "痰浊阻络",
        "cues": [
            ["恶心", "呕吐", "呕恶"],
            ["头昏", "头晕", "昏蒙"],
            ["胸闷", "纳呆"],
            ["乏力", "倦怠"],
            ["苔白腻"],
            ["脉滑", "脉弦滑"],
        ],
    },
    {
        "name": "风热上扰",
        "cues": [
            ["头痛而胀", "胀痛"],
            ["发热", "恶风"],
            ["面红", "目赤"],
            ["口渴"],
            ["苔薄黄"],
            ["脉浮数"],
        ],
    },
    {
        "name": "风寒外束",
        "cues": [
            ["畏寒", "恶寒", "怕冷"],
            ["无汗", "少汗"],
            ["项背痛", "痛连项背"],
            ["苔薄白"],
            ["脉浮紧"],
        ],
    },
    {
        "name": "瘀血阻络",
        "cues": [
            ["固定痛", "痛处固定"],
            ["刺痛", "锥刺"],
            ["外伤", "外伤史"],
            ["夜重", "日轻夜重"],
            ["舌紫", "瘀点", "瘀斑"],
        ],
    },
    {
        "name": "血虚不荣",
        "cues": [
            ["失眠", "心悸"],
            ["乏力", "神疲"],
            ["遇劳加重"],
            ["舌淡"],
            ["脉细弱"],
        ],
    },
]


def normalize_text(text: str) -> str:
    source = (text or "").replace("\ufeff", "").replace("\u3000", " ")
    source = source.replace("：", ":")
    source = re.sub(r"\r\n?", "\n", source)
    source = re.sub(r"[ \t]+", " ", source)
    source = re.sub(r"\n{3,}", "\n\n", source)
    return source.strip()


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(text))


def dedup_keep_order(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def excerpt(text: str, limit: int = 180) -> str:
    source = compact_text(text)
    if len(source) <= limit:
        return source
    return f"{source[:limit].rstrip()}..."


def canonical_field(raw_key: str) -> str | None:
    key = compact_text(raw_key).replace(" ", "")
    for alias, canonical in FIELD_ALIASES.items():
        if alias in key:
            return canonical
    return None


def extract_fields(question: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None

    for raw_line in normalize_text(question).splitlines():
        line = raw_line.strip()
        if not line:
            continue

        matched = re.match(r"^([\u4e00-\u9fffA-Za-z0-9/（）()、\-]+):\s*(.+)$", line)
        if matched:
            key = canonical_field(matched.group(1))
            if key:
                current_key = key
                value = matched.group(2).strip()
                if value:
                    fields[key] = f"{fields.get(key, '')} {value}".strip()
                continue

        if current_key:
            fields[current_key] = f"{fields.get(current_key, '')} {line}".strip()

    return fields


def detect_symptoms(text: str) -> list[str]:
    normalized = compact_text(text)
    hits: list[str] = []
    for name, aliases in SYMPTOM_ALIASES.items():
        positive_alias = next(
            (
                alias
                for alias in aliases
                if alias in normalized
                and not re.search(rf"(无|否认|未见|未诉)[^，。；;\n ]{{0,8}}{re.escape(alias)}", normalized)
            ),
            "",
        )
        if positive_alias:
            hits.append(name)
    return hits


def detect_danger_signs(text: str) -> tuple[list[str], list[str]]:
    normalized = compact_text(text)
    present: list[str] = []
    absent: list[str] = []

    for name, aliases in DANGER_ALIASES.items():
        alias_hits = [alias for alias in aliases if alias in normalized]
        if not alias_hits:
            continue

        negative_hit = any(re.search(rf"(无|否认|未见|未诉){re.escape(alias)}", normalized) for alias in alias_hits)
        if negative_hit:
            absent.append(name)
        else:
            present.append(name)

    return dedup_keep_order(present), dedup_keep_order(absent)


def detect_vitals(text: str) -> dict[str, str]:
    normalized = compact_text(text)
    vitals: dict[str, str] = {}

    patterns = {
        "T": r"T\s*([0-9]+(?:\.[0-9]+)?\s*℃?)",
        "P": r"P\s*([0-9]+(?:\.[0-9]+)?\s*次/分)",
        "R": r"R\s*([0-9]+(?:\.[0-9]+)?\s*次/分)",
        "BP": r"BP\s*([0-9]{2,3}\s*/\s*[0-9]{2,3}(?:\s*mmHg)?)",
        "SpO2": r"SpO2\s*([0-9]{2,3}\s*%?)",
    }

    for key, pattern in patterns.items():
        matched = re.search(pattern, normalized, flags=re.IGNORECASE)
        if matched:
            vitals[key] = matched.group(1).strip()

    return vitals


def detect_pain_score(text: str) -> str:
    normalized = compact_text(text)
    matched = re.search(r"(NRS|VAS)\s*([0-9]{1,2})\s*分?", normalized, flags=re.IGNORECASE)
    if not matched:
        return ""
    return f"{matched.group(1).upper()} {matched.group(2)}分"


def parse_bp_level(bp_text: str) -> str:
    if not bp_text:
        return ""
    matched = re.search(r"([0-9]{2,3})\s*/\s*([0-9]{2,3})", bp_text)
    if not matched:
        return ""
    systolic = int(matched.group(1))
    diastolic = int(matched.group(2))
    if systolic >= 180 or diastolic >= 120:
        return "重度升高"
    if systolic >= 160 or diastolic >= 100:
        return "中度升高"
    if systolic >= 140 or diastolic >= 90:
        return "轻度升高"
    return ""


def detect_tcm_findings(text: str, fields: dict[str, str]) -> list[str]:
    collected: list[str] = []
    source = " ".join(
        value for value in [fields.get("tcm_findings", ""), fields.get("history", ""), compact_text(text)] if value
    )

    for pattern in (r"舌[^，。；;\n ]{0,12}", r"苔[^，。；;\n ]{0,12}", r"脉[^，。；;\n ]{0,12}"):
        collected.extend(re.findall(pattern, source))

    normalized_items = [item.strip(" ，。；;") for item in collected if item.strip()]
    normalized_items = [item for item in normalized_items if len(item) >= 2]
    deduped = dedup_keep_order(normalized_items)
    filtered: list[str] = []
    for item in deduped:
        if any(item != other and item in other for other in deduped):
            continue
        filtered.append(item)
    return filtered


def infer_main_complaint(fields: dict[str, str], symptoms: list[str]) -> str:
    chief = compact_text(fields.get("chief_complaint", ""))
    for symptom in symptoms:
        if symptom in chief:
            return symptom
    return symptoms[0] if symptoms else ""


def infer_pattern_candidates(main_complaint: str, summary_blob: str) -> list[dict[str, Any]]:
    if main_complaint != "头痛":
        return []

    ranked: list[dict[str, Any]] = []
    for pattern in HEADACHE_PATTERNS:
        score = 0
        reasons: list[str] = []
        for cue_group in pattern["cues"]:
            matched = next((cue for cue in cue_group if cue in summary_blob), "")
            if matched:
                score += 1
                reasons.append(matched)
        if score >= 2:
            ranked.append(
                {
                    "name": pattern["name"],
                    "score": score,
                    "reasons": reasons[:4],
                }
            )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:2]


def extract_case_profile(question: str) -> dict[str, Any]:
    normalized = normalize_text(question)
    fields = extract_fields(normalized)
    vitals = detect_vitals(normalized)
    pain_score = detect_pain_score(" ".join([fields.get("pain_score", ""), normalized]))

    sex = ""
    age = ""
    patient_blob = compact_text(fields.get("patient", "")) or compact_text(normalized)

    sex_age_match = re.search(r"(男|女)[，, ]*(\d{1,3})岁", patient_blob)
    age_sex_match = re.search(r"(\d{1,3})岁[，, ]*(男|女)", patient_blob)
    if sex_age_match:
        sex = sex_age_match.group(1)
        age = f"{sex_age_match.group(2)}岁"
    elif age_sex_match:
        age = f"{age_sex_match.group(1)}岁"
        sex = age_sex_match.group(2)

    department = ""
    for dept in ("神经内科", "心内科", "呼吸科", "内科", "外科", "妇科", "儿科", "急诊", "门诊", "住院"):
        if dept in patient_blob:
            department = dept
            break

    symptom_blob = " ".join(
        [
            fields.get("chief_complaint", ""),
            fields.get("history", ""),
            fields.get("past_history", ""),
            fields.get("tcm_findings", ""),
            normalized,
        ]
    )
    symptoms = detect_symptoms(symptom_blob)
    main_complaint = infer_main_complaint(fields, symptoms)

    danger_present, danger_absent = detect_danger_signs(" ".join([fields.get("danger_signs", ""), normalized]))
    tcm_findings = detect_tcm_findings(normalized, fields)
    bp_level = parse_bp_level(vitals.get("BP", ""))
    summary_blob = compact_text(
        " ".join(
            [
                main_complaint,
                " ".join(symptoms),
                " ".join(tcm_findings),
                bp_level,
                fields.get("history", ""),
                fields.get("past_history", ""),
            ]
        )
    )
    pattern_candidates = infer_pattern_candidates(main_complaint, summary_blob)

    suggested_terms = dedup_keep_order(
        [main_complaint]
        + symptoms[:8]
        + [item["name"] for item in pattern_candidates]
        + ([bp_level] if bp_level else [])
    )

    is_case = bool(fields) and (len(fields) >= 3 or bool(vitals) or bool(pain_score))
    if not is_case:
        strong_markers = ["主诉", "现病史", "生命体征", "危险征象", "舌", "脉", "NRS", "SpO2", "BP"]
        marker_hits = sum(1 for marker in strong_markers if marker in normalized)
        is_case = marker_hits >= 3

    summary_parts: list[str] = []
    if sex or age:
        summary_parts.append(f"{sex}{age}".strip())
    if department:
        summary_parts.append(department)
    if main_complaint:
        summary_parts.append(f"以{main_complaint}为主")
    if pain_score:
        summary_parts.append(pain_score)
    if bp_level:
        summary_parts.append(f"血压{bp_level}")
    if pattern_candidates:
        summary_parts.append(f"证候更偏向{pattern_candidates[0]['name']}")

    return {
        "isCase": is_case,
        "fields": fields,
        "sex": sex,
        "age": age,
        "department": department,
        "mainComplaint": main_complaint,
        "symptoms": symptoms,
        "dangerSignsPresent": danger_present,
        "dangerSignsAbsent": danger_absent,
        "vitals": vitals,
        "painScore": pain_score,
        "bpLevel": bp_level,
        "tcmFindings": tcm_findings,
        "patternCandidates": pattern_candidates,
        "suggestedTerms": suggested_terms,
        "summary": excerpt("，".join(summary_parts), 150),
    }
