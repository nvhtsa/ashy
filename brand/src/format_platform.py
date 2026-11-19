"""Cut the platform set from a finished header artwork.

Usage:
    python brand/src/format_platform.py <source.png> <outdir>

Nothing is redrawn. The artwork is scaled, positioned inside YouTube's safe
band and cropped for each surface.

The letter mass of the piece is described by CONTENT, as fractions of the
artwork's width/height — measured off the file once, because automatic
detection cannot separate the word from the tentacles it grows out of (both are
the same dark ink). Pass a different box if the artwork changes.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WHITE = (255, 255, 255)

# x0, y0, x1, y1 of the lettering, as fractions of the source image.
CONTENT = (0.17, 0.255, 0.865, 0.845)

# YouTube channel art: 2560x1440 canvas, of which only a centred band is shown
# on every device (TV / desktop / mobile all guarantee 1546x423).
YT_W, YT_H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423


def content_box(im, frac):
    x0, y0, x1, y1 = frac
    return (int(round(x0 * im.width)), int(round(y0 * im.height)),
            int(round(x1 * im.width)), int(round(y1 * im.height)))


def scale_for_band(box, safe_w, safe_h):
    """Scale that puts the lettering inside the safe band on both axes."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    return min(safe_h / bh, safe_w / bw)


def banner(im, box):
    """White 16:9 canvas with the art centred so its letters fill the band."""
    # 0.5% under, so integer rounding of the paste offset can never push a
    # letter over the band edge.
    s = scale_for_band(box, SAFE_W, SAFE_H) * 0.995
    w, h = int(round(im.width * s)), int(round(im.height * s))
    art = im.resize((w, h), Image.LANCZOS)

    # Offset the art so the lettering's centre, not the art's centre, lands on
    # the canvas centre — the tentacles are asymmetric.
    cx = (box[0] + box[2]) / 2 * s
    cy = (box[1] + box[3]) / 2 * s
    ox = int(round(YT_W / 2 - cx))
    oy = int(round(YT_H / 2 - cy))

    # Feather the art's edges into the page: the source is a rectangle of
    # near-white paper with pale washes, and a hard seam reads as a pasted
    # block rather than one continuous background.
    fx = max(40, int(w * 0.10))
    fy = max(24, int(h * 0.05))
    ramp = np.ones((h, w), np.float32)

    def smooth(n):
        t = np.linspace(0.0, 1.0, n, dtype=np.float32)
        return t * t * (3.0 - 2.0 * t)

    sx, sy = smooth(fx), smooth(fy)
    ramp[:fy, :] *= sy[:, None]
    ramp[-fy:, :] *= sy[::-1, None]
    ramp[:, :fx] *= sx[None, :]
    ramp[:, -fx:] *= sx[::-1][None, :]
    art = art.convert("RGBA")
    art.putalpha(Image.fromarray((ramp * 255).astype(np.uint8), "L"))

    canvas = Image.new("RGB", (YT_W, YT_H), WHITE)
    canvas.paste(art, (ox, oy), art)
    placed = (ox + box[0] * s, oy + box[1] * s, ox + box[2] * s, oy + box[3] * s)
    return canvas, placed


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    r = im.resize((int(round(im.width * s)), int(round(im.height * s))), Image.LANCZOS)
    left, top = (r.width - w) // 2, (r.height - h) // 2
    return r.crop((left, top, left + w, top + h))


def avatar(im, box, side_factor=1.40, x_bias=0.07):
    """Square crop on the first letter, for the circular profile mask."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    side = min(int(round(bh * side_factor)), im.width, im.height)
    cx = x0 + bw * x_bias
    cy = (y0 + y1) / 2
    left = int(round(min(max(cx - side / 2, 0), im.width - side)))
    top = int(round(min(max(cy - side / 2, 0), im.height - side)))
    return im.crop((left, top, left + side, top + side))


def knockout(sq, size=150):
    """Solid white silhouette of the letter, for video corners.

    A shrink-wrapped copy of the shaded art turns to grey mush at 150px, so the
    mark is rebuilt as one flat shape: take the ink, flood the outside from a
    corner, and everything the flood cannot reach is inside the letter.
    """
    m = sq.resize((size, size), Image.LANCZOS)
    a = np.asarray(m.convert("RGB")).astype(np.float32)
    lum = a.mean(2)
    sat = a.max(2) - a.min(2)
    ink = ((sat > 60) & (lum < 205)).astype(np.uint8) * 255
    alpha = Image.fromarray(ink, "L").filter(ImageFilter.GaussianBlur(1.0))
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.putalpha(alpha)
    return out


def run(src, outdir, content=CONTENT):
    if not os.path.exists(src):
        raise SystemExit("missing source: %s" % src)
    os.makedirs(outdir, exist_ok=True)

    im = Image.open(src).convert("RGB")
    box = content_box(im, content)
    print("source    %s  %dx%d" % (os.path.basename(src), im.width, im.height))
    print("letters   %dx%d at (%d,%d)" % (box[2] - box[0], box[3] - box[1], box[0], box[1]))

    written = []

    def save(img, name):
        img.save(os.path.join(outdir, name))
        written.append((name, img.size))

    # --- YouTube channel art -------------------------------------------------
    b, placed = banner(im, box)
    save(b, "youtube-banner-2560x1440.png")

    guide = b.copy()
    d = ImageDraw.Draw(guide)
    gl, gt = (YT_W - SAFE_W) // 2, (YT_H - SAFE_H) // 2
    d.rectangle([gl, gt, gl + SAFE_W, gt + SAFE_H], outline=(255, 60, 60), width=4)
    save(guide, "_check-safe-band-2560x1440.png")

    print("letters in banner  x %d..%d  y %d..%d"
          % (placed[0], placed[2], placed[1], placed[3]))
    print("safe band          x %d..%d  y %d..%d" % (gl, gl + SAFE_W, gt, gt + SAFE_H))
    inside = (placed[0] >= gl and placed[2] <= gl + SAFE_W
              and placed[1] >= gt and placed[3] <= gt + SAFE_H)
    print("letters inside band: %s" % ("yes" if inside else "NO"))

    # --- Twitch panel --------------------------------------------------------
    save(cover(im, 1200, 480), "twitch-banner-1200x480.png")

    # --- Profile pictures ----------------------------------------------------
    sq = avatar(im, box)
    for s in (1024, 800, 512, 256):
        save(sq.resize((s, s), Image.LANCZOS), "profile-%d.png" % s)
    # No watermark: at 150px the splash detail in this artwork collapses into
    # noise, so a corner mark has to be drawn separately rather than cropped.

    # --- X / Twitter header --------------------------------------------------
    save(cover(im, 1500, 500), "twitter-header-1500x500.png")

    for name, size in written:
        print("  %-32s %dx%d" % (name, size[0], size[1]))
    print("done -> %s" % outdir)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    run(a[0], a[1] if len(a) > 1 else os.path.dirname(os.path.abspath(a[0])))
