"""Inked set: symmetrical, hand-drawn-by-code headers.

The language: bone paper, heavy black linework, screen-tone shading, a portal
composition mirrored down the centre line, fangs, eyes, chain, one crimson.

Drawn, not filtered: curves are parametric, strokes carry a little jitter so they
read as pen, and the whole thing is finished with grain.

    python brand/src/build_ink.py probe     # quick half-size look
    python brand/src/build_ink.py           # full export set
"""
import math
import pathlib
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BRAND = pathlib.Path(__file__).resolve().parent.parent
OUT = BRAND / "export"
LAYERS = pathlib.Path(__file__).resolve().parent / "layers"

BOLD = BRAND / "fonts" / "BricolageGrotesque-Bold.ttf"
SEMI = BRAND / "fonts" / "BricolageGrotesque-SemiBold.ttf"

INK = (10, 10, 11)
PAPER = (240, 236, 226)
RED = (212, 18, 34)
RED_DEEP = (122, 8, 18)
WHITE = (250, 248, 242)


# ------------------------------------------------------------------ curves


def qbez(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def cbez(p0, p1, p2, p3, n=56):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def catenary(p0, p1, sag, n=70):
    return [(p0[0] + (p1[0] - p0[0]) * t,
             p0[1] + (p1[1] - p0[1]) * t + sag * math.sin(math.pi * t))
            for t in (i / n for i in range(n + 1))]


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=36):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + (rx * math.cos(a)) * c - (ry * math.sin(a)) * s,
             cy + (rx * math.cos(a)) * s + (ry * math.sin(a)) * c)
            for a in (2 * math.pi * i / n for i in range(n))]


def wobble(pts, amp=1.6, seed=0):
    rng = np.random.default_rng(seed)
    return [(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)) for x, y in pts]


def stroke(draw, pts, colour=INK, width=4, close=False, jitter=1.2, seed=0):
    seq = wobble(pts, jitter, seed)
    draw.line(seq + ([seq[0]] if close else []), fill=colour, width=width, joint="curve")


# ------------------------------------------------------------------ anatomy


def teeth_row(draw, x0, x1, y, depth, count, down=True, colour=WHITE, seed=0):
    """A row of fangs rooted on `y`. Tips point away from the root when `down`."""
    rng = np.random.default_rng(seed)
    s = 1 if down else -1
    step = (x1 - x0) / count
    for i in range(count):
        cx = x0 + step * (i + 0.5)
        half = step * 0.46
        ln = depth * (0.62 + 0.38 * rng.random())
        draw.polygon([(cx - half, y), (cx + half, y),
                      (cx + half * 0.14, y + s * ln), (cx - half * 0.14, y + s * ln)],
                     fill=colour)


def teeth_col(draw, y0, y1, x, depth, count, right=True, colour=WHITE, seed=0):
    """Fangs rooted on a vertical edge."""
    rng = np.random.default_rng(seed)
    s = 1 if right else -1
    step = (y1 - y0) / count
    for i in range(count):
        cy = y0 + step * (i + 0.5)
        half = step * 0.46
        ln = depth * (0.62 + 0.38 * rng.random())
        draw.polygon([(x, cy - half), (x, cy + half), (x + s * ln, cy + half * 0.14), (x + s * ln, cy - half * 0.14)],
                     fill=colour)


def socket(draw, cx, cy, r, seed=1, rim=18):
    """Irregular black mass behind an eye. Without it the eye floats on paper."""
    rng = np.random.default_rng(seed)
    pts = []
    for i in range(46):
        a = 2 * math.pi * i / 46
        rr = r * (0.78 + 0.34 * rng.random())
        pts.append((cx + math.cos(a) * rr * 1.35, cy + math.sin(a) * rr))
    draw.polygon(pts, fill=INK)


