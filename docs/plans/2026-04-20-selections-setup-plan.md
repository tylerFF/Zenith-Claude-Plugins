# Selections Sheet Setup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `zenith-selections` Claude Code plugin that tailors a per-project copy of the Zenith master selections template based on a designer's free-form description.

**Architecture:** A Claude Code skill (`SKILL.md`) drives the user-facing flow; discrete Python helpers handle parsing, API calls, diffing, and the master-template safety check. Tests use pytest against the helpers. The skill runs on designer laptops (Windows), invoking helpers via `python3`.

**Tech Stack:**
- Claude Code plugin marketplace (GitHub repo `tylerFF/Zenith-Claude-Plugins`)
- Python 3 (stdlib only — `urllib.request`, `json`, `re`)
- pytest (dev-only, for helper tests)
- 1Password CLI (`op`) for runtime token fetch
- Smartsheet REST API v2

**Reference spec:** `docs/specs/2026-04-20-selections-setup-design.md`

**Note on worktrees:** Brainstorming would normally create a worktree; we're working on `main` directly because the repo is fresh and has no conflicting in-flight work.

---

## File structure

Everything below is relative to the repo root `/Users/Tyler/Documents/GitHub/Zenith-Cluade-Plugins/`.

```
.claude-plugin/
  marketplace.json                                [Phase 0]
plugins/
  zenith-selections/
    .claude-plugin/
      plugin.json                                 [Phase 0]
    skills/
      setup-selections-sheet/
        SKILL.md                                  [Phase 4]
        scripts/
          __init__.py                             [Phase 1]
          url_parser.py                           [Phase 1]
          master_guard.py                         [Phase 2]
          smartsheet_client.py                    [Phase 3]
          sheet_analyzer.py                       [Phase 3]
          scope_diff.py                           [Phase 3]
          snapshot.py                             [Phase 3]
        tests/
          __init__.py                             [Phase 1]
          test_url_parser.py                      [Phase 1]
          test_master_guard.py                    [Phase 2]
          test_sheet_analyzer.py                  [Phase 3]
          test_scope_diff.py                      [Phase 3]
          test_snapshot.py                        [Phase 3]
        pytest.ini                                [Phase 1]
scripts/
  zenith-claude-setup.ps1.template                [Phase 5]
README.md                                         [Phase 0]
.gitignore                                        [Phase 0]
```

The Python helpers are split by responsibility:
- `url_parser.py` — pure string manipulation, no network
- `master_guard.py` — hardcoded master IDs + phrase detection
- `smartsheet_client.py` — thin wrapper around Smartsheet REST v2
- `sheet_analyzer.py` — given a fetched sheet JSON, computes top-level rooms, descendants, etc.
- `scope_diff.py` — given a sheet analysis + parsed scope, computes the change set
- `snapshot.py` — serialize/deserialize sheet state for undo

Each is under 150 lines. Claude reasons better about focused files.

---

## Phase 0 — Repo scaffolding (no code, just manifests)

### Task 0.1: Add `.gitignore` and `README.md`

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
*.egg-info/

# Secrets — never commit
zenith-claude-setup.ps1
*.env
.env
.env.*
!*.env.example

# OS
.DS_Store
Thumbs.db

# Editors
.vscode/
.idea/
```

- [ ] **Step 2: Write `README.md`**

```markdown
# Zenith Claude Plugins

Internal Claude Code plugin marketplace for Zenith Design + Build.

## For designers

One-time setup (your manager sends you a PowerShell script). After that, install any plugin from this marketplace with:

```
/plugin marketplace add tylerFF/Zenith-Claude-Plugins
/plugin install <plugin-name>
```

## Available plugins

- **zenith-selections** — Set up a Smartsheet selections sheet for a new project from a free-form scope description.

## For developers

See `CLAUDE.md` for repo orientation and `docs/` for design specs and implementation plans.
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore README.md
git commit -m "chore: add .gitignore and README"
```

---

### Task 0.2: Create marketplace manifest

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Verify the current Claude Code plugin marketplace schema**

Before writing the manifest, check the current schema. Run:

```bash
claude --help 2>&1 | grep -iE "plugin|marketplace" | head -20
```

Also consult: `https://docs.claude.com/en/docs/claude-code/plugins` (WebFetch it if needed). The marketplace JSON format has stabilized, but verify field names (`name`, `version`, `plugins`, etc.) against current docs before writing.

- [ ] **Step 2: Write `.claude-plugin/marketplace.json`**

Use the verified schema. Expected shape (verify before committing):

