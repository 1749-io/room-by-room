import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.check_public_tree import check


class PublicDistribution(unittest.TestCase):
    def test_staged_asset_substitution_and_private_files_are_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git = ["git", "-C", str(root)]
            subprocess.run([*git, "init", "-q"], check=True)
            (root / ".gitignore").write_text("/houses/\n")
            assets = root / "examples"
            assets.mkdir()
            sample = assets / "proof.png"
            sample.write_bytes(b"checked fixture")
            row = {"sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
                   "origin": "Fictional test", "rights": "Original fixture"}
            (assets / "asset-inventory.json").write_text(json.dumps({"examples/proof.png": row}))
            subprocess.run([*git, "add", "."], check=True)
            self.assertEqual(check(root), [])
            sample.write_bytes(b"replacement")
            (root / "houses").mkdir()
            (root / "houses/record.json").write_text("{}")
            (assets / "unknown.pdf").write_bytes(b"unreviewed")
            subprocess.run([*git, "add", "-f", "houses", "examples"], check=True)
            errors = "\n".join(check(root))
            for expected in ("changed asset", "Private or unsupported", "Unreviewed file type"):
                self.assertIn(expected, errors)
