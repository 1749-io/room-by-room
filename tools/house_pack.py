"""Assemble a house edition from previously saved recipient files."""
from html import escape
from pathlib import Path
from urllib.parse import quote

import fitz

import house_revisions as revisions
from house_delivery import SCHEDULES, digest, resolve
from tools import render_pack

DIRECTORIES = {"room-review": "Rooms/", "drawing": "Drawings/", "shopping": "Schedules/"}
ROOM_FILES_PER_PAGE = 8


def publication(kind):
    from tools.audience_packs import TITLES, edition_index
    if kind in SCHEDULES:
        return SCHEDULES[kind], f"Schedules/{kind}/Read me.html"
    return TITLES[kind], edition_index(kind)


def require_recipients(source, request):
    allowed = {source["audience"], *source.get("share_with", [])}
    missing = {request["audience"], *request.get("share_with", [])} - allowed
    if missing:
        raise ValueError(f"{source['issue']}: audience permission missing for {', '.join(sorted(missing))}")


def selected_issues(selection, edition):
    for component, value in sorted(selection.items()):
        if isinstance(value, list) and (component == "drawing" or edition and component == "room-review"):
            if not value or any(not isinstance(v, str) for v in value) or len(set(value)) != len(value):
                raise ValueError(f"Select distinct saved revisions for {component}")
            for revision in value:
                yield component, revision
        else:
            if not isinstance(value, str):
                raise ValueError(f"Select a saved revision for {component}")
            yield component, value


def room_sources(root, req, components):
    registered = {p.parent.name for p in (root / "rooms").glob("*/review.csv")}
    supplied = set(req["rooms"])
    if registered != supplied:
        raise ValueError(f"House room coverage differs. Missing {sorted(registered-supplied)}, unexpected {sorted(supplied-registered)}")
    checked = {}
    omissions = req.get("omissions", {}) if req.get("profile") == "edition" else {}
    if not isinstance(omissions, dict) or set(omissions) - supplied:
        raise ValueError("Declare omissions against commissioned rooms")
    for slug, selection in sorted(req["rooms"].items()):
        omitted = omissions.get(slug, {})
        if (not isinstance(omitted, dict) or not isinstance(selection, dict) or set(omitted) & set(selection)
                or any(not isinstance(v, str) or not v.strip() for v in omitted.values())
                or set(selection) | set(omitted) != set(components)):
            raise ValueError(f"{slug}: name a saved issue for each commissioned component")
        for component, revision in selected_issues(selection, req.get("profile") == "edition"):
            rev = revisions.revision_id(revision)
            folder = revisions.record_dir(root, rev)
            if rev not in checked:
                record = revisions.verify_revision(root, rev)
                receipt = record.get("pack_issue", {}).get("checked", {})
                envelope = folder / "outputs/pack"
                manifest = revisions.stored_json(envelope / "issue-manifest.json")
                source = manifest["request"]
                if source.get("profile", "room") != "room" or not receipt:
                    raise ValueError(f"{rev}: select a previously issued room component")
                if receipt != render_pack.verify(envelope, source, manifest):
                    raise ValueError(f"{rev}: the reviewed source issue differs")
                checked[rev] = record, source, manifest["files"]
            record, source, names = checked[rev]
            require_recipients(source, req)
            if source["slug"] != slug or component not in source["components"]:
                raise ValueError(f"{slug} / {component}: {rev} differs in room, audience or scope")
            current, raw_assets = resolve(root, record, folder, components=[component])
            for role, grants in current.get("visual_reviews", {}).items():
                if grants.get(component) != source.get("visual_reviews", {}).get(role, {}).get(component):
                    raise ValueError(f"{rev}: reissue {component} with its current visual placement review")
            if component == "shopping" and current["items"] != source.get("items"):
                raise ValueError(f"{slug}: the issued shopping rows differ from the current allocation")
            for role, reference in current["sources"].items():
                if source["sources"].get(role) != reference:
                    raise ValueError(f"{slug} / {component}: {role} has changed since {rev}")
            if component == "room-review" and current["sources"] != source["sources"]:
                raise ValueError(f"{slug}: the room now requires different reviewed views")
            issued = {n: (label, revisions.local_path(folder / "outputs/pack/delivery", n))
                      for n, label in names.items() if n.startswith(DIRECTORIES[component])}
            yield slug, component, current, raw_assets, issued


