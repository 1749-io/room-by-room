"""Build the public Alder Cottage demo in a new directory. Requires Poppler."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import runpy
from tempfile import TemporaryDirectory
import zipfile

from select_component import REFERENCE, recover


SITE = Path(__file__).with_name("site")
PACKS = {
    "room-review": ("Room review", "Room decisions and review evidence"),
    "drawing": ("Library drawing", "Occupied layout and drawing key"),
    "shopping": ("Shopping schedule", "Selected products and quantities"),
    "homeowner-presentation": ("Homeowner presentation", "Presentation slides and printable edition"),
    "architect-pack": ("Architect pack", "Design brief, drawing and register"),
    "buyer-brief": ("Buyer brief", "Purchase requirements and outstanding checks"),
    "decorator-finishes": ("Decorator finishes", "Finish instructions by surface"),
    "cost-schedule": ("Editable cost schedule", "Cost allowances and calculations"),
    "programme": ("Programme", "Work sequence and dependencies"),
}


def build(output):
    catalogue = json.loads((REFERENCE / "components.json").read_text(encoding="utf-8"))
    if set(PACKS) != set(catalogue["components"]):
        raise ValueError("Update the demo to match the reviewed pack catalogue")
    archive = REFERENCE / "Alder-Cottage-furnished-handover.zip"
    review = json.loads((REFERENCE / "review.json").read_text(encoding="utf-8"))
    concept = REFERENCE / "library-concept.png"
    if sha256(concept.read_bytes()).hexdigest() != review["photo_sha256"]:
        raise ValueError("The concept differs from the reviewed public example")
    if output.exists():
        raise FileExistsError(output)
    with TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / "site"
        downloads = stage / "downloads"
        downloads.mkdir(parents=True)
        links = []
        for key, (title, description) in PACKS.items():
            name = f"Alder-Cottage-{key}.zip"
            (downloads / name).write_bytes(recover(archive, catalogue, key))
            links.append(f'<a class="pack" href="downloads/{name}" download>'
                         f'<strong>{title}</strong><span>{description}</span>'
                         '<small>Download ZIP ↓</small></a>')
        shutil.copyfile(archive, downloads / archive.name)
        shutil.copyfile(concept, stage / concept.name)
        with zipfile.ZipFile(archive) as house:
            (stage / "plan.pdf").write_bytes(house.read(
                "Drawings/alder-cottage-library-DRAWING-drawing.pdf"))
        subprocess.run(["pdftoppm", "-singlefile", "-scale-to", "1600", "-png",
                        str(stage / "plan.pdf"), str(stage / "plan")], check=True)
        template = (SITE / "index.html").read_text(encoding="utf-8-sig")
        (stage / "index.html").write_text(template.replace("<!-- packs -->", "\n".join(links)),
                                         encoding="utf-8")
        (stage / ".nojekyll").touch()
        orchard = SITE.parents[1] / "conservatory" / "build_page.py"
        runpy.run_path(str(orchard))["build"](stage)
        stage.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output.resolve())

