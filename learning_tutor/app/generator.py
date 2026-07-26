"""Generate a static learner app from a course lesson plan."""

from __future__ import annotations

import http.server
import socketserver
import string
from pathlib import Path

from ..config import TEMPLATE_DIR, artifact_path, load_course, read_json, site_path
from ..planner.assembler import assemble_lesson_plan
from ..videos.manager import verify_videos


def generate_app(course_arg: str | Path, use_existing_plan: bool = False) -> dict:
    course = load_course(course_arg)
    errors, warnings, report = verify_videos(course_arg)
    if errors:
        raise RuntimeError("app generate requires videos verify to pass:\n" + "\n".join(errors))

    plan_path = artifact_path(course, "lesson_plan.json")
    if use_existing_plan and plan_path.exists():
        plan = read_json(plan_path)
    else:
        plan = assemble_lesson_plan(course_arg, require_video_ready=False)

    target = site_path(course)
    target.mkdir(parents=True, exist_ok=True)
    data_json = _json_for_script(plan)
    replacements = {
        "COURSE_TITLE": str(plan.get("course", {}).get("title") or course.get("title")),
        "COURSE_DATA_JSON": data_json,
    }
    for filename in ("index.html", "styles.css", "app.js"):
        template = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
        output = string.Template(template).safe_substitute(replacements)
        (target / filename).write_text(output, encoding="utf-8")
    return {
        "status": "ready",
        "site_path": str(target),
        "lesson_count": len(plan.get("lessons", [])),
        "video_report": report,
        "warnings": warnings,
    }


def serve_app(course_arg: str | Path, port: int = 8765) -> None:
    course = load_course(course_arg)
    directory = site_path(course)
    if not (directory / "index.html").exists():
        raise RuntimeError(f"No generated app found at {directory}. Run app generate first.")

    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=str(directory), **kwargs)
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {directory} at http://127.0.0.1:{port}")
        httpd.serve_forever()


def _json_for_script(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)
