"""Render both complete house editions from one reviewed JSON manifest."""
import argparse
import base64
import hashlib
import html
import json
import re
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from room_by_room import house_revisions as revisions
from room_by_room.house_visuals import checksum
from tools import comparison_visuals


CSS = """
@page{size:297mm 210mm;margin:0}*{box-sizing:border-box}
body{margin:0;background:#eae8df;color:#243b32;font:16px/1.45 Arial,sans-serif}
section{position:relative;max-width:1120px;margin:20px auto;background:#fbfaf5;padding:36px 45px 48px;break-after:page}
header,footer,.label{font:600 12px/1.5 Arial,sans-serif;letter-spacing:.08em;color:#476659}
h1{font:normal 42px/1.08 Georgia,serif;margin:13px 0}p{max-width:920px;margin:10px 0}
figure{margin:12px 0}img{display:block;width:100%;height:400px;object-fit:contain;background:#eeeee6}
figcaption{font-size:14px;margin-top:6px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.grid img{height:305px}.plan img{height:440px}.toc{columns:2;column-gap:30px}a{color:#215943}
footer{display:flex;gap:25px;margin-top:18px;align-items:center}small{font-size:13px}
@media(max-width:650px){.grid{display:block}.toc{columns:1}section{padding:20px}img,.grid img{height:auto;max-height:390px}}
@media print{body{background:white}section{width:297mm;height:210mm;margin:0;padding:9mm 12mm 12mm;overflow:hidden}
footer{position:absolute;bottom:7mm;left:12mm}footer a{display:none}section:last-child{break-after:auto}a{text-decoration:none}}
"""


def build(manifest, assets, out, channel=None, house=None):
    supplied_empty = out.is_dir() and not any(out.iterdir())
    if out.exists() and not supplied_empty:
        raise ValueError("Choose an empty output directory to preserve earlier issues")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".brochure-") as private:
        stage = Path(private) / "issue"
        render(manifest, assets, stage, channel, house)
        if supplied_empty:
            out.rmdir()  # Only succeeds if the caller's directory is still empty.
        stage.rename(out)


