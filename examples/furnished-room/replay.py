"""Rehearse the checked Alder layout and furnished camera in a new scratch house."""
import argparse
import csv
import json
from pathlib import Path
import runpy
import shutil

from occupied_plan import build as occupied_plan
from opening_report import write_report


HERE = Path(__file__).resolve().parent
component = runpy.run_path(str(HERE.parent / "component-pack" / "replay.py"))
HOUSE, CAD, SCENE = "Alder Cottage", "LIB-CAD-01", "LIB-FURN-01"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def begin(work):
    if work.exists() and any(work.iterdir()):
        raise ValueError("Choose a new scratch directory for the example")
    home = component["prepare"](work)
    decision = read(HERE / "library.json")["decision"]
    room = home / "rooms/library"
    brief = ("The owner of this fictional house requests a furnished reading-room concept. "
             + decision["accepted"] + " Exclusions: " + decision["excluded"])
    (room / "README.md").write_text("# Library\n\nLIB-01 covered the CAD assessment.\n\n" + brief + "\n", encoding="utf-8")
    with (home / "decisions.md").open("a", encoding="utf-8") as stream:
        stream.write("\n| Fictional design acceptance | " + decision["accepted"] +
                     " | Develop the furnished concept | L01 and L02 | Installer to confirm fixings and socket. |\n")
    out = Path(component["run"](work, "begin-revision", HOUSE, CAD, "--from", "LIB-01", "--input", "rooms/library/README.md"))
    shutil.copyfile(HERE / "library.json", out / "library.json")
    (out / "Commission.md").write_text(brief + "\n", encoding="utf-8")
    return out


def inspect_layout(out):
    record = read(out / "Layout checks.json")
    write_report(out, out / "Alder library.FCStd", record, CAD, CAD)
    result = occupied_plan(out)
    write(out / "Occupied checks.json", result)
    return out / "Occupied library.pdf"


def accept_layout(work, home, out, reviewer):
    if not reviewer.strip():
        raise ValueError("Name the person who inspected this example layout")
    evidence = read(out / "Occupied checks.json")
    component["run"](work, "save-revision", HOUSE, CAD, "--change", "Record the occupied library layout",
                     "--why", "Check the two readers together", "--by", reviewer, "--affects", "Library",
                     "--next", "Match the furnished scene to the CAD revision")
    prefix = f"revisions/{CAD}/outputs/"
    room = home / "rooms/library"
    with (room / "review.csv").open(encoding="utf-8-sig", newline="") as stream:
        reviews = list(csv.DictReader(stream))
    checks = {
        "brief": ("Commission.md", "The fictional owner accepted the chair and bookcase arrangement."),
        "existing-cad": ("Alder library.FCStd", "Checked the clear room, retained chair and west opening."),
        "proposed-cad": ("Occupied library.pdf", "Inspected both readers, the parked leaf and the hall route together."),
    }
    for row in reviews:
        if row["stage"] in checks:
            file, finding = checks[row["stage"]]
            row.update(status="pass", revision=CAD, reviewer=reviewer, finding=finding, evidence=prefix + file)
    write_csv = component["write_csv"]
    write_csv(room / "review.csv", reviews[0].keys(), reviews)
    positions = [{"check_id": "reader", "activity": "Read seated", "position": "Retained chair"},
                 {"check_id": "browser", "activity": "Choose a book", "position": "North bookcase"}]
    write_csv(room / "activity-positions.csv", positions[0].keys(), positions)
    entries = [
        ("intent", "", "Retain the chair by the south window", "The chair faces west in its agreed footprint."),
        ("use", "reader", "Allow space beyond the seat", "The drawing includes 400 mm for knees and feet."),
        ("use", "browser", "Reach the bookcase", f"The standing position is {evidence['standing_reader_to_shelf_mm']:g} mm from the front."),
        ("journey", "", "Enter with the door parked", f"The {evidence['route_width_mm']} mm route clears the occupied chair by {evidence['route_to_occupied_chair_mm']} mm."),
        ("whole-room", "", "Read and browse together", "Both readers and the route are visible on the coordinated plan."),
    ]
    rows = [dict(revision=CAD, kind=k, check_id=i, source=prefix+"Commission.md", expectation=e, observed=o,
                 evidence=prefix+"Occupied library.pdf", result="pass") for k, i, e, o in entries]
    write_csv(room / "layout-checks.csv", rows[0].keys(), rows)
    component["run"](work, "checklist", HOUSE)
    print(component["run"](work, "check-layout", HOUSE, "Library", "--input-revision", CAD))
    return component["run"](work, "begin-revision", HOUSE, SCENE, "--from", CAD)


def check_camera(work, out):
    measured = read(out / "Scene checks.json")
    cad = read(out / "Layout checks.json")
    for name, limits in measured["bounds_mm"].items():
        if cad["bounds_mm"][name] != limits:
            raise ValueError(name + " no longer matches its reviewed CAD bounds")
    write_report(out, out / "Alder library.blend", measured, SCENE, CAD)
    return component["run"](work, "check-render", HOUSE, "Library", "blender",
                            "--input-revision", CAD, "--scene-revision", SCENE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("begin", "inspect-layout", "accept-layout", "check-camera"))
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--reviewer", help="Person who inspected the occupied layout")
    args = parser.parse_args()
    work = args.scratch.resolve()
    home = work / "houses/alder-cottage"
    drafts = home / ".revision-work"
    cad_out = drafts / CAD / "outputs"
    if args.step == "begin":
        print(begin(work))
    elif args.step == "inspect-layout":
        print(inspect_layout(cad_out))
    elif args.step == "accept-layout":
        if not args.reviewer:
            parser.error("Pass --reviewer after inspecting the occupied plan")
        print(accept_layout(work, home, cad_out, args.reviewer))
    else:
        print(check_camera(work, drafts / SCENE / "outputs"))
