"""Structural queries over a fetched Smartsheet sheet JSON."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


# Canonical template rooms (for sanity check and alias matching).
# Order matches the standard Zenith master template.
TEMPLATE_ROOM_NAMES: List[str] = [
    "Everywhere (in scope)",
    "Kitchen/Bar",
    "Master Bathroom",
    "Powder Bathroom",
    "Hall Bathroom",
    "Mudroom/Laundry",
    "Basement - Kitchen/Bar",
    "Basement - Hall Bathroom",
    "Bedroom/Living/Dining/Family/Office/Sunroom",
    "Exterior",
]

# The generic section that applies to every project and is never auto-deleted.
EVERYWHERE_SECTION_NAME: str = "Everywhere (in scope)"

# Column titles we care about (used to look up column IDs dynamically).
_DESCRIPTION_COL_TITLE = "Description"
_CATEGORY_COL_TITLE = "Category"
_LOCATION_COL_TITLE = "Location"


@dataclass(frozen=True)
class Row:
    id: int
    row_number: int
    parent_id: Optional[int]
    description: str
    category: str
    location: str


class SheetAnalyzer:
    def __init__(self, sheet_json: Dict[str, Any]):
        self._sheet = sheet_json
        self._columns = {c["title"]: c["id"] for c in sheet_json.get("columns", [])}
        self._rows: List[Row] = [self._parse_row(r) for r in sheet_json.get("rows", [])]
        self._by_id: Dict[int, Row] = {r.id: r for r in self._rows}
        self._by_parent: Dict[Optional[int], List[Row]] = {}
        for r in self._rows:
            self._by_parent.setdefault(r.parent_id, []).append(r)

    def _parse_row(self, raw: Dict) -> Row:
        def cell_value(title: str) -> str:
            col_id = self._columns.get(title)
            if col_id is None:
                return ""
            for c in raw.get("cells", []):
                if c.get("columnId") == col_id:
                    return str(c.get("displayValue") or c.get("value") or "")
            return ""

        return Row(
            id=raw["id"],
            row_number=raw.get("rowNumber", 0),
            parent_id=raw.get("parentId"),
            description=cell_value(_DESCRIPTION_COL_TITLE),
            category=cell_value(_CATEGORY_COL_TITLE),
            location=cell_value(_LOCATION_COL_TITLE),
        )

    def top_level_rooms(self) -> List[Row]:
        """Rows with no parent."""
        return list(self._by_parent.get(None, []))

    def find_room_by_description(self, description: str) -> Optional[Row]:
        """Case-sensitive exact match on Description for a top-level row."""
        for r in self.top_level_rooms():
            if r.description == description:
                return r
        return None

    def descendants(self, row_id: int) -> List[Row]:
        """All descendants (children + grandchildren + ...) of a row."""
        out: List[Row] = []
        stack = list(self._by_parent.get(row_id, []))
        while stack:
            r = stack.pop()
            out.append(r)
            stack.extend(self._by_parent.get(r.id, []))
        return out

    def is_in_everywhere_section(self, row_id: int) -> bool:
        """True if the row is a descendant of the Everywhere (in scope) parent."""
        everywhere = self.find_room_by_description(EVERYWHERE_SECTION_NAME)
        if everywhere is None:
            return False
        descendant_ids = {r.id for r in self.descendants(everywhere.id)}
        return row_id in descendant_ids

    def looks_like_selections_template(self) -> bool:
        """Heuristic: at least one known template room name is a top-level row."""
        top_names = {r.description for r in self.top_level_rooms()}
        known = set(TEMPLATE_ROOM_NAMES)
        return bool(top_names & known)

    def column_id(self, title: str) -> Optional[int]:
        return self._columns.get(title)
