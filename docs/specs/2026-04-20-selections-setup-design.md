# Selections Sheet Setup Skill - Design

**Date:** 2026-04-20
**Status:** Approved, ready for implementation plan
**Author:** Tyler Fox (with Claude brainstorming assistance)

---

## Problem

When Zenith starts a new construction project, a project manager makes a fresh copy of a canonical Smartsheet called `Job# - Name Selections` and hands it to a designer. That template contains every room Zenith ever builds for (Kitchen, Master Bath, Powder Bath, Hall Bath, Mudroom, Basement variants, Bedroom/Living areas, Exterior) with a standard roster of items per room (sinks, faucets, toilets, tile, countertops, lighting, cabinetry, etc.).

The designer's job is to trim the copy down to only the rooms and items that are actually in scope for this project, and add any items or rooms that weren't in the template. Today this is manual: the designer reads through ~350 rows, right-clicks to delete sections, types in new items. For a typical project this takes 30-60 minutes of tedious clicking.

This skill automates that work. The designer describes the project scope in plain English, Claude Code does the edits.

## User workflow (end-to-end)

A designer opens Claude Code and types:

> *"Set up selections for the new Wentzel project. Here's the sheet: https://app.smartsheet.com/sheets/... . We're doing a hall bath remodel: toilet, faucet, sink, tile floor, heated towel rack. Also a new kitchen: sink, faucet, countertop. And a nursery build-out: flooring, paint."*

The skill, step by step:

