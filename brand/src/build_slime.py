"""Bio-slime graffiti: inflated glossy letters that drip and grow tendrils.

Every letterform is unioned with its neighbours and its drips, then the whole
mass is inflated once — so the word reads as a single organism rather than six
shapes. Volume is faked from the silhouette: a blurred copy of the mask is
treated as a height field, its gradient as a surface normal, and a hard
top-left light does the rest. That is what gives the plastic gloss.

    python brand/src/build_slime.py probe
    python brand/src/build_slime.py
"""
import math
import pathlib
import sys
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BRAND = pathlib.Path(__file__).resolve().parent.parent
OUT = BRAND / "export"
LAYERS = pathlib.Path(__file__).resolve().parent / "layers"
BOLD = BRAND / "fonts" / "BricolageGrotesque-Bold.ttf"
# typography: Rubik Wet Paint (Google Fonts, SIL OFL 1.1) — the letterforms and
# their built-in drips are the designer's work; everything around them is generated
SLIME = BRAND / "fonts" / "RubikWetPaint-Regular.ttf"

WHITE = np.array([255, 255, 255], np.float32)
BRIGHT = np.array([164, 228, 84], np.float32)
MID = np.array([92, 180, 60], np.float32)
DARK = np.array([38, 96, 36], np.float32)
EDGE = np.array([22, 66, 24], np.float32)
BLUE = np.array([92, 205, 236], np.float32)
BLUE_D = np.array([18, 96, 140], np.float32)
PALE = np.array([206, 232, 198], np.float32)


def rgb(c):
    """PIL wants ints; the maths wants floats."""
    return tuple(int(round(float(v))) for v in c)


# ------------------------------------------------------------------ masks


def glyph_mask(px, ch, path=None):
    f = ImageFont.truetype(str(path or SLIME), px)
    box = f.getbbox(ch)
    img = Image.new("L", (box[2] - box[0] + 60, box[3] - box[1] + 60), 0)
    ImageDraw.Draw(img).text((30 - box[0], 30 - box[1]), ch, font=f, fill=255)
    m = img.crop(img.getbbox())
    # the reference is tall and leaning; stretch the type before it gets inflated
    return m.resize((max(1, int(m.width * 1.04)), max(1, int(m.height * 1.12))), Image.LANCZOS)


