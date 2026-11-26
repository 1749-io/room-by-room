"""Build and verify four illustrative deliveries through the public house commands."""
import argparse
import csv
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EDITIONS = {"ROOM": ["room-review"], "DRAWING": ["drawing"], "SHOP": ["shopping"],
            "COMPLETE": ["room-review", "drawing", "shopping"]}


def plan_drawing(path):
    """A fictional measured-room fixture. All its dimensions use 100 points per metre."""
    with fitz.open() as doc:
        page = doc.new_page(width=660, height=390)
        ink, wall, fern, amber = (0.12, 0.22, 0.19), (0.27, 0.34, 0.31), (0.48, 0.62, 0.51), (0.91, 0.79, 0.60)
        def label(x, y, value, size=10):
            page.insert_text((x, y), value, fontsize=size, color=ink)
        def rect(coords, colour):
            page.draw_rect(fitz.Rect(coords), color=ink, fill=colour, width=1)
        page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
        # Interior clear faces are x=28..408 and y=30..330.
        rect((22, 24, 414, 30), wall)
        rect((408, 30, 414, 336), wall)
        rect((22, 330, 414, 336), wall)
        rect((22, 30, 28, 204), wall)
        rect((22, 294, 28, 330), wall)
        rect((112, 30, 287, 59), fern)
        label(165, 48, "Bookcase")
        rect((295, 211, 366, 290), amber)
        label(314, 254, "Chair")
        page.draw_circle((383, 274), 9, color=ink, fill=amber)
        label(361, 301, "Lamp")
        page.draw_line((28, 294), (118, 294), color=ink, width=2)
        arc = page.new_shape()
        arc.draw_bezier((28, 204), (78, 204), (118, 244), (118, 294))
        arc.finish(color=wall, dashes="[4 3] 0", closePath=False)
        arc.commit()
        page.draw_line((190, 333), (325, 333), color=(0.51, 0.78, 0.86), width=5)
        label(177, 350, "South window")
        label(174, 18, "3,800 mm clear")
        label(37, 164, "3,000 mm clear")
        label(53, 312, "Hall door")
        label(455, 48, "Drawing key", 17)
        for y, colour, word in [(80, wall, "Existing wall"), (111, fern, "Fixed bookcase"), (142, amber, "Reading furniture")]:
            rect((456, y-10, 477, y), colour)
            label(489, y, word)
        page.draw_line((456, 169), (477, 169), color=wall, dashes="[4 3] 0")
        label(489, 173, "Door swing")
        page.draw_line((456, 201), (477, 201), color=(0.51, 0.78, 0.86), width=4)
        label(489, 205, "Window")
        page.draw_line((456, 264), (556, 264), color=ink, width=3)
        label(456, 281, "0")
        label(539, 281, "1 m")
        label(455, 329, "Top of sheet is north.")
        label(455, 350, "Fictional example / LIB-01")
        doc.save(path, garbage=4, deflate=True, no_new_id=True)


