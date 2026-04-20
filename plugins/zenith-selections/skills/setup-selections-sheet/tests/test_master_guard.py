import pytest
from scripts.master_guard import (
    MASTER_TEMPLATE_SHEET_ID,
    MASTER_EDIT_PHRASE,
    is_master_template,
    check_master_guard,
    GuardResult,
)

class TestIsMasterTemplate:
    def test_matches_numeric_id_as_string(self):
        assert is_master_template("8909191432693636") is True

    def test_matches_numeric_id_as_int(self):
        assert is_master_template(8909191432693636) is True

    def test_rejects_other_ids(self):
        assert is_master_template("228526784466820") is False

    def test_rejects_zero(self):
        assert is_master_template(0) is False

    def test_rejects_empty_string(self):
        assert is_master_template("") is False

class TestCheckMasterGuard:
    def test_non_master_sheet_always_allowed(self):
        result = check_master_guard(
            sheet_id="228526784466820",
            designer_message="do whatever",
        )
        assert result.allowed is True
        assert result.banner is None

    def test_master_sheet_blocked_without_phrase(self):
        result = check_master_guard(
            sheet_id="8909191432693636",
            designer_message="update the template please",
        )
        assert result.allowed is False
        assert "MASTER EDIT" in result.reason

    def test_master_sheet_allowed_with_phrase(self):
        result = check_master_guard(
            sheet_id="8909191432693636",
            designer_message="MASTER EDIT: add a new row for shower niche",
        )
        assert result.allowed is True
        assert result.banner is not None
        assert "MASTER TEMPLATE" in result.banner

    def test_phrase_is_case_sensitive(self):
        # "master edit" (lowercase) should NOT satisfy the guard.
        result = check_master_guard(
            sheet_id="8909191432693636",
            designer_message="master edit please",
        )
        assert result.allowed is False

    def test_phrase_is_exact_match_not_substring_of_word(self):
        # "REMASTER EDIT" or "MASTER EDITOR" should NOT trigger.
        # We require word-boundary match on both sides.
        result = check_master_guard(
            sheet_id="8909191432693636",
            designer_message="MASTER EDITOR should handle this",
        )
        assert result.allowed is False

    def test_phrase_embedded_mid_sentence(self):
        result = check_master_guard(
            sheet_id="8909191432693636",
            designer_message="I want to MASTER EDIT the tile section.",
        )
        assert result.allowed is True