def qbez(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def drip(draw, x, y, length, w, seed=0):
    """Viscous run: fat neck holding on, heavy bulb at the end, satellite drop."""
    rng = np.random.default_rng(seed)
    wob = rng.uniform(-1, 1) * w * 0.3
    r = w * 0.62
    left = qbez((x - w / 2, y), (x - w * 0.46 + wob, y + length * 0.55), (x - r, y + length - r), 20)
    right = qbez((x + r, y + length - r), (x + w * 0.46 + wob, y + length * 0.55), (x + w / 2, y), 20)
    draw.polygon(left + right, fill=255)
    draw.ellipse([x - r, y + length - 2 * r, x + r, y + length], fill=255)
    if length > w * 3.2:
        sr = r * rng.uniform(0.30, 0.46)
        sy = y + length + rng.uniform(r * 0.9, r * 2.2)
        draw.ellipse([x - sr, sy - sr, x + sr, sy + sr], fill=255)


def run(text, px, size):
    """Union of every letter plus the drips — one organism."""
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    rng = np.random.default_rng(7)
    x = 0
    boxes = []
    for ch in text:
        g = glyph_mask(px, ch)
        ang = rng.uniform(-5, 5)
        g = g.rotate(ang, resample=Image.BICUBIC, expand=True)
        boxes.append((x, g.width, g.height))
        x += g.width - int(px * 0.012)
    total = x
    start = (size[0] - total) // 2
    base_y = int(size[1] * 0.5 - px * 0.36)
    for i, ch in enumerate(text):
        g = glyph_mask(px, ch)
        ang = rng.uniform(-5, 5)
        g = g.rotate(ang, resample=Image.BICUBIC, expand=True)
        bx = start + sum(b[1] for b in boxes[:i]) - int(px * 0.06) * i
        by = base_y + int(rng.uniform(-0.03, 0.03) * px)
        mask.paste(255, (bx, by), g)
    # weld only the joints that would otherwise float apart
    for i in range(len(boxes) - 1):
        if i % 2:
            continue
        jx = start + sum(b[1] for b in boxes[:i + 1]) - int(px * 0.06) * (i + 1)
        jy = base_y + int(px * rng.uniform(0.34, 0.52))
        d.line([(jx - px * 0.08, jy), (jx + px * 0.08, jy + rng.uniform(-px * 0.05, px * 0.05))],
               fill=255, width=int(px * 0.10))
    # drips off the baseline and out of the counters
    bottom = base_y + int(px * 0.80)
    for i in range(7):
        dx = start + rng.uniform(0.02, 0.98) * total
        drip(d, dx, bottom - px * 0.16, rng.uniform(px * 0.12, px * 0.38),
             int(px * rng.uniform(0.030, 0.055)), seed=i)
    # bubbles punched through the mass
    for i in range(9):
        cx = start + rng.uniform(0.02, 0.98) * total
        cy = base_y + rng.uniform(0.1, 0.85) * px
        rr = rng.uniform(0.008, 0.020) * px
        d.ellipse([cx - rr, cy - rr * rng.uniform(0.7, 1.3), cx + rr, cy + rr * rng.uniform(0.7, 1.3)], fill=0)
    # gentle fuse: keep the counters open, just soften the joins
    soft = mask.filter(ImageFilter.GaussianBlur(max(1, px * 0.006)))
    return soft.point(lambda v: 255 if v >= 118 else 0)


def grow(mask, px, k=0.016):
    b = mask.filter(ImageFilter.GaussianBlur(px * k))
    return b.point(lambda v: 255 if v > 58 else 0)


# ------------------------------------------------------------------ volume


def shade(mask, px, light=(-0.55, -0.60, 0.58)):
    h = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(2, px * 0.016))), np.float32) / 255.0
    gy, gx = np.gradient(h)
    k = px * 0.040
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(h)
    nrm = np.sqrt(nx * nx + ny * ny + nz * nz)
    lx, ly, lz = light
    lam = np.clip((nx * lx + ny * ly + nz * lz) / nrm, 0, 1)
    # remap so most of the body sits on the bright colour and only the shaded
    # side falls into the dark green — a wash across the whole letter reads muddy
    lam = np.clip((lam - 0.26) / 0.46, 0, 1) ** 1.05

    col = DARK[None, None, :] + (BRIGHT - DARK)[None, None, :] * lam[..., None]
    col += (MID - DARK)[None, None, :] * ((1 - lam) ** 2.2)[..., None] * 0.35
    spec = np.clip((lam - 0.80) / 0.20, 0, 1) ** 1.6
    col += spec[..., None] * (WHITE - col) * 0.95
    return np.clip(col, 0, 255).astype(np.uint8)


def blob_layer(size, items, seed=0):
    """Blue slime islands: same shading, different palette."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    for (cx, cy, r, seed_i) in items:
        m = Image.new("L", size, 0)
        d = ImageDraw.Draw(m)
        rng = np.random.default_rng(seed_i)
        pts = []
        for i in range(28):
            a = 2 * math.pi * i / 28
            rr = r * (0.72 + 0.34 * rng.random())
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        d.polygon(pts, fill=255)
        for j in range(3):
            drip(d, cx + rng.uniform(-r * 0.6, r * 0.6), cy + r * 0.5,
                 rng.uniform(r * 0.5, r * 1.5), max(4, int(r * rng.uniform(0.14, 0.24))), seed=seed_i + j)
        m = m.filter(ImageFilter.GaussianBlur(r * 0.10)).point(lambda v: 255 if v >= 128 else 0)
        g = grow(m, r * 3)
        ring = ImageChops.subtract(g, m)

        h = np.asarray(m.filter(ImageFilter.GaussianBlur(r * 0.22)), np.float32) / 255.0
        gy, gx = np.gradient(h)
        k = r * 0.45
        nx, ny, nz = -gx * k, -gy * k, np.ones_like(h)
        nrm = np.sqrt(nx * nx + ny * ny + nz * nz)
        lam = np.clip((nx * -0.5 + ny * -0.6 + nz * 0.62) / nrm, 0, 1) ** 1.2
        col = BLUE_D[None, None, :] + (BLUE - BLUE_D)[None, None, :] * lam[..., None]
        col += (np.clip((lam - 0.7) / 0.3, 0, 1) ** 2)[..., None] * (WHITE - col) * 0.9
        col = np.clip(col, 0, 255).astype(np.uint8)

        edge = Image.new("RGBA", size, (18, 60, 92, 255)); edge.putalpha(ring)
        body = Image.fromarray(col, "RGB").convert("RGBA"); body.putalpha(m)
        layer.alpha_composite(edge)
        layer.alpha_composite(body)
        # specular dots
        d2 = ImageDraw.Draw(layer)
        for j in range(2):
            hx = cx + rng.uniform(-r * 0.35, r * 0.1)
            hy = cy - rng.uniform(r * 0.15, r * 0.45)
            hr = r * rng.uniform(0.07, 0.12)
            d2.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(235, 252, 255, 220))
    return layer


def catmull(pts, samples=14):
    if len(pts) < 3:
        return list(pts)
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(p) - 3):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    out.append(pts[-1])
    return out


def ribbon(d, pts, w0, w1, colour, alpha):
    left, right = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        t = i / max(1, n - 1)
        w = w0 + (w1 - w0) * t
        a = pts[min(n - 1, i + 1)]
        b = pts[max(0, i - 1)]
        ang = math.atan2(a[1] - b[1], a[0] - b[0]) + math.pi / 2
        left.append((p[0] + math.cos(ang) * w / 2, p[1] + math.sin(ang) * w / 2))
        right.append((p[0] - math.cos(ang) * w / 2, p[1] - math.sin(ang) * w / 2))
    d.polygon(left + right[::-1], fill=rgb(colour) + (alpha,))


def tendrils(size, px, seed=0, colour=EDGE, core=MID, width=None, count=14, alpha=255):
    """Tapered vines with a lighter core — wide where they leave the mass, hair thin at the tip."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    w = width or max(6, int(px * 0.030))
    for i in range(count):
        start = (rng.uniform(-size[0] * 0.1, size[0] * 1.1), rng.uniform(-size[1] * 0.1, size[1] * 1.1))
        ang = rng.uniform(0, 2 * math.pi)
        pts = [start]
        for _ in range(int(rng.integers(3, 6))):
            ang += rng.uniform(-1.1, 1.1)
            ln = rng.uniform(px * 0.25, px * 0.75)
            pts.append((pts[-1][0] + math.cos(ang) * ln, pts[-1][1] + math.sin(ang) * ln))
        smooth = catmull(pts, 16)
        ribbon(d, smooth, w * rng.uniform(0.8, 1.4), w * 0.16, colour, alpha)
        ribbon(d, smooth, w * rng.uniform(0.45, 0.85), w * 0.06, core, alpha)
    return layer