def resolve_house(root, req, issue):
    files = {"Start here.html": "House issue contents", "Issue.pdf": "House transmittal"}
    assets, sources = {}, {}
    placements = []
    for _, component, source, _, issued in room_sources(root, req, req["components"]):
        for name, (label, path) in issued.items():
            if name in files:
                raise ValueError(f"Two commissioned components use the same file: {name}. Use distinct sheet IDs.")
            files[name] = f"{source['room']} | {label}"
            assets[name] = path
            sources[name] = {"revision": source["issue"], "component": component, "room": source["room"],
                             "sha256": digest(path)}
            if source.get("visual_reviews"):
                trace = render_pack.asset_uses(source, render_pack.outputs(source))
                for role, item in trace.items():
                    for use in item["uses"]:
                        if use["file"] == name:
                            placements.append({"placement": source["visual_reviews"][role][component], "use": use})
    for kind, rev in sorted(req.get("editions", {}).items()):
        from tools.audience_packs import verify_edition
        from tools.schedule_pack import verify_schedule
        record = revisions.verify_revision(root, rev)
        folder = revisions.record_dir(root, rev)
        envelope = folder / "outputs/pack"
        manifest = revisions.stored_json(envelope / "issue-manifest.json")
        source = manifest["request"]
        profile = "schedule" if kind in SCHEDULES else "edition"
        if source.get("profile") != profile or source["components"] != [kind]:
            raise ValueError(f"{rev}: select an issued {kind}")
        require_recipients(source, req)
        current, edition_assets = resolve(root, record, folder)
        receipt = (verify_schedule(envelope, current, manifest) if profile == "schedule"
                   else verify_edition(envelope, current, manifest, edition_assets))
        if receipt != record.get("pack_issue", {}).get("checked"):
            raise ValueError(f"{rev}: missing or different edition review")
        title, entry = publication(kind)
        prefix = entry.rsplit("/", 1)[0] + "/"
        for name, label in source["files"].items():
            if name.startswith(prefix):
                path = envelope / "delivery" / name
                files[name] = f"{title} | {label}"
                assets[name] = path
                sources[name] = {"revision": rev, "component": kind, "edition": kind, "sha256": digest(path)}
                for item in manifest["asset_uses"].values():
                    placements.extend(use for use in item.get("reviewed_uses", []) if use["use"]["file"] == name)
                    if "placement_review" in item:
                        placements.extend({"placement": item["placement_review"], "use": use}
                                          for use in item["uses"] if use["file"] == name)
    spec = dict(req, house_name=revisions.stored_json(root / "project.json")["name"], issue=issue,
                room="Whole house", slug="house", files=files, sources=sources)
    if placements:
        from house_visuals import Catalogue
        proofs = [entry["placement"] for entry in placements]
        if "drawing" in req["components"] and "room-review" in req["components"]:
            Catalogue(root).coverage(proofs, {"room/"+slug for slug in req["rooms"]},
                                     phases={p["design"]["phase"] for p in proofs})
        spec["visual_uses"] = placements
    return spec, assets


def commissioned_room_files(spec, choices):
    issues = {revisions.revision_id(rev) for _, rev in selected_issues(choices, False)}
    return [name for name, source in spec["sources"].items() if source["revision"] in issues]


def build_house(envelope, spec, assets, selection_hash):
    root = envelope / "delivery"
    root.mkdir(parents=True)
    for name, path in assets.items():
        if revisions.copy_file(path, root / name) != spec["sources"][name]["sha256"]:
            raise ValueError(f"Source changed during assembly: {name}")
    sections = []
    with fitz.open() as doc:
        for _, choices in sorted(spec["rooms"].items()):
            names = commissioned_room_files(spec, choices)
            room = spec["sources"][names[0]]["room"]
            links, printed = [], []
            for name in names:
                source = spec["sources"][name]
                label = spec["files"][name].split(" | ", 1)[1]
                detail = f"{label} · {Path(name).suffix[1:].upper()} · {source['revision']}"
                links.append(f'<li><a href="{quote(name)}">{escape(detail)}</a></li>')
                printed.append(detail)
            sections.append(f"<h2>{escape(room)}</h2><ul>{''.join(links)}</ul>")
            for start in range(0, len(printed), ROOM_FILES_PER_PAGE):
                page = render_pack.sheet_page(doc, spec, room + " / issue contents")
                render_pack.pdf_text(page, (34, 99, 803, 180), spec["purpose"], 15)
                render_pack.pdf_text(page, (34, 190, 803, 500), "\n".join(printed[start:start+ROOM_FILES_PER_PAGE]), 14)
        if spec.get("editions"):
            heading = "Included in this handover" if SCHEDULES.keys() & spec["editions"].keys() else "Audience editions"
            for index, (kind, rev) in enumerate(sorted(spec["editions"].items())):
                if index % 4 == 0:
                    page = render_pack.sheet_page(doc, spec, heading)
                label, entry = publication(kind)
                sections.append(f'<h2><a href="{quote(entry)}">{escape(label)}</a></h2>')
                render_pack.pdf_text(page, (34, 105+(index%4)*90, 802, 181+(index%4)*90),
                                     f"{label}  /  {rev}\n{entry}", 15)
        (root / "Issue.pdf").write_bytes(render_pack.pdf_bytes(doc))
    sections.append('<p><a href="Issue.pdf">Print the house issue contents</a></p>')
    (root / "Start here.html").write_bytes(render_pack.html_page(spec, "House handover", "".join(sections)).encode())
    render_pack.seal(envelope, spec, selection_hash, spec["files"])
    verify_house(envelope, spec, revisions.stored_json(envelope / "issue-manifest.json"))


def verify_house(envelope, spec, manifest):
    name = render_pack.verify_contents(envelope, spec, manifest, spec["files"])
    if spec.get("editions"):
        from tools.check_delivery import Page
        links = Page((envelope / "delivery/Start here.html").read_bytes()).links
        if any(quote(publication(kind)[1]) not in links for kind in spec["editions"]):
            raise ValueError("A commissioned publication is missing from the house entry page")
    for member, source in spec["sources"].items():
        if digest(envelope / "delivery" / member) != source["sha256"]:
            raise ValueError(f"House issue differs from the standalone component: {member}")
    with fitz.open(envelope / "delivery/Issue.pdf") as doc:
        room_sizes = (len(commissioned_room_files(spec, choices)) for choices in spec["rooms"].values())
        expected_pages = sum((n+ROOM_FILES_PER_PAGE-1)//ROOM_FILES_PER_PAGE for n in room_sizes)
        expected_pages += (len(spec.get("editions", {})) + 3) // 4
        if len(doc) != expected_pages or any(spec["issue"] not in page.get_text() for page in doc):
            raise ValueError("Missing house transmittal page or issue identity")
    return render_pack.receipt(spec, manifest, envelope, name)
