"""Read-only storage and retention review for one house backup directory."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile


def report(directory):
    entries = {}
    for path in directory.glob("*.zip"):
        with ZipFile(path) as archive:
            header = json.loads(archive.read("backup.json"))
        if header.get("format") not in (1, 2):
            raise ValueError(f"Unknown backup format: {path.name}")
        entries[path.name] = (path, header)
    if len({header["house"] for _, header in entries.values()}) > 1:
        raise ValueError("Use a single-house directory")
    newest = sorted(entries, key=lambda n: entries[n][0].stat().st_mtime_ns, reverse=True)
    keep = set(newest[:3])
    full = next((n for n in newest if entries[n][1]["format"] == 1), None)
    if full:
        keep.add(full)
    for name in list(keep):
        header = entries[name][1]
        if header["format"] == 2:
            base = header["base"]
            if base not in entries or entries[base][1]["format"] != 1:
                raise ValueError(f"Missing full recovery base for {name}")
            keep.add(base)
    for name in newest:
        path, header = entries[name]
        print(f"{'KEEP' if name in keep else 'REVIEW'}  {path.stat().st_size / 1e6:9.1f} MB  {name}")
    print("Review older snapshots for unique drafts before pruning. Keep each retained delta's full base.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    report(parser.parse_args().directory)