1. **Resolves the sheet.** Extracts the sheet ID from the URL.
2. **Verifies it's not the master template.** If the URL resolves to the master template's sheet ID and the designer did not include the exact phrase `MASTER EDIT` in their message, the skill refuses to proceed. See [Master template protection](#master-template-protection).
3. **Runs pre-flight checks.** Token retrieval, sheet access, structural sanity. See [Pre-flight checks](#pre-flight-checks).
4. **Parses scope.** Uses Claude's language understanding to structure the designer's paragraph into `{room: [items]}`.
5. **Takes a snapshot.** Captures the full current state of the sheet in session memory for later undo.
6. **Diffs scope against template.** Identifies rooms/items to keep, to delete, and things to ask about.
7. **Asks about unknowns.** For new rooms (not in template) and items Claude can't confidently match, asks the designer one question at a time. See [Scope matching](#scope-matching).
8. **Executes.** Deletes out-of-scope rows in batches, adds confirmed new rows. No preview step for template-matched actions.
9. **Reports.** Prints a summary of what was kept, added, deleted, and how to undo.

The `Everywhere (in scope)` section of the template is left untouched - it holds project-wide specs that apply regardless of room.

## Architecture

### Repository layout

This skill lives in the `tylerFF/Zenith-Claude-Plugins` public GitHub repository, structured as a Claude Code plugin marketplace:

```
Zenith-Claude-Plugins/
├── .claude-plugin/
│   └── marketplace.json              Plugin marketplace manifest
├── plugins/
│   └── zenith-selections/            Plugin directory
│       ├── .claude-plugin/
│       │   └── plugin.json           Plugin metadata
│       └── skills/
│           └── setup-selections-sheet/
│               └── SKILL.md          The skill instructions (core logic)
├── docs/
│   └── specs/                        Design docs (this file)
├── CLAUDE.md                         Repo orientation for future devs
└── README.md                         Human-facing overview
```

The exact `marketplace.json` and `plugin.json` schemas will be verified against current Claude Code documentation at implementation time rather than guessed from older references.

### External dependencies

The skill talks to exactly two services, both over HTTPS:

1. **1Password**, via the `op` CLI installed on the designer's laptop. The skill runs `op read "op://Zenith Automations/Smart Sheet - API Key/credential"` to fetch the Smartsheet API token. Token is used in-memory for the call and discarded.
2. **Smartsheet API** at `api.smartsheet.com`. Used to GET sheet contents and POST/DELETE rows.

No database, no Claude API calls (the designer's Claude Code is the LLM), no other services.

### Runtime state

- **Smartsheet API token**: pulled from 1Password on demand. Never persisted to disk by the skill.
- **Current sheet contents**: fetched from Smartsheet at the start of each skill invocation. Not cached between runs.
- **Session snapshot (undo buffer)**: stored in the Claude Code conversation as a data block. Persists only for the current session. Lost when the designer closes Claude Code or starts a new conversation.
- **Designer's scope description**: lives in the conversation. Re-parsed if the skill is re-invoked.

No durable state between sessions. Resetting = restart the session.

## Master template protection

The master template must never be edited by default. Its identity is hardcoded in the skill:

- **Name:** `Job# - Name Selections`
- **Numeric sheet ID:** `8909191432693636`
- **Permalink:** `https://app.smartsheet.com/sheets/6jh54C2xRQ8fwcQWp6Q8hXP8cxMqrcJp5rmX63x1`

### Behavior

Before any other pre-flight check:

1. The skill resolves the designer's URL/ID to a numeric Smartsheet sheet ID.
2. If that ID equals `8909191432693636`:
   - Scan the designer's message in this turn for the exact phrase `MASTER EDIT` (case-sensitive).
   - **Phrase absent**: abort immediately with this message:
     > *This is the Master Template (`Job# - Name Selections`). The skill won't edit it by default.*
     >
     > *If you're sure you want to modify the master template, re-run your request and include the phrase `MASTER EDIT` in your message.*
     >
     > *More likely: you want a per-project copy of the template. Go to Smartsheet, right-click the master, choose "Save as New," rename it for your project, and paste the new sheet's URL.*
   - **Phrase present**: proceed, but prepend a banner to all user-facing output:
     > ⚠️ *You are editing the MASTER TEMPLATE. Changes will affect all future project copies.*

This check runs before token checks, URL sanity, everything. A typo that points at the master should never cost anyone a master-template edit.

## Pre-flight checks

Run in order. First failure aborts the skill with a designer-friendly message. No writes occur unless all checks pass.

1. **Master template protection** (see previous section).
2. **1Password reachable**: `op whoami`. On failure: *"1Password isn't responding. Make sure the 1Password app is running and you're signed in, then try again."*
3. **Smartsheet token retrievable**: `op read "op://Zenith Automations/Smart Sheet - API Key/credential"`. On failure: *"Couldn't fetch the Smartsheet token from 1Password. Tell Tyler the service account may need attention."*
4. **URL parseable**: extract a valid Smartsheet sheet ID from the provided URL. On failure: *"That doesn't look like a Smartsheet sheet URL. Paste the URL from the browser when viewing the sheet in grid view."*
5. **Sheet accessible**: GET `/sheets/{id}` with the token. On 403/404: *"I can't access that sheet. Make sure (a) the URL is correct, and (b) Zenith's Smartsheet automation account has Edit access to it."*
6. **Looks like a selections template**: verify the sheet has at least one expected top-level room row (case-insensitive match on names like `Hall Bathroom`, `Kitchen/Bar`, `Master Bathroom`, `Powder Bathroom`, etc.). On failure: *"This sheet doesn't look like a standard selections template. Double-check the URL. If it is the right sheet, message Tyler so we can investigate."*

## Scope matching

Claude's language model does the matching between the designer's free-form description and the template's canonical room/item names. The skill enforces three confidence tiers:

### High confidence: proceed silently

Obvious aliases map directly to template sections:

| Designer says | Maps to |
|---|---|
| "hall bath", "hallway bath" | Hall Bathroom |
| "kitchen", "main kitchen" | Kitchen/Bar |
| "master bath", "master bathroom" | Master Bathroom |
| "powder room", "half bath" | Powder Bathroom |
| "mudroom", "laundry room", "laundry" | Mudroom/Laundry |
| "basement kitchen", "basement bar" | Basement - Kitchen/Bar |
| "basement bath" | Basement - Hall Bathroom |
| "exterior", "outside", "backyard" | Exterior |

For items, similar obvious mappings ("toilet", "WC", "water closet" all → Toilet).

These proceed without asking.

### Uncertain match: ask the designer

Claude asks a clarifying question before proceeding. Examples:

- *"You mentioned 'den.' The template has 'Bedroom/Living/Dining/Family/Office/Sunroom' as a catch-all for those spaces - should I map 'den' there, or add a new 'Den' section?"*
- *"You mentioned 'guest bath.' That's not explicitly in the template. Is this the Hall Bathroom, the Powder Bathroom, or a new section?"*
- *"You mentioned 'mirror' for the kitchen. Template has mirrors listed under bathrooms only - should I add one to the kitchen as a new row, or did you mean a different room?"*

One question at a time. The designer's answer feeds forward into the rest of the scope matching.

### No reasonable match: flag as new

Things that are clearly not in the template (e.g., "wine cellar", "dog wash station", "sauna") are treated as new rooms/items and flagged per the [Flag-and-ask](#flag-and-ask-for-new-rooms-and-items) rules below.

## Flag-and-ask for new rooms and items

For anything not in the template that passes the matching step, the skill asks one question at a time before adding:

**New item in an existing template room:**
> *"'Heated towel rack' isn't in the Hall Bathroom template. Want me to add it? If yes, what category - `16 ACCESSORIES:Material`, `09 PLUMBING:Material`, or something else?"*

**New top-level room:**
> *"'Nursery' isn't in the template. Want me to add it as a new top-level room section? I'll create a parent row named 'Nursery' and add the items you listed (flooring, paint) as children."*

All additions are confirmed before writing.

## Write-time error handling

Smartsheet batch limits and partial-failure behavior:

- Deletes are grouped into batches of up to 300 row IDs per API call (under the 450 limit for safety headroom).
- Adds happen after all deletes complete, also batched.
- The skill does **not** interleave deletes and adds.

### Partial failure

If any batch fails mid-run:

1. Stop immediately. Do not attempt further batches.
2. Keep the session snapshot intact.
3. Report exactly what succeeded and what didn't, for example:
   > *"I deleted Master Bath and Powder Bath (54 rows). Then a Smartsheet error stopped me. The Mudroom, Basement, and Exterior sections are still there, and none of the new items were added yet. You can re-run the skill or say 'undo' to restore the 54 rows."*
4. Let the designer decide: re-run, undo, or go to the nuclear option.

## Undo / restore

### What the snapshot captures

Before any writes, the skill records:
- Every row's ID, parent ID, sibling order
- Every cell's column ID and value
- The row's current expanded/collapsed state (best-effort)

This lives in session memory as structured data.

### Granularity

- **"Undo"** or **"undo everything"**: full restore. All skill-originated additions are deleted. All skill-originated deletions are re-added in their original parent-child structure with original cell values.
- **"Undo [room name]"** (e.g., *"undo the nursery"*): scoped revert. If the named change was an addition, it's removed. If it was a deletion, those rows are re-added.
- **"Restore [room name]"**: synonym for scoped undo on a deleted section. Re-adds the rows for that one room.

### Known limitations

- **Row IDs change on restore.** Restored rows get new Smartsheet row IDs. If any external reference points at specific row IDs in this sheet (rare for selections sheets, which use self-contained formulas), those references break. In practice, the template's formulas (Location, Ancestors, Children, ETA Formula Helper) are all relative and self-contained, so this is not expected to be a real problem.
- **Session scope only.** Snapshot is lost when the Claude Code conversation ends. If the designer restarts Claude Code, they cannot undo changes from a prior session - they must use the nuclear option.

## Nuclear option

If the sheet is wedged and undo cannot fix it, the always-available escape hatch is to abandon the per-project copy and get a fresh one from the PM. The master template (`Job# - Name Selections`) is never touched by the skill (see [Master template protection](#master-template-protection)), so a fresh copy is always available.

On unrecoverable errors, the final summary includes:

> *Something went wrong mid-way through. You have two options:*
>
> *1. Ask me to "undo" - I'll restore from the snapshot.*
>
> *2. If that doesn't work, get a fresh template copy from your PM and start over. The master template is untouched.*

## Reporting

After successful execution, the skill prints a summary:

```
Wentzel project setup complete.

Matched to template:
  "hall bath"   -> Hall Bathroom
  "kitchen"     -> Kitchen/Bar

Kept (in scope):
  Hall Bathroom: Faucet, Sink, Toilet, Tile Flooring
  Kitchen/Bar:   Sink, Faucet, Countertop

Added (new):
  Hall Bathroom: Heated Towel Rack  [16 ACCESSORIES:Material]
  Nursery (new top-level section): Flooring, Paint

Deleted (out of scope):
  Master Bathroom, Powder Bathroom, Mudroom/Laundry,
  Basement - Kitchen/Bar, Basement - Hall Bathroom,
  Bedroom/Living/Dining/..., Exterior
  Total: 8 sections, 254 rows

Session snapshot saved. Say "undo" or "restore [room]" to revert.
```

## Constants (hardcoded in the skill)

| Constant | Value |
|---|---|
| Master template numeric sheet ID | `8909191432693636` |
| Master template name (for messaging) | `Job# - Name Selections` |
| 1Password reference for Smartsheet token | `op://Zenith Automations/Smart Sheet - API Key/credential` |
| Required phrase to authorize master edits | `MASTER EDIT` (case-sensitive, exact match) |
| Protected "always leave alone" section name | `Everywhere (in scope)` |
| Delete batch size | 300 row IDs per API call |

## Out of scope (future work)

Not included in v1. Captured here so we don't forget:

- **Pulling project scope from JobTread.** Designer currently types scope in free-form English. A future version could pull line items from the matching JobTread job and propose the scope automatically.
- **Creating the per-project copy automatically.** Currently a human (the PM) copies the master template in Smartsheet UI. A future version could handle this via the Smartsheet API.
- **Filling in spec details beyond the item name.** The skill currently adds placeholder spec templates (manufacturer/style/finish/link) to new items. A future version could let the designer include specs in their description (*"tile floor - 12x24 porcelain from Daltile"*) and the skill fills those in.
- **Cross-session undo.** Snapshots currently die with the session. A future version could persist snapshots somewhere durable (1Password item? Smartsheet attachment?) so undo survives.
- **Multiple sheets in one invocation.** Current design assumes one sheet per skill run.
- **Additional skills in the same repo** (invoicing helper, QC grid assistant, etc.) - the repo layout supports this but nothing else is designed yet.

## Security notes

- The Smartsheet token in 1Password is scoped via a service account named "Zenith Claude Skills" with **read-only** access to the `Zenith Automations` vault. It has no write access to 1Password, so a compromised token cannot be used to plant backdoor items.
- The Smartsheet API token itself has Smartsheet-level permissions matching the underlying Smartsheet user. That user should be a dedicated automation account (e.g. `automation@zenithdesignbuild.com`) added as an Editor to selections sheets, not a human's personal Smartsheet login.
- The setup PowerShell script embeds the 1Password service account token. That script must never be committed to any git repo. It is distributed to designers via direct message only.
- Service account token rotation: regenerate in 1Password, update the Employee vault item with the new value, re-embed in the PowerShell script, re-distribute to designers via DM, re-run. No skill changes required.
