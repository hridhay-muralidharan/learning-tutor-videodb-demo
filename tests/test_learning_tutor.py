from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from learning_tutor.app.generator import generate_app
from learning_tutor.cli import main
from learning_tutor.config import artifact_path, load_course, write_json
from learning_tutor.course.validate import validate_course
from learning_tutor.planner.assembler import assemble_lesson_plan
from learning_tutor.questions.indexer import index_questions
from learning_tutor.textbooks.indexer import index_textbooks
from learning_tutor.videos.costs import BudgetGate, cost_manifest_path
from learning_tutor.videos.manager import dry_run_videos, estimate_videos, ingest_videos, verify_videos


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_COURSE = PROJECT_ROOT / "courses" / "gate_organic_chemistry"


class LearningTutorCourseTests(unittest.TestCase):
    def test_demo_course_validates(self) -> None:
        errors, warnings = validate_course(DEMO_COURSE)
        self.assertEqual(errors, [])
        self.assertIsInstance(warnings, list)

    def test_video_verification_passes_for_demo_artifacts(self) -> None:
        errors, warnings, report = verify_videos(DEMO_COURSE)
        self.assertEqual(errors, [])
        self.assertIsInstance(warnings, list)
        self.assertEqual(report["status"], "ready")

    def test_ingest_without_confirm_refuses(self) -> None:
        result = ingest_videos(DEMO_COURSE, confirm=False)
        self.assertEqual(result["status"], "refused")
        self.assertIn("--confirm", result["error"])

    def test_ingest_without_dry_run_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            manifest = cost_manifest_path(load_course(course))
            if manifest.exists():
                manifest.unlink()

            result = ingest_videos(course, confirm=True)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("dry-run", result["error"])

    def test_estimate_over_budget_blocks_ingest_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir), duration_seconds=7200)

            result = estimate_videos(course, budget_usd=0.01)

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any("exceeds budget" in item for item in result["blocked_reasons"]))

    def test_actual_cost_over_budget_aborts_next_operation(self) -> None:
        decision = BudgetGate(10).check_actual(actual_spent_usd=9.95, next_estimated_usd=0.10)

        self.assertFalse(decision.allowed)
        self.assertIn("exceeds budget", decision.reason)

    def test_already_ingested_videos_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir), already_ingested=True)

            result = estimate_videos(course)

            self.assertEqual(result["status"], "estimate_ready")
            self.assertEqual(result["estimated_total_usd"], 0)
            self.assertEqual(result["skipped"][0]["ingest_status"], "skipped")

    def test_missing_videodb_key_blocks_paid_path_after_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir))
            dry_run_videos(course)

            with patch("learning_tutor.videos.manager.videodb_api_key", return_value=None):
                result = ingest_videos(course, confirm=True)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("VIDEODB_API_KEY", result["error"])

    def test_missing_sdk_blocks_paid_path_after_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir))
            dry_run_videos(course)

            real_import = __import__

            def guarded_import(name, *args, **kwargs):
                if name == "videodb":
                    raise ImportError("no sdk")
                return real_import(name, *args, **kwargs)

            with patch("learning_tutor.videos.manager.videodb_api_key", return_value="fake"):
                with patch("builtins.__import__", side_effect=guarded_import):
                    result = ingest_videos(course, confirm=True)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("SDK", result["error"])

    def test_confirmed_ingest_records_real_videodb_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            self._reset_pilot_ingest_state(course)
            dry_run_videos(course, lesson_ids=["stereochemistry", "reaction_mechanisms", "organic_synthesis"])
            runtime = FakeVideoDBRuntime()

            with patch("learning_tutor.videos.manager.videodb_api_key", return_value="fake"):
                with patch("learning_tutor.videos.manager.VideoDBRuntime", return_value=runtime):
                    result = ingest_videos(
                        course,
                        confirm=True,
                        lesson_ids=["stereochemistry", "reaction_mechanisms", "organic_synthesis"],
                        budget_usd=10,
                    )

            course_data = load_course(course)
            index = __import__("json").loads(artifact_path(course_data, "video_index.json").read_text(encoding="utf-8"))
            plan = assemble_lesson_plan(course, require_video_ready=False)
            source_states = {
                lesson["id"]: lesson["readiness"]["source_states"]["video"]["state"]
                for lesson in plan["lessons"]
            }

            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["ingested"]), 3)
            self.assertEqual(result["actual_cost_delta"], 3)
            self.assertEqual(len([item for item in index["videos"] if str(item.get("video_id", "")).startswith("vdb_real_")]), 3)
            self.assertEqual(source_states["stereochemistry"], "source_backed")
            self.assertEqual(source_states["reaction_mechanisms"], "source_backed")
            self.assertEqual(source_states["organic_synthesis"], "source_backed")
            self.assertEqual(source_states["heterocycles"], "needs_processing")

    def test_failed_videodb_operation_records_failure_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_three_confident_candidates(Path(tmpdir))
            dry_run_videos(course)
            runtime = FakeVideoDBRuntime(fail_on_source="pilot_video_1")

            with patch("learning_tutor.videos.manager.videodb_api_key", return_value="fake"):
                with patch("learning_tutor.videos.manager.VideoDBRuntime", return_value=runtime):
                    result = ingest_videos(course, confirm=True)

            index = __import__("json").loads(artifact_path(load_course(course), "video_index.json").read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failed_sources"], ["pilot_video_1"])
            self.assertEqual(index["videos"][0]["upload_status"], "failed")
            self.assertEqual(len(index["videos"]), 1)

    def test_actual_spend_over_budget_aborts_before_next_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_three_confident_candidates(Path(tmpdir))
            dry_run_videos(course, budget_usd=10)
            runtime = FakeVideoDBRuntime(usage_values=[0, 9.95, 9.95, 9.95])

            with patch("learning_tutor.videos.manager.videodb_api_key", return_value="fake"):
                with patch("learning_tutor.videos.manager.VideoDBRuntime", return_value=runtime):
                    result = ingest_videos(course, confirm=True, budget_usd=10)

            index = __import__("json").loads(artifact_path(load_course(course), "video_index.json").read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "blocked")
            self.assertIn("exceeds budget", result["error"])
            self.assertEqual(len(index["videos"]), 1)

    def test_empty_transcript_real_video_is_not_source_backed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            course_data = load_course(course)
            lesson_id = course_data["videodb_pilot"]["recommended_lessons"][0]
            write_json(artifact_path(course_data, "video_index.json"), {
                "videos": [{
                    "source_id": "partial_real_video",
                    "title": "Partial real video",
                    "citation_label": "Processed video source",
                    "video_id": "vdb_real_partial",
                    "collection_id": "collection_real",
                    "upload_status": "uploaded",
                    "spoken_word_index_status": "ready",
                    "scene_index_status": "not_required",
                    "timestamp_searchable": True,
                    "lesson_ids": [lesson_id],
                    "transcript_cache": {"segments": []},
                }],
                "candidates": [],
            })

            payload = assemble_lesson_plan(course, require_video_ready=False)

            state = payload["lessons"][0]["readiness"]["source_states"]["video"]["state"]
            self.assertEqual(state, "needs_processing")

    def test_transcript_fallback_search_is_not_source_backed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            course_data = load_course(course)
            lesson_id = course_data["videodb_pilot"]["recommended_lessons"][0]
            write_json(artifact_path(course_data, "video_index.json"), {
                "videos": [{
                    "source_id": "real_video_with_fallback_only",
                    "title": "Fallback-only real video",
                    "url": "https://www.youtube.com/watch?v=example",
                    "citation_label": "Processed video source",
                    "video_id": "vdb_real_fallback",
                    "collection_id": "collection_real",
                    "upload_status": "uploaded",
                    "spoken_word_index_status": "ready",
                    "scene_index_status": "not_required",
                    "timestamp_searchable": True,
                    "lesson_ids": [lesson_id],
                    "transcript_cache": {"segments": [
                        {"start": 120, "end": 210, "label": "02:00-03:30", "text": "Configuration and stereochemistry teaching example."},
                    ]},
                    "search_validation": [{
                        "lesson_id": lesson_id,
                        "query": "stereochemistry",
                        "validation_mode": "transcript_cache_fallback",
                        "result_count": 1,
                        "results": [{"start": 120, "end": 210, "label": "02:00-03:30", "text": "Configuration and stereochemistry teaching example."}],
                    }],
                }],
                "candidates": [],
            })

            payload = assemble_lesson_plan(course, require_video_ready=False)

            lesson = payload["lessons"][0]
            self.assertEqual(lesson["readiness"]["source_states"]["video"]["state"], "needs_processing")
            self.assertEqual(lesson["video_evidence"][0]["evidence_mode"], "needs_review")

    def test_lesson_plan_skips_useless_intro_video_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            course_data = load_course(course)
            lesson_id = course_data["videodb_pilot"]["recommended_lessons"][0]
            write_json(artifact_path(course_data, "video_index.json"), {
                "videos": [{
                    "source_id": "real_video_with_intro",
                    "title": "Real video with intro",
                    "url": "https://www.youtube.com/watch?v=example",
                    "citation_label": "Processed video source",
                    "video_id": "vdb_real_intro",
                    "collection_id": "collection_real",
                    "upload_status": "uploaded",
                    "spoken_word_index_status": "ready",
                    "scene_index_status": "not_required",
                    "timestamp_searchable": True,
                    "lesson_ids": [lesson_id],
                    "transcript_cache": {"segments": [
                        {"start": 0, "end": 3, "label": "00:00-00:03", "text": "hello and welcome everyone"},
                        {"start": 120, "end": 210, "label": "02:00-03:30", "text": "Now compare chiral molecules, enantiomers, mirror images, and specific rotation using a concrete teaching example."},
                    ]},
                    "search_validation": [{
                        "lesson_id": lesson_id,
                        "query": "stereochemistry",
                        "validation_mode": "videodb_spoken_word_search",
                        "result_count": 1,
                        "results": [
                            {"start": 0, "end": 3, "label": "00:00-00:03", "text": "hello and welcome everyone"},
                            {"start": 120, "end": 210, "label": "02:00-03:30", "text": "Now compare chiral molecules, enantiomers, mirror images, and specific rotation using a concrete teaching example."},
                        ],
                    }],
                }],
                "candidates": [],
            })

            payload = assemble_lesson_plan(course, require_video_ready=False)

            video = payload["lessons"][0]["video_evidence"][0]
            self.assertEqual(video["timestamp_label"], "02:00-03:30")
            self.assertIn("concrete teaching example", video["transcript_preview"])

    def test_cli_estimate_writes_manifest_without_spend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir))

            code = main(["videos", "estimate", "--course", str(course), "--budget", "10"])

            manifest = cost_manifest_path(load_course(course))
            self.assertEqual(code, 0)
            self.assertTrue(manifest.exists())

    def test_curated_three_video_candidates_pass_dry_run_under_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_three_confident_candidates(Path(tmpdir))

            result = dry_run_videos(course, budget_usd=10)

            self.assertEqual(result["status"], "dry_run_ready")
            self.assertLess(result["estimated_total_usd"], 10)
            self.assertEqual(len(result["credit_consuming_sources"]), 3)
            for source in result["credit_consuming_sources"]:
                self.assertEqual(len(source["lesson_ids"]), 1)

    def test_broad_video_candidate_with_extra_lessons_blocks_pilot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir))
            course_data = load_course(course)
            candidate = {
                "source_id": "broad_video_001",
                "kind": "video",
                "title": "Broad video",
                "url": "https://example.edu/video/broad",
                "lesson_ids": ["stereochemistry", "heterocycles"],
                "status": "ready_for_ingest",
                "citation_label": "Approved video source",
                "duration_seconds": 1200,
            }
            write_json(artifact_path(course_data, "video_index.json"), {"videos": [], "candidates": [candidate]})

            result = dry_run_videos(course)

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any("cannot be confidently mapped" in item for item in result["blocked_reasons"]))

    def test_reference_playlist_is_ignored_by_paid_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_three_confident_candidates(Path(tmpdir))
            course_data = load_course(course)
            index = __import__("json").loads(artifact_path(course_data, "video_index.json").read_text(encoding="utf-8"))
            index["candidates"].insert(0, {
                "source_id": "reference_playlist",
                "kind": "playlist",
                "title": "Reference playlist",
                "url": "https://example.edu/playlist",
                "lesson_ids": ["stereochemistry", "reaction_mechanisms", "organic_synthesis", "heterocycles"],
                "status": "candidate_review_required",
                "citation_label": "Reference playlist",
                "ingest_candidate": False,
            })
            write_json(artifact_path(course_data, "video_index.json"), index)

            result = dry_run_videos(course)

            self.assertEqual(result["status"], "dry_run_ready")
            self.assertEqual(len(result["credit_consuming_sources"]), 3)
            self.assertNotIn("reference_playlist", {item["source_id"] for item in result["credit_consuming_sources"]})

    def test_missing_duration_blocks_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_confident_candidate(Path(tmpdir), duration_seconds=0)

            result = estimate_videos(course)

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any("missing duration_seconds" in item for item in result["blocked_reasons"]))

    def test_source_states_distinguish_ready_placeholder_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = self._course_with_mixed_video_states(Path(tmpdir))

            payload = assemble_lesson_plan(course, require_video_ready=False)

            states = {lesson["id"]: lesson["readiness"]["source_states"]["video"]["state"] for lesson in payload["lessons"]}
            self.assertEqual(states["stereochemistry"], "source_backed")
            self.assertEqual(states["reaction_mechanisms"], "demo_placeholder")
            self.assertEqual(states["organic_synthesis"], "needs_processing")

    def test_artifact_only_indexes_preserve_bundled_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)
            self._add_artifact_fallbacks(course)
            write_json(course / "textbook_sources.json", [{
                "id": "missing_textbook",
                "source_type": "local_pdf",
                "local_path": "resources/textbooks/missing.pdf",
                "citation_label": "Missing textbook source",
                "required": True,
                "artifact_only_allowed": True,
            }])
            write_json(course / "question_bank_sources.json", [{
                "id": "missing_questions",
                "source_type": "local_pdf",
                "local_path": "resources/question_banks/missing.pdf",
                "citation_label": "Missing question source",
                "required": False,
                "artifact_only_allowed": True,
            }])

            textbook_index = index_textbooks(course)
            question_index = index_questions(course)

            self.assertEqual(textbook_index["status"], "artifact_only_ready")
            self.assertEqual(question_index["status"], "artifact_only_ready")
            self.assertTrue(textbook_index["lessons"][0]["matched_passages"][0]["artifact_only"])
            self.assertTrue(question_index["lessons"][0]["questions"][0]["artifact_only"])

    def test_curated_textbook_sections_preserve_in_app_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)

            textbook_index = index_textbooks(course)
            payload = assemble_lesson_plan(course, require_video_ready=False)

            passage = textbook_index["lessons"][0]["matched_passages"][0]
            lesson_passage = payload["lessons"][0]["textbook_evidence"][0]
            self.assertGreater(len(passage["full_text"]), len(passage["text_preview"]))
            self.assertTrue(passage["content_blocks"])
            self.assertEqual(lesson_passage["content_blocks"], passage["content_blocks"])

    def test_app_generation_writes_static_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course = Path(tmpdir) / "course"
            shutil.copytree(DEMO_COURSE, course)

            result = generate_app(course)

            self.assertEqual(result["status"], "ready")
            self.assertTrue((course / "site" / "index.html").exists())
            self.assertTrue((course / "site" / "app.js").exists())
            self.assertTrue((course / "site" / "styles.css").exists())

    def test_generic_python_has_no_demo_subject_leakage(self) -> None:
        forbidden = (
            "J" + "E" + "E",
            "G" + "A" + "T" + "E",
            "Clay" + "den",
            "P" + "W",
            "stereo" + "chemistry",
        )
        package_root = PROJECT_ROOT / "learning_tutor"
        for path in package_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                    self.assertNotIn(token, text, f"{token} leaked into {path}")

    def _course_with_confident_candidate(
        self,
        root: Path,
        duration_seconds: int = 1800,
        already_ingested: bool = False,
    ) -> Path:
        course = root / "course"
        shutil.copytree(DEMO_COURSE, course)
        course_data = load_course(course)
        lesson_ids = course_data["videodb_pilot"]["recommended_lessons"]
        candidate = {
            "source_id": "pilot_video_001",
            "kind": "video",
            "title": "Pilot video",
            "url": "https://example.edu/video/001",
            "lesson_ids": lesson_ids,
            "status": "ready_for_ingest",
            "citation_label": "Approved video source",
            "duration_seconds": duration_seconds,
        }
        videos = []
        if already_ingested:
            videos.append({
                **candidate,
                "video_id": "vdb_real_001",
                "collection_id": "collection_real",
                "upload_status": "uploaded",
                "spoken_word_index_status": "ready",
                "scene_index_status": "not_required",
                "timestamp_searchable": True,
                "transcript_cache": {
                    "segments": [{"start": 0, "end": 60, "label": "00:00-01:00", "text": "Processed transcript."}]
                },
            })
        write_json(artifact_path(course_data, "video_index.json"), {"videos": videos, "candidates": [candidate]})
        return course

    def _course_with_three_confident_candidates(self, root: Path) -> Path:
        course = root / "course"
        shutil.copytree(DEMO_COURSE, course)
        course_data = load_course(course)
        lesson_ids = course_data["videodb_pilot"]["recommended_lessons"]
        candidates = [
            {
                "source_id": f"pilot_video_{idx}",
                "kind": "video",
                "title": f"Pilot video {idx}",
                "url": f"https://example.edu/video/{idx}",
                "lesson_ids": [lesson_id],
                "status": "ready_for_ingest",
                "citation_label": "Approved video source",
                "duration_seconds": 1800,
            }
            for idx, lesson_id in enumerate(lesson_ids, 1)
        ]
        write_json(artifact_path(course_data, "video_index.json"), {"videos": [], "candidates": candidates})
        return course

    def _course_with_mixed_video_states(self, root: Path) -> Path:
        course = root / "course"
        shutil.copytree(DEMO_COURSE, course)
        course_data = load_course(course)
        lesson_ids = course_data["videodb_pilot"]["recommended_lessons"]
        bundled = {
            "source_id": "bundled_demo_video",
            "title": "Bundled demo evidence",
            "citation_label": "Bundled video source",
            "video_id": "bundled_demo_001",
            "collection_id": "bundled_collection",
            "upload_status": "uploaded",
            "spoken_word_index_status": "ready",
            "scene_index_status": "not_required",
            "timestamp_searchable": True,
            "lesson_ids": [lesson_ids[0], lesson_ids[1]],
            "transcript_cache": {
                "segments": [{"start": 0, "end": 60, "label": "00:00-01:00", "text": "Placeholder marker."}]
            },
        }
        real = {
            "source_id": "real_pilot_video",
            "title": "Processed pilot evidence",
            "citation_label": "Processed video source",
            "video_id": "vdb_real_001",
            "collection_id": "collection_real",
            "upload_status": "uploaded",
            "spoken_word_index_status": "ready",
            "scene_index_status": "not_required",
            "timestamp_searchable": True,
            "lesson_ids": [lesson_ids[0]],
            "transcript_cache": {
                "segments": [{"start": 0, "end": 60, "label": "00:00-01:00", "text": "Processed transcript evidence."}]
            },
            "search_validation": [{
                "lesson_id": lesson_ids[0],
                "query": "stereochemistry",
                "validation_mode": "videodb_spoken_word_search",
                "result_count": 1,
                "results": [{
                    "start": 120,
                    "end": 210,
                    "label": "02:00-03:30",
                    "query": "stereochemistry",
                    "text": "Chiral molecules, enantiomers, mirror images, and specific rotation teaching example with enough classroom explanation.",
                }],
            }],
        }
        write_json(artifact_path(course_data, "video_index.json"), {"videos": [bundled, real], "candidates": []})
        return course

    def _reset_pilot_ingest_state(self, course: Path) -> None:
        course_data = load_course(course)
        index_path = artifact_path(course_data, "video_index.json")
        index = __import__("json").loads(index_path.read_text(encoding="utf-8"))
        pilot_source_ids = {
            "gate_organic_graph_stereochemistry_specific_rotation",
            "gate_organic_pilot_reaction_mechanism_ifas",
            "gate_organic_pilot_organic_synthesis_retrosynthesis",
        }
        index["videos"] = [
            item for item in index.get("videos", [])
            if str(item.get("video_id") or "").startswith("bundled_")
        ]
        for candidate in index.get("candidates", []):
            if candidate.get("source_id") in pilot_source_ids or candidate.get("video_id"):
                candidate["status"] = "ready_for_ingest"
                candidate.pop("video_id", None)
                candidate.pop("collection_id", None)
        write_json(index_path, index)

    def _add_artifact_fallbacks(self, course: Path) -> None:
        lesson_path = course / "lesson_map.json"
        lesson_map = __import__("json").loads(lesson_path.read_text(encoding="utf-8"))
        for lesson in lesson_map.get("lessons", []):
            lesson.setdefault("bundled_textbook_citations", [{
                "chunk_id": f"artifact_textbook_{lesson['id']}",
                "citation_label": "Bundled textbook placeholder",
                "text_preview": "Bundled placeholder citation for artifact-only testing.",
                "artifact_only": True,
            }])
            lesson.setdefault("bundled_question_refs", [{
                "question_id": f"artifact_question_{lesson['id']}",
                "citation_label": "Bundled question placeholder",
                "prompt_preview": "Bundled placeholder question for artifact-only testing.",
                "artifact_only": True,
            }])
        lesson_path.write_text(__import__("json").dumps(lesson_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class FakeVideoDBRuntime:
    def __init__(self, usage_values: list[float] | None = None, fail_on_source: str | None = None) -> None:
        self.usage_values = usage_values or [0, 1, 2, 3]
        self.usage_index = 0
        self.fail_on_source = fail_on_source

    def check_usage(self) -> dict:
        value = self.usage_values[min(self.usage_index, len(self.usage_values) - 1)]
        self.usage_index += 1
        return {"credit_used": value}

    def ingest_candidate(self, candidate: dict, lesson_queries: dict, requires_scene_index: bool) -> dict:
        source_id = candidate["source_id"]
        if source_id == self.fail_on_source:
            raise RuntimeError("simulated VideoDB failure")
        lesson_id = candidate["lesson_ids"][0]
        return {
            "source_id": source_id,
            "title": candidate.get("title"),
            "url": candidate.get("url"),
            "citation_label": candidate.get("citation_label"),
            "video_id": f"vdb_real_{source_id}",
            "collection_id": "collection_real",
            "upload_status": "uploaded",
            "spoken_word_index_status": "ready",
            "scene_index_status": "not_required",
            "timestamp_searchable": True,
            "lesson_ids": candidate.get("lesson_ids", []),
            "transcript_cache": {
                "segments": [{"start": 0, "end": 30, "label": "00:00-00:30", "text": f"Transcript for {lesson_id}."}]
            },
            "search_validation": [{
                "lesson_id": lesson_id,
                "query": lesson_queries[lesson_id],
                "validation_mode": "videodb_spoken_word_search",
                "result_count": 1,
                "results": [{"start": 5, "end": 45, "label": "00:05-00:45", "text": self._aligned_result_text(lesson_id), "score": 0.9}],
            }],
        }

    def _aligned_result_text(self, lesson_id: str) -> str:
        if lesson_id == "stereochemistry":
            return "Search hit for chiral molecules, enantiomers, mirror images, and specific rotation with enough classroom explanation."
        if lesson_id == "reaction_mechanisms":
            return "Search hit for reaction mechanism, intermediates, bond breaking, and electron movement with enough classroom explanation."
        if lesson_id == "organic_synthesis":
            return "Search hit for synthesis, reaction sequence, reagents, transformation, and major product planning with enough classroom explanation."
        return f"Search hit for {lesson_id} with enough classroom explanation for this concept."


if __name__ == "__main__":
    unittest.main()
