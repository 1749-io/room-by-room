"""Render portable publications from a resolved, single-room commission."""
import base64
import csv
from contextlib import contextmanager
import io
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import tempfile
from urllib.parse import quote

import house_revisions as revisions
from house_delivery import digest
from tools.check_delivery import verify_issue

NUMERIC_FIELDS = {"Quantity", "Source quantity", "Unit GBP", "Quantity x unit GBP"}
CSS = """*{box-sizing:border-box}body{margin:0;background:#f3f1eb;color:#1f3833;
font:17px/1.5 system-ui,sans-serif}main{max-width:920px;margin:32px auto;padding:32px 5%;
background:white;border-top:6px solid #386754}h1,h2{font-family:Georgia,serif;line-height:1.15}
h1{font-size:2.35rem}h2{margin-top:1.6em}a{color:#205d48}img{width:100%;height:auto}
figure{margin:22px 0}figcaption,footer{font-size:.88rem;color:#41534d}
li{margin:.6em 0}.context{color:#3c5c50}footer{border-top:1px solid #c9d4ce;padding-top:16px}
@media(max-width:600px){main{margin:0;padding:20px}h1{font-size:1.9rem}}
@media print{main{margin:0;max-width:none}figure{break-inside:avoid}}"""


def outputs(spec):
    stem = f"{spec['house']}-{spec['slug']}-{spec['issue']}"
    files = {"Start here.html": "Issue contents"}
    if "room-review" in spec["components"]:
        for ext, label in (("html", "Read the room review"), ("pdf", "Print the room review")):
            files[f"Rooms/{spec['slug']}/{stem}-review.{ext}"] = label
    if "drawing" in spec["components"]:
        files[f"Drawings/{stem}-drawing.pdf"] = spec["sheet_title"]
    if "shopping" in spec["components"]:
        for ext, label in (("xlsx", "Filter the shopping schedule"), ("csv", "Shopping data")):
            files[f"Schedules/{stem}-shopping.{ext}"] = label
    if len(spec["components"]) > 1:
        files["Issue.pdf"] = "Print the issue contents"
    return files


def plan_text(spec):
    return "\n".join([f"{spec['house_name']} / {spec['room']} / {spec['issue']}",
                      *outputs(spec), f"Limit: {spec['limitation']}", f"Next: {spec['next_action']}"])


def meta(spec):
    return f"{spec['house_name']}  /  {spec['room']}  /  {spec['issue']}"


def html_page(spec, title, body):
    text = lambda field: escape(spec[field])
    return (f'<!doctype html><html lang="en-GB"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)} | {escape(meta(spec))}</title><style>{CSS}</style>'
            f'<main><p class="context">{escape(meta(spec))}</p><h1>{escape(title)}</h1>'
            f'<p>{text("purpose")}</p>{body}<footer><p><b>Use and limits</b><br>{text("limitation")}</p>'
            f'<p><b>Next action</b><br>{text("next_action")}</p>{text("audience")}</footer></main></html>')


def pdf_text(page, box, value, size, *, serif=False):
    import fitz
    room = page.insert_textbox(fitz.Rect(box), value, fontsize=size, fontname="tiro" if serif else "helv",
                               lineheight=1.18, color=(0.12, 0.23, 0.19))
    if room < 0:
        raise ValueError(f"Text exceeds the print area. Shorten or split: {value[:80]}")


def sheet_page(doc, spec, title, visual=None, page_number=1, caption=""):
    import fitz
    page = doc.new_page(width=842, height=595)
    page.draw_rect(page.rect, fill=(0.985, 0.981, 0.963), color=None)
    pdf_text(page, (34, 20, 807, 41), meta(spec), 11)
    pdf_text(page, (34, 47, 809, 91), title, 25, serif=True)
    if visual:
        bounds = fitz.Rect(34, 98, 808, 452)
        if visual.suffix.lower() == ".pdf":
            with fitz.open(visual) as source:
                if not 1 <= page_number <= len(source):
                    raise ValueError(f"Missing source sheet page {page_number}")
                page.show_pdf_page(bounds, source, page_number - 1)
        else:
            if page_number != 1:
                raise ValueError("Raster drawings have one sheet")
            page.insert_image(bounds, filename=str(visual))
        pdf_text(page, (34, 461, 807, 515), caption, 11)
    page.draw_line((34, 521), (807, 521), color=(0.67, 0.73, 0.69))
    pdf_text(page, (34, 531, 808, 581), spec["limitation"] + "\n" + spec["next_action"], 10)
    return page


