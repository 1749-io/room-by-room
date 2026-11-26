"""Issue audience-specific publications from signed room components and reviewed copy."""
from decimal import Decimal
from html import escape
from pathlib import Path
from urllib.parse import quote, unquote

import fitz

import house_revisions as revisions
from house_delivery import EDITIONS, digest, required
from tools import audience_pages as pages
from tools import render_pack
from tools.check_delivery import Page
from tools.house_pack import room_sources

TITLES = {"homeowner-presentation": "Homeowner presentation",
          "architect-pack": "Architect pack", "buyer-brief": "Buyer brief"}
# Each entry is a commissioned decision, with approved words and the basis the reader may see.
CHAPTERS = {
    "homeowner-presentation": ("decision", "options", "phasing"),
    "architect-pack": ("appointment", "exclusions", "survey", "coordination"),
    "buyer-brief": ("scenario", "cost_basis", "occupation", "viewing", "follow_up"),
}


def edition_index(kind):
    return f"Briefs/{kind}/Read me.html"


def note(label, text, basis):
    return {"label": label, "text": text, "basis": basis}


def read_editorial(req, folder):
    kind, = req["components"]
    data = revisions.stored_json(revisions.local_path(folder, req["editorial"]))
    if (data.get("edition") != kind or data.get("house") != req["house"]
            or data.get("audience") != req["audience"]):
        raise ValueError("Audience copy must match the house, edition and recipient")
    chapters = data.get("chapters")
    if not isinstance(chapters, dict) or set(chapters) != set(CHAPTERS[kind]):
        raise ValueError(f"{kind}: expected chapters " + ", ".join(CHAPTERS[kind]))
    for key in CHAPTERS[kind]:
        entries = chapters[key]
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Supply a reviewed entry for {key}")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - {"label", "text", "basis", "evidence"}:
                raise ValueError(f"{key}: expected label, text and basis")
            for field in ("label", "text", "basis"):
                required(entry, field)
            refs = entry.get("evidence", [])
            if not isinstance(refs, list):
                raise ValueError(f"{key}: evidence must list house-relative source files")
            for ref in refs:
                if revisions.safe_relative(ref).parts[0] == revisions.WORK:
                    raise ValueError("Use saved evidence for the audience copy")
            entry["source"] = "editorial"
    return chapters


def cited_files(req, chapters):
    paths = [ref for entries in chapters.values() for entry in entries for ref in entry.get("evidence", [])]
    return list(dict.fromkeys([req["editorial"], *paths]))


def editorial_inputs(root, req):
    return cited_files(req, read_editorial(req, root))


def shopping_note(source):
    items = source["items"]
    priced = [Decimal(i["Quantity x unit GBP"]) for i in items if i["Quantity x unit GBP"]]
    pending = len(items) - len(priced)
    text = f"£{sum(priced):,.2f} across {len(priced)} priced lines." if priced else "No allocated, priced lines."
    if pending:
        text += f" {pending} further line(s) need a price or room allocation."
    dates = sorted({item["Price date"] or "undated" for item in items})
    return note(source["room"] + " shopping subtotal", text + " Covers scheduled items only.",
                "Shopping issue " + source["issue"] + " | Price dates " + ", ".join(dates))


