"""Build the loud set: chrome mark inside a HUD composition.

The language is pulled from the sort of social-header work on Behance — a chrome
object as the hero, hard diagonal shards, technical overlay furniture (grid dots,
registration marks, rulers, microcopy), cropped display type bleeding off the
frame, and one saturated system colour against near-black.

Everything here is drawn: no stock, no photos. The object comes from
render_mark_3d.py with MATERIAL = "chrome", so it reflects a studio that only
exists in code.

    python brand/src/build_cyber.py            # hero still + banner + twitch + avatar set
    python brand/src/build_cyber.py probe 700  # quick half-size look
"""
import pathlib
import sys
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_mark as flat          # noqa: E402
import render_mark_3d as r3       # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
BRAND = ROOT.parent
OUT = BRAND / "export"
LAYERS = ROOT / "layers"

BOLD = BRAND / "fonts" / "BricolageGrotesque-Bold.ttf"
SEMI = BRAND / "fonts" / "BricolageGrotesque-SemiBold.ttf"
MONO_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/consolab.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]
MONO = next((p for p in MONO_CANDIDATES if pathlib.Path(p).exists()), None)

BLACK = np.array([10, 12, 20], np.float32) / 255
DEEP = np.array([6, 8, 14], np.float32) / 255
WHITE = (242, 247, 255)
CYAN = (53, 224, 255)
IRIS = (155, 138, 240)
HOT = (255, 45, 85)
STEEL = (150, 178, 196)

r3.MATERIAL = "chrome"


# ------------------------------------------------------------------ object


def object_rgba(res=1200, aa=2):
    """Chrome glyph, tight-cropped, with a neon counter and its own bloom."""
    premult, alpha = r3.render(res, aa)
    straight = np.where(alpha > 1e-4, premult / np.maximum(alpha, 1e-6), 0)
    rgba = np.dstack([np.clip(straight, 0, 1), np.clip(alpha, 0, 1)])
    obj = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")
    obj = obj.crop(obj.getchannel("A").getbbox())

    # the counter: cyan at the top of the bowl falling into iris, plus bloom
    alpha_img = obj.getchannel("A")
    holes = np.asarray(flat.hole_mask(alpha_img)) > 127
    if holes.any():
        ys, xs = np.nonzero(holes)
        cy, cx = ys.mean(), xs.mean()
        radius = max(6.0, np.sqrt(((ys - cy) ** 2 + (xs - cx) ** 2).max()))
        gy, gx = np.mgrid[0:obj.height, 0:obj.width].astype(np.float32)
        t = np.clip(((gy - (cy - radius)) / (2 * radius)), 0, 1)[..., None]
        grad = np.array(CYAN, np.float32)[None, None, :] * (1 - t) + np.array(IRIS, np.float32)[None, None, :] * t
        hot = np.exp(-(((gx - cx) ** 2 + (gy - (cy - radius * 0.15)) ** 2) / (2 * (radius * 0.55) ** 2)))

        arr = np.asarray(obj).astype(np.float32)
        arr[..., :3] = np.where(holes[..., None], np.clip(grad + hot[..., None] * 90, 0, 255), arr[..., :3])
        arr[..., 3] = np.where(holes, 255.0, arr[..., 3])
        obj = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    # bloom: soft light escaping the counter, drawn under the object
    glow = Image.new("RGBA", obj.size, (*CYAN, 0))
    mask = Image.fromarray((holes * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.GaussianBlur(obj.height * 0.02)).point(lambda v: int(v * 0.75))
    glow.putalpha(mask)
    out = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(obj)
    return out


def chromatic(obj, dx=-9, dy=5, colour=IRIS, alpha=90):
    """Offset coloured copy: the cheap scan-registration tell the style leans on."""
    layer = Image.new("RGBA", obj.size, (*colour, 0))
    layer.putalpha(obj.getchannel("A").point(lambda v: int(v * alpha / 255)))
    out = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    out.alpha_composite(layer, dest=(0, 0))
    return out, (dx, dy)


# ------------------------------------------------------------------ type


def text_mask(text, font_path, size, tracking=0.0):
    font = ImageFont.truetype(str(font_path), size)
    adv = [font.getlength(ch) + tracking * size for ch in text]
    total = sum(adv) - tracking * size
    asc, desc = font.getmetrics()
    pad = int(size * 0.35)
    canvas = Image.new("L", (max(1, int(total) + pad * 2), asc + desc + pad * 2), 0)
    draw = ImageDraw.Draw(canvas)
    x = pad
    for ch, a in zip(text, adv):
        draw.text((x, pad + asc), ch, font=font, fill=255, anchor="ls")
        x += a
    return canvas.crop(canvas.getbbox())


def shear(mask, k):
    w, h = mask.size
    out_w = w + int(abs(k) * h) + 2
    off = int(abs(k) * h) if k < 0 else 0
    return mask.transform((out_w, h), Image.AFFINE, (1, -k, off, 0, 1, 0), resample=Image.BICUBIC)


def display(text, size, colour, tracking=-0.03, k=0.0, alpha=255, font=BOLD):
    mask = text_mask(text, font, size, tracking)
    if k:
        mask = shear(mask, k)
    if alpha < 255:
        mask = mask.point(lambda v: int(v * alpha / 255))
    img = Image.new("RGBA", mask.size, (*colour, 0))
    img.putalpha(mask)
    return img


def mono(text, size, colour, tracking=0.16, alpha=255):
    if MONO:
        mask = text_mask(text, MONO, size, tracking)
    else:
        mask = text_mask(text, SEMI, size, tracking)
    if alpha < 255:
        mask = mask.point(lambda v: int(v * alpha / 255))
    img = Image.new("RGBA", mask.size, (*colour, 0))
    img.putalpha(mask)
    return img


# ------------------------------------------------------------------ furniture


def radial(arr, cx, cy, radius, colour, strength):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx) / radius) ** 2 + ((yy - cy) / radius) ** 2)
    g = np.clip(1 - d, 0, 1) ** 2.1 * strength
    return arr + np.array(colour, np.float32)[None, None, :] * g[..., None]


