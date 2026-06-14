"""Filesystem helpers shared by the skill engine."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def validate_path_component(value: str, label: str = "path component") -> str:
    """Reject empty, absolute, nested, and traversal path components."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    if len(value) > 128:
        raise ValueError(f"{label} is too long")
    if "\x00" in value or value in {".", ".."}:
        raise ValueError(f"invalid {label}: {value!r}")
    if Path(value).is_absolute() or Path(value).name != value:
        raise ValueError(f"{label} must not contain a path: {value!r}")
    if "/" in value or "\\" in value:
        raise ValueError(f"{label} must not contain separators: {value!r}")
    return value


def safe_child(root: Path, component: str, label: str = "path component") -> Path:
    """Return a direct child of root after validating the component."""
    validate_path_component(component, label)
    root_resolved = root.resolve()
    child = (root_resolved / component).resolve()
    if child.parent != root_resolved:
        raise ValueError(f"{label} escapes its root: {component!r}")
    return child


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write a text file atomically in the destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
    )
