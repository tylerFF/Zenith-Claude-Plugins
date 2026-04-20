"""Session-scoped snapshot of a sheet's row state, with restore helpers."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from scripts.sheet_analyzer import SheetAnalyzer


@dataclass
class RowSnapshot:
    id: int
    parent_id: Optional[int]
    row_number: int
    cells: List[Dict[str, Any]]


@dataclass
class Snapshot:
    sheet_id: int
    rows: List[RowSnapshot] = field(default_factory=list)
    # Column formula columns that can't be written to (we strip these at restore time)
    formula_column_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Snapshot":
        return cls(
            sheet_id=d["sheet_id"],
            rows=[RowSnapshot(**r) for r in d["rows"]],
            formula_column_ids=list(d.get("formula_column_ids", [])),
        )


def snapshot_sheet(analyzer: SheetAnalyzer) -> Snapshot:
    """Capture the full state of a sheet's rows in a restorable form."""
    formula_col_ids = [
        c["id"]
        for c in analyzer._sheet.get("columns", [])
        if c.get("formula") or c.get("systemColumnType")
    ]
    rows = []
    for raw in analyzer._sheet.get("rows", []):
        rows.append(
            RowSnapshot(
                id=raw["id"],
                parent_id=raw.get("parentId"),
                row_number=raw.get("rowNumber", 0),
                # Strip read-only cell values from formula columns at snapshot time
                cells=[
                    {"columnId": c["columnId"], "value": c.get("value")}
                    for c in raw.get("cells", [])
                    if c.get("columnId") not in formula_col_ids
                    and c.get("value") is not None
                ],
            )
        )
    return Snapshot(
        sheet_id=analyzer._sheet["id"],
        rows=rows,
        formula_column_ids=formula_col_ids,
    )


def rows_for_restore(snapshot: Snapshot, root_row_ids: List[int]) -> List[Dict[str, Any]]:
    """Return API-ready row payloads to restore the given roots + their descendants.

    Output is ordered parent-before-child so that when POSTed in sequence with
    `parentId` pointing to the *new* ID of the previously-restored parent,
    the hierarchy is preserved. The caller is responsible for translating
    original IDs to newly-assigned IDs between calls.
    """
    # Build parent -> children adjacency from snapshot
    by_parent: Dict[Optional[int], List[RowSnapshot]] = {}
    for r in snapshot.rows:
        by_parent.setdefault(r.parent_id, []).append(r)

    out: List[Dict[str, Any]] = []
    # Depth-first traversal emitting parents before their own children.
    for root_id in root_row_ids:
        roots = [r for r in snapshot.rows if r.id == root_id]
        stack = list(roots)
        while stack:
            current = stack.pop(0)
            out.append({
                "_original_id": current.id,
                "_original_parent_id": current.parent_id,
                "cells": current.cells,
                "toBottom": True,  # default placement; caller can override
            })
            # Enqueue children in original row-number order, at front (depth-first)
            children = sorted(by_parent.get(current.id, []), key=lambda r: r.row_number)
            stack[0:0] = children

    return out