def resolve_edition(root, req, issue, inputs):
    kind, = req["components"]
    title = TITLES[kind]
    folder = Path("Briefs") / kind
    stem = (folder / f"{req['house']}-{kind}-{issue}").as_posix()
    pdf = stem + ".pdf"
    files = {"Start here.html": "Issue contents", edition_index(kind): title,
             pdf: "Print " + title.lower()}
    if kind == "homeowner-presentation":
        files[stem + ".pptx"] = "Edit the presentation in PowerPoint"
    register = (folder / "Drawing-register.csv").as_posix()
    if kind == "architect-pack":
        files[register] = "Drawing register"
    chapters = read_editorial(req, inputs)
    spec = dict(req, slug=kind, room="Whole house", issue=issue,
                house_name=revisions.stored_json(root / "project.json")["name"],
                files=files, pdf=pdf, pages=[], drawings=[], sources={})
    assets = {}
    for ref in cited_files(req, chapters):
        path = revisions.local_path(inputs, ref)
        checksum = digest(path)
        if checksum != digest(revisions.local_path(root, ref)):
            raise ValueError(f"Audience copy or cited evidence changed: {ref}. Begin a fresh edition.")
        key = "editorial" if ref == req["editorial"] else "evidence/" + ref
        assets[key] = path
        spec["sources"][key] = {"revision": issue, "path": ref, "sha256": checksum}
    costs = []
    room_pages = []
    visual_inputs = {}
    from house_visuals import Catalogue, checked_placement
    live = frozen = None
    def chapter(title, entries):
        return {"title": title, "notes": entries, "visual": None}
    for slug, component, source, raw, issued in room_sources(root, req, EDITIONS[kind]):
        if component == "shopping":
            key = f"{slug}/{source['issue']}/shopping"
            csv_path, = [path for name, (_, path) in issued.items() if name.endswith(".csv")]
            assets[key] = csv_path
            spec["sources"][key] = {"revision": source["issue"], "sha256": digest(csv_path)}
            costs.append(dict(shopping_note(source), source=key))
            continue
        basis = f"{source['stage']} | {source['sheet_id']} | {source['source_revision']}"
        if live is None:
            live, frozen = Catalogue(root), Catalogue(root, inputs)
        def placement(role, purpose):
            original = source["visual_reviews"][role][component]
            return checked_placement(live, frozen, visual_id=original["id"], path=raw[role], purpose=purpose,
                                     phase=original["design"]["phase"], scope="room/"+slug,
                                     view=original["view"], page=original["page"])
        if kind == "architect-pack":
            (name, (_, path)), = issued.items()
            target = (folder / "Drawings" / Path(name).name).as_posix()
            if target in files or any(d["Sheet"] == source["sheet_id"] for d in spec["drawings"]):
                raise ValueError("Each architect drawing needs a distinct file and sheet ID")
            files[target] = source["sheet_id"] + " | " + source["sheet_title"]
            spec["drawings"].append({"Sheet": source["sheet_id"], "Room": source["room"],
                                     "Title": source["sheet_title"], "Review stage": source["stage"],
                                     "Design revision": source["source_revision"], "Issued sheet": source["issue"],
                                     "Scale basis": source["scale_basis"], "Issue limitation": source["limitation"],
                                     "File": "Drawings/" + path.name})
            spec["sources"][target] = {"revision": source["issue"], "sha256": digest(path),
                                       "placement_review": placement("sheet", "architect-pack.drawing")}
            assets[target] = path
            continue
        detail = [note("Reviewed finding", source["finding"], basis)]
        if component == "room-review":
            detail.insert(0, note("Using the room", source["daily_use"], source["room"] + " review " + source["issue"]))
        for role in raw:
            key = f"{slug}/{source['issue']}/{role}"
            assets[key] = raw[role]
            reference = source["sources"][role]
            spec["sources"][key] = {"revision": reference["path"].split("/")[1], **reference}
            visual_inputs[key] = source["visual_reviews"][role][component]
            sheet = role == "sheet"
            caption = source["sheet_caption"] if sheet else source["view_captions"][role]
            if sheet:
                caption += " " + source["scale_basis"]
            visual = {"key": key, "page": source.get("sheet_page", 1) if sheet else 1,
                      "caption": caption, "purpose": kind+".room"}
            role_title = "Reviewed camera" if role.startswith("camera-") else "Reviewed concept photo"
            room_pages.append({"title": source["room"] if sheet else source["room"] + " | " + role_title,
                               "notes": detail if sheet else [note(role_title, caption, source["issue"])],
                               "visual": visual})
    limits = [note("Issue limits", req["limitation"], req["purpose"]),
              note("Next action", req["next_action"], req["audience"])]
    omissions = [note(slug + " | " + role, reason, "Recorded scope of this issue")
                 for slug, omitted in sorted(req.get("omissions", {}).items())
                 for role, reason in sorted(omitted.items())]
    if kind == "buyer-brief":
        # Combine short related entries so a viewing copy stays compact.
        opening = chapter("Purchase scenario", chapters["scenario"])
        if room_pages:
            first_room, *room_pages = room_pages
            opening["visual"] = dict(first_room["visual"], purpose="buyer-brief.scenario")
            opening["notes"] = [*opening["notes"], *first_room["notes"]]
        spec["pages"] = [opening, *room_pages,
                         chapter("Costs and occupation", [*chapters["cost_basis"], *costs,
                                                          *chapters["occupation"], *omissions]),
                         chapter("Viewing and follow-up", [*chapters["viewing"], *chapters["follow_up"], *limits])]
    elif kind == "architect-pack":
        if not spec["drawings"]:
            raise ValueError("The architect pack requires a reviewed drawing")
        approved = [r["placement_review"] for r in spec["sources"].values() if "placement_review" in r]
        live.coverage(approved, {p["scope"] for p in approved}, phases={p["design"]["phase"] for p in approved})
        register_notes = [note(d["Sheet"] + " | " + d["Room"], d["Title"],
                               d["Review stage"] + " | Design " + d["Design revision"] + " | Issue "
                               + d["Issued sheet"] + " | " + d["Scale basis"]) for d in spec["drawings"]]
        spec["pages"] = [chapter("Appointment brief", [*chapters["appointment"], *chapters["exclusions"],
                                                       *chapters["survey"], *chapters["coordination"]]),
                         chapter("Drawing register and issue limits", [*register_notes, *omissions, *limits])]
    else:
        opening = chapter("Your decision", chapters["decision"])
        if room_pages:
            opening["visual"] = dict(room_pages[0]["visual"], purpose="homeowner-presentation.opening")
        spec["pages"] = [opening, *room_pages, chapter("The options", chapters["options"]),
                         chapter("Costs and order of work", [*costs, *chapters["phasing"], *omissions, *limits])]
    # Paginate before freezing the manifest so asset uses have actual printed page numbers.
    spec["pages"] = pages.paginate(spec)
    for page in spec["pages"]:
        visual = page["visual"]
        if visual:
            key, purpose = visual["key"], visual["purpose"]
            original = visual_inputs[key]
            grants = spec["sources"][key].setdefault("placement_reviews", {})
            if purpose not in grants:
                grants[purpose] = checked_placement(live, frozen, visual_id=original["id"], path=assets[key],
                    purpose=purpose, phase=original["design"]["phase"], scope=original["scope"],
                    view=original["view"], page=visual["page"])
    return spec, assets


