"""Legacy: the bracket `[a]` logo, superseded by make_mark.py.

Writes into export/legacy/ so re-running it can never overwrite the current mark.
Kept because the video glyph strips (build_video.py) still come from these renders.

Build the transparent [a] logo from two renders of the same mark.

Chrome screenshots carry no alpha channel, so the mark is rendered once on pure
black and once on pure white. For any pixel:  black = a*C  and  white = a*C + (1-a)*255
which solves to  a = 1 - (white - black)/255  and  C = black / a.

The logo gets generous breathing room; the watermark is padded tight so the mark
fills the small square YouTube renders it into.
"""
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
LAYERS = ROOT / "layers"
OUT = ROOT.parent / "export" / "legacy"
OUT.mkdir(parents=True, exist_ok=True)

black = np.asarray(Image.open(LAYERS / "mk-black.png").convert("RGB")).astype(np.float32)
white = np.asarray(Image.open(LAYERS / "mk-white.png").convert("RGB")).astype(np.float32)
assert black.shape == white.shape

# per-channel coverage, averaged so colour noise on the edges cancels out
alpha = np.clip((1.0 - ((white - black) / 255.0)).mean(axis=2), 0.0, 1.0)

# un-premultiply: recover the colour that was under the mask
safe = np.where(alpha > 0.004, alpha, 1.0)[..., None]
colour = np.clip(black / safe, 0, 255)

rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
rgba[..., :3] = np.round(colour).astype(np.uint8)
rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)

tight = Image.fromarray(rgba, "RGBA").crop(Image.fromarray(rgba, "RGBA").getbbox())


def square(img, margin):
    """Pad to a square with `margin` of the long side as breathing room."""
    side = int(round(max(img.size) * (1 + 2 * margin)))
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return out


def recolour(img, rgb, size):
    """Solid-colour version: keep the alpha mask, replace the RGB wholesale."""
    mask = img.getchannel("A").resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (*rgb, 0))
    out.putalpha(mask)
    return out


logo = square(tight, 0.13).resize((1024, 1024), Image.LANCZOS)
logo.save(OUT / "logo-transparent-1024.png")
recolour(logo, (255, 255, 255), 1024).save(OUT / "logo-white-1024.png")
recolour(logo, (20, 18, 26), 1024).save(OUT / "logo-black-1024.png")

mark = square(tight, 0.045).resize((150, 150), Image.LANCZOS)
mark.save(OUT / "watermark-150.png")
recolour(mark, (255, 255, 255), 150).save(OUT / "watermark-150-white.png")

print("tight mark", tight.size)
for f in ("logo-transparent-1024.png", "logo-white-1024.png", "logo-black-1024.png",
          "watermark-150.png", "watermark-150-white.png"):
    im = Image.open(OUT / f)
    a = np.asarray(im.getchannel("A"))
    print(f"{f:28} {im.size} {im.mode} alpha min/max={a.min()}/{a.max()} corner alpha={a[2, 2]}")
