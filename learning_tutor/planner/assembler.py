"""Assemble lesson plans from generic evidence indexes."""

from __future__ import annotations

from pathlib import Path

from ..config import artifact_path, course_path, load_course, read_json, write_json
from ..graph.builder import build_evidence_graph, evidence_key_for_video_segment
from ..videos.manager import verify_videos


def assemble_lesson_plan(course_arg: str | Path, require_video_ready: bool = True) -> dict:
    course = load_course(course_arg)
    if require_video_ready:
        video_errors, _video_warnings, _report = verify_videos(course_arg)
        if video_errors:
            raise RuntimeError("VideoDB evidence incomplete:\n" + "\n".join(video_errors))

    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    syllabus = read_json(artifact_path(course, "syllabus_index.json"), default={"anchors": []})
    textbooks = read_json(artifact_path(course, "textbook_index.json"), default={"lessons": []})
    questions = read_json(artifact_path(course, "question_index.json"), default={"lessons": []})
    videos = read_json(artifact_path(course, "video_index.json"), default={"videos": []})
    graph = build_evidence_graph(course_arg)
    graph_by_lesson = {item.get("lesson_id"): item for item in graph.get("lessons", [])}

    syllabus_by_lesson = {item.get("lesson_id"): item for item in syllabus.get("anchors", [])}
    textbook_by_lesson = {item.get("lesson_id"): item for item in textbooks.get("lessons", [])}
    question_by_lesson = {item.get("lesson_id"): item for item in questions.get("lessons", [])}
    videos_by_lesson: dict[str, list[dict]] = {}
    for video in videos.get("videos", []):
        for lesson_id in video.get("lesson_ids", []):
            videos_by_lesson.setdefault(lesson_id, []).append(video)

    lessons = []
    for idx, lesson in enumerate(lesson_map.get("lessons", []), 1):
        lesson_id = lesson.get("id")
        lesson_graph = graph_by_lesson.get(lesson_id, {})
        textbook_evidence = textbook_by_lesson.get(lesson_id, {})
        question_evidence = question_by_lesson.get(lesson_id, {})
        textbook_items = _filter_textbook_items(textbook_evidence.get("matched_passages") or lesson.get("bundled_textbook_citations", []), lesson_graph)
        question_items = _filter_question_items(question_evidence.get("questions") or lesson.get("bundled_question_refs", []), lesson_graph)
        video_evidence = _prefer_processed_videos(videos_by_lesson.get(lesson_id, []), lesson, lesson_graph)
        completeness = {
            "syllabus": bool(syllabus_by_lesson.get(lesson_id) or lesson.get("syllabus_anchor")),
            "textbook": bool(textbook_items),
            "video": _has_graph_or_ready_video(video_evidence, lesson_graph),
            "questions": bool(question_items),
        }
        score = sum(1 for value in completeness.values() if value) / len(completeness)
        source_states = _source_states(
            textbook_items,
            video_evidence,
            question_items,
            lesson,
            lesson_graph,
        )
        lessons.append({
            "id": lesson_id,
            "order": idx,
            "title": lesson.get("title"),
            "module": lesson.get("module"),
            "syllabus_anchor": lesson.get("syllabus_anchor"),
            "concept_thread": lesson_graph.get("selected_thread") or {},
            "source_grounded_summary": lesson.get("source_grounded_summary"),
            "textbook_evidence": textbook_items,
            "video_evidence": _video_cards(video_evidence, lesson, lesson_graph),
            "question_evidence": question_items,
            "review_prompts": lesson.get("review_prompts", []),
            "readiness": {
                "state": "ready" if completeness["syllabus"] and completeness["textbook"] and completeness["video"] else "incomplete",
                "completeness": completeness,
                "source_states": source_states,
                "source_integrity_state": _source_integrity_state(source_states),
                "evidence_completeness_score": round(score, 2),
                "missing_messages": _missing_messages(completeness),
            },
            "mastery_state": "not_started",
        })

    plan = {
        "course": {
            "title": course.get("title"),
            "learner_level": course.get("learner_level"),
            "active_scope": course.get("active_scope"),
        },
        "status": "ready" if lessons and all(item["readiness"]["state"] == "ready" for item in lessons) else "incomplete",
        "lessons": lessons,
        "evidence_rules": {
            "textbook_grounding_required": course.get("readiness", {}).get("requires_textbook_index", True),
            "videodb_required_for_generation": True,
            "concept_graph_required_for_generation": True,
            "unsupported_content_policy": "missing or disconnected evidence is shown as incomplete instead of guessed",
        },
        "personalization": course.get("personalization", {}),
    }
    write_json(artifact_path(course, "lesson_plan.json"), plan)
    return plan


