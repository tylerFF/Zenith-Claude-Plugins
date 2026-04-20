import json
from pathlib import Path
import pytest

from scripts.sheet_analyzer import SheetAnalyzer
from scripts.scope_diff import (
    compute_change_set,
    ChangeSet,
    RoomChange,
    AmbiguousItem,
    AmbiguousRoom,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sheet_sample.json"


@pytest.fixture
def analyzer():
    return SheetAnalyzer(json.loads(FIXTURE.read_text()))


class TestDeleteNonScopeRooms:
    def test_unmentioned_rooms_deleted(self, analyzer):
        # Scope: Hall Bathroom only. Kitchen/Bar should be deleted.
        scope = {"Hall Bathroom": ["Faucet", "Toilet"]}
        cs = compute_change_set(analyzer, scope)
        deleted_room_names = {rc.room_name for rc in cs.rooms_to_delete}
        assert "Kitchen/Bar" in deleted_room_names
        assert "Hall Bathroom" not in deleted_room_names

    def test_everywhere_section_never_deleted(self, analyzer):
        scope = {}  # empty scope
        cs = compute_change_set(analyzer, scope)
        deleted_room_names = {rc.room_name for rc in cs.rooms_to_delete}
        assert "Everywhere (in scope)" not in deleted_room_names


class TestDeleteNonScopeItemsInKeptRoom:
    def test_items_not_in_scope_deleted(self, analyzer):
        # Hall Bathroom in fixture has: Faucet, Sink, Toilet, Bathroom Accessories.
        # Scope keeps only Faucet + Toilet. Sink (and Bathroom Accessories) should be deleted.
        scope = {"Hall Bathroom": ["Faucet", "Toilet"]}
        cs = compute_change_set(analyzer, scope)
        hb = next(rc for rc in cs.rooms_to_keep if rc.room_name == "Hall Bathroom")
        deleted_desc = {r.description for r in hb.rows_to_delete}
        assert "Sink" in deleted_desc
        assert "Faucet" not in deleted_desc

    def test_kept_items_listed(self, analyzer):
        scope = {"Hall Bathroom": ["Faucet", "Toilet"]}
        cs = compute_change_set(analyzer, scope)
        hb = next(rc for rc in cs.rooms_to_keep if rc.room_name == "Hall Bathroom")
        kept_desc = {r.description for r in hb.rows_to_keep}
        assert "Faucet" in kept_desc
        assert "Toilet" in kept_desc


class TestAmbiguous:
    def test_new_item_in_known_room_is_ambiguous(self, analyzer):
        # "Heated Towel Rack" doesn't exist in the Hall Bathroom template (fixture).
        scope = {"Hall Bathroom": ["Faucet", "Heated Towel Rack"]}
        cs = compute_change_set(analyzer, scope)
        ambig_names = {ai.item_name for ai in cs.ambiguous_items}
        assert "Heated Towel Rack" in ambig_names

    def test_new_room_is_ambiguous(self, analyzer):
        # "Nursery" doesn't exist in the template.
        scope = {"Nursery": ["Flooring"]}
        cs = compute_change_set(analyzer, scope)
        ambig_room_names = {ar.room_name for ar in cs.ambiguous_rooms}
        assert "Nursery" in ambig_room_names
