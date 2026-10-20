"""godot-studio desktop backend — read-only build/version facts.

Routes mount under /api/plugins/godot-studio/. Deliberately self-contained
(duplicates the small preset parser from __init__.py) so the desktop half
works even when the agent half's module is not importable in this process.
No writes, no subprocess beyond `godot --version`.
"""

import os
import shutil
import subprocess

from fastapi import APIRouter, Query

router = APIRouter()


def _godot_binary():
    found = shutil.which("godot") or shutil.which("godot4")
    if found:
        return found
    app = "/Applications/Godot.app/Contents/MacOS/Godot"
    return app if os.path.exists(app) else None


def _parse_presets(project: str):
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


@router.get("/version")
async def version():
    godot = _godot_binary()
    if not godot:
        return {"installed": False}
    try:
        proc = subprocess.run([godot, "--version"], capture_output=True, text=True, timeout=30)
        return {"installed": True, "binary": godot, "version": proc.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"installed": False, "error": str(exc)}


@router.get("/builds")
async def builds(project: str = Query(...)):
    if not os.path.exists(os.path.join(project, "project.godot")):
        return {"error": f"no project.godot at {project}", "builds": []}
    return {"project": project, "builds": _parse_presets(project)}
