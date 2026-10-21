"""godot-studio — headless Godot workflows for the agent game studio.

Atomic tools only; the workflow intelligence lives in skills/godot-studio/SKILL.md.
"""

import json
import os
import shutil
import subprocess


def _godot_binary() -> str | None:
    """Locate a Godot 4 binary: PATH, then the standard macOS app bundle."""
    found = shutil.which("godot") or shutil.which("godot4")
    if found:
        return found
    app = "/Applications/Godot.app/Contents/MacOS/Godot"
    return app if os.path.exists(app) else None


def _run(args: list[str], timeout: int = 300) -> dict:
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-20000:],
            "stderr": proc.stderr[-20000:],
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except OSError as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def _parse_presets(project: str) -> list[dict]:
    """Parse export_presets.cfg → [{name, export_path, exists, size_bytes, modified}]."""
    cfg = os.path.join(project, "export_presets.cfg")
    if not os.path.exists(cfg):
        return []
    presets, current, section = [], {}, ""
    try:
        with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    if section.startswith("preset.") and ".options" not in section:
                        if current.get("name"):
                            presets.append(current)
                        current = {}
                    continue
                if "=" in line and section.startswith("preset.") and ".options" not in section:
                    key, _, val = line.partition("=")
                    key, val = key.strip(), val.strip().strip('"')
                    if key == "name":
                        current["name"] = val
                    elif key == "export_path":
                        current["export_path"] = val
        if current.get("name"):
            presets.append(current)
    except OSError:
        return []
    out = []
    for p in presets:
        entry = {"preset": p["name"], "export_path": p.get("export_path", "")}
        artifact = os.path.normpath(os.path.join(project, entry["export_path"])) if entry["export_path"] else ""
        entry["artifact_path"] = artifact
        try:
            st = os.stat(artifact)
            entry.update({"exists": True, "size_bytes": st.st_size, "modified": int(st.st_mtime)})
        except (OSError, ValueError):
            entry.update({"exists": False, "size_bytes": 0, "modified": 0})
        out.append(entry)
    return out


