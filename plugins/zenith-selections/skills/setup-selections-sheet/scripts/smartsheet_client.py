"""Smartsheet REST API v2 client (stdlib only).

Focused surface: read a sheet, batch-delete rows, batch-add rows,
resolve permalinks to numeric IDs. Auth token is fetched from 1Password
via the `op` CLI.
"""

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Dict, Any


API_BASE = "https://api.smartsheet.com/2.0"
DELETE_BATCH_SIZE = 300  # Smartsheet's hard cap is ~450; 300 gives headroom
ONEPASSWORD_REF = "op://Zenith Automations/Smart Sheet - API Key/credential"


class SmartsheetError(RuntimeError):
    """Raised on any Smartsheet API failure or auth problem."""


def get_smartsheet_token_from_1password() -> str:
    """Fetch the Smartsheet API token from 1Password via the `op` CLI."""
    try:
        result = subprocess.run(
            ["op", "read", ONEPASSWORD_REF],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise SmartsheetError(
            "The `op` CLI is not installed. Run the Zenith setup script first."
        )
    except subprocess.TimeoutExpired:
        raise SmartsheetError("1Password `op` CLI timed out.")

    if result.returncode != 0:
        raise SmartsheetError(
            "Couldn't fetch the Smartsheet token from 1Password. "
            f"`op` said: {result.stderr.strip()}. "
            "Make sure the 1Password app is running and you're signed in."
        )
    token = result.stdout.strip()
    if not token:
        raise SmartsheetError("1Password returned an empty token.")
    return token


def _request(token: str, method: str, path: str, body: Any = None) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SmartsheetError(
            f"Smartsheet API {method} {path} failed ({e.code}): {detail[:300]}"
        )
    except urllib.error.URLError as e:
        raise SmartsheetError(f"Network error calling Smartsheet: {e}")


def list_sheets(token: str) -> List[dict]:
    result = _request(token, "GET", "/sheets?includeAll=true")
    return result.get("data", [])


def resolve_permalink(token: str, permalink_slug: str) -> int:
    """Given a permalink slug, return the numeric sheet ID."""
    sheets = list_sheets(token)
    for s in sheets:
        if permalink_slug in s.get("permalink", ""):
            return s["id"]
    raise SmartsheetError(
        f"Sheet with permalink '{permalink_slug}' not found. "
        "Make sure the automation Smartsheet account has access to it."
    )


def get_sheet(token: str, sheet_id: int) -> dict:
    """Fetch full sheet contents (rows, columns, everything)."""
    return _request(token, "GET", f"/sheets/{sheet_id}")


def delete_rows(token: str, sheet_id: int, row_ids: List[int]) -> int:
    """Batch-delete rows. Returns total count successfully deleted."""
    if not row_ids:
        return 0
    total = 0
    for i in range(0, len(row_ids), DELETE_BATCH_SIZE):
        chunk = row_ids[i : i + DELETE_BATCH_SIZE]
        qs = urllib.parse.urlencode(
            {"ids": ",".join(str(x) for x in chunk), "ignoreRowsNotFound": "true"}
        )
        result = _request(token, "DELETE", f"/sheets/{sheet_id}/rows?{qs}")
        total += len(result.get("result", []))
    return total


def add_rows(token: str, sheet_id: int, rows: List[Dict]) -> List[int]:
    """POST rows to the sheet. Returns new row IDs in order."""
    if not rows:
        return []
    result = _request(token, "POST", f"/sheets/{sheet_id}/rows", body=rows)
    return [r["id"] for r in result.get("result", [])]
