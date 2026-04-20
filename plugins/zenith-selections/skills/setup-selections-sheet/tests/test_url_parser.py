import pytest
from scripts.url_parser import parse_sheet_reference, SheetReference

class TestParseNumericId:
    def test_bare_numeric_id(self):
        result = parse_sheet_reference("228526784466820")
        assert result == SheetReference(kind="numeric", value="228526784466820")

    def test_numeric_id_with_whitespace(self):
        result = parse_sheet_reference("  228526784466820  ")
        assert result == SheetReference(kind="numeric", value="228526784466820")

    def test_numeric_id_rejects_too_short(self):
        with pytest.raises(ValueError, match="doesn't look like"):
            parse_sheet_reference("123")

class TestParsePermalink:
    def test_standard_grid_url(self):
        url = "https://app.smartsheet.com/sheets/jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1?view=grid"
        result = parse_sheet_reference(url)
        assert result == SheetReference(kind="permalink", value="jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1")

    def test_url_without_query_string(self):
        url = "https://app.smartsheet.com/sheets/jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1"
        result = parse_sheet_reference(url)
        assert result == SheetReference(kind="permalink", value="jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1")

    def test_url_with_trailing_slash(self):
        url = "https://app.smartsheet.com/sheets/jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1/"
        result = parse_sheet_reference(url)
        assert result == SheetReference(kind="permalink", value="jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1")

    def test_url_with_b_path_segment(self):
        # Smartsheet sometimes uses /b/home/sheets/... URLs
        url = "https://app.smartsheet.com/b/home/sheets/jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1"
        result = parse_sheet_reference(url)
        assert result == SheetReference(kind="permalink", value="jWXQ3Wgchxfx73MJqVrmMvM7hWJJwr99QpCcFhF1")

class TestParseErrors:
    def test_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            parse_sheet_reference("")

    def test_non_smartsheet_url(self):
        with pytest.raises(ValueError, match="doesn't look like"):
            parse_sheet_reference("https://docs.google.com/spreadsheets/d/abc123")

    def test_garbage_string(self):
        with pytest.raises(ValueError, match="doesn't look like"):
            parse_sheet_reference("hello world")