```json
{
  "name": "zenith-claude-plugins",
  "owner": {
    "name": "Zenith Design + Build",
    "url": "https://github.com/tylerFF/Zenith-Claude-Plugins"
  },
  "plugins": [
    {
      "name": "zenith-selections",
      "source": "./plugins/zenith-selections",
      "description": "Tailor a per-project Smartsheet selections sheet from a free-form scope description."
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add marketplace manifest with zenith-selections entry"
```

---

### Task 0.3: Create plugin manifest

**Files:**
- Create: `plugins/zenith-selections/.claude-plugin/plugin.json`

- [ ] **Step 1: Write the plugin manifest**

Use the verified schema from Task 0.2's doc check. Expected shape:

```json
{
  "name": "zenith-selections",
  "version": "0.1.0",
  "description": "Tailor a per-project Smartsheet selections sheet from a free-form scope description.",
  "author": "Zenith Design + Build"
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/zenith-selections/.claude-plugin/plugin.json
git commit -m "feat: add zenith-selections plugin manifest"
```

---

## Phase 1 — URL parsing helper (first TDD cycle)

The Python helpers start here. This is intentionally the smallest possible helper — it establishes the test pattern we'll follow for the rest.

### Task 1.1: Set up Python test scaffolding

**Files:**
- Create: `plugins/zenith-selections/skills/setup-selections-sheet/scripts/__init__.py` (empty)
- Create: `plugins/zenith-selections/skills/setup-selections-sheet/tests/__init__.py` (empty)
- Create: `plugins/zenith-selections/skills/setup-selections-sheet/pytest.ini`

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
touch plugins/zenith-selections/skills/setup-selections-sheet/scripts/__init__.py
touch plugins/zenith-selections/skills/setup-selections-sheet/tests/__init__.py
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 3: Verify pytest picks it up**

```bash
cd plugins/zenith-selections/skills/setup-selections-sheet
pytest --collect-only
```

Expected: "no tests ran" (no test files yet, but pytest config loaded without errors).

- [ ] **Step 4: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/__init__.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/__init__.py \
        plugins/zenith-selections/skills/setup-selections-sheet/pytest.ini
git commit -m "chore: scaffold Python test structure for setup-selections-sheet skill"
```

---

### Task 1.2: URL parser — extract sheet ID from URL or accept bare ID

**Responsibility:** `url_parser.py` takes a string that's either a Smartsheet URL (permalink form) or a bare numeric sheet ID, and returns the bare numeric ID. Network-free. Does NOT resolve permalink IDs — that requires an API call, handled in `smartsheet_client.py`.

**Files:**
- Create: `scripts/url_parser.py`
- Create: `tests/test_url_parser.py`

- [ ] **Step 1: Write the failing tests**

File: `tests/test_url_parser.py`

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd plugins/zenith-selections/skills/setup-selections-sheet
pytest tests/test_url_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.url_parser'` or similar.

- [ ] **Step 3: Write the minimal implementation**

File: `scripts/url_parser.py`

```python
"""Parse Smartsheet sheet references (URLs or bare numeric IDs)."""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SheetReference:
    """A parsed sheet reference.

    kind="numeric" means `value` is the Smartsheet numeric sheet ID.
    kind="permalink" means `value` is the permalink slug (e.g. "jWXQ3...").
                      Needs to be resolved to a numeric ID via the API.
    """
    kind: Literal["numeric", "permalink"]
    value: str


# Permalink slugs are long base58-ish strings (letters + digits).
# Numeric IDs are 16-20 digit integers.
_PERMALINK_RE = re.compile(r"/sheets/([A-Za-z0-9]{20,})")
_NUMERIC_RE = re.compile(r"^\d{10,}$")


def parse_sheet_reference(raw: str) -> SheetReference:
    """Return a SheetReference from a URL or bare numeric ID.

    Raises ValueError with a designer-friendly message on malformed input.
    """
    if not raw or not raw.strip():
        raise ValueError("Sheet reference is empty. Paste the Smartsheet URL.")

    s = raw.strip()

    # Try numeric first (most common for automation)
    if _NUMERIC_RE.match(s):
        return SheetReference(kind="numeric", value=s)

    # Try permalink URL
    m = _PERMALINK_RE.search(s)
    if m:
        return SheetReference(kind="permalink", value=m.group(1))

    raise ValueError(
        f"That doesn't look like a Smartsheet sheet reference: {s!r}. "
        "Paste the URL from the browser when viewing the sheet in grid view, "
        "or a bare numeric sheet ID."
    )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_url_parser.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/url_parser.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_url_parser.py
git commit -m "feat(selections): parse sheet URL and numeric ID references"
```

---

## Phase 2 — Master template guard (security-critical)

### Task 2.1: Master template guard

**Responsibility:** `master_guard.py` holds the hardcoded master template identifiers. Given a sheet's numeric ID and the designer's message text, it decides whether to allow the skill to proceed, abort, or proceed-with-banner.

