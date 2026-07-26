"""Build a concept graph across syllabus, textbook, video, and question evidence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import artifact_path, course_path, load_course, read_json, write_json


SOURCE_TYPES = ("textbook", "video", "questions")
DEFAULT_REQUIRED_SOURCE_TYPES = ("textbook", "video", "questions")


def build_evidence_graph(course_arg: str | Path) -> dict:
    course = load_course(course_arg)
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    syllabus = read_json(artifact_path(course, "syllabus_index.json"), default={"anchors": []})
    textbooks = read_json(artifact_path(course, "textbook_index.json"), default={"lessons": []})
    questions = read_json(artifact_path(course, "question_index.json"), default={"lessons": []})
    videos = read_json(artifact_path(course, "video_index.json"), default={"videos": []})

    syllabus_by_lesson = {item.get("lesson_id"): item for item in syllabus.get("anchors", [])}
    textbook_by_lesson = {item.get("lesson_id"): item for item in textbooks.get("lessons", [])}
    question_by_lesson = {item.get("lesson_id"): item for item in questions.get("lessons", [])}
    videos_by_lesson: dict[str, list[dict]] = {}
    for video in videos.get("videos", []):
        for lesson_id in video.get("lesson_ids", []):
            videos_by_lesson.setdefault(lesson_id, []).append(video)

    graph = {
        "status": "ready",
        "course_title": course.get("title"),
        "model": {
            "principle": "A lesson is assembled from the strongest shared concept thread across indexed source types.",
            "primary_rule": "Primary evidence must connect through the same concept thread; broad lesson-id matches are treated as insufficient.",
            "source_types": list(SOURCE_TYPES),
        },
        "nodes": [],
        "edges": [],
        "lessons": [],
    }

    for lesson in lesson_map.get("lessons", []):
        lesson_node_id = _node_id("lesson", lesson.get("id"))
        graph["nodes"].append({
            "id": lesson_node_id,
            "type": "lesson",
            "label": lesson.get("title") or lesson.get("id"),
            "lesson_id": lesson.get("id"),
        })
        lesson_graph = _lesson_graph(
            lesson,
            syllabus_by_lesson.get(lesson.get("id"), {}),
            textbook_by_lesson.get(lesson.get("id"), {}),
            question_by_lesson.get(lesson.get("id"), {}),
            videos_by_lesson.get(lesson.get("id"), []),
            graph,
            lesson_node_id,
        )
        graph["lessons"].append(lesson_graph)

    graph["status"] = "ready" if all(item.get("selected_thread", {}).get("alignment_state") == "source_backed" for item in graph["lessons"]) else "needs_alignment"
    write_json(artifact_path(course, "evidence_graph.json"), graph)
    return graph


def verify_evidence_graph(course_arg: str | Path) -> tuple[list[str], list[str], dict]:
    graph = build_evidence_graph(course_arg)
    errors: list[str] = []
    warnings: list[str] = []
    for lesson in graph.get("lessons", []):
        selected = lesson.get("selected_thread") or {}
        missing = selected.get("missing_source_types") or []
        if missing:
            warnings.append(
                f"{lesson.get('lesson_id')}: selected thread '{selected.get('label')}' missing {', '.join(missing)}"
            )
        video_only = [
            item.get("label") for item in lesson.get("concept_threads", [])
            if item.get("source_coverage", {}).get("video", 0) and not item.get("source_coverage", {}).get("textbook", 0)
        ]
        if video_only:
            warnings.append(f"{lesson.get('lesson_id')}: video-only concept thread(s): {', '.join(video_only)}")
    report = {
        "status": graph.get("status"),
        "lesson_count": len(graph.get("lessons", [])),
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
    }
    return errors, warnings, report


def evidence_key_for_video_segment(source_id: str, segment: dict) -> str:
    return f"{source_id}:{_number_key(segment.get('start'))}-{_number_key(segment.get('end'))}"


def _lesson_graph(
    lesson: dict,
    syllabus_anchor: dict,
    textbook_evidence: dict,
    question_evidence: dict,
    videos: list[dict],
    graph: dict,
    lesson_node_id: str,
) -> dict:
    threads = _concept_threads(lesson)
    thread_graphs = []
    for thread in threads:
        concept_node_id = _node_id("concept", lesson.get("id"), thread.get("id"))
        graph["nodes"].append({
            "id": concept_node_id,
            "type": "concept",
            "label": thread.get("label") or thread.get("id"),
            "lesson_id": lesson.get("id"),
            "concept_id": thread.get("id"),
        })
        graph["edges"].append({
            "from": lesson_node_id,
            "to": concept_node_id,
            "type": "defines_thread",
            "weight": 1.0,
        })
        thread_graphs.append(_thread_graph(
            lesson,
            thread,
            syllabus_anchor,
            textbook_evidence,
            question_evidence,
            videos,
            graph,
            concept_node_id,
        ))

    selected = _select_thread(thread_graphs)
    return {
        "lesson_id": lesson.get("id"),
        "title": lesson.get("title"),
        "selected_thread": _thread_summary(selected),
        "concept_threads": thread_graphs,
    }


def _thread_graph(
    lesson: dict,
    thread: dict,
    syllabus_anchor: dict,
    textbook_evidence: dict,
    question_evidence: dict,
    videos: list[dict],
    graph: dict,
    concept_node_id: str,
) -> dict:
    aliases = _aliases_for_thread(thread)
    evidence = {
        "syllabus": _syllabus_matches(lesson, syllabus_anchor, aliases),
        "textbook": _textbook_matches(textbook_evidence.get("matched_passages", []), aliases),
        "video": _video_matches(videos, lesson.get("id"), aliases),
        "questions": _question_matches(question_evidence.get("questions", []), aliases),
    }
    source_coverage = {source_type: len(evidence[source_type]) for source_type in ("textbook", "video", "questions")}
    required = list(thread.get("required_source_types") or DEFAULT_REQUIRED_SOURCE_TYPES)
    missing = [source_type for source_type in required if not source_coverage.get(source_type)]
    alignment_state = "source_backed" if not missing else "needs_alignment"
    score = _alignment_score(source_coverage, required, bool(evidence["syllabus"]), bool(thread.get("primary", True)))

    for source_type, items in evidence.items():
        for item in items:
            node_id = _node_id(source_type, item.get("id"))
            graph["nodes"].append({
                "id": node_id,
                "type": source_type,
                "label": item.get("label") or item.get("id"),
                "lesson_id": lesson.get("id"),
            })
            graph["edges"].append({
                "from": concept_node_id,
                "to": node_id,
                "type": "supported_by",
                "source_type": source_type,
                "weight": item.get("score", 1.0),
                "evidence_id": item.get("id"),
            })

    return {
        "id": thread.get("id"),
        "label": thread.get("label") or thread.get("id"),
        "aliases": aliases,
        "primary": bool(thread.get("primary", True)),
        "required_source_types": required,
        "source_coverage": source_coverage,
        "missing_source_types": missing,
        "alignment_state": alignment_state,
        "alignment_score": round(score, 3),
        "evidence": evidence,
    }


def _select_thread(threads: list[dict]) -> dict:
    if not threads:
        return {
            "id": "unmapped",
            "label": "Unmapped concept",
            "source_coverage": {},
            "missing_source_types": list(DEFAULT_REQUIRED_SOURCE_TYPES),
            "alignment_state": "needs_alignment",
            "alignment_score": 0,
            "evidence": {},
        }
    primary_threads = [item for item in threads if item.get("primary", True)]
    pool = primary_threads or threads
    return max(pool, key=lambda item: item.get("alignment_score", 0))


def _thread_summary(thread: dict) -> dict:
    return {
        "id": thread.get("id"),
        "label": thread.get("label"),
        "source_coverage": thread.get("source_coverage", {}),
        "missing_source_types": thread.get("missing_source_types", []),
        "alignment_state": thread.get("alignment_state"),
        "alignment_score": thread.get("alignment_score", 0),
        "evidence_ids": {
            source_type: [item.get("id") for item in items]
            for source_type, items in (thread.get("evidence") or {}).items()
        },
    }


def _concept_threads(lesson: dict) -> list[dict]:
    configured = lesson.get("concept_threads") or []
    if configured:
        return configured
    aliases = []
    for value in (
        lesson.get("title"),
        lesson.get("module"),
        lesson.get("syllabus_anchor"),
        *(lesson.get("question_match_terms") or []),
        *(lesson.get("video_validation_terms") or []),
    ):
        aliases.extend(_keywords_from_text(str(value or "")))
    return [{
        "id": "main_thread",
        "label": lesson.get("title") or "Main concept",
        "aliases": sorted(set(aliases)),
        "required_source_types": list(DEFAULT_REQUIRED_SOURCE_TYPES),
        "primary": True,
    }]


def _aliases_for_thread(thread: dict) -> list[str]:
    values = [thread.get("label"), *(thread.get("aliases") or [])]
    aliases: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            aliases.append(text)
    return sorted(set(aliases), key=lambda item: (-len(item), item.casefold()))


def _syllabus_matches(lesson: dict, syllabus_anchor: dict, aliases: list[str]) -> list[dict]:
    text = _join_fields(lesson, ("title", "module", "syllabus_anchor", "source_grounded_summary"))
    text += " " + _join_fields(syllabus_anchor, ("anchor_text", "title", "module", "matched_text"))
    hits = _hits(text, aliases)
    if not hits:
        return []
    return [{
        "id": f"{lesson.get('id')}:syllabus",
        "label": lesson.get("syllabus_anchor") or lesson.get("title"),
        "matched_aliases": hits,
        "score": _hit_score(hits),
    }]


def _textbook_matches(items: list[dict], aliases: list[str]) -> list[dict]:
    matches = []
    for item in items:
        text = _join_fields(item, ("section_title", "text_preview", "full_text"))
        text += " " + " ".join(str(keyword) for keyword in item.get("keywords", []))
        hits = _hits(text, aliases)
        if hits:
            matches.append({
                "id": item.get("chunk_id") or item.get("section_title"),
                "label": item.get("section_title") or item.get("citation_label"),
                "matched_aliases": hits,
                "score": _hit_score(hits),
            })
    return sorted(matches, key=lambda item: item.get("score", 0), reverse=True)


def _question_matches(items: list[dict], aliases: list[str]) -> list[dict]:
    matches = []
    for item in items:
        text = _join_fields(item, ("prompt_preview", "citation_label"))
        text += " " + " ".join(str(keyword) for keyword in item.get("keywords", []))
        text += " " + " ".join(str(term) for term in item.get("matched_terms", []))
        hits = _hits(text, aliases)
        if hits:
            matches.append({
                "id": item.get("question_id"),
                "label": item.get("prompt_preview"),
                "matched_aliases": hits,
                "score": _hit_score(hits),
            })
    return sorted(matches, key=lambda item: item.get("score", 0), reverse=True)


def _video_matches(videos: list[dict], lesson_id: str | None, aliases: list[str]) -> list[dict]:
    matches = []
    for video in videos:
        source_id = str(video.get("source_id") or "")
        for validation in video.get("search_validation", []) or []:
            if lesson_id and validation.get("lesson_id") and validation.get("lesson_id") != lesson_id:
                continue
            if validation.get("validation_mode") != "videodb_spoken_word_search":
                continue
            for result in validation.get("results") or []:
                if not _valid_segment(result):
                    continue
                text = _join_fields(result, ("text", "query"))
                hits = _hits(text, aliases)
                if hits:
                    matches.append({
                        "id": evidence_key_for_video_segment(source_id, result),
                        "label": result.get("label"),
                        "source_id": source_id,
                        "start": result.get("start"),
                        "end": result.get("end"),
                        "matched_aliases": hits,
                        "score": _hit_score(hits),
                    })
    return sorted(matches, key=lambda item: item.get("score", 0), reverse=True)


def _alignment_score(source_coverage: dict[str, int], required: list[str], has_syllabus: bool, primary: bool) -> float:
    score = 0.0
    for source_type in required:
        if source_coverage.get(source_type):
            score += 10
    score += min(source_coverage.get("textbook", 0), 3) * 1.5
    score += min(source_coverage.get("video", 0), 3) * 1.5
    score += min(source_coverage.get("questions", 0), 3) * 1.0
    if has_syllabus:
        score += 2
    if primary:
        score += 1
    if source_coverage.get("video", 0) and not source_coverage.get("textbook", 0):
        score -= 8
    if source_coverage.get("video", 0) and not source_coverage.get("questions", 0):
        score -= 4
    return score


def _hits(text: str, aliases: list[str]) -> list[str]:
    normalized = _normalize(text)
    hits = []
    for alias in aliases:
        normalized_alias = _normalize(alias)
        if len(normalized_alias) < 3:
            continue
        if _contains(normalized, normalized_alias):
            hits.append(alias)
    return hits


def _contains(text: str, term: str) -> bool:
    if re.search(r"[a-z0-9]", term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def _hit_score(hits: list[str]) -> float:
    return sum(max(1.0, min(len(_normalize(hit)) / 10, 3.0)) for hit in hits)


def _keywords_from_text(text: str) -> list[str]:
    return [item for item in re.split(r"[^A-Za-z0-9]+", text.casefold()) if len(item) >= 5]


def _valid_segment(segment: dict) -> bool:
    start = _float_or_none(segment.get("start"))
    end = _float_or_none(segment.get("end"))
    text = str(segment.get("text") or "").strip()
    return start is not None and end is not None and end - start >= 25 and len(text) >= 70


def _join_fields(item: dict, keys: tuple[str, ...]) -> str:
    return " ".join(str(item.get(key) or "") for key in keys)


def _normalize(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.replace("π", "pi")
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^0-9a-z\u0900-\u097f+-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _number_key(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return "unknown"
    return f"{number:.2f}"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _node_id(*parts: Any) -> str:
    raw = ":".join(str(part or "unknown") for part in parts)
    return re.sub(r"[^A-Za-z0-9_:.+-]+", "_", raw)
