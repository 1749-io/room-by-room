"""A homeowner-readable projection of the room gates, with a separate survey return trail."""
import csv
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from . import house_photos
from . import house_revisions as revisions

START = "<!-- BEGIN VERIFIED ROOM STATUS -->"
END = "<!-- END VERIFIED ROOM STATUS -->"
ACCEPT = "<!-- NEW ROOM ACCEPTANCES -->"
FIELDS = ("ref", "room", "question", "owner", "affects", "status", "return_evidence", "recheck_evidence")
SURVEY = {"required": "Required", "requested": "Requested", "returned": "Recheck due",
          "rechecked": "Rechecked", "not-required": "Not required"}


def clean(value):
    return " ".join(value.split()).replace("|", "&#124;")


def link(title, path):
    return f"[{clean(title)}]({quote(str(path).replace(chr(92), '/'), safe='/:')})"


def room_title(register):
    brief = register.with_name("README.md")
    if brief.exists():
        heading = brief.read_text(encoding="utf-8-sig").splitlines()
        if heading and heading[0].startswith("# "):
            return clean(heading[0][2:])
    return register.parent.name.replace("-", " ").capitalize()


def survey_rows(root, rooms):
    path = root / "survey-returns.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Keep the survey-returns.csv column headings from the house template.")
        rows = list(reader)
    seen = set()
    for row in rows:
        ref = row["ref"]
        if (not all(row.get(k) and row[k].strip() for k in FIELDS[:6]) or ref in seen
                or row["room"] not in {*rooms, "whole-house"} or row["status"] not in SURVEY):
            raise ValueError(f"Check survey return {ref!r}: give a unique reference, known room, owner, question, affected work and valid status.")
        seen.add(ref)
        needed = []
        if row["status"] in ("returned", "rechecked"):
            needed.append("return_evidence")
        if row["status"] == "rechecked":
            needed.append("recheck_evidence")
        for field in needed:
            if not row.get(field):
                raise ValueError(f"{ref}: link a retained house file in {field}.")
            path = revisions.local_path(root, row[field])
            if not path.is_file() or revisions.safe_relative(row[field]).parts[0] == revisions.WORK:
                raise ValueError(f"{ref}: link a retained house file in {field}.")
    return rows


def room_states(root, register, verified):
    import house
    rows = house.review_rows(register)
    passed = []
    complete, reason = house.status_through(root, register, rows, "handover", verified=verified, passed=passed)
    cells = []
    for i, row in enumerate(rows):
        if row["stage"] in passed:
            cells.append(link("Order held" if row.get("hold_scope") == "purchase" else "Pass", row["evidence"]))
        elif i == len(passed):
            cells.append("Pending" if row["status"] == "pending" else "**Hold**")
        else:
            cells.append("Hold" if row["status"] == "hold" else "Waiting")
    photo = "Waiting"
    neighbours = set()
    if complete:
        revision = rows[-1]["revision"]
        out = revisions.record_dir(root, revision) / "outputs"
        try:
            review = house_photos.review(out, register.parent, revision)
            for entry in review["photos"]:
                neighbours.update(n["room"] for n in entry["visible_rooms"] if n["status"] == "provisional")
            photo = link("Pass", f"revisions/{revision}/outputs/photo-reviews/{register.parent.name}.json")
        except (ValueError, KeyError, TypeError, OSError):
            photo = "Review due"
    return cells, complete, reason, photo, neighbours