**Files:**
- Create: `scripts/master_guard.py`
- Create: `tests/test_master_guard.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_master_guard.py`

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_master_guard.py -v
```

Expected: all tests FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

File: `scripts/master_guard.py`

```python
"""Master template safety guard.

The Zenith master selections template must never be edited by default.
If a designer's URL resolves to the master's sheet ID, the skill aborts
unless the designer's message contains the exact phrase `MASTER EDIT`.
"""

import re
from dataclasses import dataclass
from typing import Optional, Union


# Hardcoded identifiers for the Zenith master selections template.
# Source: resolved from permalink 6jh54C2xRQ8fwcQWp6Q8hXP8cxMqrcJp5rmX63x1
# via Smartsheet API on 2026-04-20.
MASTER_TEMPLATE_SHEET_ID: int = 8909191432693636
MASTER_TEMPLATE_NAME: str = "Job# - Name Selections"

# Exact phrase required to authorize editing the master.
# Case-sensitive. Must be a whole-word match.
MASTER_EDIT_PHRASE: str = "MASTER EDIT"

# Word-boundary regex for exact phrase detection.
_MASTER_EDIT_RE = re.compile(r"\bMASTER EDIT\b")


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: Optional[str] = None
    banner: Optional[str] = None


def is_master_template(sheet_id: Union[str, int]) -> bool:
    """True if the given sheet ID is the Zenith master selections template."""
    try:
        return int(sheet_id) == MASTER_TEMPLATE_SHEET_ID
    except (ValueError, TypeError):
        return False


def check_master_guard(sheet_id: Union[str, int], designer_message: str) -> GuardResult:
    """Decide whether editing this sheet should be allowed.

    - Non-master sheet: always allowed.
    - Master sheet without MASTER_EDIT_PHRASE in designer_message: blocked.
    - Master sheet with MASTER_EDIT_PHRASE: allowed, with banner.
    """
    if not is_master_template(sheet_id):
        return GuardResult(allowed=True)

    if _MASTER_EDIT_RE.search(designer_message or ""):
        banner = (
            "\u26a0\ufe0f You are editing the MASTER TEMPLATE "
            f"(`{MASTER_TEMPLATE_NAME}`). "
            "Changes will affect all future project copies."
        )
        return GuardResult(allowed=True, banner=banner)

    reason = (
        f"This is the Master Template (`{MASTER_TEMPLATE_NAME}`). "
        "The skill won't edit it by default. "
        f"If you're sure, include the phrase `{MASTER_EDIT_PHRASE}` in your message. "
        "More likely: you want a per-project copy. In Smartsheet, right-click "
        "the master, choose 'Save as New', rename it, and paste that URL instead."
    )
    return GuardResult(allowed=False, reason=reason)
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_master_guard.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/master_guard.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_master_guard.py
git commit -m "feat(selections): master template guard with MASTER EDIT phrase check"
```

---

## Phase 3 — Smartsheet client, sheet analyzer, scope diff, snapshot

These four helpers depend on each other but each has a focused responsibility. Build them in order.

### Task 3.1: Smartsheet API client

**Responsibility:** `smartsheet_client.py` wraps the Smartsheet REST API. Functions:
- `get_smartsheet_token_from_1password() -> str` — runs `op read ...`
- `list_sheets(token) -> list[dict]` — for resolving permalink → numeric ID
- `get_sheet(token, sheet_id) -> dict` — full sheet contents
- `delete_rows(token, sheet_id, row_ids) -> int` — batched, returns count deleted
- `add_rows(token, sheet_id, rows) -> list[int]` — returns new row IDs
- `resolve_permalink(token, permalink_slug) -> int` — list sheets, match permalink, return numeric ID

Network code is hard to test without mocks. Use `unittest.mock.patch` on `urllib.request.urlopen` for tests.

**Files:**
- Create: `scripts/smartsheet_client.py`
- Create: `tests/test_smartsheet_client.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_smartsheet_client.py`

```python
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
        # Simulate 700 rows → 3 batches at size 300
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_smartsheet_client.py -v
```

Expected: all tests FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

File: `scripts/smartsheet_client.py`

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_smartsheet_client.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/smartsheet_client.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_smartsheet_client.py
git commit -m "feat(selections): Smartsheet API client with batched delete/add"
```

---

### Task 3.2: Sheet analyzer

**Responsibility:** `sheet_analyzer.py` consumes a sheet JSON (from `get_sheet`) and exposes structural queries: list top-level rooms, get all descendants of a row, find the "Everywhere (in scope)" section, verify the sheet looks like a selections template.

