"""Build a lightweight syllabus index from course-owned source manifests."""

from __future__ import annotations

from pathlib import Path

from ..config import artifact_path, course_path, load_course, read_json, write_json


def validate_syllabus(course_arg: str | Path) -> tuple[list[str], list[str]]:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "syllabus_sources.json"), default=[])
    errors: list[str] = []
    warnings: list[str] = []
    if not sources:
        errors.append("syllabus_sources.json has no sources")
    for source in sources:
        if not source.get("citation_label"):
            errors.append("syllabus source missing citation_label")
        if not source.get("url") and not source.get("local_path"):
            errors.append(f"{source.get('id', 'unknown')}: syllabus source needs url or local_path")
        local_path = source.get("local_path")
        if local_path and not course_path(course, local_path).exists():
            warnings.append(f"{source.get('id')}: local syllabus file not found; URL/artifact may still be used")
    return errors, warnings


def index_syllabus(course_arg: str | Path) -> dict:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "syllabus_sources.json"), default=[])
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    lessons = lesson_map.get("lessons", [])
    index = {
        "course_title": course.get("title"),
        "scope": course.get("active_scope"),
        "source_count": len(sources),
        "sources": sources,
        "anchors": [
            {
                "lesson_id": lesson.get("id"),
                "module": lesson.get("module"),
                "title": lesson.get("title"),
                "syllabus_anchor": lesson.get("syllabus_anchor"),
                "citation_label": _first_label(sources),
            }
            for lesson in lessons
        ],
        "status": "ready" if sources and lessons else "incomplete",
    }
    write_json(artifact_path(course, "syllabus_index.json"), index)
    return index


def _first_label(sources: list[dict]) -> str | None:
    if not sources:
        return None
    return sources[0].get("citation_label")
