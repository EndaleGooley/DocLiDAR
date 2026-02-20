import fitz  # PyMuPDF
from typing import Tuple
import numpy as np
import math

def normalize(arr: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    mn = float(arr.min())
    mx = float(arr.max())
    if mx - mn < eps:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - mn) / (mx - mn)).astype(np.float32)

def smooth_gaussian(grid: np.ndarray, sigma: float) -> np.ndarray:
    """
    Lightweight Gaussian blur without scipy.
    Separable 1D kernel convolution along x and y.
    """
    if sigma <= 0:
        return grid.astype(np.float32)

    radius = int(max(1, math.ceil(3 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    kernel = np.exp(-(x * x) / (2 * sigma * sigma))
    kernel /= kernel.sum()

    pad = radius

    # Convolve rows
    padded = np.pad(grid, ((0, 0), (pad, pad)), mode="edge").astype(np.float32)
    tmp = np.zeros_like(grid, dtype=np.float32)
    for r in range(grid.shape[0]):
        tmp[r, :] = np.convolve(padded[r, :], kernel, mode="valid")

    # Convolve cols
    padded2 = np.pad(tmp, ((pad, pad), (0, 0)), mode="edge").astype(np.float32)
    out = np.zeros_like(tmp, dtype=np.float32)
    for c in range(tmp.shape[1]):
        out[:, c] = np.convolve(padded2[:, c], kernel, mode="valid")

    return out

def compute_word_density(words, page_w_pt: float, page_h_pt: float, grid_size: Tuple[int, int]) -> np.ndarray:
    """
    words: PyMuPDF page.get_text("words")
    Returns: (gy, gx) grid of word counts
    """
    gx, gy = grid_size
    word_grid = np.zeros((gy, gx), dtype=np.float32)

    def to_cell(x: float, y: float):
        cx = int((x / page_w_pt) * gx)
        cy = int((y / page_h_pt) * gy)
        return max(0, min(gx - 1, cx)), max(0, min(gy - 1, cy))

    for x0, y0, x1, y1, txt, *_ in words:
        txt = (txt or "").strip()
        if not txt:
            continue
        cx_pt = 0.5 * (x0 + x1)
        cy_pt = 0.5 * (y0 + y1)
        cx, cy = to_cell(cx_pt, cy_pt)
        word_grid[cy, cx] += 1.0

    return word_grid

def compute_letter_terrain(words, page_w_pt: float, page_h_pt: float, grid_size: Tuple[int, int]) -> np.ndarray:
    """
    Terrain metric (grayscale):
      sum_{c in a..z} cell_count(c) / global_count(c)
    Normalized 0..1.
    """
    gx, gy = grid_size
    letter_grids = np.zeros((26, gy, gx), dtype=np.float32)
    global_letters = np.zeros(26, dtype=np.float32)

    def to_cell(x: float, y: float):
        cx = int((x / page_w_pt) * gx)
        cy = int((y / page_h_pt) * gy)
        return max(0, min(gx - 1, cx)), max(0, min(gy - 1, cy))

    for x0, y0, x1, y1, txt, *_ in words:
        txt = (txt or "").strip()
        if not txt:
            continue

        cx_pt = 0.5 * (x0 + x1)
        cy_pt = 0.5 * (y0 + y1)
        cx, cy = to_cell(cx_pt, cy_pt)

        for ch in txt.lower():
            if "a" <= ch <= "z":
                idx = ord(ch) - ord("a")
                letter_grids[idx, cy, cx] += 1.0
                global_letters[idx] += 1.0

    denom = np.maximum(global_letters, 1.0)
    terrain = np.zeros((gy, gx), dtype=np.float32)
    for i in range(26):
        terrain += (letter_grids[i] / denom[i])

    return normalize(terrain)