def pdf_bytes(document):
    return document.tobytes(garbage=4, deflate=True, no_new_id=True)


def inline_figure(page, caption):
    import fitz
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    data = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    return f'<figure><img alt="{escape(caption, quote=True)}" src="data:image/png;base64,{data}"><figcaption>{escape(caption)}</figcaption></figure>'


def write_design(delivery, files, spec, assets):
    import fitz
    title = f"{spec['sheet_id']}  /  {spec['sheet_title']}"
    caption = f"{spec['sheet_caption']}  |  {spec['scale_basis']}  |  Source {spec['source_revision']}"
    number = spec.get("sheet_page", 1)
    if type(number) is not int or number < 1:
        raise ValueError("sheet_page must be a positive page number")
    with fitz.open() as drawing:
        sheet = sheet_page(drawing, spec, title, assets["sheet"], number, caption)
        if "drawing" in spec["components"]:
            dest = next(n for n in files if n.startswith("Drawings/"))
            (delivery / dest).write_bytes(pdf_bytes(drawing))
        if "room-review" not in spec["components"]:
            return
        figures = [inline_figure(sheet, caption)]
        with fitz.open() as room:
            summary = sheet_page(room, spec, spec["room"] + " review")
            summary.show_pdf_page(fitz.Rect(34, 112, 526, 436), drawing, 0,
                                  clip=fitz.Rect(32, 96, 810, 454))
            pdf_text(summary, (34, 450, 524, 513), caption, 10)
            for y, header, content in [(101, "Purpose", spec["purpose"]), (213, "Using this room", spec["daily_use"]),
                                       (386, "Reviewed finding", spec["finding"])]:
                pdf_text(summary, (550, y, 807, y+22), header, 15, serif=True)
                end = 375 if header == "Using this room" else y+110
                pdf_text(summary, (550, y+26, 807, end), content, 11)
            room.insert_pdf(drawing)
            for role, path in assets.items():
                if role == "sheet":
                    continue
                label = role.replace("camera-", "Reviewed furnished camera ").replace("photo-", "Final concept photo ")
                view = spec["view_captions"][role]
                image_page = sheet_page(room, spec, label, path, caption=view)
                figures.append(inline_figure(image_page, label + " | " + view))
            body = ("<h2>Using this room</h2><p>" + escape(spec["daily_use"]) + "</p>"
                    "<h2>Reviewed finding</h2><p>" + escape(spec["finding"]) + "</p>" + "".join(figures))
            for name in files:
                if name.startswith("Rooms/"):
                    if name.endswith(".pdf"):
                        (delivery / name).write_bytes(pdf_bytes(room))
                    else:
                        (delivery / name).write_bytes(html_page(spec, spec["room"] + " review", body).encode())


def check_visual_files(delivery, spec, assets):
    """Reproduce current issue files from the signed sources before recording reader approval."""
    for role, path in assets.items():
        expected = {p["approval"]["source"]["sha256"] for p in spec["visual_reviews"][role].values()}
        if expected != {digest(path)}:
            raise ValueError(f"The {role} source differs from the signed visual")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        names = [n for n in outputs(spec) if n.startswith(("Rooms/", "Drawings/"))]
        for name in names:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
        write_design(root, names, spec, assets)
        for name in names:
            if digest(root / name) != digest(delivery / name):
                raise ValueError(f"{name}: the issued page differs from the signed visual placement")


