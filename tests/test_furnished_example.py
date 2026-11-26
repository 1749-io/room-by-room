import hashlib
import io
import json
from pathlib import Path
import runpy
import unittest
import zipfile

import fitz
from PIL import Image


EXAMPLE = Path(__file__).resolve().parents[1] / "examples/furnished-room"
REFERENCE = EXAMPLE / "reference"


class FurnishedExample(unittest.TestCase):
    def test_nine_original_component_issues_can_be_recovered(self):
        catalogue = json.loads((REFERENCE / "components.json").read_text(encoding="utf-8"))
        recover = runpy.run_path(str(EXAMPLE / "select_component.py"))["recover"]
        self.assertEqual(set(catalogue["components"]), {
            "room-review", "drawing", "shopping", "architect-pack", "buyer-brief",
            "homeowner-presentation", "decorator-finishes", "cost-schedule", "programme"})
        for name, entry in catalogue["components"].items():
            with self.subTest(component=name):
                data = recover(REFERENCE / catalogue["house_file"], catalogue, name)
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["archive_sha256"])

    def test_room_pdf_contains_the_exact_reviewed_camera_and_photo_pixels(self):
        catalogue = json.loads((REFERENCE / "components.json").read_text(encoding="utf-8"))
        review = json.loads((REFERENCE / "review.json").read_text(encoding="utf-8"))
        with zipfile.ZipFile(REFERENCE / catalogue["house_file"]) as house:
            sheet, = [name for name in house.namelist() if name.startswith("Rooms/") and name.endswith(".pdf")]
            with fitz.open(stream=house.read(sheet), filetype="pdf") as doc:
                for page, role in zip((doc[-2], doc[-1]), ("camera", "photo")):
                    images = page.get_image_info(xrefs=True)
                    self.assertEqual(len(images), 1, f"Expected one displayed {role} image")
                    delivered = doc.extract_image(images[0]["xref"])["image"]
                    source = (REFERENCE / review[role + "_file"]).read_bytes()
                    self.assertEqual(hashlib.sha256(source).hexdigest(), review[role + "_sha256"])
                    with Image.open(io.BytesIO(delivered)) as found, Image.open(io.BytesIO(source)) as reviewed:
                        self.assertEqual(found.size, reviewed.size)
                        found_pixels = hashlib.sha256(found.convert("RGB").tobytes()).hexdigest()
                        reviewed_pixels = hashlib.sha256(reviewed.convert("RGB").tobytes()).hexdigest()
                        self.assertEqual(found_pixels, reviewed_pixels, f"Different {role} pixels")