def eye(draw, cx, cy, w, h, look=-1.0, seed=2):
    corner_l, corner_r = (cx - w / 2, cy), (cx + w / 2, cy)
    upper = cbez(corner_l, (cx - w * 0.22, cy - h * 1.25), (cx + w * 0.26, cy - h * 1.10), corner_r)
    lower = cbez(corner_l, (cx - w * 0.18, cy + h * 0.66), (cx + w * 0.24, cy + h * 0.60), corner_r)
    outline = upper + lower[::-1]
    draw.polygon(outline, fill=PAPER)
    stroke(draw, outline, INK, max(5, round(h * 0.075)), close=True, seed=seed)

    ix = cx + w * 0.14 * look
    ir = w * 0.28
    draw.ellipse([ix - ir, cy - ir, ix + ir, cy + ir], fill=RED)
    for k in range(20):
        a = 2 * math.pi * k / 20
        stroke(draw, [(ix + math.cos(a) * ir * 0.42, cy + math.sin(a) * ir * 0.42),
                      (ix + math.cos(a) * ir * 0.95, cy + math.sin(a) * ir * 0.95)],
               RED_DEEP, max(1, round(ir * 0.05)), jitter=0.6)
    stroke(draw, ellipse_pts(ix, cy, ir, ir, 0, 48), INK, max(4, round(ir * 0.22)), close=True, seed=seed)
    pr = ir * 0.46
    draw.ellipse([ix - pr, cy - pr, ix + pr, cy + pr], fill=INK)
    g = max(3, round(ir * 0.12))
    draw.ellipse([ix - ir * 0.46, cy - ir * 0.58, ix - ir * 0.46 + g, cy - ir * 0.58 + g], fill=WHITE)

    for i in range(8):
        t = 0.14 + 0.72 * i / 7
        bx, by = upper[int(t * (len(upper) - 1))]
        a = -math.pi / 2 + (t - 0.5) * 1.7
        ln = h * (0.75 + 0.35 * math.sin(math.pi * t))
        stroke(draw, [(bx, by), (bx + math.cos(a) * ln, by + math.sin(a) * ln)],
               INK, max(4, round(h * 0.07)), seed=seed + i)


def chain(draw, p0, p1, sag, link=(60, 34), width=9, count=16):
    pts = catenary(p0, p1, sag)
    for i in range(count):
        t = i / (count - 1)
        idx = min(len(pts) - 1, int(t * (len(pts) - 1)))
        cx, cy = pts[idx]
        n0, n1 = pts[max(0, idx - 2)], pts[min(len(pts) - 1, idx + 2)]
        a = math.atan2(n1[1] - n0[1], n1[0] - n0[0])
        rx, ry = (link[0], link[1]) if i % 2 == 0 else (link[1], link[0])
        stroke(draw, ellipse_pts(cx, cy, rx, ry, a), INK, width, close=True, jitter=0.8)


def drip(draw, x, y_top, y_bottom, w):
    r = w * 0.34
    left = qbez((x - w / 2, y_top), (x - w * 0.16, y_bottom - r * 2.4), (x - r, y_bottom - r), 22)
    right = qbez((x + r, y_bottom - r), (x + w * 0.16, y_bottom - r * 2.4), (x + w / 2, y_top), 22)
    draw.polygon(left + right + [(x + w / 2, y_top), (x - w / 2, y_top)], fill=RED)
    draw.ellipse([x - r, y_bottom - 2 * r, x + r, y_bottom], fill=RED)
    stroke(draw, [(x + w * 0.30, y_top + w * 0.3), (x + w * 0.22, y_bottom - r * 1.5)],
           RED_DEEP, max(2, round(w * 0.09)), jitter=0.5)
    stroke(draw, [(x - w * 0.20, y_top + w * 0.4), (x - w * 0.16, y_bottom - r * 1.7)],
           (255, 232, 232), max(1, round(w * 0.07)), jitter=0.4)


# ------------------------------------------------------------------ texture


