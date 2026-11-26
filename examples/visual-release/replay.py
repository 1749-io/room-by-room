"""Create a fictional, versioned design decision and its reviewed comparison-book placements."""
import argparse
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from house_visuals import arrangement_signature, checksum, signature


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def draw(model, view, target):
    """An editable orthographic fixture in millimetres. The camera mock is deliberately schematic."""
    scale = 0.12
    x, y = 48, 70
    width = int(model["width_mm"]*scale)
    height = int((model["depth_mm"] if view == "plan" else model["height_mm"])*scale)
    cut = int(model["opening_from_west_mm"]*scale)
    opening = int(model["opening_width_mm"]*scale)
    canvas = Image.new("RGB", (620, 510), "#faf8ee")
    pen = ImageDraw.Draw(canvas)
    pen.text((x, 25), f"{model['label']} | {view} | fictional geometry", fill="#173c35")
    pen.rectangle((x, y, x+width, y+height), outline="#364f47", width=8)
    pen.line((x+cut, y+height-4, x+cut+opening, y+height-4), fill="#faf8ee", width=9)
    if view != "plan":
        pen.rectangle((x+cut, y+height-int(model["opening_height_mm"]*scale), x+cut+opening, y+height),
                      outline="#3c6756", width=3)
    pen.text((x+cut, y+height+12), f"Retained opening  {model['opening_width_mm']} mm", fill="#173c35")
    pen.text((x, 465), "Key   Dark outline: room fabric     Gap: retained opening", fill="#173c35")
    canvas.save(target)


