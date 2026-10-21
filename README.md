# godot-studio — headless Godot workflows for the agent game studio

Hermes Agent plugin + skill. Godot was the missing engine in the agent game
studio: `hi-godot/godot-ai` already bridges a **live editor** to agents
(46 MCP tools, Hermes is a supported client), but nothing covered the half of
the loop that needs **no GUI** — verifying a project, exporting builds, closing
the loop a playtester can read. This plugin covers that half.

## What it adds

Four tools (toolset `godot`), registered only when a Godot 4 binary is found
(`check_fn`):

- **`godot_headless_check`** — runs `godot --headless --quit` (or
  `--quit-after N` frames) against a project and surfaces script/resource
  errors without an editor. Run it after every batch of MCP edits, before
  claiming progress.
- **`godot_export`** — CI-style export from a named export preset
  (`--export-release` / `--export-debug`), e.g. a Web build a playtester agent
  can actually load.
- **`godot_builds`** — lists every export preset in the project and the state
  of its artifact (exists, size, modified). The gallery data: check before
  re-exporting, attach the fresh artifact in chat (`MEDIA:`) after.
- **`godot_setup`** — reports Godot / godot-ai / uv install state and emits the
  exact registration path for the godot-ai MCP server. It installs nothing.

## Optional desktop companion (unified package)

This package ships a desktop half (`desktop/plugin.js`) plus its read-only
backend (`dashboard/plugin_api.py`), following the Hermes
“One package, both SDKs” layout. When the package is installed under a
`plugins/` root, the desktop app picks up the UI half automatically
(opt-in, off until enabled in Capabilities → Plugins):

- a **statusbar chip** showing the installed Godot version;
- a **Godot builds pane**: pick a project, see its presets and artifacts
  (size, state, time) — the same data `godot_builds` exposes to the agent.

The pane degrades gracefully when the Python backend is not enabled.

Plus the **`godot-studio` skill**: the full loop — edit via godot-ai MCP →
headless verify → export → playtest — with the pitfalls that cost real hours
(a project without `run/main_scene` errors differently than a broken script;
`--quit` validates parse-time only, `--quit-after` reaches runtime; export
presets must exist in the project first).

## Requirements

- Godot 4.x on PATH or `/Applications/Godot.app` (macOS). Tested on 4.7.2.
- Optional but recommended: the godot-ai addon for the editing half
  (https://github.com/hi-godot/godot-ai, MIT — needs its own editor + uv).

## Disclosed behaviour (catalog rule 13)

- **Shell commands**: `godot --headless …` (the local Godot binary), a read-only
  `godot --version` in the desktop backend, and a read-only `hermes mcp list`
  inside `godot_setup`. Nothing else is executed.
- **Executes the target project's GDScript**: `godot_headless_check` and
  `godot_export` run the project's own code (autoloads, main scene when
  `--quit-after` is used, export plugins) with **no approval prompt**. Point
  them only at projects you trust.
- **No network calls** by the plugin itself; no reads outside the Godot project
  the caller targets (the desktop pane reads `export_presets.cfg` and artifact
  metadata inside the project path the user configures in the pane).
- **No stored credentials, no telemetry, no background processes.**
- `godot_export` writes only inside the target project: the output path is
  resolved and must sit inside the project directory, and an existing file is
  never overwritten unless it is a known export artifact of that project (from
  `export_presets.cfg`). When no output path is given, the preset's own
  `export_path` is used.

## Why this shape

Hermes plugin convention: atomic tools in `__init__.py`, workflow intelligence
in the bundled skill. The plugin deliberately does not wrap godot-ai — two
bridges to one editor is one too many. It is the verification and export leg,
and the skill teaches the agent when to use which half.

## Ecosystem map (verified 2026-10-19)

| Project | Stars | License | Activity | Role |
|---|---|---|---|---|
| `hi-godot/godot-ai` | 1.9k | MIT | very active | 46 MCP tools, Hermes listed as supported client (`godot-ai attach` stdio). Needs Godot 4.7+ and uv. |
| `Coding-Solo/godot-mcp` | 5.4k | MIT | quiet since 2026-04 | most starred, dormant |
| `yurineko73/Godot-MCP-Native` | 722 | MIT | active | 155 tools, pure GDScript, zero Node/Python deps, `gdmcp` CLI with progressive discovery |
| `youichi-uda/godot-mcp-pro` | 575 | commercial | active | 175 tools, Asset Library |

## Status

Validated with `hermes plugins validate --install-deps` (all checks green).
Headless check verified end-to-end on Godot 4.7.2 (`test/hello`).
