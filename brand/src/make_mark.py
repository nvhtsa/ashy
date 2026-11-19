"""Build the channel identity: a lowercase `a` whose counter is lit.

The mark is one letter with its enclosed counter filled in iris. Nothing else —
no brackets, no plate, no second glyph. This module renders the mark and the
`ashtyn` wordmark straight from the shipped SemiBold instance, so the exports
and the wordmark in the board are the same drawing.

    python brand/src/make_mark.py
"""
import pathlib
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
BRAND = ROOT.parent
OUT = BRAND / "export"
OUT.mkdir(exist_ok=True)
LAYERS = ROOT / "layers"

FONT = BRAND / "fonts" / "BricolageGrotesque-SemiBold.ttf"

CHARCOAL = (20, 18, 26)
SMOKE = (233, 229, 221)
IRIS = (155, 138, 240)
IRIS_INK = (111, 91, 208)


# ---------------------------------------------------------------- type + holes


def render_text(text, size, tracking=0.0):
    """Ink mask for `text`, tight-cropped. `tracking` is in em."""
    font = ImageFont.truetype(str(FONT), size)
    advances = [font.getlength(ch) + tracking * size for ch in text]
    total = sum(advances) - tracking * size
    asc, desc = font.getmetrics()

    pad = int(size * 0.6)
    canvas = Image.new("L", (int(total) + pad * 2, asc + desc + pad * 2), 0)
    draw = ImageDraw.Draw(canvas)
    x = pad
    for ch, adv in zip(text, advances):
        draw.text((x, pad + asc), ch, font=font, fill=255, anchor="ls")
        x += adv
    return canvas.crop(canvas.getbbox())


