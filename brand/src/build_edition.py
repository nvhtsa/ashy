"""Edition identity — a print-shop rebrand set.

Nothing is drawn by hand: the wordmark is set in Anton, the second plate is
offset to fake misregistration, and the paper, grain and ink density are
generated. Two inks, one stock, no illustration.

    python brand/src/build_edition.py [outdir]
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")
ANTON = os.path.join(FONTS, "Anton-Regular.ttf")
MONO = os.path.join(FONTS, "SpaceMono-Regular.ttf")

PAPER = (238, 232, 219)
INK = (18, 16, 14)
ACID = (206, 255, 58)

YT_W, YT_H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
BAND_L, BAND_T = (YT_W - SAFE_W) // 2, (YT_H - SAFE_H) // 2


# ---------------------------------------------------------------- type setting
def _tracked(text, font_path, size, tracking):
    font = ImageFont.truetype(font_path, size)
    adv = [font.getlength(c) + tracking * size for c in text]
    w = int(sum(adv)) + size
    h = int(size * 1.7)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    x, base = size // 2, int(size * 1.25)
    for c, a in zip(text, adv):
        d.text((x, base), c, font=font, fill=255, anchor="ls")
        x += a
    bb = img.getbbox()
    return img.crop(bb) if bb else img


def word(text, cap_h, tracking=0.0):
    m = _tracked(text, ANTON, 700, tracking)
    s = cap_h / m.height
    return m.resize((max(1, int(round(m.width * s))), int(round(cap_h))), Image.LANCZOS)


def mono(text, size, tracking=0.26):
    return _tracked(text.upper(), MONO, size, tracking)


def ink(mask, color, density=0.96, jitter=0.10, seed=7):
    """One printed plate: flat colour with slightly uneven coverage."""
    a = np.asarray(mask).astype(np.float32) / 255.0
    if jitter:
        rng = np.random.default_rng(seed)
        n = rng.random(a.shape).astype(np.float32)
        n = np.asarray(
            Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
        ).astype(np.float32) / 255.0
        a = a * (1.0 - jitter + jitter * n)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = color
    out[..., 3] = np.clip(a * 255.0 * density, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def paper(w, h, base=PAPER, seed=11):
    canvas = np.zeros((h, w, 3), np.float32)
    canvas[..., 0], canvas[..., 1], canvas[..., 2] = base
    rng = np.random.default_rng(seed)
    fine = rng.normal(0, 1.3, (h, w)).astype(np.float32)
    coarse = rng.normal(0, 1.0, (max(2, h // 6), max(2, w // 6))).astype(np.float32)
    coarse = np.asarray(
        Image.fromarray(((coarse * 26) + 128).clip(0, 255).astype(np.uint8), "L")
        .resize((w, h), Image.BICUBIC)
    ).astype(np.float32) - 128.0
    shade = fine + coarse * 0.16
    for i in range(3):
        canvas[..., i] = np.clip(canvas[..., i] + shade, 0, 255)
    return Image.fromarray(canvas.astype(np.uint8), "RGB")


def paste(canvas, layer, cx, cy):
    canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def registration(d, x, y, s, color):
    d.ellipse([x - s, y - s, x + s, y + s], outline=color, width=max(2, s // 8))
    d.line([x - s * 1.7, y, x + s * 1.7, y], fill=color, width=max(2, s // 8))
    d.line([x, y - s * 1.7, x, y + s * 1.7], fill=color, width=max(2, s // 8))


def plates(canvas, mask, cx, cy, dx, dy):
    """Acid plate nudged off the black one — the registration error is the look."""
    paste(canvas, ink(mask, ACID, density=1.0, seed=3), cx + dx, cy + dy)
    paste(canvas, ink(mask, INK, density=0.97, seed=9), cx, cy)


# ------------------------------------------------------------------- the pages
def banner(outdir):
    canvas = paper(YT_W, YT_H).convert("RGBA")
    d = ImageDraw.Draw(canvas)

    cap = int(SAFE_H * 0.80)
    m = word("ASHTYN", cap, tracking=0.045)
    if m.width > SAFE_W * 0.94:
        s = SAFE_W * 0.94 / m.width
        m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
    plates(canvas, m, YT_W / 2, BAND_T + 12 + m.height / 2, 13, 9)

    rule_y = BAND_T + 360
    d.line([BAND_L + 30, rule_y, BAND_L + SAFE_W - 30, rule_y], fill=INK + (95,), width=2)
    meta = mono("streams / clips / edits      edition 01 · reprint 2026", 26, 0.24)
    paste(canvas, ink(meta, INK, density=0.85, jitter=0.05, seed=5), YT_W / 2, BAND_T + 394)

    # Marks sit outside the band: visible on desktop, cropped on phones.
    for x, y in ((BAND_L - 95, BAND_T - 95), (BAND_L + SAFE_W + 95, BAND_T - 95),
                 (BAND_L - 95, BAND_T + SAFE_H + 95), (BAND_L + SAFE_W + 95, BAND_T + SAFE_H + 95)):
        registration(d, x, y, 27, INK + (110,))

    for text, right in (("ashtyn — channel identity", False), ("reprint 2026", True)):
        lay = ink(mono(text, 24, 0.22), INK, density=0.55, jitter=0.04, seed=5)
        x = (YT_W - 120 - lay.width) if right else 120
        canvas.alpha_composite(lay, (x, 92))

    canvas.convert("RGB").save(os.path.join(outdir, "youtube-banner-2560x1440.png"))
    return canvas


def avatar(outdir):
    """An ink stamp, not a paper page: it has to hold at 32 pixels."""
    S = 1024
    canvas = paper(S, S, base=INK, seed=21).convert("RGBA")
    m = word("A", int(S * 0.54))
    # Paper-white letter on the ink field: a black letter would vanish into it,
    # and at 32px only a light form survives the circular mask.
    paste(canvas, ink(m, ACID, density=1.0, seed=3), S / 2 + 11, S / 2 + 8)
    paste(canvas, ink(m, PAPER, density=1.0, jitter=0.04, seed=9), S / 2, S / 2)
    for s in (1024, 800, 512, 256):
        canvas.convert("RGB").resize((s, s), Image.LANCZOS).save(
            os.path.join(outdir, "profile-%d.png" % s))


def panel(outdir, w, h, name, meta_text):
    canvas = paper(w, h, seed=33).convert("RGBA")
    d = ImageDraw.Draw(canvas)
    cap = int(h * 0.40)
    m = word("ASHTYN", cap, tracking=0.045)
    if m.width > w * 0.86:
        s = w * 0.86 / m.width
        m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
    plates(canvas, m, w / 2, h * 0.10 + m.height / 2, max(7, cap // 22), max(5, cap // 30))
    rule_y = h * 0.70
    d.line([(w - m.width) / 2, rule_y, (w + m.width) / 2, rule_y], fill=INK + (90,), width=2)
    meta = mono(meta_text, max(14, int(h * 0.042)), 0.24)
    paste(canvas, ink(meta, INK, density=0.85, jitter=0.05, seed=5), w / 2, h * 0.85)
    canvas.convert("RGB").save(os.path.join(outdir, name))


def run(outdir):
    os.makedirs(outdir, exist_ok=True)
    banner(outdir)
    avatar(outdir)
    panel(outdir, 1200, 480, "twitch-banner-1200x480.png",
          "live / streams / clips      edition 01")
    panel(outdir, 1500, 500, "twitter-header-1500x500.png",
          "ashtyn      edition 01 · reprint 2026")
    print("wrote set ->", outdir)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "export", "edition"))
