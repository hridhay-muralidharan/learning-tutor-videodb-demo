"""Textbook validation and generic local passage indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import artifact_path, course_path, load_course, read_json, write_json


def validate_textbooks(course_arg: str | Path) -> tuple[list[str], list[str]]:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "textbook_sources.json"), default=[])
    errors: list[str] = []
    warnings: list[str] = []
    if not sources:
        errors.append("textbook_sources.json has no sources")
    for source in sources:
        source_id = source.get("id", "unknown")
        if source.get("source_type") == "curated_sections":
            sections = _curated_sections(course, source)
            if source.get("required", True) and not sections:
                errors.append(f"{source_id}: required curated textbook sections are missing")
            continue
        if source.get("required", True) and not source.get("local_path"):
            errors.append(f"{source_id}: required textbook needs local_path")
        if not source.get("citation_label"):
            errors.append(f"{source_id}: missing citation_label")
        local_path = source.get("local_path")
        if local_path and not course_path(course, local_path).exists():
            if source.get("artifact_only_allowed"):
                warnings.append(f"{source_id}: local textbook file absent; using bundled artifact evidence only")
            else:
                errors.append(f"{source_id}: local textbook file not found: {local_path}")
    return errors, warnings


def index_textbooks(course_arg: str | Path) -> dict:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "textbook_sources.json"), default=[])
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    passages = []
    missing_required = []
    artifact_only_sources = []

    for source in sources:
        if source.get("source_type") == "curated_sections":
            passages.extend(_curated_sections(course, source))
            continue
        path_value = source.get("local_path")
        path = course_path(course, path_value) if path_value else None
        if path and path.exists():
            for page in _extract_pages(path):
                for idx, text in enumerate(_chunk(page["text"]), 1):
                    passages.append({
                        "source_id": source.get("id"),
                        "citation_label": source.get("citation_label"),
                        "page": page["page"],
                        "chunk_id": f"{source.get('id')}_p{page['page']:04d}_{idx:02d}",
                        "text_preview": text[:700],
                        "full_text": text,
                        "content_blocks": [{"type": "paragraph", "text": text}],
                        "keywords": _keywords(text),
                    })
        elif source.get("artifact_only_allowed"):
            artifact_only_sources.append(source.get("id"))
        elif source.get("required", True):
            missing_required.append(source.get("id"))

    lessons = []
    for lesson in lesson_map.get("lessons", []):
        matched = _match_passages(lesson, passages)
        if not matched and artifact_only_sources:
            matched = _artifact_passages(lesson)
        lessons.append({
            "lesson_id": lesson.get("id"),
            "title": lesson.get("title"),
            "module": lesson.get("module"),
            "matched_passages": matched,
            "status": "ready" if matched else "incomplete",
            "message": None if matched else "Concept evidence incomplete. Add/index a relevant textbook source.",
        })

    index = {
        "source_count": len(sources),
        "passage_count": len(passages),
        "artifact_only_sources": artifact_only_sources,
        "missing_required_sources": missing_required,
        "lessons": lessons,
        "status": _index_status(lessons, passages, missing_required),
        "note": "Curated sections may intentionally bundle full text and content blocks when the source license allows in-app reading.",
    }
    write_json(artifact_path(course, "textbook_index.json"), index)
    return index


def _extract_text(path: Path) -> str:
    return "\n".join(page["text"] for page in _extract_pages(path))


def _extract_pages(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".txt":
        return [{"page": 1, "text": path.read_text(encoding="utf-8", errors="ignore")}]
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            return [{"page": 1, "text": path.read_bytes().decode("utf-8", errors="ignore")}]
    reader = PdfReader(str(path))
    pages = []
    for page_no, page in enumerate(reader.pages, 1):
        try:
            pages.append({"page": page_no, "text": page.extract_text() or ""})
        except Exception:
            pages.append({"page": page_no, "text": ""})
    return pages


def _chunk(text: str, size: int = 1800) -> list[str]:
    clean = " ".join(text.split())
    return [clean[start : start + size] for start in range(0, len(clean), size) if clean[start : start + size].strip()]


def _keywords(text: str) -> list[str]:
    words = []
    for raw in text.lower().replace("-", " ").split():
        word = "".join(ch for ch in raw if ch.isalnum())
        if len(word) >= 5 and word not in words:
            words.append(word)
        if len(words) >= 24:
            break
    return words


def _match_passages(lesson: dict, passages: list[dict]) -> list[dict]:
    terms = set(_keywords(" ".join([
        str(lesson.get("title") or ""),
        str(lesson.get("module") or ""),
        str(lesson.get("syllabus_anchor") or ""),
    ])))
    matches = []
    for passage in passages:
        if lesson.get("id") in passage.get("lesson_ids", []):
            matches.append({**passage, "matched_terms": ["curated_lesson_mapping"]})
            if len(matches) >= 3:
                break
    if matches:
        return matches
    matched_ids = {item.get("chunk_id") for item in matches}
    for passage in passages:
        if passage.get("chunk_id") in matched_ids:
            continue
        overlap = terms.intersection(set(passage.get("keywords", [])))
        if overlap:
            matches.append({**passage, "matched_terms": sorted(overlap)[:8]})
        if len(matches) >= 3:
            break
    return matches


def _curated_sections(course: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    if source.get("sections"):
        raw_sections = source.get("sections") or []
    elif source.get("local_path"):
        raw_sections = read_json(course_path(course, source["local_path"]), default=[])
    else:
        raw_sections = []

    sections = []
    for idx, section in enumerate(raw_sections, 1):
        text = str(section.get("text_preview") or section.get("full_text") or "").strip()
        if not text:
            continue
        full_text = str(section.get("full_text") or text).strip()
        content_blocks = section.get("content_blocks") or [{"type": "paragraph", "text": full_text}]
        section_title = section.get("section_title") or section.get("title")
        citation = section.get("citation_label") or source.get("citation_label")
        if section_title and citation and section_title not in citation:
            citation = f"{citation}, {section_title}"
        sections.append({
            "source_id": source.get("id"),
            "citation_label": citation,
            "source_url": section.get("source_url") or source.get("url"),
            "license": section.get("license") or source.get("license"),
            "section_title": section_title,
            "page": section.get("page"),
            "chunk_id": section.get("chunk_id") or f"{source.get('id')}_{idx:04d}",
            "text_preview": text,
            "full_text": full_text,
            "content_blocks": content_blocks,
            "keywords": section.get("keywords") or _keywords(" ".join([
                full_text,
                str(section_title or ""),
                " ".join(section.get("lesson_ids", [])),
            ])),
            "lesson_ids": section.get("lesson_ids", []),
        })
    return sections


def _artifact_passages(lesson: dict) -> list[dict]:
    citations = []
    for item in lesson.get("bundled_textbook_citations", []):
        citations.append({
            **item,
            "artifact_only": True,
            "keywords": _keywords(" ".join([
                str(item.get("text_preview") or ""),
                str(lesson.get("title") or ""),
                str(lesson.get("syllabus_anchor") or ""),
            ])),
        })
    return citations


def _index_status(lessons: list[dict], passages: list[dict], missing_required: list[str]) -> str:
    if missing_required:
        return "incomplete"
    if passages:
        return "ready"
    if lessons and all(lesson.get("matched_passages") for lesson in lessons):
        return "artifact_only_ready"
    return "incomplete"