def _video_cards(videos: list[dict], lesson: dict | None = None, lesson_graph: dict | None = None) -> list[dict]:
    cards = []
    for video in videos:
        teaching_segment = _best_teaching_segment(video, lesson or {}, lesson_graph or {})
        if not teaching_segment:
            cards.append({
                "source_id": video.get("source_id"),
                "title": video.get("title"),
                "citation_label": video.get("citation_label"),
                "source_url": video.get("url") or video.get("source_url"),
                "video_id": video.get("video_id"),
                "collection_id": video.get("collection_id"),
                "timestamp_start": None,
                "timestamp_end": None,
                "timestamp_label": None,
                "transcript_preview": "VideoDB spoken-word search has not produced a lesson-matched teaching segment yet.",
                "evidence_mode": _unmatched_video_mode(video, lesson or {}, lesson_graph or {}),
            })
            continue
        cards.append({
            "source_id": video.get("source_id"),
            "title": video.get("title"),
            "citation_label": video.get("citation_label"),
            "source_url": video.get("url") or video.get("source_url"),
            "video_id": video.get("video_id"),
            "collection_id": video.get("collection_id"),
            "timestamp_start": teaching_segment.get("start"),
            "timestamp_end": teaching_segment.get("end"),
            "timestamp_label": teaching_segment.get("label"),
            "transcript_preview": teaching_segment.get("text"),
            "evidence_mode": teaching_segment.get("source") or "videodb_spoken_word_search",
        })
    return cards


def _prefer_processed_videos(videos: list[dict], lesson: dict | None = None, lesson_graph: dict | None = None) -> list[dict]:
    processed = [video for video in videos if _is_ready_video(video, lesson, lesson_graph) and not _has_placeholder([video])]
    return processed or videos


def _filter_textbook_items(items: list[dict], lesson_graph: dict) -> list[dict]:
    allowed_ids = _graph_evidence_ids(lesson_graph, "textbook")
    if allowed_ids is None:
        return items
    return [item for item in items if (item.get("chunk_id") or item.get("section_title")) in allowed_ids]


def _filter_question_items(items: list[dict], lesson_graph: dict) -> list[dict]:
    allowed_ids = _graph_evidence_ids(lesson_graph, "questions")
    if allowed_ids is None:
        return items
    return [item for item in items if item.get("question_id") in allowed_ids]


def _graph_evidence_ids(lesson_graph: dict, source_type: str) -> set[str] | None:
    selected = lesson_graph.get("selected_thread") or {}
    evidence_ids = selected.get("evidence_ids")
    if evidence_ids is None:
        return None
    return {str(item) for item in evidence_ids.get(source_type, []) if item}


def _graph_video_keys(lesson_graph: dict) -> set[str] | None:
    return _graph_evidence_ids(lesson_graph, "video")


def _graph_missing_source(lesson_graph: dict, source_type: str) -> bool:
    selected = lesson_graph.get("selected_thread") or {}
    return source_type in set(selected.get("missing_source_types") or [])


def _has_graph_or_ready_video(video_items: list[dict], lesson_graph: dict) -> bool:
    allowed_ids = _graph_video_keys(lesson_graph)
    if allowed_ids is not None:
        return bool(allowed_ids)
    return bool(video_items)


def _unmatched_video_mode(video: dict, lesson: dict, lesson_graph: dict) -> str:
    if not _graph_missing_source(lesson_graph, "video"):
        return "needs_review"
    if _has_placeholder([video]) or not _has_real_video_id(video):
        return "needs_review"
    technical_only_graph = {}
    if _has_incomplete_video([video], lesson, technical_only_graph):
        return "needs_review"
    return "needs_alignment"


def _source_states(textbook_items: list[dict], video_items: list[dict], question_items: list[dict], lesson: dict | None = None, lesson_graph: dict | None = None) -> dict:
    return {
        "syllabus": _source_state(True, False),
        "textbook": _source_state(bool(textbook_items), _has_placeholder(textbook_items), alignment_missing=_graph_missing_source(lesson_graph or {}, "textbook")),
        "video": _source_state(
            bool(video_items),
            _has_placeholder(video_items),
            _has_incomplete_video(video_items, lesson or {}, lesson_graph or {}),
            alignment_missing=_graph_missing_source(lesson_graph or {}, "video"),
        ),
        "questions": _source_state(bool(question_items), _has_placeholder(question_items), alignment_missing=_graph_missing_source(lesson_graph or {}, "questions")),
    }


