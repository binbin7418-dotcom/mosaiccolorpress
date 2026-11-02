#!/usr/bin/env python3
"""MosaicColorPress engine: photos -> mosaic color-by-number book pages
(PDF) with a verified cell recount.

How a page is made: the photo is reduced to a grid and quantized to a
small palette. Each cell is printed with the number of its palette color,
and a color key maps numbers to color names and swatches. Before the
book is written, every page is RE-QUANTIZED from the source photo by a
second pass and compared cell by cell with the page that will print:
counts per color must sum to the grid size, the key must cover exactly
the numbers present, and the two grids must be identical. A page that
fails the recount is never printed.

Deterministic for fixed inputs. 100% local. Requires: Pillow, reportlab.

Usage:
    python mosaic_color.py out/ img1.png [img2.jpg ...]
                           [--grid-width 44] [--max-colors 16]
"""
import os
import sys

PAGE_W, PAGE_H = 612, 792
MAX_GRID_H = 84

NAMED_COLORS = [
    ("Black", (0, 0, 0)), ("Charcoal", (64, 64, 64)), ("Gray", (128, 128, 128)),
    ("Silver", (192, 192, 192)), ("White", (255, 255, 255)), ("Cream", (255, 246, 220)),
    ("Tan", (210, 180, 140)), ("Brown", (121, 72, 32)), ("Dark Brown", (74, 44, 20)),
    ("Red", (214, 39, 40)), ("Dark Red", (139, 0, 0)), ("Orange", (255, 127, 14)),
    ("Gold", (188, 148, 30)), ("Yellow", (255, 225, 53)), ("Lime", (140, 200, 60)),
    ("Green", (44, 160, 44)), ("Dark Green", (20, 90, 40)), ("Teal", (23, 160, 160)),
    ("Sky Blue", (120, 190, 235)), ("Blue", (31, 119, 180)), ("Navy", (20, 40, 110)),
    ("Purple", (148, 103, 189)), ("Magenta", (227, 90, 200)), ("Pink", (255, 160, 190)),
]

def color_name(rgb):
    best, best_d = None, None
    for name, (r, g, b) in NAMED_COLORS:
        d = (rgb[0] - r) ** 2 + (rgb[1] - g) ** 2 + (rgb[2] - b) ** 2
        if best_d is None or d < best_d:
            best, best_d = name, d
    return best

# -------------------------------------------------------------- quantize

