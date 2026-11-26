"""Issue three standalone publications and assemble their verified files into a house."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
module = importlib.util.spec_from_file_location("room_fixture", HERE.parent / "component-pack/replay.py")
room = importlib.util.module_from_spec(module)
module.loader.exec_module(room)

EDITIONS = {
    "OWNER": ("homeowner-presentation", "Homeowner", "homeowner", {"room-review": "ROOM", "shopping": "SHOP"},
              "Decide whether to keep the existing library storage or add two shelves.",
              "The installer checks the fixing substrate and socket before the homeowner releases the order."),
    "ARCH": ("architect-pack", "Architect", "architect", {"drawing": "DRAWING"},
             "Scope an appointment to coordinate the library shelf option against the existing room.",
             "The architect agrees a measured survey return with the installer."),
    "BUYER": ("buyer-brief", "Buyer", "buyer", {"drawing": "DRAWING", "shopping": "SHOP"},
              "Use the library viewing to distinguish immediate use from possible work.",
              "The buyer records the viewing answers and requests the outstanding checks."),
}


def issue(work, home, revision, request):
    name = f"request-{revision}.json"
    (home / name).write_text(json.dumps(request, indent=2), encoding="utf-8")
    room.run(work, "begin-revision", "Alder Cottage", revision, "--pack-request", name)
    room.run(work, "plan-pack", "Alder Cottage", revision)
    return Path(room.run(work, "build-pack", "Alder Cottage", revision)).parent.parent


def replay(work):
    work.mkdir(parents=True, exist_ok=False)
    home = room.prepare(work)
    for rev, component, recipients in [("ROOM", "room-review", []), ("DRAWING", "drawing", ["Architect", "Buyer"]),
                                        ("SHOP", "shopping", ["Buyer"])]:
        room.build_issue(work, home, rev, [component], share_with=recipients)
        room.save_example(work, rev, "Fictional reader exercise checked the selected room component.")
    for rev, (kind, audience, copy, sources, purpose, next_action) in EDITIONS.items():
        editorial = f"{copy}.json"
        (home / editorial).write_bytes((HERE / editorial).read_bytes())
        req = {"version": 1, "profile": "edition", "house": "alder-cottage", "components": [kind],
               "audience": audience, "purpose": purpose, "limitation": "Fictional library assessment using existing CAD. Wall fixings and service positions require a site check.",
               "next_action": next_action, "editorial": editorial, "rooms": {"library": sources}}
        if audience != "Homeowner":
            req["share_with"] = ["Homeowner"]
        issue(work, home, rev, req)
        room.save_example(work, rev, f"Automated example checked the {kind} against its commissioned pages and sources.")
    full = json.loads((room.HERE / "house-request.json").read_text(encoding="utf-8"))
    full["purpose"] = "Review the library decision, forward the appointment drawings and take the buyer questions to the viewing."
    full["editions"] = {row[0]: rev for rev, row in EDITIONS.items()}
    issue(work, home, "HOUSE-ALL", full)
    room.save_example(work, "HOUSE-ALL", "Matched room files and all three audience editions to their saved standalone copies.")
    return home


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="A new directory for the fictional house and its backups")
    args = parser.parse_args()
    print(replay(args.directory.resolve()) / "revisions/HOUSE-ALL/outputs/pack/delivery/Start here.html")