def schedule(spec):
    return [dict(House=spec["house_name"], Room=spec["room"], Issue=spec["issue"], **item,
                 **{"Issue limitation": spec["limitation"], "Next action": spec["next_action"]})
            for item in spec["items"]]


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def stable_office_bytes(stream, replacements=None):
    """Use the same ZIP headers on every platform when packaging Office parts."""
    out = io.BytesIO()
    with zipfile.ZipFile(stream) as source, zipfile.ZipFile(out, "w") as target:
        for name in sorted(source.namelist()):
            entry = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            data = replacements[name] if replacements and name in replacements else source.read(name)
            target.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()


@contextmanager
def editable_workbook(path):
    import xlsxwriter
    stream = io.BytesIO()
    # In-memory XML avoids platform-dependent newlines in XlsxWriter's temporary files.
    with xlsxwriter.Workbook(stream, {"in_memory": True, "strings_to_formulas": False,
                                      "strings_to_urls": False}) as book:
        yield book
    path.write_bytes(stable_office_bytes(stream))


def write_shopping(delivery, files, spec):
    rows = schedule(spec)
    columns = list(rows[0])
    csv_path = next(n for n in files if n.endswith("-shopping.csv"))
    (delivery / csv_path).write_bytes(csv_bytes(rows))
    with editable_workbook((delivery / csv_path).with_suffix(".xlsx")) as book:
        book.set_properties({"title": meta(spec), "created": datetime(2000, 1, 1, tzinfo=timezone.utc)})
        sheet = book.add_worksheet("Shopping")
        sheet.freeze_panes(1, 3)
        sheet.add_table(0, 0, len(rows), len(columns)-1, {"columns": [{"header": c} for c in columns],
                                                         "style": "Table Style Medium 4"})
        wrapped = book.add_format({"text_wrap": True, "valign": "top"})
        for col, field in enumerate(columns):
            sheet.set_column(col, col, min(58, max(15, len(field)+3, max(len(r[field]) for r in rows)+1)))
        for index, row in enumerate(rows, 1):
            for col, field in enumerate(columns):
                value = row[field]
                if field in NUMERIC_FIELDS and value:
                    sheet.write_number(index, col, float(value))
                elif value:
                    sheet.write_string(index, col, value, wrapped)


def build(envelope, spec, assets, selection_hash):
    import fitz
    files = outputs(spec)
    root = envelope / "delivery"
    for name in files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
    if assets:
        write_design(root, files, spec, assets)
    if "shopping" in spec["components"]:
        write_shopping(root, files, spec)
    links = "".join(f'<li><a href="{quote(n)}">{escape(label)}</a> · {Path(n).suffix[1:].upper()}</li>'
                    for n, label in files.items() if n != "Start here.html")
    (root / "Start here.html").write_bytes(html_page(spec, spec["room"] + " issue", "<ul>"+links+"</ul>").encode())
    if "Issue.pdf" in files:
        with fitz.open() as doc:
            page = sheet_page(doc, spec, spec["room"] + " issue")
            pdf_text(page, (34, 98, 800, 179), spec["purpose"], 15)
            pdf_text(page, (34, 186, 800, 502), "\n".join(label + "  /  " + Path(n).suffix[1:].upper()
                     for n, label in files.items() if n not in ("Start here.html", "Issue.pdf")), 14)
            (root / "Issue.pdf").write_bytes(pdf_bytes(doc))
    seal(envelope, spec, selection_hash, files)
    verify(envelope, spec, revisions.stored_json(envelope / "issue-manifest.json"))