def _source_state(has_items: bool, has_placeholder: bool, has_incomplete: bool = False, alignment_missing: bool = False) -> dict:
    if not has_items:
        return {
            "state": "needs_processing",
            "label": "Needs processing",
            "message": "This source type is not linked yet.",
        }
    if has_incomplete:
        return {
            "state": "needs_processing",
            "label": "Needs processing",
            "message": "This source type is linked but has not produced ready timestamp evidence yet.",
        }
    if has_placeholder:
        return {
            "state": "demo_placeholder",
            "label": "Demo placeholder",
            "message": "This is a bundled placeholder. Regenerate after indexing or ingesting the real source.",
        }
    if alignment_missing:
        return {
            "state": "needs_alignment",
            "label": "Needs alignment",
            "message": "This source type is linked, but not to the same concept thread as the lesson.",
        }
    return {
        "state": "source_backed",
        "label": "Source-backed",
        "message": "This lesson has processed source evidence.",
    }


def _source_integrity_state(source_states: dict) -> str:
    states = {item.get("state") for item in source_states.values()}
    if "needs_alignment" in states:
        return "needs_alignment"
    if "needs_processing" in states:
        return "needs_processing"
    if "demo_placeholder" in states:
        return "demo_placeholder"
    return "source_backed"


def _has_placeholder(items: list[dict]) -> bool:
    for item in items:
        if item.get("artifact_only"):
            return True
        if str(item.get("video_id", "")).startswith("bundled_"):
            return True
        searchable = " ".join(str(item.get(key, "")) for key in (
            "text_preview",
            "prompt_preview",
            "transcript_preview",
            "note",
        )).lower()
        if "placeholder" in searchable or "marker" in searchable:
            return True
    return False


def _has_incomplete_video(items: list[dict], lesson: dict, lesson_graph: dict | None = None) -> bool:
    return any(_looks_like_video(item) and not _is_ready_video(item, lesson, lesson_graph) and not str(item.get("video_id", "")).startswith("bundled_") for item in items)


def _looks_like_video(item: dict) -> bool:
    return any(key in item for key in ("video_id", "upload_status", "spoken_word_index_status", "timestamp_searchable", "transcript_cache"))


def _is_ready_video(item: dict, lesson: dict | None = None, lesson_graph: dict | None = None) -> bool:
    transcript = item.get("transcript_cache") or {}
    return (
        _has_real_video_id(item)
        and item.get("upload_status") == "uploaded"
        and item.get("spoken_word_index_status") == "ready"
        and bool(item.get("timestamp_searchable"))
        and bool(transcript.get("segments"))
        and _has_valid_videodb_segment(item, lesson or {}, lesson_graph or {})
    )


def _has_real_video_id(item: dict) -> bool:
    video_id = str(item.get("video_id") or "")
    return bool(video_id and not video_id.startswith("bundled_"))


INTRO_MARKERS = (
    "hello",
    "welcome",
    "good evening",
    "very good evening",
    "कैसे हो",
    "गुड इवनिंग",
    "स्वागत",
    "नमस्ते",
    "डिनर",
    "खाने",
    "ट्रेन",
    "पेंट्री",
    "पेनेट्री",
    "लाइक",
    "like",
    "share",
    "subscribe",
    "voice clear",
    "live",
    "thank you",
    "थैंक",
)


def _best_teaching_segment(video: dict, lesson: dict, lesson_graph: dict | None = None) -> dict:
    candidates = []
    allowed_keys = _graph_video_keys(lesson_graph or {})
    for validation in video.get("search_validation", []) or []:
        if lesson.get("id") and validation.get("lesson_id") and validation.get("lesson_id") != lesson.get("id"):
            continue
        if validation.get("validation_mode") != "videodb_spoken_word_search":
            continue
        results = validation.get("results") or []
        for result in results:
            segment_key = evidence_key_for_video_segment(str(video.get("source_id") or ""), result)
            if allowed_keys is not None and segment_key not in allowed_keys:
                continue
            if _valid_teaching_clip(result, lesson):
                enriched = {**result, "source": "videodb_spoken_word_search", "source_id": video.get("source_id"), "concept_evidence_id": segment_key}
                candidates.append((_clip_score(enriched, lesson, trusted_search=True), enriched))

    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return {}


