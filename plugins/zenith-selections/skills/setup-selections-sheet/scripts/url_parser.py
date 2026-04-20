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
