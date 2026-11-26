"""Recover one independently issued Alder component from the furnished example archive."""
import argparse
from copy import copy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile


REFERENCE = Path(__file__).resolve().parent / "reference"


def recover(archive_path, catalogue, component):
    entry = catalogue["components"][component]
    if sha256(archive_path.read_bytes()).hexdigest() != catalogue["house_sha256"]:
        raise ValueError("The house archive differs from the reviewed issue")
    register = entry["link_register"].encode("utf-8")
    items = csv.DictReader(io.StringIO(register.decode("utf-8-sig")))
    hashes = {row["path"]: row["sha256"] for row in items}
    result = io.BytesIO()
    with zipfile.ZipFile(archive_path) as house, zipfile.ZipFile(result, "w") as standalone:
        for name in sorted([*hashes, "Link-register.csv"]):
            if name == "Link-register.csv":
                data = register
            else:
                data = entry["start_here"].encode("utf-8") if name == "Start here.html" else house.read(name)
                if sha256(data).hexdigest() != hashes[name]:
                    raise ValueError(f"{component}: changed recipient file {name}")
            standalone.writestr(copy(house.getinfo(name)), data)
    payload = result.getvalue()
    if sha256(payload).hexdigest() != entry["archive_sha256"]:
        raise ValueError(f"{component}: the reconstructed ZIP differs from the standalone issue")
    return payload


if __name__ == "__main__":
    catalogue = json.loads((REFERENCE / "components.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=sorted(catalogue["components"]))
    parser.add_argument("output", type=Path, help="New ZIP for the selected recipient")
    args = parser.parse_args()
    data = recover(REFERENCE / catalogue["house_file"], catalogue, args.component)
    with args.output.open("xb") as stream:
        stream.write(data)
    print(args.output.resolve())
