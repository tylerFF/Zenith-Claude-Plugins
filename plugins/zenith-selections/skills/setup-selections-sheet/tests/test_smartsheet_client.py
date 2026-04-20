import io
import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from scripts.smartsheet_client import (
    SmartsheetError,
    get_smartsheet_token_from_1password,
    resolve_permalink,
    get_sheet,
    delete_rows,
    add_rows,
)


def _mock_http_response(payload: dict, status: int = 200):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.status = status
    resp.__enter__ = lambda self: resp
    resp.__exit__ = lambda self, *args: None
    return resp


class TestGetTokenFromOnePassword:
    @patch("subprocess.run")
    def test_returns_token_on_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        token = get_smartsheet_token_from_1password()
        assert token == "abc123"
        # Verify it called `op read` with the right path
        args = mock_run.call_args[0][0]
        assert args[0] == "op"
        assert args[1] == "read"
        assert "Zenith Automations" in args[2]
        assert "Smart Sheet - API Key" in args[2]

    @patch("subprocess.run")
    def test_raises_on_op_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="not signed in"
        )
        with pytest.raises(SmartsheetError, match="1Password"):
            get_smartsheet_token_from_1password()


class TestResolvePermalink:
    @patch("urllib.request.urlopen")
    def test_finds_matching_sheet(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response({
            "data": [
                {"id": 111, "permalink": "https://app.smartsheet.com/sheets/aaa"},
                {"id": 222, "permalink": "https://app.smartsheet.com/sheets/bbb"},
            ]
        })
        result = resolve_permalink("tok", "bbb")
        assert result == 222

    @patch("urllib.request.urlopen")
    def test_raises_when_not_found(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response({"data": []})
        with pytest.raises(SmartsheetError, match="not found"):
            resolve_permalink("tok", "missing")


class TestGetSheet:
    @patch("urllib.request.urlopen")
    def test_returns_sheet_json(self, mock_urlopen):
        expected = {"id": 123, "name": "Test", "rows": []}
        mock_urlopen.return_value = _mock_http_response(expected)
        result = get_sheet("tok", 123)
        assert result == expected


class TestDeleteRows:
    @patch("urllib.request.urlopen")
    def test_batches_ids_under_limit(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response({"result": [1, 2, 3]})
        count = delete_rows("tok", 123, [1, 2, 3])
        assert count == 3
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_splits_into_multiple_batches(self, mock_urlopen):
        # Simulate 700 rows -> 3 batches at size 300
        mock_urlopen.side_effect = [
            _mock_http_response({"result": list(range(300))}),
            _mock_http_response({"result": list(range(300))}),
            _mock_http_response({"result": list(range(100))}),
        ]
        row_ids = list(range(700))
        count = delete_rows("tok", 123, row_ids)
        assert count == 700
        assert mock_urlopen.call_count == 3


class TestAddRows:
    @patch("urllib.request.urlopen")
    def test_returns_new_row_ids(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response({
            "result": [{"id": 111}, {"id": 222}]
        })
        new_ids = add_rows("tok", 123, [{"cells": []}, {"cells": []}])
        assert new_ids == [111, 222]
