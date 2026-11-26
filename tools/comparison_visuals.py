"""Bind brochure page placements to approved source bytes and recheck an issued brochure."""
from html.parser import HTMLParser
import base64
import hashlib
import io
import fitz
from PIL import Image, ImageOps

from room_by_room import house_revisions as revisions
from room_by_room.house_visuals import Catalogue, checksum, signature, words

REPORT = "Visual-uses.json"
FILES = ("existing.html", "proposed.html", "existing.pdf", "proposed.pdf", "Comparison.pdf", "Start here.html")


def reader_jpeg(raw):
    with Image.open(io.BytesIO(raw)) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        rgb.thumbnail((2000, 1700))
        out = io.BytesIO()
        rgb.save(out, format="JPEG", quality=88, subsampling=0)
        return out.getvalue()


class PrintedPlacements(HTMLParser):
    def __init__(self, phase):
        super().__init__()
        self.page = self.slot = 0
        self.anchor = ""
        self.images = []
        self.phase = phase

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section":
            self.page += 1
            self.slot = 0
            self.anchor = attrs["id"]
            self.group = attrs["data-group"]
            self.scope = attrs.get("data-scope")
        if tag == "img":
            self.slot += 1
            request = target(self.phase, self.group, {"id": self.anchor, "scope": self.scope},
                             {"visual_id": attrs.get("data-visual"), "view": attrs.get("data-view")})
            prefix = "data:image/jpeg;base64,"
            if not attrs.get("src", "").startswith(prefix):
                raise ValueError("A brochure image is missing its offline reviewed pixels")
            raw = base64.b64decode(attrs["src"][len(prefix):], validate=True)
            self.images.append((self.anchor, self.page, self.slot, request, hashlib.sha256(raw).hexdigest()))


def target(kind, group, page, image):
    if group == "layouts":
        scope, views = "floor/" + page["id"], ("plan",)
    elif group == "rooms":
        scope, views = "room/" + page["id"], ("photo", "camera", "locator", "plan")
    elif group == "studies":
        scope, views = words(page, "scope"), ("section", "plan", "photo", "camera", "illustration")
    else:
        scope, views = "house", ("photo", "camera", "plan", "illustration")
    view = image.get("view", views[0])
    if view not in views:
        raise ValueError(f"{kind} {group}/{page['id']}: invalid {view} placement")
    return dict(purpose="comparison." + group, phase=kind, scope=scope, view=view,
                visual_id=words(image, "visual_id"), accepted=kind == "proposed")


def preflight(house, data, assets):
    if house is None:
        raise ValueError("Supply --house with the design-state and visual-approval registers")
    registry = Catalogue(house)
    if data.get("house") != registry.house:
        raise ValueError("Brochure manifest must identify the same house as its approvals")
    placements, proofs = [], []
    offset = 0
    for kind in ("existing", "proposed"):
        doc = data[kind]
        if not doc["layouts"] or any(not p.get("images") for p in doc["layouts"]):
            raise ValueError(f"{kind}: supply each commissioned floor layout")
        number = 0
        for group, pages in [("cover", [doc["cover"]]), ("contents", [{}]), ("layouts", doc["layouts"]),
                             ("rooms", doc["rooms"]), ("studies", doc.get("studies", [])), ("particulars", doc["particulars"])]:
            for page in pages:
                number += 1
                for slot, image in enumerate(page.get("images", []), 1):
                    request = target(kind, group, page, image)
                    path = revisions.local_path(assets, image["path"])
                    proof = registry.approve(path=path, **request)
                    proofs.append(proof)
                    placements.append({"request": request, "source_revision": proof["approval"]["source"]["revision"],
                                       "source_sha256": proof["approval"]["source"]["sha256"],
                                       "state_id": proof["state_id"], "state_sha256": signature(proof["design"]),
                                       "review_sha256": signature(proof["approval"]), "slot": slot,
                                       "uses": [{"file": kind+".html", "anchor": page["id"]},
                                                {"file": kind+".pdf", "page": number},
                                                {"file": "Comparison.pdf", "page": offset+number}]})
        offset += number
    scopes = {scope for state in registry.states.values() for scope in state.get("scopes", [])}
    registry.coverage(proofs, scopes, phases={"existing", "proposed"})
    return {"version": 1, "house": registry.house, "placements": placements}


