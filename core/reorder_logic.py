"""core/reorder_logic.py

Small, UI-agnostic helpers for reordering.

The UI is responsible for detecting *when* a swap should happen. These helpers
provide a single place to keep the list mutation and index refresh consistent.
"""

from __future__ import annotations

from typing import List, MutableSequence, TypeVar

T = TypeVar("T")


def move_item(seq: MutableSequence[T], from_pos: int, to_pos: int) -> None:
    """Move one element inside `seq`.

    Positions are 0-based.
    """

    if from_pos == to_pos:
        return
    if from_pos < 0 or from_pos >= len(seq):
        return
    if to_pos < 0 or to_pos >= len(seq):
        return

    item = seq.pop(from_pos)
    seq.insert(to_pos, item)


def refresh_item_indices(items: List[object], index_attr: str = "index") -> None:
    """Update each item's `.index` (or any attribute name) to be 1..N."""

    for idx, item in enumerate(items, start=1):
        setattr(item, index_attr, idx)
