"""Build a custom Jellyfin logo: a geometric A with a sheared crossbar that
overshoots the right leg, plus wordmark, tile, favicons and a CSS drop-in.

Usage:  python brand/src/build_jellyfin_logo.py <outdir>
"""
import base64
import os
import sys

from PIL import Image, ImageDraw, ImageFont

GRID = 1000
SS = 4  # supersample factor

INK = (12, 9, 20)
VIO_LIGHT = (196, 181, 253)
VIO_DEEP = (124, 58, 237)
BONE = (244, 240, 255)
BONE_SHADE = (214, 205, 240)

# --- A geometry -----------------------------------------------------------
APEX_Y = 70
BASE_Y = 880
APEX_HALF = 12          # half width of the flat apex
FOOT_OUT = 190          # outer edge at the baseline (left); mirrored for right
SLOPE = 0.368           # dx per dy on both outer edges (190 at the baseline)
LEG_T = 118             # horizontal leg thickness
BAR_TOP, BAR_BOT = 610, 716
BAR_RIGHT = 748         # overshoot past the right leg

FONT_DIR = os.path.join("brand", "fonts")


def x_outer_left(y):
    return 500 - APEX_HALF - SLOPE * (y - APEX_Y)


def x_outer_right(y):
    return 500 + APEX_HALF + SLOPE * (y - APEX_Y)


def x_inner_left(y):
    return x_outer_left(y) + LEG_T


def x_inner_right(y):
    return x_outer_right(y) - LEG_T


def counter_apex_y():
    # where the two inner edges meet
    return APEX_Y + (APEX_HALF + LEG_T) / SLOPE


def body_polys():
    outer = [
        (500 - APEX_HALF, APEX_Y),
        (500 + APEX_HALF, APEX_Y),
        (FOOT_OUT + 620, BASE_Y),
        (FOOT_OUT, BASE_Y),
    ]
    cy = counter_apex_y()
    counter = [(500, cy), (x_inner_left(BAR_TOP), BAR_TOP), (x_inner_right(BAR_TOP), BAR_TOP)]
    gap = [
        (x_inner_left(BAR_BOT), BAR_BOT),
        (x_inner_right(BAR_BOT), BAR_BOT),
        (x_inner_right(BASE_Y), BASE_Y),
        (x_inner_left(BASE_Y), BASE_Y),
    ]
    return outer, counter, gap


def bar_poly():
    return [
        (x_outer_left(BAR_TOP), BAR_TOP),
        (BAR_RIGHT, BAR_TOP),
        (BAR_RIGHT, BAR_BOT),
        (x_outer_left(BAR_BOT), BAR_BOT),
    ]


def render_mask(polys):
    im = Image.new("L", (GRID * SS, GRID * SS), 0)
    d = ImageDraw.Draw(im)
    for poly, fill in polys:
        d.polygon([(x * SS, y * SS) for x, y in poly], fill=fill)
    return im.resize((GRID, GRID), Image.LANCZOS)


def masks():
    outer, counter, gap = body_polys()
    body = render_mask([(outer, 255), (counter, 0), (gap, 0)])
    bar = render_mask([(bar_poly(), 255)])
    return body, bar


# --- colour helpers -------------------------------------------------------
def solid(mask, rgb):
    out = Image.new("RGBA", mask.size, rgb + (0,))
    out.putalpha(mask)
    return out


def gradient(mask, top, bottom):
    w, h = mask.size
    ramp = Image.new("RGBA", (1, h))
    px = ramp.load()
    for y in range(h):
        f = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3)) + (255,)
    out = ramp.resize((w, h), Image.BILINEAR)
    out.putalpha(mask)
    return out


