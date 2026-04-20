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

## Setup: where the Python helpers live

All Python helpers for this skill live alongside this SKILL.md in a `scripts/`
directory. Run them with `python3` (macOS/Linux) or `python` (Windows — the binary is registered as `python`, not `python3`, by the Windows installer). Prefer the absolute path if in doubt: `python3 "$CLAUDE_PLUGIN_DIR/scripts/<name>.py"` on Unix, or use whatever Python executable is on PATH on Windows. The skill's files are:

- `scripts/url_parser.py` — parse URLs/IDs
- `scripts/master_guard.py` — master template safety check
- `scripts/smartsheet_client.py` — Smartsheet API wrapper
- `scripts/sheet_analyzer.py` — structural queries over sheet JSON
- `scripts/scope_diff.py` — compute change set from scope
- `scripts/snapshot.py` — snapshot + restore helpers

All helpers are stdlib-only. No pip install needed at runtime.

## 0. Master template protection (runs FIRST, always)

The master template must NEVER be edited by default. Before any other action:

1. Parse the designer's URL or ID using `url_parser.parse_sheet_reference`.
2. **If `reference.kind == "numeric"`**: immediately run `master_guard.check_master_guard(reference.value, designer_message)`. If `result.allowed is False`: print `result.reason` verbatim and STOP. No token fetch, no sheet fetch, no snapshot. If allowed, proceed to step 3 knowing the sheet_id is `reference.value`.
3. **If `reference.kind == "permalink"`**: fetch the Smartsheet token via `smartsheet_client.get_smartsheet_token_from_1password()`. Then call `smartsheet_client.resolve_permalink(token, reference.value)` to get the numeric ID. THEN run `master_guard.check_master_guard(numeric_id, designer_message)`. Same stop behavior on `allowed is False`.
4. If the guard passed with a banner (`result.banner is not None`): keep the banner text and prepend it to your final summary.

## 1. Pre-flight checks

Run in order. First failure aborts with the designer-friendly error message.

1. **1Password reachable.** Run `op whoami`. On nonzero exit:
   > "1Password isn't responding. Make sure the 1Password app is running and you're signed in, then try again."
2. **Smartsheet token retrievable.** Already fetched in step 0. If that raised `SmartsheetError`, the message is already clear — print it and stop.
3. **URL parseable.** Already done in step 0.
4. **Sheet accessible.** Call `smartsheet_client.get_sheet(token, sheet_id)`. On `SmartsheetError`:
   > "I can't access that sheet. Make sure (a) the URL is correct, and (b) Zenith's Smartsheet automation account has Edit access to it."
5. **Looks like a selections template.** Build a `sheet_analyzer.SheetAnalyzer(sheet_json)` and call `.looks_like_selections_template()`. On False:
   > "This sheet doesn't look like a standard selections template. Double-check the URL. If it is the right sheet, message Tyler so we can investigate."

## 2. Snapshot the current state

Call `snapshot.snapshot_sheet(analyzer)` and hold the result in the conversation.
You'll use it for undo/restore. Emit the snapshot as a JSON block in your reply,
wrapped in `<details>` tags so it doesn't clutter the chat but is recoverable:

```html
<details>
<summary>Pre-change snapshot (for undo)</summary>

<pre><code class="language-json">
{...snapshot_dict...}
</code></pre>

</details>
```

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

Call `scope_diff.compute_change_set(analyzer, scope)`. Inspect the result:

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

1. Collect all row IDs to delete:
   - From `rooms_to_delete[*].all_descendant_ids` plus the room's own ID
   - From `rooms_to_keep[*].rows_to_delete` (direct children to remove, plus the grandchildren that already cascaded into that list)

2. Call `smartsheet_client.delete_rows(token, sheet_id, row_ids)`.

3. Build row payloads for confirmed new items/rooms (from step 5 answers). For a new room, add the parent row first and remember its new ID, then add children with `parentId` set to the new parent's ID. For a new item in an existing room, add directly under that room's ID.

4. Call `smartsheet_client.add_rows(token, sheet_id, new_rows)`.

### Partial failure

If any call raises `SmartsheetError`, stop immediately. Do not continue. Report:

> "I was deleting rows when a Smartsheet error stopped me mid-way: {error}. Some rows may have been deleted before the failure; the rest are untouched. You can re-run the skill (delete_rows is idempotent — it ignores already-deleted IDs) or say 'undo' to restore from the snapshot."

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

If the master guard banner was set in step 0, prepend it to this output.

## Undo / restore

If the designer says "undo" or "restore [room]" in the SAME session:

1. Recall the `Snapshot` from step 2.
2. For "undo everything":
   - Call `snapshot.rows_for_restore(snapshot, [all_deleted_root_ids])` to get an ordered list of row payloads. Each payload has `_original_id`, `_original_parent_id`, `cells`, and `toBottom` fields.
   - The Smartsheet API requires literal `parentId` (not `_original_parent_id`) and does NOT accept those underscore-prefixed fields. You must translate IDs in a loop:

```python
id_map = {}  # original id -> new id
for payload in restore_payloads:
    api_row = {"cells": payload["cells"], "toBottom": payload["toBottom"]}
    if payload["_original_parent_id"] is not None:
        api_row["parentId"] = id_map[payload["_original_parent_id"]]
    new_ids = smartsheet_client.add_rows(token, sheet_id, [api_row])
    id_map[payload["_original_id"]] = new_ids[0]
```

   - This is N `add_rows` calls (one per row). Unavoidable for hierarchy restoration — you can't know a parent's new ID until after you POST it.
   - Also delete any rows the skill added in step 6.
3. For "restore [room]": scope the `rows_for_restore` call to just that room's original ID. The same ID-translation loop applies — just scoped to one room's root ID.

Row IDs will change on restore; this is documented and expected.

## If the session ends

The snapshot is lost. Tell the designer to get a fresh template copy from the PM and re-run the skill. The master template is never touched, so a fresh copy is always available.
