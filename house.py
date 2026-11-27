"""House project starter with optional CAD route analysis."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

from room_by_room import house_backup
from room_by_room import house_checklist
from room_by_room import house_openings
from room_by_room import house_revisions as revisions

ROOT = Path(__file__).resolve().parent
HOUSES = ROOT / "houses"
TEMPLATES = ROOT / "templates"
GATES = ("brief", "existing-cad", "proposed-cad", "blender", "products", "final-ai", "handover")
ROOM_REGISTERS = ("layout-checks.csv", "activity-positions.csv", "route-journeys.csv", "finish-checks.csv", "decorator-finishes.csv")
VISUAL_EVIDENCE = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".tif", ".tiff"}
PRIVATE_DIRS = ("source", "models", "views", "handover")
RESERVED = {"con", "prn", "aux", "nul", *(f"{base}{n}" for base in ("com", "lpt") for n in range(1,10))}

def identifier(name):
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    if not slug or len(slug)>80 or slug in RESERVED:
        raise ValueError("Choose a shorter name containing letters or numbers.")
    return slug

def initialise(name, original, room_names):
    slug = identifier(name)
    HOUSES.mkdir(parents=True, exist_ok=True)
    dest = HOUSES / slug
    if dest.exists():
        raise ValueError(f"A project already exists at {dest}. Open its README.md to continue.")
    if original and not original.is_file():
        raise ValueError(f"Original brief file missing: {original}")
    with tempfile.TemporaryDirectory(dir=HOUSES) as tmp:
        stage = Path(tmp) / slug
        shutil.copytree(TEMPLATES / "house", stage)
        for folder in PRIVATE_DIRS:
            (stage / folder).mkdir()
        (stage / "rooms").mkdir()
        (stage / 'source' / 'original-brief').mkdir()
        if original:
            folder = stage / "source" / "original-brief"
            saved_brief = folder / original.name
            shutil.copy2(original, saved_brief)
            with (stage / "sources.csv").open("a", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerow((
                    "E01", "Original brief", saved_brief.relative_to(stage).as_posix(),
                    "", "Homeowner-supplied file", "As supplied", "Initial scope",
                ))
        for file in stage.glob("*.md"):
            content = file.read_text(encoding="utf-8").replace("{{house}}",name)
            if dest.parent.parent.resolve() != ROOT:
                # An external library can move independently of the toolkit, including to another drive.
                content = re.sub(r"\[([^\]]+)\]\(\.\./\.\./((?:docs/|skills/|README\.md)[^)]+)\)",
                                 r"\1 (toolkit: `\2`)", content)
            file.write_text(content, encoding="utf-8")
        (stage/"project.json").write_text(json.dumps({"name":name,"id":slug,"version":2},indent=2)+"\n",encoding="utf-8")
        for room in room_names:
            add_room(stage, room, refresh_checklist=False)
        house_checklist.refresh(stage, published=dest)
        revisions.publish_directory(stage, dest)
    return dest

def project(name):
    path = HOUSES / identifier(name)
    if not (path / "project.json").is_file():
        raise ValueError(f"House not found: {name}. Use 'list' to see your houses.")
    return path

def add_room(path, name, *, refresh_checklist=True):
    slug = identifier(name)
    rooms = path / "rooms"
    rooms.mkdir(exist_ok=True)
    dest = rooms / slug
    if dest.exists():
        raise ValueError(f"Room already exists: {dest.name}. Its work has been preserved.")
    with tempfile.TemporaryDirectory(dir=rooms) as tmp:
        stage = Path(tmp) / slug
        stage.mkdir()
        content=(TEMPLATES/"room.md").read_text(encoding="utf-8").replace("{{room}}",name)
        (stage/"README.md").write_text(content,encoding="utf-8")
        for name in ROOM_REGISTERS:
            shutil.copyfile(TEMPLATES/name, stage/name)
        with (stage/"review.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.writer(f)
            writer.writerow(["stage","status","revision","evidence","reviewer","finding","hold_scope"])
            writer.writerows((g,"pending","","","","","") for g in GATES)
        stage.rename(dest)
    if refresh_checklist:
        house_checklist.try_refresh(path)

def check_layout_evidence(house_path, room_path, revision):
    checks = room_path / "layout-checks.csv"
    if not checks.is_file():
        return "add layout-checks.csv with prepare-reviews, then record this revision's checks"
    with checks.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = {"revision", "kind", "source", "expectation", "observed", "evidence", "result"}
        if not fields.issubset(reader.fieldnames or ()):
            return "layout-checks.csv is missing required columns"
        rows = [row for row in reader if row.get("revision") == revision]
    required = {"intent", "use", "journey", "whole-room"}
    climate = {"external-shadow", "seated-glare", "summer-heat", "winter-cold"}
    brief = room_path / "README.md"
    tagged = brief.is_file() and re.search(
        r"^Glazing review:[ \t]*required[ \t]*\r?$", brief.read_text(encoding="utf-8-sig"), re.I | re.M
    )
    named = re.search(r"(?:^|-)(?:conservatory|sun-?room|winter-garden|orangery)(?:-|$)", room_path.name)
    if named or tagged or any(row.get("kind") in climate for row in rows):
        required.update(climate)
    missing = required.difference(row.get("kind") for row in rows)
    if missing:
        return "missing current layout checks: " + ", ".join(sorted(missing))
    positions = room_path / "activity-positions.csv"
    if positions.is_file():
        with positions.open(encoding="utf-8-sig", newline="") as f:
            inventory = csv.DictReader(f)
            if not {"check_id", "activity", "position"}.issubset(inventory.fieldnames or ()):
                return "activity-positions.csv is missing required columns"
            expected = {}
            for entry in inventory:
                if not all((entry.get(k) or "").strip() for k in ("check_id", "activity", "position")):
                    return "incomplete activity or position in the room brief"
                key = entry["check_id"].strip()
                if key in expected:
                    return f"duplicate position ID in the room brief: {key}"
                expected[key] = f"{entry['activity']} / {entry['position']}"
        observed = [(r.get("check_id") or "").strip() for r in rows if r.get("kind") == "use"]
        for key, description in expected.items():
            if observed.count(key) != 1:
                return f"expected one current use check for {description} ({key})"
    route_reviews = {}
    inventory_file = room_path / "route-journeys.csv"
    if inventory_file.is_file():
        with inventory_file.open(encoding="utf-8-sig", newline="") as stream:
            inventory = csv.DictReader(stream)
            if not {"journey_id", "routine"}.issubset(inventory.fieldnames or ()):
                return "route-journeys.csv is missing required columns"
            declared = set()
            for entry in inventory:
                key = (entry["journey_id"] or "").strip()
                if not key or not (entry["routine"] or "").strip() or key in declared:
                    return "give each modelled journey a unique ID and a household routine"
                declared.add(key)
        recorded = [r.get("check_id") for r in rows if r["kind"] == "journey"]
        for key in sorted(declared):
            if recorded.count("route:" + key) != 1:
                return f"expected one current route study for {key}"
    for row in rows:
        if row.get("kind") not in required:
            return f"unknown layout check kind: {row.get('kind')}"
        if row.get("result") != "pass":
            return f"unresolved layout check: {row.get('expectation') or 'unnamed check'}"
        if not all((row.get(k) or "").strip() for k in ("source", "expectation", "observed", "evidence")):
            return "layout check lacks a source, expectation, observation or evidence"
        evidence = (house_path / row["evidence"]).resolve()
        if Path(row["evidence"]).is_absolute() or house_path.resolve() not in evidence.parents or not evidence.is_file():
            return "layout check evidence file missing from this house"
        if row["kind"] in climate and not evidence.is_relative_to(
            (house_path / revisions.HISTORY / revision / "outputs").resolve()
        ):
            return "link the seasonal comfort evidence from this room's current saved revision"
        route_id = (row.get("check_id") or "").strip()
        if row["kind"] == "journey" and (route_id.startswith("route:") or evidence.name.endswith(".routes.json")):
            if not route_id.startswith("route:") or not evidence.name.endswith(".routes.json"):
                return "link the route study and its route:<journey> ID"
            if evidence not in route_reviews:
                try:
                    route_reviews[evidence] = route_report(house_path, row["evidence"], revision)
                except (OSError, ValueError) as exc:
                    return str(exc)
            result = route_reviews[evidence]["journeys"].get(route_id[6:])
            if result is None:
                return f"journey missing from route study: {route_id}"
            if result["status"] != "fits" and not result.get("retained_constraint"):
                return f"{route_id} / {route_summary(result)}"
        if row["kind"] == "whole-room" and evidence.suffix.lower() not in {
            ".fcstd", ".dxf", ".dwg", ".svg", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"
        }:
            return "whole-room evidence must link to the reviewed CAD plan or its drawing export"
    return None

def house_evidence(house_path, value):
    relative = Path(value or "")
    file = (house_path / relative).resolve()
    if not relative.is_absolute() and house_path.resolve() in file.parents and file.is_file():
        return file
    return None


def route_report(house_path, relative, revision, option=None):
    path = house_evidence(house_path, relative)
    if not path or not path.name.endswith(".routes.json"):
        raise ValueError("Link a .routes.json study within this house")
    try:
        from room_by_room.house_routes import analyse, number
    except ImportError as exc:
        raise ValueError("Install route dependencies with python -m pip install -r requirements/routes.txt") from exc
    study = json.loads(path.read_text(encoding="utf-8-sig"))
    try:
        if study["revision"] != revision:
            raise ValueError("Route study differs from the requested CAD revision")
        source = house_evidence(house_path, study["source"])
        if not source:
            raise ValueError("Link the CAD read-back or measured source within this house")
        if study.get("source_sha256"):
            raw = source.read_bytes()
            if source.suffix.lower() in {".json", ".csv", ".md", ".txt", ".svg"}:
                raw = raw.replace(b"\r\n", b"\n")
            if hashlib.sha256(raw).hexdigest() != study["source_sha256"]:
                raise ValueError("Source changed since the route export. Reopen the CAD and refresh the affected study")
        chosen = option if option is not None else study.get("review_option", "baseline")
        if chosen != "baseline" and not house_evidence(house_path, study.get("authority")):
            raise ValueError("Link the house decision authorising this option")
        if option is None and chosen != "baseline" and not house_evidence(house_path, study.get("selection")):
            raise ValueError("Link the homeowner selection or delegated choice for the reviewed option")
        journeys = analyse(study, chosen)
        if chosen != "baseline":
            reference = analyse(study, "baseline")
            for name, result in journeys.items():
                result["baseline_mm"] = reference[name]["tested_mm"]
                result["baseline_status"] = reference[name]["status"]
                limit = study["journeys"][name].get("max_loss_mm")
                if limit is not None:
                    if number(limit, "Allowed clearance loss") < 0:
                        raise ValueError("Allowed clearance loss cannot be negative")
                    if result["status"] == "fits" and result["baseline_mm"] - result["tested_mm"] > limit:
                        result.update(status="review", finding="Clearance loss exceeds the household's agreed limit")
        for name, result in journeys.items():
            kept = study["journeys"][name].get("retained_constraint")
            if kept and kept["option"] == chosen and result["status"] == "restricted":
                if (result.get("baseline_status", "restricted") == "restricted"
                        and result["tested_mm"] >= result.get("baseline_mm", result["tested_mm"])
                        and kept["reason"].strip() and house_evidence(house_path, kept["decision"])):
                    result["retained_constraint"] = kept["reason"]
        return {"revision": revision, "option": chosen, "source": study["source"],
                "basis": study["basis"], "journeys": journeys}
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Invalid route study {path.name}: {exc}") from exc


def route_summary(result):
    text = f"{result['status']} / {result['tested_mm']} mm modelled against {result['required_mm']} mm study target"
    if "beside" in result:
        text += f" / drawn path {result['path_clearance_mm']} mm by {result['beside']}"
    if result["status"] == "review":
        text += " / " + result["finding"]
    if "baseline_mm" in result:
        text += f" / reference {result['baseline_mm']} mm"
    if result["measurements"]:
        text += " / check " + ", ".join(result["measurements"])
    if result.get("retained_constraint"):
        text += " / retained by decision: " + result["retained_constraint"]
    return text


def check_finish_evidence(house_path, room_path, revision, stage="products"):
    register = room_path / "finish-checks.csv"
    if not register.is_file():
        return "add finish-checks.csv with prepare-reviews and record the lighting and finish comparisons"
    required = {"revision", "kind", "subject", "source", "evidence", "finding", "result"}
    with register.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or ()):
            return "finish-checks.csv is missing review columns"
        current = [row for row in reader if row["revision"] == revision]
    kinds = {row["kind"] for row in current}
    if kinds - {"lighting", "finish", "room-palette", "palette", "ai-colour"}:
        return "unknown finish check kind"
    if stage == "final-ai":
        current = [row for row in current if row["kind"] == "ai-colour"]
        if not current:
            return "record the final image colour comparison with the reviewed Blender camera"
    elif not {"lighting", "finish"}.issubset(kinds):
        return "record current lighting and finish comparisons"
    elif "room-palette" not in kinds:
        return "record the whole-room palette review for this revision before releasing the final camera"
    else:
        current = [row for row in current if row["kind"] != "ai-colour"]
    for row in current:
        kind = row["kind"]
        if kind == "palette" and row["result"] != "pass":
            question = row["finding"] or "ask the homeowner which option to carry forward"
            return f"resolve the open palette choice for {row['subject']} before releasing the final camera: {question}"
        if kind == "room-palette" and row["result"] != "pass":
            return f"resolve the whole-room palette finding for {row['subject']}: {row['finding'] or 'review the furnished view'}"
        if kind == "ai-colour" and row["result"] != "pass":
            return f"resolve the final image colour finding for {row['subject']}"
        if row["result"] != "pass" or not all((row[field] or "").strip() for field in ("subject", "source", "finding")):
            return "resolve the lighting and finish findings for this revision"
        evidence = house_evidence(house_path, row["evidence"])
        if kind == "room-palette":
            if not house_evidence(house_path, row["source"]):
                return "link the room brief or recorded palette decision within this house"
            if not evidence or evidence.suffix.lower() not in VISUAL_EVIDENCE:
                return "link the reviewed furnished room view within this house"
            continue
        if kind == "palette":
            if not evidence:
                return "link the homeowner's choice or delegated decision within this house"
            continue
        if not evidence or evidence.suffix.lower() not in VISUAL_EVIDENCE:
            return "link the reviewed lighting or finish comparison image within this house"
        if kind == "ai-colour":
            camera = house_evidence(house_path, row["source"])
            if not camera or camera.suffix.lower() not in VISUAL_EVIDENCE or camera.samefile(evidence):
                return "link the reviewed Blender camera and final image as separate files within this house"
    return None


def check_decorator(house_path, room_path, revision, surface=None):
    register = room_path / "decorator-finishes.csv"
    if not register.is_file():
        return "add decorator-finishes.csv with prepare-reviews and record the requested surfaces"
    with register.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"revision", "surface", "manufacturer", "colour", "code", "finish", "status", "evidence"}
        if not required.issubset(reader.fieldnames or ()):
            return "decorator-finishes.csv is missing specification columns"
        rows = [row for row in reader if row["revision"] == revision]
    if surface is not None:
        rows = [row for row in rows if (row["surface"] or "").strip().casefold() == surface.strip().casefold()]
    if not rows:
        return f"no decorator finish recorded for {surface or 'this room'} at {revision}"
    seen = set()
    for row in rows:
        name = (row["surface"] or "").strip()
        if not name or name.casefold() in seen:
            return "give each specified surface one distinct entry for this revision"
        seen.add(name.casefold())
        if row["status"] != "approved":
            return f"{name}: {row['status'] or 'awaiting selection'}"
        if not all((row[key] or "").strip() for key in ("manufacturer", "colour", "finish")):
            return f"{name}: record the manufacturer, named colour and finish"
        if not house_evidence(house_path, row["evidence"]):
            return f"{name}: link the recorded sample approval or explicit finish instruction within this house"
    return None

def review_rows(room):
    with room.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    stages = tuple(row.get("stage") for row in rows)
    if stages == ("brief", "cad", *GATES[3:]):
        rows[1]["stage"] = "proposed-cad"
        rows.insert(1, {"stage": "existing-cad", "status": "pending",
                        "finding": "Record a separate comparison with source plans and photographs."})
    elif stages != GATES:
        raise ValueError(f"Unexpected review stages in {room}")

    return rows

def status_through(path, room, rows, through, *, verified=None, passed=None):
    revision = None
    config = revisions.stored_json(path / "project.json")
    legacy = config.get("legacy_output_revisions", {}).get(room.parent.name, [])
    verified = {} if verified is None else verified
    for row in rows:
        stage, state = row["stage"], row["status"]
        if state not in ("pending", "hold", "pass"):
            raise ValueError(f"Unknown status in {room}: {state}")
        if row.get("hold_scope") and not (stage == "products" and state == "hold" and row["hold_scope"] == "purchase"):
            return False, f"{stage} / use hold_scope=purchase only for a purchase-only product hold"
        if state != "pass" and row.get("hold_scope") != "purchase":
            finding = f" / {row['finding']}" if row["finding"] else ""
            return False, f"{stage} / {state}{finding}"
        ref = (path / row["evidence"]).resolve()
        if not (row["reviewer"].strip() and row["revision"].strip() and row["finding"].strip()
                and path.resolve() in ref.parents and ref.is_file()):
            return False, f"{stage} / evidence or review details missing"
        if revision and row["revision"] != revision:
            return False, f"{stage} / revision differs from preceding handover"
        revision = row["revision"]
        parts = ref.relative_to(path.resolve()).parts
        if parts[0] == revisions.WORK:
            return False, f"{stage} / hold / save the draft and link its published output"
        if parts[0] == revisions.HISTORY:
            if len(parts) < 4 or parts[2] != "outputs":
                return False, f"{stage} / hold / link an output from the saved revision"
            try:
                if parts[1] not in verified:
                    verified[parts[1]] = revisions.verify_revision(path, parts[1])
                if "/".join(parts[3:]) not in verified[parts[1]]["outputs"]:
                    return False, f"{stage} / hold / evidence is missing from the saved revision"
            except (OSError, ValueError, KeyError) as exc:
                return False, f"{stage} / hold / cannot verify saved evidence: {exc}"
        elif stage != "brief" and config["version"] >= 2 and revision not in legacy:
            return False, f"{stage} / hold / save a revision and link its published output"
        if stage == "proposed-cad":
            problem = check_layout_evidence(path, room.parent, revision)
            if problem:
                return False, f"{stage} / hold / {problem}"
        if stage == "blender" or (stage == "proposed-cad" and revision not in legacy):
            problem = house_openings.registered_review(path, room.parent.name, revision,
                                                       camera=stage == "blender", verified=verified, walkthrough=True)
            if problem:
                return False, f"{stage} / hold / {problem}"
        if stage in ("products", "final-ai"):
            problem = check_finish_evidence(path, room.parent, revision, stage)
            if problem:
                return False, f"{stage} / hold / {problem}"
        if stage == "handover" and verified.get(revision, {}).get("delivery_format"):
            try:
                revisions.verify_room_pack(revisions.record_dir(path, revision) / "outputs", room.parent,
                                           revision, {entry["stage"]: entry for entry in rows},
                                           photo_quality=verified[revision]["delivery_format"] >= 2,
                                           require_windows=verified[revision]["delivery_format"] >= 3,
                                           require_details=verified[revision]["delivery_format"] >= 4,
                                           require_heads=verified[revision]["delivery_format"] >= 5,
                                           require_operation=verified[revision]["delivery_format"] >= 6)
            except (OSError, ValueError) as exc:
                return False, f"handover / hold / {exc}"
        if passed is not None:
            passed.append(stage)
        if stage == through:
            return True, f"reviewed through {through} / {revision}"
    raise ValueError(f"Unknown review stage: {through}")

def opening_folder(path, revision):
    folder = revisions.record_dir(path, revision)
    if folder.is_dir():
        return folder
    return revisions.local_path(path, f"{revisions.WORK}/{revisions.revision_id(revision)}")

def render_status(path, room, stage, *, input_revision=None, scene_revision=None):
    before = {"blender": "proposed-cad", "final-ai": "products"}[stage]
    rows = review_rows(room)
    passed, reason = status_through(path, room, rows, before)
    if not passed:
        return False, reason
    target = next(row for row in rows if row["stage"] == stage)
    if target["status"] == "hold":
        return False, f"{stage} / hold / {target['finding']}"
    if target["status"] not in ("pending", "pass"):
        raise ValueError(f"Unknown status for {stage}: {target['status']}")
    reviewed_revision = next(row["revision"] for row in rows if row["stage"] == before)
    if input_revision is not None and input_revision != reviewed_revision:
        return False, f"{stage} / hold / input revision {input_revision} differs from reviewed {reviewed_revision}"
    if stage == "blender":
        scene = revisions.revision_id(scene_revision or reviewed_revision)
        folder = opening_folder(path, scene)
        if folder.parent.name == revisions.HISTORY and scene != reviewed_revision:
            revisions.verify_revision(path, scene)
        if scene == reviewed_revision:
            problem = house_openings.registered_review(path, room.parent.name, scene, camera=True, walkthrough=True)
        else:
            problem = house_openings.review(folder, room.parent.name, scene, camera=True,
                                            cad_folder=revisions.record_dir(path, reviewed_revision), cad_revision=reviewed_revision, walkthrough=True)
        if problem:
            return False, f"blender / hold / {problem}"
    return True, f"{stage} may proceed / {reason}"

def read_status(path):
    lines = [f"{review.parent.name}: {status_through(path, review, review_rows(review), 'handover')[1]}"
             for review in sorted((path / "rooms").glob("*/review.csv"))]
    return lines or ["Add the rooms and shared spaces from your floor plan."]

def main():
    global HOUSES
    parser=argparse.ArgumentParser(description="Start a house design or pick up an existing one.")
    parser.add_argument("--houses-dir", type=Path, help="Use a separate house library, e.g. for a recovery drill")
    sub=parser.add_subparsers(dest="action",required=True)
    start=sub.add_parser("start",help="Create a house folder and its homeowner brief")
    start.add_argument("name")
    start.add_argument("--brief-file",type=Path,help="Copy an original email export, document or note unchanged")
    start.add_argument("--room",action="append",default=[],help="Add a room or activity zone; repeat as needed")
    sub.add_parser("list",help="List house projects")
    room=sub.add_parser("add-room",help="Add a room brief and review record")
    room.add_argument("house")
    room.add_argument("name")
    checklist = sub.add_parser("checklist", help="Refresh the house checklist from the room and survey evidence")
    checklist.add_argument("house")
    status=sub.add_parser("status",help="Show the first outstanding handover for each room")
    status.add_argument("house")
    choice = sub.add_parser("next", help="Show the next homeowner choice or its recorded reply")
    choice.add_argument("house")
    choice.add_argument("revision", nargs="?")
    ask = sub.add_parser("ask", help="Check and record a mid-study question, then print it ready for the homeowner")
    ask.add_argument("house")
    ask.add_argument("revision")
    ask.add_argument("--ask", required=True, help="Question to present against the open revision")
    answer = sub.add_parser("answer", help="Record the homeowner's actual handover reply")
    answer.add_argument("house")
    answer.add_argument("revision")
    answer.add_argument("reply")
    begin = sub.add_parser("begin-revision", help="Open a fresh private workspace for house outputs")
    begin.add_argument("house")
    begin.add_argument("revision")
    begin.add_argument("--from", dest="parent", help="Start from a private copy of this saved revision's outputs")
    begin.add_argument("--input", dest="inputs", action="append", default=[], help="Snapshot a house-relative input file (repeatable)")
    begin.add_argument("--pack-request", help="Freeze a house-relative component issue request")
    visual = sub.add_parser("check-visual", help="Check the approved design and derivative for one intended placement")
    visual.add_argument("house")
    visual.add_argument("visual_id")
    for field in ("purpose", "phase", "scope", "view"):
        visual.add_argument("--"+field, required=True)
    visual.add_argument("--page", type=int, default=1)
    design = sub.add_parser("check-design", help="Read the recorded arrangement and its source decision")
    design.add_argument("house")
    design.add_argument("state")
    design.add_argument("--scope", required=True)
    for cmd, description in (("plan-pack", "Check the requested components and source evidence"),
                             ("build-pack", "Build standalone components and their portable issue"),
                             ("check-pack", "Verify the exact issue files and record an optional reader review")):
        pack = sub.add_parser(cmd, help=description)
        pack.add_argument("house")
        pack.add_argument("revision")
        if cmd == "check-pack":
            pack.add_argument("--reviewer")
            pack.add_argument("--finding", help="What you checked in the extracted recipient files")
    save = sub.add_parser("save-revision", help="Back up the whole house and publish the verified revision")
    save.add_argument("house")
    save.add_argument("revision")
    save.add_argument("--ask", help="One homeowner question to present at this handover")
    for command in (ask, save):
        command.add_argument("--question-kind", choices=revisions.QUESTION_KINDS,
                             help="Defaults to visual. Use a text category for a non-spatial choice.")
        command.add_argument("--ask-image", help="Decision image path relative to this revision's outputs")
        command.add_argument("--image-description", help="What the homeowner should see in the decision image")
    for flag, help_text in (("change", "What changed"), ("why", "Decision or reason"),
                            ("by", "Person or agent responsible"), ("affects", "Rooms, costs or other work affected"),
                            ("next", "Next action, decision or hold")):
        save.add_argument("--" + flag, required=True, help=help_text)
    history = sub.add_parser("history", help="Read the house's saved changes, reasons and next actions")
    history.add_argument("house")
    history.add_argument("revision", nargs="?", help="Show the input and output paths for one revision")
    verify = sub.add_parser("verify-revision", help="Verify saved private inputs and outputs against the recorded hashes")
    verify.add_argument("house")
    verify.add_argument("revision")
    backup = sub.add_parser("backup", help="Write a new verified ZIP of one whole house, including private files")
    backup.add_argument("house")
    backup.add_argument("archive", type=Path)
    restore = sub.add_parser("restore", help="Restore and verify the named house, preserving existing files")
    restore.add_argument("house")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--to", type=Path, help="Recover into a separate house folder")
    prepare = sub.add_parser("prepare-reviews", help="Add missing room check registers to an existing house")
    prepare.add_argument("house")
    openings = sub.add_parser("check-openings", help="Check a CAD or furnished-scene opening study in a draft or saved revision")
    openings.add_argument("house")
    openings.add_argument("room")
    openings.add_argument("--input-revision", required=True)
    openings.add_argument("--camera", action="store_true", help="Check geometry in the actual furnished Blender scene")
    openings.add_argument("--door-heads-only", action="store_true", help="Review doorway elevations for a planning concept")
    openings.add_argument("--current", action="store_true", help="Apply a saved addendum to its registered room revision")
    openings.add_argument("--cad-revision", help="Checked CAD inventory when the furnished draft has its own revision")
    for command, purpose in (
        ("check-study", "Verify the existing shell before an unrendered furniture study"),
        ("check-layout", "Verify the occupied proposed layout before furnishing"),
    ):
        check = sub.add_parser(command, help=purpose)
        check.add_argument("house")
        check.add_argument("room")
        check.add_argument("--input-revision", help="Revision read from the native study input")
    outside = sub.add_parser("check-exterior-photos", help="Check each exterior window against its owning room")
    outside.add_argument("house")
    outside.add_argument("--input-revision", required=True)
    outside.add_argument("--final", action="store_true", help="Require all visible window treatments to match for house issue")
    room_photos = sub.add_parser("check-room-photos", help="Check required views, camera comparisons and sightlines")
    room_photos.add_argument("house")
    room_photos.add_argument("room")
    room_photos.add_argument("--input-revision", required=True)
    photos = sub.add_parser("check-house-photos", help="Check every room photo and its visible adjoining rooms")
    photos.add_argument("house")
    assemble = sub.add_parser("pack-house-photos", help="Build the checked whole-house room pack in an open revision")
    assemble.add_argument("house")
    assemble.add_argument("revision")
    render = sub.add_parser("check-render", help="Check the room's prerequisites and explicit render hold")
    render.add_argument("house")
    render.add_argument("room")
    render.add_argument("stage", choices=("blender", "final-ai"))
    render.add_argument("--input-revision", help="Revision read from the actual CAD or camera input")
    render.add_argument("--scene-revision", help="Furnished Blender snapshot or draft, when separate from the CAD input")
    decorator = sub.add_parser("check-decorator", help="Check specified finishes for decorator issue")
    decorator.add_argument("house")
    decorator.add_argument("room")
    decorator.add_argument("--input-revision", required=True, help="Revision of the decorator schedule being issued")
    decorator.add_argument("--surface", help="Check just this named surface")
    routes = sub.add_parser("check-routes", help="Assess a saved CAD route study without releasing or editing a design")
    routes.add_argument("house")
    routes.add_argument("study", help="House-relative .routes.json input")
    routes.add_argument("--input-revision", required=True)
    routes.add_argument("--option", help="Named study option or baseline")
    routes.add_argument("--json", action="store_true", help="Include paths and pinch coordinates for CAD")
    routes.add_argument("--require-walked-path", action="store_true",
                        help="Fail unless every journey supplies a recorded trajectory that fits")
    args=parser.parse_args()
    if args.houses_dir:
        HOUSES = args.houses_dir.expanduser().resolve()
        if HOUSES.is_relative_to(ROOT) and HOUSES != ROOT / "houses":
            parser.error("Choose a separate house library outside the checkout.")
    if args.action=="start":
        path = initialise(args.name, args.brief_file, args.room)
        print("Open", path / "README.md")
        print("Checklist", path / "CHECKLIST.md")
    elif args.action=="list":
        files=sorted(HOUSES.glob("*/project.json"))
        for file in files:
            print(json.loads(file.read_text(encoding="utf-8"))["name"],"|",file.parent/"README.md")
        if not files: print("No houses yet. Start with: python house.py start \"My house\"")
    elif args.action=="add-room":
        path=project(args.house)
        add_room(path,args.name)
        print("Open",path/"rooms"/identifier(args.name)/"README.md")
    elif args.action == "checklist":
        print(house_checklist.refresh(project(args.house)))
    elif args.action == "begin-revision":
        print(revisions.begin(project(args.house), args.revision, args.parent, args.inputs, pack_request=args.pack_request))
    elif args.action == "check-visual":
        from room_by_room.house_visuals import Catalogue
        proof = Catalogue(project(args.house)).approve(visual_id=args.visual_id, purpose=args.purpose, phase=args.phase,
                                                       scope=args.scope, view=args.view, page=args.page)
        print(f"{proof['id']} | {proof['state_id']} ({proof['design']['status']}) | {args.purpose} | {args.scope}")
    elif args.action == "check-design":
        from room_by_room.house_visuals import Catalogue
        register = Catalogue(project(args.house), design_only=True)
        state = register.design(args.state, register.states.get(args.state, {}).get("phase"), args.scope, accepted=True)
        print(json.dumps(state, ensure_ascii=False, indent=2))
    elif args.action in ("plan-pack", "build-pack", "check-pack"):
        from room_by_room import house_delivery
        print(house_delivery.command(project(args.house), args.revision, args.action,
                                     getattr(args, "reviewer", None), getattr(args, "finding", None)))
    elif args.action == "save-revision":
        saved = revisions.save(project(args.house), args.revision, change=args.change, why=args.why,
                               author=vars(args)["by"], affects=args.affects, next_step=args.next, question=args.ask,
                               question_image=args.ask_image, image_description=args.image_description,
                               question_kind=args.question_kind)
        print(saved)
        print("Verified private backup:", house_backup.backup_directory() / revisions.stored_json(saved / "record.json")["backup"])
        if revisions.stored_json(saved / "record.json").get("question"):
            path = project(args.house)
            print(revisions.next_choice(path, revisions.records(path), args.revision))
    elif args.action == "ask":
        path = project(args.house)
        revisions.ask(path, args.revision, args.ask, args.question_kind, args.ask_image, args.image_description)
        print(revisions.next_choice(path, revisions.records(path), args.revision))
    elif args.action == "next":
        path = project(args.house)
        house_checklist.try_refresh(path)
        print(revisions.next_choice(path, revisions.records(path), args.revision))
    elif args.action == "answer":
        print("Recorded homeowner reply:", revisions.record_answer(project(args.house), args.revision, args.reply))
    elif args.action == "history":
        path = project(args.house)
        if args.revision:
            record = revisions.stored_json(revisions.record_dir(path, args.revision) / "record.json")
            print(revisions.describe(record, files=True))
        else:
            print("\n\n".join(revisions.describe(record) for record in revisions.records(path))
                  or "No saved revisions yet. Earlier house work is listed on the dashboard.")
    elif args.action == "verify-revision":
        record = revisions.verify_revision(project(args.house), args.revision)
        print(f"{record['revision']} verified: {len(record['inputs'])} inputs, {len(record['outputs'])} outputs")
    elif args.action == "backup":
        count = house_backup.backup(project(args.house), args.archive, ROOT)
        print(f"Verified {count} house files in {args.archive}")
    elif args.action == "restore":
        house_id = identifier(args.house)
        target = args.to.expanduser() if args.to else HOUSES / house_id
        if target.resolve().is_relative_to(ROOT) and target.resolve() != ROOT / "houses" / house_id:
            parser.error("Restore to the named house or choose a separate folder outside the checkout.")
        count = house_backup.restore(house_id, args.archive, target)
        print(f"Restored {count} missing files to {target}")
    elif args.action == "prepare-reviews":
        path = project(args.house)
        for review in sorted((path / "rooms").glob("*/review.csv")):
            for name in ROOM_REGISTERS:
                register = review.with_name(name)
                try:
                    with register.open("x", encoding="utf-8") as f:
                        f.write((TEMPLATES / name).read_text(encoding="utf-8"))
                except FileExistsError:
                    continue
                print("Added", register.relative_to(path))
    elif args.action == "check-routes":
        report = route_report(project(args.house), args.study, args.input_revision, args.option)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for name, result in report["journeys"].items():
                print(f"{name} / {report['option']} / {route_summary(result)}")
        if args.require_walked_path and any(
                result.get("path_kind") != "recorded" or result["status"] != "fits"
                for result in report["journeys"].values()):
            sys.exit("Walkthrough held: every journey must have a checked recorded trajectory that fits.")
    elif args.action == "check-openings":
        path = project(args.house)
        room = identifier(args.room)
        if not (path / "rooms" / room / "review.csv").is_file():
            sys.exit(f"Unknown room: {args.room}")
        revision = revisions.revision_id(args.input_revision)
        folder = opening_folder(path, revision)
        if folder.is_dir() and folder.parent.name == revisions.HISTORY:
            revisions.verify_revision(path, revision)
        if not folder.is_dir():
            sys.exit(f"No open or saved revision: {revision}")
        cad = revisions.revision_id(args.cad_revision or revision)
        cad_folder = opening_folder(path, cad)
        if cad != revision and cad_folder.parent.name == revisions.HISTORY:
            revisions.verify_revision(path, cad)
        if args.current:
            if folder.parent.name != revisions.HISTORY or cad != revision:
                sys.exit("A current room check needs one registered saved CAD and scene revision")
            rows = review_rows(path / "rooms" / room / "review.csv")
            stage = "blender" if args.camera else "proposed-cad"
            registered = next(row["revision"] for row in rows if row["stage"] == stage)
            if registered != revision:
                sys.exit(f"{stage} / hold / requested {revision}, currently registered {registered or 'no revision'}")
            problem = house_openings.registered_review(path, room, revision, camera=args.camera, heads_only=args.door_heads_only)
        else:
            problem = house_openings.review(folder, room, revision, camera=args.camera, cad_folder=cad_folder, cad_revision=cad, heads_only=args.door_heads_only)
        label = "door heads" if args.door_heads_only else "opening clearance"
        if problem:
            sys.exit(f"{label} / hold / {problem}")
        print(f"{label} checked / {room} / {revision}")
    elif args.action == "check-decorator":
        path = project(args.house)
        problem = check_decorator(path, path / "rooms" / identifier(args.room), args.input_revision, args.surface)
        if problem:
            sys.exit(f"decorator / hold / {problem}")
        print(f"decorator finishes checked / {args.surface or args.room} / {args.input_revision}")
    elif args.action == "check-exterior-photos":
        from room_by_room import house_photos
        path = project(args.house)
        revision = revisions.revision_id(args.input_revision)
        folder = opening_folder(path, revision)
        if folder.parent.name == revisions.HISTORY:
            revisions.verify_revision(path, revision)
        inventory = house_photos.exterior_register(path).get(revision, {})
        if not inventory:
            raise ValueError("No current exterior photos registered for this revision")
        unresolved = []
        house_photos.exterior_review(path, folder / "outputs", revision, inventory, final=args.final, unresolved=unresolved)
        print(f"{len(inventory)} exterior photos checked / {revision}")
        if unresolved:
            print(f"{len(unresolved)} provisional window observations still need a return before house issue")
            print("\n".join(unresolved))
    elif args.action == "check-room-photos":
        from room_by_room import house_photos
        path = project(args.house)
        revision = revisions.revision_id(args.input_revision)
        folder = opening_folder(path, revision)
        if folder.parent.name == revisions.HISTORY:
            revisions.verify_revision(path, revision)
        room = path / "rooms" / identifier(args.room)
        report = house_photos.review(folder / "outputs", room, revision)
        print(f"{len(report['photos'])} room photos reviewed / {room.name} / {revision}")
    elif args.action in ("check-house-photos", "pack-house-photos"):
        from room_by_room import house_photos
        path = project(args.house)
        if args.action == "check-house-photos":
            print(f"{len(house_photos.house_issue(path))} files passed the whole-house photo check")
        else:
            folder = revisions.local_path(path, f"{revisions.WORK}/{revisions.revision_id(args.revision)}")
            if not (folder / "draft.json").is_file():
                raise ValueError("Begin a revision for the assembled house pack first")
            print(house_photos.package(path, folder / "outputs"))
    elif args.action in ("check-study", "check-layout", "check-render"):
        path = project(args.house)
        review = path / "rooms" / identifier(args.room) / "review.csv"
        if args.action == "check-render":
            passed, result = render_status(path, review, args.stage, input_revision=args.input_revision, scene_revision=args.scene_revision)
        else:
            stage = "existing-cad" if args.action == "check-study" else "proposed-cad"
            rows = review_rows(review)
            passed, result = status_through(path, review, rows, stage)
            if passed and args.input_revision is not None:
                revision = next(row["revision"] for row in rows if row["stage"] == stage)
                if args.input_revision != revision:
                    passed = False
                    result = f"{stage} / hold / input revision {args.input_revision} differs from reviewed {revision}"
        if not passed:
            sys.exit(result)
        print(result)
    else:
        path = project(args.house)
        house_checklist.try_refresh(path)
        print("\n".join(read_status(path)))
        saved = revisions.records(path)
        if saved:
            print("\nLatest saved work\n" + revisions.describe(saved[-1]))
        drafts = revisions.open_drafts(path)
        if drafts:
            print("Open drafts: " + ", ".join(drafts))
        choice = revisions.next_choice(path, saved, suggest=not drafts)
        if choice:
            print("\n" + choice)

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError) as exc:
        sys.exit(str(exc))
