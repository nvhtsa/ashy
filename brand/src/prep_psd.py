"""Prepare raw RGBA buffers for the thumbnail PSD builder.

Chrome will not emit alpha for these screenshots, so every non-geometric layer in
the PSD is a live text layer (Photoshop renders those itself). Only the art and
the tag plate are pixels, and both are produced here.
"""
import json
import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent
LAYERS = ROOT / "layers"
OUT = ROOT / "psd"
OUT.mkdir(exist_ok=True)

W, H = 1280, 720


def dump(im, name, left=0, top=0):
    im = im.convert("RGBA")
    (OUT / f"{name}.rgba").write_bytes(im.tobytes())
    return {"width": im.width, "height": im.height, "left": left, "top": top}


meta = {}

# --- art: full bleed, opaque ---
art = Image.open(LAYERS / "art.png").convert("RGBA")
assert art.size == (W, H), art.size
meta["art"] = dump(art, "art")

# --- tag plate: rounded rect, matches .chip geometry measured in the browser ---
plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(plate)
x, y, w, h = 51, 616, 391, 54
d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=7,
                    fill=(20, 18, 26, 199), outline=(233, 229, 221, 71), width=1)
# cropped to its own bounds so the layer carries 391x54 instead of a full canvas
meta["plate"] = dump(plate.crop((x, y, x + w, y + h)), "plate", x, y)

# --- flattened composite, used as the PSD preview image ---
comp = Image.open(LAYERS / "thumb-composite.png").convert("RGBA")
meta["composite"] = dump(comp, "composite")

(OUT / "meta.json").write_text(json.dumps(meta, indent=2))
print("wrote", meta)
