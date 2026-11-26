import csv
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.check_delivery import verify, verify_issue


def make_pack(path, changes=None):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as nested:
        nested.writestr("Room.html", '<a href="Photo.jpg">View the photo</a>')
        nested.writestr("Photo.jpg", b"test contents")
    files = {
        "Start here.html": b'<a href="Room%20one.html#window">Room one</a>',
        "Room one.html": b'<h1 id="window">Window review</h1><a href="Source.zip">Download source ZIP</a>',
        "Source.zip": inner.getvalue(),
    }
    files.update(changes or {})
    index = io.StringIO()
    writer = csv.writer(index)
    writer.writerow(["label", "purpose", "path", "sha256"])
    for name, data in files.items():
        writer.writerow([name, "Test evidence", name, hashlib.sha256(data).hexdigest()])
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("Link-register.csv", index.getvalue())


class DeliveryTest(unittest.TestCase):
    def test_portable_nested_pack(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "House.zip"
            make_pack(path)
            self.assertEqual(verify(path)["archives"], 2)

    def test_saved_issue_requires_the_same_browser_and_zip_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "House.zip"
            make_pack(pack)
            with zipfile.ZipFile(pack) as archive:
                archive.extractall(root)
            verify_issue(root)
            (root / "Room one.html").write_text("Outdated copy")
            with self.assertRaisesRegex(ValueError, "Loose delivery differs"):
                verify_issue(root)

    def test_missing_targets_fragments_and_workstation_paths(self):
        for destination in ("Missing.html", "Room%20one.html#missing", "../private.pdf", "file:///C:/private.txt", ""):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as root:
                path = Path(root) / "House.zip"
                make_pack(path, {"Start here.html": f'<a href="{destination}">Room</a>'.encode()})
                with self.assertRaises(ValueError):
                    verify(path)

    def test_broken_nested_navigation(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as archive:
            archive.writestr("Room.html", '<img src="Missing.jpg">')
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "House.zip"
            make_pack(path, {"Source.zip": inner.getvalue()})
            with self.assertRaisesRegex(ValueError, "Missing.jpg"):
                verify(path)


if __name__ == "__main__":
    unittest.main()
