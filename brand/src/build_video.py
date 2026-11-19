"""Render the ashtyn brand in motion: OBS scenes, a Twitch stinger and a YouTube intro.

Everything is drawn from the same two source PNGs the still exports use
(mk-black.png / mk-white.png, the mark rendered by Chrome at #mkstage). The
alpha is solved from those two renders, then the mark is split into its three
glyph groups by the gaps between them, so the brackets can move independently
of the letter without anyone re-typing a font size that might drift.

Usage:
    python brand/src/build_video.py            # everything
    python brand/src/build_video.py screens    # one target
"""
import math
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = pathlib.Path(__file__).resolve().parent
LAYERS = ROOT / "layers"
OUT = ROOT.parent / "video"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080

CHARCOAL = (20, 18, 26)
SMOKE = (233, 229, 221)
IRIS = (155, 138, 240)
ASH = (137, 131, 154)

SANS = str(ROOT.parent / "fonts" / "BricolageGrotesque-SemiBold.ttf")
MONO = "C:/Windows/Fonts/consola.ttf"

FFMPEG = get_ffmpeg_exe()


# ---------------------------------------------------------------- easing
def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= b)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def ease_in_out(x):
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- mark
def solve_alpha():
    """Recover the mark's real alpha from the black and white Chrome renders."""
    b = np.asarray(Image.open(LAYERS / "mk-black.png").convert("RGB")).astype(np.float32)
    w = np.asarray(Image.open(LAYERS / "mk-white.png").convert("RGB")).astype(np.float32)
    alpha = np.clip((1.0 - ((w - b) / 255.0).mean(axis=2)), 0.0, 1.0)
    safe = np.where(alpha > 0.004, alpha, 1.0)[..., None]
    colour = np.clip(b / safe, 0, 255)
    rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.round(colour).astype(np.uint8)
    rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


class Mark:
    """The [a] mark, split into left bracket / letter / right bracket."""

    def __init__(self):
        src = solve_alpha()
        ink = np.asarray(src.getchannel("A")) > 0
        cols = ink.any(axis=0)
        runs, start = [], None
        for i, v in enumerate(cols):
            if v and start is None:
                start = i
            elif not v and start is not None:
                runs.append((start, i))
                start = None
        if start is not None:
            runs.append((start, len(cols)))
        if len(runs) != 3:
            raise RuntimeError(f"expected 3 glyph groups, found {len(runs)}: {runs}")

        box = src.getbbox()
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        self.parts = []
        for x0, x1 in runs:
            strip = src.crop((x0, 0, x1, src.height))
            bb = strip.getbbox()
            glyph = strip.crop(bb)
            self.parts.append([glyph, x0 + (bb[0] + bb[2]) / 2 - cx, (bb[1] + bb[3]) / 2 - cy])
        self.letter_h = self.parts[1][0].height
        self.ink_w = box[2] - box[0]
        self._cache = {}

    def scaled(self, i, k):
        key = (i, round(k, 3))
        if key not in self._cache:
            g = self.parts[i][0]
            self._cache[key] = g.resize(
                (max(1, round(g.width * k)), max(1, round(g.height * k))), Image.LANCZOS
            )
        return self._cache[key]

    @staticmethod
    def wipe_mask(size, progress, feather=0.22):
        """Soft-edged vertical reveal: 0 hides the glyph, 1 shows all of it."""
        w, h = size
        edge = progress * (1 + 2 * feather) - feather
        ys = (np.arange(h, dtype=np.float32) + 0.5) / max(1, h)
        col = np.clip((edge - ys) / feather, 0.0, 1.0) * 255.0
        return Image.fromarray(np.round(np.repeat(col[:, None], w, axis=1)).astype(np.uint8), "L")

    def draw(self, canvas, cx, cy, letter_h, dx=(0, 0, 0), dy=(0, 0, 0), alpha=(1, 1, 1),
             scale=(1, 1, 1), rot=(0, 0, 0), blur=(0, 0, 0), wipe=(1, 1, 1)):
        for i, (glyph, px, py) in enumerate(self.parts):
            k = letter_h * scale[i] / self.letter_h
            im = self.scaled(i, k)
            a = alpha[i]
            b = blur[i]
            if b > 0.05:
                # soften the cut as it dissolves, so the fade reads as liquid rather than opacity
                im = im.filter(ImageFilter.GaussianBlur(b))
            if abs(rot[i]) > 0.02:
                im = im.rotate(rot[i], resample=Image.BICUBIC, expand=True)
            if wipe[i] < 0.999:
                im = im.copy()
                im.putalpha(ImageChops.multiply(im.getchannel("A"), self.wipe_mask(im.size, wipe[i])))
            if a < 0.999:
                im = im.copy()
                im.putalpha(im.getchannel("A").point([round(v * a) for v in range(256)]))
            canvas.alpha_composite(
                im,
                (round(cx + px * k + dx[i] - im.width / 2), round(cy + py * k + dy[i] - im.height / 2)),
            )


