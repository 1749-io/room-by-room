"""Lay out the reviewed edition copy once for editable slides and print."""
import io
import zipfile

import fitz

from tools.render_pack import pdf_bytes

INK, GREEN, MUTED, PAPER = "19352E", "30624F", "465D55", "FBF9F3"
BASE_FONTS = {"body": "helv", "heading": "tiro", "label": "hebo"}
FONTS = {key: fitz.Font(fontname=value) for key, value in BASE_FONTS.items()}
SIZES = {"homeowner-presentation": (864, 486), "architect-pack": (595, 842), "buyer-brief": (595, 842)}


def lines(value, width, size, face):
    # Leave a small metric allowance for replacement fonts on an office reader's computer.
    result = []
    for paragraph in value.splitlines():
        current = ""
        for word in paragraph.split():
            trial = (current + " " + word).strip()
            if FONTS[face].text_length(trial, fontsize=size) > width * .96:
                if not current or FONTS[face].text_length(word, fontsize=size) > width * .96:
                    raise ValueError(f"Word will not fit the issue layout: {word}")
                result.append(current)
                current = word
            else:
                current = trial
        result.append(current)
    return result


def layout(spec, item, number):
    w, h = SIZES[spec["slug"]]
    wide = w > h
    blocks = []
    def block(value, x, top, width, size, face="body", colour=INK):
        rows = lines(value, width, size, face)
        block_height = len(rows) * size * 1.30
        blocks.append((rows, x, top, width, size, face, colour))
        return top + block_height
    title = spec["slug"].replace("-", " ").capitalize()
    top = block(title.upper() + "   /   " + spec["issue"], 34, 21, w-68, 10, "label", GREEN)
    top = block(item["title"], 34, top+11, w-68, 31 if wide else 30, "heading") + 18
    footer_y = h-45
    if block(f"{spec['house_name']}   /   {spec['audience']}   /   {number:02}",
             34, footer_y+11, w-68, 10, colour=MUTED) > h-6:
        raise ValueError("House and audience names exceed the edition footer")
    visual = item["visual"]
    width = (w * .40 - 40) if wide and visual else w-68
    body_top = top
    for entry in item["notes"]:
        top = block(entry["label"], 34, top, width, 16 if wide else 15, "label", GREEN)
        top = block(entry["text"], 34, top+3, width, 15 if wide else 13) + 4
        top = block(entry["basis"], 34, top, width, 10, colour=MUTED) + (17 if wide else 20)
    image = None
    if visual:
        x = int(w*.41) if wide else 34
        vwidth = w-34-x
        caption_h = len(lines(visual["caption"], vwidth, 11, "body")) * 14.3
        caption_y = footer_y-caption_h-13
        block(visual["caption"], x, caption_y, vwidth, 11, colour=MUTED)
        image_y = body_top if wide else top+4
        image = fitz.Rect(x, image_y, w-34, caption_y-9)
        if image.height < (100 if wide else 160):
            raise OverflowError
    if top > footer_y-6:
        raise OverflowError
    return blocks, image


def paginate(spec):
    output = []
    for original in spec["pages"]:
        pending = []
        page = dict(original)
        for entry in original["notes"]:
            page["notes"] = [*pending, entry]
            try:
                layout(spec, page, len(output)+1)
            except OverflowError:
                if not pending:
                    raise ValueError(f"Split the long entry '{entry['label']}' in {original['title']}") from None
                output.append(dict(page, notes=pending))
                page = dict(original, notes=[entry], title=original["title"] + " (continued)")
                try:
                    layout(spec, page, len(output)+1)
                except OverflowError:
                    raise ValueError(f"Split the long entry '{entry['label']}' in {original['title']}") from None
                pending = []
            pending.append(entry)
        output.append(dict(page, notes=pending))
    return output


def rgb(value):
    return tuple(int(value[i:i+2], 16)/255 for i in (0, 2, 4))


def draw_visual(page, box, source, number):
    """Preserve the vector sheet in print and embed an offline picture in its slide."""
    if source.suffix.lower() == ".pdf":
        with fitz.open(source) as doc:
            if not 1 <= number <= len(doc):
                raise ValueError(f"Missing page {number} of {source.name}")
            page.show_pdf_page(box, doc, number-1)
            return doc[number-1].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
    data = source.read_bytes()
    page.insert_image(box, stream=data)
    return fitz.Pixmap(data).tobytes("png")


def slide_text(slide, blocks):
    from pptx.dml.color import RGBColor
    from pptx.util import Pt
    for rows, x, y, width, size, face, colour in blocks:
        height = len(rows)*size*1.3+3
        box = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(width), Pt(height))
        frame = box.text_frame
        frame.word_wrap = False
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = Pt(0)
        frame.text = "\v".join(rows)
        para = frame.paragraphs[0]
        para.line_spacing = Pt(size*1.3)
        para.space_before = para.space_after = Pt(0)
        for run in para.runs:
            run.font.name = "Times New Roman" if face == "heading" else "Arial"
            run.font.bold = face == "label"
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor.from_string(colour)