def asset_uses(spec):
    result = {}
    presentations = [n for n in spec["files"] if n.endswith((".pdf", ".pptx")) and "/Drawings/" not in n]
    for key, source in spec["sources"].items():
        if key in spec["files"]:
            position = next(i for i, d in enumerate(spec["drawings"], 1)
                            if key.endswith("/" + d["File"]))
            uses = [{"file": key}, {"file": spec["pdf"], "pages": [len(spec["pages"]) + position]}]
        else:
            numbers = [i for i, page in enumerate(spec["pages"], 1)
                       if (page["visual"] and page["visual"]["key"] == key)
                       or any(entry.get("source") == key or key in ["evidence/" + p for p in entry.get("evidence", [])]
                              for entry in page["notes"])]
            uses = [{"file": n, "pages": numbers} for n in presentations]
        result[key] = {**source, "uses": uses}
        if "placement_reviews" in source:
            result[key]["reviewed_uses"] = [{"placement": proof, "use": {"file": name, "pages": [i]}}
                for purpose, proof in source["placement_reviews"].items()
                for i, page in enumerate(spec["pages"], 1)
                if page["visual"] and (page["visual"]["key"], page["visual"]["purpose"]) == (key, purpose)
                for name in presentations]
    return result


def build_edition(envelope, spec, assets, selection_hash):
    root = envelope / "delivery"
    kind = spec["slug"]
    index = edition_index(kind)
    for name in spec["files"]:
        (root / name).parent.mkdir(exist_ok=True, parents=True)
    for key, source in spec["sources"].items():
        if digest(assets[key]) != source["sha256"]:
            raise ValueError(f"Source changed before rendering {key}")
        if key in spec["files"] and revisions.copy_file(assets[key], root / key) != source["sha256"]:
            raise ValueError(f"Issued sheet changed during copy: {key}")
    if spec["drawings"]:
        (root / index).with_name("Drawing-register.csv").write_bytes(render_pack.csv_bytes(spec["drawings"]))
    pages.render(root, spec, assets)
    parent = Path(index).parent
    links = []
    for name, label in spec["files"].items():
        if name in (index, "Start here.html"):
            continue
        rel = Path(name).relative_to(parent).as_posix()
        links.append(f'<li><a href="{quote(rel)}">{escape(label)}</a> · {Path(name).suffix[1:].upper()}</li>')
    (root / index).write_bytes(render_pack.html_page(spec, TITLES[kind], "<ul>" + "".join(links) + "</ul>").encode())
    entry = f'<p><a href="{quote(index)}">Open the {escape(TITLES[kind].lower())}</a></p>'
    (root / "Start here.html").write_bytes(render_pack.html_page(spec, TITLES[kind], entry).encode())
    render_pack.seal(envelope, spec, selection_hash, spec["files"])


def verify_edition(envelope, spec, manifest, assets):
    name = render_pack.verify_contents(envelope, spec, manifest, spec["files"])
    root = envelope / "delivery"
    index = edition_index(spec["slug"])
    expected = {Path(n).relative_to(Path(index).parent).as_posix() for n in spec["files"]
                if n not in (index, "Start here.html")}
    links = {unquote(url) for url in Page((root / index).read_bytes()).links}
    if links != expected or index not in [unquote(url) for url in Page((root / "Start here.html").read_bytes()).links]:
        raise ValueError("The edition entry page must link every commissioned reader file")
    pages.verify(root, spec, assets)
    if spec["drawings"]:
        directory = (root / spec["pdf"]).parent
        if (directory / "Drawing-register.csv").read_bytes() != render_pack.csv_bytes(spec["drawings"]):
            raise ValueError("Architect register differs from its commissioned sheets")
        with fitz.open(root / spec["pdf"]) as book:
            for i, drawing in enumerate(spec["drawings"], len(spec["pages"])):
                sheet = directory / drawing["File"]
                if digest(sheet) != spec["sources"][sheet.relative_to(root).as_posix()]["sha256"]:
                    raise ValueError(f"Forwardable drawing changed: {drawing['Sheet']}")
                with fitz.open(sheet) as original:
                    if original[0].get_pixmap().digest != book[i].get_pixmap().digest:
                        raise ValueError(f"Bound drawing differs from {drawing['Sheet']}")
    return render_pack.receipt(spec, manifest, envelope, name)
