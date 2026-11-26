"""Build and reopen the example from a Blender Python console."""
from hashlib import sha256
import json
from pathlib import Path
import runpy

import bpy


def prepare(folder):
    folder = Path(folder).resolve(strict=True)
    model = folder / "Alder library.blend"
    output = folder / "Scene checks.json"
    if model.exists() or output.exists():
        raise FileExistsError("Choose a fresh furnished revision")
    if bpy.data.filepath or bpy.data.is_dirty:
        raise ValueError("Use a new Blender session for the example")
    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True, load_ui=False)
    spec = json.loads((folder / "library.json").read_text(encoding="utf-8"))
    builder = runpy.run_path(str(Path(__file__).with_name("build_blender.py")))
    builder["build"](spec)
    bpy.ops.wm.save_as_mainfile(filepath=str(model))
    bpy.ops.wm.open_mainfile(filepath=str(model), load_ui=False, use_scripts=False)
    record = builder["measure"](spec)
    record["model_sha256"] = sha256(model.read_bytes()).hexdigest()
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return output
