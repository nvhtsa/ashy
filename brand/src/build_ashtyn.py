"""ASHTYN — warped chrome identity.

Real letterforms (Anton: correctly drawn curves and fit), carried through a
treatment that belongs to this brand only:

  1. arc warp        — the word bows, so it never sits like plain type
  2. lean            — the top of each letter opens out, the baseline tightens
  3. one slice break — a single thin band shifted, the deliberate error
  4. chrome ramp     — polished metal lit by a violet room
  5. ghost plate     — violet duplicate split a few pixels behind

    python brand/src/build_ashtyn.py [outdir]
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")
ANTON = os.path.join(FONTS, "Anton-Regular.ttf")
MONO = os.path.join(FONTS, "SpaceMono-Regular.ttf")

WHITE = (247, 245, 250)
BLACK = (7, 5, 11)

YT_W, YT_H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
BAND_L, BAND_T = (YT_W - SAFE_W) // 2, (YT_H - SAFE_H) // 2


# -------------------------------------------------------------------- typework
def set_word(text, cap, tracking=0.02, font=ANTON):
    f = ImageFont.truetype(font, int(cap * 1.6))
    adv = [f.getlength(c) + tracking * cap for c in text]
    W, H = int(sum(adv)) + int(cap), int(cap * 2.4)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    x, base = int(cap * 0.5), int(cap * 1.9)
    for c, a in zip(text, adv):
        d.text((x, base), c, font=f, fill=255, anchor="ls")
        x += a
    bb = img.getbbox()
    m = img.crop(bb)
    s = cap / m.height
    return m.resize((max(1, int(m.width * s)), int(round(cap))), Image.LANCZOS)


def warp(mask, arc=0.0, lean=0.0, slice_shift=0.0):
    a = np.asarray(mask).astype(np.float32)
    h, w = a.shape
    xs = np.arange(w)[None, :]
    ys = np.arange(h)[:, None]
    cols = np.broadcast_to(xs, (h, w))

    if arc:
        dy = (arc * h * np.sin(np.pi * xs / max(w - 1, 1))).astype(np.int32)
        a = a[np.clip(ys - dy, 0, h - 1), cols]

    if lean:
        cx = (w - 1) / 2.0
        spread = 1.0 + lean * (1.0 - (ys / max(h - 1, 1)))
        src_x = np.clip(cx + (xs - cx) / spread, 0, w - 1).astype(np.int32)
        a = a[ys, src_x]

    if slice_shift:
        out = a.copy()
        y0 = int(h * 0.72)
        y1 = y0 + max(2, int(h * 0.012))
        sh = max(2, int(w * slice_shift))
        out[y0:y1] = np.roll(a[y0:y1], sh, axis=1)
        out[y0:y1, :sh] = 0
        a = out

    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L")


def chrome(mask):
    """Polished metal: bright horizon just above centre, deep shoulders."""
    w, h = mask.size
    stops = [(0.00, (238, 238, 246)), (0.10, (96, 94, 110)), (0.22, (252, 252, 255)),
             (0.34, (58, 54, 72)), (0.46, (255, 255, 255)), (0.50, (208, 206, 222)),
             (0.54, (72, 68, 88)), (0.66, (232, 230, 242)), (0.80, (54, 50, 68)),
             (0.92, (198, 196, 212)), (1.00, (36, 32, 46))]
    ys = np.linspace(0, 1, h)
    ramp = np.zeros((h, 3), np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (ys >= p0) & (ys <= p1)
        t = ((ys[m] - p0) / max(p1 - p0, 1e-6))[:, None]
        ramp[m] = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    arr = np.repeat(ramp[:, None, :], w, axis=1)

    strength = (1.0 - np.linspace(0, 1, w))[None, :] ** 3
    arr[..., 0] += strength * 58
    arr[..., 2] += strength * 104

    a = np.asarray(mask).astype(np.float32) / 255.0
    return Image.fromarray(np.dstack([np.clip(arr, 0, 255), a * 255]).astype(np.uint8), "RGBA")


def tint(alpha_mask, color, alpha=255):
    a = np.asarray(alpha_mask)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = color
    out[..., 3] = (a.astype(np.float32) * alpha / 255.0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def ground(w, h, seed=5):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.5, h * 0.52
    r = np.sqrt(((xx - cx) / (w * 0.55)) ** 2 + ((yy - cy) / (h * 0.65)) ** 2)
    glowv = np.clip(1 - r, 0, 1) ** 2.6
    base = np.zeros((h, w, 3), np.float32)
    base[..., 0], base[..., 1], base[..., 2] = BLACK
    base[..., 0] += glowv * 78
    base[..., 1] += glowv * 20
    base[..., 2] += glowv * 140
    rng = np.random.default_rng(seed)
    base += rng.normal(0, 1.8, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def place(canvas, mask, x, y, split=10, glow_radius=45):
    """Drop the plate: halo, split violet ghosts, then the chrome on top."""
    halo = tint(mask, (150, 60, 255), 150).filter(ImageFilter.GaussianBlur(glow_radius))
    canvas.alpha_composite(halo, (x, y))
    canvas.alpha_composite(tint(mask, (170, 90, 255), 120), (x - split, y))
    canvas.alpha_composite(tint(mask, (96, 30, 210), 120), (x + split, y))
    canvas.alpha_composite(chrome(mask), (x, y))


def fit(mask, max_w, max_h):
    s = min(max_w / mask.width, max_h / mask.height)
    return mask.resize((max(1, int(mask.width * s)), max(1, int(mask.height * s))), Image.LANCZOS)


# ----------------------------------------------------------------------- pages
def banner(outdir, master):
    canvas = ground(YT_W, YT_H).convert("RGBA")
    m = fit(master, SAFE_W * 0.94, SAFE_H * 0.80)
    x, y = (YT_W - m.width) // 2, BAND_T + int((SAFE_H - m.height) / 2) - 26
    place(canvas, m, x, y, split=9, glow_radius=52)

    meta = set_word("ASHTYN   /   EST. 2026   /   EDITION 01", 22, 0.30, MONO)
    meta_x = (YT_W - meta.width) // 2
    canvas.alpha_composite(tint(meta, WHITE, 120), (meta_x, BAND_T + SAFE_H - 34))

    canvas.convert("RGB").save(os.path.join(outdir, "youtube-banner-2560x1440.png"))

    guide = canvas.convert("RGB").copy()
    gd = ImageDraw.Draw(guide)
    gd.rectangle([BAND_L, BAND_T, BAND_L + SAFE_W, BAND_T + SAFE_H], outline=(255, 60, 90), width=4)
    guide.save(os.path.join(outdir, "_check-safe-band.png"))
    return m.size


def avatar(outdir):
    S = 1024
    canvas = ground(S, S, seed=9).convert("RGBA")
    m = set_word("A", int(S * 0.62))          # no warp: the counter must stay true
    place(canvas, m, (S - m.width) // 2, (S - m.height) // 2, split=7, glow_radius=30)
    for s in (1024, 800, 512, 256):
        canvas.convert("RGB").resize((s, s), Image.LANCZOS).save(
            os.path.join(outdir, "profile-%d.png" % s))


def panel(outdir, w, h, name, cap_ratio=0.42):
    canvas = ground(w, h, seed=17).convert("RGBA")
    m = set_word("ASHTYN", int(h * cap_ratio), 0.02)
    m = warp(m, arc=0.07, lean=0.10, slice_shift=0.004)
    m = fit(m, w * 0.90, h * 0.62)
    place(canvas, m, (w - m.width) // 2, int(h * 0.5 - m.height / 2),
          split=max(4, w // 130), glow_radius=max(20, h // 24))
    canvas.convert("RGB").save(os.path.join(outdir, name))


def run(outdir):
    os.makedirs(outdir, exist_ok=True)
    master = warp(set_word("ASHTYN", 900, 0.02), arc=0.075, lean=0.12, slice_shift=0.003)
    size = banner(outdir, master)
    avatar(outdir)
    panel(outdir, 1200, 480, "twitch-banner-1200x480.png")
    panel(outdir, 1500, 500, "twitter-header-1500x500.png")
    print("banner wordmark", size, "-> set written to", outdir)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "export", "ashtyn"))
