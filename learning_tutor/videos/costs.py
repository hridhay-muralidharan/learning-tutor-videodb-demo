"""Credit-safe VideoDB cost estimation and budget gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT, artifact_path, read_json, read_yaml, write_json


DEFAULT_BUDGET_USD = 10.0
RATE_CARD_PATH = PROJECT_ROOT / "config" / "videodb_rate_card.yaml"
COST_MANIFEST_NAME = "videodb_cost_manifest.json"
DRY_RUN_MODE = "dry_run"


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str


class BudgetGate:
    """Enforce an estimate-plus-actual hard cap for VideoDB operations."""

    def __init__(self, budget_usd: float = DEFAULT_BUDGET_USD):
        self.budget_usd = float(budget_usd)

    def check_estimate(self, estimated_usd: float) -> BudgetDecision:
        if estimated_usd > self.budget_usd:
            return BudgetDecision(
                False,
                f"estimated spend ${estimated_usd:.4f} exceeds budget ${self.budget_usd:.2f}",
            )
        return BudgetDecision(True, "estimate is within budget")

    def check_actual(self, actual_spent_usd: float, next_estimated_usd: float = 0.0) -> BudgetDecision:
        projected = actual_spent_usd + next_estimated_usd
        if projected > self.budget_usd:
            return BudgetDecision(
                False,
                f"actual/projected spend ${projected:.4f} exceeds budget ${self.budget_usd:.2f}",
            )
        return BudgetDecision(True, "actual/projected spend is within budget")


def cost_manifest_path(course: dict[str, Any]) -> Path:
    return artifact_path(course, COST_MANIFEST_NAME)


def load_rate_card() -> dict[str, Any]:
    return read_yaml(RATE_CARD_PATH)


def build_cost_plan(
    course: dict[str, Any],
    index: dict[str, Any],
    lesson_ids: list[str] | None,
    budget_usd: float = DEFAULT_BUDGET_USD,
    mode: str = "estimate",
) -> dict[str, Any]:
    """Build a deterministic no-spend ingest plan from discovered candidates."""

    normalized_lessons = _normalize_lesson_ids(course, lesson_ids)
    budget = float(budget_usd)
    rate_card = load_rate_card()
    requires_scene = bool(course.get("readiness", {}).get("requires_scene_index", False))
    pilot_config = course.get("videodb_pilot", {}) or {}
    required_lesson_count = pilot_config.get("required_lesson_count")
    allowed_lesson_counts = [int(item) for item in pilot_config.get("allowed_lesson_counts", []) if item]
    require_confident_mapping = bool(pilot_config.get("require_confident_mapping", True))

    candidates = index.get("candidates") or []
    existing_videos = index.get("videos") or []
    real_ingested_sources = _real_ingested_source_ids(existing_videos)
    operations: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    allowed_counts = set(allowed_lesson_counts)
    if required_lesson_count:
        allowed_counts.add(int(required_lesson_count))
    if allowed_counts and len(normalized_lessons) not in allowed_counts:
        blocked_reasons.append(
            f"VideoDB ingest requires one of {sorted(allowed_counts)} lessons; received {len(normalized_lessons)}"
        )

    covered_lessons: set[str] = set()
    for candidate in candidates:
        if candidate.get("ingest_candidate") is False:
            continue
        source_id = str(candidate.get("source_id") or "")
        candidate_lessons = [str(item) for item in candidate.get("lesson_ids", []) if item]
        relevant_lessons = [item for item in candidate_lessons if item in normalized_lessons]
        if not relevant_lessons:
            continue

        if source_id in real_ingested_sources or _has_real_video_id(candidate):
            skipped.append(_candidate_status(candidate, "skipped", relevant_lessons, "already ingested"))
            covered_lessons.update(relevant_lessons)
            continue

        status = str(candidate.get("status") or "")
        ambiguous_mapping = require_confident_mapping and (
            status == "candidate_review_required"
            or not candidate_lessons
            or any(item not in normalized_lessons for item in candidate_lessons)
        )
        if ambiguous_mapping:
            blocked_reasons.append(
                f"{source_id or 'unknown'} cannot be confidently mapped only to requested lessons"
            )
            planned.append(_candidate_status(candidate, "blocked", relevant_lessons, "manual lesson mapping required"))
            continue

        duration = float(candidate.get("duration_seconds") or 0)
        if duration <= 0:
            blocked_reasons.append(f"{source_id or 'unknown'} is missing duration_seconds for cost estimate")
            planned.append(_candidate_status(candidate, "blocked", relevant_lessons, "missing duration"))
            continue

        estimate = estimate_candidate_cost(candidate, rate_card, requires_scene)
        operations.append(estimate)
        planned.append(_candidate_status(candidate, "planned", relevant_lessons, None, estimate))
        covered_lessons.update(relevant_lessons)

    for lesson_id in normalized_lessons:
        if lesson_id not in covered_lessons:
            blocked_reasons.append(f"{lesson_id}: no planned or already-ingested video candidate")

    total = round(sum(item["estimated_total_usd"] for item in operations), 4)
    budget_decision = BudgetGate(budget).check_estimate(total)
    if not budget_decision.allowed:
        blocked_reasons.append(budget_decision.reason)

    status = "blocked" if blocked_reasons else ("dry_run_ready" if mode == DRY_RUN_MODE else "estimate_ready")
    plan = {
        "manifest_version": 1,
        "mode": mode,
        "course_slug": course.get("_slug"),
        "course_path": course.get("_path"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "budget_usd": budget,
        "lesson_ids": normalized_lessons,
        "required_lesson_count": required_lesson_count,
        "allowed_lesson_counts": sorted(allowed_counts),
        "requires_scene_index": requires_scene,
        "scene_index_policy": "enabled" if requires_scene else "not_required",
        "rate_card_version": rate_card.get("version"),
        "estimated_total_usd": total,
        "status": status,
        "would_spend_credits": bool(operations),
        "credit_consuming_sources": [
            {
                "source_id": item["source_id"],
                "title": item.get("title"),
                "url": item.get("url"),
                "lesson_ids": item.get("lesson_ids", []),
                "estimated_total_usd": item["estimated_total_usd"],
            }
            for item in operations
        ],
        "operations": operations,
        "planned": planned,
        "skipped": skipped,
        "blocked_reasons": sorted(set(blocked_reasons)),
    }
    plan["request_signature"] = _plan_signature(plan, candidates)
    return plan


def write_cost_manifest(course: dict[str, Any], plan: dict[str, Any]) -> Path:
    return write_json(cost_manifest_path(course), plan)


def load_cost_manifest(course: dict[str, Any]) -> dict[str, Any] | None:
    path = cost_manifest_path(course)
    if not path.exists():
        return None
    return read_json(path)


def update_index_with_plan(index: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    index["cost_estimate"] = {
        "status": plan.get("status"),
        "mode": plan.get("mode"),
        "budget_usd": plan.get("budget_usd"),
        "estimated_total_usd": plan.get("estimated_total_usd"),
        "lesson_ids": plan.get("lesson_ids", []),
        "rate_card_version": plan.get("rate_card_version"),
        "blocked_reasons": plan.get("blocked_reasons", []),
        "manifest": f"artifacts/{COST_MANIFEST_NAME}",
    }
    index["ingest_plan"] = {
        "status": plan.get("status"),
        "lesson_ids": plan.get("lesson_ids", []),
        "credit_consuming_sources": plan.get("credit_consuming_sources", []),
        "planned": plan.get("planned", []),
        "skipped": plan.get("skipped", []),
        "requires_confirm": True,
        "dry_run_required": True,
    }
    return index


def validate_dry_run_manifest(
    course: dict[str, Any],
    index: dict[str, Any],
    lesson_ids: list[str] | None,
    budget_usd: float,
) -> tuple[dict[str, Any] | None, list[str]]:
    manifest = load_cost_manifest(course)
    if manifest is None:
        return None, ["missing dry-run manifest; run videos dry-run before ingest"]
    if manifest.get("mode") != DRY_RUN_MODE or manifest.get("status") != "dry_run_ready":
        return manifest, ["latest cost manifest is not a successful dry-run"]

    expected = build_cost_plan(course, index, lesson_ids, budget_usd, mode=DRY_RUN_MODE)
    errors: list[str] = []
    if manifest.get("request_signature") != expected.get("request_signature"):
        errors.append("dry-run manifest is stale for the requested lessons, budget, or candidates")
    if float(manifest.get("estimated_total_usd") or 0) > float(budget_usd):
        errors.append("dry-run estimate exceeds requested ingest budget")
    return manifest, errors


def usage_delta(before: dict[str, Any] | None, after: dict[str, Any] | None) -> float | None:
    if not before or not after:
        return None
    before_used = _usage_number(before, "credit_used")
    after_used = _usage_number(after, "credit_used")
    if before_used is not None and after_used is not None:
        return round(after_used - before_used, 4)

    before_balance = _usage_number(before, "credit_balance", "credit_remaining")
    after_balance = _usage_number(after, "credit_balance", "credit_remaining")
    if before_balance is not None and after_balance is not None:
        return round(before_balance - after_balance, 4)
    return None


def record_credit_snapshot(course: dict[str, Any], before: dict[str, Any] | None, after: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = load_cost_manifest(course) or {}
    manifest["credit_before"] = sanitize_usage_snapshot(before)
    if after is not None:
        manifest["credit_after"] = sanitize_usage_snapshot(after)
        manifest["actual_cost_delta"] = usage_delta(manifest["credit_before"], manifest["credit_after"])
    write_cost_manifest(course, manifest)
    return manifest


def sanitize_usage_snapshot(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    allowed_keys = {
        "agentic_stream_run",
        "cost_metric",
        "credit_balance",
        "credit_used",
        "dubbing",
        "file_upload",
        "generate_audio_url",
        "generate_image_url",
        "image_generation",
        "indexing_bundle_basic",
        "indexing_bundle_pro",
        "indexing_bundle_ultra",
        "llm",
        "llm_basic",
        "llm_custom",
        "llm_pro",
        "llm_ultra",
        "media_storage",
        "meeting_recording",
        "music_generation",
        "programmable_stream",
        "rtstream_compute",
        "rtstream_storage",
        "sandbox_medium",
        "sandbox_small",
        "scene",
        "scene_index",
        "search_query",
        "search_v2_aggregate",
        "search_v2_query",
        "search_v2_semantic",
        "simple_stream",
        "spoken_index",
        "spoken_index_storage",
        "streaming",
        "transcoding",
        "transcription",
        "translation",
        "video_generation",
        "voice_generation",
        "youtube_search",
    }
    return {key: value for key, value in payload.items() if key in allowed_keys}


def estimate_candidate_cost(candidate: dict[str, Any], rate_card: dict[str, Any], requires_scene: bool) -> dict[str, Any]:
    duration_seconds = float(candidate.get("duration_seconds") or 0)
    duration_minutes = duration_seconds / 60
    size_gb = _candidate_size_gb(candidate, rate_card, duration_seconds)
    search_queries = int(candidate.get("estimated_search_queries") or rate_card.get("learning_tutor_estimation", {}).get("default_search_queries_per_video", 3))

    upload_cost = size_gb * float(rate_card["ingest"]["file_upload_per_gb"])
    transcription_cost = duration_minutes * float(rate_card["indexing"]["transcription_per_min"])
    search_cost = (search_queries / 1000) * float(rate_card["indexing"]["search_query_per_1k"])
    media_storage_cost = size_gb * float(rate_card["storage"]["media_per_gb_month"])
    index_storage_cost = duration_minutes * float(rate_card["storage"]["index_per_min_month"])
    scene_cost = 0.0
    if requires_scene:
        estimated_scenes = int(candidate.get("estimated_scene_count") or 0)
        scene_cost = estimated_scenes * float(rate_card["indexing"]["scene_processing_per_scene"])

    costs = {
        "upload_usd": round(upload_cost, 4),
        "transcription_usd": round(transcription_cost, 4),
        "scene_index_usd": round(scene_cost, 4),
        "search_validation_usd": round(search_cost, 4),
        "first_month_storage_usd": round(media_storage_cost + index_storage_cost, 4),
    }
    return {
        "source_id": candidate.get("source_id"),
        "title": candidate.get("title"),
        "url": candidate.get("url"),
        "lesson_ids": candidate.get("lesson_ids", []),
        "duration_seconds": duration_seconds,
        "estimated_size_gb": round(size_gb, 4),
        "estimated_search_queries": search_queries,
        "costs": costs,
        "estimated_total_usd": round(sum(costs.values()), 4),
        "status": "planned",
    }


def _normalize_lesson_ids(course: dict[str, Any], lesson_ids: list[str] | None) -> list[str]:
    if lesson_ids:
        return [item.strip() for item in lesson_ids if item and item.strip()]
    pilot_config = course.get("videodb_pilot", {}) or {}
    configured = pilot_config.get("recommended_lessons") or []
    return [str(item) for item in configured if item]


def _candidate_status(
    candidate: dict[str, Any],
    status: str,
    lesson_ids: list[str],
    reason: str | None,
    estimate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "source_id": candidate.get("source_id"),
        "title": candidate.get("title"),
        "url": candidate.get("url"),
        "lesson_ids": lesson_ids,
        "ingest_status": status,
    }
    if reason:
        payload["reason"] = reason
    if estimate:
        payload["estimated_total_usd"] = estimate.get("estimated_total_usd")
    return payload


def _candidate_size_gb(candidate: dict[str, Any], rate_card: dict[str, Any], duration_seconds: float) -> float:
    explicit = candidate.get("file_size_gb") or candidate.get("size_gb")
    if explicit:
        return float(explicit)
    gb_per_hour = float(rate_card.get("learning_tutor_estimation", {}).get("remote_video_gb_per_hour", 1.5))
    return (duration_seconds / 3600) * gb_per_hour


def _real_ingested_source_ids(videos: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("source_id")) for item in videos if _has_real_video_id(item)}


def _has_real_video_id(item: dict[str, Any]) -> bool:
    video_id = str(item.get("video_id") or "")
    return bool(video_id and not video_id.startswith("bundled_"))


def _plan_signature(plan: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    import json

    payload = {
        "budget_usd": plan.get("budget_usd"),
        "lesson_ids": plan.get("lesson_ids", []),
        "estimated_total_usd": plan.get("estimated_total_usd"),
        "operations": [
            {
                "source_id": item.get("source_id"),
                "duration_seconds": item.get("duration_seconds"),
                "lesson_ids": item.get("lesson_ids", []),
                "estimated_total_usd": item.get("estimated_total_usd"),
            }
            for item in plan.get("operations", [])
        ],
        "candidates": [
            {
                "source_id": item.get("source_id"),
                "url": item.get("url"),
                "duration_seconds": item.get("duration_seconds"),
                "lesson_ids": item.get("lesson_ids", []),
                "status": item.get("status"),
                "video_id": item.get("video_id"),
                "ingest_candidate": item.get("ingest_candidate", True),
            }
            for item in candidates
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _usage_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return float(value)
    return None
