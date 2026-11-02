# MosaicColorPress

Turn your own photos into **mosaic color-by-number book pages** — a whole book in one run, with every page recounted cell by cell before it prints.

## Why

Photo-to-color-by-number converters usually charge per page in credits and run in someone's cloud. MosaicColorPress runs 100% on your machine: drop in a folder of photos, get a complete book — for each photo, a numbered coloring page plus a color-key page with named swatches and a filled reference image. And because a single wrong number quietly ruins a page, every page is **re-quantized from the source photo and compared cell by cell** before the book is written: palette counts must sum to the full grid, the color key must cover exactly the numbers the grid uses, and the two grids must be identical. A page that fails the recount is never printed.

## Use

**App (Windows):** launch `MosaicColorPress.exe`, add photos (PNG/JPG/BMP/WebP), set grid width (default 44 cells) and max colors (default 16), click **Build the book**. Output: `mosaic_book.pdf` in a `mosaiccolorpress_out` folder — title page, then per photo a coloring page and a key page. 8.5×11in (612×792pt).

**Command line:** `python mosaic_color.py out/ photo1.png photo2.jpg --grid-width=44 --max-colors=16`

A sample photo and its converted book are included (`sample_photo.png`, `sample_book.pdf`) — the sample image is a drawn landscape, so you can inspect the full pipeline without using your own photos first.

## How the numbers work

Colors are numbered by frequency — the most-used color on the page is 1 — and named from a fixed 24-color naming palette (nearest match), so keys read like "1. Sky Blue #78BEEB (212 cells)" instead of bare hex codes. Grid height follows each photo's aspect ratio (capped at 84 rows).

## Verified

Acceptance test (11/11 PASS, `test/acceptance_results.txt`): a 2-photo book — both pages recounted clean cell-by-cell; per-color totals independently re-derived with raw Pillow calls; one deliberately flipped cell flagged by the recount (and clean again after restore); counts sum exactly to each grid (1,452 and 1,936 cells); color keys cover exactly the numbers used; PDF exactly 612×792pt, 5 pages for 2 photos; quantization fully deterministic.

## Scope

Mosaic (square-cell) color-by-number — the style that prints cleanly at book scale. Your photos never leave your machine; there are no per-page credits because there is no cloud. Deterministic: same photo + same settings = same page, every time.

## Build from source

`pip install pyinstaller reportlab pillow`, then `pyinstaller mosaiccolorpress.spec`. Or push to GitHub and let the included Actions workflow build the Windows package.
