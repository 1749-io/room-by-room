"""Render the full house workflow and its quick reference from their editable sources."""
import argparse
import base64
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from textwrap import wrap
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WIDTH = 1060
MARGIN = 48
CONTENT = WIDTH - 2 * MARGIN
INK, MUTED = "#183735", "#3F5E59"
PAPER, GREEN, AMBER, RUST = "#FAF8F2", "#165D52", "#8A591B", "#873E30"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Arial, Helvetica, sans-serif"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)


def element(parent, tag, **attrs):
    return ET.SubElement(parent, "{%s}%s" % (SVG, tag), {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def text(parent, x, y, value, size=16, colour=INK, family=SANS, weight="normal", **attrs):
    node = element(parent, "text", x=x, y=y, fill=colour, font_size=size,
                   font_family=family, font_weight=weight, **attrs)
    node.text = value
    return node


def box(parent, x, y, width, height, colour, radius=0, **attrs):
    return element(parent, "rect", x=x, y=y, width=width, height=height,
                   fill=colour, rx=radius, **attrs)


def line(parent, x1, y1, x2, y2, colour, weight=1):
    element(parent, "line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=colour, stroke_width=weight)


def lines(value, width, size):
    # Keep a little breathing room for font substitution in GitHub and native SVG viewers.
    return wrap(value, width=int(width / (size * .55)), break_long_words=False, break_on_hyphens=False)


def paragraph(parent, x, y, words, size=16, colour=INK, leading=22):
    for value in words:
        text(parent, x, y, value, size, colour)
        y += leading
    return y


def report_rows(markdown):
    for row in markdown.splitlines():
        if row.startswith("| "):
            yield [field.strip() for field in row.strip("|").split("|")]


def gate_sections():
    sections = []
    for section in re.split(r"^## ", (HERE / "workflow-decisions.md").read_text(encoding="utf-8"), flags=re.M)[1:]:
        pieces = re.split(r"^### ", section, flags=re.M)
        gates = []
        for part in pieces[1:]:
            heading, body = part.split("\n", 1)
            fields = dict(report_rows(body))
            gates.append((heading, fields))
        sections.append((pieces[0].strip(), gates))
    return sections


def specialist_rows():
    source = ROOT / "skills/renovation-pack/references/specialist-design-tools.md"
    body = source.read_text(encoding="utf-8").split("## Requests that trigger a specialist study\n", 1)[1]
    return list(report_rows(body.split("\n## ", 1)[0]))[2:]


def map_image(source="workflow.dot"):
    dot = shutil.which("dot")
    if not dot and os.name == "nt":
        dot = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Graphviz/bin/dot.exe"
    if not dot or not Path(dot).is_file():
        raise SystemExit("Install Graphviz and put dot on PATH to rebuild the workflow diagrams.")
    return subprocess.check_output([str(dot), "-Tsvg", str(HERE / source)])


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


# Graphviz node names map to the review that owns the work.
NODE_REVIEWS = {
    "intake": "Brief", "checklist": "Brief", "survey": "Existing CAD",
    "shell": "Existing CAD", "fixed": "Existing CAD", "study": "Furniture study",
    "options": "Proposed CAD", "living": "Proposed CAD", "decide": "Scope",
    "style": "Products", "finish": "Blender", "fidelity": "Products", "ai": "Final AI",
    "decor": "Decorator", "release": "Handover", "assembled": "Handover",
    "climate": "Study-glazing",
}

# Same order as the specialist request table. Match the wording as a guard
# against silently attaching a new request to the wrong review.
STUDIES = (
    ("A conservatory", "Glazing", "Proposed CAD"),
    ("“Can we open up", "Structural openings", "Opening enquiry"),
    ("“Could the sink", "Services", "Existing CAD"),
    ("“Can Dad", "Access", "Proposed CAD"),
    ("“Can everyone", "Sightlines", "Proposed CAD"),
    ("“Where can we sit", "Sun and shade", "Proposed CAD"),
    ("“Will these doors", "Thermal comfort", "Proposed CAD"),
    ("“Is there room", "Solar panels", "Whole house"),
    ("“Could this patio", "Levels and drainage", "Existing CAD"),
    ("“Can the garage", "Consent", "Consent"),
    ("“Will music", "Acoustics", "Proposed CAD"),
    ("“Make the room", "Colour", "Products"),
    ("“Show me", "Furnishing", "Blender"),
    ("“Which paint", "Finishes", "Decorator"),
    ("“Can we stay", "Occupation", "Occupied works"),
    ("“What will it be worth", "Valuation", "Whole house"),
    ("“Does this quote", "Tenders", "Whole house"),
    ("“What should we check", "Survey returns", "Brief"),
)


def link_to(parent, destination, label):
    link = element(parent, "a", aria_label=label)
    link.set("{%s}href" % XLINK, "#" + slug(destination))
    return link


def link_label(parent, x, y, label, destination):
    link = link_to(parent, destination, label)
    text(link, x, y, label, 15, GREEN, text_decoration="underline")


def tools_for_review(parent, y, fields):
    text(parent, MARGIN, y, "Tools in use", 15, GREEN, weight="bold")
    return paragraph(parent, MARGIN+122, y, lines(fields["Tools"], CONTENT-122, 16)) + 12


def destination_rail(parent, x, y, names, stages, colour):
    for index, name in enumerate(names.split(" / ")):
        if index:
            text(parent, x, y, "·", 14, colour)
            x += 10
        target = parent
        if name in stages or name == "Specialist study":
            target = element(parent, "a")
            target.set("{%s}href" % XLINK, "#"+slug(name))
        text(target, x, y, name, 13, colour, weight="bold")
        # A textLength fixes the navigation label width across font substitutions.
        label_width = len(name)*7.5
        target[-1].set("textLength", str(label_width))
        target[-1].set("lengthAdjust", "spacingAndGlyphs")
        x += label_width+6


def route_card(parent, x, y, width, height, heading, words, colour, background, destinations, stages):
    box(parent, x, y, width, height, background, 7)
    text(parent, x+16, y+23, heading, 14, colour, weight="bold")
    paragraph(parent, x+16, y+47, words, 16, INK, 22)
    line(parent, x+16, y+height-32, x+width-16, y+height-32, "#BACBC0")
    destination_rail(parent, x+16, y+height-12, destinations, stages, colour)


def gate_panel(parent, y, heading, fields, stages):
    stage, question = heading.split(" · ", 1)
    group = element(parent, "g", id=slug(stage), role="group", aria_label=heading)
    panel_top = y
    check, passed, held, ask = (fields[k] for k in ("Check", "Proceed", "Return", "Ask"))
    box(group, MARGIN, y, CONTENT, 2, "#C5D3C9")
    text(group, MARGIN, y+28, stage.upper(), 13, GREEN, weight="bold", letter_spacing=1.2)
    text(group, MARGIN, y+61, question, 25, INK, SERIF)
    y = paragraph(group, MARGIN, y+91, lines(check, CONTENT, 16))
    y = tools_for_review(group, y+8, fields)
    link_label(group, WIDTH-MARGIN-115, panel_top+26, "Back to map", "room-map")
    if stage == "Handover":
        guide = element(group, "a", aria_label="Open the separate pack delivery workflow")
        guide.set("{%s}href" % XLINK, "pack-delivery.svg")
        text(guide, WIDTH-MARGIN-330, panel_top+26, "Pack delivery workflow", 15, GREEN, text_decoration="underline")
    half = (CONTENT-20)/2
    left, right = lines(passed, half-32, 16), lines(held, half-32, 16)
    h = 78 + max(len(left), len(right))*22
    mid = WIDTH/2
    # A real fork at each gate. The two destinations remain readable without colour.
    element(group, "path", d=f"M {mid} {y+2} l 6 6 -6 6 -6 -6 Z", fill=AMBER)
    for x in (MARGIN+half/2, WIDTH-MARGIN-half/2):
        element(group, "path", d=f"M {mid} {y+14} V {y+19} H {x} V {y+28}",
                fill="none", stroke="#64817A", stroke_width=1.4)
        element(group, "path", d=f"M {x-3} {y+25} l 3 5 3 -5", fill="none", stroke="#64817A")
    y += 31
    route_card(group, MARGIN, y, half, h, "Proceed", left, GREEN, "#E5EFE7",
               fields["Next review or output"], stages)
    route_card(group, MARGIN+half+20, y, half, h, "Hold, correct and return", right, RUST, "#F5E9E1",
               fields["Return destinations"], stages)
    y += h + 20
    text(group, MARGIN, y+13, "Who decides", 14, AMBER, weight="bold")
    words = lines(ask, CONTENT-132, 16)
    y = paragraph(group, MARGIN+132, y+14, words)
    return y+22


def section_heading(parent, y, heading, anchor=None):
    group = element(parent, "g", id=anchor or slug(heading))
    box(group, 0, y, WIDTH, 66, "#203F3D")
    text(group, MARGIN, y+43, heading, 29, "#FFFFFF", SERIF)
    return y+88


def routing_guide(parent, y):
    y = section_heading(parent, y, "What calls for a specialist?", "specialist-study")
    y = paragraph(parent, MARGIN, y+3, lines(
        "Screen new instructions, follow-ups and findings from other rooms. Use the study if its answer could "
        "change the decision. Check permissions, run linked studies where needed, then return to the affected review.",
        CONTENT, 17), 17, leading=24) + 16
    widths = (278, 390, CONTENT-278-390)
    columns = (MARGIN, MARGIN+widths[0], MARGIN+widths[0]+widths[1])
    box(parent, MARGIN, y, CONTENT, 38, "#DCE7DF")
    for x, title in zip(columns, ("Household request or clue", "Specialist response", "Return to the decision")):
        text(parent, x+12, y+25, title, 15, GREEN, weight="bold")
    y += 38
    rows = specialist_rows()
    if len(rows) != len(STUDIES):
        raise ValueError("Map each specialist request to its return review.")
    for index, (row, (prefix, name, review)) in enumerate(zip(rows, STUDIES)):
        if not row[0].startswith(prefix):
            raise ValueError(f"Check the specialist mapping for {name}")
        row = [re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", cell) for cell in row]
        group = element(parent, "g", id=slug("study-" + name))
        cells = [lines(value, width-24, 15) for value, width in zip(row, widths)]
        h = 24+max(map(len, cells))*21
        box(group, MARGIN, y, CONTENT, h+28, "#FFFFFF" if index % 2 == 0 else "#F0F3EB")
        for x, words in zip(columns, cells):
            paragraph(group, x+12, y+24, words, 15, INK, 21)
        link_label(group, columns[2]+12, y+h+6, "Open " + review + " review", review)
        link_label(group, MARGIN+12, y+h+6, "Back to map", "room-map")
        y += h+28
    return y+32


def evidence_figure(parent, y, path, title, caption):
    # Embed the tracked evidence so the standalone diagram works offline.
    box(parent, MARGIN, y, CONTENT, 64, "#E4ECE5", 6)
    text(parent, MARGIN+16, y+26, title, 19, GREEN, weight="bold")
    text(parent, MARGIN+16, y+49, caption, 16)
    png = (ROOT / path).read_bytes()
    w, h = struct.unpack(">II", png[16:24])
    height = round(CONTENT*h/w)
    img = element(parent, "image", x=MARGIN, y=y+70, width=CONTENT, height=height)
    img.set("{%s}href" % XLINK, "data:image/png;base64,"+base64.b64encode(png).decode("ascii"))
    element(img, "title").text = title
    return y+height+94


def specialist_loop(parent, y):
    y = section_heading(parent, y, "Route a new question from any stage")
    words = lines("Read the request alongside the brief and current findings. An ordinary phrase, a changed product "
                  "or a measurement from site can introduce a specialist question.", CONTENT, 17)
    y = paragraph(parent, MARGIN, y+3, words, 17, leading=24)+14
    labels = (
        ("What could change?", "Identify the decision, the evidence already available and the affected rooms."),
        ("Who can answer?", "Choose the relevant skill, study or professional. Check scope and evidence."),
        ("What comes back?", "Record the finding or deciding unknown. Reopen affected reviews and orders."),
    )
    width = (CONTENT-88)/3
    for index, (heading, summary) in enumerate(labels):
        x = MARGIN + index*(width+44)
        box(parent, x, y, width, 118, "#E5EFE7", 8, stroke="#A1B7A8")
        text(parent, x+15, y+29, heading, 19, GREEN, SERIF, "bold")
        paragraph(parent, x+15, y+55, lines(summary, width-30, 15), 15, leading=19)
        if index < 2:
            end = x+width+38
            line(parent, x+width+4, y+59, end, y+59, GREEN, 2)
            element(parent, "path", d=f"M {end-7} {y+54} l 7 5 -7 5", fill="none", stroke=GREEN, stroke_width=2)
    start, end = WIDTH-MARGIN-width/2, MARGIN+width/2
    element(parent, "path", d=f"M {start} {y+118} v 24 H {end} v -19",
            fill="none", stroke=RUST, stroke_width=1.6)
    element(parent, "path", d=f"M {end-4} {y+130} l 4 -7 4 7", fill="none", stroke=RUST, stroke_width=1.6)
    text(parent, WIDTH/2, y+166, "Changed assumption or unresolved fit? Return to the affected decision and retest.",
         15, RUST, text_anchor="middle")
    return y+192


def finish_svg(result, background, y):
    background.set("height", str(y))
    result.set("height", str(y))
    result.set("viewBox", f"0 0 {WIDTH} {y}")
    ET.indent(result, space="  ")
    return ET.tostring(result, encoding="utf-8", xml_declaration=True)+b"\n"


def render(raw_map, detailed, preview=False):
    title = "House renovation workflow" if detailed else "Room design at a glance"
    result = ET.Element("{%s}svg" % SVG, {"width":str(WIDTH), "role":"document", "aria-labelledby":"title description"})
    element(result, "title", id="title").text = title
    element(result, "desc", id="description").text = (
        "Room design decisions with correction loops. The full guide includes each stage, homeowner questions, "
        "specialist triggers, scoped issues and a worked support-beam example." if detailed else
        "A quick reference for the renovation-pack, FreeCAD and Blender skills, including the return paths at three reviews.")
    element(result, "style").text = (
        "a { cursor: pointer } a:focus, a:hover { outline: 2px solid #165D52 } "
        "a:hover .node text, a:focus .node text { text-decoration: underline }"
    )
    background = box(result, 0, 0, WIDTH, 1, PAPER)
    box(result, 0, 0, WIDTH, 131, "#173D39")
    text(result, MARGIN, 34, "HOUSE RENOVATIONS", 13, "#C7DFCE", weight="bold", letter_spacing=2.6)
    text(result, MARGIN, 86, title, 43, "#FFFFFF", SERIF)
    text(result, MARGIN, 113, "Review gates, return paths and homeowner decisions" if detailed else
         "From the brief to a checked plan, furnished camera and issued room", 18, "#DEEBE3")
    text(result, MARGIN, 163, "Every output", 16, GREEN, weight="bold")
    text(result, MARGIN+127, 163, "Begin a private revision, check the actual work and save it. Publication follows verified backup.", 16)
    text(result, MARGIN, 190, "On resuming", 16, GREEN, weight="bold")
    text(result, MARGIN+127, 190, "Open CHECKLIST.md with the history and reviews. Check outstanding surveys and design holds.", 16)
    line(result, MARGIN, 208, WIDTH-MARGIN, 208, "#BCCAC0")
    key = element(result, "g", role="group", aria_label="Diagram key")
    text(key, MARGIN, 232, "Diagram key", 15, GREEN, weight="bold")
    box(key, 176, 220, 21, 14, "#E8F1ED", 4, stroke="#73938D")
    text(key, 206, 232, "Task or record", 14)
    element(key, "polygon", points="354,219 367,227 354,235 341,227", fill="#F8E9C4", stroke="#AB854A")
    text(key, 376, 232, "Decision or study", 14)
    for x, dashed, label in ((537, False, "Next step or return"), (766, True, "Conditional route")):
        attrs = {"stroke_dasharray": "5 3"} if dashed else {}
        element(key, "line", x1=x, x2=x+30, y1=227, y2=227, stroke="#507470", stroke_width=1.5, **attrs)
        element(key, "polygon", points=f"{x+30},224 {x+36},227 {x+30},230", fill="#507470")
        text(key, x+43, 232, label, 14)
    map_top = 252
    if not preview:
        menu = element(result, "g", id="room-map", aria_label="Workflow navigation")
        text(menu, MARGIN, 266, "Select a task or diamond to see its tools and review.", 17, GREEN, weight="bold")
        for x, label, destination in (
            (48, "All reviews", "review-index"), (170, "Specialist studies", "specialist-study"),
            (332, "Beam analysis", "Study-Structural openings"), (474, "Costs and works", "Whole house"),
        ):
            link_label(menu, x, 294, label, destination)
        map_top = 315
    graph = ET.fromstring(raw_map)
    layout = graph.find("{%s}g" % SVG)
    for node in list(layout):
        if not preview and node.get("class") == "node":
            key = node.findtext("{%s}title" % SVG)
            stage = NODE_REVIEWS[key]
            link = link_to(layout, stage, key + " tools: " + stage)
            layout.remove(node)
            link.append(node)
    _, _, w, h = map(float, graph.get("viewBox").split())
    map_height = round((WIDTH-48)*h/w)
    scale = (WIDTH-48)/w
    map_group = element(result, "g", transform=f"translate(24 {map_top}) scale({scale:.8f})")
    map_group.append(graph.find("{%s}g" % SVG))
    y = map_top+map_height+20
    if preview:
        return finish_svg(result, background, y)
    for label, body in (
        ("Assessment", "Issue a finding and next site check when the evidence answers the buyer’s question."),
        ("CAD only", "Issue the checked plan or measured hold after occupied review. Later visual stages stay pending or held."),
        ("Whole house", "Reopen linked rooms, orders, costs and phases when a shared decision changes.")):
        text(result, MARGIN, y, label, 15, GREEN, weight="bold")
        text(result, MARGIN+130, y, body, 15)
        y += 25
    y += 10
    sections = gate_sections()
    stages = {gate.split(" · ", 1)[0] for _, gates in sections for gate, _ in gates}
    y = section_heading(result, y, "Find a review or specialist study", "review-index")
    entries = [(gate.split(" · ", 1)[0], gate.split(" · ", 1)[0]) for _, gates in sections for gate, _ in gates]
    for label, items in (("Reviews", entries), ("Specialist studies", [(name, "study-" + name) for _, name, _ in STUDIES])):
        text(result, MARGIN, y, label, 17, GREEN, weight="bold")
        y += 26
        for index, (name, destination) in enumerate(items):
            link_label(result, MARGIN+(index % 4)*238, y+(index//4)*26, name, destination)
        y += ((len(items)+3)//4)*26+20
    if detailed:
        y = specialist_loop(result, y)
    for heading, gates in sections:
        if heading.startswith("Worked example"):
            y = routing_guide(result, y)
        y = section_heading(result, y, heading)
        for gate, fields in gates:
            if detailed:
                y = gate_panel(result, y, gate, fields, stages)
            else:
                stage = gate.split(" · ", 1)[0]
                group = element(result, "g", id=slug(stage))
                text(group, MARGIN, y, stage, 20, GREEN, weight="bold")
                link_label(group, WIDTH-MARGIN-115, y, "Back to map", "room-map")
                y = tools_for_review(group, y+29, fields)+18
    if detailed:
        y = evidence_figure(result, y, "examples/whole-house-changes/reference/occupied-plan.png",
                            "Orchard House · The occupied return path",
                            "Fictional pier return. Follow the serving route past eight diners as the kitchen changes.")
        y = evidence_figure(result, y, "examples/structural-opening/reference/solver-comparison.png",
                            "Fictional beam benchmark",
                            "Recorded hand check, PyNite result and reopened FreeCAD FEM result for the assumed member.")
    return finish_svg(result, background, y)


# Short labels for GitHub's diagrams. The evidence and return instructions below
# each diagram come from the same specialist guide used by the interactive SVG.
SPECIALIST_FLOWS = {
    "Glazing": ("Glazed room enters review", "QGIS or LiDAR for obstructions", "Sun Position or pvlib for exposure", "EnergyPlus if thermal inputs support it", "Review seat, shade and ventilation"),
    "Structural openings": ("Wall, opening or post changes", "FreeCAD BIM and TechDraw section", "Engineer verifies loads, bearings and supports", "Return finished supports to occupied CAD"),
    "Services": ("Fitting, duct or drain moves", "FreeCAD section and supplied IFC via IfcOpenShell", "Installer verifies connection and fall", "Update fit and order hold"),
    "Access": ("Doorway, furniture or mobility aid changes", "Read occupied geometry in FreeCAD", "Shapely and NetworkX test the journey", "Retest the pinch and adjoining room"),
    "Sightlines": ("Seat, target or privacy changes", "FreeCAD tests every intended viewpoint", "Compare permitted Blender views", "Recheck seating and passage"),
    "Sun and shade": ("Hedge, roof or garden seat changes", "Register north and heights in QGIS", "Blender Sun Position or pvlib", "Compare seasonal shade at the seat"),
    "Thermal comfort": ("Glazing, fabric or ventilation changes", "Establish fabric, weather and occupancy", "Compare cases in EnergyPlus", "Revisit shading and ventilation"),
    "Solar panels": ("Rooflight or panel layout changes", "Measure roof area, aspect and shade", "Compare module fit and pvlib yield", "Update roof choice and budget"),
    "Levels and drainage": ("Threshold, patio or outfall changes", "Survey levels to one datum", "Trace the fall and verify the outfall", "Recheck threshold section and access"),
    "Consent": ("Footprint, use or frontage changes", "Renovation Pack identifies jurisdiction", "Check authority records against the drawing", "Record decision and affected work"),
    "Acoustics": ("Noise source, partition or use changes", "Trace direct and flanking sound paths", "Listening trial or acoustic advice", "Revisit door, fabric and ventilation"),
    "Colour": ("Paint, upholstery or lighting changes", "Compare fixed products in Blender", "Colour Expert for an open choice", "Record palette and recheck finishes"),
    "Furnishing": ("Camera or selected product changes", "Blender checks variants, counts and fit", "Image editor uses reviewed camera", "Compare photo and return discrepancies"),
    "Finishes": ("Shade, sheen or sample changes", "Reconcile surface schedule and sample", "Run house.py check-decorator", "Issue approved surfaces"),
    "Occupation": ("Isolation, trade or delivery changes", "Map access and essential facilities", "Phase table or commissioned OpenProject schedule", "Recheck each occupied night"),
    "Valuation": ("Freeze unpriced subject description", "Measure existing and proposed areas", "Research sold comparables and condition", "Call local UK HPI and reconcile range"),
    "Tenders": ("Quote, exclusion or substitution arrives", "Compare quantities and terms on common scope", "Reopen affected fit and product reviews", "Update procurement and budget"),
    "Survey returns": ("New evidence contradicts the issue", "Renovation Pack traces affected decisions", "Surveyor, installer or authority resolves unknown", "Recheck affected rooms and orders"),
}


def specialist_diagrams():
    groups = {
        "Building and site": ("Structural openings", "Services", "Levels and drainage", "Consent"),
        "Sun, glazing and energy": ("Glazing", "Sun and shade", "Thermal comfort", "Solar panels"),
        "People, rooms and finishes": ("Access", "Sightlines", "Acoustics", "Colour", "Furnishing", "Finishes"),
        "Buying and building": ("Valuation", "Tenders", "Occupation", "Survey returns"),
    }
    rows = specialist_rows()
    if len(rows) != len(STUDIES):
        raise ValueError("Every specialist request needs a workflow diagram.")
    by_name = {name: row for (_, name, _), row in zip(STUDIES, rows)}
    grouped = [name for names in groups.values() for name in names]
    if len(grouped) != len(set(grouped)) or set(grouped) != set(by_name) or set(grouped) != set(SPECIALIST_FLOWS):
        raise ValueError("Specialist diagrams and request table must cover the same studies.")
    out = ["# Specialist workflow diagrams", "",
           "Start with the change that prompted the question. Follow the arrows to see which evidence or tool enters the study and which decision to revisit. A single change can trigger several studies.", "",
           "Run the study when its answer could change the design. If a deciding measurement, permission or specialist input is missing, record its owner and return to the affected review when it arrives.", "",
           "## Choose a study", ""]
    for group, names in groups.items():
        links = " · ".join(f"[{name}](#{slug(name)})" for name in names)
        out.extend([f"**{group}**", "", links, ""])
    for name in grouped:
        trigger, response, result = by_name[name]
        response = response.replace("(valuation.md)", "(../skills/renovation-pack/references/valuation.md)")
        result = result.replace("(glazed-rooms.md)", "(../skills/renovation-pack/references/glazed-rooms.md)")
        out.extend([f"## {name}", "", trigger, "", "```mermaid", "flowchart TD"])
        for i, caption in enumerate(SPECIALIST_FLOWS[name]):
            out.append(f'    step{i}["{caption}"]')
            if i:
                out.append(f"    step{i-1} --> step{i}")
        if name == "Structural openings":
            out.extend(['    step2 -->|Commissioned analysis with verified inputs| frame["PyNite beam or frame model"]',
                        '    step2 -->|Solid analysis required| solid["FreeCAD FEM with CalculiX"]',
                        '    frame --> review["Engineer interprets results"]', '    solid --> review', '    review --> step3',
                        '    step3 --> fit["Retest kitchen routes, cabinets, tender and sequence"]'])
        out.extend(["```", "", response, "", result, ""])
        if name == "Structural openings":
            out.extend(["[Open the worked two-solver beam example](../examples/structural-opening/README.md)", ""])
        out.extend(["[Back to study list](#choose-a-study)", ""])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    args.output_dir.mkdir(exist_ok=True, parents=True)
    (args.output_dir / "pack-delivery.svg").write_bytes(map_image("pack-delivery.dot"))
    (args.output_dir / "specialist-workflows.md").write_text(specialist_diagrams(), encoding="utf-8")
    raw_map = map_image()
    for name, detailed in (("workflow.svg", True), ("workflow-quick.svg", False)):
        data = render(raw_map, detailed)
        (args.output_dir / name).write_bytes(data)
    (args.output_dir / "workflow-preview.svg").write_bytes(render(raw_map, False, preview=True))


if __name__ == "__main__":
    main()