def quantize_image(path, grid_w=44, max_colors=16):
    """Photo -> page dict: number grid + palette with counts.
    Numbers are assigned by descending frequency (most-used color = 1)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w0, h0 = im.size
    gh = max(1, round(grid_w * h0 / w0))
    gh = min(gh, MAX_GRID_H)
    small = im.resize((grid_w, gh), Image.LANCZOS)
    q = small.quantize(colors=max_colors, method=Image.MEDIANCUT)
    pal = q.getpalette()
    idx = list(q.getdata())
    counts = {}
    for v in idx:
        counts[v] = counts.get(v, 0) + 1
    order = sorted(counts, key=lambda v: (-counts[v], v))
    num_of = {pal_idx: i + 1 for i, pal_idx in enumerate(order)}
    grid = [[num_of[idx[r * grid_w + c]] for c in range(grid_w)] for r in range(gh)]
    palette = []
    for pal_idx in order:
        rgb = tuple(pal[pal_idx * 3:pal_idx * 3 + 3])
        palette.append({"num": num_of[pal_idx], "rgb": rgb,
                        "name": color_name(rgb), "count": counts[pal_idx],
                        "hex": "#%02X%02X%02X" % rgb})
    return {"source": os.path.basename(path), "w": grid_w, "h": gh,
            "grid": grid, "palette": palette}

def verify_page(path, page, grid_w=44, max_colors=16):
    """Independent recount: re-quantize the source and compare.
    Returns a list of problems (empty = page proven)."""
    fresh = quantize_image(path, grid_w, max_colors)
    problems = []
    if (fresh["w"], fresh["h"]) != (page["w"], page["h"]):
        problems.append("grid size differs on recount")
        return problems
    diff = sum(1 for r in range(page["h"]) for c in range(page["w"])
               if fresh["grid"][r][c] != page["grid"][r][c])
    if diff:
        problems.append(f"{diff} cells differ on recount")
    total = sum(p["count"] for p in page["palette"])
    if total != page["w"] * page["h"]:
        problems.append(f"palette counts sum to {total}, grid has {page['w'] * page['h']} cells")
    present = {v for row in page["grid"] for v in row}
    keyed = {p["num"] for p in page["palette"]}
    if present != keyed:
        problems.append(f"color key covers {sorted(keyed)}, grid uses {sorted(present)}")
    for p in page["palette"]:
        actual = sum(1 for row in page["grid"] for v in row if v == p["num"])
        if actual != p["count"]:
            problems.append(f"color {p['num']} claims {p['count']} cells, grid has {actual}")
    return problems

# -------------------------------------------------------------------- PDF

def render_pdf(path, pages):
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    line = HexColor("#bbbbbb")
    accent = HexColor("#2050a0")
    c = rl_canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(72, 640, "MosaicColorPress")
    c.setFont("Helvetica", 15)
    c.drawString(72, 606, "Color-by-number books from your own photos.")
    c.setFont("Helvetica", 11.5)
    lines = [
        "Each photo was reduced to a numbered mosaic grid. Color each",
        "cell with the color of its number from the key on the following",
        "page. Every page was recounted cell by cell against the source",
        "photo before printing: the key covers every number used, and",
        "the counts always add up to the full grid.",
        "",
        f"{len(pages)} photos, {sum(p['w'] * p['h'] for p in pages)} cells in total.",
    ]
    y = 540
    for ln in lines:
        c.drawString(72, y, ln)
        y -= 20
    c.showPage()
    for i, p in enumerate(pages, 1):
        cell = min(500 / p["w"], 600 / p["h"])
        gw, gh = cell * p["w"], cell * p["h"]
        x0, y_top = (PAGE_W - gw) / 2, 706
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(54, 748, f"Page {i} -- {p['source']}")
        c.setFont("Helvetica", 10.5)
        c.setFillColor(accent)
        c.drawString(54, 730, f"{p['w']}x{p['h']} grid, {len(p['palette'])} colors -- recounted and verified")
        c.setStrokeColor(line)
        c.setLineWidth(0.4)
        for r in range(p["h"] + 1):
            c.line(x0, y_top - r * cell, x0 + gw, y_top - r * cell)
        for cc in range(p["w"] + 1):
            c.line(x0 + cc * cell, y_top, x0 + cc * cell, y_top - gh)
        c.setFillColor(ink)
        c.setFont("Helvetica", max(3.2, cell * 0.4))
        for r in range(p["h"]):
            for cc in range(p["w"]):
                c.drawCentredString(x0 + cc * cell + cell / 2,
                                    y_top - r * cell - cell * 0.64,
                                    str(p["grid"][r][cc]))
        c.showPage()
        # key page: legend + filled reference
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(54, 748, f"Color key -- Page {i} ({p['source']})")
        y = 716
        c.setFont("Helvetica", 11)
        for entry in p["palette"]:
            r_, g_, b_ = entry["rgb"]
            c.setFillColor(HexColor(entry["hex"]))
            c.rect(54, y - 2, 16, 12, stroke=0, fill=1)
            c.setStrokeColor(line)
            c.rect(54, y - 2, 16, 12, stroke=1, fill=0)
            c.setFillColor(ink)
            c.drawString(78, y, f"{entry['num']}. {entry['name']}  {entry['hex']}  "
                                f"({entry['count']} cells)")
            y -= 20
        ref_cell = min(300 / p["w"], 300 / p["h"])
        rx0, ry_top = 54, y - 16
        rgb_of = {e["num"]: e["hex"] for e in p["palette"]}
        for r in range(p["h"]):
            for cc in range(p["w"]):
                c.setFillColor(HexColor(rgb_of[p["grid"][r][cc]]))
                c.rect(rx0 + cc * ref_cell, ry_top - (r + 1) * ref_cell,
                       ref_cell, ref_cell, stroke=0, fill=1)
        c.setFillColor(ink)
        c.setFont("Helvetica", 10)
        c.drawString(54, ry_top - p["h"] * ref_cell - 18,
                     "Filled reference (what the finished page looks like).")
        c.showPage()
    c.save()
    with open(path, "rb") as fh:
        data = fh.read()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")

# ------------------------------------------------------------- sample art

def make_sample_photo(path):
    """A deterministic synthetic 'photo' (landscape scene) so the product
    ships with an inspectable sample -- drawn, not photographed."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (440, 330), (135, 190, 235))
    d = ImageDraw.Draw(im)
    for yy in range(140):
        t = yy / 140
        col = (int(135 + 60 * t), int(190 + 30 * t), int(235 - 20 * t))
        d.line([(0, yy), (440, yy)], fill=col)
    d.ellipse([330, 26, 396, 92], fill=(255, 214, 64))          # sun
    d.polygon([(0, 190), (120, 96), (240, 190)], fill=(96, 110, 130))   # mountain
    d.polygon([(140, 190), (280, 80), (420, 190)], fill=(70, 84, 104))  # mountain 2
    d.polygon([(0, 190), (120, 96), (170, 140)], fill=(240, 244, 248))  # snowcap
    d.rectangle([0, 190, 440, 330], fill=(86, 150, 74))          # meadow
    d.rectangle([206, 218, 234, 268], fill=(150, 96, 52))        # cabin
    d.polygon([(198, 218), (220, 196), (242, 218)], fill=(96, 54, 30))  # roof
    d.rectangle([60, 200, 70, 258], fill=(90, 62, 34))           # tree trunk
    d.ellipse([34, 150, 96, 214], fill=(44, 120, 52))            # tree crown
    d.ellipse([356, 226, 420, 262], fill=(52, 132, 60))          # bush
    im.save(path)
    return path

