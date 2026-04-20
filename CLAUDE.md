# CLAUDE.md - Zenith-Claude-Plugins

Orientation for future sessions working on this repo.

## What this repo is

This is Zenith's internal Claude Code plugin marketplace. It's a public GitHub repository with a specific structure that lets designers (and eventually other Zenith employees) subscribe to a curated set of Claude Code skills maintained by Tyler.

Designers install skills from this repo by running `/plugin marketplace add tylerFF/Zenith-Claude-Plugins` in Claude Code once, then installing individual plugins with `/plugin install <name>`.

## Repo layout

```
Zenith-Claude-Plugins/
├── .claude-plugin/
│   └── marketplace.json              Marketplace manifest (lists all plugins)
├── plugins/
│   └── <plugin-name>/                One folder per plugin
│       ├── .claude-plugin/
│       │   └── plugin.json           Plugin metadata
│       └── skills/
│           └── <skill-name>/
│               └── SKILL.md          Skill instructions
├── docs/
│   └── specs/                        Design docs (YYYY-MM-DD-<topic>-design.md)
├── CLAUDE.md                         This file
└── README.md                         Human-facing overview
```

## Current plugins

- **zenith-selections** (planned, not yet built) - helps designers set up a per-project copy of the Smartsheet selections template. See `docs/specs/2026-04-20-selections-setup-design.md`.

## Skill design principles

1. **Never touch master templates.** Every skill that writes to a Smartsheet has a hardcoded check against Zenith's master template sheet IDs. The skill refuses to write to a master unless the designer includes an explicit safety phrase (e.g. `MASTER EDIT`) in their message.
2. **Tokens live in 1Password.** Skills fetch credentials at runtime via the `op` CLI (`op read "op://Zenith Automations/<item>/credential"`). Never embed tokens in skill code.
3. **Session-scoped undo.** Skills that make destructive changes should snapshot pre-change state in conversation memory so the designer can say "undo" within the same session.
4. **Fail early, fail loud.** Pre-flight checks before any writes. Clear, designer-friendly error messages.
5. **Nuclear-option safety net.** Since skills operate on per-project copies (not masters), the worst-case recovery is always "get a fresh copy from the master." Remind designers of this when errors occur.

## Making changes to an existing skill

1. Edit the SKILL.md (or helper files) in the plugin folder.
2. Test locally: from a separate Claude Code session, point it at this repo as a local marketplace (see Claude Code docs for local marketplace testing) or temporarily copy the skill into `~/.claude/skills/`.
3. Commit and push.
4. Designers' Claude Code will pick up the change on next plugin update. For urgent changes, DM them asking to run `/plugin update <plugin-name>`.

## Adding a new skill

1. Start with brainstorming (superpowers:brainstorming) to produce a spec doc in `docs/specs/`.
2. Create a new plugin folder under `plugins/`.
3. Write the SKILL.md following the existing skill patterns.
4. Add an entry to `.claude-plugin/marketplace.json`.
5. Test.
6. Commit and push.

## Secrets and service accounts

- Skills authenticate to external services via 1Password service account tokens stored on each designer's laptop as environment variables.
- The Windows PowerShell setup script that bootstraps a designer's laptop contains the real service account token and must **never** be committed to this (or any) git repo. It lives on Tyler's Mac and is distributed via DM.
- If a service account token is rotated: regenerate in 1Password, update the master copy in Tyler's 1Password Employee vault, re-embed in the PowerShell setup script, re-distribute to designers.

## Related repos

- `Zenith DB Execution Report` - the KPI automation (private, runs on Tyler's machine only, not distributed).
