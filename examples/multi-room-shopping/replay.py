"""Issue a procurement-only handover for every registered room of a fictional flat."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
CLI = HERE.parents[1] / "house.py"
ROOMS = {"kitchen": "Kitchen", "shower-room": "Shower room", "studio": "Studio"}


def replay(work):
    work.mkdir(parents=True, exist_ok=False)
    name = "Maple Mews"
    home = work / "houses/maple-mews"
    env = dict(os.environ, HOUSE_BACKUP_DIR=str(work / "backups"), PYTHONIOENCODING="utf-8")

    def run(action, *args):
        return subprocess.check_output([sys.executable, str(CLI), "--houses-dir", str(home.parent),
                                        action, name, *args], env=env, text=True, encoding="utf-8").strip()

    def issue(revision, request):
        file = home / f"{revision}.json"
        file.write_text(json.dumps(request, indent=2), encoding="utf-8")
        run("begin-revision", revision, "--pack-request", file.name)
        run("plan-pack", revision)
        index = Path(run("build-pack", revision))
        run("check-pack", revision)
        return next(index.parent.parent.glob("*.zip"))

    def save(revision, finding):
        run("check-pack", revision, "--reviewer", "Fictional fixture reader", "--finding", finding)
        run("save-revision", revision, "--change", "Issued the commissioned shopping files",
            "--why", "Portable purchasing review", "--by", "Fictional fixture reader",
            "--affects", "Selected shopping schedules", "--next", "Resolve fit and shared quantities")

    run("start", *(arg for label in ROOMS.values() for arg in ("--room", label)))
    (home / "shopping.csv").write_bytes((HERE / "items.csv").read_bytes())
    common = {"version": 1, "house": "maple-mews", "components": ["shopping"], "audience": "Homeowner",
              "purpose": "Review the selected and retained items before ordering.",
              "limitation": "Fictional prices. Shared quantities and site fit remain open.",
              "next_action": "Check fit and allocate the shared floor pads."}
    with (HERE / "items.csv").open(encoding="utf-8", newline="") as source:
        inventory = list(csv.DictReader(source))
    selections, received = {}, {}
    for slug, label in ROOMS.items():
        revision = slug.upper()
        selections[slug] = {"shopping": revision}
        with ZipFile(issue(revision, dict(common, room=label))) as archive:
            members = {n: archive.read(n) for n in archive.namelist() if n.startswith("Schedules/")}
            csv_name, = [n for n in members if n.endswith(".csv")]
            rows = list(csv.DictReader(io.StringIO(members[csv_name].decode("utf-8-sig"))))
            expected = {r["item_id"] for r in inventory if label in r["room"].split(" / ")}
            if {r["Item ID"] for r in rows} != expected:
                raise ValueError(f"{label}: schedule differs from the room allocation")
            for row in rows:
                if row["Item ID"] == "SH01" and (row["Quantity"] or row["Source quantity"] != "2"):
                    raise ValueError("Shared purchase acquired a room quantity")
            received.update(members)
        save(revision, f"Opened both shopping formats and checked {label} against the fictional inventory.")
    revision = "ALL-ROOMS"
    with ZipFile(issue(revision, dict(common, profile="house", rooms=selections))) as combined:
        combined_files = {n: combined.read(n) for n in combined.namelist() if n.startswith("Schedules/")}
        if combined_files != received:
            raise ValueError("The house handover differs from the three standalone schedules")
    save(revision, "Matched every room workbook and CSV to its issued standalone file.")
    return home / "revisions" / revision / "outputs/pack/delivery/Start here.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New private example directory")
    print(replay(parser.parse_args().directory.resolve()))
