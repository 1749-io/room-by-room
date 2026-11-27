"""Add only named, reviewed public study files to a newly built Pages tree."""
import csv
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
REF = ROOT / "reference"


def survey_plan(survey, samples):
    def xy(x,y):
        return 214+24*x, 140-24*y
    def circle(x,y,r,fill):
        a,b=xy(x,y)
        return f'<circle cx="{a}" cy="{b}" r="{r*24}" fill="{fill}"/>'
    parts=['<svg class="chart" viewBox="0 0 460 400" role="img" aria-label="Fictional site plan with two tree crowns and two sun directions">',
           '<rect x="214" y="53.6" width="129.6" height="86.4" fill="#fff9e8" stroke="#3d5245"/>',
           '<text x="225" y="76">Garden room</text><text x="404" y="40">↑ N</text>']
    for tree in survey["trees"]:
        parts.append(circle(tree["east"],tree["north"],tree["radius"],"#a4b691"))
        parts.append(circle(tree["east"],tree["north"],.14,"#435b41"))
    seat=survey["seat_eye_m"][:2]
    a,b=xy(*seat)
    for hour,row in samples.items():
        az=math.radians(float(row["sun_azimuth_deg"]))
        x,y=xy(seat[0]+8*math.sin(az),seat[1]+8*math.cos(az))
        parts.append(f'<path d="M{a} {b} L{x} {y}" stroke="#a65a2d" stroke-width="2.5" stroke-dasharray="6 3"/>')
        parts.append(f'<text x="{x-13}" y="{y+18}">{hour}</text>')
    parts.append(circle(*seat,.16,"#8e3f27"))
    parts.append('<text x="301" y="100">Seat</text><text x="27" y="278">Field maple · 8.5 m</text><text x="265" y="365">Apple · 5.3 m</text></svg>')
    return "".join(parts)


def build(stage):
    data=json.loads((REF/"results.json").read_text())
    survey=json.loads((ROOT/"survey.json").read_text(encoding="utf-8-sig"))
    with (REF/"hourly.csv").open() as stream:
        samples={r["local_time"][11:16]:r for r in csv.DictReader(stream)
                 if r["local_time"].startswith(("2019-06-21 12:30","2019-06-21 16:30"))}
    assert len(samples)==2 and float(samples["16:30"]["seat_beam_transmission"])==.18
    labels={"Original":"Existing glass roof","External screens":"Add external screens only",
            "Cross ventilation":"Improve ventilation only","Roof and glazing":"Replace roof and upgrade glazing",
            "Combined":"Combine fabric, screens and vents","All-season design":"Add timed heating and cooling"}
    rows=[]
    for key,label in labels.items():
        case=data[key]
        rows.append(f'<tr><td>{label}</td><td>{case["hot_hours"]:,}</td><td>{case["cold_hours"]:,}</td></tr>')
    final=data["All-season design"]
    seasons="".join(f'<tr><td>{s}</td><td>{data["Original"]["in_band_pct"][s]:.1f}%</td>'
                    f'<td>{pct:.1f}%</td></tr>' for s,pct in final["in_band_pct"].items())
    page=(ROOT/"page.html").read_text(encoding="utf-8-sig")
    for key,value in {"survey":survey_plan(survey,samples),"rows":"".join(rows),"seasons":seasons,
                      "cold":str(data["Combined"]["cold_hours"]),"heat":f'{final["heating_kWh"]:,}'}.items():
        page=page.replace("{{"+key+"}}",value)
    tree=stage/"orchard"
    tree.mkdir()
    for name in ("camera.png","concept.png","results.json","hourly.csv","walkthrough-v3.mp4","walkthrough-v3.vtt"):
        shutil.copyfile(REF/name,tree/name)
    for name in ("_worker.js", "_routes.json"):
        shutil.copyfile(ROOT / name, stage / name)
    shutil.copyfile(ROOT/"survey.json",tree/"survey.json")
    shutil.copyfile(ROOT/"README.md",tree/"method.txt")
    models=stage/"examples"/"conservatory"/"reference"
    models.mkdir(parents=True)
    for name in ("Orchard-Fold.blend","Orchard-Fold.FCStd"):
        shutil.copyfile(REF/name,models/name)
    (stage/"index.html").rename(stage/"library.html")
    (stage/"index.html").write_text(page,encoding="utf-8")
