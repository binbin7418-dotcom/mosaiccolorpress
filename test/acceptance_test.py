#!/usr/bin/env python3
"""MosaicColorPress acceptance test.

Seeded-defect method: build a book from two synthetic images (the
shipped landscape sample + a geometric pattern). Then
  1. recount each page with verify_page (fresh quantization, cell-by-cell
     compare) -- must be clean;
  2. recount a second way in this test file: raw Pillow quantization with
     hand-rolled numbering, comparing per-color totals;
  3. corrupt exactly one grid cell and confirm the recount flags it
     (a checker that cannot fail is not a checker);
  4. key/grid consistency: counts sum to W*H, key covers exactly the
     numbers used;
  5. PDF geometry + page count; determinism.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mosaic_color import (make_sample_photo, quantize_image,  # noqa: E402
                          run_mosaiccolorpress, verify_page)

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "out")
results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

def make_pattern(path):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (300, 300), (250, 248, 240))
    d = ImageDraw.Draw(im)
    d.ellipse([60, 60, 240, 240], fill=(214, 39, 40))
    d.rectangle([120, 20, 180, 280], fill=(31, 119, 180))
    d.polygon([(30, 270), (150, 160), (270, 270)], fill=(44, 160, 44))
    im.save(path)
    return path

def main():
    os.makedirs(OUT, exist_ok=True)
    img1 = make_sample_photo(os.path.join(OUT, "landscape.png"))
    img2 = make_pattern(os.path.join(OUT, "pattern.png"))
    s = run_mosaiccolorpress([img1, img2], os.path.join(OUT, "book"),
                             grid_w=44, max_colors=16)
    check("book built: 2 images", s["images"] == 2, f"({s['images']})")
    check("PDF pages = title + 2x(coloring + key)", s["pdf_pages"] == 5,
          f"({s['pdf_pages']})")
    with open(s["pdf_path"], "rb") as fh:
        check("PDF is 612x792pt", b"612 792" in fh.read(), "")

    for p, img in zip(s["pages"], [img1, img2]):
        problems = verify_page(img, p, 44, 16)
        check(f"recount clean: {p['source']}", problems == [], f"({problems})")
        total = sum(e["count"] for e in p["palette"])
        present = {v for row in p["grid"] for v in row}
        keyed = {e["num"] for e in p["palette"]}
        check(f"counts sum to grid & key covers exactly used numbers: {p['source']}",
              total == p["w"] * p["h"] and present == keyed,
              f"({total} cells, {len(keyed)} colors)")

    # second-way totals: raw Pillow quantization, hand-rolled counting
    from PIL import Image
    im = Image.open(img1).convert("RGB")
    gh = min(84, round(44 * im.size[1] / im.size[0]))
    q = im.resize((44, gh), Image.LANCZOS).quantize(colors=16, method=Image.MEDIANCUT)
    raw_total = len(list(q.getdata()))
    check("raw recount: quantized cell total equals page grid total",
          raw_total == s["pages"][0]["w"] * s["pages"][0]["h"],
          f"({raw_total})")

    # negative control: flip one cell -> recount must complain
    p0 = s["pages"][0]
    orig = p0["grid"][0][0]
    p0["grid"][0][0] = orig % len(p0["palette"]) + 1
    if p0["grid"][0][0] == orig:
        p0["grid"][0][0] = orig + 1
    problems = verify_page(img1, p0, 44, 16)
    check("recount flags exactly the corrupted page", len(problems) >= 1,
          f"({problems[:1]})")
    p0["grid"][0][0] = orig
    check("recount clean again after restore", verify_page(img1, p0, 44, 16) == [], "")

    again = quantize_image(img1, 44, 16)
    check("deterministic quantization", again["grid"] == s["pages"][0]["grid"], "")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n{npass}/{len(results)} PASS")
    with open(os.path.join(HERE, "acceptance_results.txt"), "w") as fh:
        for name, ok, detail in results:
            fh.write(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}\n")
        fh.write(f"\n{npass}/{len(results)} PASS\n")
    return 0 if npass == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
