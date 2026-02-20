# DLM-Document_Lidar_Mapping
* Hello, I’m Endale Gooley. I built DLM to demonstrate analytical thinking, software development, and visual design experimentation. This project was developed with assistance from ChatGPT/Copilot.

DLM generates LiDAR-style visualizations that help you evaluate document layout quality (e.g., over/under-use of whitespace) and identify dense or repetitive regions that may reduce readability.

## What it does

DLM produces LiDAR-inspired maps of text distribution on each page:
- Elevation (blue → red): word-density per grid region
- Terrain (grayscale): letter-usage concentration per region
- Legend: low → high in the corner of the visualization

## Why is it useful
- Document readability is often impacted by uneven spacing and dense clusters of text. - DLM provides a fast visual diagnostic for layout balance, helping you spot areas that may benefit from reformatting, spacing adjustments, or rewriting.

## Improvemnets
1.	Issue: density “hotspots” appeared as smooth blobs around each word center
Initially, word density was rendered in a way that visually over-emphasized individual word centers.

Solution: discretize the page into a fixed grid of spatial bins. This makes density quantifiable and comparable across regions, and produces stable, interpretable heatmaps.

Added a grid overlay:

```python
def draw_grid_overlay(img: Image.Image, grid_size: Tuple[int, int], alpha: int = 80, width: int = 1) -> Image.Image:
    gx, gy = grid_size
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # vertical 
    for i in range(1, gx):
        x = int(i * w / gx)
        d.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha), width=width)

    # horizontal
    for j in range(1, gy):
        y = int(j * h / gy)
        d.line([(0, y), (w, y)], fill=(0, 0, 0, alpha), width=width)

    return Image.alpha_composite(img.convert("RGBA"), overlay)
```
- And a call before returning the final image:

```python
out = draw_grid_overlay(out, grid_size=grid_size, alpha=90, width=1)
```

2.	Issue: grid cell boundaries were not visually preserved after resizing
Bilinear resizing blends adjacent bins and introduces artificial gradients, which can mask true local density differences.

Solution: switch the elevation/terrain resize from bilinear to nearest-neighbor. Nearest-neighbor preserves each bin as an exact discrete block, maintaining spatial integrity of the grid.

Before:

```python
 elev_img = Image.fromarray((elev * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.BILINEAR
    )
    terr_img = Image.fromarray((terrain * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.BILINEAR
    )
```
After:

```python
 elev_img = Image.fromarray((elev * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.NEAREST
    )
    terr_img = Image.fromarray((terrain * 255).astype(np.uint8), mode="L").resize(
        base.size, resample=Image.NEAREST
    )
```

## Installation
1.	Place your .pdf or .docx files into the input/ folder.
2.	Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  #For Windows: .venv\Scripts\activate
pip install -r requirements.txt 
```
## Usage
```bash
python3 main.py --in-dir input
```
## Running again
- If you open a new terminal session, re-activate the environment:
1. Delete .venv
2. Start the "Install section" steps over

## Technical notes
- Add document oppacity slider, for render
- Add slider for grid size
- Add UI selection options density theme

# License
MIT License

Copyright (c) [2026] [Endale Gooley]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.