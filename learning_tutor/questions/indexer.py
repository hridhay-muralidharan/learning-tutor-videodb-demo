"""Question source validation and lightweight exercise indexing."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ..config import artifact_path, course_path, load_course, read_json, write_json
from ..textbooks.indexer import _extract_pages, _extract_text, _keywords


def validate_questions(course_arg: str | Path) -> tuple[list[str], list[str]]:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "question_bank_sources.json"), default=[])
    errors: list[str] = []
    warnings: list[str] = []
    if not sources and not course.get("readiness", {}).get("allow_missing_questions", False):
        errors.append("question_bank_sources.json has no sources")
    for source in sources:
        source_id = source.get("id", "unknown")
        if not source.get("citation_label"):
            errors.append(f"{source_id}: missing citation_label")
        local_path = source.get("local_path")
        if local_path and not course_path(course, local_path).exists():
            if source.get("artifact_only_allowed"):
                warnings.append(f"{source_id}: local question PDF absent; using bundled artifact evidence only")
            else:
                errors.append(f"{source_id}: local question file not found: {local_path}")
        if not local_path and not source.get("url"):
            errors.append(f"{source_id}: question source needs local_path or url")
    return errors, warnings


def index_questions(course_arg: str | Path) -> dict:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "question_bank_sources.json"), default=[])
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    questions = []
    missing_sources = []
    artifact_only_sources = []

    for source in sources:
        local_path = source.get("local_path")
        path = course_path(course, local_path) if local_path else None
        if path and path.exists():
            questions.extend(_extract_questions(path, source))
        elif source.get("artifact_only_allowed"):
            artifact_only_sources.append(source.get("id"))
        elif source.get("required", False):
            missing_sources.append(source.get("id"))

    lessons = []
    for lesson in lesson_map.get("lessons", []):
        matches = _match_questions(lesson, questions)
        if not matches and artifact_only_sources:
            matches = _artifact_questions(lesson)
        lessons.append({
            "lesson_id": lesson.get("id"),
            "title": lesson.get("title"),
            "questions": matches,
            "status": "ready" if matches else "incomplete",
            "message": None if matches else "Practice questions not linked yet.",
        })

    allow_missing = course.get("readiness", {}).get("allow_missing_questions", False)
    index = {
        "source_count": len(sources),
        "question_count": len(questions),
        "artifact_question_ref_count": sum(len(lesson.get("questions", [])) for lesson in lessons),
        "artifact_only_sources": artifact_only_sources,
        "missing_required_sources": missing_sources,
        "lessons": lessons,
        "unmatched_questions": [],
        "status": _index_status(lessons, questions, missing_sources, allow_missing),
    }
    write_json(artifact_path(course, "question_index.json"), index)
    return index


def _extract_questions(path: Path, source: dict) -> list[dict]:
    chunks = []
    for page in _extract_pages(path):
        clean = " ".join(str(page.get("text") or "").replace("\r", "\n").split())
        if not clean:
            continue
        matches = list(re.finditer(r"(?=(Q\.\s*\d+|Q\s+\d+|Q\.\d+))", clean))
        if not matches:
            chunks.append({"page": page["page"], "text": clean})
            continue
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean)
            text = clean[start:end].strip()
            if text:
                chunks.append({"page": page["page"], "text": text})
    return [
        {
            "question_id": f"{source.get('id')}_{idx:04d}",
            "citation_label": source.get("citation_label"),
            "year": source.get("year"),
            "source_url": source.get("url"),
            "source_path": source.get("local_path"),
            "page": chunk["page"],
            "prompt_preview": _clean_question_preview(chunk["text"]),
            "keywords": _keywords(chunk["text"]),
        }
        for idx, chunk in enumerate(chunks[:200], 1)
        if _looks_like_chemistry_question(chunk["text"])
    ]


def _match_questions(lesson: dict, questions: list[dict]) -> list[dict]:
    priority_terms = [str(item).lower() for item in lesson.get("question_match_terms", []) if item]
    scored = []
    for question in questions:
        haystack = " ".join([
            str(question.get("prompt_preview") or ""),
            " ".join(question.get("keywords", [])),
        ]).lower()
        hits = [term for term in priority_terms if term in haystack]
        if hits:
            scored.append((len(hits), {**question, "matched_terms": hits[:8]}))
    if scored:
        scored.sort(key=lambda item: (-item[0], -(item[1].get("year") or 0), item[1].get("page") or 0))
        return [item for _score, item in scored[:5]]

    terms = set(_keywords(" ".join([
        str(lesson.get("title") or ""),
        str(lesson.get("module") or ""),
        str(lesson.get("syllabus_anchor") or ""),
    ])))
    matches = []
    for question in questions:
        overlap = terms.intersection(set(question.get("keywords", [])))
        if overlap:
            matches.append({**question, "matched_terms": sorted(overlap)[:8]})
        if len(matches) >= 5:
            break
    return matches


def _clean_question_preview(text: str, limit: int = 500) -> str:
    text = re.sub(r"Chemistry \(CY\)\s+Page \d+ of \d+\s+Organizing Institute:[^Q]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _looks_like_chemistry_question(text: str) -> bool:
    lower = text.lower()
    if "general aptitude" in lower:
        return False
    return bool(re.search(r"\bQ\.?\s*(1[1-9]|[2-6][0-9])\b", text))


def _artifact_questions(lesson: dict) -> list[dict]:
    refs = []
    for item in lesson.get("bundled_question_refs", []):
        refs.append({
            **item,
            "artifact_only": True,
            "keywords": _keywords(" ".join([
                str(item.get("prompt_preview") or ""),
                str(lesson.get("title") or ""),
                str(lesson.get("syllabus_anchor") or ""),
            ])),
        })
    return refs


def _index_status(lessons: list[dict], questions: list[dict], missing_sources: list[str], allow_missing: bool) -> str:
    if missing_sources:
        return "incomplete"
    if questions:
        return "ready"
    if lessons and all(lesson.get("questions") for lesson in lessons):
        return "artifact_only_ready"
    return "ready" if allow_missing else "incomplete"
