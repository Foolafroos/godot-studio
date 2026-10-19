"""godot-studio — headless Godot workflows for the agent game studio.

Atomic tools only; the workflow intelligence lives in skills/godot-studio/SKILL.md.
"""

import json
import os
import shutil
import subprocess

_ALLOWED_GODOT_FLAGS = {
    "--headless", "--quit", "--quit-after", "--path", "--export-release",
    "--export-debug", "--export-pack", "--main-pack", "--script", "--check-only",
    "--validate-extension-api", "--build-solutions", "--clean", "--no-header",
}


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


def register(ctx):
    godot = _godot_binary()

    # ── Tool: headless project check (scripts parse, resources load) ──
    check_schema = {
        "name": "godot_headless_check",
        "description": (
            "Run a Godot project headless and quit, surfacing script/resource errors "
            "without opening the editor. Use before and after any MCP-driven edit."
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

    ctx.register_tool("godot_headless_check", check_schema, handle_check)

    # ── Tool: CI-style export ──
    export_schema = {
        "name": "godot_export",
        "description": "Export a Godot build headless using a named export preset (e.g. 'Web', 'macOS').",
        "parameters": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "preset": {"type": "string", "description": "Export preset name as configured in the project"},
                "debug": {"type": "boolean", "description": "Use --export-debug instead of --export-release. Default false."},
                "output_path": {"type": "string", "description": "Optional output file path override"},
            },
            "required": ["project_path", "preset"],
        },
    }

    def handle_export(params, **kwargs):
        if not godot:
            return json.dumps({"error": "godot binary not found — install Godot 4 first"})
        project = params.get("project_path", "")
        preset = params.get("preset", "")
        flag = "--export-debug" if params.get("debug") else "--export-release"
        out = params.get("output_path") or "."
        result = _run([godot, "--headless", "--path", project, flag, preset, out], timeout=900)
        return json.dumps(result)

    ctx.register_tool("godot_export", export_schema, handle_export)

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
            "(godot-ai attach over stdio). See vendor/godot-ai/docs/client-configuration.md."
        )
        return json.dumps(state)

    ctx.register_tool("godot_setup", setup_schema, handle_setup)