def render(manifest, assets, out, channel, house):
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    root = assets.resolve()
    if house is None:
        house = next((folder for folder in (root, *root.parents)
                      if (folder / "project.json").is_file() and (folder / "rooms").is_dir()), None)
    if house is not None:
        if not (house / "project.json").is_file() or not (house / "rooms").is_dir():
            raise ValueError("Supply the named house containing project.json and rooms")
    esc = html.escape
    receipt = comparison_visuals.preflight(house, data, root)
    uses = {(p["uses"][0]["file"], p["uses"][0]["anchor"], p["slot"]): p for p in receipt["placements"]}

    @lru_cache(None)
    def uri(name, expected):
        raw = revisions.local_path(root, name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"{name}: source changed before rendering")
        return "data:image/jpeg;base64," + base64.b64encode(comparison_visuals.reader_jpeg(raw)).decode()

    editions = {}
    for kind in ("existing", "proposed"):
        doc = data[kind]
        rooms = doc["rooms"]
        ids = [room["id"] for room in rooms]
        expected = doc["expected_rooms"]
        if not ids or sorted(ids) != sorted(expected) or len(ids) != len(set(ids)):
            raise ValueError(f"{kind}: reconcile the room inventory and tour")
        pages = [doc["cover"], {"id": "contents", "title": "Room directory", "text": doc["directory"]},
                 *doc["layouts"], *rooms, *doc.get("studies", []), *doc["particulars"]]
        groups = {id(p): group for group, items in [("cover", [doc["cover"]]), ("layouts", doc["layouts"]),
                  ("rooms", rooms), ("studies", doc.get("studies", [])), ("particulars", doc["particulars"])] for p in items}
        keys = [p["id"] for p in pages]
        if len(set(keys)) != len(keys) or not all(re.fullmatch(r"[a-z][a-z0-9-]*", k) for k in keys):
            raise ValueError(f"{kind}: duplicate or invalid page IDs")
        parts = []
        for i, p in enumerate(pages):
            pictures = p.get("images", [])
            figures = []
            for slot, im in enumerate(pictures, 1):
                use = uses[kind+".html", p["id"], slot]
                src = uri(im["path"], use["source_sha256"])
                view = use["request"]["view"]
                figures.append(f"<figure><img data-visual='{esc(im['visual_id'], quote=True)}' data-view='{view}' src='{src}' alt='{esc(im['caption'], quote=True)}'><figcaption>{esc(im['caption'])}</figcaption></figure>")
            block = "".join(figures)
            if p["id"] == "contents":
                block = "<ol class='toc'>" + "".join(f"<li><a href='#{v['id']}'>{esc(v['title'])}</a></li>" for v in pages if v["id"] not in ("contents",pages[0]["id"])) + "</ol>"
            elif len(pictures) > 1:
                block = "<div class='grid'>" + block + "</div>"
            links = []
            for label, url in p.get("sources", {}).items():
                if not url.startswith("https://"):
                    raise ValueError("Public sources need explicit HTTPS addresses")
                links.append(f"<a href='{esc(url, quote=True)}'>{esc(label)}</a>")
            controls = "".join(f"<a href='#{key}'>{label}</a>" for key,label in
                               [(keys[max(i-1,0)],"Previous"),("contents","Directory"),(keys[min(i+1,len(keys)-1)],"Next")])
            group = groups.get(id(p), "contents")
            scope = esc(p.get("scope", ""), quote=True)
            parts.append(f"<section id='{p['id']}' data-group='{group}' data-scope='{scope}' class='{'plan' if p in doc['layouts'] else ''}'><header>{esc(data['address'])} &nbsp; / &nbsp; {esc(doc['label'])}</header><h1>{esc(p['title'])}</h1><p>{esc(p['text'])}</p>{block}<p>{esc(p.get('note',''))}</p><small>{' · '.join(links)}</small><footer>{i+1} / {len(pages)} {controls}</footer></section>")
        editions[kind] = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+esc(data['address']+" | "+doc['label'])+"</title><style>"+CSS+"</style>"+''.join(parts)+"</html>",len(pages))
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("Choose an empty output directory to preserve earlier issues")
    combined = fitz.open()
    with sync_playwright() as api:
        browser = api.chromium.launch(channel=channel)
        for kind, (markup, count) in editions.items():
            page = browser.new_page()
            filename = out / (kind + ".html")
            filename.write_text(markup,encoding="utf8")
            page.goto(filename.resolve().as_uri())
            page.locator("img").evaluate_all("els => Promise.all(els.map(e => e.decode()))")
            page.emulate_media(media="print")
            overflow = page.locator("section").evaluate_all("els => els.filter(e => [...e.children].some(c => c.tagName !== 'FOOTER' && c.getBoundingClientRect().bottom > e.querySelector('footer').getBoundingClientRect().top)).map(e=>e.id)")
            if overflow:
                raise ValueError(f"{kind}: content overlaps the footer on {overflow}")
            pdf = page.pdf(prefer_css_page_size=True,print_background=True)
            with fitz.open(stream=pdf,filetype="pdf") as doc:
                if len(doc) != count:
                    raise ValueError(f"{kind}: expected {count} pages, got {len(doc)}")
                doc.set_metadata({"title": data["address"]+" | "+data[kind]["label"]})
                doc.save(out/(kind+".pdf"),garbage=4,deflate=True,no_new_id=True)
                combined.insert_pdf(doc)
            page.close()
        browser.close()
    combined.set_toc([[1,data["existing"]["label"],1],[1,data["proposed"]["label"],editions["existing"][1]+1]])
    combined.save(out/"Comparison.pdf",garbage=4,deflate=True,no_new_id=True)
    combined.close()
    index = "<h1>"+esc(data["address"])+"</h1>"+ "".join(f"<p><a href='{k}.html'>{esc(data[k]['label'])} · browser edition</a> &nbsp; <a href='{k}.pdf'>Print PDF</a></p>" for k in editions)
    (out/"Start here.html").write_text("<!doctype html><meta charset='utf-8'><style>"+CSS+"</style><section>"+index+"<p><a href='Comparison.pdf'>Both editions in one PDF</a></p></section>",encoding="utf8")
    if comparison_visuals.preflight(house, data, root) != receipt:
        raise ValueError("Visual approvals changed during brochure rendering")
    receipt["files"] = {name: checksum(out / name) for name in comparison_visuals.FILES}
    revisions.write_json(out / comparison_visuals.REPORT, receipt)
    comparison_visuals.verify_saved(house, out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ("manifest","assets","out"):
        ap.add_argument(arg,type=Path)
    ap.add_argument("--channel")
    ap.add_argument("--house", type=Path, help="House library entry when rendering from an external asset folder")
    a = ap.parse_args()
    build(a.manifest,a.assets,a.out,a.channel,a.house)