def hole_mask(mask):
    """Everything enclosed by ink: flood the background from the border, keep the rest."""
    # Work small: the counters are low-frequency shapes, so a 400px pass is exact
    # enough and keeps the Python flood fill quick.
    scale = 400 / max(mask.size)
    small = mask.resize(
        (max(1, round(mask.width * scale)), max(1, round(mask.height * scale))),
        Image.BOX,
    )
    free = np.asarray(small) <= 127

    padded = np.pad(free, 1, constant_values=True)
    seen = np.zeros_like(padded)
    height, width = padded.shape
    seen[0, 0] = True
    queue = deque([(0, 0)])
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < height and 0 <= nx < width and padded[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                queue.append((ny, nx))

    enclosed = free & ~seen[1:-1, 1:-1]
    if not enclosed.any():
        return Image.new("L", mask.size, 0)

    up = Image.fromarray((enclosed * 255).astype(np.uint8), "L").resize(mask.size, Image.BICUBIC)
    up = up.point(lambda v: 255 if v > 127 else 0).filter(ImageFilter.GaussianBlur(0.8))
    return up


def compose(mask, ink, counter):
    """RGBA glyph: `ink` for the strokes, `counter` for the enclosed holes."""
    holes = hole_mask(mask)
    rgb = np.empty((mask.height, mask.width, 3), dtype=np.uint8)
    rgb[...] = ink
    filled = np.asarray(holes) > 127
    rgb[filled] = counter
    alpha = np.where(filled, 255, np.asarray(mask)).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def fit(img, height=None, width=None):
    if width is not None:
        height = round(img.height * width / img.width)
    scale = height / img.height
    return img.resize((max(1, round(img.width * scale)), height), Image.LANCZOS)


def knockdown(rgba, rgb):
    """Single-colour cut: counters stay open, so it reads as a stencil, not a blob."""
    out = Image.new("RGBA", rgba.size, (*rgb, 0))
    out.putalpha(rgba.getchannel("A"))
    return out


# ---------------------------------------------------------------- compositions


def tile(size, background, ink, counter, fill):
    """Square avatar: mark optically centred, its ink at `fill` of the tile."""
    canvas = Image.new("RGBA", (size, size), (*background, 255))
    glyph = compose(render_text("a", 900), ink, counter)
    glyph = fit(glyph, height=round(size * fill))
    # an `a` sits its mass low-left; nudge so it looks centred, not measured-centred
    canvas.alpha_composite(glyph, ((size - glyph.width) // 2, round((size - glyph.height) / 2 + size * 0.012)))
    return canvas


def wordmark(height, ink, counter, tracking=-0.028):
    return compose(render_text("ashtyn", 900, tracking=tracking), ink, counter)


def plate(width, height, background, ink, counter, glow=None, word_width=0.39):
    canvas = Image.new("RGBA", (width, height), (*background, 255))
    if glow:
        yy, xx = np.mgrid[0:height, 0:width]
        d = np.sqrt(
            ((xx - width / 2) / (width * 0.52)) ** 2 + ((yy - height * 1.35) / (height * 3.1)) ** 2
        )
        g = np.clip(1 - d, 0, 1) ** 2 * glow[1]
        base = np.array(background, np.float32)
        rgb = (base[None, None, :] * (1 - g[..., None]) + np.array(glow[0], np.float32) * g[..., None])
        canvas = Image.fromarray(np.dstack([np.round(rgb), np.full((height, width, 1), 255)]).astype(np.uint8), "RGBA")
    word = wordmark(900, ink, counter)
    word = fit(word, width=round(width * word_width))
    canvas.alpha_composite(word, ((width - word.width) // 2, (height - word.height) // 2))
    return canvas


def mark_asset(size, ink, counter, margin):
    """Transparent mark with `margin` of the long side as breathing room."""
    glyph = compose(render_text("a", 900), ink, counter)
    side = round(size * (1 - 2 * margin))
    glyph = fit(glyph, height=side if glyph.height >= glyph.width else None,
                width=None if glyph.height >= glyph.width else side)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    return out


# ---------------------------------------------------------------- outputs


def export():
    tile(1024, CHARCOAL, SMOKE, IRIS, 0.54).save(OUT / "profile-dark-1024.png")
    tile(800, CHARCOAL, SMOKE, IRIS, 0.54).save(OUT / "profile-dark-800.png")
    tile(256, CHARCOAL, SMOKE, IRIS, 0.58).save(OUT / "profile-dark-256.png")
    tile(800, SMOKE, CHARCOAL, IRIS_INK, 0.54).save(OUT / "profile-light-800.png")

    logo = mark_asset(1024, SMOKE, IRIS, 0.13)
    logo.save(OUT / "logo-transparent-1024.png")
    knockdown(logo, (255, 255, 255)).save(OUT / "logo-white-1024.png")
    knockdown(logo, CHARCOAL).save(OUT / "logo-black-1024.png")

    mark = mark_asset(150, SMOKE, IRIS, 0.06)
    mark.save(OUT / "watermark-150.png")
    knockdown(mark, (255, 255, 255)).save(OUT / "watermark-150-white.png")

    plate(2560, 1440, SMOKE, CHARCOAL, IRIS_INK, word_width=0.40).save(
        OUT / "youtube-banner-light-2560x1440.png"
    )
    plate(2560, 1440, CHARCOAL, SMOKE, IRIS, word_width=0.40).save(
        OUT / "youtube-banner-dark-2560x1440.png"
    )
    plate(1200, 480, CHARCOAL, SMOKE, IRIS, glow=(IRIS, 0.16), word_width=0.46).save(
        OUT / "twitch-banner-1200x480.png"
    )

    for f in sorted(OUT.glob("*.png")):
        im = Image.open(f)
        a = np.asarray(im.getchannel("A")) if im.mode == "RGBA" else None
        extra = f"alpha {a.min()}/{a.max()} corner {a[2, 2]}" if a is not None else "opaque"
        print(f"  {f.name:34} {im.size} {im.mode:4} {extra}")


if __name__ == "__main__":
    export()