def seal(envelope, spec, selection_hash, files):
    root = envelope / "delivery"
    rows = [{"label": label, "purpose": spec["purpose"], "path": name, "sha256": digest(root/name)}
            for name, label in files.items()]
    (root / "Link-register.csv").write_bytes(csv_bytes(rows))
    archive = envelope / f"{spec['house']}-{spec['slug']}-{spec['issue']}.zip"
    with zipfile.ZipFile(archive, "x") as out:
        for name in sorted([*files, "Link-register.csv"]):
            entry = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            out.writestr(entry, (root / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    manifest = {"version": 1, "selection_sha256": selection_hash, "request": spec,
                "asset_uses": asset_uses(spec, files),
                "files": files, "archive": archive.name, "archive_sha256": digest(archive)}
    revisions.write_json(envelope / "issue-manifest.json", manifest)


def asset_uses(spec, files):
    if spec.get("profile") == "schedule":
        return {key: {**source, "uses": [{"file": n} for n in files if n.startswith("Schedules/")]}
                for key, source in spec["sources"].items()}
    if spec.get("profile") == "edition":
        from tools.audience_packs import asset_uses as edition_uses
        return edition_uses(spec)
    if spec.get("profile") == "house":
        return {name: {"source_revision": source["revision"], "source_sha256": source["sha256"],
                       "uses": [{"file": name}]} for name, source in spec["sources"].items()}
    uses = {}
    for index, (role, source) in enumerate(spec["sources"].items()):
        destinations = []
        for name in files:
            if name.startswith("Drawings/") and role == "sheet":
                destinations.append({"file": name, "pages": [1]})
            if name.startswith("Rooms/"):
                pages = [1, 2] if role == "sheet" else [index + 2]
                destinations.append({"file": name, "pages": pages} if name.endswith(".pdf") else {"file": name})
        uses[role] = {**source, "uses": destinations}
        if "visual_reviews" in spec:
            uses[role]["placement_reviews"] = spec["visual_reviews"][role]
    return uses


def verify(envelope, spec, manifest):
    import fitz
    files = outputs(spec)
    root = envelope / "delivery"
    name = verify_contents(envelope, spec, manifest, files)
    for path in root.rglob("*.pdf"):
        with fitz.open(path) as doc:
            if not len(doc) or any(spec["issue"] not in page.get_text() for page in doc):
                raise ValueError(f"Missing print issue identity in {path.name}")
    if "shopping" in spec["components"]:
        verify_shopping(root, spec)
    return receipt(spec, manifest, envelope, name)


def verify_contents(envelope, spec, manifest, files):
    root = envelope / "delivery"
    name = f"{spec['house']}-{spec['slug']}-{spec['issue']}.zip"
    if (manifest.get("request") != spec or manifest.get("files") != files or manifest.get("archive") != name
            or manifest.get("asset_uses") != asset_uses(spec, files)
            or set(revisions.inventory(root)[0]) != {*files, "Link-register.csv"}
            or {p.name for p in envelope.iterdir()} != {"delivery", "issue-manifest.json", name}):
        raise ValueError("The issue differs from the commissioned file list")
    verify_issue(root, archive_folder=envelope, expected_files=files)
    if digest(envelope / name) != manifest["archive_sha256"]:
        raise ValueError("The portable issue has changed since build")
    return name


def verify_shopping(root, spec):
    from decimal import Decimal

    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
    expected = schedule(spec)
    path = next(root.rglob("*-shopping.csv"))
    if path.read_bytes() != csv_bytes(expected):
        raise ValueError("The shopping CSV differs from the selected rows")
    book = load_workbook(io.BytesIO(path.with_suffix(".xlsx").read_bytes()))
    try:
        sheet = book["Shopping"]
        data = list(sheet.values)
        coverage = f"A1:{get_column_letter(len(expected[0]))}{len(expected)+1}"
        filtered = any(t.ref == coverage and t.autoFilter and t.autoFilter.ref == coverage
                       for t in sheet.tables.values())
        if len(data) != len(expected)+1 or list(data[0]) != list(expected[0]) or not filtered:
            raise ValueError("The shopping workbook has different rows, columns or filters")
        for cells, row in zip(data[1:], expected):
            for actual, (field, wanted) in zip(cells, row.items()):
                if field in NUMERIC_FIELDS and wanted:
                    matches = type(actual) in (int, float) and Decimal(str(actual)) == Decimal(wanted)
                else:
                    matches = ("" if actual is None else actual) == wanted
                if not matches:
                    raise ValueError(f"Shopping workbook differs for {row['Item ID']} / {field}")
    finally:
        book.close()


def receipt(spec, manifest, envelope, name):
    return {"house": spec["house"], "room": spec["room"], "audience": spec["audience"],
            "components": [*spec["components"], *sorted(spec.get("editions", {}))],
            "archive": name, "sha256": manifest["archive_sha256"],
            "manifest_sha256": digest(envelope / "issue-manifest.json")}
