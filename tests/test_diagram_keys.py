"""Exercise visible keys on exported homeowner drawing sheets."""
import sys
import unittest
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/renovation-pack/scripts"))
from diagram_key import draw_key, check_key

class DiagramKeys(unittest.TestCase):
    def setUp(self):
        self.figure = plt.figure(figsize=(8, 5))
        self.panels = [self.figure.add_axes([x, .4, .35, .52]) for x in (.05, .54)]
        self.addCleanup(plt.close, self.figure)

    def test_shared_key_matches_actual_artists(self):
        for ax in self.panels:
            ax.plot([0, 1], [0, 1], "--", label="Serving route")
            ax.add_patch(Rectangle((.4, .4), .1, .1, hatch="xx", label="Trial support"))
        key = draw_key(self.figure, self.panels, at=(.08, .25), columns=2)
        self.assertEqual([item.get_text() for item in key.get_texts()], ["Serving route", "Trial support"])
        check_key(self.figure, self.panels, key)
        self.panels[0].plot([0, 1], [1, 0], label="Laundry route")
        with self.assertRaisesRegex(ValueError, "each plotted symbol"):
            check_key(self.figure, self.panels, key)

    def test_empty_overlapping_and_clipped_keys_fail(self):
        with self.assertRaisesRegex(ValueError, "Label the symbols"):
            draw_key(self.figure, self.panels, at=(.05, .2), columns=1)
        self.panels[0].plot([0, 1], [0, 1], label="Serving route")
        for at, error in [((.08, .8), "outside the drawing"), ((.99, .2), "beyond the sheet")]:
            key = draw_key(self.figure, self.panels, at=at, columns=1)
            with self.assertRaisesRegex(ValueError, error):
                check_key(self.figure, self.panels, key)
            key.remove()
