"""ASHTYN — bespoke alphabet.

Every glyph is drawn here as coordinates on a 100-unit cap height. No typeface
is loaded: the letters exist only in this file, so the wordmark cannot be
retyped and cannot look like anybody else's.

Every letter is then cut by the same two angled lines at cap and baseline —
one shared gesture across the alphabet, which is what turns a set of shapes
into an identity.

    python brand/src/build_ashtyn_type.py proof [outdir]
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONO = os.path.join(ROOT, "fonts", "SpaceMono-Regular.ttf")

WHITE = (247, 245, 250)
BLACK = (8, 6, 12)

# Heavy, condensed, struck from straight segments. y runs down; 0 = cap line.
GLYPHS = {
    "A": dict(w=78, polys=[[(0, 100), (28, 0), (50, 0), (78, 100), (55, 100),
                            (49, 76), (29, 76), (23, 100)]],
              holes=[[(33, 58), (45, 58), (39, 26)]]),
    "S": dict(w=62, polys=[
        [(0, 0), (62, 0), (62, 22), (0, 22)],
        [(0, 22), (22, 22), (22, 39), (0, 39)],
        [(0, 39), (62, 39), (62, 61), (0, 61)],
        [(40, 61), (62, 61), (62, 78), (40, 78)],
        [(0, 78), (62, 78), (62, 100), (0, 100)],
    ], holes=[]),
    "H": dict(w=66, polys=[[(0, 0), (22, 0), (22, 100), (0, 100)],
                           [(44, 0), (66, 0), (66, 100), (44, 100)],
                           [(0, 39), (66, 39), (66, 61), (0, 61)]], holes=[]),
    "T": dict(w=66, polys=[[(0, 0), (66, 0), (66, 22), (0, 22)],
                           [(22, 0), (44, 0), (44, 100), (22, 100)]], holes=[]),
    "Y": dict(w=70, polys=[[(0, 0), (24, 0), (47, 56), (23, 56)],
                           [(46, 0), (70, 0), (47, 56), (23, 56)],
                           [(23, 50), (47, 50), (47, 100), (23, 100)]], holes=[]),
    "N": dict(w=70, polys=[[(0, 0), (22, 0), (22, 100), (0, 100)],
                           [(48, 0), (70, 0), (70, 100), (48, 100)],
                           [(0, 0), (24, 0), (70, 100), (46, 100)]], holes=[]),
}

TRACKING = 6      # gap between letters, in cap units
CUT = 9           # shared angled trim at cap and baseline, in cap units


def glyph(ch, cap, ss=4):
    g = GLYPHS[ch]
    s = cap * ss / 100.0
    w, h = int(round(g["w"] * s)), int(round(cap * ss))
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    for poly in g["polys"]:
        d.polygon([(x * s, y * s) for x, y in poly], fill=255)
    for poly in g["holes"]:
        d.polygon([(x * s, y * s) for x, y in poly], fill=0)
    img = img.resize((int(round(w / ss)), int(round(h / ss))), Image.LANCZOS)

    # The shared cut: top edge drops to the right, bottom edge rises to the
    # right. Every letter carries it, so the alphabet reads as one hand.
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    drop = (xx / max(w - 1, 1)) * (CUT * h / 100.0)
    keep = (yy >= drop) & (yy <= h - 1 - drop)
    return Image.fromarray((np.asarray(img).astype(np.float32) * keep).astype(np.uint8), "L")


def wordmark(text, cap):
    gap = int(round(TRACKING * cap / 100.0))
    parts = [glyph(c, cap) for c in text]
    W = sum(p.width for p in parts) + gap * (len(parts) - 1)
    out = Image.new("L", (W, cap), 0)
    x = 0
    for p in parts:
        out.paste(p, (x, 0))
        x += p.width + gap
    return out


def slice_warp(mask, bands=4, amount=5):
    """One restrained break: a couple of bands nudged apart, nothing more."""
    w, h = mask.size
    out = Image.new("L", (w, h), 0)
    step = h / bands
    shifts = (0, amount, amount, -amount, 0, amount)
    for i in range(bands):
        y0, y1 = int(i * step), int((i + 1) * step)
        out.paste(mask.crop((0, y0, w, y1)), (shifts[i % len(shifts)], y0))
    return out


def tint(mask, color, alpha=255):
    a = np.asarray(mask)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = color
    out[..., 3] = (a.astype(np.float32) * alpha / 255.0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def ground(w, h, hot=(120, 40, 200), seed=5):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.5, h * 0.44
    r = np.sqrt(((xx - cx) / (w * 0.60)) ** 2 + ((yy - cy) / (h * 0.62)) ** 2)
    glow = np.clip(1.0 - r, 0, 1) ** 2.2
    base = np.zeros((h, w, 3), np.float32)
    base[..., 0], base[..., 1], base[..., 2] = BLACK
    for i in range(3):
        base[..., i] += glow * hot[i] * 0.55
    rng = np.random.default_rng(seed)
    base += rng.normal(0, 2.2, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def chrome(mask, cap):
    w, h = mask.size
    stops = [(0.00, (252, 252, 255)), (0.16, (120, 118, 132)), (0.28, (255, 255, 255)),
             (0.40, (74, 70, 88)), (0.54, (226, 224, 234)), (0.70, (56, 52, 70)),
             (0.84, (204, 202, 216)), (1.00, (38, 34, 48))]
    ys = np.linspace(0, 1, h)
    ramp = np.zeros((h, 3), np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (ys >= p0) & (ys <= p1)
        t = ((ys[m] - p0) / max(p1 - p0, 1e-6))[:, None]
        ramp[m] = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    arr = np.repeat(ramp[:, None, :], w, axis=1)
    a = np.asarray(mask).astype(np.float32) / 255.0
    out = np.dstack([np.clip(arr, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def proof(outdir):
    os.makedirs(outdir, exist_ok=True)
    cap = 300
    m = wordmark("ASHTYN", cap)
    W, H = m.width + 300, cap + 300
    canvas = ground(W, H).convert("RGBA")
    canvas.alpha_composite(tint(m, (150, 70, 255), 120), (150 - 6, 150))
    canvas.alpha_composite(tint(m, WHITE), (150, 150))
    canvas.convert("RGB").save(os.path.join(outdir, "proof-wordmark.png"))

    # Alphabet sheet: every glyph at size, so bad geometry is obvious.
    letters = "ASHTYN"
    big = 220
    sheet = Image.new("RGB", (6 * (big + 40) + 40, big + 120), BLACK)
    x = 40
    for c in letters:
        g = glyph(c, big)
        sheet.paste(g, (x, 40), g)
        x += g.width + 40
    sheet.save(os.path.join(outdir, "proof-glyphs.png"))

    # Chrome, at avatar scale, to see whether the ramp survives.
    av = chrome(wordmark("A", 700), 700)
    a = Image.new("RGBA", (1000, 1000), (10, 8, 16, 255))
    a.alpha_composite(av, ((1000 - av.width) // 2, (1000 - av.height) // 2))
    a.convert("RGB").save(os.path.join(outdir, "proof-chrome-a.png"))
    print("wrote proof ->", outdir)


if __name__ == "__main__":
    proof(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "export", "ashtyn"))
