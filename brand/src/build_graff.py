"""Notebook graffiti: chisel letters on ruled paper with margin doodles.

The language is a school notebook that got out of hand — ballpoint scribbles,
marker block letters with hatch shading, blue rules, a red margin, tape, and
little drawings crowding the edges.

The letters are type, but not typeset: each one is fattened, flared at the top,
sheared, scaled and rotated on its own, then overlapped by its neighbour. Every
stroke in the file — letter edge, crown, web — is displaced by a little noise so
nothing reads as vector.

    python brand/src/build_graff.py probe
    python brand/src/build_graff.py
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
HAND_CANDIDATES = [
    "C:/Windows/Fonts/Inkfree.ttf",
    "C:/Windows/Fonts/seguiscript.ttf",
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/comicbd.ttf",
]
HAND = next((p for p in HAND_CANDIDATES if pathlib.Path(p).exists()), str(BOLD))

PAPER = (252, 251, 247)
RULE = (168, 190, 210)
MARGIN = (222, 132, 132)
INK = (16, 16, 18)
PEN = (54, 68, 88)
RED = (188, 30, 42)

FONT_CACHE = {}


def font(path, px):
    key = (str(path), px)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = ImageFont.truetype(str(path), px)
    return FONT_CACHE[key]


# ------------------------------------------------------------------ paper


def notebook(size, rule=None, margin=True):
    w, h = size
    rule = rule or max(18, round(h / 34))
    img = Image.new("RGB", size, PAPER)
    d = ImageDraw.Draw(img)
    for y in range(rule, h, rule):
        d.line([(0, y + 1), (w, y + 1)], fill=(206, 214, 220), width=1)
        d.line([(0, y), (w, y)], fill=RULE, width=2)
    if margin:
        d.line([(w * 0.055, 0), (w * 0.055, h)], fill=MARGIN, width=3)
    arr = np.asarray(img, np.float32)
    rng = np.random.default_rng(3)
    arr = np.clip(arr * 0.985 + 4 + rng.normal(0, 3.2, (h, w, 1)).astype(np.float32), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def tape(size, pos, w, h, angle):
    w, h = int(w), int(h)
    layer = Image.new("RGBA", (max(2, w), max(2, h)), (224, 222, 212, 175))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, w - 1, h - 1], outline=(198, 196, 186, 200), width=2)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(layer, (int(pos[0] - layer.width / 2), int(pos[1] - layer.height / 2)))
    return canvas


def jit(pts, amp=1.8, seed=0):
    rng = np.random.default_rng(seed)
    return [(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)) for x, y in pts]


def sl(d, pts, colour, width, close=False, amp=1.7, seed=0):
    """A stroke that refuses to be straight."""
    p = jit(pts, amp, seed)
    d.line(p + ([p[0]] if close else []), fill=colour + (255,), width=width, joint="curve")


def pen_scribble(d, seed, box, loops=5, width=2):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = box
    for i in range(loops):
        pts = [(rng.uniform(x0, x1), rng.uniform(y0, y1))]
        for _ in range(int(rng.integers(5, 9))):
            pts.append((pts[-1][0] + rng.uniform(-1, 1) * (x1 - x0) * 0.3,
                        pts[-1][1] + rng.uniform(-1, 1) * (y1 - y0) * 0.35))
        d.line(pts, fill=PEN + (255,), width=width, joint="curve")


def web(d, corner, size, lines=7, width=2):
    cx, cy = corner
    sx = 1 if cx < size[0] / 2 else -1
    sy = 1 if cy < size[1] / 2 else -1
    ends = []
    for i in range(lines):
        a = (math.pi / 2) * (i / (lines - 1)) * 0.95
        ex, ey = cx + sx * math.cos(a) * size[0] * 0.17, cy + sy * math.sin(a) * size[1] * 0.24
        ends.append((ex, ey))
        sl(d, [(cx, cy), (ex, ey)], PEN, width, amp=2.2, seed=i)
    for r in (0.30, 0.55, 0.80):
        pts = [(cx + (ex - cx) * r, cy + (ey - cy) * r) for ex, ey in ends]
        sl(d, pts, PEN, width, amp=1.6)


# ------------------------------------------------------------------ lettering


def glyph_mask(px, ch):
    f = font(BOLD, px)
    box = f.getbbox(ch)
    img = Image.new("L", (box[2] - box[0] + 40, box[3] - box[1] + 40), 0)
    ImageDraw.Draw(img).text((20 - box[0], 20 - box[1]), ch, font=f, fill=255)
    return img.crop(img.getbbox())


def flare(mask, amount=0.16):
    """Widen the top of the letter — the chisel-mark tell."""
    arr = np.asarray(mask)
    h, w = arr.shape
    out = np.zeros_like(arr)
    xs = np.arange(w, dtype=np.float32)
    for y in range(h):
        s = 1.0 + amount * (0.5 - y / h)
        idx = np.clip(((xs - w / 2) / s + w / 2).astype(np.int32), 0, w - 1)
        out[y] = arr[y, idx]
    return Image.fromarray(out, "L")


def chisel(mask, shear=0.13):
    w, h = mask.size
    out_w = int(w + abs(shear) * h) + 4
    off = int(abs(shear) * h) if shear < 0 else 0
    return mask.transform((out_w, h), Image.AFFINE, (1, -shear, off, 0, 1, 0), resample=Image.BICUBIC)


def letter(ch, px, seed=0, angle=0.0, scale=1.0):
    rng = np.random.default_rng(seed)
    m = glyph_mask(px, ch)
    fat = max(3, round(px * 0.030) * 2 + 1)
    m = m.filter(ImageFilter.MaxFilter(fat))
    m = flare(m, 0.14)
    m = chisel(m, 0.14)
    if scale != 1.0:
        m = m.resize((max(1, int(m.width * scale)), max(1, int(m.height * scale))), Image.LANCZOS)

    pad = int(px * 0.20)
    size = (m.width + pad * 2, m.height + pad * 2)
    body = Image.new("RGBA", size, (0, 0, 0, 0))

    # paper-coloured gap around the letter: overlapping letters stay separated,
    # the way two marker strokes do on the same sheet
    grow = m.filter(ImageFilter.MaxFilter(max(3, round(px * 0.020) * 2 + 1)))
    ring = ImageChops.subtract(grow, m)
    ring_full = Image.new("L", size, 0)
    ring_full.paste(ring, (pad, pad))
    white = Image.new("RGBA", size, (251, 250, 245, 0))
    white.putalpha(ring_full.point(lambda v: 255 if v > 60 else 0))
    body.alpha_composite(white)

    # marker passes: same shape, three offsets — the doubled edge is the whole point
    for dx, dy in ((int(-px * 0.018), int(px * 0.012)), (int(px * 0.015), int(-px * 0.014)), (0, 0)):
        p = Image.new("RGBA", size, (0, 0, 0, 0))
        p.paste(Image.new("RGBA", m.size, INK + (255,)), (pad + dx, pad + dy), m)
        body.alpha_composite(p)

    # hatch inside
    inner = m.filter(ImageFilter.MinFilter(max(3, round(px * 0.032) * 2 + 1)))
    hatch = Image.new("RGBA", size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hatch)
    step = max(6, round(px * 0.030))
    for i in range(-size[1], size[0], step):
        hd.line([(i + pad, pad), (i + pad + size[1] * 0.45, pad + size[1])],
                fill=(0, 0, 0, 210), width=max(2, round(px * 0.012)))
    clip = Image.new("L", size, 0)
    clip.paste(inner, (pad, pad))
    hatch.putalpha(ImageChops.multiply(hatch.getchannel("A"), clip))
    body.alpha_composite(hatch)

    # white slash highlights
    hl = Image.new("RGBA", size, (0, 0, 0, 0))
    hw = ImageDraw.Draw(hl)
    for k in range(2):
        x0 = pad + m.width * (0.20 + 0.26 * k) + rng.uniform(-6, 6)
        hw.line([(x0, pad + m.height * 0.34), (x0 + m.width * 0.12, pad + m.height * 0.07)],
                fill=(250, 249, 244, 240), width=max(2, round(px * 0.018)))
    hl.putalpha(ImageChops.multiply(hl.getchannel("A"), clip))
    body.alpha_composite(hl)

    if angle:
        body = body.rotate(angle, resample=Image.BICUBIC, expand=True)
    return body.crop(body.getbbox())


def word(text, px, seed=0, tilt=-2.5, bow=0.03):
    rng = np.random.default_rng(seed)
    pieces = []
    for i, ch in enumerate(text):
        pieces.append(letter(ch, px, seed + i * 7,
                             angle=rng.uniform(-5, 5),
                             scale=rng.uniform(0.93, 1.08)))

    total_w = 0
    for p in pieces:
        total_w += p.width
    overlap = int(px * 0.04)
    total_w -= overlap * (len(pieces) - 1)
    total_h = max(p.height for p in pieces) + int(px * 0.2)
    canvas = Image.new("RGBA", (total_w + 2, total_h), (0, 0, 0, 0))

    x = 0
    for i, p in enumerate(pieces):
        t = i / max(1, len(pieces) - 1)
        y = int(total_h * 0.5 - p.height * 0.5) + int(px * bow * math.cos(math.pi * (t - 0.5)) * 2)
        y += int(rng.uniform(-0.03, 0.03) * px)
        canvas.alpha_composite(p, (x, max(0, y)))
        x += p.width - overlap
    canvas = canvas.crop(canvas.getbbox())
    if tilt:
        canvas = canvas.rotate(tilt, resample=Image.BICUBIC, expand=True)
    return canvas.crop(canvas.getbbox())


# ------------------------------------------------------------------ doodles


def doodle_crown(d, cx, cy, w, seed=0, width=6):
    h = w * 0.62
    pts = [(cx - w / 2, cy + h * 0.42), (cx - w / 2, cy - h * 0.2),
           (cx - w * 0.24, cy + h * 0.12), (cx, cy - h * 0.45),
           (cx + w * 0.24, cy + h * 0.12), (cx + w / 2, cy - h * 0.2),
           (cx + w / 2, cy + h * 0.42)]
    sl(d, pts + [pts[0]], INK, width, amp=1.6, seed=seed)
    for dx in (-w / 2, 0, w / 2):
        r = width * 0.9
        yy = cy - h * (0.34 if dx == 0 else 0.10)
        d.ellipse([cx + dx - r, yy - r, cx + dx + r, yy + r], fill=INK + (255,))


def doodle_star(d, cx, cy, r, seed=0, width=5, points=5):
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + math.pi * i / points
        rr = r if i % 2 == 0 else r * 0.44
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    sl(d, pts + [pts[0]], INK, width, amp=1.9, seed=seed)


def doodle_gem(d, cx, cy, w, seed=0, width=5):
    h = w * 0.9
    top = [(cx - w / 2, cy - h * 0.1), (cx - w * 0.28, cy - h * 0.42),
           (cx + w * 0.28, cy - h * 0.42), (cx + w / 2, cy - h * 0.1)]
    sl(d, top + [(cx, cy + h * 0.5)], INK, width, seed=seed)
    sl(d, [top[0], (cx, cy + h * 0.5), top[3]], INK, width, seed=seed + 1)
    sl(d, [(cx - w * 0.28, cy - h * 0.42), (cx - w * 0.14, cy - h * 0.1), (cx + w * 0.14, cy - h * 0.1),
           (cx + w * 0.28, cy - h * 0.42)], INK, width, seed=seed + 2)
    sl(d, [(cx - w * 0.14, cy - h * 0.1), (cx, cy + h * 0.5), (cx + w * 0.14, cy - h * 0.1)],
       INK, width, seed=seed + 3)


def doodle_cube(d, cx, cy, w, seed=0, width=5):
    h = w * 0.58
    sl(d, [(cx - w / 2, cy - h / 2), (cx, cy - h), (cx + w / 2, cy - h / 2), (cx, cy)], INK, width, close=True, seed=seed)
    sl(d, [(cx - w / 2, cy - h / 2), (cx - w / 2, cy + h / 2), (cx, cy + h), (cx, cy)], INK, width, seed=seed + 1)
    sl(d, [(cx, cy + h), (cx + w / 2, cy + h / 2), (cx + w / 2, cy - h / 2)], INK, width, seed=seed + 2)


def doodle_horn(d, cx, cy, r, flip=1, seed=0, width=6):
    pts = [(cx + flip * (r * math.sin(math.pi * 0.9 * (i / 23))) * 0.9,
            cy - r * 0.4 + r * 0.9 * (1 - math.cos(math.pi * 0.9 * (i / 23)))) for i in range(24)]
    sl(d, pts, INK, width, amp=1.4, seed=seed)


def doodle_arrow(d, p0, p1, bend, seed=0, width=6):
    pts = []
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    for i in range(20):
        t = i / 19
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * (mx + bend) + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * my + t * t * p1[1]))
    sl(d, pts, INK, width, amp=1.2, seed=seed)
    a = math.atan2(p1[1] - pts[-2][1], p1[0] - pts[-2][0])
    for s in (0.6, -0.6):
        sl(d, [p1, (p1[0] - math.cos(a + s) * width * 3.6, p1[1] - math.sin(a + s) * width * 3.6)],
           INK, width, amp=0.8)


def doodle_smiley(d, cx, cy, r, seed=0, width=6):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK + (255,), width=width)
    for dx in (-r * 0.34, r * 0.34):
        er = r * 0.18
        d.ellipse([cx + dx - er, cy - r * 0.18 - er, cx + dx + er, cy - r * 0.18 + er], fill=INK + (255,))
    d.arc([cx - r * 0.55, cy - r * 0.08, cx + r * 0.55, cy + r * 0.64], 20, 160, fill=INK + (255,), width=width)


def doodle_hand(d, cx, cy, s, seed=0, width=6):
    sl(d, [(cx, cy + s), (cx, cy - s * 0.75)], INK, width * 2, seed=seed)
    for dx in (-0.46, 0.42):
        sl(d, [(cx + s * dx, cy + s * 0.24), (cx + s * dx, cy - s * 0.18)], INK, width, seed=seed + 1)
    d.arc([cx - s * 0.52, cy - s * 0.02, cx + s * 0.52, cy + s * 0.62], 0, 180, fill=INK + (255,), width=width)


def doodle_spiral(d, cx, cy, r, seed=0, width=4):
    pts = []
    for i in range(56):
        t = i / 55
        a = t * 5.2 * math.pi
        pts.append((cx + math.cos(a) * r * t, cy + math.sin(a) * r * t))
    sl(d, pts, PEN, width, amp=0.8, seed=seed)


def mark_text(text, px, angle=0, colour=INK):
    f = font(HAND, px)
    box = f.getbbox(text)
    img = Image.new("RGBA", (box[2] - box[0] + 24, box[3] - box[1] + 24), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((12 - box[0], 12 - box[1]), text, font=f, fill=colour + (255,))
    if angle:
        img = img.rotate(angle, expand=True, resample=Image.BICUBIC)
    return img


# ------------------------------------------------------------------ finish


def finish(img, seed=1):
    w, h = img.size
    arr = np.asarray(img.convert("RGB"), np.float32)
    rng = np.random.default_rng(seed)
    arr = arr * 0.985 + rng.normal(0, 2.4, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ layouts


def banner(w=2560, h=1440):
    canvas = notebook((w, h)).convert("RGBA")
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    web(d, (w * 0.035, h * 0.03), (w, h), lines=8)
    web(d, (w * 0.965, h * 0.02), (w, h), lines=7)
    web(d, (w * 0.03, h * 0.975), (w, h), lines=7)
    pen_scribble(d, 5, (w * 0.015, h * 0.08, w * 0.20, h * 0.50), loops=4)
    pen_scribble(d, 9, (w * 0.80, h * 0.08, w * 0.99, h * 0.44), loops=4)
    pen_scribble(d, 13, (w * 0.04, h * 0.72, w * 0.26, h * 0.96), loops=3)
    pen_scribble(d, 17, (w * 0.72, h * 0.78, w * 0.99, h * 0.96), loops=3)
    canvas.alpha_composite(layer)

    # the tag, fitted to the safe band
    tag = word("ASHTYN", round(h * 0.30), seed=2)
    scale = min(w * 0.92 / tag.width, (h * 0.42) / tag.height)
    tag = tag.resize((max(1, round(tag.width * scale)), max(1, round(tag.height * scale))), Image.LANCZOS)
    tx, ty = round(w / 2 - tag.width / 2), round(h * 0.50 - tag.height / 2) - round(h * 0.02)
    canvas.alpha_composite(tag, (tx, ty))

    d2 = ImageDraw.Draw(canvas)
    # marker swoosh under the tag, with the flick at the end
    sw = [(tx + tag.width * 0.06 + i * tag.width * 0.028,
           ty + tag.height * 0.985 + math.sin(i * 0.55) * tag.height * 0.022) for i in range(31)]
    sl(d2, sw, INK, max(6, round(h * 0.007)), amp=2.0, seed=5)
    end = sw[-1]
    sl(d2, [end, (end[0] + w * 0.045, end[1] - h * 0.030)], INK, max(6, round(h * 0.007)), amp=1.2, seed=6)
    sl(d2, [(end[0] + w * 0.045, end[1] - h * 0.030), (end[0] + w * 0.012, end[1] - h * 0.026)],
       INK, max(6, round(h * 0.007)), amp=1.0, seed=7)
    # stray pen strokes over the lettering
    pen_scribble(d2, 44, (tx + tag.width * 0.25, ty, tx + tag.width * 0.95, ty + tag.height), loops=1, width=2)

    doodle_crown(d2, w * 0.255, h * 0.205, w * 0.050, seed=11)
    doodle_horn(d2, w * 0.700, h * 0.175, w * 0.028, flip=1, seed=12)
    doodle_horn(d2, w * 0.747, h * 0.196, w * 0.018, flip=1, seed=13)
    doodle_star(d2, w * 0.135, h * 0.635, w * 0.022, seed=14)
    doodle_star(d2, w * 0.925, h * 0.610, w * 0.017, seed=15)
    doodle_star(d2, w * 0.640, h * 0.905, w * 0.014, seed=16)
    doodle_gem(d2, w * 0.068, h * 0.690, w * 0.042, seed=17)
    doodle_cube(d2, w * 0.955, h * 0.775, w * 0.040, seed=18)
    doodle_arrow(d2, (w * 0.46, h * 0.885), (w * 0.575, h * 0.845), w * 0.02, seed=19)
    doodle_smiley(d2, w * 0.225, h * 0.845, w * 0.017, seed=20)
    doodle_hand(d2, w * 0.175, h * 0.885, w * 0.019, seed=21)
    doodle_spiral(d2, w * 0.845, h * 0.235, w * 0.020, seed=22)
    doodle_cube(d2, w * 0.055, h * 0.165, w * 0.030, seed=23)
    doodle_star(d2, w * 0.545, h * 0.155, w * 0.012, seed=24)
    doodle_arrow(d2, (w * 0.905, h * 0.925), (w * 0.985, h * 0.905), w * 0.015, seed=25)
    pen_scribble(d2, 51, (w * 0.30, h * 0.02, w * 0.52, h * 0.12), loops=2, width=2)
    pen_scribble(d2, 52, (w * 0.30, h * 0.90, w * 0.46, h * 0.98), loops=2, width=2)

    canvas.alpha_composite(mark_text("LOL!", round(h * 0.050), 8), (int(w * 0.795), int(h * 0.128)))
    canvas.alpha_composite(mark_text("ok.", round(h * 0.042), -7), (int(w * 0.086), int(h * 0.470)))
    canvas.alpha_composite(mark_text("sheesh", round(h * 0.038), -9), (int(w * 0.690), int(h * 0.885)))
    canvas.alpha_composite(mark_text("no.", round(h * 0.034), 6), (int(w * 0.905), int(h * 0.470)))

    canvas.alpha_composite(tape((w, h), (w * 0.055, h * 0.045), w * 0.10, h * 0.045, 38))
    canvas.alpha_composite(tape((w, h), (w * 0.945, h * 0.048), w * 0.09, h * 0.042, -34))
    return finish(canvas)


def twitch(w=1200, h=480):
    canvas = notebook((w, h), rule=max(14, round(h / 15))).convert("RGBA")
    d = ImageDraw.Draw(canvas)
    web(d, (w * 0.03, h * 0.05), (w, h), lines=5)
    web(d, (w * 0.97, h * 0.95), (w, h), lines=4)
    pen_scribble(d, 21, (w * 0.01, h * 0.55, w * 0.16, h * 0.98), loops=3)
    pen_scribble(d, 22, (w * 0.84, h * 0.06, w * 0.99, h * 0.45), loops=3)

    tag = word("ASHTYN", round(h * 0.40), seed=7, tilt=-2)
    tag = tag.resize((round(w * 0.66), round(tag.height * (w * 0.66) / tag.width)), Image.LANCZOS)
    canvas.alpha_composite(tag, (round(w * 0.13), round(h * 0.20)))

    d2 = ImageDraw.Draw(canvas)
    doodle_crown(d2, w * 0.205, h * 0.125, w * 0.040, seed=31, width=4)
    doodle_star(d2, w * 0.855, h * 0.26, w * 0.019, seed=32, width=4)
    doodle_gem(d2, w * 0.905, h * 0.70, w * 0.038, seed=33, width=4)
    doodle_smiley(d2, w * 0.085, h * 0.82, w * 0.015, seed=34, width=4)
    doodle_arrow(d2, (w * 0.62, h * 0.86), (w * 0.74, h * 0.80), w * 0.02, seed=35, width=5)
    canvas.alpha_composite(mark_text("LOL!", round(h * 0.075), 7), (int(w * 0.735), int(h * 0.55)))
    return finish(canvas)


def avatar(size=1024):
    canvas = notebook((size, size), rule=max(20, round(size / 20))).convert("RGBA")
    d = ImageDraw.Draw(canvas)
    web(d, (size * 0.04, size * 0.05), (size, size), lines=5)
    pen_scribble(d, 31, (size * 0.06, size * 0.08, size * 0.22, size * 0.32), loops=2)

    g = letter("A", round(size * 0.60), seed=41, angle=-3, scale=1.02)
    canvas.alpha_composite(g, (size // 2 - g.width // 2, round(size * 0.44) - g.height // 2))

    d2 = ImageDraw.Draw(canvas)
    doodle_crown(d2, size * 0.50, size * 0.175, size * 0.19, seed=42, width=max(5, size // 140))
    doodle_star(d2, size * 0.845, size * 0.285, size * 0.050, seed=43, width=max(4, size // 180))
    doodle_star(d2, size * 0.135, size * 0.700, size * 0.032, seed=44, width=max(3, size // 220))
    doodle_smiley(d2, size * 0.155, size * 0.855, size * 0.042, seed=45, width=max(4, size // 190))
    doodle_gem(d2, size * 0.855, size * 0.700, size * 0.085, seed=46, width=max(4, size // 200))
    canvas.alpha_composite(mark_text("!", round(size * 0.09), 12), (int(size * 0.755), int(size * 0.855)))
    return finish(canvas, seed=4)


def export():
    LAYERS.mkdir(exist_ok=True)
    t0 = time.time()
    banner().save(OUT / "youtube-banner-graff-2560x1440.png")
    twitch().save(OUT / "twitch-banner-graff-1200x480.png")
    a = avatar()
    a.save(OUT / "profile-graff-1024.png")
    a.resize((800, 800), Image.LANCZOS).save(OUT / "profile-graff-800.png")
    a.resize((256, 256), Image.LANCZOS).save(OUT / "profile-graff-256.png")
    print(f"graff set in {time.time() - t0:.1f}s — hand font: {pathlib.Path(HAND).name}")


if __name__ == "__main__":
    if "probe" in sys.argv:
        LAYERS.mkdir(exist_ok=True)
        t0 = time.time()
        banner(1600, 900).save(LAYERS / "_graff_banner.jpg", quality=86)
        avatar(700).save(LAYERS / "_graff_avatar.jpg", quality=88)
        twitch(1000, 400).save(LAYERS / "_graff_twitch.jpg", quality=86)
        print(f"probe {time.time() - t0:.1f}s — hand font: {pathlib.Path(HAND).name}")
    else:
        export()
