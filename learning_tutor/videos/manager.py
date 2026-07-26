"""Generic VideoDB lifecycle gates for course app generation."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import artifact_path, course_path, load_course, read_json, videodb_api_key, write_json
from .costs import (
    DEFAULT_BUDGET_USD,
    DRY_RUN_MODE,
    BudgetGate,
    build_cost_plan,
    cost_manifest_path,
    record_credit_snapshot,
    sanitize_usage_snapshot,
    update_index_with_plan,
    usage_delta,
    validate_dry_run_manifest,
    write_cost_manifest,
)
from .runtime import VideoDBRuntime


def validate_videos(course_arg: str | Path) -> tuple[list[str], list[str]]:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "video_sources.json"), default=[])
    errors: list[str] = []
    warnings: list[str] = []
    if not sources:
        errors.append("video_sources.json has no sources")
    for source in sources:
        source_id = source.get("id", "unknown")
        if source.get("type") == "playlist" and not source.get("url"):
            errors.append(f"{source_id}: playlist source missing url")
        if source.get("type") == "video" and not source.get("url") and not source.get("local_path"):
            errors.append(f"{source_id}: video source needs url or local_path")
        if not source.get("citation_label"):
            errors.append(f"{source_id}: missing citation_label")
        if source.get("requires_videodb", True) is False:
            warnings.append(f"{source_id}: requires_videodb is false; regenerated lesson plans will still require VideoDB evidence")
    return errors, warnings


def discover_videos(course_arg: str | Path, limit: int = 50) -> dict[str, Any]:
    course = load_course(course_arg)
    sources = read_json(course_path(course, "video_sources.json"), default=[])
    existing = read_json(artifact_path(course, "video_index.json"), default={})
    discovered = []
    ytdlp = shutil.which("yt-dlp")

    for source in sources:
        if source.get("type") == "playlist" and ytdlp:
            discovered.extend(_discover_playlist(source, limit))
        else:
            discovered.append({
                "source_id": source.get("id"),
                "kind": source.get("type", "video"),
                "title": source.get("title"),
                "url": source.get("url"),
                "module": source.get("module"),
                "lesson_ids": source.get("lesson_ids", []),
                "status": "candidate_review_required" if source.get("type") == "playlist" else "ready_for_ingest",
                "citation_label": source.get("citation_label"),
                "duration_seconds": source.get("duration_seconds"),
                "ingest_candidate": source.get("ingest_candidate", True),
                "requires_scene_index": source.get("requires_scene_index"),
            })

    index = {
        **existing,
        "source_count": len(sources),
        "discovered_count": len(discovered),
        "discovery_status": "ready" if discovered else "incomplete",
        "candidates": discovered,
        "credit_control": "discover never uploads and never spends VideoDB credits",
    }
    if "videos" not in index:
        index["videos"] = existing.get("videos", [])
    write_json(artifact_path(course, "video_index.json"), index)
    return index


def estimate_videos(
    course_arg: str | Path,
    lesson_ids: list[str] | None = None,
    budget_usd: float = DEFAULT_BUDGET_USD,
) -> dict[str, Any]:
    course = load_course(course_arg)
    index = read_json(artifact_path(course, "video_index.json"), default={"videos": [], "candidates": []})
    plan = build_cost_plan(course, index, lesson_ids, budget_usd, mode="estimate")
    write_cost_manifest(course, plan)
    write_json(artifact_path(course, "video_index.json"), update_index_with_plan(index, plan))
    return plan


def dry_run_videos(
    course_arg: str | Path,
    lesson_ids: list[str] | None = None,
    budget_usd: float = DEFAULT_BUDGET_USD,
) -> dict[str, Any]:
    course = load_course(course_arg)
    index = read_json(artifact_path(course, "video_index.json"), default={"videos": [], "candidates": []})
    plan = build_cost_plan(course, index, lesson_ids, budget_usd, mode=DRY_RUN_MODE)
    write_cost_manifest(course, plan)
    write_json(artifact_path(course, "video_index.json"), update_index_with_plan(index, plan))
    return plan


def ingest_videos(
    course_arg: str | Path,
    confirm: bool = False,
    lesson_ids: list[str] | None = None,
    budget_usd: float = DEFAULT_BUDGET_USD,
) -> dict[str, Any]:
    course = load_course(course_arg)
    if not confirm:
        return {
            "status": "refused",
            "error": "videos ingest spends VideoDB credits and requires --confirm",
        }
    index = read_json(artifact_path(course, "video_index.json"), default={"videos": [], "candidates": []})
    manifest, manifest_errors = validate_dry_run_manifest(course, index, lesson_ids, budget_usd)
    if manifest_errors:
        return {
            "status": "blocked",
            "error": "; ".join(manifest_errors),
            "dry_run_required": True,
        }
    estimate_total = float((manifest or {}).get("estimated_total_usd") or 0)
    budget_decision = BudgetGate(budget_usd).check_estimate(estimate_total)
    if not budget_decision.allowed:
        return {
            "status": "blocked",
            "error": budget_decision.reason,
            "estimated_total_usd": estimate_total,
            "budget_usd": float(budget_usd),
        }

    candidates = index.get("candidates") or []
    requested_lessons = set((manifest or {}).get("lesson_ids", []))
    planned_source_ids = {item.get("source_id") for item in (manifest or {}).get("credit_consuming_sources", [])}
    existing_by_source = _real_ingested_by_source(index.get("videos") or [])
    pending = [
        item for item in candidates
        if item.get("source_id") in planned_source_ids and item.get("source_id") not in existing_by_source
    ]
    skipped = [
        item for item in candidates
        if item.get("source_id") in planned_source_ids and item.get("source_id") in existing_by_source
    ]
    if not pending:
        return {
            "status": "completed",
            "message": "No paid VideoDB operations needed; all planned sources already have real video IDs.",
            "budget_usd": float(budget_usd),
            "estimated_total_usd": estimate_total,
            "videos_to_ingest": 0,
            "already_ingested": len(skipped),
            "skipped": [item.get("source_id") for item in skipped],
        }

    api_key = videodb_api_key()
    if not api_key:
        return {
            "status": "blocked",
            "error": "VIDEODB_API_KEY or VIDEO_DB_API_KEY is required before VideoDB ingestion.",
        }
    try:
        import videodb  # noqa: F401
    except Exception:
        return {
            "status": "blocked",
            "error": "videodb SDK is not installed. Install it before running ingestion.",
        }

    try:
        runtime = VideoDBRuntime(api_key=api_key, collection_id=_videodb_collection_id(course))
        credit_before = sanitize_usage_snapshot(runtime.check_usage())
    except Exception as exc:
        return {
            "status": "blocked",
            "error": f"VideoDB check_usage() snapshot failed; refusing paid ingest without before/after credit tracking. {exc}",
        }

    manifest = record_credit_snapshot(course, credit_before)
    usage_snapshots = [{
        "stage": "before_ingest",
            "usage": credit_before,
    }]
    manifest["usage_snapshots"] = usage_snapshots
    manifest["ingest_status"] = "running"
    write_cost_manifest(course, manifest)

    operations_by_source = {item.get("source_id"): item for item in (manifest or {}).get("operations", [])}
    lesson_queries = _lesson_queries(course, requested_lessons)
    ingested: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    last_usage = credit_before

    for candidate in pending:
        source_id = candidate.get("source_id")
        estimate_next = float((operations_by_source.get(source_id) or {}).get("estimated_total_usd") or 0)
        actual_so_far = usage_delta(credit_before, last_usage)
        if actual_so_far is None:
            return _abort_ingest(
                course,
                index,
                manifest,
                failures,
                f"VideoDB usage delta could not be computed before {source_id}; stopping before next paid operation.",
                credit_before,
                last_usage,
            )
        actual_decision = BudgetGate(budget_usd).check_actual(actual_so_far, estimate_next)
        if not actual_decision.allowed:
            return _abort_ingest(course, index, manifest, failures, actual_decision.reason, credit_before, last_usage)

        try:
            video_record = runtime.ingest_candidate(
                candidate,
                lesson_queries=lesson_queries,
                requires_scene_index=bool(course.get("readiness", {}).get("requires_scene_index", False)),
            )
        except Exception as exc:
            failure = _failed_video_record(candidate, str(exc))
            failures.append(failure)
            _upsert_video(index, failure)
            return _abort_ingest(course, index, manifest, failures, f"{source_id}: {exc}", credit_before, last_usage)

        _upsert_video(index, video_record)
        _mark_candidate_ingested(index, source_id, video_record)
        write_json(artifact_path(course, "video_index.json"), index)
        if not video_record.get("timestamp_searchable"):
            failures.append(video_record)
            return _abort_ingest(
                course,
                index,
                manifest,
                failures,
                f"{source_id}: uploaded but timestamp evidence is not ready yet",
                credit_before,
                last_usage,
            )
        ingested.append({
            "source_id": source_id,
            "video_id": video_record.get("video_id"),
            "collection_id": video_record.get("collection_id"),
        })

        try:
            last_usage = sanitize_usage_snapshot(runtime.check_usage())
        except Exception as exc:
            return _abort_ingest(
                course,
                index,
                manifest,
                failures,
                f"VideoDB check_usage() failed after {source_id}; stopping before next paid operation. {exc}",
                credit_before,
                last_usage,
            )
        usage_snapshots.append({
            "stage": f"after_{source_id}",
            "usage": last_usage,
        })
        actual_so_far = usage_delta(credit_before, last_usage)
        manifest["usage_snapshots"] = usage_snapshots
        manifest["credit_after"] = last_usage
        manifest["actual_cost_delta"] = actual_so_far
        write_cost_manifest(course, manifest)

        if actual_so_far is None:
            return _abort_ingest(
                course,
                index,
                manifest,
                failures,
                f"VideoDB usage delta could not be computed after {source_id}; stopping before next paid operation.",
                credit_before,
                last_usage,
            )
        actual_decision = BudgetGate(budget_usd).check_actual(actual_so_far, 0)
        if not actual_decision.allowed:
            return _abort_ingest(course, index, manifest, failures, actual_decision.reason, credit_before, last_usage)

    usage_snapshots.append({
        "stage": "final",
        "usage": last_usage,
    })
    manifest["usage_snapshots"] = usage_snapshots
    manifest["credit_after"] = last_usage
    manifest["actual_cost_delta"] = usage_delta(credit_before, last_usage)
    manifest["ingest_status"] = "completed"
    write_cost_manifest(course, manifest)
    write_json(artifact_path(course, "video_index.json"), index)

    return {
        "status": "completed",
        "budget_usd": float(budget_usd),
        "estimated_total_usd": estimate_total,
        "credit_before": credit_before,
        "credit_after": last_usage,
        "actual_cost_delta": usage_delta(credit_before, last_usage),
        "videos_to_ingest": len(pending),
        "ingested": ingested,
        "already_ingested": len(skipped),
        "skipped": [item.get("source_id") for item in skipped],
        "credit_consuming_sources": (manifest or {}).get("credit_consuming_sources", []),
    }


def refresh_video_searches(
    course_arg: str | Path,
    confirm: bool = False,
    lesson_ids: list[str] | None = None,
    budget_usd: float = DEFAULT_BUDGET_USD,
) -> dict[str, Any]:
    course = load_course(course_arg)
    if not confirm:
        return {
            "status": "refused",
            "error": "videos refresh-search uses live VideoDB search and requires --confirm",
        }
    api_key = videodb_api_key()
    if not api_key:
        return {
            "status": "blocked",
            "error": "VIDEODB_API_KEY or VIDEO_DB_API_KEY is required before VideoDB search refresh.",
        }
    index = read_json(artifact_path(course, "video_index.json"), default={"videos": []})
    requested_lessons = set(lesson_ids or _all_lesson_ids(course))
    videos = [
        video for video in index.get("videos", [])
        if _has_real_video_id(video)
        and set(video.get("lesson_ids", [])) & requested_lessons
        and video.get("upload_status") == "uploaded"
        and video.get("spoken_word_index_status") == "ready"
    ]
    if not videos:
        return {
            "status": "completed",
            "message": "No uploaded VideoDB videos matched the requested lessons.",
            "refreshed": [],
        }

    try:
        runtime = VideoDBRuntime(api_key=api_key, collection_id=_videodb_collection_id(course))
        credit_before = sanitize_usage_snapshot(runtime.check_usage())
    except Exception as exc:
        return {
            "status": "blocked",
            "error": f"VideoDB check_usage() snapshot failed; refusing live search without before/after credit tracking. {exc}",
        }

    manifest = read_json(cost_manifest_path(course), default={})
    manifest["search_refresh_status"] = "running"
    manifest["search_refresh_started_at"] = datetime.now(timezone.utc).isoformat()
    manifest["search_refresh_credit_before"] = credit_before
    write_cost_manifest(course, manifest)

    refreshed = []
    failed = []
    last_usage = credit_before
    lesson_queries = _lesson_queries(course, requested_lessons)
    for video in videos:
        source_id = video.get("source_id")
        try:
            updated = runtime.refresh_search_validation(video, lesson_queries=lesson_queries)
        except Exception as exc:
            failed.append({"source_id": source_id, "error": str(exc)})
            break
        _upsert_video(index, updated)
        refreshed.append({
            "source_id": source_id,
            "video_id": updated.get("video_id"),
            "lesson_ids": updated.get("lesson_ids", []),
            "timestamp_searchable": updated.get("timestamp_searchable"),
            "result_count": sum((item.get("result_count") or 0) for item in updated.get("search_validation", [])),
        })
        write_json(artifact_path(course, "video_index.json"), index)
        try:
            last_usage = sanitize_usage_snapshot(runtime.check_usage())
        except Exception as exc:
            failed.append({"source_id": source_id, "error": f"check_usage failed after refresh: {exc}"})
            break
        actual_so_far = usage_delta(credit_before, last_usage)
        if actual_so_far is not None and not BudgetGate(budget_usd).check_actual(actual_so_far, 0).allowed:
            failed.append({"source_id": source_id, "error": "VideoDB search refresh crossed the configured budget."})
            break

    manifest["search_refresh_credit_after"] = last_usage
    manifest["search_refresh_actual_cost_delta"] = usage_delta(credit_before, last_usage)
    manifest["search_refresh_refreshed"] = refreshed
    manifest["search_refresh_failed"] = failed
    manifest["search_refresh_status"] = "blocked" if failed else "completed"
    write_cost_manifest(course, manifest)
    write_json(artifact_path(course, "video_index.json"), index)

    return {
        "status": "blocked" if failed else "completed",
        "budget_usd": float(budget_usd),
        "credit_before": credit_before,
        "credit_after": last_usage,
        "actual_cost_delta": usage_delta(credit_before, last_usage),
        "refreshed": refreshed,
        "failed": failed,
    }


def verify_videos(course_arg: str | Path) -> tuple[list[str], list[str], dict[str, Any]]:
    course = load_course(course_arg)
    index = read_json(artifact_path(course, "video_index.json"), default={})
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    errors: list[str] = []
    warnings: list[str] = []
    videos = index.get("videos", [])
    by_lesson = {}
    for video in videos:
        for lesson_id in video.get("lesson_ids", []):
            by_lesson.setdefault(lesson_id, []).append(video)

    requires_scene = bool(course.get("readiness", {}).get("requires_scene_index", False))
    for lesson in lesson_map.get("lessons", []):
        lesson_id = lesson.get("id")
        lesson_videos = by_lesson.get(lesson_id, [])
        if not lesson_videos:
            errors.append(f"{lesson_id}: no video mapped to lesson")
            continue
        ready_videos = [video for video in lesson_videos if _is_video_ready(video, requires_scene, lesson_id)]
        if ready_videos:
            for video in lesson_videos:
                if not _is_video_ready(video, requires_scene, lesson_id):
                    source_id = video.get("source_id") or "unknown"
                    warnings.append(f"{lesson_id}/{source_id}: retained non-ready video record is not used as ready evidence")
                if not video.get("citation_label"):
                    source_id = video.get("source_id") or "unknown"
                    warnings.append(f"{lesson_id}/{source_id}: missing citation label")
            continue
        for video in lesson_videos:
            _check_video_ready(video, lesson_id, requires_scene, errors, warnings)

    report = {
        "status": "ready" if not errors else "incomplete",
        "lesson_count": len(lesson_map.get("lessons", [])),
        "video_count": len(videos),
        "requires_scene_index": requires_scene,
    }
    return errors, warnings, report


def _is_video_ready(video: dict, requires_scene: bool, lesson_id: str | None = None) -> bool:
    transcript = video.get("transcript_cache") or {}
    has_scene = not requires_scene or video.get("scene_index_status") == "ready"
    return bool(
        video.get("source_id")
        and video.get("video_id")
        and video.get("collection_id")
        and video.get("upload_status") == "uploaded"
        and video.get("spoken_word_index_status") == "ready"
        and transcript.get("segments")
        and video.get("timestamp_searchable")
        and has_scene
        and _has_videodb_search_result(video, lesson_id)
    )


def _check_video_ready(video: dict, lesson_id: str, requires_scene: bool, errors: list[str], warnings: list[str]) -> None:
    source_id = video.get("source_id") or "unknown"
    for key in ("source_id", "video_id", "collection_id", "upload_status"):
        if not video.get(key):
            errors.append(f"{lesson_id}/{source_id}: missing {key}")
    if video.get("spoken_word_index_status") != "ready":
        errors.append(f"{lesson_id}/{source_id}: spoken-word index is not ready")
    transcript = video.get("transcript_cache") or {}
    if not transcript.get("segments"):
        errors.append(f"{lesson_id}/{source_id}: transcript cache has no segments")
    if not video.get("timestamp_searchable"):
        errors.append(f"{lesson_id}/{source_id}: timestamp-searchable evidence missing")
    if not _has_videodb_search_result(video, lesson_id):
        errors.append(f"{lesson_id}/{source_id}: VideoDB spoken-word search has no timestamped result for this lesson")
    if requires_scene and video.get("scene_index_status") != "ready":
        errors.append(f"{lesson_id}/{source_id}: scene index required but not ready")
    if not video.get("citation_label"):
        warnings.append(f"{lesson_id}/{source_id}: missing citation label")


def _has_real_video_id(item: dict) -> bool:
    video_id = str(item.get("video_id") or "")
    return bool(video_id and not video_id.startswith("bundled_"))


def _has_videodb_search_result(video: dict, lesson_id: str | None = None) -> bool:
    for validation in video.get("search_validation", []) or []:
        if lesson_id and validation.get("lesson_id") != lesson_id:
            continue
        if validation.get("validation_mode") != "videodb_spoken_word_search":
            continue
        for result in validation.get("results") or []:
            if result.get("start") is not None and result.get("end") is not None and str(result.get("text") or "").strip():
                return True
    return False


def _real_ingested_by_source(videos: list[dict]) -> dict[str, dict]:
    return {str(item.get("source_id")): item for item in videos if item.get("source_id") and _has_real_video_id(item)}


def _videodb_collection_id(course: dict[str, Any]) -> str:
    pilot = course.get("videodb_pilot", {}) or {}
    return str(pilot.get("collection_id") or course.get("videodb_collection_id") or "default")


def _lesson_queries(course: dict[str, Any], lesson_ids: set[str]) -> dict[str, str | list[str]]:
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    queries = {}
    for lesson in lesson_map.get("lessons", []):
        lesson_id = lesson.get("id")
        if lesson_id not in lesson_ids:
            continue
        configured_queries = lesson.get("video_search_queries") or []
        if configured_queries:
            queries[lesson_id] = [str(item).strip() for item in configured_queries if str(item).strip()]
            continue
        parts = [lesson.get("title"), lesson.get("syllabus_anchor")]
        queries[lesson_id] = [" ".join(str(item) for item in parts if item).strip() or str(lesson_id)]
    return queries


def _all_lesson_ids(course: dict[str, Any]) -> list[str]:
    lesson_map = read_json(course_path(course, "lesson_map.json"), default={"lessons": []})
    return [str(lesson.get("id")) for lesson in lesson_map.get("lessons", []) if lesson.get("id")]


def _upsert_video(index: dict[str, Any], video_record: dict[str, Any]) -> None:
    videos = index.setdefault("videos", [])
    source_id = video_record.get("source_id")
    for idx, existing in enumerate(videos):
        if existing.get("source_id") == source_id:
            videos[idx] = video_record
            return
    videos.append(video_record)


def _mark_candidate_ingested(index: dict[str, Any], source_id: str | None, video_record: dict[str, Any]) -> None:
    if not source_id:
        return
    for candidate in index.get("candidates", []):
        if candidate.get("source_id") == source_id:
            candidate["status"] = "ingested" if video_record.get("timestamp_searchable") else "needs_processing"
            candidate["video_id"] = video_record.get("video_id")
            candidate["collection_id"] = video_record.get("collection_id")


def _failed_video_record(candidate: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "source_id": candidate.get("source_id"),
        "title": candidate.get("title"),
        "url": candidate.get("url"),
        "provider": candidate.get("provider"),
        "module": candidate.get("module"),
        "citation_label": candidate.get("citation_label"),
        "lesson_ids": candidate.get("lesson_ids", []),
        "upload_status": "failed",
        "spoken_word_index_status": "failed",
        "scene_index_status": "not_required",
        "timestamp_searchable": False,
        "transcript_cache": {"segments": []},
        "error": error,
    }


def _abort_ingest(
    course: dict[str, Any],
    index: dict[str, Any],
    manifest: dict[str, Any],
    failures: list[dict[str, Any]],
    error: str,
    credit_before: dict[str, Any],
    credit_after: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest["ingest_status"] = "blocked"
    manifest["ingest_error"] = error
    manifest["failed_sources"] = [item.get("source_id") for item in failures]
    manifest["credit_before"] = credit_before
    if credit_after is not None:
        manifest["credit_after"] = credit_after
        manifest["actual_cost_delta"] = usage_delta(credit_before, credit_after)
    write_cost_manifest(course, manifest)
    write_json(artifact_path(course, "video_index.json"), index)
    return {
        "status": "blocked",
        "error": error,
        "failed_sources": manifest["failed_sources"],
        "credit_before": credit_before,
        "credit_after": credit_after,
        "actual_cost_delta": usage_delta(credit_before, credit_after),
    }


def _discover_playlist(source: dict, limit: int) -> list[dict]:
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--playlist-end",
        str(limit),
        source["url"],
    ]
    completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        return [{
            "source_id": source.get("id"),
            "kind": "playlist",
            "title": source.get("title"),
            "url": source.get("url"),
            "lesson_ids": source.get("lesson_ids", []),
            "status": "discovery_failed",
            "error": completed.stderr.strip(),
            "citation_label": source.get("citation_label"),
            "ingest_candidate": source.get("ingest_candidate", True),
            "requires_scene_index": source.get("requires_scene_index"),
        }]
    import json

    payload = json.loads(completed.stdout)
    entries = []
    for idx, entry in enumerate(payload.get("entries", []), 1):
        video_id = entry.get("id") or entry.get("url")
        entries.append({
            "source_id": f"{source.get('id')}_{idx:03d}",
            "kind": "video",
            "title": entry.get("title"),
            "url": entry.get("webpage_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None),
            "module": source.get("module"),
            "lesson_ids": source.get("lesson_ids", []),
            "status": "candidate_review_required",
            "citation_label": source.get("citation_label"),
            "duration_seconds": entry.get("duration"),
            "ingest_candidate": source.get("ingest_candidate", True),
            "requires_scene_index": source.get("requires_scene_index"),
        })
    return entries