**Files:**
- Create: `scripts/sheet_analyzer.py`
- Create: `tests/test_sheet_analyzer.py`

- [ ] **Step 1: Create a fixture file** (saves repeating large JSON in tests)

File: `tests/fixtures/sheet_sample.json`

Build a minimal but realistic sheet JSON matching what we saw earlier: columns include Category/Location/Description, some rooms at the top level (Everywhere, Hall Bathroom, Kitchen/Bar), each with a handful of children. Use `mkdir -p tests/fixtures` and write ~60 lines of JSON.

The fixture should contain at least:
- 2-3 columns (with IDs)
- 1 "Everywhere (in scope)" top-level row
- 2 room top-level rows (e.g., "Hall Bathroom", "Kitchen/Bar")
- 3-4 child rows per room
- A 2-level descendant (e.g., "Bathroom Accessories" sub-parent under Hall Bathroom with 2 children)

- [ ] **Step 2: Write failing tests**

File: `tests/test_sheet_analyzer.py`

```python
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
        # If "Bathroom Accessories" is a sub-parent with children,
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

    def test_everywhere_descendants_are_protected(self, sheet):
        a = SheetAnalyzer(sheet)
        assert a.is_in_everywhere_section(a.find_room_by_description("Everywhere (in scope)").id) is False  # parent itself
        # Children of Everywhere should be detected as "in Everywhere"
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
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
pytest tests/test_sheet_analyzer.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Write the implementation**

File: `scripts/sheet_analyzer.py`

```python
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
```

- [ ] **Step 5: Run tests, verify they pass**

```bash
pytest tests/test_sheet_analyzer.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/sheet_analyzer.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_sheet_analyzer.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/fixtures/sheet_sample.json
git commit -m "feat(selections): sheet analyzer for structural queries"
```

---

### Task 3.3: Scope diff

**Responsibility:** `scope_diff.py` takes a `SheetAnalyzer` and a parsed scope `{room_name: [item_names]}` and produces a `ChangeSet` describing what to delete, what to keep, and what's ambiguous (rooms/items not in the template).

**Files:**
- Create: `scripts/scope_diff.py`
- Create: `tests/test_scope_diff.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_scope_diff.py`

```python
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
        # Hall Bathroom has Faucet, Sink, Toilet, ... in fixture.
        # Scope keeps only Faucet + Toilet. Sink should be deleted.
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
        # "Heated Towel Rack" doesn't exist in the Hall Bathroom template.
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_scope_diff.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

File: `scripts/scope_diff.py`

```python
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

    # Direct children of this room
    children = analyzer.descendants(room.id)
    # We operate on direct children only for keep/delete decisions;
    # grandchildren ride along with their parent.
    direct_children = [r for r in children if r.parent_id == room.id]

    scope_items_remaining = list(scope_items)
    for child in direct_children:
        # Simple case-insensitive substring match for kept items.
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

    # Scope items that didn't match any template child → ambiguous
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_scope_diff.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/scope_diff.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_scope_diff.py
git commit -m "feat(selections): compute change set from scope and sheet structure"
```

---

### Task 3.4: Snapshot + restore

**Responsibility:** `snapshot.py` has `snapshot_sheet(analyzer) -> Snapshot` and `restore_rows(token, sheet_id, snapshot, row_ids_to_restore)`. A Snapshot is a JSON-serializable object capturing full row state at snapshot time.

**Files:**
- Create: `scripts/snapshot.py`
- Create: `tests/test_snapshot.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_snapshot.py`

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_snapshot.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

File: `scripts/snapshot.py`

```python
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
    # BFS from each root, emitting parents before children
    for root_id in root_row_ids:
        stack: List[RowSnapshot] = [r for r in snapshot.rows if r.id == root_id]
        while stack:
            current = stack.pop(0)
            out.append({
                "_original_id": current.id,
                "_original_parent_id": current.parent_id,
                "cells": current.cells,
                "toBottom": True,  # default placement; caller can override
            })
            # Enqueue children in original row-number order
            children = sorted(by_parent.get(current.id, []), key=lambda r: r.row_number)
            stack[0:0] = children  # prepend (BFS would use append; we want depth-first parent-first)

    return out
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_snapshot.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/scripts/snapshot.py \
        plugins/zenith-selections/skills/setup-selections-sheet/tests/test_snapshot.py
git commit -m "feat(selections): snapshot + rows-for-restore helpers"
```

---

## Phase 4 — The SKILL.md

### Task 4.1: Write the SKILL.md

**Responsibility:** `SKILL.md` is the main entry point. Claude reads it when the skill is triggered. It orchestrates: pre-flight → master guard → fetch → snapshot → parse scope → diff → ask about ambiguous → execute → report.

