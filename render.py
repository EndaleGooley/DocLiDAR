from __future__ import annotations
import fitz  # PyMuPDF
import matplotlib.cm as cm
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from typing import List, Tuple
from metrics import normalize, smooth_gaussian, compute_word_density, compute_letter_terrain

def add_legend(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    cmap_name: str,
    label: str = "Word density",
) -> None:
    margin = 24
    bar_w = max(18, w // 60)
    bar_h = max(140, h // 5)
    x1, y1 = w - margin, h - margin
    x0, y0 = x1 - bar_w, y1 - bar_h

    box_pad = 10
    draw.rectangle(
        [x0 - box_pad, y0 - 34, x1 + box_pad, y1 + box_pad],
        fill=(255, 255, 255, 220),
        outline=(0, 0, 0, 120),
        width=2,
    )

    cmap = cm.get_cmap(cmap_name)
    for i in range(bar_h):
        t = 1.0 - (i / max(1, bar_h - 1))  # top=high
        r, g, b, _ = cmap(t)
        draw.line(
            [(x0, y0 + i), (x1, y0 + i)],
            fill=(int(255 * r), int(255 * g), int(255 * b), 255),
        )

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size=max(12, w // 85))
    except Exception:
        font = ImageFont.load_default()

    draw.text((x0 - box_pad, y0 - 30), label, fill=(0, 0, 0, 255), font=font)
    draw.text((x1 + 6, y0 - 6), "high", fill=(0, 0, 0, 255), font=font)
    draw.text((x1 + 6, y1 - 12), "low", fill=(0, 0, 0, 255), font=font)

def draw_grid_overlay(img: Image.Image, grid_size: Tuple[int, int], alpha: int = 80, width: int = 1) -> Image.Image:
    gx, gy = grid_size
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # vertical lines
    for i in range(1, gx):
        x = int(i * w / gx)
        d.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha), width=width)

    # horizontal lines
    for j in range(1, gy):
        y = int(j * h / gy)
        d.line([(0, y), (w, y)], fill=(0, 0, 0, alpha), width=width)

    return Image.alpha_composite(img.convert("RGBA"), overlay)

def images_to_pdf(images: List[Image.Image], out_pdf_path: str) -> None:
    rgb_imgs = [im.convert("RGB") if im.mode != "RGB" else im for im in images]
    if not rgb_imgs:
        return
    rgb_imgs[0].save(out_pdf_path, save_all=True, append_images=rgb_imgs[1:])

def render_page_overlay(
    page: fitz.Page,
    grid_size: Tuple[int, int],
    sigma: float,
    alpha: float,
    dpi: int,
    cmap_name: str = "coolwarm",
    terrain_bias_white: bool = True,
    ) -> Image.Image:
    """
    Produces a LiDAR-like composite:
      - Base: rendered page image
      - Terrain: grayscale "paper" texture from letter metric
      - Elevation: blue->red overlay from smoothed word density
      - Legend bottom-right
    """
    rect = page.rect
    w_pt, h_pt = rect.width, rect.height

    words = page.get_text("words")

    word_grid = compute_word_density(words, w_pt, h_pt, grid_size)
    word_s = smooth_gaussian(word_grid, sigma=sigma)
    elev = normalize(word_s)

    terrain = compute_letter_terrain(words, w_pt, h_pt, grid_size)

    # render page to pixels
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    base = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

    elev_img = Image.fromarray((elev * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.NEAREST
    )
    terr_img = Image.fromarray((terrain * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.NEAREST
    )

    # Terrain as near-white paper texture
    terr_rgba = Image.merge("RGBA", (terr_img, terr_img, terr_img, Image.new("L", terr_img.size, 255)))
    if terrain_bias_white:
        terr_arr = np.array(terr_rgba).astype(np.float32)
        terr_arr[..., :3] = 220 + (terr_arr[..., :3] / 255.0) * 35  # [220..255]
        terr_rgba = Image.fromarray(terr_arr.astype(np.uint8), mode="RGBA")

    # Elevation colormap overlay
    cmap = cm.get_cmap(cmap_name)
    elev_arr = np.array(elev_img).astype(np.float32) / 255.0
    rgba = (cmap(elev_arr) * 255).astype(np.uint8)
    heat = Image.fromarray(rgba, mode="RGBA")

    # Alpha scaled by elevation, so low density stays subtle
    a = (alpha * (elev_arr ** 0.85) * 255.0).astype(np.uint8)
    heat.putalpha(Image.fromarray(a, mode="L"))

    out = Image.alpha_composite(base, terr_rgba)
    out = Image.alpha_composite(out, heat)

    draw = ImageDraw.Draw(out, "RGBA")
    add_legend(draw, out.size[0], out.size[1], cmap_name=cmap_name, label="Word density")
    out = draw_grid_overlay(out, grid_size=grid_size, alpha=90, width=1)
    return out