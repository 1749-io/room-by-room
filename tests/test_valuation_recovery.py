import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import house_backup as backups
from tools.valuation import evaluate


class ValuationAndRecovery(unittest.TestCase):
    def test_index_adjustment_requires_unchanged_subject_and_in_window_sale(self):
        with tempfile.TemporaryDirectory() as folder:
            brief = Path(folder) / "brief.md"
            brief.write_bytes(b"Measured detached house before pricing")
            evidence = dict(brief_sha256=hashlib.sha256(brief.read_bytes()).hexdigest(),
                            as_of="2026-11-26", index_month="2026-09", region="trafford",
                            index_field="housePriceIndexDetached",
                            sales=[dict(address="1 Test Road", date="2024-05-01", price=100000,
                                        source="test record", condition="Updated kitchen", role="size reference")])
            def fetch(url):
                return {"result": {"primaryTopic": {"housePriceIndexDetached": 110 if "2026-09" in url else 100}}}
            self.assertEqual(evaluate(brief, evidence, fetch)[0]["adjusted_gbp"], 110000)
            evidence["sales"][0]["date"] = "2023-11-25"
            with self.assertRaisesRegex(ValueError, "date"):
                evaluate(brief, evidence, fetch)
            brief.write_bytes(b"changed area")
            with self.assertRaisesRegex(ValueError, "brief changed"):
                evaluate(brief, evidence, fetch)

    def test_delta_restores_without_intermediate_snapshot_and_checks_base(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            house = repo / "houses/sample"
            history = house / "revisions"
            history.mkdir(parents=True)
            (house / "project.json").write_text('{"id":"sample"}')
            (house / "existing").write_bytes(b"same native model")
            base = root / "backups/base.zip"
            backups.backup(house, base, repo)
            stage = root / "R1"
            (stage / "inputs").mkdir(parents=True)
            (stage / "outputs").mkdir()
            (stage / "outputs/photo").write_bytes(b"photo")
            (stage / "record.json").write_text(json.dumps(dict(house="sample", revision="R1", saved="2026-11-26",
                inputs={}, outputs={"photo":hashlib.sha256(b"photo").hexdigest()})))
            delta = base.with_name("revision.zip")
            backups.backup(house, delta, repo, staged_revision=stage)
            with ZipFile(delta) as z:
                self.assertEqual(json.loads(z.read("backup.json"))["base"], base.name)
                self.assertNotIn("objects/" + hashlib.sha256(b"same native model").hexdigest(), z.namelist())
            restored = root / "separate"
            backups.restore("sample", delta, restored)
            self.assertEqual((restored / "existing").read_bytes(), b"same native model")
            self.assertEqual((restored / "revisions/R1/outputs/photo").read_bytes(), b"photo")
            base.rename(base.with_suffix(".moved"))
            with self.assertRaises(FileNotFoundError):
                backups.restore("sample", delta, root / "incomplete")
            self.assertFalse((root / "incomplete").exists())
