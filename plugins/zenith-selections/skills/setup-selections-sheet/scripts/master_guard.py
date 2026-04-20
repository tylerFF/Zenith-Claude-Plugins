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