def stable_deck(deck, thumbnail):
    stream = io.BytesIO()
    deck.save(stream)
    out = io.BytesIO()
    with zipfile.ZipFile(stream) as source, zipfile.ZipFile(out, "w") as target:
        for name in sorted(source.namelist()):
            entry = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            data = thumbnail if name == "docProps/thumbnail.jpeg" else source.read(name)
            target.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()


def render(root, spec, assets):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Pt
    w, h = SIZES[spec["slug"]]
    deck = Presentation() if spec["slug"] == "homeowner-presentation" else None
    if deck is not None:
        deck.slide_width, deck.slide_height = Pt(w), Pt(h)
        deck.core_properties.title = spec["house_name"] + " | Homeowner presentation"
        deck.core_properties.author = spec["house_name"]
        deck.core_properties.last_modified_by = spec["house_name"]
        deck.core_properties.subject = spec["purpose"]
    pdf = root / spec["pdf"]
    with fitz.open() as doc:
        for n, item in enumerate(spec["pages"], 1):
            blocks, box = layout(spec, item, n)
            page = doc.new_page(width=w, height=h)
            page.draw_rect(page.rect, color=None, fill=rgb(PAPER))
            page.draw_line((34, h-45), (w-34, h-45), color=rgb("A3B1A4"), width=.7)
            for rows, x, y, _, size, face, colour in blocks:
                fontname = BASE_FONTS[face]
                # Standard PDF fonts cover the Western text used in the public fixtures.
                # Preserve the embedded font path for text outside that character set.
                if any(ord(char) > 255 for row in rows for char in row):
                    page.insert_font(fontname=face, fontbuffer=FONTS[face].buffer)
                    fontname = face
                for offset, row in enumerate(rows):
                    page.insert_text((x, y+size+offset*size*1.3), row, fontsize=size,
                                     fontname=fontname, color=rgb(colour))
            slide = None
            if deck is not None:
                slide = deck.slides.add_slide(deck.slide_layouts[6])
                slide.background.fill.solid()
                slide.background.fill.fore_color.rgb = RGBColor.from_string(PAPER)
                slide_text(slide, blocks)
            if box is not None:
                visual = item["visual"]
                image = draw_visual(page, box, assets[visual["key"]], visual["page"])
                if slide is not None:
                    pix = fitz.Pixmap(image)
                    factor = min(box.width/pix.width, box.height/pix.height)
                    width, height = pix.width*factor, pix.height*factor
                    slide.shapes.add_picture(io.BytesIO(image), Pt(box.x0+(box.width-width)/2),
                                             Pt(box.y0+(box.height-height)/2), Pt(width), Pt(height))
        for drawing in spec["drawings"]:
            with fitz.open(pdf.parent / drawing["File"]) as sheet:
                if len(sheet) != 1:
                    raise ValueError("Expected a single issued sheet in the drawing register")
                doc.insert_pdf(sheet)
        pdf.write_bytes(pdf_bytes(doc))
        if deck is not None:
            cover = doc[0].get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
            pdf.with_suffix(".pptx").write_bytes(stable_deck(deck, cover.tobytes("jpeg")))


def verify(root, spec, assets):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    pdf = root / spec["pdf"]
    deck = Presentation(pdf.with_suffix(".pptx")) if spec["slug"] == "homeowner-presentation" else None
    if deck is not None and len(deck.slides) != len(spec["pages"]):
        raise ValueError("PowerPoint slide count differs from the approved presentation")
    with fitz.open(pdf) as doc:
        if len(doc) != len(spec["pages"]) + len(spec["drawings"]):
            raise ValueError("Missing pages in the reader PDF")
        for n, item in enumerate(spec["pages"], 1):
            page = doc[n-1]
            blocks, box = layout(spec, item, n)
            text = " ".join(page.get_text().split())
            expected = [" ".join(" ".join(rows).split()) for rows, *_ in blocks]
            if any(chunk not in text for chunk in expected):
                raise ValueError(f"Approved text is missing from {pdf.name}, page {n}")
            if box:
                visual = item["visual"]
                with fitz.open() as proof:
                    reference = proof.new_page(width=page.rect.width, height=page.rect.height)
                    reference.draw_rect(reference.rect, color=None, fill=rgb(PAPER))
                    image = draw_visual(reference, box, assets[visual["key"]], visual["page"])
                    if reference.get_pixmap(clip=box).digest != page.get_pixmap(clip=box).digest:
                        raise ValueError(f"Printed illustration differs from reviewed source on page {n}")
            if deck is not None:
                slide = deck.slides[n-1]
                actual = [" ".join(s.text.split()) for s in slide.shapes if s.has_text_frame]
                pictures = [s.image.blob for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
                if actual != expected or pictures != ([image] if box else []):
                    raise ValueError(f"Editable content or reviewed picture differs on slide {n}")