def prepare(work):
    work.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, HOUSE_BACKUP_DIR=str(work/"backups"), PYTHONIOENCODING="utf-8")
    def cli(*args):
        return subprocess.check_output([sys.executable, str(ROOT/"house.py"), "--houses-dir", str(work/"houses"), *args],
                                       text=True, encoding="utf-8", env=env).strip()
    name = "Example House"
    cli("start", name, "--room", "Living room")
    home = work / "houses/example-house"
    revision = "DESIGN-01"
    draft = Path(cli("begin-revision", name, revision))
    (draft/"geometry.py").write_text("from PIL import Image, ImageDraw\n\n" + inspect.getsource(draw), encoding="utf-8")
    for phase in ("existing", "proposed"):
        model = {"label": phase.title(), "width_mm": 4200, "depth_mm": 2900, "height_mm": 2300,
                 "opening_width_mm": 900, "opening_from_west_mm": 650, "opening_height_mm": 1950}
        save_json(draft/(phase+"-model.json"), model)
        for view, suffix in (("plan", "plan.png"), ("camera mock", "living.jpg"), ("section", "section.png")):
            draw(model, view, draft/(phase+"-"+suffix))
    cli("save-revision", name, revision, "--change", "Saved fictional native room geometry and example projections",
        "--why", "Test purpose and cross-view approvals", "--by", "Fixture author", "--affects", "Living room",
        "--next", "Record the fictional homeowner decision and review each derivative")
    assets = home/"revisions"/revision/"outputs"
    def ref(path):
        return {"path": path.relative_to(home).as_posix(), "sha256": checksum(path)}
    def output(name):
        return dict(ref(assets/name), revision=revision)
    decision = home/"source"/"layout-decision.md"
    quote = "I accept the living-room arrangement with the 900 mm opening retained. Fixings remain outside this decision."
    decision.write_text("Fictional homeowner, 24 November 2026\n\n"+quote+"\n", encoding="utf-8")
    scopes = ["floor/ground", "room/living-room"]
    states, visuals = {}, {}
    for phase in ("existing", "proposed"):
        key = phase+"-arrangement"
        geometry = [output(phase+"-model.json"), output("geometry.py")]
        state = {"phase": phase, "status": "accepted" if phase == "proposed" else "observed",
                 "scopes": scopes, "revision": revision, "arrangement": "The west-side 900 mm opening is retained.",
                 "exclusions": ["Fixing detail and construction design"], "geometry": geometry,
                 "supersedes": [], "features": {"retained-opening": {"description": "West-side opening in the south wall",
                 "scopes": scopes, "required_views": ["plan", "section"] if phase == "proposed" else ["plan"]}}}
        if phase == "proposed":
            binding = home/"source"/"accepted-arrangement.json"
            save_json(binding, {"house": "example-house", "state": key, "kind": "design-acceptance",
                                "arrangement_sha256": arrangement_signature(state), "decision_sha256": checksum(decision),
                                "by": "Fictional homeowner", "date": "2026-11-24", "quote": quote})
            state["homeowner_decision"] = dict(ref(decision), kind="design-acceptance", by="Fictional homeowner",
                                               date="2026-11-24", quote=quote, binding=ref(binding))
        states[key] = state
        camera = phase+"-door-view"
        frame = home/"source"/(camera+".json")
        save_json(frame, {"state_sha256": signature(state), "camera": camera, "basis": "native-camera",
                          "reference": output(phase+"-section.png"), "features": {"retained-opening": "visible"}})
        for suffix, view, scope, group in [("plan.png", "plan", scopes[0], "layouts"),
                                            ("living.jpg", "photo", scopes[1], "rooms"),
                                            ("section.png", "section", scopes[0], "studies")]:
            file = phase+"-"+suffix
            visual = {"state": key, "state_sha256": signature(state), "status": "signed", "view": view,
                      "source": output(file), "placements": [{"purpose": "comparison."+group, "scope": scope}],
                      "reviewer": "Fictional projection reviewer", "supersedes": [], "dependencies": geometry,
                      "limitations": ["Schematic test illustration. Dimensions and selections are fictional."],
                      "features": {"retained-opening": {"visibility": "shown", "evidence": output(file),
                                   "finding": "The labelled 900 mm opening agrees with the versioned geometry."}}}
            if view == "photo":
                visual.update(camera=camera, framing=ref(frame))
            visuals[Path(file).stem] = visual
    for name, content in [("design-states.json", {"states": states}), ("visual-approvals.json", {"visuals": visuals})]:
        save_json(home/name, dict(version=1, house="example-house", **content))
    manifest = json.loads((ROOT/"skills/property-comparison-pack/example.json").read_text(encoding="utf-8"))
    manifest["proposed"]["studies"].append({"id": "opening-section", "title": "Retained opening",
        "scope": "floor/ground", "text": "The schematic section checks the agreed opening against the native arrangement.",
        "images": [{"path": "proposed-section.png", "visual_id": "proposed-section", "view": "section",
                    "caption": "Section through the retained west-side opening."}]})
    for phase in ("existing", "proposed"):
        manifest[phase]["rooms"][0]["images"][0]["caption"] = "Schematic test camera facing the retained opening."
    source = home/"source"/"comparison.json"
    save_json(source, manifest)
    return home, source, assets


def issue(work, home, manifest, assets):
    env = dict(os.environ, HOUSE_BACKUP_DIR=str(work/"backups"), PYTHONIOENCODING="utf-8")
    cli = [sys.executable, str(ROOT/"house.py"), "--houses-dir", str(home.parent)]
    revision = "BROCHURE-01"
    output = Path(subprocess.check_output([*cli, "begin-revision", "Example House", revision, "--input",
                                          manifest.relative_to(home).as_posix()], env=env, text=True).strip())
    # Render the captured commission in the private revision workspace.
    captured = output.parent/"inputs"/manifest.relative_to(home)
    subprocess.run([sys.executable, str(ROOT/"skills/property-comparison-pack/scripts/build.py"),
                    str(captured), str(assets), str(output/"Brochure"), "--house", str(home)], check=True)
    subprocess.run([*cli, "save-revision", "Example House", revision, "--change", "Issued both fictional brochures",
                    "--why", "Exercise signed design and visual placements", "--by", "Fixture issuer",
                    "--affects", "Example whole-house comparison", "--next", "Read the floor plan and opening section"],
                   check=True, env=env)
    return home/"revisions"/revision/"outputs/Brochure"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    work = args.directory.resolve()
    home, manifest, assets = prepare(work)
    out = issue(work, home, manifest, assets)
    print(out/"Start here.html")
