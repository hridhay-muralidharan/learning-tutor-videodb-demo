"""Generic course configuration validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import CourseError, artifact_path, course_path, load_course, read_json


REQUIRED_COURSE_KEYS = {
    "title",
    "learner_level",
    "active_scope",
    "readiness",
    "generation",
}

SOURCE_FILES = {
    "syllabus_sources.json": list,
    "textbook_sources.json": list,
    "video_sources.json": list,
    "question_bank_sources.json": list,
    "lesson_map.json": dict,
}


def validate_course(course_arg: str | Path) -> tuple[list[str], list[str]]:
    course = load_course(course_arg)
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_COURSE_KEYS - set(course))
    errors.extend(f"course.yaml missing key: {key}" for key in missing)

    for filename, expected_type in SOURCE_FILES.items():
        path = course_path(course, filename)
        if not path.exists():
            errors.append(f"missing source file: {filename}")
            continue
        try:
            payload = read_json(path)
        except Exception as exc:
            errors.append(f"{filename}: {exc}")
            continue
        if not isinstance(payload, expected_type):
            errors.append(f"{filename}: expected {expected_type.__name__}")

    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    lessons = lesson_map.get("lessons", []) if isinstance(lesson_map, dict) else []
    if not lessons:
        errors.append("lesson_map.json must include at least one lesson")
    for idx, lesson in enumerate(lessons, 1):
        _require(lesson, ["id", "title", "module", "syllabus_anchor"], f"lesson {idx}", errors)

    artifacts = {
        "syllabus_index.json": course["readiness"].get("requires_syllabus_index", True),
        "textbook_index.json": course["readiness"].get("requires_textbook_index", True),
        "question_index.json": not course["readiness"].get("allow_missing_questions", False),
        "video_index.json": course["readiness"].get("requires_video_index", True),
        "lesson_plan.json": course["generation"].get("uses_prebuilt_lesson_plan", True),
    }
    for filename, required in artifacts.items():
        path = artifact_path(course, filename)
        if not path.exists():
            message = f"artifact not present yet: {filename}"
            if required and not course["generation"].get("allow_bundled_source_gap", False):
                errors.append(message)
            else:
                warnings.append(message)

    return errors, warnings


def _require(payload: dict[str, Any], keys: list[str], label: str, errors: list[str]) -> None:
    for key in keys:
        if not payload.get(key):
            errors.append(f"{label}: missing {key}")


def assert_valid_course(course_arg: str | Path) -> None:
    errors, _warnings = validate_course(course_arg)
    if errors:
        raise CourseError("\n".join(errors))
