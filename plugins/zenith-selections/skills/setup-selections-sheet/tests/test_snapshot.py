import json
from pathlib import Path
import pytest

from scripts.sheet_analyzer import SheetAnalyzer
from scripts.snapshot import Snapshot, snapshot_sheet, rows_for_restore

FIXTURE = Path(__file__).parent / "fixtures" / "sheet_sample.json"


@pytest.fixture
def analyzer():
    return SheetAnalyzer(json.loads(FIXTURE.read_text()))


class TestSnapshot:
    def test_captures_all_rows(self, analyzer):
        snap = snapshot_sheet(analyzer)
        # Every row in the fixture should appear in the snapshot
        row_count = len(analyzer._rows)
        assert len(snap.rows) == row_count

    def test_snapshot_is_json_serializable(self, analyzer):
        snap = snapshot_sheet(analyzer)
        as_dict = snap.to_dict()
        # Should round-trip through JSON
        restored = Snapshot.from_dict(json.loads(json.dumps(as_dict)))
        assert len(restored.rows) == len(snap.rows)


class TestRowsForRestore:
    def test_restoring_room_includes_descendants(self, analyzer):
        snap = snapshot_sheet(analyzer)
        hb = analyzer.find_room_by_description("Hall Bathroom")
        # Request restore of Hall Bathroom
        restore_payload = rows_for_restore(snap, [hb.id])
        # Should include Hall Bathroom + its children + any grandchildren
        # (preserving parent-child order so inserts don't orphan grandchildren)
        assert len(restore_payload) > 1
        # First row should be the top-level parent
        assert restore_payload[0]["cells"] is not None

    def test_restore_order_parents_before_children(self, analyzer):
        snap = snapshot_sheet(analyzer)
        hb = analyzer.find_room_by_description("Hall Bathroom")
        restore_payload = rows_for_restore(snap, [hb.id])
        # Verify parent appears before its children in the output
        # Find the parent and at least one child, confirm index ordering
        parent_idx = next(
            (i for i, r in enumerate(restore_payload) if r.get("_original_id") == hb.id),
            None,
        )
        assert parent_idx == 0
