from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


VECTOR_DIM = 320

COMMON_KEYWORDS = [
    "发热",
    "咳嗽",
    "咽痛",
    "腹痛",
    "腹泻",
    "失眠",
    "胸闷",
    "恶心",
    "呕吐",
    "乏力",
    "感冒",
    "中风",
    "小儿",
    "儿科",
    "妇科",
    "内科",
    "外科",
    "灸法",
    "拔罐",
    "刮痧",
    "耳穴",
    "推拿",
]

PART_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇\d]+篇")
CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇\d]+章")
SECTION_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇\d]+节")
SUB_RE = re.compile(r"^[一二三四五六七八九十]+、")
SUBSUB_RE = re.compile(r"^（[一二三四五六七八九十]+）")
TOC_RE = re.compile(r"[.．·•…]{4,}\s*\d+\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(text: str) -> str:
    text = (text or "").replace("\ufeff", "").replace("\u3000", " ")
    text = text.replace("：", ":")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(text))


def excerpt(text: str, limit: int = 180) -> str:
    source = compact_text(text)
    return source if len(source) <= limit else f"{source[:limit].rstrip()}..."


def dedup_keep_order(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def terms_of(text: str) -> list[str]:
    source = compact_text(text)
    chunks = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", source)
    terms: list[str] = []
    for chunk in chunks:
        if re.fullmatch(r"[a-zA-Z0-9]+", chunk):
            if len(chunk) >= 2:
                terms.append(chunk.lower())
            continue
        if len(chunk) <= 2:
            terms.append(chunk)
            continue
        for n in (2, 3):
            if len(chunk) < n:
                continue
            for i in range(0, len(chunk) - n + 1):
                terms.append(chunk[i : i + n])
    return dedup_keep_order(terms)


def vector_of(text: str) -> list[float]:
    vec = [0.0] * VECTOR_DIM
    tokens = terms_of(text)
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % VECTOR_DIM
        sign = -1 if int(digest[-2:], 16) % 2 else 1
        vec[idx] += float(sign)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) if a and b else 0.0


def parse_order(file_label: str) -> tuple[int, int, int]:
    src = (file_label or "").replace("KB-", "")

    def num(prefix: str) -> int:
        match = re.search(rf"{prefix}(\d+)", src, re.IGNORECASE)
        return int(match.group(1)) if match else 999

    return (num("P"), num("C"), num("S"))


def infer_intent(text: str) -> str:
    src = compact_text(text)
    if any(key in src for key in ("禁忌", "风险", "注意事项", "副反应", "不良反应")):
        return "风险评估"
    if any(key in src for key in ("适应证", "适用", "能不能用", "可不可以", "能否")):
        return "适应证判断"
    if any(key in src for key in ("宣教", "健康教育", "随访", "指导")):
        return "健康教育"
    if any(key in src for key in ("流程", "怎么做", "如何做", "操作", "步骤")):
        return "操作流程"
    return "临床护理咨询"


def iter_block_items(document: DocxDocument) -> Iterable[Paragraph | Table]:
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def heading_level(text: str, style_name: str) -> int:
    src = text.strip()
    if PART_RE.match(src):
        return 1
    if CHAPTER_RE.match(src):
        return 2
    if SECTION_RE.match(src):
        return 3
    if SUB_RE.match(src):
        return 4
    if SUBSUB_RE.match(src):
        return 5
    if style_name.startswith("Heading 1"):
        return 2
    if style_name.startswith("Heading 2"):
        return 3
    if style_name.startswith("Heading 3"):
        return 4
    return 0


def short_title(text: str) -> str:
    src = normalize_text(text)
    src = re.sub(r"^第[一二三四五六七八九十百千万零〇\d]+[篇章节]\s*", "", src)
    return src[:28] if len(src) > 28 else src