def fractal(size, scale, seed, octaves=4):
    rng = np.random.default_rng(seed)
    total = np.zeros((size[1], size[0]), np.float32)
    amp, norm, sc = 1.0, 0.0, scale
    for _ in range(octaves):
        small = rng.random((max(2, size[1] // sc), max(2, size[0] // sc))).astype(np.float32)
        up = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize(size, Image.BICUBIC),
                        np.float32) / 255
        total += up * amp
        norm += amp
        amp *= 0.5
        sc = max(2, sc // 2)
    return total / norm


def paper(size, seed=5):
    base = np.tile(np.array(PAPER, np.float32), (size[1], size[0], 1))
    base *= (0.968 + 0.064 * fractal(size, 3, seed, 3))[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def splatter(size, seed, centre, radius, count=60, colour=INK, rmax=8):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        a = rng.random() * 2 * math.pi
        dist = radius * (rng.random() ** 2.0)
        x = centre[0] + math.cos(a) * dist
        y = centre[1] + math.sin(a) * dist * 0.8
        r = 1 + rmax * (rng.random() ** 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*colour, 255))
    return layer


def halftone(size, centre, radius, cell, colour=INK, angle=0.5, strength=1.0):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ca, sa = math.cos(angle), math.sin(angle)
    span = int(radius * 2)
    for gy in range(-span, span, cell):
        for gx in range(-span, span, cell):
            dist = math.hypot(gx, gy) / radius
            if dist >= 1:
                continue
            r = cell * 0.52 * (1 - dist) ** 1.15 * strength
            if r > 0.5:
                x, y = centre[0] + gx * ca - gy * sa, centre[1] + gx * sa + gy * ca
                d.ellipse([x - r, y - r, x + r, y + r], fill=(*colour, 255))
    return layer


def glyph_mask(px, text="a", font=BOLD):
    f = ImageFont.truetype(str(font), px)
    box = f.getbbox(text)
    img = Image.new("L", (box[2] - box[0] + 40, box[3] - box[1] + 40), 0)
    ImageDraw.Draw(img).text((20 - box[0], 20 - box[1]), text, font=f, fill=255)
    return img.crop(img.getbbox())


def set_text(text, px, font=BOLD, tracking=0.0, colour=WHITE):
    f = ImageFont.truetype(str(font), px)
    adv = [f.getlength(c) + tracking for c in text]
    total = int(sum(adv) - tracking) + 8
    img = Image.new("RGBA", (total, int(px * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for c, a in zip(text, adv):
        d.text((x, px * 0.22), c, font=f, fill=(*colour, 255))
        x += a
    return img.crop(img.getbbox())


# ------------------------------------------------------------------ banner


def build_banner(w=2560, h=1440):
    half = w // 2
    band1 = round(h * 0.6468)
    portal_w = round(w * 0.30)
    px0, px1 = half - portal_w // 2, half + portal_w // 2
    ptop, pbot = round(h * 0.045), round(h * 1.02)
    canvas = paper((w, h)).convert("RGBA")

    # ---------------- flank (mirrored) ----------------
    flank = Image.new("RGBA", (half, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(flank)
    seam = half

    # spikes fanning out from behind the portal (start outside it, so nothing
    # crosses the mouth or the name)
    for i in range(5):
        y0 = h * (0.14 + 0.15 * i)
        edge = seam - portal_w * 0.56
        stroke(d, [(edge, y0), (edge - half * 0.52, y0 - h * (0.08 + 0.05 * i))],
               INK, 9, jitter=2.0, seed=i)

    # eye group
    socket(d, seam - 470, h * 0.30, 190, seed=11)
    eye(d, seam - 470, h * 0.30, 400, 210, seed=12)

    socket(d, seam - 900, h * 0.20, 150, seed=13)
    eye(d, seam - 900, h * 0.20, 310, 165, seed=14)

    socket(d, seam - 700, h * 0.68, 175, seed=15)
    eye(d, seam - 700, h * 0.68, 350, 180, seed=16)

    socket(d, seam - 1080, h * 0.50, 120, seed=17)
    eye(d, seam - 1080, h * 0.50, 250, 130, seed=18)

    # chains sagging in from the corner
    chain(d, (30, h * 0.10), (seam - 240, h * 0.34), h * 0.16, link=(58, 33), width=10, count=17)
    chain(d, (half * 0.30, h * 0.04), (seam - 120, h * 0.16), h * 0.07, link=(42, 24), width=7, count=11)

    # edge fangs: top hanging, bottom rising
    teeth_row(d, -20, seam - portal_w * 0.5, h * 0.035, h * 0.20, 8, down=True, seed=21)
    teeth_row(d, -20, seam - portal_w * 0.5, h * 0.995, h * 0.15, 7, down=False, seed=22)

    canvas.alpha_composite(flank, (0, 0))
    canvas.alpha_composite(flank.transpose(Image.FLIP_LEFT_RIGHT), (half, 0))

    # corner screen-tone + dirt
    canvas.alpha_composite(halftone((w, h), (w * 0.055, h * 0.95), h * 0.46, 15, strength=0.92))
    canvas.alpha_composite(halftone((w, h), (w * 0.945, h * 0.95), h * 0.46, 15, strength=0.92))
    canvas.alpha_composite(halftone((w, h), (w * 0.045, h * 0.06), h * 0.26, 13, strength=0.75))
    canvas.alpha_composite(halftone((w, h), (w * 0.955, h * 0.06), h * 0.26, 13, strength=0.75))
    canvas.alpha_composite(splatter((w, h), 4, (w * 0.30, h * 0.86), h * 0.30, 70, INK, 7))

    # ---------------- portal ----------------
    portal = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(portal)
    pd.rounded_rectangle([px0, ptop, px1, pbot], radius=portal_w // 2, fill=(*INK, 255))

    mould = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    md = ImageDraw.Draw(mould)
    md.rounded_rectangle([px0 - 30, ptop - 26, px1 + 30, pbot], radius=portal_w // 2,
                         outline=(*INK, 255), width=9)
    md.rounded_rectangle([px0 - 62, ptop - 56, px1 + 62, pbot], radius=portal_w // 2,
                         outline=(*INK, 235), width=4)
    canvas.alpha_composite(mould)
    canvas.alpha_composite(portal)

    # blood first, so the teeth grow over the roots of the drips
    blood = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blood)
    for i, (off, end, wid) in enumerate([(-360, 0.46, 44), (-210, 0.52, 58), (215, 0.44, 50), (375, 0.38, 34)]):
        drip(bd, half + off, ptop + 26, round(h * end), wid)
    # satellite droplets under the two long runs
    for x, y, r in ((half - 205, h * 0.555, 9), (half + 220, h * 0.475, 7), (half - 352, h * 0.495, 6)):
        bd.ellipse([x - r, y - r, x + r, y + r], fill=RED)
    canvas.alpha_composite(blood)

    # mouth fangs top and bottom of the portal
    mouth = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mdd = ImageDraw.Draw(mouth)
    teeth_row(mdd, px0, px1, ptop + 8, h * 0.16, 12, down=True, seed=31)
    teeth_row(mdd, px0, px1, pbot - 10, h * 0.12, 11, down=False, seed=32)
    # red wiped along the mouth
    mdd.rectangle([px0, ptop + 4, px1, ptop + 10], fill=RED)
    mdd.rectangle([px0, pbot - 16, px1, pbot - 10], fill=RED)
    canvas.alpha_composite(mouth)

    # ---------------- inside the portal ----------------
    inner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = glyph_mask(round(h * 0.24))
    gy = round(h * 0.415) - g.height // 2
    gx = half - g.width // 2
    glyph = Image.new("RGBA", g.size, (*WHITE, 255))
    glyph.putalpha(g)
    inner.alpha_composite(glyph, (gx, gy))

    # one drip off the counter, ending inside the glyph
    drips = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    drip(ImageDraw.Draw(drips), gx + g.width * 0.64, gy + g.height * 0.14, gy + g.height * 0.92, 26)
    inner.alpha_composite(drips)
    canvas.alpha_composite(inner)

    # name under the glyph, fully inside the safe band; no subline — the mouth does that job
    name = set_text("ASHTYN", round(h * 0.072), BOLD, tracking=9)
    nx, ny = half - name.width // 2, round(h * 0.560)
    canvas.alpha_composite(name, (nx, ny))

    # ---------------- finish ----------------
    arr = np.asarray(canvas.convert("RGB"), np.float32)
    arr *= (0.958 + 0.086 * fractal((w, h), 2, 9, 3))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ avatar


def build_avatar(size=1024):
    canvas = Image.new("RGBA", (size, size), (*INK, 255))
    d = ImageDraw.Draw(canvas)

    # fang ring: teeth pointing in from all four edges
    teeth_row(d, 0, size, size * 0.13, size * 0.16, 8, down=True, colour=WHITE, seed=41)
    teeth_row(d, 0, size, size * 0.87, size * 0.16, 8, down=False, colour=WHITE, seed=42)
    teeth_col(d, size * 0.20, size * 0.80, size * 0.13, size * 0.15, 4, right=True, colour=WHITE, seed=43)
    teeth_col(d, size * 0.20, size * 0.80, size * 0.87, size * 0.15, 4, right=False, colour=WHITE, seed=44)

    g = glyph_mask(round(size * 0.66))
    glyph = Image.new("RGBA", g.size, (*WHITE, 255))
    glyph.putalpha(g)
    gx, gy = size // 2 - g.width // 2, size // 2 - g.height // 2
    canvas.alpha_composite(glyph, (gx, gy))

    d = ImageDraw.Draw(canvas)
    drip(d, gx + g.width * 0.66, gy + g.height * 0.06, gy + g.height * 1.10, size * 0.040)

    arr = np.asarray(canvas.convert("RGB"), np.float32)
    arr *= (0.962 + 0.076 * fractal((size, size), 2, 12, 3))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ twitch


def build_twitch(w=1200, h=480):
    # 1200 x 480 is already 2.5:1, so the banner is composed at that ratio rather
    # than cropped from the 16:9 one (cropping cut the mouth in half).
    return build_banner(w * 2, h * 2).resize((w, h), Image.LANCZOS)


def export():
    LAYERS.mkdir(exist_ok=True)
    t0 = time.time()
    b = build_banner()
    b.save(OUT / "youtube-banner-ink-2560x1440.png")
    print(f"  banner  {time.time() - t0:.0f}s")

    a = build_avatar()
    a.save(OUT / "profile-ink-1024.png")
    a.resize((800, 800), Image.LANCZOS).save(OUT / "profile-ink-800.png")
    a.resize((256, 256), Image.LANCZOS).save(OUT / "profile-ink-256.png")

    build_twitch().save(OUT / "twitch-banner-ink-1200x480.png")
    print(f"  done    {time.time() - t0:.0f}s")


if __name__ == "__main__":
    if "probe" in sys.argv:
        LAYERS.mkdir(exist_ok=True)
        t0 = time.time()
        b = build_banner(1600, 900)
        b.save(LAYERS / "_ink_banner.png")
        b.resize((1180, 664), Image.LANCZOS).save(LAYERS / "_p_banner.jpg", quality=84)
        a = build_avatar(760)
        a.save(LAYERS / "_ink_avatar.png")
        a.save(LAYERS / "_p_avatar.jpg", quality=88)
        print(f"probe {time.time() - t0:.1f}s")
    else:
        export()