**Files:**
- Create: `plugins/zenith-selections/skills/setup-selections-sheet/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

(File is ~200 lines. See `SKILL.md` template below.)

File: `plugins/zenith-selections/skills/setup-selections-sheet/SKILL.md`

```markdown
---
name: setup-selections-sheet
description: |
  Use when a designer wants to set up a Smartsheet selections sheet for a new
  Zenith project. They will provide (a) a Smartsheet URL pointing at a fresh
  per-project copy of the master template, and (b) a free-form description of
  what's in scope for this project. The skill trims the copy down to only the
  rooms and items mentioned, adds anything new (after confirming), and leaves
  a session-scoped undo buffer.
---

# Setup Selections Sheet

You are helping a Zenith designer tailor a per-project copy of the master
selections template. Follow this workflow exactly.

## 0. Master template protection (runs first, always)

The master template must NEVER be edited by default. Before any other action:

1. Parse the designer's URL or ID using `scripts/url_parser.py::parse_sheet_reference`.
2. If the reference is a permalink, resolve it to a numeric ID by calling
   `scripts/smartsheet_client.py::resolve_permalink` (which requires a token —
   fetch that in step 1 of pre-flight, then come back here).
3. Run `scripts/master_guard.py::check_master_guard(sheet_id, designer_message)`.
4. If `result.allowed is False`: print `result.reason` and STOP. Do not run
   pre-flight checks, do not fetch the sheet, do not snapshot. Just stop.
5. If `result.allowed is True` and `result.banner` is not None: keep the banner
   text and prepend it to your final summary.

## 1. Pre-flight checks

Run all of these in order. First failure aborts the skill with the designer-
friendly error message. No sheet writes occur unless all checks pass.

1. **1Password reachable.** Run `op whoami`. On nonzero exit, print:
   > "1Password isn't responding. Make sure the 1Password app is running and you're signed in, then try again."
2. **Smartsheet token retrievable.** Call
   `scripts/smartsheet_client.py::get_smartsheet_token_from_1password()`. On
   failure, print the error from `SmartsheetError` and stop.
3. **URL parseable.** Already done in step 0.
4. **Sheet accessible.** Call `get_sheet(token, sheet_id)`. On `SmartsheetError`:
   > "I can't access that sheet. Make sure (a) the URL is correct, and (b) Zenith's Smartsheet automation account has Edit access to it."
5. **Looks like a selections template.** Build a `SheetAnalyzer(sheet_json)`
   and call `.looks_like_selections_template()`. On False:
   > "This sheet doesn't look like a standard selections template. Double-check the URL. If it is the right sheet, message Tyler so we can investigate."

## 2. Snapshot the current state

Call `scripts/snapshot.py::snapshot_sheet(analyzer)` and hold the result in the
conversation. You'll use it for undo/restore. Write the snapshot as a JSON
block in your reply, collapsed inside `<details>` tags so it doesn't clutter
the chat but is recoverable.

## 3. Parse the designer's scope

The designer's message contains a free-form description like:

> "Hall bath remodel: toilet, faucet, sink, tile floor. New kitchen: sink, faucet, countertop. Nursery build-out: flooring, paint."

Use your language understanding to extract a structured scope:

```
{
  "Hall Bathroom": ["Toilet", "Faucet", "Sink", "Tile Floor"],
  "Kitchen/Bar": ["Sink", "Faucet", "Countertop"],
  "Nursery": ["Flooring", "Paint"]
}
```

### Matching confidence

- **High confidence** (obvious aliases): proceed silently. Examples: "hall bath" → "Hall Bathroom", "kitchen" → "Kitchen/Bar", "powder room" / "half bath" → "Powder Bathroom", "exterior" / "outside" → "Exterior".
- **Uncertain match**: ask the designer before proceeding. Example: "You mentioned 'den.' The template has 'Bedroom/Living/Dining/Family/Office/Sunroom' as a catch-all — should I map 'den' there, or add a new 'Den' section?"
- **Clearly new** (no reasonable match): keep the original name; it'll surface as an ambiguous room/item in step 4.

Don't proceed to step 4 until all uncertain matches are resolved.

## 4. Compute the change set

Call `scripts/scope_diff.py::compute_change_set(analyzer, scope)`. Inspect the
result:

- `rooms_to_delete`: full top-level rooms that will be wiped.
- `rooms_to_keep`: rooms staying, with kept items and items to delete under each.
- `ambiguous_items`: items in scope that aren't in the template for their room.
- `ambiguous_rooms`: whole rooms mentioned that aren't in the template.

## 5. Ask about ambiguous items and rooms, one at a time

For each `AmbiguousItem`:
> "'{item_name}' isn't in the {room_name} template. Want me to add it? If yes, what category — `16 ACCESSORIES:Material`, `09 PLUMBING:Material`, or something else?"