def halftone(size, cell, colour, alpha, region=None, curve=1.0):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = region or (0, 0, w, h)
    for gy in range(y0, y1, cell):
        for gx in range(x0, x1, cell):
            u = (gx - x0) / max(1, x1 - x0)
            v = (gy - y0) / max(1, y1 - y0)
            r = cell * 0.42 * (max(0.0, 1 - ((u - 0.5) ** 2 + (v - 0.5) ** 2) * 2.2) ** curve)
            if r > 0.4:
                draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(*colour, int(alpha * min(1, r / (cell * 0.3)))))
    return layer


def shards(size, colour, specs, alpha=40):
    """Hard parallelograms: (x, y, width, height, skew)."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for x, y, w, h, k in specs:
        pts = [(x + k * h, y), (x + w + k * h, y), (x + w, y + h), (x, y + h)]
        draw.polygon(pts, fill=(*colour, alpha))
        draw.line([pts[0], pts[1]], fill=(*colour, min(255, alpha * 4)), width=2)
    return layer


def dashed_arc(layer, box, start, end, colour, width=2, dash=14, gap=11):
    draw = ImageDraw.Draw(layer)
    a = start
    while a < end:
        draw.arc(box, a, min(a + dash, end), fill=colour, width=width)
        a += dash + gap


def ticks(draw, x0, x1, y, colour, step=40, long_every=4):
    for i, x in enumerate(range(x0, x1, step)):
        length = 14 if i % long_every == 0 else 7
        draw.line([(x, y), (x, y + length)], fill=colour, width=1)


def crosshair(draw, x, y, r, colour):
    draw.line([(x - r, y), (x + r, y)], fill=colour, width=1)
    draw.line([(x, y - r), (x, y + r)], fill=colour, width=1)


def grid_dots(size, step, colour, alpha, region, jitter=0.0, seed=3):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = region
    rng = np.random.default_rng(seed)
    for gy in range(y0, y1, step):
        for gx in range(x0, x1, step):
            if jitter and rng.random() < jitter:
                continue
            draw.rectangle([gx, gy, gx + 2, gy + 2], fill=(*colour, alpha))
    return layer


def barcode(size, colour, alpha=150):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    rng = np.random.default_rng(11)
    x = 0
    while x < w - 3:
        bw = int(rng.choice([2, 2, 3, 5, 8]))
        if rng.random() > 0.45:
            draw.rectangle([x, 0, x + bw, h], fill=(*colour, alpha))
        x += bw + int(rng.choice([2, 3, 4]))
    return layer


def scanlines(size, alpha=16, step=4):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha), width=1)
    return layer


def vignette(arr, strength=0.55):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = np.clip(1 - (d / 1.45) ** 2.2, 0, 1)[..., None]
    return arr * (1 - strength + strength * v)


def background(w, h, cyan_at=(0.22, 0.30), iris_at=(0.82, 0.86)):
    arr = np.tile(np.array(DEEP, np.float32), (h, w, 1))
    arr = radial(arr, w * cyan_at[0], h * cyan_at[1], max(w, h) * 0.55, (0.10, 0.42, 0.50), 0.85)
    arr = radial(arr, w * iris_at[0], h * iris_at[1], max(w, h) * 0.55, (0.26, 0.20, 0.52), 0.55)
    arr = vignette(arr, 0.6)
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ compositions


def banner(w=2560, h=1440, obj=None):
    obj = obj or object_rgba()
    canvas = background(w, h).convert("RGBA")

    shard_layer = shards(
        (w, h),
        WHITE,
        [(w * 0.02, h * 0.10, w * 0.30, h * 0.55, 0.20),
         (w * 0.62, h * 0.02, w * 0.16, h * 0.72, -0.26),
         (w * 0.86, h * 0.34, w * 0.22, h * 0.40, 0.14)],
        alpha=16,
    )
    canvas.alpha_composite(shard_layer)
    canvas.alpha_composite(shards((w, h), CYAN, [(w * 0.05, h * 0.62, w * 0.26, h * 0.05, 0.2),
                                                 (w * 0.68, h * 0.20, w * 0.14, h * 0.035, -0.22)], alpha=110))
    canvas.alpha_composite(shards((w, h), WHITE, [(w * 0.62, h * 0.10, w * 0.30, h * 0.02, -0.18)], alpha=150))
    canvas.alpha_composite(halftone((w, h), 16, CYAN, 44, region=(int(w * 0.46), 0, w, int(h * 0.60))))
    canvas.alpha_composite(halftone((w, h), 13, CYAN, 34, region=(0, int(h * 0.78), int(w * 0.34), h)))
    canvas.alpha_composite(grid_dots((w, h), 46, STEEL, 24, (0, 0, w, h), jitter=0.4))

    # display type cropped by the bottom edge: texture, not a second headline
    ghost = display("ASHTYN", round(h * 0.56), CYAN, tracking=-0.05, k=0.16, alpha=70)
    faint = display("ASHTYN", round(h * 0.56), WHITE, tracking=-0.05, k=0.16, alpha=20)
    canvas.alpha_composite(ghost, (int(-w * 0.05) + 16, int(h * 0.74) + 10))
    canvas.alpha_composite(faint, (int(-w * 0.05), int(h * 0.74)))
    # one hot mark, one screen only
    hotbar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(hotbar).rectangle([w * 0.715, h * 0.404, w * 0.755, h * 0.416], fill=(*HOT, 235))
    canvas.alpha_composite(hotbar)

    # ---- safe band 1546 x 423 (x 507..2053, y 508..931)
    band_y0, band_h = round(h * 0.3528), round(h * 0.2938)
    hud = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud)
    draw.line([(0, band_y0), (w, band_y0)], fill=(*STEEL, 40), width=1)
    ticks(draw, 0, w, band_y0 - 16, (*STEEL, 90))
    for cx in (w * 0.5 - 773, w * 0.5 + 773):
        draw.line([(cx, band_y0), (cx, band_y0 + band_h)], fill=(*CYAN, 26), width=1)

    # rings behind the object
    ox, oy, orad = round(w * 0.33), round(h * 0.50), round(h * 0.30)
    dashed_arc(hud, (ox - orad, oy - orad, ox + orad, oy + orad), -70, 250, (*CYAN, 120), width=2)
    draw.ellipse([ox - orad * 0.74, oy - orad * 0.74, ox + orad * 0.74, oy + orad * 0.74],
                 outline=(*WHITE, 40), width=1)
    for ang in range(0, 360, 30):
        a = np.radians(ang)
        px, py = ox + np.cos(a) * orad * 1.06, oy + np.sin(a) * orad * 1.06
        draw.line([(ox + np.cos(a) * orad * 1.0, oy + np.sin(a) * orad * 1.0), (px, py)],
                  fill=(*STEEL, 70), width=1)

    hud.alpha_composite(mono("CH.01 / SIGNAL", 22, CYAN, alpha=200), (round(w * 0.5 - 773), band_y0 - 54))
    hud.alpha_composite(mono("60 FPS · 1080P", 22, STEEL, alpha=150), (round(w * 0.5 + 430), band_y0 - 54))
    hud.alpha_composite(mono("EST.2026", 22, STEEL, alpha=120), (round(w * 0.5 + 620), band_y0 + band_h + 34))
    hud.alpha_composite(barcode((190, 34), WHITE, 90), (round(w * 0.5 - 773), band_y0 + band_h + 34))
    for cx, cy in ((w * 0.5 - 773, band_y0), (w * 0.5 + 773, band_y0 + band_h),
                   (w * 0.5 - 773, band_y0 + band_h), (w * 0.5 + 773, band_y0)):
        crosshair(draw, cx, cy, 13, (*CYAN, 160))

    canvas.alpha_composite(hud)

    # object + its ring light
    oh = round(h * 0.34)
    o = obj.resize((round(obj.width * oh / obj.height), oh), Image.LANCZOS)
    ghost, off = chromatic(o)
    canvas.alpha_composite(ghost, (ox - o.width // 2 + off[0], oy - o.height // 2 + off[1]))
    ring = Image.new("RGBA", o.size, (*CYAN, 0))
    ring.putalpha(o.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.55)))
    canvas.alpha_composite(ring, (ox - o.width // 2, oy - o.height // 2))
    canvas.alpha_composite(o, (ox - o.width // 2, oy - o.height // 2))

    # name inside the band, right of the object
    name = display("ASHTYN", 156, WHITE, tracking=-0.05)
    nx = round(w * 0.47)
    ny = round(h * 0.50) - name.height // 2
    canvas.alpha_composite(name, (nx, ny))
    canvas.alpha_composite(mono("CH.01 — VARIETY", 26, CYAN, alpha=230), (nx + 4, ny + name.height + 26))
    draw2 = ImageDraw.Draw(canvas)
    draw2.line([(nx + 4, ny + name.height + 18), (nx + 430, ny + name.height + 18)], fill=(*WHITE, 70), width=1)

    canvas.alpha_composite(scanlines((w, h), 14))
    return canvas.convert("RGB")


def twitch(w=1200, h=480, obj=None):
    obj = obj or object_rgba()
    canvas = background(w, h, cyan_at=(0.2, 0.25), iris_at=(0.85, 0.9)).convert("RGBA")
    canvas.alpha_composite(shards((w, h), WHITE, [(w * 0.30, -h * 0.2, w * 0.10, h * 1.4, 0.16)], alpha=14))
    canvas.alpha_composite(halftone((w, h), 14, CYAN, 40, region=(int(w * 0.55), 0, w, h)))
    canvas.alpha_composite(grid_dots((w, h), 40, STEEL, 24, (0, 0, w, h), jitter=0.4))

    hud = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud)
    dashed_arc(hud, (40, h // 2 - 170, 380, h // 2 + 170), -80, 250, (*CYAN, 110), width=2)
    ticks(draw, 0, w, h - 18, (*STEEL, 80), step=32)
    hud.alpha_composite(mono("CH.01 / VARIETY", 18, CYAN, alpha=200), (430, 84))
    hud.alpha_composite(mono("EST.2026", 18, STEEL, alpha=120), (430, 356))
    canvas.alpha_composite(hud)

    oh = round(h * 0.62)
    o = obj.resize((round(obj.width * oh / obj.height), oh), Image.LANCZOS)
    canvas.alpha_composite(o, (200 - o.width // 2, h // 2 - o.height // 2))
    name = display("ASHTYN", 104, WHITE, tracking=-0.05)
    canvas.alpha_composite(name, (430, h // 2 - name.height // 2 - 14))
    canvas.alpha_composite(mono("SIGNAL 01 — NO FIXED GENRE", 17, STEEL, alpha=170),
                           (434, h // 2 + name.height // 2 + 6))
    canvas.alpha_composite(scanlines((w, h), 12))
    return canvas.convert("RGB")


def avatar(size=1024, obj=None):
    obj = obj or object_rgba()
    canvas = background(size, size, cyan_at=(0.5, 0.66), iris_at=(0.5, 1.05)).convert("RGBA")
    canvas.alpha_composite(halftone((size, size), 12, CYAN, 26))
    canvas.alpha_composite(grid_dots((size, size), 34, STEEL, 18, (0, 0, size, size), jitter=0.45))

    hud = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    r = round(size * 0.38)
    dashed_arc(hud, (size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r), -110, 235, (*CYAN, 150), width=3)
    draw = ImageDraw.Draw(hud)
    draw.ellipse([size // 2 - r * 0.90, size // 2 - r * 0.90, size // 2 + r * 0.90, size // 2 + r * 0.90],
                 outline=(*WHITE, 46), width=2)
    for ang in range(0, 360, 30):
        a = np.radians(ang)
        draw.line([(size / 2 + np.cos(a) * r * 1.02, size / 2 + np.sin(a) * r * 1.02),
                   (size / 2 + np.cos(a) * r * 1.10, size / 2 + np.sin(a) * r * 1.10)],
                  fill=(*STEEL, 80), width=2)
    canvas.alpha_composite(hud)

    oh = round(size * 0.60)
    oy = size // 2 - round(size * 0.015)
    o = obj.resize((round(obj.width * oh / obj.height), oh), Image.LANCZOS)
    ghost, off = chromatic(o, dx=-7, dy=4)
    canvas.alpha_composite(ghost, (size // 2 - o.width // 2 + off[0], oy - o.height // 2 + off[1]))
    ring = Image.new("RGBA", o.size, (*CYAN, 0))
    ring.putalpha(o.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.5)))
    canvas.alpha_composite(ring, (size // 2 - o.width // 2, oy - o.height // 2))
    canvas.alpha_composite(o, (size // 2 - o.width // 2, oy - o.height // 2))
    canvas.alpha_composite(scanlines((size, size), 10))
    return canvas.convert("RGB")


def hero(w=2400, h=1250, obj=None):
    obj = obj or object_rgba()
    canvas = background(w, h, cyan_at=(0.3, 0.3), iris_at=(0.8, 0.9)).convert("RGBA")
    canvas.alpha_composite(halftone((w, h), 15, CYAN, 44, region=(int(w * 0.35), 0, w, int(h * 0.7))))
    canvas.alpha_composite(grid_dots((w, h), 40, STEEL, 24, (0, 0, w, h), jitter=0.4))
    canvas.alpha_composite(shards((w, h), WHITE, [(w * 0.06, 0, w * 0.05, h, 0.14)], alpha=14))
    oh = round(h * 0.62)
    o = obj.resize((round(obj.width * oh / obj.height), oh), Image.LANCZOS)
    canvas.alpha_composite(o, (w // 2 - o.width // 2, h // 2 - o.height // 2))
    big = display("ASHTYN", round(h * 0.30), WHITE, tracking=-0.05, alpha=235)
    canvas.alpha_composite(big, (60, h - big.height - 40))
    canvas.alpha_composite(mono("CH.01 — VARIETY / NO FIXED GENRE", 22, CYAN, alpha=200), (66, h - 34))
    canvas.alpha_composite(scanlines((w, h), 12))
    return canvas.convert("RGB")


def export():
    t0 = time.time()
    obj = object_rgba()
    print(f"  object                       {obj.size}  {time.time() - t0:.0f}s")

    b = banner(obj=obj)
    b.save(OUT / "youtube-banner-dark-2560x1440.png")
    b.resize((1280, 720), Image.LANCZOS).save(LAYERS / "preview-banner-half.png")

    tw = twitch(obj=obj)
    tw.save(OUT / "twitch-banner-1200x480.png")

    av = avatar(obj=obj)
    av.save(OUT / "profile-dark-1024.png")
    av.resize((800, 800), Image.LANCZOS).save(OUT / "profile-dark-800.png")
    av.resize((256, 256), Image.LANCZOS).save(OUT / "profile-dark-256.png")

    hr = hero(obj=obj)
    hr.save(OUT / "header-hero-2400x1250.png")

    for f in ("youtube-banner-dark-2560x1440.png", "twitch-banner-1200x480.png",
              "profile-dark-1024.png", "profile-dark-800.png", "profile-dark-256.png",
              "header-hero-2400x1250.png"):
        im = Image.open(OUT / f)
        print(f"  {f:34} {im.size} {im.mode}")


if __name__ == "__main__":
    if "probe" in sys.argv:
        res = int(sys.argv[sys.argv.index("probe") + 1])
        t0 = time.time()
        obj = object_rgba(res=res, aa=1)
        avatar(820, obj=obj).save(LAYERS / "_cyber_pfp.png")
        banner(1600, 900, obj=obj).save(LAYERS / "_cyber_banner.png")
        print(f"probe in {time.time() - t0:.1f}s")
    else:
        export()