def choose_docx_path(workspace_root: Path) -> Path | None:
    configured: list[Path] = []
    cfg_path = workspace_root / "backend" / "local_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            docx_path = str(cfg.get("docxPath") or "").strip()
            if docx_path:
                configured.append(Path(docx_path))
        except Exception:
            pass

    import os

    env_raw = os.environ.get("KB_DOCX_PATH")
    if env_raw:
        configured.append(Path(env_raw))

    for candidate in configured:
        if candidate.exists() and candidate.suffix.lower() == ".docx":
            return candidate

    keyword_candidates: list[Path] = []
    search_roots = [
        workspace_root,
        workspace_root.parent,
        Path.home() / "Desktop",
        Path("D:/Desktop"),
    ]
    seen: set[Path] = set()
    for root in search_roots:
        if not root.exists() or root in seen:
            continue
        seen.add(root)
        for path in root.glob("*.docx"):
            if path.name.startswith("~$"):
                continue
            if any(key in path.name for key in ("中医护理适宜技术合稿", "中医", "适宜技术")):
                keyword_candidates.append(path)

    if keyword_candidates:
        keyword_candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        return keyword_candidates[0]

    desktop = Path("D:/Desktop")
    if desktop.exists():
        general = [p for p in desktop.glob("*.docx") if not p.name.startswith("~$")]
        if general:
            general.sort(key=lambda p: p.stat().st_size, reverse=True)
            return general[0]
    return None