def verify_saved(house, folder, *, records=None):
    registry = Catalogue(house)
    frozen = Catalogue(house, records) if records is not None else None
    path = revisions.local_path(folder, REPORT)
    if not path.is_file():
        raise ValueError("Comparison brochure is missing its checked visual-use register")
    receipt = revisions.stored_json(path)
    if receipt.get("version") != 1 or receipt.get("house") != registry.house or not receipt.get("placements"):
        raise ValueError("Missing comparison visual placements or wrong house")
    missing = [name for name in FILES if not revisions.local_path(folder, name).is_file()]
    if missing:
        raise ValueError(f"Comparison brochure is missing reader files: {', '.join(missing)}")
    if receipt.get("files") != {name: checksum(revisions.local_path(folder, name)) for name in FILES}:
        raise ValueError("Comparison reader files changed since visual review")
    proofs = []
    occurrences = []
    pixels_by_page = {}
    encoded = {}
    offset = 0
    for kind in ("existing", "proposed"):
        reader = PrintedPlacements(kind)
        reader.feed((folder / (kind+".html")).read_text(encoding="utf-8"))
        pages = [[] for _ in range(reader.page)]
        for anchor, page, slot, request, digest in reader.images:
            proof = registry.approve(**request)
            if frozen is not None and proof != frozen.approve(**request):
                raise ValueError(f"{proof['id']}: brochure approval differs from the frozen commission")
            source = proof["approval"]["source"]
            if source["sha256"] not in encoded:
                raw = reader_jpeg(registry.evidence(source, published=True).read_bytes())
                encoded[source["sha256"]] = hashlib.sha256(raw).hexdigest(), fitz.Pixmap(raw).digest
            if digest != encoded[source["sha256"]][0]:
                raise ValueError(f"{kind}/{anchor}: embedded image differs from its reviewed visual")
            pages[page-1].append(encoded[source["sha256"]][1])
            occurrences.append((request, slot, [{"file": kind+".html", "anchor": anchor},
                                               {"file": kind+".pdf", "page": page},
                                               {"file": "Comparison.pdf", "page": offset+page}]))
        offset += reader.page
        pixels_by_page[kind+".pdf"] = pages
    if occurrences != [(x["request"], x["slot"], x["uses"]) for x in receipt["placements"]]:
        raise ValueError("Brochure visual register differs from the actual page placements")
    pixels_by_page["Comparison.pdf"] = pixels_by_page["existing.pdf"] + pixels_by_page["proposed.pdf"]
    for name, expected in pixels_by_page.items():
        with fitz.open(folder / name) as pdf:
            if len(pdf) != len(expected) or any([i["digest"] for i in page.get_image_info(hashes=True)] != wanted
                                                 for page, wanted in zip(pdf, expected)):
                raise ValueError(f"{name}: printed page images differ from the signed placements")
    for entry in receipt["placements"]:
        proof = registry.approve(**entry["request"])
        if (signature(proof["approval"]) != entry["review_sha256"] or signature(proof["design"]) != entry["state_sha256"]
                or proof["state_id"] != entry["state_id"] or proof["approval"]["source"]["sha256"] != entry["source_sha256"]
                or proof["approval"]["source"]["revision"] != entry["source_revision"]):
            raise ValueError(f"{proof['id']}: brochure visual approval changed. Rebuild the affected placements.")
        proofs.append(proof)
    registry.coverage(proofs, {s for r in registry.states.values() for s in r.get("scopes", [])},
                      phases={"existing", "proposed"})
