"""Build the three schedules independently and add them to the existing Alder Cottage publications."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
module = importlib.util.spec_from_file_location("audience_example", HERE.parent / "audience-packs/replay.py")
audience = importlib.util.module_from_spec(module)
module.loader.exec_module(audience)


def add_schedules(work, home):
    for file, target in {"finishes.csv": "rooms/library/decorator-finishes.csv",
                         "sample-decision.md": "source/library-sample-decision.md",
                         "budget.csv": "budget.csv", "programme.csv": "programme.csv"}.items():
        (home / target).write_bytes((HERE / file).read_bytes())
    requests = json.loads((HERE / "requests.json").read_text(encoding="utf-8"))
    full = json.loads((home / "request-HOUSE-ALL.json").read_text(encoding="utf-8"))
    for rev, req in requests.items():
        kind, = req["components"]
        audience.issue(work, home, rev, dict(req, version=1, profile="schedule", house="alder-cottage"))
        audience.room.save_example(work, rev, f"Fixture checked the {kind} workbook, CSV and offline reader.")
        full["editions"][kind] = rev
    full.update(purpose="Issue the reviewed room, audience publications and library trade schedules together.",
                limitation="Fictional library commission. Optional shelf fitting, supply and final cost remain open.")
    audience.issue(work, home, "HOUSE-TRADE", full)
    audience.room.save_example(work, "HOUSE-TRADE", "Compared the complete handover with the saved component issues.")
    return home


def replay(work):
    return add_schedules(work, audience.replay(work))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New private directory for the fictional house and backups")
    args = parser.parse_args()
    print(replay(args.directory.resolve()) / "revisions/HOUSE-TRADE/outputs/pack/delivery/Start here.html")
