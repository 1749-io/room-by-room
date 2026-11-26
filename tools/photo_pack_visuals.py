"""Check each declared photograph and the actual media forwarded inside a sealed room ZIP."""
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import PurePosixPath
import posixpath
from urllib.parse import unquote, urlsplit
import zipfile

import fitz
import house_revisions as revisions
from house_visuals import Catalogue, signature


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            if "srcset" in attrs:
                raise ValueError("Issue the reviewed image in each selectable photo resolution")
            self.images.append(attrs.get("src", ""))


def photo_uses(root, ready, staged):
    registry = Catalogue(root)
    uses = []
    def record(proof, location, page=1):
        uses.append({"id": proof["id"], "state": proof["state_id"], "purpose": proof["purpose"],
                     "scope": proof["scope"], "source_revision": proof["approval"]["source"]["revision"],
                     "sha256": proof["approval"]["source"]["sha256"], "review_sha256": signature(proof["approval"]),
                     "file": location, "page": page})
    for slug, (_, _, doc, outputs) in ready.items():
        scope = "room/"+slug
        archive_name = slug+"/Room-pack.zip"
        known = {}
        for pair in doc["photos"]:
            for view in ("camera", "photo"):
                name = pair[view]
                corrected = f"{slug}/corrected/{name}"
                path = staged.get(corrected, outputs/name)
                proof = registry.approve(path=path, purpose="photo-pack.room", phase="proposed", scope=scope, view=view)
                known[proof["approval"]["source"]["sha256"]] = proof
                if corrected in staged:
                    record(proof, corrected)
        def member(raw, location, page, use):
            digest = hashlib.sha256(raw).hexdigest()
            proof = known.get(digest) if page == 1 else None
            if proof is None:
                candidates = [(k, v) for k, v in registry.visuals.items() if k not in registry.old_visuals
                              and v["source"]["sha256"] == digest and v.get("page", 1) == page
                              and {"purpose": "photo-pack.attachment", "scope": scope} in v["placements"]]
                if len(candidates) != 1:
                    raise ValueError(f"{location}: missing purpose-specific attachment review for page {page}")
                key, entry = candidates[0]
                proof = registry.approve(visual_id=key, purpose="photo-pack.attachment", phase="proposed",
                                         scope=scope, view=entry["view"], page=page)
            record(proof, use, page)
        with zipfile.ZipFile(staged[archive_name]) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError(f"{archive_name}: repeated member names")
            seen = set()
            for name in names:
                ext = PurePosixPath(name).suffix.casefold()
                location = archive_name + "/" + name
                if ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif", ".pdf"):
                    data = archive.read(name)
                    count = 1
                    if ext == ".pdf":
                        with fitz.open(stream=data, filetype="pdf") as pdf:
                            count = len(pdf)
                    for page in range(1, count+1):
                        member(data, location, page, location)
                    seen.add(hashlib.sha256(data).hexdigest())
                if ext in (".htm", ".html"):
                    parser = Images()
                    parser.feed(archive.read(name).decode("utf-8-sig"))
                    for slot, url in enumerate(parser.images, 1):
                        if url.startswith("data:image/") and ";base64," in url:
                            data = base64.b64decode(url.split(",", 1)[1], validate=True)
                        else:
                            ref = urlsplit(url)
                            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(ref.path)))
                            if ref.scheme or ref.netloc or target not in names:
                                raise ValueError(f"{location}: missing reviewed local image {url}")
                            data = archive.read(target)
                        member(data, location, 1, f"{location}#image-{slot}")
                        seen.add(hashlib.sha256(data).hexdigest())
            for pair in doc["photos"]:
                for view in ("camera", "photo"):
                    if pair[view+"_sha256"] not in seen and f"{slug}/corrected/{pair[view]}" not in staged:
                        raise ValueError(f"{archive_name}: reviewed {view} is missing")
    import house_photos
    for name, path in staged.items():
        if name.startswith("exterior/") and name.endswith("/"+house_photos.EXTERIOR_REVIEW):
            prefix = name.rsplit("/", 1)[0] + "/"
            for photo, item in revisions.stored_json(path)["photos"].items():
                for view, member_name in (("photo", photo), ("camera", item["camera"])):
                    target = prefix + member_name
                    record(registry.approve(path=staged[target], purpose="photo-pack.exterior", phase="proposed",
                                            scope="house", view=view), target)
    return uses
