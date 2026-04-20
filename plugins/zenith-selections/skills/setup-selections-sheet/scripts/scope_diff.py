"""Diff an analyzed sheet against the designer's parsed scope.

Produces a ChangeSet describing what to delete, keep, and resolve-by-asking.
The skill uses this to drive its flag-and-ask flow and its writes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scripts.sheet_analyzer import (
    SheetAnalyzer,
    Row,
    EVERYWHERE_SECTION_NAME,
)


@dataclass
class RoomChange:
    """A top-level room that's staying. Lists what items to keep/delete under it."""
    room_name: str
    room_id: int
    rows_to_keep: List[Row] = field(default_factory=list)
    rows_to_delete: List[Row] = field(default_factory=list)


@dataclass
class RoomDeletion:
    """A top-level room being deleted entirely (including all descendants)."""
    room_name: str
    room_id: int
    all_descendant_ids: List[int]


@dataclass
class AmbiguousItem:
    """An item mentioned in scope that's not in the template's expected items for its room."""
    item_name: str
    room_name: str  # the room the designer said to put it in


@dataclass
class AmbiguousRoom:
    """A room mentioned in scope that's not a top-level template room."""
    room_name: str
    items: List[str]


@dataclass
class ChangeSet:
    rooms_to_keep: List[RoomChange] = field(default_factory=list)
    rooms_to_delete: List[RoomDeletion] = field(default_factory=list)
    ambiguous_rooms: List[AmbiguousRoom] = field(default_factory=list)
    ambiguous_items: List[AmbiguousItem] = field(default_factory=list)


def compute_change_set(
    analyzer: SheetAnalyzer,
    scope: Dict[str, List[str]],
) -> ChangeSet:
    """Compute deletions, kept rows, and ambiguous entries from scope vs sheet.

    `scope` maps room names (canonical template names) to lists of item names
    that should stay. Rooms not in `scope` are slated for deletion (except
    "Everywhere (in scope)"). Items in `scope` but not in the template are
    flagged as ambiguous.
    """
    cs = ChangeSet()
    top_level = analyzer.top_level_rooms()

    # Bucket top-level rooms by whether they're in scope.
    in_scope_room_names = set(scope.keys())

    for room in top_level:
        if room.description == EVERYWHERE_SECTION_NAME:
            # Always preserved, never touched.
            continue

        if room.description in in_scope_room_names:
            # Room is staying — figure out which items to keep/delete.
            rc = _build_room_change(analyzer, room, scope[room.description], cs)
            cs.rooms_to_keep.append(rc)
        else:
            # Room not mentioned — delete it and everything under it.
            descendants = analyzer.descendants(room.id)
            cs.rooms_to_delete.append(
                RoomDeletion(
                    room_name=room.description,
                    room_id=room.id,
                    all_descendant_ids=[d.id for d in descendants],
                )
            )

    # Handle ambiguous rooms: scope keys that aren't top-level rooms in the sheet.
    template_top_names = {r.description for r in top_level}
    for scope_room, scope_items in scope.items():
        if scope_room not in template_top_names:
            cs.ambiguous_rooms.append(
                AmbiguousRoom(room_name=scope_room, items=list(scope_items))
            )

    return cs


def _build_room_change(
    analyzer: SheetAnalyzer,
    room: Row,
    scope_items: List[str],
    cs: ChangeSet,  # to push ambiguous items into
) -> RoomChange:
    """For a kept room, decide which direct children stay vs. get deleted.

    Also detects items in scope_items that don't match any template child —
    those go to cs.ambiguous_items.
    """
    rc = RoomChange(room_name=room.description, room_id=room.id)

    # We operate on direct children only for keep/delete decisions;
    # grandchildren ride along with their parent.
    all_descendants = analyzer.descendants(room.id)
    direct_children = [r for r in all_descendants if r.parent_id == room.id]

    scope_items_remaining = list(scope_items)
    for child in direct_children:
        # Simple case-insensitive exact match for kept items.
        matched_scope = _match_scope_item(child.description, scope_items)
        if matched_scope is not None:
            rc.rows_to_keep.append(child)
            if matched_scope in scope_items_remaining:
                scope_items_remaining.remove(matched_scope)
        else:
            rc.rows_to_delete.append(child)
            # Delete grandchildren too (cascades)
            for grand in analyzer.descendants(child.id):
                rc.rows_to_delete.append(grand)

    # Scope items that didn't match any template child -> ambiguous
    for leftover in scope_items_remaining:
        cs.ambiguous_items.append(
            AmbiguousItem(item_name=leftover, room_name=room.description)
        )

    return rc


def _match_scope_item(template_desc: str, scope_items: List[str]) -> Optional[str]:
    """Case-insensitive exact-match of template description against scope items.

    Returns the matching scope item (original case) if a match found, else None.
    """
    t = template_desc.strip().lower()
    for s in scope_items:
        if s.strip().lower() == t:
            return s
    return None
