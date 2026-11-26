"""Save two pier decisions, then recover the private house in a fresh checkout."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from replay import FOLDER, pier_results

REPO = FOLDER.parents[1]
HOUSE = "Orchard House"


def command(library, action, *args, expected_error=None):
    backup_root = library.parents[1] / "private-backups"
    result = subprocess.run([sys.executable, str(REPO / "house.py"), "--houses-dir", str(library),
                             action, HOUSE, *map(str, args)], capture_output=True, text=True,
                            env={**os.environ, "HOUSE_BACKUP_DIR": str(backup_root)})
    if expected_error:
        if result.returncode == 0 or expected_error not in result.stderr:
            raise RuntimeError(f"Expected {expected_error!r}: {result.stderr}")
    elif result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def replay(folder):
    folder.mkdir(parents=True, exist_ok=False)
    working = folder / "working"
    working.mkdir()
    library = working / "houses"
    root = library / "orchard-house"
    clone = folder / "fresh-checkout"
    recovered = clone / "houses"
    reference = FOLDER / "reference"
    command(library, "start", "--room", "Kitchen", "--room", "Dining room")
    model = "models/Example rear rooms.FCStd"
    geometry = "source/rear-rooms.json"
    shutil.copyfile(reference / "Example rear rooms.FCStd", root / model)
    shutil.copyfile(reference / "rear-rooms.json", root / geometry)
    shutil.copyfile(reference / "occupied-plan.png", root / "views/occupied-plan.png")
    (root / "handover/builder-enquiry.txt").write_text("Fictional enquiry. Confirm the finished pier position.\n")
    for design, parent, expected, change, why, next_step in (
        ("R1", None, 646, "Record the returned pier and the original kitchen run.",
         "The finished pier narrows the route while eight people are seated.",
         "Revise the cabinet, dining position and dry prep bench before tender."),
        ("R3", "PIER-R1", 845, "Shorten the cabinet, shift the table and move the dry prep bench.",
         "The earlier 646 mm serving route falls short of the example household's 825 mm target.",
         "Confirm utility storage with the owner and issue the same plan to both bidders."),
    ):
        revision = "PIER-" + design
        flags = ["--from", parent] if parent else []
        out = Path(command(library, "begin-revision", revision, *flags, "--input", model, "--input", geometry))
        frozen = out.parent / "inputs" / geometry
        result = pier_results({design: json.loads(frozen.read_text())[design]})[design, "Eight"]
        assert result["tested_mm"] == expected
        # Identical filenames across revisions are normal. Only the current draft is edited.
        report = out / "serving-route.json"
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
        command(library, "save-revision", revision, "--change", change, "--why", why, "--by", "Example reviewer",
                "--affects", "Kitchen storage, dining for eight, utility shelving and both builder tenders.",
                "--next", next_step)
        command(library, "begin-revision", revision, expected_error="already exists")
        command(library, "verify-revision", revision)
    record = json.loads((root / "revisions/PIER-R3/record.json").read_text(encoding="utf-8"))
    archive = folder / "private-backups" / record["backup"]
    # Use the real privacy rules and an actual local clone. The clone carries no household records.
    shutil.copyfile(REPO / ".gitignore", working / ".gitignore")
    git = ["git", "-C", str(working), "-c", "core.autocrlf=false", "-c", "core.hooksPath=" + str(folder / "no-hooks")]
    subprocess.run([*git, "init", "--quiet"], check=True)
    subprocess.run([*git, "add", "--all"], check=True)
    assert subprocess.check_output([*git, "ls-files"], text=True).splitlines() == [".gitignore"]
    subprocess.run([*git, "-c", "user.name=Example reviewer", "-c", "user.email=example@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Save public toolkit ignore rules"], check=True)
    subprocess.run([*git, "clone", "--quiet", "--no-local", "-c", "core.autocrlf=false",
                    str(working), str(clone)], check=True)
    restored = recovered / root.name
    assert not restored.exists()
    before = command(library, "history", "PIER-R3")
    assert "based on PIER-R1" in before and "646 mm" in before
    print(command(recovered, "restore", archive))
    assert "Restored 0 missing files" in command(recovered, "restore", archive)
    from room_by_room.house_revisions import inventory
    files, _ = inventory(root, house=True)
    for name in files:
        assert (root / name).read_bytes() == (restored / name).read_bytes(), name
    for revision, width in (("PIER-R1", 646), ("PIER-R3", 845)):
        print(command(recovered, "verify-revision", revision))
        recovered_route = restored / "revisions" / revision / "outputs/serving-route.json"
        assert json.loads(recovered_route.read_text())["tested_mm"] == width
    assert before == command(recovered, "history", "PIER-R3")
    print(before)
    print("Restored both serving routes, editable FreeCAD input, source, view and builder enquiry.")
    return restored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory outside the repository")
    replay(parser.parse_args().output.resolve())
