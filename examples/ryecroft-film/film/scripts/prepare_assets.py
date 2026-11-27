"""Copy and crop the Ryecroft run's artifacts into film/assets. Every image comes from a saved revision. The only thing
added for the film is a caption on each live-build frame, taken from the build log.

    python scripts/prepare_assets.py <house revisions directory> <extracted dining room pack directory>

The house record stays private to the run that made it and is not in this repository. The images this script made from
it are committed under film/assets, so the film rebuilds without running this. The captions use Segoe UI from Windows.

The final design is revision R7 (sliding doors, the listed rattan armchairs, the garden for context). The existing house,
the beam study, the route comparison and the comfort study keep their own revisions."""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 3:
    raise SystemExit(__doc__)
H = Path(sys.argv[1])          # .../houses/ryecroft/revisions
PACK = Path(sys.argv[2])       # the extracted dining room pack, with the screenshots from scripts/pack_shots.mjs
F = H / "R7/outputs"
A = Path(__file__).resolve().parents[1] / "assets"
A.mkdir(exist_ok=True)
sizes = {}


def save(src, name, crop=None, width=None):
    im = Image.open(src).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(A / name, "JPEG", quality=90)
    sizes[name] = im.size
    print(name, im.size)


def save169(src, name, width=1400):
    """Centre crop to 16:9, for pictures that dissolve into one another."""
    im = Image.open(src)
    w16 = min(im.width, round(im.height * 16 / 9)); x0 = (im.width - w16) / 2 / im.width
    save(src, name, crop=(x0, 0, 1 - x0, 1), width=width)


save(H / "EXISTING-R1/outputs/views/existing-isometric.png", "existing-iso.jpg", crop=(0.10, 0.10, 0.80, 0.90), width=1300)
save(H / "EXISTING-R1/outputs/drawings/existing-plan.png", "existing-plan.jpg", crop=(0.04, 0.165, 0.68, 0.83), width=900)
save(F / "drawings/proposed-plan.png", "proposed-plan.jpg", crop=(0.04, 0.367, 0.68, 0.83), width=900)          # kitchen, dining room and hall: the wall that comes out
save(F / "drawings/proposed-plan.png", "plan-cons.jpg", crop=(0.07, 0.215, 0.385, 0.405))                          # the conservatory end: sliding doors and armchairs
save(H / "OPENING-R1/outputs/structure/fem-isometric.png", "fem.jpg", crop=(0.15, 0.12, 0.85, 0.88), width=1200)
save(H / "OPENING-R1/outputs/structure/solver-comparison.png", "solver.jpg", width=1500)
save(H / "ROUTE-R1/outputs/drawings/kitchen-door-choice.png", "door-choice.jpg", crop=(0.0, 0.06, 1.0, 0.905), width=1500)
save(H / "CONSERVATORY-R1/outputs/comfort/conservatory-choice.png", "cons-choice.jpg", width=1500)
save(H / "CONSERVATORY-R1/outputs/site/trees-and-sun.png", "trees.jpg", crop=(0.04, 0.155, 0.645, 0.865), width=1300)
save(H / "CONSERVATORY-R1/outputs/comfort/comfort-options.png", "comfort.jpg", crop=(0.0, 0.12, 1.0, 0.95), width=1500)
save(F / "climate/after-all-year.png", "after.jpg", crop=(0.02, 0.185, 0.99, 0.93), width=1500)
save(F / "views/CAM-TOP.png", "blender-top.jpg", crop=(0.17, 0.08, 0.83, 0.86), width=760)
for cam in ("CAM-DINING-01", "CAM-KITCHEN-01"):
    save169(F / f"views/{cam}.png", f"{cam}.jpg")
save169(F / "final-ai/dining-room/dining-room-concept.png", "photo-dining.jpg")
save169(F / "final-ai/kitchen/kitchen-concept.png", "photo-kitchen.jpg")
save169(F / "views/CAD-CONS-01.png", "cons-cad.jpg")
save169(F / "views/CAM-CONS-01.png", "cons-blender.jpg")
save169(F / "final-ai/conservatory/conservatory-concept.png", "cons-photo.jpg")
save(H / "R5/outputs/final-ai/listing/armchair-product.png", "armchair.jpg", width=820)
save(F / "programme/programme.png", "programme.jpg", width=1500)
if (PACK / "start-here.png").exists():
    save(PACK / "start-here.png", "pack-start.jpg", crop=(0.14, 0.03, 0.86, 0.77), width=1200)
    save(PACK / "review.png", "pack-review.jpg", crop=(0.14, 0.03, 0.86, 0.60), width=900)
# the live FreeCAD rebuild, one frame per step, with the step's name from the build log as a caption
steps = json.loads((F / "views/cad-build/build-log.json").read_text(encoding="utf-8"))["steps"]
build = A / "build"
if build.exists():
    shutil.rmtree(build)
build.mkdir()
font = ImageFont.truetype("segoeuib.ttf", 34); small = ImageFont.truetype("segoeui.ttf", 30)
for st in steps:
    im = Image.open(F / f"views/cad-build/step_{st['step']:02d}.png").convert("RGB").crop((0, 0, 1280, 720))
    d = ImageDraw.Draw(im)
    d.text((40, 610), "FreeCAD, live" if st["step"] == 0 else f"FreeCAD, live · step {st['step']} of {len(steps) - 1}", font=font, fill="#1f3833")
    d.text((40, 656), st["what"], font=small, fill="#1f3833")
    im.save(build / f"b_{st['step']:04d}.jpg", "JPEG", quality=90)
print("build frames", len(steps))
# eye-level walk frames
walk = A / "walk"
if walk.exists():
    shutil.rmtree(walk)
walk.mkdir()
frames = sorted((F / "views/walk").glob("frame_*.png"))
for f in frames:
    n = int(f.stem.split("_")[1])
    Image.open(f).convert("RGB").save(walk / f"f_{n:04d}.jpg", "JPEG", quality=88)
print("walk frames", len(frames))
(A / "sizes.txt").write_text("\n".join(f"{k} {v[0]} {v[1]}" for k, v in sizes.items()), encoding="utf-8")
