"""core/data_handler.py

JSON save/load logic.

The UI works with absolute paths during a session (fast + unambiguous), but when
saving a project we attempt to store paths relative to the project file. This
improves portability when a project folder is moved.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BOMItem:
    """In-memory representation of a single BOM row."""

    index: int
    model: str = ""
    description: str = ""
    make: str = ""
    quantity: int = 1
    datasheet_path: str = ""  # absolute path at runtime

    def to_json_dict(self, project_dir: Path) -> Dict[str, Any]:
        """Serialize the item to the project schema.

        We store `datasheet_path` as relative when possible.
        """

        return {
            "index": int(self.index),
            "model": str(self.model),
            "description": str(self.description),
            "make": str(self.make),
            "quantity": int(self.quantity),
            "datasheet_path": _make_relative_if_possible(self.datasheet_path, project_dir),
        }

    @staticmethod
    def from_json_dict(d: Dict[str, Any], project_dir: Path) -> "BOMItem":
        """Parse from project schema.

        Incoming paths may be relative; we normalize to absolute.
        """

        datasheet_path = _resolve_path(d.get("datasheet_path", ""), project_dir)
        return BOMItem(
            index=int(d.get("index", 0) or 0),
            model=str(d.get("model", "")),
            description=str(d.get("description", "")),
            make=str(d.get("make", "")),
            quantity=int(d.get("quantity", 1) or 1),
            datasheet_path=str(datasheet_path) if datasheet_path else "",
        )


def new_project_payload(
    items: List[BOMItem],
    cover_page_path: Optional[str],
    project_dir: Path,
) -> Dict[str, Any]:
    """Create the canonical JSON payload per AGENTS.MD."""

    return {
        "project_metadata": {
            "cover_page_path": _make_relative_if_possible(cover_page_path, project_dir),
            "export_date": datetime.now(timezone.utc).isoformat(),
        },
        "items": [i.to_json_dict(project_dir) for i in items],
    }


def save_to_json(project_file_path: str, items: List[BOMItem], cover_page_path: Optional[str]) -> None:
    """Save the project to a JSON file."""

    project_path = Path(project_file_path)
    project_dir = project_path.parent
    payload = new_project_payload(items=items, cover_page_path=cover_page_path, project_dir=project_dir)

    project_dir.mkdir(parents=True, exist_ok=True)
    project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_from_json(project_file_path: str) -> Dict[str, Any]:
    """Load a project file.

    Returns a dict with:
    - `cover_page_path`: str|None (absolute)
    - `items`: List[BOMItem]
    """

    project_path = Path(project_file_path)
    project_dir = project_path.parent

    raw = json.loads(project_path.read_text(encoding="utf-8"))
    meta = raw.get("project_metadata", {}) or {}

    cover_page = _resolve_path(meta.get("cover_page_path"), project_dir)
    items_raw = raw.get("items", []) or []

    items = [BOMItem.from_json_dict(d, project_dir) for d in items_raw]
    # Ensure indices are sane and sequential after load.
    items = sorted(items, key=lambda x: x.index)
    for idx, item in enumerate(items, start=1):
        item.index = idx

    return {
        "cover_page_path": str(cover_page) if cover_page else None,
        "items": items,
    }


def _resolve_path(value: Any, base_dir: Path) -> Optional[Path]:
    """Resolve a path stored in JSON to an absolute Path.

    - None/"" -> None
    - relative -> base_dir / relative
    - absolute -> Path(value)
    """

    if not value:
        return None

    p = Path(str(value))
    if p.is_absolute():
        return p

    # On Windows, `Path("C:foo")` is not absolute but is drive-relative. Treat it as absolute-ish.
    if os.name == "nt" and len(p.drive) > 0:
        return p

    return (base_dir / p).resolve()


def _make_relative_if_possible(path_value: Optional[str], project_dir: Path) -> Optional[str]:
    """Convert `path_value` to a relative path when it is safe/possible."""

    if not path_value:
        return None

    try:
        abs_path = Path(path_value)
        if not abs_path.is_absolute():
            return str(abs_path)
        rel = os.path.relpath(str(abs_path), str(project_dir))
        return rel
    except Exception:
        # If we can't relativize (different drive, invalid path, etc.), keep the original.
        return str(path_value)
