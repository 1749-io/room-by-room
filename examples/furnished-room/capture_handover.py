"""Capture an issued fictional Alder pack and the inputs for its component selector."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import house_revisions as revisions
from house_delivery import digest, inspect_pack
from tools.check_delivery import verify


def issued(home, revision):
    revisions.verify_revision(home, revision)
    pack = revisions.record_dir(home, revision) / "outputs/pack"
    manifest = revisions.stored_json(pack / "issue-manifest.json")
    archive = revisions.local_path(pack, manifest["archive"])
    if digest(archive) != manifest["archive_sha256"]:
        raise ValueError(f"{revision}: the recipient ZIP differs from its manifest")
    verify(archive, expected_files=manifest["files"])
    return manifest, archive


def capture(home, revision, dest):
    if dest.exists() or revisions.stored_json(home / "project.json")["id"] != "alder-cottage":
        raise ValueError("Choose the fictional Alder house and a new output directory")
    manifest, archive = issued(home, revision)
    spec = manifest["request"]
    if spec.get("profile") != "house" or set(spec["rooms"]) != {"library"}:
        raise ValueError("The reference issue must cover the Alder library commission")
    folder = revisions.record_dir(home, revision)
    inspect_pack(home, revisions.stored_json(folder / "record.json"), folder)
    sources = {row["component"]: row["revision"] for row in spec["sources"].values()}
    if any(sources[row["component"]] != row["revision"] for row in spec["sources"].values()):
        raise ValueError("This example catalogue expects one standalone issue per component")
    if set(sources) != {"room-review", "drawing", "shopping", "architect-pack", "buyer-brief",
                        "homeowner-presentation", "decorator-finishes", "cost-schedule", "programme"}:
        raise ValueError("Issue all nine Alder components before capturing the reference")
    components = {}
    with zipfile.ZipFile(archive) as house:
        for kind, issue in sorted(sources.items()):
            receipt, source = issued(home, issue)
            with zipfile.ZipFile(source) as standalone:
                for name in standalone.namelist():
                    if name not in {"Start here.html", "Link-register.csv"} and standalone.read(name) != house.read(name):
                        raise ValueError(f"{issue}: house file differs from the standalone {name}")
                components[kind] = {
                    "source_issue": issue, "archive_sha256": receipt["archive_sha256"],
                    "start_here": standalone.read("Start here.html").decode("utf-8"),
                    "link_register": standalone.read("Link-register.csv").decode("utf-8"),
                }
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
        staged = Path(temp) / "reference"
        staged.mkdir()
        name = "Alder-Cottage-furnished-handover.zip"
        shutil.copyfile(archive, staged / name)
        catalogue = {"house_file": name, "house_sha256": manifest["archive_sha256"], "components": components}
        (staged / "components.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8", newline="\n")
        staged.rename(dest)
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("house", type=Path)
    parser.add_argument("issue")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(capture(args.house.resolve(), args.issue, args.output.resolve()))