def register(ctx):
    godot = _godot_binary()

    # ── Tool: headless project check (scripts parse, resources load) ──
    check_schema = {
        "name": "godot_headless_check",
        "description": (
            "Run a Godot project headless and quit, surfacing script/resource errors "
            "without opening the editor. Use before and after any MCP-driven edit. "
            "Runs the target project's GDScript (autoloads, main scene) with no "
            "approval prompt — point it only at projects you trust."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the Godot project directory (contains project.godot)",
                },
                "quit_after_frames": {
                    "type": "integer",
                    "description": "Quit after N frames instead of immediately (0 = --quit). Default 0.",
                },
            },
            "required": ["project_path"],
        },
    }

    def handle_check(params, **kwargs):
        if not godot:
            return json.dumps({"error": "godot binary not found — install Godot 4 first"})
        project = params.get("project_path", "")
        if not os.path.exists(os.path.join(project, "project.godot")):
            return json.dumps({"error": f"no project.godot at {project}"})
        frames = int(params.get("quit_after_frames", 0) or 0)
        args = [godot, "--headless", "--path", project]
        args += [f"--quit-after", str(frames)] if frames > 0 else ["--quit"]
        result = _run(args)
        return json.dumps(result)

    ctx.register_tool(
        "godot_headless_check", toolset="godot", schema=check_schema,
        handler=handle_check, check_fn=lambda: godot is not None,
    )

    # ── Tool: CI-style export ──
    export_schema = {
        "name": "godot_export",
        "description": (
            "Export a Godot build headless using a named export preset (e.g. 'Web', "
            "'macOS'). Runs the project's GDScript and export plugins with no approval "
            "prompt — point it only at projects you trust. Output is confined to the "
            "project directory; existing files that aren't known export artifacts are "
            "never overwritten."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "preset": {"type": "string", "description": "Export preset name as configured in the project"},
                "debug": {"type": "boolean", "description": "Use --export-debug instead of --export-release. Default false."},
                "output_path": {
                    "type": "string",
                    "description": (
                        "Optional output file path; must resolve inside project_path. "
                        "Defaults to the preset's export_path from export_presets.cfg."
                    ),
                },
            },
            "required": ["project_path", "preset"],
        },
    }

    def handle_export(params, **kwargs):
        if not godot:
            return json.dumps({"error": "godot binary not found — install Godot 4 first"})
        project = params.get("project_path", "")
        if not os.path.exists(os.path.join(project, "project.godot")):
            return json.dumps({"error": f"no project.godot at {project}"})
        preset = params.get("preset", "")
        flag = "--export-debug" if params.get("debug") else "--export-release"

        # Resolve the output path: caller override, else the preset's own
        # export_path from export_presets.cfg. Confine it to the project and
        # never overwrite a file that isn't a known export artifact of it.
        presets = _parse_presets(project)
        known_artifacts = {
            os.path.realpath(p["artifact_path"])
            for p in presets if p.get("artifact_path")
        }
        out = params.get("output_path")
        if not out:
            match = next((p for p in presets if p["preset"] == preset), None)
            if not match or not match.get("export_path"):
                return json.dumps({
                    "error": f"preset '{preset}' has no export_path in export_presets.cfg "
                             "— pass an explicit output_path inside the project",
                })
            out = os.path.join(project, match["export_path"])

        out = os.path.realpath(out)
        project_root = os.path.realpath(project)
        if os.path.isdir(out):
            return json.dumps({"error": f"output_path must be a file path, not a directory: {out}"})
        try:
            inside = os.path.commonpath([project_root, out]) == project_root
        except ValueError:
            inside = False
        if not inside:
            return json.dumps({
                "error": f"output_path must be inside the project directory ({project_root})",
            })
        if os.path.exists(out) and out not in known_artifacts:
            return json.dumps({
                "error": f"refusing to overwrite {out}: not a known export artifact of this project",
            })
        # Godot refuses to export into a missing parent directory — create it
        # (always inside the project, past the containment guard above).
        os.makedirs(os.path.dirname(out), exist_ok=True)
        result = _run([godot, "--headless", "--path", project, flag, preset, out], timeout=900)
        # Export templates are not bundled with the editor. When they are
        # missing, surface the fix instead of raw engine stderr. The
        # "export_templates" path fragment is locale-independent.
        if result["returncode"] != 0 and "export_templates" in (result["stderr"] + result["stdout"]):
            result["hint"] = (
                "export templates for this platform are not installed. Install them "
                "via the Godot editor (Project → Manage Export Templates) or "
                "`godot --headless --install-export-templates`; if that stalls, "
                "download the release .tpz from github.com/godotengine/godot-builds "
                "and extract templates/* + version.txt into the export_templates/"
                "<version> directory shown in the error."
            )
        return json.dumps(result)

    ctx.register_tool(
        "godot_export", toolset="godot", schema=export_schema,
        handler=handle_export, check_fn=lambda: godot is not None,
    )

    # ── Tool: onboarding state (what is installed, what to run next) ──
    setup_schema = {
        "name": "godot_setup",
        "description": (
            "Report Godot/godot-ai/uv installation state and emit the exact "
            "hermes mcp add command to register the godot-ai MCP server."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    }

    def handle_setup(params, **kwargs):
        state = {
            "godot_binary": godot,
            "godot_version": _run([godot, "--version"], timeout=30)["stdout"].strip() if godot else None,
            "uv": shutil.which("uv") is not None,
            "godot_ai_mcp_registered": False,
        }
        try:
            listing = subprocess.run(
                ["hermes", "mcp", "list"], capture_output=True, text=True, timeout=30,
            )
            state["godot_ai_mcp_registered"] = "godot" in (listing.stdout or "").lower()
        except (OSError, subprocess.TimeoutExpired):
            pass
        state["next_step"] = (
            "Register godot-ai: open the Godot editor with the godot-ai addon enabled, "
            "then run the 'Run this manually' command it shows for Hermes Agent "
            "(godot-ai attach over stdio). See "
            "https://github.com/hi-godot/godot-ai/blob/main/docs/client-configuration.md."
        )
        return json.dumps(state)

    ctx.register_tool("godot_setup", toolset="godot", schema=setup_schema, handler=handle_setup)

    # ── Tool: build gallery (presets + artifact state, for re-export decisions) ──
    builds_schema = {
        "name": "godot_builds",
        "description": (
            "List a project's export presets and the current state of their "
            "artifacts (exists, size, modified time). Use before re-exporting "
            "and to attach fresh builds in chat."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
            },
            "required": ["project_path"],
        },
    }

    def handle_builds(params, **kwargs):
        project = params.get("project_path", "")
        if not os.path.exists(os.path.join(project, "project.godot")):
            return json.dumps({"error": f"no project.godot at {project}"})
        return json.dumps({"project": project, "builds": _parse_presets(project)})

    ctx.register_tool(
        "godot_builds", toolset="godot", schema=builds_schema,
        handler=handle_builds, check_fn=lambda: godot is not None,
    )