For each `AmbiguousRoom`:
> "'{room_name}' isn't in the template. Want me to add it as a new top-level section with these items: {items_list}?"

Record the designer's answers. These become rows-to-add in step 6.

## 6. Execute writes

**Deletes first, then adds.** Do not interleave.

1. Collect all row IDs from `rooms_to_delete` (all descendants) and from
   `rooms_to_keep[*].rows_to_delete`. Call
   `smartsheet_client.delete_rows(token, sheet_id, row_ids)`.
2. Build row payloads for confirmed new items/rooms (from step 5 answers)
   and call `smartsheet_client.add_rows(token, sheet_id, new_rows)`.

### Partial failure

If any batch raises `SmartsheetError`, stop immediately. Do not continue. Report:

> "I deleted X rows, then a Smartsheet error stopped me: {error}. The rest is untouched. You can re-run the skill or say 'undo' to restore what I deleted."

## 7. Report

Print a structured summary:

```
{Project name if mentioned} setup complete.

Matched to template:
  "hall bath" -> Hall Bathroom
  "kitchen"   -> Kitchen/Bar

Kept (in scope):
  Hall Bathroom: Faucet, Sink, Toilet, Tile Floor
  Kitchen/Bar:   Sink, Faucet, Countertop

Added (new):
  Hall Bathroom: Heated Towel Rack  [16 ACCESSORIES:Material]
  Nursery (new top-level): Flooring, Paint

Deleted (out of scope):
  Master Bathroom, Powder Bathroom, Mudroom/Laundry, ...
  Total: N sections, M rows

Session snapshot saved. Say "undo" or "restore [room]" to revert.
```

If the master guard banner was set, prepend it to this output.

## Undo / restore

If the designer says "undo" or "restore [room]" in the SAME session:

1. Recall the `Snapshot` from step 2.
2. For "undo everything": re-add all deleted rows via
   `scripts/snapshot.py::rows_for_restore(snapshot, [all_deleted_root_ids])` +
   `smartsheet_client.add_rows`. Also delete any rows the skill added in step 6.
3. For "restore [room]": scope the rows_for_restore call to just that room's
   original ID.

Row IDs will change on restore; this is documented and expected.

## If the session ends

The snapshot is lost. Tell the designer to get a fresh template copy from the
PM and re-run the skill. The master template is never touched, so a fresh copy
is always available.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/zenith-selections/skills/setup-selections-sheet/SKILL.md
git commit -m "feat(selections): add SKILL.md driving the setup flow"
```

---

## Phase 5 — Designer install script

### Task 5.1: Windows setup script template

**Responsibility:** The PowerShell script a designer runs once on their Windows laptop. It installs `op` CLI, Python 3, saves the service account token, and registers the plugin marketplace.

The actual token goes in a `.ps1` *copy* made on Tyler's Mac (token pasted in, git-ignored). The template in the repo has a placeholder.

**Files:**
- Create: `scripts/zenith-claude-setup.ps1.template`

- [ ] **Step 1: Write the template**

File: `scripts/zenith-claude-setup.ps1.template`

```powershell
# Zenith Claude Code + 1Password + Plugin Marketplace setup (Windows)
#
# BEFORE SENDING TO A DESIGNER:
#   1. Copy this file to `zenith-claude-setup.ps1` (without .template).
#   2. Paste the 1Password service account token where it says REPLACE_ME.
#   3. DM the .ps1 file to the designer (never commit the copy).
#
# Designer usage: right-click the .ps1 file in Explorer -> Run with PowerShell.

$ErrorActionPreference = "Stop"

# ============ TYLER EDITS THIS LINE ============
$ServiceAccountToken = "ops_REPLACE_ME"
# ===============================================

$MarketplaceRepo = "tylerFF/Zenith-Claude-Plugins"

function Section($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }
function Ok($m)      { Write-Host "[OK]  $m" -ForegroundColor Green }
function Warn($m)    { Write-Host "[!!]  $m" -ForegroundColor Yellow }
function Die($m)     { Write-Host "[ERR] $m" -ForegroundColor Red; exit 1 }

if ($ServiceAccountToken -eq "ops_REPLACE_ME" -or [string]::IsNullOrWhiteSpace($ServiceAccountToken)) {
    Die "No token embedded. Request an updated copy of this script from Tyler."
}

# --- 1. winget sanity ---
Section "Checking winget"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Die "winget not available. Update Windows or install App Installer from Microsoft Store."
}

