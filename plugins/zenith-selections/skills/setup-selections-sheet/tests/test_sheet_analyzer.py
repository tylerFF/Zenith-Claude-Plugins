import json
from pathlib import Path
import pytest

from scripts.sheet_analyzer import (
    SheetAnalyzer,
    TEMPLATE_ROOM_NAMES,
    EVERYWHERE_SECTION_NAME,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sheet_sample.json"


@pytest.fixture
def sheet():
    return json.loads(FIXTURE.read_text())


class TestTopLevelRooms:
    def test_returns_all_top_level(self, sheet):
        a = SheetAnalyzer(sheet)
        names = [r.description for r in a.top_level_rooms()]
        assert "Hall Bathroom" in names
        assert "Kitchen/Bar" in names
        assert "Everywhere (in scope)" in names

    def test_excludes_children(self, sheet):
        # Child rows should NOT appear as "top level"
        a = SheetAnalyzer(sheet)
        names = [r.description for r in a.top_level_rooms()]
        assert "Faucet" not in names
        assert "Toilet" not in names


class TestDescendants:
    def test_direct_children(self, sheet):
        a = SheetAnalyzer(sheet)
        hall_bath = a.find_room_by_description("Hall Bathroom")
        assert hall_bath is not None
        descendants = a.descendants(hall_bath.id)
        desc_names = [r.description for r in descendants]
        assert "Faucet" in desc_names

    def test_includes_grandchildren(self, sheet):
        # "Bathroom Accessories" sub-parent has its own children (e.g., towel bar).
        # descendants() of Hall Bathroom should include those grandchildren.
        a = SheetAnalyzer(sheet)
        hall_bath = a.find_room_by_description("Hall Bathroom")
        descendants = a.descendants(hall_bath.id)
        desc_names = [r.description for r in descendants]
        assert any("Towel Bar" in n for n in desc_names)


class TestEverywhereSection:
    def test_finds_everywhere_section(self, sheet):
        a = SheetAnalyzer(sheet)
        everywhere = a.find_room_by_description(EVERYWHERE_SECTION_NAME)
        assert everywhere is not None

    def test_everywhere_parent_itself_not_flagged(self, sheet):
        a = SheetAnalyzer(sheet)
        ev = a.find_room_by_description(EVERYWHERE_SECTION_NAME)
        # The Everywhere PARENT row itself is not a descendant of itself
        assert a.is_in_everywhere_section(ev.id) is False

    def test_everywhere_descendants_are_flagged(self, sheet):
        # The fixture should have at least one child under Everywhere to exercise this.
        # If your fixture doesn't, add one.
        a = SheetAnalyzer(sheet)
        ev = a.find_room_by_description(EVERYWHERE_SECTION_NAME)
        for child in a.descendants(ev.id):
            assert a.is_in_everywhere_section(child.id) is True


class TestTemplateSanity:
    def test_accepts_valid_template(self, sheet):
        a = SheetAnalyzer(sheet)
        # At least one top-level room name matches the known template set
        assert a.looks_like_selections_template() is True

    def test_rejects_empty_sheet(self):
        empty = {"id": 1, "name": "Empty", "columns": [], "rows": []}
        a = SheetAnalyzer(empty)
        assert a.looks_like_selections_template() is False

    def test_rejects_unrelated_sheet(self):
        unrelated = {
            "id": 1, "name": "Budget", "columns": [],
            "rows": [
                {"id": 1, "rowNumber": 1, "cells": []},
            ],
        }
        a = SheetAnalyzer(unrelated)
        assert a.looks_like_selections_template() is False