def _has_valid_videodb_segment(video: dict, lesson: dict, lesson_graph: dict | None = None) -> bool:
    return bool(_best_teaching_segment(video, lesson, lesson_graph or {}))


def _valid_teaching_clip(segment: dict, lesson: dict) -> bool:
    start = _float_or_none(segment.get("start"))
    end = _float_or_none(segment.get("end"))
    text = str(segment.get("text") or "").strip()
    if start is None or end is None or not text:
        return False
    duration = end - start
    if duration < 25:
        return False
    if len(text) < 70:
        return False
    if _mostly_noise(text):
        return False
    haystack = _segment_topic_haystack(segment)
    intro_count = _intro_marker_count(text)
    if intro_count >= 3:
        return False
    if intro_count and _topic_hit_count(haystack, lesson) < 2:
        return False
    return _topic_hit_count(haystack, lesson) >= 1


def _clip_score(segment: dict, lesson: dict, trusted_search: bool) -> float:
    start = float(segment.get("start") or 0)
    end = float(segment.get("end") or start)
    duration = max(0, end - start)
    text = str(segment.get("text") or "")
    concept_hits = _topic_hit_count(_segment_topic_haystack(segment), lesson)
    intro_count = _intro_marker_count(text)

    score = 0.0
    score += min(duration, 180) / 30
    score += min(len(text), 1400) / 280
    score += concept_hits * 2
    if trusted_search:
        score += 1.5
    if _matches_preferred_window(segment, lesson):
        score += 10
    if start >= 60:
        score += 2
    if start >= 180:
        score += 1
    if duration < 20:
        score -= 5
    if len(text.strip()) < 80:
        score -= 5
    score -= intro_count * 4
    if start < 90 and intro_count:
        score -= 8
    if _mostly_noise(text):
        score -= 8
    return score


def _matches_preferred_window(segment: dict, lesson: dict) -> bool:
    start = _float_or_none(segment.get("start"))
    end = _float_or_none(segment.get("end"))
    if start is None or end is None:
        return False
    source_id = str(segment.get("source_id") or "")
    for window in lesson.get("video_preferred_windows") or []:
        preferred_source = str(window.get("source_id") or "")
        if preferred_source and preferred_source != source_id:
            continue
        preferred_start = _float_or_none(window.get("start"))
        preferred_end = _float_or_none(window.get("end"))
        if preferred_start is None or preferred_end is None:
            continue
        if abs(start - preferred_start) <= 12 or (start >= preferred_start and end <= preferred_end):
            return True
    return False


def _topic_hit_count(text: str, lesson: dict) -> int:
    normalized = text.casefold()
    return sum(1 for term in _lesson_terms(lesson) if term in normalized)


def _segment_topic_haystack(segment: dict) -> str:
    return " ".join(str(segment.get(key) or "") for key in ("text", "query"))


def _intro_marker_count(text: str) -> int:
    normalized = text.casefold()
    return sum(1 for marker in INTRO_MARKERS if marker in normalized)


def _lesson_terms(lesson: dict) -> set[str]:
    values = [
        lesson.get("title"),
        lesson.get("module"),
        lesson.get("syllabus_anchor"),
        lesson.get("source_grounded_summary"),
        *(lesson.get("question_match_terms") or []),
        *(lesson.get("video_validation_terms") or []),
    ]
    terms = set()
    for value in values:
        for raw in str(value or "").replace("/", " ").replace("-", " ").split():
            term = raw.casefold().strip(".,:;()[]{}")
            if len(term) >= 5:
                terms.add(term)
    return terms


def _mostly_noise(text: str) -> bool:
    stripped = "".join(char for char in text if char.isalnum())
    return len(stripped) < 12


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _missing_messages(completeness: dict[str, bool]) -> list[str]:
    messages = []
    if not completeness.get("textbook"):
        messages.append("Concept evidence incomplete. Add/index a relevant textbook source.")
    if not completeness.get("video"):
        messages.append("VideoDB evidence incomplete. Complete video ingest and verification before generating this lesson.")
    if not completeness.get("questions"):
        messages.append("Practice questions not linked yet.")
    return messages
