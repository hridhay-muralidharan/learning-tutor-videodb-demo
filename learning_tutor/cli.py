"""CLI for configurable source-grounded study-app generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app.generator import generate_app, serve_app
from .config import CourseError, artifact_path, load_course, videodb_api_key
from .course.validate import validate_course
from .graph.builder import build_evidence_graph, verify_evidence_graph
from .planner.assembler import assemble_lesson_plan
from .questions.indexer import index_questions, validate_questions
from .syllabus.indexer import index_syllabus, validate_syllabus
from .textbooks.indexer import index_textbooks, validate_textbooks
from .videos.costs import DEFAULT_BUDGET_USD
from .videos.manager import discover_videos, dry_run_videos, estimate_videos, ingest_videos, refresh_video_searches, validate_videos, verify_videos


def cmd_doctor(args: argparse.Namespace) -> int:
    course = load_course(args.course)
    errors, warnings = validate_course(args.course)
    video_errors, video_warnings, video_report = verify_videos(args.course)
    site_ready = (Path(course["_path"]) / str(course.get("site_dir", "site")) / "index.html").exists()
    print(f"Course: {course.get('title')}")
    print(f"Course path: {course['_path']}")
    print(f"VideoDB key: {'present' if videodb_api_key() else 'missing'}")
    print(f"Static app: {'ready' if site_ready else 'missing'}")
    print(f"Video artifacts: {video_report.get('status')}")
    for warning in warnings + video_warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if video_errors:
        print("Video verification issues:")
        for error in video_errors:
            print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("OK: course pack can be studied as-is." if site_ready else "OK: course metadata is valid; app not generated yet.")
    return 0


def cmd_course_validate(args: argparse.Namespace) -> int:
    return _print_validation(*validate_course(args.course), ok="course validated")


def cmd_syllabus(args: argparse.Namespace) -> int:
    if args.action == "validate":
        return _print_validation(*validate_syllabus(args.course), ok="syllabus sources validated")
    result = index_syllabus(args.course)
    print(f"OK: wrote {artifact_path(load_course(args.course), 'syllabus_index.json')} ({len(result.get('anchors', []))} anchors)")
    return 0


def cmd_textbooks(args: argparse.Namespace) -> int:
    if args.action == "validate":
        return _print_validation(*validate_textbooks(args.course), ok="textbook sources validated")
    result = index_textbooks(args.course)
    print(f"OK: wrote textbook index ({result.get('status')}, {result.get('passage_count')} passages)")
    return 0


def cmd_questions(args: argparse.Namespace) -> int:
    if args.action == "validate":
        return _print_validation(*validate_questions(args.course), ok="question sources validated")
    result = index_questions(args.course)
    print(f"OK: wrote question index ({result.get('status')}, {result.get('question_count')} questions)")
    return 0


def cmd_videos(args: argparse.Namespace) -> int:
    if args.action == "validate":
        return _print_validation(*validate_videos(args.course), ok="video sources validated")
    if args.action == "discover":
        result = discover_videos(args.course, limit=args.limit)
        print(f"OK: wrote video discovery ({result.get('discovered_count')} candidates, no credits spent)")
        return 0
    if args.action == "estimate":
        result = estimate_videos(args.course, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(result)
        return 0 if result.get("status") != "blocked" else 1
    if args.action == "dry-run":
        result = dry_run_videos(args.course, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(result)
        return 0 if result.get("status") != "blocked" else 1
    if args.action == "ingest":
        result = ingest_videos(args.course, confirm=args.confirm, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(result)
        return 0 if result.get("status") not in {"refused", "blocked"} else 1
    if args.action == "refresh-search":
        result = refresh_video_searches(args.course, confirm=args.confirm, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(result)
        return 0 if result.get("status") not in {"refused", "blocked"} else 1
    errors, warnings, report = verify_videos(args.course)
    return _print_validation(errors, warnings, ok=f"videos verified ({report.get('video_count')} videos)")


def cmd_graph(args: argparse.Namespace) -> int:
    if args.action == "build":
        result = build_evidence_graph(args.course)
        print(f"OK: wrote evidence graph ({result.get('status')}, {len(result.get('lessons', []))} lessons)")
        return 0
    errors, warnings, report = verify_evidence_graph(args.course)
    return _print_validation(errors, warnings, ok=f"evidence graph verified ({report.get('status')})")


def cmd_app(args: argparse.Namespace) -> int:
    if args.action == "generate":
        result = generate_app(args.course, use_existing_plan=args.use_existing_plan)
        _print_dict(result)
        return 0
    serve_app(args.course, port=args.port)
    return 0


def cmd_setup_course(args: argparse.Namespace) -> int:
    steps = [
        ("course validate", lambda: _must(validate_course(args.course))),
        ("syllabus index", lambda: index_syllabus(args.course)),
        ("textbooks index", lambda: index_textbooks(args.course)),
        ("questions index", lambda: index_questions(args.course)),
        ("videos discover", lambda: discover_videos(args.course)),
    ]
    for label, step in steps:
        print(f"==> {label}")
        step()
    if args.confirm_ingest:
        print("==> videos estimate")
        estimate_result = estimate_videos(args.course, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(estimate_result)
        if estimate_result.get("status") == "blocked":
            return 1
        print("==> videos dry-run")
        dry_run_result = dry_run_videos(args.course, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(dry_run_result)
        if dry_run_result.get("status") == "blocked":
            return 1
        print("==> videos ingest")
        ingest_result = ingest_videos(args.course, confirm=True, lesson_ids=_lesson_list(args.lessons), budget_usd=args.budget)
        _print_dict(ingest_result)
        if ingest_result.get("status") in {"refused", "blocked"}:
            return 1
    print("==> videos verify")
    _must(verify_videos(args.course)[:2])
    print("==> lesson plan")
    assemble_lesson_plan(args.course)
    print("==> app generate")
    result = generate_app(args.course)
    _print_dict(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learning_tutor", description="Source-grounded institutional study app generator.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check a course pack without spending credits")
    doctor.add_argument("--course", required=True)
    doctor.set_defaults(func=cmd_doctor)

    course = subparsers.add_parser("course", help="Course configuration commands")
    course_sub = course.add_subparsers(dest="action", required=True)
    course_validate = course_sub.add_parser("validate")
    course_validate.add_argument("--course", required=True)
    course_validate.set_defaults(func=cmd_course_validate)

    for name, func in (("syllabus", cmd_syllabus), ("textbooks", cmd_textbooks), ("questions", cmd_questions)):
        parent = subparsers.add_parser(name)
        child = parent.add_subparsers(dest="action", required=True)
        validate = child.add_parser("validate")
        validate.add_argument("--course", required=True)
        validate.set_defaults(func=func)
        index = child.add_parser("index")
        index.add_argument("--course", required=True)
        index.set_defaults(func=func)

    videos = subparsers.add_parser("videos")
    videos_sub = videos.add_subparsers(dest="action", required=True)
    for action in ("validate", "verify"):
        parser_action = videos_sub.add_parser(action)
        parser_action.add_argument("--course", required=True)
        parser_action.set_defaults(func=cmd_videos)
    discover = videos_sub.add_parser("discover")
    discover.add_argument("--course", required=True)
    discover.add_argument("--limit", type=int, default=50)
    discover.set_defaults(func=cmd_videos)
    estimate = videos_sub.add_parser("estimate")
    estimate.add_argument("--course", required=True)
    estimate.add_argument("--lessons", default=None, help="Comma-separated lesson IDs. Defaults to course videodb_pilot.recommended_lessons.")
    estimate.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    estimate.set_defaults(func=cmd_videos)
    dry_run = videos_sub.add_parser("dry-run")
    dry_run.add_argument("--course", required=True)
    dry_run.add_argument("--lessons", default=None, help="Comma-separated lesson IDs. Defaults to course videodb_pilot.recommended_lessons.")
    dry_run.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    dry_run.set_defaults(func=cmd_videos)
    ingest = videos_sub.add_parser("ingest")
    ingest.add_argument("--course", required=True)
    ingest.add_argument("--confirm", action="store_true")
    ingest.add_argument("--lessons", default=None, help="Comma-separated lesson IDs. Defaults to course videodb_pilot.recommended_lessons.")
    ingest.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    ingest.set_defaults(func=cmd_videos)
    refresh = videos_sub.add_parser("refresh-search")
    refresh.add_argument("--course", required=True)
    refresh.add_argument("--confirm", action="store_true")
    refresh.add_argument("--lessons", default=None, help="Comma-separated lesson IDs. Defaults to every lesson in the course.")
    refresh.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    refresh.set_defaults(func=cmd_videos)

    graph = subparsers.add_parser("graph")
    graph_sub = graph.add_subparsers(dest="action", required=True)
    for action in ("build", "verify"):
        graph_action = graph_sub.add_parser(action)
        graph_action.add_argument("--course", required=True)
        graph_action.set_defaults(func=cmd_graph)

    app = subparsers.add_parser("app")
    app_sub = app.add_subparsers(dest="action", required=True)
    generate = app_sub.add_parser("generate")
    generate.add_argument("--course", required=True)
    generate.add_argument("--use-existing-plan", action="store_true")
    generate.set_defaults(func=cmd_app)
    serve = app_sub.add_parser("serve")
    serve.add_argument("--course", required=True)
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=cmd_app)

    setup = subparsers.add_parser("setup-course", help="Validate, index, verify, and generate a course app")
    setup.add_argument("--course", required=True)
    setup.add_argument("--confirm-ingest", action="store_true")
    setup.add_argument("--lessons", default=None, help="Comma-separated pilot lesson IDs for confirmed ingest.")
    setup.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    setup.set_defaults(func=cmd_setup_course)
    return parser


def _print_validation(errors: list[str], warnings: list[str], ok: str) -> int:
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {ok}")
    return 0


def _must(result: tuple[list[str], list[str]]) -> None:
    errors, warnings = result
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        raise CourseError("\n".join(errors))


def _print_dict(payload: dict) -> None:
    import json

    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _lesson_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CourseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