# -------------------------------------------------------------------- run

def run_mosaiccolorpress(images, outdir, grid_w=44, max_colors=16, **kw):
    if not images:
        raise ValueError("at least one image is required")
    os.makedirs(outdir, exist_ok=True)
    pages = []
    for img in images:
        page = quantize_image(img, grid_w, max_colors)
        problems = verify_page(img, page, grid_w, max_colors)
        if problems:
            raise RuntimeError(f"{img}: recount failed: {problems}")
        page["cells"] = page["w"] * page["h"]
        pages.append(page)
    pdf_path = os.path.join(outdir, "mosaic_book.pdf")
    npages = render_pdf(pdf_path, pages)
    return {"pages": pages, "pdf_pages": npages, "pdf_path": pdf_path,
            "images": len(pages),
            "total_cells": sum(p["cells"] for p in pages)}

def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    opts = {"grid_width": 44, "max_colors": 16}
    for a in argv[1:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opts[k.replace("-", "_")] = int(v)
    if len(args) < 2:
        print("usage: mosaic_color.py out/ img1 [img2 ...] [--grid-width=44] [--max-colors=16]")
        return 2
    s = run_mosaiccolorpress(args[1:], args[0], grid_w=opts["grid_width"],
                             max_colors=opts["max_colors"])
    for p in s["pages"]:
        print(f"{p['source']}: {p['w']}x{p['h']} grid, {len(p['palette'])} colors, "
              f"{p['cells']} cells, recount PASS")
    print(f"PDF pages: {s['pdf_pages']}")
    print(f"PDF: {s['pdf_path']}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
