"""Thin runtime adapter around the VideoDB SDK.

Cost planning intentionally lives outside this module. Import and use this
adapter only after the explicit paid-ingest gates have passed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class VideoDBRuntimeError(RuntimeError):
    """Raised when a live VideoDB operation cannot produce ready evidence."""


class VideoDBRuntime:
    def __init__(self, api_key: str, collection_id: str | None = "default") -> None:
        try:
            import videodb
        except Exception as exc:  # pragma: no cover - exercised through manager import gate.
            raise VideoDBRuntimeError("videodb SDK is not installed.") from exc

        self._videodb = videodb
        self.connection = videodb.connect(api_key=api_key)
        self.collection_id = collection_id or "default"
        self.collection = self.connection.get_collection(self.collection_id)

    def check_usage(self) -> dict[str, Any]:
        usage = self.connection.check_usage()
        if not isinstance(usage, dict):
            raise VideoDBRuntimeError("VideoDB check_usage() returned an unexpected payload.")
        return usage

    def ingest_candidate(
        self,
        candidate: dict[str, Any],
        lesson_queries: dict[str, str | list[str]],
        requires_scene_index: bool,
        max_transcript_segments: int = 8,
        max_search_results: int = 5,
    ) -> dict[str, Any]:
        if requires_scene_index:
            raise VideoDBRuntimeError("Scene indexing is required by the course but not enabled for this ingest path.")

        video = self._upload(candidate)
        video_id = _field(video, "id")
        collection_id = _field(video, "collection_id") or self.collection_id
        if not video_id:
            raise VideoDBRuntimeError("VideoDB upload completed without a video ID.")

        index_error = None
        try:
            video.index_spoken_words(language_code=candidate.get("language_code"))
        except Exception as exc:
            index_error = str(exc)
        try:
            transcript_segments = _normalize_transcript(
                video.get_transcript(segmenter="sentence", length=1),
                max_transcript_segments,
            )
        except Exception as exc:
            transcript_segments = []
            index_error = index_error or str(exc)
        if not transcript_segments:
            return {
                "source_id": candidate.get("source_id"),
                "title": candidate.get("title"),
                "url": candidate.get("url"),
                "provider": candidate.get("provider"),
                "module": candidate.get("module"),
                "citation_label": candidate.get("citation_label"),
                "video_id": video_id,
                "collection_id": collection_id,
                "upload_status": "uploaded",
                "spoken_word_index_status": "needs_processing" if index_error else "failed",
                "scene_index_status": "not_required",
                "timestamp_searchable": False,
                "lesson_ids": candidate.get("lesson_ids", []),
                "transcript_cache": {
                    "segments": [],
                },
                "search_validation": [],
                "processing_status": "needs_processing",
                "error": index_error or "VideoDB transcript cache is empty after spoken-word indexing.",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

        search_validation, timestamp_searchable = self._search_lesson_timestamps(
            video,
            candidate.get("lesson_ids", []),
            lesson_queries,
            fallback_query=str(candidate.get("title") or ""),
            max_search_results=max_search_results,
        )

        if not timestamp_searchable:
            return {
                "source_id": candidate.get("source_id"),
                "title": candidate.get("title"),
                "url": candidate.get("url"),
                "provider": candidate.get("provider"),
                "module": candidate.get("module"),
                "citation_label": candidate.get("citation_label"),
                "video_id": video_id,
                "collection_id": collection_id,
                "upload_status": "uploaded",
                "spoken_word_index_status": "ready",
                "scene_index_status": "not_required",
                "timestamp_searchable": False,
                "lesson_ids": candidate.get("lesson_ids", []),
                "transcript_cache": {
                    "segments": transcript_segments,
                },
                "search_validation": search_validation,
                "processing_status": "needs_processing",
                "error": "VideoDB spoken-word search returned no timestamped validation results.",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "source_id": candidate.get("source_id"),
            "title": candidate.get("title"),
            "url": candidate.get("url"),
            "provider": candidate.get("provider"),
            "module": candidate.get("module"),
            "citation_label": candidate.get("citation_label"),
            "video_id": video_id,
            "collection_id": collection_id,
            "upload_status": "uploaded",
            "spoken_word_index_status": "ready",
            "scene_index_status": "not_required",
            "timestamp_searchable": True,
            "lesson_ids": candidate.get("lesson_ids", []),
            "transcript_cache": {
                "segments": transcript_segments,
            },
            "search_validation": search_validation,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            **({"index_warning": index_error} if index_error else {}),
        }

    def refresh_search_validation(
        self,
        video_record: dict[str, Any],
        lesson_queries: dict[str, str | list[str]],
        max_search_results: int = 5,
    ) -> dict[str, Any]:
        video_id = video_record.get("video_id")
        if not video_id:
            raise VideoDBRuntimeError("Cannot refresh search validation without a VideoDB video_id.")
        video = self.collection.get_video(video_id)
        search_validation, timestamp_searchable = self._search_lesson_timestamps(
            video,
            video_record.get("lesson_ids", []),
            lesson_queries,
            fallback_query=str(video_record.get("title") or video_record.get("source_id") or ""),
            max_search_results=max_search_results,
        )
        return {
            **video_record,
            "search_validation": search_validation,
            "timestamp_searchable": timestamp_searchable,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _upload(self, candidate: dict[str, Any]) -> Any:
        name = candidate.get("title") or candidate.get("source_id")
        if candidate.get("local_path"):
            return self.collection.upload(file_path=candidate["local_path"], name=name)
        if candidate.get("url"):
            return self.collection.upload(url=candidate["url"], name=name)
        raise VideoDBRuntimeError("Candidate has neither url nor local_path.")

    def _search_lesson_timestamps(
        self,
        video: Any,
        lesson_ids: list[str],
        lesson_queries: dict[str, str | list[str]],
        fallback_query: str,
        max_search_results: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        search_validation = []
        timestamp_searchable = False
        for lesson_id in lesson_ids:
            queries = _query_list(lesson_queries.get(lesson_id), fallback_query or lesson_id)
            results_by_key: dict[tuple[float, float, str], dict[str, Any]] = {}
            search_errors = []
            for query in queries:
                try:
                    results = _normalize_search_result(
                        video.search(query, result_threshold=max_search_results),
                        max_search_results,
                        query=query,
                    )
                except Exception as exc:
                    search_errors.append({"query": query, "error": str(exc)})
                    continue
                for result in results:
                    key = (
                        float(result.get("start") or 0),
                        float(result.get("end") or 0),
                        str(result.get("text") or "")[:160],
                    )
                    results_by_key.setdefault(key, result)
            results = list(results_by_key.values())[:max_search_results]
            if results:
                timestamp_searchable = True
            validation = {
                "lesson_id": lesson_id,
                "queries": queries,
                "query": " | ".join(queries),
                "validation_mode": "videodb_spoken_word_search" if results else "videodb_spoken_word_search_empty",
                "result_count": len(results),
                "results": results,
            }
            if search_errors:
                validation["search_errors"] = search_errors
            search_validation.append(validation)
        return search_validation, timestamp_searchable


def _normalize_transcript(raw_segments: Any, max_segments: int) -> list[dict[str, Any]]:
    segments = []
    for raw in list(raw_segments or [])[:max_segments]:
        start = _number(_field(raw, "start"))
        end = _number(_field(raw, "end"))
        text = str(_field(raw, "text") or "").strip()
        if start is None or end is None or not text:
            continue
        segments.append({
            "start": start,
            "end": end,
            "label": _timestamp_label(start, end),
            "text": text,
        })
    return segments


def _normalize_search_result(search_result: Any, max_results: int, query: str | None = None) -> list[dict[str, Any]]:
    if hasattr(search_result, "get_shots"):
        raw_items = search_result.get_shots()
    elif isinstance(search_result, dict):
        raw_items = search_result.get("shots") or search_result.get("results") or []
    else:
        raw_items = getattr(search_result, "shots", []) or []

    results = []
    for raw in list(raw_items or [])[:max_results]:
        start = _number(_field(raw, "start"))
        end = _number(_field(raw, "end"))
        text = str(_field(raw, "text") or "").strip()
        if start is None or end is None or not text:
            continue
        results.append({
            "video_id": _field(raw, "video_id"),
            "start": start,
            "end": end,
            "label": _timestamp_label(start, end),
            "text": text,
            "score": _number(_field(raw, "score")),
            **({"query": query} if query else {}),
        })
    return results


def _query_list(value: str | list[str] | None, fallback: str) -> list[str]:
    if isinstance(value, list):
        queries = [str(item).strip() for item in value if str(item).strip()]
    elif value:
        queries = [str(value).strip()]
    else:
        queries = []
    if fallback and not queries:
        queries.append(str(fallback).strip())
    return queries


def _field(payload: Any, name: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(name)
    return getattr(payload, name, None)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _timestamp_label(start: float, end: float) -> str:
    return f"{_format_time(start)}-{_format_time(end)}"


def _format_time(seconds: float) -> str:
    seconds_int = max(0, int(seconds))
    minutes, secs = divmod(seconds_int, 60)
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"
