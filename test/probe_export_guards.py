"""Probe: godot_export path guards (no real Godot run)."""
import importlib.util, json, os

spec = importlib.util.spec_from_file_location("godot_studio", "__init__.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

calls = []
mod._run = lambda args, timeout=300: (calls.append(args), {"returncode": 0, "stdout": "FAKE", "stderr": ""})[1]

tools = {}
class Ctx:
    def register_tool(self, name, toolset=None, schema=None, handler=None, check_fn=None):
        tools[name] = handler

mod.register(Ctx())
proj = os.path.abspath("test/hello")
export = lambda p: json.loads(tools["godot_export"](p))

print("1 no project.godot :", export({"project_path": "/tmp", "preset": "Web"}).get("error", "NO ERROR"))
print("2 outside project  :", export({"project_path": proj, "preset": "Web", "output_path": os.path.expanduser("~/.bashrc")}).get("error", "NO ERROR"))
notes = os.path.join(proj, "notes.txt"); open(notes, "w").write("x")
print("3 overwrite non-art:", export({"project_path": proj, "preset": "Web", "output_path": notes}).get("error", "NO ERROR"))
os.remove(notes)
print("4 directory        :", export({"project_path": proj, "preset": "Web", "output_path": proj}).get("error", "NO ERROR"))
r = export({"project_path": proj, "preset": "Web"})
print("5 default=preset   :", r, "| godot args:", calls[-1])
print("6 unknown preset   :", export({"project_path": proj, "preset": "Nope"}).get("error", "NO ERROR"))
print("7 new file builds/ :", export({"project_path": proj, "preset": "Web", "output_path": os.path.join(proj, "builds/web/index.html")}).get("error", "NO ERROR"), "| last arg:", calls[-1][-1])
# 8: existing known artifact -> allowed
os.makedirs(os.path.join(proj, "builds/web"), exist_ok=True)
open(os.path.join(proj, "builds/web/index.html"), "w").write("old build")
r = export({"project_path": proj, "preset": "Web"})
print("8 known artifact   :", r, "| last arg:", calls[-1][-1])
import shutil; shutil.rmtree(os.path.join(proj, "builds"))