class KnowledgeService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.cache_path = workspace_root / "backend" / "data" / "knowledge_cache.json"
        self.docx_path: Path | None = None
        self.data: dict[str, Any] = {}
        self.tree: list[dict[str, Any]] = []
        self.articles: list[dict[str, Any]] = []
        self.article_map: dict[str, dict[str, Any]] = {}
        self.chapters: list[dict[str, Any]] = []
        self.tag_pool: list[str] = []
        self.load()

    def load(self) -> None:
        self.docx_path = choose_docx_path(self.workspace_root)
        if self.docx_path and self.docx_path.exists():
            parsed = self._parse_docx(self.docx_path)
            self.data = parsed
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        elif self.cache_path.exists():
            self.data = json.loads(self.cache_path.read_text(encoding="utf-8-sig"))
        else:
            self.data = {
                "appName": "中医适宜技术助手",
                "generatedAt": now_string(),
                "stats": {"articleCount": 0, "partCount": 0, "lastExport": now_string()},
                "tree": [],
                "articles": [],
            }

        self.tree = self._sort_tree(self.data.get("tree", []))
        self.articles = []
        self.article_map = {}

        for raw in self.data.get("articles", []):
            article = dict(raw)
            article["_order"] = parse_order(str(article.get("fileLabel") or ""))
            article["_body_markdown"] = normalize_text(str(article.get("body") or ""))
            article["_body_plain"] = compact_text(self._markdown_to_plain(article["_body_markdown"]))
            article["_blob"] = compact_text(
                " ".join(
                    [
                        str(article.get("title") or ""),
                        str(article.get("shortTitle") or ""),
                        str(article.get("partTitle") or ""),
                        str(article.get("chapterTitle") or ""),
                        " ".join(article.get("tags") or []),
                        str(article.get("summary") or ""),
                        article["_body_plain"],
                    ]
                )
            )
            article["_vector"] = vector_of(article["_blob"])
            article["_terms"] = set(terms_of(article["_blob"]))
            self.articles.append(article)
            article_id = str(article.get("articleId") or "")
            file_label = str(article.get("fileLabel") or "")
            if article_id:
                self.article_map[article_id] = article
            if file_label:
                self.article_map[file_label] = article

        self.articles.sort(key=lambda item: (item["_order"], str(item.get("articleId") or "")))
        self._build_chapters()
        self._build_tag_pool()

    def _build_tag_pool(self) -> None:
        tags: list[str] = []
        for article in self.articles:
            tags.extend(article.get("tags") or [])
        self.tag_pool = dedup_keep_order(tags)

    def _sort_tree(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def clone(node: dict[str, Any]) -> dict[str, Any]:
            copied = dict(node)
            children = [clone(child) for child in (copied.get("children") or [])]
            children.sort(key=lambda item: (parse_order(str(item.get("fileLabel") or "")), str(item.get("title") or "")))
            copied["children"] = children
            return copied

        out = [clone(node) for node in nodes]
        out.sort(key=lambda item: (parse_order(str(item.get("fileLabel") or "")), str(item.get("title") or "")))
        return out

    def _parse_docx(self, docx_path: Path) -> dict[str, Any]:
        document = Document(str(docx_path))
        articles: list[dict[str, Any]] = []
        part_nodes: list[dict[str, Any]] = []
        chapter_nodes: dict[tuple[int, int], dict[str, Any]] = {}
        part_idx = 0
        chapter_idx = 0
        section_idx = 0
        article_seq = 0

        current_part = "第一篇 基础理论"
        current_chapter = "第一章 绪论"
        current_section = ""
        active_article: dict[str, Any] | None = None

        def ensure_part(title: str) -> None:
            nonlocal part_idx
            if not part_nodes or part_nodes[-1].get("title") != title:
                part_idx += 1
                part_nodes.append(
                    {
                        "id": f"part-{part_idx:02d}",
                        "fileLabel": f"KB-P{part_idx:02d}",
                        "type": "part",
                        "title": title,
                        "shortTitle": short_title(title),
                        "children": [],
                    }
                )

        def ensure_chapter(title: str) -> dict[str, Any]:
            nonlocal chapter_idx
            title = title.strip() or "总论"
            key = (part_idx, chapter_idx)
            if not part_nodes:
                ensure_part(current_part)
            if key in chapter_nodes and chapter_nodes[key].get("title") == title:
                return chapter_nodes[key]

            chapter_idx += 1
            key = (part_idx, chapter_idx)
            node = {
                "id": f"chapter-{part_idx:02d}-{chapter_idx:02d}",
                "fileLabel": f"KB-P{part_idx:02d}-C{chapter_idx:02d}",
                "type": "chapter",
                "title": title,
                "shortTitle": short_title(title),
                "children": [],
            }
            chapter_nodes[key] = node
            part_nodes[-1]["children"].append(node)
            return node

        def make_article_title() -> str:
            if current_section:
                return current_section
            if current_chapter:
                return f"{current_chapter} 正文"
            return "正文"

        def open_article(title: str) -> dict[str, Any]:
            nonlocal active_article, article_seq, section_idx, current_chapter
            if not part_nodes:
                ensure_part(current_part)
            if not current_chapter.strip():
                # 若在篇标题后尚未进入章节，统一挂到“总论”避免出现空章节节点
                current_chapter = "总论"
            if (part_idx, chapter_idx) not in chapter_nodes:
                ensure_chapter(current_chapter)
            if section_idx <= 0:
                section_idx = 1

            article_seq += 1
            article_id = f"article-{article_seq:04d}"
            file_label = f"KB-P{part_idx:02d}-C{chapter_idx:02d}-S{section_idx:02d}"
            active_article = {
                "articleId": article_id,
                "fileLabel": file_label,
                "title": title,
                "shortTitle": short_title(title),
                "partTitle": current_part,
                "chapterTitle": current_chapter,
                "tags": [],
                "summary": "",
                "body": "",
                "sections": [],
                "updatedAt": now_string(),
                "_blocks": [],
            }
            chapter_nodes[(part_idx, chapter_idx)]["children"].append(
                {
                    "id": article_id,
                    "fileLabel": file_label,
                    "type": "section",
                    "title": title,
                    "shortTitle": short_title(title),
                    "articleId": article_id,
                    "children": [],
                }
            )
            return active_article

        def ensure_article() -> dict[str, Any]:
            nonlocal section_idx
            if active_article:
                return active_article
            if section_idx <= 0:
                section_idx = 1
            return open_article(make_article_title())

        def push_paragraph(text: str) -> None:
            article = ensure_article()
            article["_blocks"].append({"type": "paragraph", "text": text})

        def push_heading(text: str, level: int) -> None:
            article = ensure_article()
            article["_blocks"].append({"type": "heading", "level": level, "text": text})

        def push_table(table: Table) -> None:
            rows: list[list[str]] = []
            for row in table.rows:
                cells = [compact_text(cell.text).replace("|", "｜") for cell in row.cells]
                rows.append(cells)
            rows = [row for row in rows if any(cell.strip() for cell in row)]
            if not rows:
                return
            width = max(len(row) for row in rows)
            padded = [row + [""] * (width - len(row)) for row in rows]
            headers = padded[0]
            body_rows = padded[1:] if len(padded) > 1 else []
            article = ensure_article()
            article["_blocks"].append({"type": "table", "headers": headers, "rows": body_rows})

        def finalize_article() -> None:
            nonlocal active_article
            if not active_article:
                return
            blocks = active_article.pop("_blocks", [])
            if not blocks:
                active_article = None
                return
            body_markdown = self._blocks_to_markdown(blocks)
            body_plain = self._markdown_to_plain(body_markdown)
            sections = self._split_sections(blocks)
            tags = self._collect_tags(
                active_article.get("title", ""),
                active_article.get("partTitle", ""),
                active_article.get("chapterTitle", ""),
                body_plain,
            )

            active_article["body"] = body_markdown
            active_article["summary"] = excerpt(body_plain, 150)
            active_article["sections"] = sections
            active_article["tags"] = tags
            articles.append(active_article)
            active_article = None

        ensure_part(current_part)
        ensure_chapter(current_chapter)

        for block in iter_block_items(document):
            if isinstance(block, Paragraph):
                line = normalize_text(block.text)
                if not line:
                    continue
                if line in {"目录", "目 录"} or TOC_RE.search(line):
                    continue
                if line.startswith("图 ") or line.startswith("图-"):
                    continue

                level = heading_level(line, block.style.name if block.style else "")
                if level == 1:
                    finalize_article()
                    current_part = line
                    current_chapter = ""
                    current_section = ""
                    chapter_idx = 0
                    section_idx = 0
                    ensure_part(current_part)
                    continue
                if level == 2:
                    finalize_article()
                    current_chapter = line
                    current_section = ""
                    section_idx = 0
                    ensure_chapter(current_chapter)
                    continue
                if level == 3:
                    finalize_article()
                    current_section = line
                    section_idx += 1
                    open_article(current_section)
                    continue
                if level in (4, 5):
                    push_heading(line, level)
                    continue
                push_paragraph(line)
            else:
                push_table(block)

        finalize_article()

        for article in articles:
            if not article.get("chapterTitle"):
                article["chapterTitle"] = "未分章"
            if not article.get("partTitle"):
                article["partTitle"] = "未分篇"

        tree = self._tree_from_articles(articles)
        return {
            "appName": "中医适宜技术助手",
            "generatedAt": now_string(),
            "stats": {
                "articleCount": len(articles),
                "partCount": len(tree),
                "lastExport": now_string(),
                "sourceDocx": str(docx_path),
            },
            "tree": tree,
            "articles": articles,
        }

    def _tree_from_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        part_map: dict[str, dict[str, Any]] = {}
        chapter_map: dict[tuple[str, str], dict[str, Any]] = {}
        out: list[dict[str, Any]] = []

        def part_node(part_title: str, file_label: str) -> dict[str, Any]:
            key = part_title or "未分篇"
            if key in part_map:
                return part_map[key]
            p_label = re.search(r"(KB-P\d+)", file_label or "")
            node = {
                "id": f"part-{len(part_map) + 1:02d}",
                "fileLabel": p_label.group(1) if p_label else f"KB-P{len(part_map) + 1:02d}",
                "type": "part",
                "title": key,
                "shortTitle": short_title(key),
                "children": [],
            }
            part_map[key] = node
            out.append(node)
            return node

        for article in articles:
            part_title = str(article.get("partTitle") or "未分篇")
            chapter_title = str(article.get("chapterTitle") or "未分章")
            label = str(article.get("fileLabel") or "")
            part = part_node(part_title, label)
            chapter_key = (part_title, chapter_title)
            chapter = chapter_map.get(chapter_key)
            if not chapter:
                c_label = re.search(r"(KB-P\d+-C\d+)", label)
                chapter = {
                    "id": f"chapter-{len(chapter_map) + 1:03d}",
                    "fileLabel": c_label.group(1) if c_label else label,
                    "type": "chapter",
                    "title": chapter_title,
                    "shortTitle": short_title(chapter_title),
                    "children": [],
                }
                chapter_map[chapter_key] = chapter
                part["children"].append(chapter)

            chapter["children"].append(
                {
                    "id": str(article.get("articleId") or ""),
                    "fileLabel": label,
                    "type": "section",
                    "title": str(article.get("title") or ""),
                    "shortTitle": str(article.get("shortTitle") or ""),
                    "articleId": str(article.get("articleId") or ""),
                    "children": [],
                }
            )

        for part in out:
            chapters = [ch for ch in (part.get("children") or []) if (ch.get("children") or [])]
            merged: list[dict[str, Any]] = []
            for chapter in chapters:
                if chapter.get("title") == "总论" and merged:
                    if len(chapter.get("children") or []) <= 2:
                        merged[-1]["children"].extend(chapter.get("children") or [])
                        continue
                merged.append(chapter)
            part["children"] = merged

        out.sort(key=lambda item: parse_order(str(item.get("fileLabel") or "")))
        for part in out:
            children = part.get("children") or []
            children.sort(key=lambda item: parse_order(str(item.get("fileLabel") or "")))
            for chapter in children:
                chapter_children = chapter.get("children") or []
                chapter_children.sort(key=lambda item: parse_order(str(item.get("fileLabel") or "")))

        return out

    def _blocks_to_markdown(self, blocks: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for block in blocks:
            block_type = block.get("type")
            if block_type == "paragraph":
                lines.append(str(block.get("text") or ""))
                lines.append("")
            elif block_type == "heading":
                level = int(block.get("level") or 4)
                hashes = "#" * min(max(level, 3), 6)
                lines.append(f"{hashes} {block.get('text', '')}")
                lines.append("")
            elif block_type == "table":
                headers = [str(cell or "").replace("|", "｜") for cell in (block.get("headers") or [])]
                rows = [[str(cell or "").replace("|", "｜") for cell in row] for row in (block.get("rows") or [])]
                if not headers:
                    continue
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for row in rows:
                    padded = row + [""] * (len(headers) - len(row))
                    lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
                lines.append("")
        return normalize_text("\n".join(lines))

    def _markdown_to_plain(self, markdown_text: str) -> str:
        text = normalize_text(markdown_text)
        text = re.sub(r"!\[[^\]]*]\([^)]*\)", "", text)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{2,}", "\n", text)
        return compact_text(text)

    def _split_sections(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        title = "正文"
        level = 2
        bucket: list[dict[str, Any]] = []

        def flush() -> None:
            if not bucket:
                return
            markdown = self._blocks_to_markdown(bucket)
            plain = self._markdown_to_plain(markdown)
            if plain:
                sections.append(
                    {
                        "title": title,
                        "level": level,
                        "content": markdown,
                    }
                )

        for block in blocks:
            if block.get("type") == "heading":
                flush()
                title = str(block.get("text") or "正文")
                level = int(block.get("level") or 4)
                bucket = []
                continue
            bucket.append(block)
        flush()
        if not sections:
            markdown = self._blocks_to_markdown(blocks)
            sections.append({"title": "正文", "level": 2, "content": markdown})
        return sections

    def _collect_tags(self, title: str, part_title: str, chapter_title: str, plain_text: str) -> list[str]:
        seed = [short_title(part_title), short_title(chapter_title), short_title(title)]
        text_blob = compact_text(f"{title} {part_title} {chapter_title} {plain_text}")
        for key in COMMON_KEYWORDS:
            if key in text_blob:
                seed.append(key)
        return dedup_keep_order(seed)[:10]

    def _build_chapters(self) -> None:
        grouped: dict[str, dict[str, Any]] = {}
        for article in self.articles:
            chapter_key = f"{article.get('partTitle', '')}::{article.get('chapterTitle', '')}"
            if chapter_key not in grouped:
                grouped[chapter_key] = {
                    "id": chapter_key,
                    "partTitle": article.get("partTitle", ""),
                    "chapterTitle": article.get("chapterTitle", ""),
                    "title": f"{article.get('partTitle', '')} / {article.get('chapterTitle', '')}",
                    "articleIds": [],
                    "blobParts": [],
                    "tags": [],
                }
            grouped[chapter_key]["articleIds"].append(article.get("articleId"))
            grouped[chapter_key]["blobParts"].append(article.get("_blob", ""))
            grouped[chapter_key]["tags"].extend(article.get("tags") or [])

        chapters: list[dict[str, Any]] = []
        for chapter in grouped.values():
            blob = compact_text(" ".join(chapter.pop("blobParts")))
            chapter["blob"] = blob
            chapter["vector"] = vector_of(blob)
            chapter["tags"] = dedup_keep_order(chapter.get("tags", []))
            chapters.append(chapter)

        chapters.sort(key=lambda item: item["title"])
        self.chapters = chapters

    def get_home_payload(self) -> dict[str, Any]:
        quick_entries = [self._to_article_card(article) for article in self.articles[:6]]
        tip_article = self.articles[0] if self.articles else None
        return {
            "appName": "中医适宜技术助手",
            "generatedAt": now_string(),
            "stats": {
                "articleCount": len(self.articles),
                "partCount": len(self.tree),
                "lastExport": self.data.get("stats", {}).get("lastExport", now_string()),
            },
            "quickEntries": quick_entries,
            "sampleQueries": [
                "小儿发热可用哪些中医适宜技术？",
                "耳穴压豆在失眠护理中的应用要点是什么？",
                "糖尿病患者中药湿热敷的护理观察重点有哪些？",
                "感冒患者使用艾灸时有哪些禁忌和风险提醒？",
            ],
            "dailyTip": {
                "title": "临床要点",
                "content": tip_article.get("summary", "保持辨证施护与观察记录同步进行。") if tip_article else "知识库加载中",
            },
        }

    def get_tree(self) -> list[dict[str, Any]]:
        return self.tree

    def list_articles(self, query_text: str = "", tag: str = "", limit: int = 60) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        if query_text.strip():
            analysis = self.analyze_query(query_text, {})
            retrieval = self.search(query_text, analysis, top_k=safe_limit)
            result: list[dict[str, Any]] = []
            for hit in retrieval.get("hits", []):
                article = self.article_map.get(hit.get("articleId", ""))
                if not article:
                    continue
                if tag and tag not in (article.get("tags") or []) and tag not in article.get("title", ""):
                    continue
                result.append(self._to_article_card(article, score=hit.get("score")))
            return result[:safe_limit]

        items = self.articles
        if tag:
            items = [
                article
                for article in self.articles
                if tag in (article.get("tags") or []) or tag in str(article.get("title") or "")
            ]
        return [self._to_article_card(article) for article in items[:safe_limit]]

    def _to_article_card(self, article: dict[str, Any], score: float | None = None) -> dict[str, Any]:
        payload = {
            "articleId": article.get("articleId", ""),
            "fileLabel": article.get("fileLabel", ""),
            "title": article.get("title", ""),
            "shortTitle": article.get("shortTitle", ""),
            "partTitle": article.get("partTitle", ""),
            "chapterTitle": article.get("chapterTitle", ""),
            "tags": article.get("tags", []),
            "summary": article.get("summary", ""),
            "updatedAt": article.get("updatedAt", ""),
        }
        if score is not None:
            payload["score"] = round(float(score), 2)
        return payload

    def get_article(self, article_id: str) -> dict[str, Any] | None:
        article = self.article_map.get(article_id)
        if not article:
            return None
        return {
            "articleId": article.get("articleId", ""),
            "fileLabel": article.get("fileLabel", ""),
            "title": article.get("title", ""),
            "shortTitle": article.get("shortTitle", ""),
            "partTitle": article.get("partTitle", ""),
            "chapterTitle": article.get("chapterTitle", ""),
            "tags": article.get("tags", []),
            "summary": article.get("summary", ""),
            "body": article.get("_body_markdown", article.get("body", "")),
            "sections": article.get("sections", []),
            "updatedAt": article.get("updatedAt", ""),
        }

    def analyze_query(self, question: str, memory: dict[str, Any] | None) -> dict[str, Any]:
        normalized = compact_text(question)
        keywords = terms_of(question)[:16]
        memory_tags = dedup_keep_order((memory or {}).get("memoryTags") or [])[:8]
        matched_tags: list[str] = []

        for kw in COMMON_KEYWORDS:
            if kw in normalized:
                matched_tags.append(kw)

        for tag in self.tag_pool:
            if tag and tag in normalized:
                matched_tags.append(tag)
            if len(matched_tags) >= 12:
                break

        if memory_tags:
            matched_tags.extend(memory_tags[:3])

        matched_tags = dedup_keep_order(matched_tags)[:12]
        recent_focus = str((memory or {}).get("recentFocus") or "")
        focus = matched_tags[0] if matched_tags else (recent_focus or "临床护理")

        fragments = [frag for frag in re.split(r"[，。；、\n！？? ]+", question) if frag]
        return {
            "question": question,
            "normalized": normalized,
            "intent": infer_intent(question),
            "focus": focus,
            "matchedTags": matched_tags,
            "keywords": keywords[:8],
            "fragments": fragments[:6],
            "memoryTags": memory_tags,
            "useMemory": bool(memory_tags or recent_focus),
        }

    def _best_snippet(self, article: dict[str, Any], query_terms: list[str]) -> str:
        body = str(article.get("_body_markdown") or article.get("body") or "")
        plain = self._markdown_to_plain(body)
        if not plain:
            return article.get("summary", "")
        candidates = re.split(r"(?<=[。！？；])", plain)
        best_line = ""
        best_score = -1
        for line in candidates:
            line_text = line.strip()
            if not line_text:
                continue
            score = sum(1 for term in query_terms[:8] if term and term in line_text)
            if score > best_score:
                best_score = score
                best_line = line_text
        if best_line:
            return excerpt(best_line, 220)
        return excerpt(plain, 220)

    def _score_article(
        self,
        article: dict[str, Any],
        query_vector: list[float],
        query_terms: list[str],
        tags: list[str],
    ) -> tuple[float, list[str]]:
        basis: list[str] = []
        semantic = cosine(query_vector, article.get("_vector", []))
        score = semantic * 70
        if semantic >= 0.16:
            basis.append("语义相似")

        overlap = sum(1 for term in query_terms if term and term in article.get("_blob", ""))
        if overlap:
            score += min(22, overlap * 2.6)
            basis.append("关键词命中")

        title_text = str(article.get("title") or "")
        if any(term and term in title_text for term in query_terms[:8]):
            score += 12
            basis.append("标题相关")

        tag_hit = [tag for tag in tags if tag and tag in (article.get("tags") or [])]
        if tag_hit:
            score += min(16, len(tag_hit) * 4)
            basis.append("标签匹配")

        return score, dedup_keep_order(basis)

    def _best_chapter_fallback(self, query_vector: list[float], query_terms: list[str]) -> dict[str, Any] | None:
        if not self.chapters:
            return None
        best: dict[str, Any] | None = None
        best_score = -1.0
        for chapter in self.chapters:
            semantic = cosine(query_vector, chapter.get("vector", []))
            overlap = sum(1 for term in query_terms if term and term in chapter.get("blob", ""))
            score = semantic * 65 + min(20, overlap * 2.4)
            if score > best_score:
                best_score = score
                best = chapter
        return best

    def search(self, question: str, analysis: dict[str, Any], top_k: int = 5) -> dict[str, Any]:
        safe_k = max(1, min(top_k, 12))
        query_text = compact_text(" ".join([question, analysis.get("focus", ""), " ".join(analysis.get("memoryTags", []))]))
        query_terms = dedup_keep_order(terms_of(query_text) + (analysis.get("keywords") or []))
        query_vector = vector_of(query_text)
        matched_tags = analysis.get("matchedTags") or []

        ranked: list[tuple[float, dict[str, Any], list[str]]] = []
        for article in self.articles:
            score, basis = self._score_article(article, query_vector, query_terms, matched_tags)
            ranked.append((score, article, basis))

        ranked.sort(key=lambda item: item[0], reverse=True)
        picked = [item for item in ranked[: safe_k * 3] if item[0] >= 16][:safe_k]
        chapter_context: dict[str, Any] | None = None

        if not picked and self.articles:
            chapter = self._best_chapter_fallback(query_vector, query_terms)
            if chapter:
                chapter_context = {
                    "title": chapter.get("title", ""),
                    "summary": excerpt(chapter.get("blob", ""), 280),
                }
                allowed = set(chapter.get("articleIds") or [])
                fallback = [item for item in ranked if item[1].get("articleId") in allowed][:safe_k]
                picked = fallback if fallback else ranked[:safe_k]
                picked = [(score, article, dedup_keep_order(basis + ["章节回溯"])) for score, article, basis in picked]

        hits: list[dict[str, Any]] = []
        for score, article, basis in picked[:safe_k]:
            snippet = self._best_snippet(article, query_terms)
            hits.append(
                {
                    "articleId": article.get("articleId", ""),
                    "fileLabel": article.get("fileLabel", ""),
                    "title": article.get("title", ""),
                    "score": round(score, 2),
                    "basis": basis or ["语义相关"],
                    "snippet": snippet,
                    "context": excerpt(article.get("_body_plain", ""), 420),
                }
            )

        if not chapter_context:
            chapter = self._best_chapter_fallback(query_vector, query_terms)
            if chapter:
                chapter_context = {
                    "title": chapter.get("title", ""),
                    "summary": excerpt(chapter.get("blob", ""), 280),
                }

        return {
            "matched": bool(hits),
            "hits": hits,
            "chapterContext": chapter_context or {},
        }
