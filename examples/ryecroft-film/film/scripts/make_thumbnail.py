"""YouTube thumbnail, 1280 x 720: the conservatory from one camera as FreeCAD, Blender and the concept photo, under the
film's title. Every picture is a saved output of revision R7; nothing is generated here.

    python scripts/make_thumbnail.py <house revisions directory>/R7/outputs

The house record is private to the run and is not in this repository. The result is committed as publish/thumbnail.jpg.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
F = Path(sys.argv[1])
OUT = Path(__file__).resolve().parents[2] / "publish"
OUT.mkdir(exist_ok=True)
S = 2                                   # supersample
W, H = 1280 * S, 720 * S
BAND = 196 * S                          # title band
GROUND, INK, ACCENT = "#f3f1eb", "#1f3833", "#205d48"
SRC = [("views/CAD-CONS-01.png", "FreeCAD"), ("views/CAM-CONS-01.png", "Blender"),
       ("final-ai/conservatory/conservatory-concept.png", "AI concept photo")]
CUTS = [455 * S, 850 * S]               # slice boundaries at mid-height
LEAN = 25 * S                           # each boundary leans this far either side of its middle
TOP = 178 * S                           # row of the full view that sits at the top of the picture area


def view(path):
    im = Image.open(F / path).convert("RGB")
    w16 = min(im.width, round(im.height * 16 / 9)); x0 = (im.width - w16) // 2
    im = im.crop((x0, 0, x0 + w16, im.height)).resize((W, H), Image.LANCZOS)
    return im.crop((0, TOP, W, TOP + H - BAND))


def edge(b):
    """Boundary b as a line across the picture area, top to bottom."""
    return (b + LEAN, 0), (b - LEAN, H - BAND)


ph = H - BAND
pic = view(SRC[0][0])
for k in (1, 2):
    (xt, _), (xb, _) = edge(CUTS[k - 1])
    mask = Image.new("L", (W, ph), 0)
    ImageDraw.Draw(mask).polygon([(xt, 0), (W, 0), (W, ph), (xb, ph)], fill=255)
    pic.paste(view(SRC[k][0]), (0, 0), mask)
d = ImageDraw.Draw(pic)
for b in CUTS:
    d.line(edge(b), fill=GROUND, width=7 * S)

im = Image.new("RGB", (W, H), GROUND)
im.paste(pic, (0, BAND))
d = ImageDraw.Draw(im)
d.line([(0, BAND), (W, BAND)], fill=INK, width=3 * S)
size = 92 * S
while ImageFont.truetype("georgiab.ttf", size).getlength("Dream home. Needs work.") > W - 92 * S:
    size -= 2
title = ImageFont.truetype("georgiab.ttf", size)
sub = ImageFont.truetype("seguisb.ttf", 38 * S)
pill = ImageFont.truetype("seguisb.ttf", 34 * S)
d.text((44 * S, 18 * S), "Dream home. Needs work.", font=title, fill=INK)
d.ellipse((48 * S, 141 * S, 68 * S, 161 * S), fill=ACCENT)
d.text((82 * S, 126 * S), "room-by-room", font=sub, fill=ACCENT)
d.text((82 * S + d.textlength("room-by-room   ", font=sub), 126 * S), "an AI agent draws it finished, before the offer", font=sub, fill=INK)
# a label at the top of each slice
lefts = [28 * S, CUTS[0] + LEAN + 22 * S, CUTS[1] + LEAN + 22 * S]
for (_, name), x in zip(SRC, lefts):
    tw = d.textlength(name, font=pill); y = BAND + 22 * S
    d.rounded_rectangle((x, y, x + tw + 36 * S, y + 58 * S), radius=29 * S, fill=INK)
    d.text((x + 18 * S, y + 5 * S), name, font=pill, fill=GROUND)
im = im.resize((1280, 720), Image.LANCZOS)
im.save(OUT / "thumbnail.png")
im.save(OUT / "thumbnail.jpg", "JPEG", quality=92)
im.resize((320, 180), Image.LANCZOS).save(OUT / "thumbnail-320-check.png")
print("written", (OUT / "thumbnail.jpg").stat().st_size, "bytes")
