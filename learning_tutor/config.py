"""Configuration and file helpers for generic course packs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - validation catches missing dependency.
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "app"


class CourseError(RuntimeError):
    """Raised for user-fixable course configuration errors."""


def load_env(project_root: Path = PROJECT_ROOT) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def videodb_api_key() -> str | None:
    load_env()
    return os.getenv("VIDEODB_API_KEY") or os.getenv("VIDEO_DB_API_KEY")


def resolve_course_path(course: str | Path) -> Path:
    course_path = Path(course)
    if not course_path.is_absolute():
        course_path = PROJECT_ROOT / course_path
    return course_path.resolve()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise CourseError(f"Missing required file: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise CourseError("PyYAML is required. Install dependencies from requirements.txt.")
    if not path.exists():
        raise CourseError(f"Missing required file: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise CourseError(f"{path} must contain a YAML mapping.")
    return data


def load_course(course: str | Path) -> dict[str, Any]:
    course_path = resolve_course_path(course)
    data = read_yaml(course_path / "course.yaml")
    data["_path"] = str(course_path)
    data["_slug"] = course_path.name
    data.setdefault("artifacts_dir", "artifacts")
    data.setdefault("site_dir", "site")
    data.setdefault("readiness", {})
    data.setdefault("generation", {})
    return data


def course_path(course: dict[str, Any], *parts: str) -> Path:
    return Path(str(course["_path"]), *parts)


def artifact_path(course: dict[str, Any], name: str) -> Path:
    return course_path(course, str(course.get("artifacts_dir", "artifacts")), name)


def site_path(course: dict[str, Any], *parts: str) -> Path:
    return course_path(course, str(course.get("site_dir", "site")), *parts)


def source_path(course: dict[str, Any], source_file: str) -> Path:
    return course_path(course, source_file)
