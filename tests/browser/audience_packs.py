"""Exercise the extracted audience editions and optionally render the actual PPTX in LibreOffice."""
import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

import fitz
from playwright.sync_api import sync_playwright
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.smoke_pack_browser import check


def check_office(deck_path, executable, target):
    profile = (target / "office-profile").as_uri()
    subprocess.run([executable, "-env:UserInstallation=" + profile, "--headless", "--convert-to", "pdf",
                    "--outdir", str(target), str(deck_path)], check=True, timeout=90, capture_output=True)
    deck = Presentation(deck_path)
    with fitz.open(target / (deck_path.stem + ".pdf")) as rendered:
        assert len(rendered) == len(deck.slides)
        for index, slide in enumerate(deck.slides):
            page = rendered[index]
            words = " ".join(page.get_text().split())
            for shape in slide.shapes:
                if shape.has_text_frame:
                    assert " ".join(shape.text.split()) in words, (deck_path, index+1, shape.text)
            assert all(page.rect.contains(fitz.Rect(w[:4])) for w in page.get_text("words")), (deck_path, index+1)
            assert len(page.get_image_info()) == sum(s.shape_type == 13 for s in slide.shapes), (deck_path, index+1)
    print(f"LibreOffice rendered and read back all {len(deck.slides)} editable slides.")


def exercise(home, directory, office):
    kinds = {"OWNER": "homeowner-presentation", "ARCH": "architect-pack", "BUYER": "buyer-brief"}
    for rev in [*kinds, "HOUSE-ALL"]:
        folder = directory / rev
        with zipfile.ZipFile(next((home / "revisions" / rev / "outputs/pack").glob("*.zip"))) as pack:
            pack.extractall(folder)
        for width in (390, 1280):
            pages, clicks = check(folder / "Start here.html", width=width)
            print(f"{rev} at {width}px | {pages} offline pages / {clicks} navigation links")
    with sync_playwright() as app:
        browser = app.chromium.launch()
        page = browser.new_page(accept_downloads=True, viewport={"width": 390, "height": 844})
        page.context.set_offline(True)
        for rev, kind in kinds.items():
            for folder in [directory / rev, directory / "HOUSE-ALL"]:
                page.goto((folder / "Start here.html").as_uri())
                page.locator(f'a[href*="{kind}/Read"]').click()
                assert page.locator("h1").inner_text().casefold() == kind.replace("-", " ")
                assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
                directory_in_pack = folder / "Briefs" / kind
                links = page.locator("li a").all()
                expected = sorted({"OWNER": [".pptx", ".pdf"], "ARCH": [".pdf", ".pdf", ".csv"],
                                   "BUYER": [".pdf"]}[rev])
                assert sorted(Path(unquote(link.get_attribute("href"))).suffix for link in links) == expected
                for link in links:
                    path = directory_in_pack / unquote(link.get_attribute("href"))
                    # Ask Chromium to download the local target, including PDFs it normally opens inline.
                    link.evaluate("(a) => { a.download = ''; }")
                    with page.expect_download() as download:
                        link.click()
                    actual = download.value.path().read_bytes()
                    single = directory / rev / path.relative_to(folder)
                    assert actual == single.read_bytes(), path
        browser.close()
    if office:
        deck_path = next((directory / "OWNER").rglob("*.pptx"))
        check_office(deck_path, office, directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--house", type=Path, help="Previously issued fictional Alder Cottage")
    parser.add_argument("--office", help="LibreOffice executable for an independent PowerPoint render")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="Audience reader ") as temp:
        path = Path(temp)
        home = args.house
        if home is None:
            work = path / "example"
            subprocess.run([sys.executable, str(ROOT / "examples/audience-packs/replay.py"), str(work)], check=True)
            home = work / "houses/alder-cottage"
        exercise(home, path, args.office)
