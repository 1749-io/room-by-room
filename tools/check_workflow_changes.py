"""Require workflow changes in a Git change set to update their published diagram."""
import argparse
from pathlib import PurePosixPath
import subprocess


PACK_CODE = {
    "room_by_room/house_delivery.py", "tools/check_delivery.py", "tools/house_pack.py",
    "tools/render_pack.py", "tools/audience_packs.py", "tools/schedule_pack.py",
}


def coverage_problems(paths):
    room = set()
    pack = set()
    for name in paths:
        path = PurePosixPath(name)
        if name.startswith("skills/room-by-room-film/"):
            continue  # Films about the toolkit are publicity. They are not a step in a room review.
        if name in PACK_CODE or name.startswith("skills/pack-delivery/"):
            pack.add(name)
        elif (name == "AGENTS.md"
              or (name.startswith("room_by_room/house_") and path.suffix == ".py")
              or (name.startswith("skills/") and path.suffix in {".md", ".py"})
              or (name.startswith("templates/") and path.name in {"review.csv", "layout-checks.csv"})):
            room.add(name)

    problems = []
    sources = {"docs/workflow.dot", "docs/workflow-decisions.md", "docs/render_workflow.py",
               "skills/renovation-pack/references/specialist-design-tools.md"}
    room_updated = bool(paths.intersection(sources)) and "docs/workflow.svg" in paths
    pack_updated = {"docs/pack-delivery.dot", "docs/pack-delivery.svg"}.issubset(paths)
    if "house.py" in paths and not (room_updated or pack_updated):
        problems.append("Update the affected room or pack diagram for the shared house.py CLI")
    if room and not room_updated:
        problems.append("Update the room map or review text and regenerate docs/workflow.svg for: " + ", ".join(sorted(room)))
    if pack and not pack_updated:
        problems.append("Update docs/pack-delivery.dot and regenerate its SVG for: " + ", ".join(sorted(pack)))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="PR base or pre-push commit")
    args = parser.parse_args()
    # Disable rename detection so both the former and new workflow locations count.
    diff = subprocess.check_output(["git", "diff", "--no-renames", "--name-only", "-z", args.base, "HEAD", "--"])
    problems = coverage_problems(set(diff.decode("utf-8").split("\0")))
    if problems:
        raise SystemExit("\n".join(problems))


if __name__ == "__main__":
    main()