def run(work, *args):
    env = dict(os.environ, HOUSE_BACKUP_DIR=str(work / "backups"), PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(REPO / "house.py"), "--houses-dir",
                             str(work / "houses"), *args], env=env, capture_output=True, encoding="utf-8", check=False)
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare(work):
    name = "Alder Cottage"
    run(work, "start", name, "--room", "Library")
    home = work / "houses/alder-cottage"
    room = home / "rooms/library"
    (room / "README.md").write_text("# Library\n\nCAD-only assessment of reading and book access.\n", encoding="utf-8")
    schedule = home / "shopping.csv"
    fields = next(csv.reader(schedule.read_text().splitlines()))
    items = [
        {"item_id": "L01", "room": "Library", "product_and_variant": "Retained reading chair", "quantity": "1",
             "status": "Reuse", "finish": "Oak frame, sage linen", "unit_price_gbp": "0", "price_date": "2026-11-01",
             "fit_hold": "Existing chair remains in place."},
        {"item_id": "L02", "room": "Library", "product_and_variant": "Wall shelf, 875 mm", "quantity": "2",
             "status": "Proposed", "finish": "Oiled oak", "unit_price_gbp": "84.50", "price_date": "2026-11-01",
             "fit_hold": "Purchase held until the installer confirms the wall fixings."},
        {"item_id": "K01", "room": "Kitchen", "product_and_variant": "Kitchen-only mixer tap", "quantity": "1",
             "status": "Proposed", "unit_price_gbp": "99", "fit_hold": "Kitchen survey pending."},
    ]
    write_csv(schedule, fields, items)
    output = Path(run(work, "begin-revision", name, "LIB-01"))
    (output / "Library-geometry.py").write_text("import fitz\n\n" + inspect.getsource(plan_drawing), encoding="utf-8")
    plan_drawing(output / "Library-plan.pdf")
    run(work, "save-revision", name, "LIB-01", "--change", "Prepared fictional library baseline",
        "--why", "Exercise delivery from a saved drawing", "--by", "Example author",
        "--affects", "Library", "--next", "Check the sheet and room register")
    sys.path.insert(0, str(REPO))
    from room_by_room.house_visuals import checksum, signature
    def reference(filename):
        rel = "revisions/LIB-01/outputs/" + filename
        return {"revision": "LIB-01", "path": rel, "sha256": checksum(home / rel)}
    scope = "room/library"
    state = {"phase": "existing", "status": "observed", "scopes": [scope], "revision": "LIB-01",
             "arrangement": "Hall door opens clear of the chair and fixed bookcase.",
             "exclusions": ["Shelf fixings and socket location require a site check."],
             "geometry": [reference("Library-geometry.py")], "supersedes": [],
             "features": {"hall-door": {"description": "900 mm west-side hall door and swing",
                                       "scopes": [scope], "required_views": ["plan"]}}}
    sheet = reference("Library-plan.pdf")
    visual = {"state": "LIB-EXISTING", "state_sha256": signature(state), "status": "signed", "view": "plan",
              "source": sheet, "reviewer": "Fictional library drawing reviewer", "limitations": state["exclusions"],
              "placements": [{"purpose": p, "scope": scope} for p in
                             ("drawing", "room-review", "homeowner-presentation.opening", "homeowner-presentation.room",
                              "architect-pack.drawing", "buyer-brief.scenario", "buyer-brief.room")],
              "supersedes": [], "dependencies": state["geometry"], "features": {"hall-door": {
                  "visibility": "shown", "finding": "Swing and opening are labelled on L-01.", "evidence": sheet}}}
    for filename, records in [("design-states.json", {"states": {"LIB-EXISTING": state}}),
                              ("visual-approvals.json", {"visuals": {"LIB-PLAN-01": visual}})]:
        (home / filename).write_text(json.dumps(dict(version=1, house="alder-cottage", **records), indent=2),
                                    encoding="utf-8")
    register = room / "review.csv"
    with register.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows[:2]:
        row.update(status="pass", revision="LIB-01", reviewer="Example reviewer",
                   evidence="revisions/LIB-01/outputs/Library-plan.pdf",
                   finding="The 900 mm door swing is clear of the reading chair and fixed bookcase.")
    write_csv(register, rows[0].keys(), rows)
    run(work, "checklist", name)
    return home


def build_issue(work, home, issue, components, *, share_with=()):
    request = json.loads((HERE / "request.json").read_text(encoding="utf-8"))
    request["components"] = components
    if share_with:
        request["share_with"] = list(share_with)
    path = home / f"request-{issue}.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    name = "Alder Cottage"
    run(work, "begin-revision", name, issue, "--pack-request", path.name)
    run(work, "plan-pack", name, issue)
    result = run(work, "build-pack", name, issue)
    run(work, "check-pack", name, issue)
    return Path(result).parent.parent


def save_example(work, issue, finding, reviewer="Fictional fixture check"):
    run(work, "check-pack", "Alder Cottage", issue, "--reviewer", reviewer, "--finding", finding)
    run(work, "save-revision", "Alder Cottage", issue, "--change", "Issued the requested example files",
        "--why", "Exercise standalone and house delivery", "--by", reviewer, "--affects", "Fictional library",
        "--next", "Check the shelf fixings before ordering")
    run(work, "check-pack", "Alder Cottage", issue)


def build_house(work, home):
    source = HERE / "house-request.json"
    (home / source.name).write_bytes(source.read_bytes())
    run(work, "begin-revision", "Alder Cottage", "HOUSE", "--pack-request", source.name)
    run(work, "plan-pack", "Alder Cottage", "HOUSE")
    return Path(run(work, "build-pack", "Alder Cottage", "HOUSE")).parent.parent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New directory outside the repository")
    args = parser.parse_args()
    work = args.directory.resolve()
    work.mkdir(parents=True, exist_ok=False)
    home = prepare(work)
    for edition, components in EDITIONS.items():
        print(edition, build_issue(work, home, edition, components))
        save_example(work, edition, "Automated fixture checked the archived files against the frozen commission.")
    print("HOUSE", build_house(work, home))
    save_example(work, "HOUSE", "Verified that the house carries each separately issued component byte for byte.")
    print("Open", home / "revisions/HOUSE/outputs/pack/delivery/Start here.html")