MARK = None


def mark():
    global MARK
    if MARK is None:
        MARK = Mark()
    return MARK


# ---------------------------------------------------------------- background
def field():
    """Charcoal with the same low iris glow the Twitch banner uses."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (x - W * 0.5) / (0.80 * W)
    dy = (y - H * 1.28) / (1.20 * H)
    d = np.sqrt(dx * dx + dy * dy)
    g = np.clip(1 - d / 0.70, 0, 1) ** 1.4 * 0.16
    base = np.array(CHARCOAL, np.float32)
    img = base * (1 - g[..., None]) + np.array(IRIS, np.float32) * g[..., None]

    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / 1.41
    img *= (1 - 0.10 * np.clip(r, 0, 1) ** 2)[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


BG = None


def bg():
    global BG
    if BG is None:
        BG = field()
    return BG


# ---------------------------------------------------------------- type
def mono(text, px, tracking, colour, ss=3):
    """Monospace caps with tracking, rendered oversized then downsampled for crisp edges."""
    f = ImageFont.truetype(MONO, px * ss)
    track = tracking * px * ss
    widths = [f.getlength(c) for c in text]
    total = sum(widths) + track * (len(text) - 1)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (int(math.ceil(total)) + 12, asc + desc + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 6
    for c, w in zip(text, widths):
        d.text((x, 6), c, font=f, fill=colour)
        x += w + track
    bb = img.getbbox()
    img = img.crop(bb)
    return img.resize((max(1, round(img.width / ss)), max(1, round(img.height / ss))), Image.LANCZOS)


def paste_centre(canvas, sprite, cx, cy, opacity=1.0):
    im = sprite
    if opacity < 0.999:
        lut = [round(v * opacity) for v in range(256)]
        im = sprite.copy()
        im.putalpha(im.getchannel("A").point(lut))
    canvas.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))


def blob_points(cx, cy, r, rot=0.0, a1=0.0, a2=0.0, n=200):
    """A closed organic curve: two harmonics riding on a circle."""
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        rr = r * (1 + a1 * math.sin(3 * th + rot) + a2 * math.sin(5 * th - 1.7 * rot))
        pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
    return pts


def blob_mask(size, cx, cy, r, rot=0.0, a1=0.0, a2=0.0, scale=2, n=200):
    w, h = size
    m = Image.new("L", (int(w * scale), int(h * scale)), 0)
    ImageDraw.Draw(m).polygon(
        [(x * scale, y * scale) for x, y in blob_points(cx, cy, r, rot, a1, a2, n)], fill=255
    )
    return m.resize((w, h), Image.LANCZOS)


def rule(canvas, y, width, t, amp=3.0, waves=2.4, thickness=2.0):
    """The hairline, but alive: a slow wave with a highlight riding it."""
    ss = 3
    w2, h2 = width * ss, 12 * ss
    xs = np.linspace(0, waves * 2 * math.pi, w2)
    yc = h2 / 2 + amp * ss * np.sin(xs + 2 * math.pi * t)
    yy = np.arange(h2)[:, None]
    a = np.clip(thickness * 0.5 * ss + 0.5 - np.abs(yy - yc[None, :]), 0, 1)

    x = np.linspace(-1, 1, w2)
    g = np.exp(-(((x - 1.7 * math.sin(2 * math.pi * t)) / 0.17) ** 2))
    a = a * (0.20 + 0.80 * g)[None, :]

    layer = np.zeros((h2, w2, 4), np.uint8)
    layer[..., 0], layer[..., 1], layer[..., 2] = IRIS
    layer[..., 3] = np.round(a * 255).astype(np.uint8)
    img = Image.fromarray(layer, "RGBA").resize((width, 12), Image.LANCZOS)
    canvas.alpha_composite(img, (round(W / 2 - width / 2), round(y - 6)))


# ---------------------------------------------------------------- screens
LOOP = 10.0


def screen(sec, label=None, sub=None):
    """Starting / BRB / ending plate. Every motion has a whole-number period in 10s
    so the loop closes exactly."""
    t = sec / LOOP
    ph = 2 * math.pi * t
    canvas = bg().convert("RGBA")

    # ambient light that morphs behind the mark, blurred so it reads as glow not shape
    r = 300 + 70 * math.sin(ph + 0.4)
    bx = W / 2 + 80 * math.sin(ph + 0.6)
    by = H * 0.40 + 34 * math.sin(2 * ph + 1.2)
    low = (W // 4, H // 4)
    m = blob_mask(low, bx / 4, by / 4, r / 4, rot=ph, a1=0.11, a2=0.06, scale=1)
    m = m.filter(ImageFilter.GaussianBlur(16)).resize((W, H), Image.BILINEAR)
    glow = Image.new("RGBA", (W, H), (*IRIS, 0))
    glow.putalpha(m.point([round(v * 0.16) for v in range(256)]))
    canvas = Image.alpha_composite(canvas, glow)

    # the mark floats; the brackets lag half a beat behind the letter
    lift = 15 * math.sin(ph)
    lag = 15 * math.sin(ph - 0.5)
    spread = 8 * math.sin(ph + 1.9)
    mark_cy = H * (0.395 if sub else 0.405) + 7 * math.sin(ph + 0.8)
    mark().draw(
        canvas,
        W / 2,
        mark_cy,
        296 * (1 + 0.012 * math.sin(ph + 0.9)),
        dx=(-spread, 0, spread),
        dy=(lag, lift, lag),
    )

    rule(canvas, H * 0.60, 340, t)

    drift = 2 * math.sin(ph + 2.0)
    pulse = 0.88 + 0.12 * math.sin(ph + 1.4)
    if label:
        paste_centre(canvas, label, W / 2, H * (0.685 if sub else 0.675) + drift, pulse)
    if sub:
        paste_centre(canvas, sub, W / 2, H * 0.755 + drift, 0.82 + 0.18 * math.sin(ph + 2.6))
    return canvas


# ---------------------------------------------------------------- stinger
STINGER_SECS = 1.45
R_FULL = 1330.0


def smooth(x):
    return ease_in_out(clamp01(x))


def stinger_radius(sec):
    """Blooms past the frame edge slowly, then snaps back in."""
    r = 150 + (R_FULL - 150) * ease_in_out(seg(sec, 0.06, 0.88))
    c = ease_in_out(seg(sec, 1.04, 1.42))
    return max(0.0, r * (1 - c) + 70 * c)


def stinger_frame(sec):
    """A charcoal surface rises out of the mark, ripples, holds, then drains away."""
    plate = 1 - ease_in_out(seg(sec, 1.22, 1.44))

    wob = 0.05 + 0.03 * seg(sec, 1.02, 1.34)

    # the surface thickens in: nothing is born opaque and nothing is born with a hard
    # edge, so the opening condenses rather than pops
    surf = smooth(seg(sec, 0.02, 0.56))
    rim_gain = smooth(seg(sec, 0.26, 0.74))
    mask = blob_mask(
        (W, H), W / 2, H / 2, stinger_radius(sec), rot=1.2 * sec, a1=wob, a2=0.03, n=260
    ).filter(ImageFilter.GaussianBlur(1.6 + 24.0 * (1 - surf) ** 1.7))
    body = mask.point([round(v * plate * surf) for v in range(256)])

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # light bleeding out ahead of the edge, so the surface reads wet rather than cut.
    # Built at a quarter of the frame from a shape wider than the mask, so it is a bloom
    # rather than an outline no matter how small the surface currently is.
    low = (W // 4, H // 4)
    gr = stinger_radius(sec) * 1.24 / 4 + 10
    glow = blob_mask(low, W / 8, H / 8, gr, rot=1.2 * sec, a1=wob, a2=0.03, scale=1, n=200)
    glow = glow.filter(ImageFilter.GaussianBlur(max(2.5, gr * 0.22))).resize((W, H), Image.BILINEAR)
    halo_layer = Image.new("RGBA", (W, H), (*IRIS, 0))
    halo_layer.putalpha(
        glow.point([round(v * 0.34 * surf * plate) for v in range(256)])
    )
    canvas = Image.alpha_composite(canvas, halo_layer)

    plate_layer = Image.new("RGBA", (W, H), (*CHARCOAL, 0))
    plate_layer.putalpha(body)
    canvas = Image.alpha_composite(canvas, plate_layer)

    # solid rim: a 2px line that survives being laid over bright footage
    rim = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(5)))
    rim_layer = Image.new("RGBA", (W, H), (*IRIS, 0))
    rim_layer.putalpha(rim.point([min(255, round(v * 2.6 * plate * rim_gain)) for v in range(256)]))
    canvas = Image.alpha_composite(canvas, rim_layer)

    # the mark presents itself: brackets draw downward, then the letter rises into focus
    ph = 2 * math.pi * 0.55 * sec
    arr = (smooth(seg(sec, 0.06, 0.28)), smooth(seg(sec, 0.30, 0.78)), smooth(seg(sec, 0.10, 0.32)))
    dep = (1 - smooth(seg(sec, 1.06, 1.34)), 1 - smooth(seg(sec, 1.02, 1.26)), 1 - smooth(seg(sec, 1.10, 1.38)))
    alpha = tuple(a * d for a, d in zip(arr, dep))

    if max(alpha) > 0.004:
        blur = tuple(
            max(13.0 * (1 - arr[i]) ** 1.2 if i == 1 else 3.0 * (1 - arr[i]), 5.0 * (1 - dep[i]) ** 1.2)
            for i in range(3)
        )
        wipe = (smooth(seg(sec, 0.08, 0.60)), 1.0, smooth(seg(sec, 0.13, 0.66)))
        spread = 26 * (1 - smooth(seg(sec, 0.06, 0.74))) + 4.5 * math.sin(ph)
        bob = 3.2 * math.sin(ph + 1.1)
        sway = 1.7 * math.sin(ph - 0.7)
        tilt = 1.4 * math.sin(ph * 0.83 + 0.4)
        rise = 26 * (1 - smooth(seg(sec, 0.26, 0.84)))
        mark().draw(
            canvas,
            W / 2,
            H / 2,
            172,
            dx=(-spread, 0, spread),
            dy=(bob + sway, bob - sway * 0.55 + rise, bob + sway),
            alpha=alpha,
            scale=(1, 0.955 + 0.045 * smooth(seg(sec, 0.28, 0.84)), 1),
            rot=(-tilt * 0.55, tilt, tilt * 0.55),
            blur=blur,
            wipe=wipe,
        )
    return canvas


# ---------------------------------------------------------------- intro
INTRO_SECS = 2.00


def intro_frame(sec, with_field=True):
    """Brackets fly in, the letter lands between them, then everything clears."""
    canvas = bg().convert("RGBA") if with_field else Image.new("RGBA", (W, H), (0, 0, 0, 0))

    enter = ease_out(seg(sec, 0.00, 0.46))
    travel = W * 0.62 * (1 - enter)

    letter_in = ease_out(seg(sec, 0.10, 0.60))
    scale = 0.70 + 0.30 * letter_in
    out = ease_in(seg(sec, 1.42, 1.92))
    total = 1 - out

    mark().draw(
        canvas,
        W / 2,
        H / 2,
        300 * scale,
        dx=(-travel, 0, travel),
        alpha=(total, letter_in * total, total),
    )
    return canvas


# ---------------------------------------------------------------- encode
def encode(path, frames, fps, alpha=False, crf=18):
    w, h = frames[0].size
    pix = "rgba" if alpha else "rgb24"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
    ]
    if alpha:
        cmd += [
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(crf),
            "-row-mt", "1", "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "2",
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
    cmd.append(str(path))

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        proc.stdin.write(f.convert("RGBA" if alpha else "RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")
    print(f"  {path.name:34} {path.stat().st_size / 1024 / 1024:6.2f} MB")


def render(name, frames, fps, alpha=False, crf=18):
    path = OUT / name
    encode(path, frames, fps, alpha=alpha, crf=crf)


def build_screens():
    labels = {
        "starting": ("STARTING SOON", None),
        "brb": ("BE RIGHT BACK", None),
        "ending": ("THANKS FOR WATCHING", "@ASHTYN"),
    }
    fps = 30
    n = round(LOOP * fps)
    for key, (text, sub) in labels.items():
        cap = mono(text, 34, 0.30, (*ASH, 255))
        sub_sprite = mono(sub, 22, 0.34, (*IRIS, 255)) if sub else None
        frames = [screen(i / fps, cap, sub_sprite) for i in range(n)]
        render(f"screen-{key}.mp4", frames, fps, crf=20)
        frames[0].convert("RGB").save(OUT / f"screen-{key}-still.png")


def build_stinger():
    n = round(STINGER_SECS * 60)
    frames = [stinger_frame(i / 60) for i in range(n)]

    # find where the plate actually covers the whole frame, and cut in the middle of it
    covered = []
    for i, f in enumerate(frames):
        a = np.asarray(f.getchannel("A"))
        if a[::80, ::120].min() == 255:
            covered.append(i / 60)
    if not covered:
        raise RuntimeError("plate never fully covers the frame")
    point = (covered[0] + covered[-1]) / 2
    print(f"  full coverage {covered[0]:.2f}s to {covered[-1]:.2f}s")
    print(f"  transition point {round(point * 1000)} ms")

    render("twitch-stinger-1080p60.webm", frames, 60, alpha=True, crf=24)
    # a still from the assembly, not from the held cover (which is just flat charcoal)
    frames[round(0.46 * 60)].save(OUT / "twitch-stinger-still.png")


def build_intro():
    n = round(INTRO_SECS * 60)
    frames = [intro_frame(i / 60, with_field=True) for i in range(n)]
    render("youtube-intro-1080p60.mp4", frames, 60, crf=17)
    frames[54].convert("RGB").save(OUT / "youtube-intro-still.png")

    overlay = [intro_frame(i / 60, with_field=False) for i in range(n)]
    render("intro-mark-overlay-alpha.webm", overlay, 60, alpha=True, crf=26)


TARGETS = {"screens": build_screens, "stinger": build_stinger, "intro": build_intro}

if __name__ == "__main__":
    want = sys.argv[1:] or list(TARGETS)
    for name in want:
        print(f"[{name}]")
        TARGETS[name]()
    print("done")
