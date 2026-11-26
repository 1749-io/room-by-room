"""Click local HTML links and decode page images in Chromium after extracting a pack."""
import argparse
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright


def check(start, channel=None, *, width=1280):
    with sync_playwright() as api:
        browser = api.chromium.launch(channel=channel)
        page = browser.new_page(accept_downloads=False, viewport={"width": width, "height": 850})
        page.context.set_offline(True)
        pending = [start.resolve()]
        seen = set()
        clicks = 0
        while pending:
            source = pending.pop()
            if source in seen:
                continue
            seen.add(source)
            page.goto(source.as_uri())
            urls = page.locator("a[href]").evaluate_all("(els) => els.map(e => e.getAttribute('href'))")
            for index, url in enumerate(urls):
                ref = urlsplit(url)
                if ref.scheme or not ref.path or not ref.path.lower().endswith(".html"):
                    continue
                target = (source.parent / unquote(ref.path)).resolve()
                if target not in seen:
                    pending.append(target)
                page.locator("a[href]").nth(index).click()
                assert page.url.split("#")[0] == target.as_uri(), (source, url, page.url)
                assert page.locator("body").inner_text().strip(), target
                page.goto(source.as_uri())
                clicks += 1
            images = page.locator("img")
            for index in range(images.count()):
                img = images.nth(index)
                label = img.get_attribute("alt") or f"image {index + 1}"
                try:
                    img.scroll_into_view_if_needed()
                    img.evaluate("async i => { i.loading = 'eager'; await i.decode() }")
                except Exception as exc:
                    raise ValueError(f"{source.name} at {width}px: could not display {label}") from exc
        browser.close()
        return len(seen), clicks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", type=Path)
    parser.add_argument("--channel")
    parser.add_argument("--width", type=int, default=1280)
    args = parser.parse_args()
    print(check(args.start, args.channel, width=args.width))
