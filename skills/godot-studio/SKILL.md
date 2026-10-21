---
name: godot-studio
description: "Use when an agent builds or tests a Godot game project."
version: 0.2.1
author: Min (Dingbat) for the Hermes game-studio plugin effort
license: MIT
metadata:
  hermes:
    tags: [godot, game-development, mcp, headless]
    related_skills: [hermes-agent, rea-reverse-engineering]
---

# Godot studio workflow

## When to Use

- Building, editing, or testing a Godot 4 project with an agent in the loop.
- A playtest/export loop must run without a human opening the editor.

## Two halves — use both

1. **Editor-side (live editing)**: the `godot-ai` MCP server (hi-godot/godot-ai, MIT).
   46 tools / 120+ ops: scenes, nodes, scripts, signals, UI, materials, animation.
   Hermes Agent is a supported client — register via the addon's dock
   ("Run this manually" → `godot-ai attach` over stdio). Requires Godot 4.7+ and `uv`.
   Do NOT hand-edit .tscn/.godot files while the editor is open — go through MCP.
2. **Headless-side (verification)**: the `godot-studio` plugin tools.
   - `godot_headless_check <project>` → scripts parse, resources load, errors surface. No editor needed.
   - `godot_export <project> <preset>` → CI builds (Web/macOS/…).
   - `godot_builds <project>` → every export preset and the state of its artifact
     (exists, size, modified). Check before re-exporting; use the artifact path after.
   - `godot_setup` → install state + exact registration command.

## Deliver the build in chat

After a successful `godot_export`, call `godot_builds` to confirm the artifact,
then attach it in the reply: `MEDIA:/absolute/path/to/artifact` (the desktop app
renders it as a card; zip/pck/exe attach as files). Never claim a build without
the artifact existing in `godot_builds` output.

## The loop

```
edit via godot-ai MCP  →  godot_headless_check  →  fix reported errors
                       →  godot_export (Web preset)  →  playtest
```

- Run `godot_headless_check` after EVERY batch of MCP edits, before declaring progress.
- For the playtest step on a native build, use REA (`observe_native_calls`,
  `capture_native_ui_scenario`) — see the rea-reverse-engineering skill.
- Web export is the cheapest playable artifact for a playtester agent
  (`godot_export <p> Web` → serve the export directory, drive with browser tools).

## Pitfalls

- godot-ai needs a LIVE editor; headless checks are a different tool — don't confuse them.
- `--quit-after N` (frames) is for runtime errors; `--quit` only validates load-time parsing.
- Export presets must exist in the project (editor → Project → Export); `godot_export` cannot invent one.
- Export templates are NOT bundled with the editor: an export fails with
  "export template not found" until they are installed (editor → Manage Export
  Templates, or `godot --headless --install-export-templates`; if that stalls,
  download the release `.tpz` from github.com/godotengine/godot-builds and
  extract `templates/*` for the needed platforms + `version.txt` into
  `~/Library/Application Support/Godot/export_templates/<version>/`).
- Godot does not create the output's parent directory — a raw `godot --export-*`
  into a preset `export_path` whose directory doesn't exist yet fails with
  "target folder does not exist". `godot_export` creates it (inside the project)
  before running; when scripting Godot by hand, `mkdir -p` first.
- Coding-Solo/godot-mcp (5.4k stars) is dormant since 2026-04 — prefer godot-ai.
- Godot-MCP-Native (pure GDScript, `gdmcp` CLI, progressive discovery) is a valid
  zero-dependency alternative when uv/Node must stay off the machine.