def generated(root, published, registers, returns):
    import house
    relative = os.path.relpath(house.ROOT / "docs", published) if published.drive == house.ROOT.drive else (house.ROOT / "docs").as_posix()
    maps = link("Quick workflow diagram", relative + "/workflow-quick.svg") + " · " + link("Full workflow diagram", relative + "/workflow.svg")
    verified, body, blockers, neighbours = {}, [], [], set()
    issued = quality = 0
    for reg in registers:
        slug, title = reg.parent.name, room_title(reg)
        try:
            cells, complete, reason, photo, visible = room_states(root, reg, verified)
        except (OSError, ValueError, KeyError) as exc:
            cells = ["**Check register**"] + ["Waiting"] * (len(house.GATES) - 1)
            complete, photo, visible = False, "Waiting", set()
            reason = str(exc) if reg.is_file() else "Restore or create the room review register."
        issued += complete
        quality += photo.startswith("[Pass]")
        neighbours.update((title, name) for name in visible)
        if not complete:
            blockers.append(f"- **{title}** · {clean(reason)}")
        statuses = {row["status"] for row in returns if row["room"] == slug}
        survey = ", ".join(label for code, label in SURVEY.items() if code in statuses) or "Assess"
        source = reg if reg.exists() else reg.with_name("README.md")
        room_link = link(title, source.relative_to(root))
        body.append("| " + " | ".join([room_link, *cells, photo, survey]) + " |")
    lines = [maps, "", "## Current position", "",
             f"**{issued} of {len(registers)} rooms have passed concept handover.** "
             f"Current photo quality has passed in {quality} of {len(registers)} rooms.", ""]
    if issued > quality:
        outstanding = issued - quality
        noun = "room needs" if outstanding == 1 else "rooms need"
        lines.extend([f"{outstanding} issued {noun} the current photo review before whole-house publication.", ""])
    if registers and issued == quality == len(registers):
        try:
            house_photos.house_issue(root)
            assembly = "Ready to assemble. Issue the combined pack in its own revision."
        except (OSError, ValueError) as exc:
            assembly = "On hold. " + clean(str(exc))
    elif registers:
        assembly = "On hold until the room packs, photo reviews and visible adjoining rooms are ready."
    else:
        assembly = "Add the rooms and shared spaces from the brief."
    lines.extend(["**Whole-house photo issue.** " + assembly, ""])
    editions = {}
    for record in revisions.records(root):
        issue = record.get("pack_issue", {}).get("checked")
        if issue:
            key = (issue["audience"], issue["room"], tuple(sorted(issue["components"])))
            editions[key] = record["revision"], issue["archive"]
    if editions:
        lines.extend(["## Issued components", ""])
        for (audience, room, components), (revision, archive) in sorted(editions.items()):
            folder = f"revisions/{revision}/outputs/pack"
            lines.append(f"- {clean(audience)} · {clean(room)} · {', '.join(components)} · "
                         + link(revision, folder + "/delivery/Start here.html") + " · "
                         + link("Download ZIP", folder + "/" + archive))
        lines.append("")
    for rev, views in house_photos.exterior_register(root).items():
        lines.extend([f"**Exterior window review · {rev}.** {len(views)} registered views. "
                      + link("Window and room inventory", "exterior-views.csv")
                      + ". Check the outside face and operating state before whole-house issue.", ""])
    for subject, target in sorted(neighbours):
        lines.append(f"- {subject} shows {target.replace('-', ' ')} as provisional.")
    lines.extend(["", "## Room checks", "",
                  "Each Pass links to the reviewed evidence. Waiting follows an earlier open gate. "
                  "Order held means the product passed visual review and purchasing still needs a return.", "",
                  "| Room | Brief | Existing CAD | Occupied CAD | Blender | Products | Final photo | Room pack | Photo quality | Survey |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |", *body, "",
                  "## Next design checks", "", *(blockers or ["All registered concept packs have passed." if registers else "Add rooms to start their design reviews."]), "",
                  "## Survey follow-ups", "",
                  "Update the [survey register](survey-returns.csv) with the owner, affected work and evidence. "
                  "A returned measurement stays open until the affected design has been rechecked.", ""])
    totals = Counter(row["status"] for row in returns)
    if totals:
        lines.extend([" · ".join(f"{count} {SURVEY[status].lower()}" for status, count in totals.items()), ""])
    for row in returns:
        checked = "x" if row["status"] in ("rechecked", "not-required") else " "
        source = [link(title, row[key]) for key, title in (("return_evidence", "Return"), ("recheck_evidence", "Recheck")) if row[key]]
        subject = row["room"].replace("-", " ")
        lines.extend([f"- [{checked}] **{clean(row['ref'])} · {subject} · {SURVEY[row['status']]}**. {clean(row['question'])}",
                      f"  **Owner** {clean(row['owner'])}. **Affects** {clean(row['affects'])}." + (" " + " · ".join(source) if source else "")])
    if not returns:
        lines.append("Assess survey need as each room enters review. Record a reason for any explicit exemption.")
    return "\n".join(lines).strip()


def refresh(root, *, published=None):
    """Replace only the generated section and insert acceptance lines for newly added rooms."""
    import house
    target = revisions.local_path(root, "CHECKLIST.md")
    work = revisions.local_path(root, revisions.WORK)
    work.mkdir(exist_ok=True)
    with revisions._save_lock(work):
        template = house.TEMPLATES / "house"
        survey = revisions.local_path(root, "survey-returns.csv")
        if not survey.exists():
            with survey.open("x", encoding="utf-8", newline="") as stream:
                stream.write((template / survey.name).read_text(encoding="utf-8"))
        name = revisions.stored_json(root / "project.json")["name"]
        existing = target.read_bytes() if target.exists() else None
        previous = existing.decode("utf-8-sig") if existing is not None else ""
        skeleton = (template / target.name).read_text(encoding="utf-8").replace("{{house}}", name)
        text = previous or skeleton
        if not any(marker in text for marker in (START, END, ACCEPT)):
            text = text.rstrip() + "\n\n" + skeleton[skeleton.index(START):]
        if any(text.count(marker) != 1 for marker in (START, END, ACCEPT)) or text.index(END) < text.index(START):
            raise ValueError("Repair the checklist section markers before refreshing. The existing checklist is preserved.")
        regs = sorted(folder / "review.csv" for folder in (root / "rooms").glob("*")
                      if (folder / "review.csv").is_file() or (folder / "README.md").is_file())
        rows = survey_rows(root, {reg.parent.name for reg in regs})
        report = generated(root, published or root, regs, rows)
        before, tail = text.split(START)
        _, after = tail.split(END)
        updated = before + START + "\n\n" + report + "\n\n" + END + after
        new = []
        for reg in regs:
            marker = f"<!-- acceptance {reg.parent.name} -->"
            if marker not in updated:
                new.append(f"- [ ] {room_title(reg)}. Record revision, decision, date and exclusions. {marker}")
        if new:
            updated = updated.replace(ACCEPT, "\n".join(new) + "\n" + ACCEPT)
        if updated == previous:
            return target
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as stream:
            tmp = Path(stream.name)
        try:
            with tmp.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(updated)
            if (target.read_bytes() if target.exists() else None) != existing:
                raise ValueError("The checklist was edited during refresh. Rerun to include those edits.")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
    return target



def try_refresh(root):
    """Keep completed operations usable if a working register needs attention."""
    try:
        return refresh(root)
    except (OSError, ValueError) as exc:
        print(f"Checklist refresh needed for {root.name}: {exc}", file=sys.stderr)
