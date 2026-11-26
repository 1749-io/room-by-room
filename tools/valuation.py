"""Time-adjust comparable sales using the UK HPI for one region and dwelling class."""
import argparse
import calendar
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote


def evaluate(brief, evidence, fetch):
    if hashlib.sha256(brief.read_bytes()).hexdigest() != evidence["brief_sha256"]:
        raise ValueError("Subject brief changed; repeat the comparison against the new brief")
    as_of = date.fromisoformat(evidence["as_of"])
    earliest = as_of.replace(year=as_of.year - 3, day=min(as_of.day, calendar.monthrange(as_of.year - 3, as_of.month)[1]))
    target = evidence["index_month"]
    if date.fromisoformat(target + "-01") > as_of:
        raise ValueError("Index date follows the valuation date")
    rates = {}
    def rate(month):
        if month not in rates:
            url = "https://landregistry.data.gov.uk/data/ukhpi/region/{}/month/{}.json".format(quote(evidence["region"], safe=""), month)
            value = float(fetch(url)["result"]["primaryTopic"][evidence["index_field"]])
            if value <= 0:
                raise ValueError("Invalid index observation")
            rates[month] = value, url
        return rates[month]
    latest, url = rate(target)
    rows = []
    seen = set()
    for sale in evidence["sales"]:
        when = date.fromisoformat(sale["date"])
        identity = (sale["address"], when)
        if identity in seen or not earliest <= when <= as_of or sale["date"][:7] > target:
            raise ValueError("Check the comparable date or duplicate address and date")
        seen.add(identity)
        if sale["price"] <= 0 or not all(sale[k] for k in ("source","condition","role")):
            raise ValueError("Complete the sale evidence before reconciliation")
        before, source = rate(sale["date"][:7])
        rows.append(dict(sale, sale_index=before, target_index=latest, sale_index_source=source,
                         target_index_source=url, adjusted_gbp=round(sale["price"] * latest / before)))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("brief","evidence","output"):
        p.add_argument(name, type=Path)
    args = p.parse_args()
    def fetch(url):
        with urlopen(url, timeout=25) as response:
            return json.load(response)
    rows = evaluate(args.brief, json.loads(args.evidence.read_text(encoding="utf-8")), fetch)
    if not rows:
        raise ValueError("No comparable sales")
    with args.output.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