# --- 2. 1Password CLI ---
Section "Installing 1Password CLI (op)"
if (-not (Get-Command op -ErrorAction SilentlyContinue)) {
    winget install --id AgileBits.1Password.CLI -e --silent `
        --accept-source-agreements --accept-package-agreements
}
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path","User")
if (-not (Get-Command op -ErrorAction SilentlyContinue)) {
    Die "op CLI install completed but binary not on PATH. Restart PowerShell and re-run."
}
Ok "op $(op --version)"

# --- 3. Python 3 ---
Section "Installing Python 3"
if (-not (Get-Command python3 -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    winget install --id Python.Python.3.12 -e --silent `
        --accept-source-agreements --accept-package-agreements
}
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path","User")
$py = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { Die "Python install completed but binary not on PATH. Restart PowerShell and re-run." }
Ok "Python $((& $py.Source --version).Split()[-1])"

# --- 4. Claude Code sanity check ---
Section "Checking Claude Code"
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Die "Claude Code not found. Install from https://claude.com/download then re-run."
}
Ok "Claude Code $(claude --version)"

# --- 5. Save the service account token ---
Section "Saving Zenith 1Password service account token"
[Environment]::SetEnvironmentVariable("OP_SERVICE_ACCOUNT_TOKEN", $ServiceAccountToken, "User")
$env:OP_SERVICE_ACCOUNT_TOKEN = $ServiceAccountToken
Ok "OP_SERVICE_ACCOUNT_TOKEN set (User scope, persists across reboots)"

# --- 6. Verify token ---
Section "Testing token"
$vaultsJson = & op vault list --format=json 2>&1
if ($LASTEXITCODE -ne 0) { Die "Token rejected by 1Password: $vaultsJson" }
$vaults = $vaultsJson | ConvertFrom-Json
Ok "Accessible vaults:"
$vaults | ForEach-Object { Write-Host "    - $($_.name)" }
if (-not ($vaults | Where-Object { $_.name -eq "Zenith Automations" })) {
    Warn "'Zenith Automations' is NOT in the accessible list. Service account needs read access to it."
}

# --- 7. Register the plugin marketplace in Claude Code ---
Section "Registering Zenith plugin marketplace"
# The exact CLI command varies slightly between Claude Code versions.
# Try both known forms; ignore errors on the non-matching one.
$added = $false
try {
    claude plugin marketplace add $MarketplaceRepo 2>$null
    if ($LASTEXITCODE -eq 0) { $added = $true }
} catch {}
if (-not $added) {
    try {
        claude /plugin marketplace add $MarketplaceRepo 2>$null
        if ($LASTEXITCODE -eq 0) { $added = $true }
    } catch {}
}
if ($added) {
    Ok "Marketplace registered: $MarketplaceRepo"
} else {
    Warn "Couldn't auto-register the marketplace. In Claude Code, run:  /plugin marketplace add $MarketplaceRepo"
}

# --- 8. Done ---
Section "Setup complete"
Write-Host "In Claude Code, run:" -ForegroundColor White
Write-Host "    /plugin install zenith-selections" -ForegroundColor White
Write-Host ""
Write-Host "Then ask Claude Code:" -ForegroundColor White
Write-Host '    "set up selections for my new project, here is the sheet URL ..."' -ForegroundColor White
```

- [ ] **Step 2: Commit**

```bash
git add scripts/zenith-claude-setup.ps1.template
git commit -m "feat: PowerShell setup script template for designer laptops"
```

---

## Phase 6 — Manual validation

These aren't code tasks; they're verification that the plumbing works end to end. Each produces a short report we can refer to later.

### Task 6.1: Local marketplace test (Tyler's Mac)

**Goal:** Install the plugin from your own repo on your own Mac and smoke-test it.

- [ ] **Step 1: Point your Claude Code at the marketplace**

In your Claude Code session:
```
/plugin marketplace add tylerFF/Zenith-Claude-Plugins
/plugin install zenith-selections
```

- [ ] **Step 2: Verify the skill shows up**

```
/plugin list
```
Expected: `zenith-selections` appears as installed.

- [ ] **Step 3: Try it against a SAFE test copy of the master template**

Make a fresh copy of `Job# - Name Selections` in Smartsheet (name it "TEST - delete me"). Paste its URL to Claude Code:

> "Set up selections for a test project. Here's the sheet: <URL>. Hall bath remodel: faucet, toilet, sink."

Expected:
- Master guard is NOT triggered (because the test copy has a different sheet ID).
- Pre-flight passes.
- Claude asks about any ambiguous items.
- Deletes out-of-scope rooms and extra items.
- Prints a summary matching the spec's reporting format.

- [ ] **Step 4: Try the master guard**

Paste the real master template URL into Claude Code (without `MASTER EDIT` in the message):
> "Set up a project on this sheet: https://app.smartsheet.com/sheets/6jh54C2xRQ8fwcQWp6Q8hXP8cxMqrcJp5rmX63x1"