def gloss(mask, px, seed=0, count=34):
    """Hard white speculars sitting on the top edge of the mass — the wet look."""
    arr = np.asarray(mask)
    h, w = arr.shape
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    cols = np.nonzero(arr.any(axis=0))[0]
    if cols.size == 0:
        return layer
    for _ in range(count):
        x = int(rng.choice(cols)) + int(rng.uniform(-px * 0.01, px * 0.01))
        col = arr[:, np.clip(x, 0, w - 1)]
        ys = np.nonzero(col)[0]
        if ys.size == 0:
            continue
        y = int(ys[0] + rng.uniform(px * 0.02, px * 0.10))
        rw = px * rng.uniform(0.010, 0.030)
        rh = px * rng.uniform(0.004, 0.011)
        d.ellipse([x - rw, y - rh, x + rw, y + rh], fill=(255, 255, 255, int(rng.uniform(180, 240))))
    layer = layer.filter(ImageFilter.GaussianBlur(max(1, px * 0.004)))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    return layer


def droplets(size, px, seed=0, count=9):
    """Stray slime balls thrown off the mass."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    rng = np.random.default_rng(seed)
    for i in range(count):
        cx, cy = rng.uniform(0.05, 0.95) * size[0], rng.uniform(0.1, 0.95) * size[1]
        r = px * rng.uniform(0.018, 0.045)
        d.ellipse([cx - r, cy - r * rng.uniform(0.8, 1.2), cx + r, cy + r * rng.uniform(0.8, 1.2)], fill=255)
        if rng.random() < 0.5:
            d.line([(cx, cy + r * 0.6), (cx, cy + r * 2.4)], fill=255, width=int(r * 0.6))
    m = m.filter(ImageFilter.GaussianBlur(r * 0.6)).point(lambda v: 255 if v > 60 else 0)
    body = Image.fromarray(shade(m, px * 0.5), "RGB").convert("RGBA")
    body.putalpha(m)
    ring = ImageChops.subtract(grow(m, px * 0.4, 0.03), m)
    edge = Image.new("RGBA", size, rgb(EDGE) + (255,))
    edge.putalpha(ring)
    layer.alpha_composite(edge)
    layer.alpha_composite(body)
    return layer


# ------------------------------------------------------------------ builds


def banner(w=2560, h=1440):
    px = round(h * 0.30)
    size = (w, h)
    mask = run("ASHTYN", px, size)
    # keep the mass inside the safe band plus a little bleed
    band_top, band_bot = h * 0.3528, h * 0.6468
    ys, xs = np.nonzero(np.asarray(mask) > 0)
    if ys.size:
        top, bot, left, right = ys.min(), ys.max(), xs.min(), xs.max()
        target_h = (band_bot - band_top) * 1.06
        scale = min(target_h / max(1, bot - top), (w * 0.88) / max(1, right - left))
        if abs(scale - 1) > 0.01:
            mask = mask.resize((max(1, int(mask.width * scale)), max(1, int(mask.height * scale))), Image.LANCZOS)
    ys, xs = np.nonzero(np.asarray(mask) > 0)
    ox, oy = int(w / 2 - (xs.min() + xs.max()) / 2), int((band_top + band_bot) / 2 - (ys.min() + ys.max()) / 2)
    placed = Image.new("L", size, 0)
    placed.paste(mask, (ox, oy))

    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    canvas.alpha_composite(tendrils(size, px, seed=3, alpha=210, count=16))
    canvas.alpha_composite(tendrils(size, px, seed=8, colour=PALE // 1, core=PALE, width=max(3, int(px * 0.008)),
                                    count=10, alpha=170))

    edge = grow(placed, px, 0.020)
    ring = ImageChops.subtract(edge, placed)
    o_layer = Image.new("RGBA", size, rgb(EDGE) + (255,))
    o_layer.putalpha(ring)
    canvas.alpha_composite(o_layer)

    body = Image.fromarray(shade(placed, px), "RGB").convert("RGBA")
    body.putalpha(placed)
    canvas.alpha_composite(body)
    canvas.alpha_composite(gloss(placed, px, seed=5))

    canvas.alpha_composite(blob_layer(size, [
        (w * 0.235, h * 0.235, px * 0.16, 11),
        (w * 0.300, h * 0.190, px * 0.10, 12),
        (w * 0.700, h * 0.300, px * 0.13, 13),
        (w * 0.735, h * 0.760, px * 0.09, 14),
        (w * 0.470, h * 0.845, px * 0.075, 15),
    ]))
    canvas.alpha_composite(tendrils(size, px, seed=21, alpha=120, count=4, width=max(3, int(px * 0.010))))
    canvas.alpha_composite(droplets(size, px, seed=9, count=10))
    return canvas.convert("RGB")


def twitch(w=1200, h=480):
    img = banner(w, h)
    return img


def avatar(size=1024):
    px = round(size * 0.52)
    mask = run("A", px, (size, size))
    ys, xs = np.nonzero(np.asarray(mask) > 0)
    ox, oy = int(size / 2 - (xs.min() + xs.max()) / 2), int(size * 0.52 - (ys.min() + ys.max()) / 2)
    placed = Image.new("L", (size, size), 0)
    placed.paste(mask, (ox, oy))

    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    canvas.alpha_composite(tendrils((size, size), px, seed=31, alpha=200, count=7))

    edge = grow(placed, px, 0.024)
    ring = ImageChops.subtract(edge, placed)
    o_layer = Image.new("RGBA", (size, size), rgb(EDGE) + (255,))
    o_layer.putalpha(ring)
    canvas.alpha_composite(o_layer)

    body = Image.fromarray(shade(placed, px), "RGB").convert("RGBA")
    body.putalpha(placed)
    canvas.alpha_composite(body)
    canvas.alpha_composite(gloss(placed, px, seed=6, count=22))
    canvas.alpha_composite(blob_layer((size, size), [(size * 0.76, size * 0.30, px * 0.14, 41),
                                                     (size * 0.24, size * 0.78, px * 0.10, 42)]))
    return canvas.convert("RGB")


def export():
    LAYERS.mkdir(exist_ok=True)
    t0 = time.time()
    banner().save(OUT / "youtube-banner-slime-2560x1440.png")
    twitch().save(OUT / "twitch-banner-slime-1200x480.png")
    a = avatar()
    a.save(OUT / "profile-slime-1024.png")
    a.resize((800, 800), Image.LANCZOS).save(OUT / "profile-slime-800.png")
    a.resize((256, 256), Image.LANCZOS).save(OUT / "profile-slime-256.png")
    print(f"slime set in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    if "probe" in sys.argv:
        LAYERS.mkdir(exist_ok=True)
        t0 = time.time()
        banner(1500, 844).save(LAYERS / "_slime_banner.jpg", quality=88)
        avatar(700).save(LAYERS / "_slime_avatar.jpg", quality=88)
        print(f"probe {time.time() - t0:.1f}s")
    else:
        export()
