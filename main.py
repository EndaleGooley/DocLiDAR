#!/usr/bin/env python3
import fitz  # PyMuPDF
import argparse
from pathlib import Path
from typing import Tuple

from render import render_page_overlay, images_to_pdf
from utils import collect_inputs, is_pdf, is_docx, convert_docx_to_pdf

def parse_grid(grid_str: str) -> Tuple[int, int]:
    parts = grid_str.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Grid must be like 140x180")
    gx, gy = int(parts[0]), int(parts[1])
    if gx <= 0 or gy <= 0:
        raise argparse.ArgumentTypeError("Grid dimensions must be positive")
    return gx, gy

def process_pdf(
    pdf_path: Path,
    outdir: Path,
    grid_size: Tuple[int, int],
    sigma: float,
    cmap: str,
    alpha: float,
    dpi: int,
    write_pdf: bool, 
    ) -> None:

    outdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path)) 
    rendered = []

    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            out_img = render_page_overlay(
                page=page,
                grid_size=grid_size,
                sigma=sigma,
                cmap_name=cmap,
                alpha=alpha,
                dpi=dpi,
            )
            png_path = outdir / f"Doc_{i+1:02d}_maping.png"
            out_img.save(png_path)
            print(f"Wrote {png_path}")
            rendered.append(out_img)

        if write_pdf:
            out_pdf = outdir / "map_overlay.pdf"
            images_to_pdf(rendered, str(out_pdf))
            print(f"Wrote {out_pdf}")
    finally:
        doc.close()

def main() -> None:
    ap = argparse.ArgumentParser(
        description="LiDAR-style word density (elevation) + letter terrain visualization for PDF/DOCX."
    )
    ap.add_argument("inputs", nargs="*", help="Input files (.pdf, .docx). You can pass multiple.")
    ap.add_argument("--in-dir", default=None, help="Process all .pdf/.docx in a directory (recursively).")
    ap.add_argument("--outdir", default="out", help="Base output directory (matches your repo 'out').")

    ap.add_argument("--grid", type=parse_grid, default="70x90", help="Grid resolution WxH cells (e.g. 140x180).")
    ap.add_argument("--sigma", type=float, default=2.5, help="Gaussian smoothing sigma (grid space).")
    ap.add_argument("--cmap", default="turbo", help="Matplotlib colormap name (e.g. turbo, jet).")
    ap.add_argument("--alpha", type=float, default=0.85, help="Max overlay opacity (0..1).")
    ap.add_argument("--dpi", type=int, default=200, help="Render DPI for page context image.")
    ap.add_argument("--pdf", action="store_true", help="Also write a combined PDF per input.")
    args = ap.parse_args()

    if not args.inputs and not args.in_dir:
        
        ap.error("Provide at least one input file or --in-dir.")

    base_out = Path(args.outdir).expanduser().resolve()
    base_out.mkdir(parents=True, exist_ok=True)

    inputs = collect_inputs(args.inputs, args.in_dir)

    for inp in inputs:
        out_sub = base_out / inp.stem

        if is_pdf(inp):
            process_pdf(inp, out_sub, args.grid, args.sigma, args.cmap, args.alpha, args.dpi, args.pdf)
        elif is_docx(inp):
            cache_dir = out_sub / "_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = cache_dir / f"{inp.stem}.pdf"
            pdf_path = convert_docx_to_pdf(inp, pdf_path)
            process_pdf(pdf_path, out_sub, args.grid, args.sigma, args.cmap, args.alpha, args.dpi, args.pdf)

if __name__ == "__main__":
    main()