Expected: the skill refuses, quoting the protection message from the spec.

Then include the phrase:
> "MASTER EDIT - I want to fix a typo in the master"

Expected: the skill proceeds, with the red master-edit banner in its output.

**Do not actually let the skill commit writes to the master.** Halt after the banner shows. Back out of the session.

- [ ] **Step 5: Clean up the test copy**

Delete the "TEST - delete me" sheet in Smartsheet.

- [ ] **Step 6: Record what you observed**

Add a brief note to `docs/plans/2026-04-20-selections-setup-plan.md` at the bottom describing what worked and what didn't. Commit.

---

### Task 6.2: Designer-side test (Tyler's Windows VM or a trusted designer's laptop)

**Goal:** Verify the full designer onboarding works.

- [ ] **Step 1: Prepare a designer-flavored install**

On your Mac, copy `scripts/zenith-claude-setup.ps1.template` to a new file `~/Downloads/zenith-claude-setup.ps1`, replace `ops_REPLACE_ME` with the real service account token from your Employee vault in 1Password. Do NOT commit this file.

- [ ] **Step 2: Run it on a Windows target**

Transfer the .ps1 to the Windows machine (Slack DM, USB, whatever), run it in PowerShell. Verify all sections print OK/Ok.

- [ ] **Step 3: Install and run the skill**

From Windows Claude Code:
```
/plugin install zenith-selections
```

Create another throwaway TEST copy in Smartsheet, paste its URL, run the skill with a simple scope.

- [ ] **Step 4: Record results**

Update the notes in the plan doc.

---

## Self-review (write this section once all tasks above are done)

After all phases are complete, do a fresh-eyes read:

1. **Spec coverage.** Walk through each section of `docs/specs/2026-04-20-selections-setup-design.md`; can you point to the tasks that implement it?
2. **Placeholder scan.** Any remaining TODOs, `pass`, `raise NotImplementedError`, or `# TODO` in the code? Fix.
3. **Type consistency.** Do `SheetAnalyzer`, `Snapshot`, `ChangeSet`, etc., have consistent field names across their uses in SKILL.md, tests, and scripts?
4. **Security review.** Is the master guard invoked BEFORE any network call that could reveal information about a sheet? Is the token ever logged to stdout/stderr? Is the PowerShell `.ps1` (with token) in `.gitignore`?

Fix issues inline. No separate commit ceremony — just fix and move on.

---

## Plan self-review (pre-execution)

Done by the plan author before handing off:

**1. Spec coverage:**
- ✅ User workflow (spec §1) → SKILL.md (Task 4.1)
- ✅ Architecture (spec §2) → File structure + helpers (Phase 0-3)
- ✅ Master template protection (spec §3.0) → `master_guard.py` (Task 2.1), invoked first in SKILL.md (Task 4.1)
- ✅ Pre-flight checks (spec §3.1) → SKILL.md (Task 4.1)
- ✅ Scope matching with confidence tiers (spec §3.2) → SKILL.md (Task 4.1); Python helpers produce the raw diff, Claude does the language matching
- ✅ Flag-and-ask (spec §flag-and-ask) → SKILL.md (Task 4.1)
- ✅ Write-time errors (spec §3.3) → `smartsheet_client.py` raises, SKILL.md handles partial failure
- ✅ Undo / restore (spec §3.4) → `snapshot.py` (Task 3.4), SKILL.md (Task 4.1)
- ✅ Nuclear option (spec §3.5) → SKILL.md closing text (Task 4.1)
- ✅ Reporting format (spec §reporting) → SKILL.md (Task 4.1)
- ✅ Constants (spec §constants) → `master_guard.py`, `smartsheet_client.py`
- ✅ Security (spec §security) → `.gitignore` rules (Task 0.1), PowerShell template comment (Task 5.1)

**2. Placeholder scan:** None in the plan. Every step has actual code or actual commands.

**3. Type consistency:**
- `SheetReference` (from `url_parser.py`) → used only in SKILL.md comment and tests; no mismatches.
- `GuardResult` (from `master_guard.py`) → consistent.
- `Row`, `SheetAnalyzer` → Row's fields (id, parent_id, description, etc.) used consistently in `scope_diff.py` and `snapshot.py`.
- `ChangeSet`, `RoomChange`, `RoomDeletion`, `AmbiguousItem`, `AmbiguousRoom` → defined in `scope_diff.py`, referenced in SKILL.md step 4 with matching names.
- `Snapshot`, `RowSnapshot` → defined in `snapshot.py`, referenced in SKILL.md step 2.
- `SmartsheetError` → defined in `smartsheet_client.py`, raised by multiple helpers.