def tight(im, pad=0.03):
    im = im.crop(im.getchannel("A").getbbox())
    w, h = im.size
    side = max(w, h) + int(max(w, h) * pad) * 2
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.alpha_composite(im, ((side - w) // 2, (side - h) // 2))
    return out


# --- pieces ---------------------------------------------------------------
def make_mark(body, bar, variant):
    if variant == "white":
        return tight(solid(body, BONE))
    if variant == "ink":
        return tight(solid(body, INK))
    if variant == "violet":
        return tight(gradient(body, VIO_LIGHT, VIO_DEEP))
    # two-tone: bone A, violet bar that overshoots
    im = solid(body, BONE)
    im.alpha_composite(gradient(bar, VIO_LIGHT, VIO_DEEP))
    return tight(im)


def make_tile(mark, px=512):
    tile = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    r = int(px * 0.22)
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=r, fill=INK + (255,))
    d.rounded_rectangle(
        [0, 0, px - 1, px - 1],
        radius=r,
        outline=(43, 34, 66, 255),
        width=max(1, px // 256),
    )
    inner = int(px * 0.66)
    m = mark.resize((inner, inner), Image.LANCZOS)
    tile.alpha_composite(m, ((px - inner) // 2, (px - inner) // 2))
    return tile


def draw_spaced(d, text, font, x, baseline_top, fill, track):
    for ch in text:
        bbox = font.getbbox(ch)
        d.text((x - bbox[0], baseline_top), ch, font=font, fill=fill)
        x += (bbox[2] - bbox[0]) + track


def measure(text, font, track):
    w = 0
    for ch in text:
        b = font.getbbox(ch)
        w += (b[2] - b[0]) + track
    return w - track if text else 0


def make_wordmark(text="ASHTYN", cap=260, color=BONE):
    font = ImageFont.truetype(os.path.join(FONT_DIR, "ArchivoBlack-Regular.ttf"), cap)
    track = int(cap * 0.045)
    w = measure(text, font, track) + int(cap * 0.12) * 2
    h = int(cap * 1.34)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_spaced(d, text, font, int(cap * 0.12), int(cap * 0.14), color + (255,), track)
    return im.crop(im.getchannel("A").getbbox())


def make_lockup(mark, wordmark, out_h=340):
    mh = int(out_h * 0.92)
    m = mark.resize((int(mark.size[0] * mh / mark.size[1]), mh), Image.LANCZOS)
    wh = int(out_h * 0.50)
    wm = wordmark.resize((int(wordmark.size[0] * wh / wordmark.size[1]), wh), Image.LANCZOS)
    space = int(out_h * 0.22)
    w = m.size[0] + space + wm.size[0]
    im = Image.new("RGBA", (w, out_h), (0, 0, 0, 0))
    im.alpha_composite(m, (0, (out_h - mh) // 2))
    im.alpha_composite(wm, (m.size[0] + space, (out_h - wh) // 2 - int(out_h * 0.02)))
    return im


# --- previews -------------------------------------------------------------
def previews(outdir, marks):
    def row(bg, name, items, label_sizes=False):
        im = Image.new("RGB", (1500, 520), bg)
        x = 70
        for m, h in items:
            mm = m.resize((max(1, int(m.size[0] * h / m.size[1])), h), Image.LANCZOS)
            if x + mm.size[0] > 1440:
                mm = m.resize((int(m.size[0] * (1440 - x) / m.size[1]), 1440 - x), Image.LANCZOS)
            im.paste(mm, (x, (520 - h) // 2 - 40), mm)
            x += mm.size[0] + 60
        im.save(os.path.join(outdir, name), quality=93)

    row((12, 9, 20), "preview-dark.jpg", [(marks["two-tone"], 360), (marks["white"], 360), (marks["violet"], 360)])
    row((243, 241, 248), "preview-light.jpg", [(marks["ink"], 360), (marks["violet"], 360)])

    # small sizes on the actual header ground
    strip = Image.new("RGB", (1200, 160), INK)
    x = 40
    for px in (64, 48, 40, 32, 24, 16):
        sm = marks["white"].resize((px, px), Image.LANCZOS)
        strip.paste(sm, (x, (160 - px) // 2), sm)
        x += px + 46
    strip.save(os.path.join(outdir, "preview-sizes.png"))


def write_css(outdir, mark_white_128, wordmark):
    b64_mark = base64.b64encode(open(mark_white_128, "rb").read()).decode()
    b64_word = base64.b64encode(open(wordmark, "rb").read()).decode()
    css = f"""/* ASHTYN — Jellyfin branding
   Dashboard > Branding > Custom CSS, paste everything below, Save, hard-refresh.
   Logo is white so it reads on the dark theme; swap in the -ink version for light. */

/* header + drawer mark */
.headerLogo,
.pageTitleWithDefaultLogo {{
  content: url("data:image/png;base64,{b64_mark}") !important;
  height: 2.4em !important;
  width: auto !important;
  object-fit: contain !important;
}}

/* login screen + splash */
.splashLogo {{
  background-image: url("data:image/png;base64,{b64_word}") !important;
  background-size: contain !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
}}
"""
    with open(os.path.join(outdir, "jellyfin-branding.css"), "w", encoding="utf-8") as f:
        f.write(css)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)

    body, bar = masks()
    marks = {v: make_mark(body, bar, v) for v in ("white", "ink", "violet", "two-tone")}

    for name, im in marks.items():
        for px in (1024, 512, 256, 128, 64):
            im.resize((px, px), Image.LANCZOS).save(
                os.path.join(outdir, f"jellyfin-mark-{name}-{px}.png")
            )
    for px in (48, 32, 16):
        marks["white"].resize((px, px), Image.LANCZOS).save(
            os.path.join(outdir, f"jellyfin-favicon-{px}.png")
        )

    tile = make_tile(marks["two-tone"])
    for px in (1024, 512, 256):
        tile.resize((px, px), Image.LANCZOS).save(
            os.path.join(outdir, f"jellyfin-tile-{px}.png")
        )

    wordmark = make_wordmark()
    wordmark.save(os.path.join(outdir, "jellyfin-wordmark.png"))
    make_wordmark(color=INK).save(os.path.join(outdir, "jellyfin-wordmark-ink.png"))

    lockup = make_lockup(marks["two-tone"], wordmark)
    lockup.save(os.path.join(outdir, "jellyfin-lockup.png"))

    previews(outdir, marks)
    write_css(
        outdir,
        os.path.join(outdir, "jellyfin-mark-white-128.png"),
        os.path.join(outdir, "jellyfin-wordmark.png"),
    )
    print("mark:", marks["white"].size, "wordmark:", wordmark.size, "lockup:", lockup.size)


if __name__ == "__main__":
    main()
