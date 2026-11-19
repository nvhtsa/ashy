"""Render the mark as a physical object: an extruded, bevelled slab with a lit lens.

No GPU and no Blender on this machine, so this is a small signed-distance
raymarcher in numpy. The glyph comes from the same font render the flat exports
use, so the object and the flat mark are literally the same letterform.

The scene is built the way dimensional signage is: a halo-lit letter standing off
a wall, with the counter glazed so the light behind it reads as a lens.

    python brand/src/render_mark_3d.py             # hero square + avatar + banner
    python brand/src/render_mark_3d.py probe 380   # quick low-res look and timing

Conventions: object space is in SDF texels, +z toward the camera, +y down.
"""
import pathlib
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_mark as flat  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT.parent / "export"
LAYERS = ROOT / "layers"

TEX = 1300                # SDF texture size
GLYPH_FILL = 0.60         # glyph height as a share of the texture
DEPTH = 96.0              # slab thickness, texels
BEVEL = 26.0              # rounded edge radius, texels
YAW, PITCH = 10.0, 4.0    # degrees; small, so the counter stays readable
FOCAL = 4.0               # long lens: less distortion, object fills more frame

CHARCOAL = np.array([20, 18, 26], np.float32) / 255
SMOKE = np.array([233, 229, 221], np.float32) / 255
IRIS = np.array([155, 138, 240], np.float32) / 255

# "satin" = the matte smoke object; "chrome" = mirrored studio environment
MATERIAL = "satin"


def environment(r):
    """A procedural studio for reflections: white ceiling, hard horizon, dark floor,
    two strip lights. Chrome only reads as chrome if the thing it reflects has edges."""
    ry = r[..., 1]
    up = np.clip(-ry, 0, 1)
    sky = np.array([0.86, 0.97, 1.0], np.float32) * (0.35 + 0.85 * up[..., None] ** 0.55)
    floor = np.array([0.02, 0.03, 0.05], np.float32) + np.array([0.02, 0.10, 0.13], np.float32) * (
        np.clip(1 - up, 0, 1)[..., None] ** 2
    )
    horizon = np.clip(1 - np.abs(ry) / 0.06, 0, 1)[..., None]
    base = np.where((ry < 0)[..., None], sky, floor) + horizon * np.array([0.55, 0.95, 1.0], np.float32)

    rx = r[..., 0]
    strip = np.exp(-((np.abs(rx) - 0.42) / 0.08) ** 2) * 0.75
    strip += np.exp(-((np.abs(rx) - 0.78) / 0.05) ** 2) * 0.45
    warm = np.exp(-((rx + 0.62) / 0.10) ** 2) * np.exp(-((ry + 0.25) / 0.25) ** 2) * 0.35
    return base + (strip[..., None] * np.array([0.45, 0.92, 1.0], np.float32)) + warm[..., None] * IRIS


# ------------------------------------------------------------------ distance field


def dt1d(f):
    """Exact 1-D squared Euclidean distance transform (Felzenszwalb & Huttenlocher)."""
    n = f.size
    d = np.empty(n, np.float64)
    v = np.zeros(n, np.int64)
    z = np.zeros(n + 1, np.float64)
    k = 0
    z[0], z[1] = -np.inf, np.inf
    for q in range(1, n):
        fq = f[q] + q * q
        s = (fq - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k])
        while s <= z[k]:
            k -= 1
            s = (fq - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k])
        k += 1
        v[k], z[k], z[k + 1] = q, s, np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        d[q] = (q - v[k]) ** 2 + f[v[k]]
    return d


def edt(seeds):
    f = np.where(seeds, 0.0, 1e12)
    rows = np.apply_along_axis(dt1d, 1, f)
    return np.sqrt(np.apply_along_axis(dt1d, 0, rows))


def blur_f(field, sigma):
    """Separable Gaussian on a float array (PIL only blurs 8-bit modes)."""
    radius = max(1, int(np.ceil(sigma * 3)))
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, field)
    return np.apply_along_axis(lambda c: np.convolve(c, k, mode="same"), 0, out)


def build_field():
    """Signed distance to the glyph outline, in texels, zero on the edge."""
    mask = flat.render_text("a", 900)
    height = round(TEX * GLYPH_FILL)
    width = round(mask.width * height / mask.height)
    mask = mask.resize((width, height), Image.LANCZOS)

    canvas = Image.new("L", (TEX, TEX), 0)
    canvas.paste(mask, ((TEX - width) // 2, (TEX - height) // 2))
    ink = np.asarray(canvas) > 127

    outside = edt(ink)        # background pixel → nearest ink
    inside = edt(~ink)        # ink pixel → nearest background
    sd = np.where(ink, -(inside - 0.5), outside - 0.5)
    # The EDT is quantised to whole texels; blurring it in the float domain is what
    # turns stair-stepped normals into smooth bevels on the lit surface.
    return blur_f(sd.astype(np.float32), 2.2)


FIELD = build_field()


def sample_sd(x, y):
    """Bilinear lookup of the 2-D field, a far value outside the texture."""
    h, w = FIELD.shape
    fx, fy = x + w / 2 - 0.5, y + h / 2 - 0.5
    x0 = np.floor(fx).astype(np.int32)
    y0 = np.floor(fy).astype(np.int32)
    tx, ty = fx - x0, fy - y0
    ok = (x0 >= 0) & (y0 >= 0) & (x0 + 1 < w) & (y0 + 1 < h)
    x0c, y0c = np.clip(x0, 0, w - 2), np.clip(y0, 0, h - 2)
    flat_field = FIELD.reshape(-1)
    i = y0c * w + x0c
    a, b = flat_field[i], flat_field[i + 1]
    c, d = flat_field[i + w], flat_field[i + w + 1]
    top = a + (b - a) * tx
    bottom = c + (d - c) * tx
    return np.where(ok, top + (bottom - top) * ty, 64.0)


def sd3(x, y, z):
    """Rounded slab around the glyph: extrusion and bevel in one expression."""
    d2 = sample_sd(x, y) + BEVEL
    dz = np.abs(z) - (DEPTH * 0.5 - BEVEL)
    outside = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dz, 0) ** 2)
    return outside + np.minimum(np.maximum(d2, dz), 0) - BEVEL


# ------------------------------------------------------------------ camera + march


def rotation(yaw, pitch):
    ry, rx = np.radians(yaw), np.radians(pitch)
    ry_m = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    rx_m = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    return ry_m @ rx_m


EYE = rotation(YAW, PITCH).T @ np.array([0, 0, TEX * 2.1])


def render(res, aa=2):
    """Return premultiplied colour and coverage for the object alone."""
    rot = rotation(YAW, PITCH)
    premult = np.zeros((res, res, 3), np.float32)
    alpha = np.zeros((res, res, 1), np.float32)

    for ay in range(aa):
        for ax in range(aa):
            px = (np.arange(res) + (ax + 0.5) / aa) / res * 2 - 1
            py = (np.arange(res) + (ay + 0.5) / aa) / res * 2 - 1
            gx, gy = np.meshgrid(px, py)
            d_cam = np.stack([gx / FOCAL, gy / FOCAL, -np.ones_like(gx)], -1).reshape(-1, 3)
            d = d_cam @ rot
            d /= np.linalg.norm(d, axis=1, keepdims=True)

            p = np.tile(EYE, (d.shape[0], 1))
            alive = np.ones(d.shape[0], bool)
            for _ in range(96):
                idx = np.flatnonzero(alive)
                if idx.size == 0:
                    break
                q = p[idx]
                s = sd3(q[:, 0], q[:, 1], q[:, 2])
                hit = s < 0.45
                if hit.any():
                    alive[idx[hit]] = False
                rest = idx[~hit]
                if rest.size:
                    step = np.clip(s[~hit], 0.8, None)
                    p[rest] += d[rest] * step[:, None]
                    far = np.linalg.norm(p[rest] - EYE, axis=1) > 4.2 * TEX
                    alive[rest[far]] = False

            covered = ~alive & (sd3(p[:, 0], p[:, 1], p[:, 2]) < 0.45)
            shade_out = shade(p, d, covered)
            premult += shade_out[..., :3].reshape(res, res, 3)
            alpha += shade_out[..., 3:4].reshape(res, res, 1)

    return premult / (aa * aa), alpha / (aa * aa)


def shade(p, d, covered):
    """Studio lighting: key, fill, rim, fresnel, occlusion and a soft key shadow."""
    out = np.zeros((p.shape[0], 4), np.float32)
    idx = np.flatnonzero(covered)
    if idx.size == 0:
        return out

    q = p[idx]
    # a wide epsilon: the field is blurred but still quantised, and a narrow gradient
    # turns that into ribbing along the extruded side walls
    e = 2.2
    n = np.stack(
        [
            sd3(q[:, 0] + e, q[:, 1], q[:, 2]) - sd3(q[:, 0] - e, q[:, 1], q[:, 2]),
            sd3(q[:, 0], q[:, 1] + e, q[:, 2]) - sd3(q[:, 0], q[:, 1] - e, q[:, 2]),
            sd3(q[:, 0], q[:, 1], q[:, 2] + e) - sd3(q[:, 0], q[:, 1], q[:, 2] - e),
        ],
        -1,
    )
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)

    v = -d[idx]
    n_dot_v = np.maximum((n * v).sum(1), 0.0)

    if MATERIAL == "chrome":
        refl = 2 * n_dot_v[:, None] * n - v
        refl /= np.maximum(np.linalg.norm(refl, axis=1, keepdims=True), 1e-6)
        lit = environment(refl)
        fres = (1 - n_dot_v) ** 2.2
        lit = lit * (0.92 + 0.35 * fres[:, None]) + IRIS * (fres[:, None] * 0.28)
        out[idx, :3] = np.clip(lit, 0, 1)
        out[idx, 3] = 1.0
        return out

    key = np.array([-0.40, -0.62, 0.60]); key /= np.linalg.norm(key)
    fill = np.array([0.74, -0.12, 0.42]); fill /= np.linalg.norm(fill)
    rim = np.array([0.24, 0.60, -0.34]); rim /= np.linalg.norm(rim)

    diff_key = np.maximum((n * key).sum(1), 0.0)
    diff_fill = np.maximum((n * fill).sum(1), 0.0)
    diff_rim = np.maximum((n * rim).sum(1), 0.0)

    half = key + v
    half /= np.maximum(np.linalg.norm(half, axis=1, keepdims=True), 1e-6)
    spec = np.maximum((n * half).sum(1), 0.0) ** 54
    sheen = n_dot_v ** 5

    ao = np.ones(idx.size, np.float32)
    for dist, weight in ((5.0, 0.5), (14.0, 0.3), (32.0, 0.22)):
        s = sd3(q[:, 0] + n[:, 0] * dist, q[:, 1] + n[:, 1] * dist, q[:, 2] + n[:, 2] * dist)
        ao -= weight * np.clip(1 - s / dist, 0, 1)
    ao = np.clip(ao, 0.12, 1.0)

    occ = np.zeros(idx.size, np.float32)
    for step in range(1, 15):
        dist = step * 8.0
        s = sd3(q[:, 0] + key[0] * dist, q[:, 1] + key[1] * dist, q[:, 2] + key[2] * dist)
        occ = np.maximum(occ, np.clip(1 - s / (dist * 0.5), 0, 1) * (1 - step / 16))
    shadow = 1 - 0.72 * occ

    ambient = 0.13 * (0.6 + 0.4 * (-n[:, 1] * 0.5 + 0.5))
    lit = (
        SMOKE[None, :] * (ambient[:, None] * ao[:, None])
        + SMOKE[None, :] * (diff_key[:, None] * 1.02 * shadow[:, None] * ao[:, None])
        + SMOKE[None, :] * (diff_fill[:, None] * 0.20)
        + IRIS[None, :] * (diff_rim[:, None] * 0.22)
    )
    lit += np.array([1.0, 0.995, 0.98])[None, :] * (spec[:, None] * 0.46 * shadow[:, None] * ao[:, None])
    lit += np.array([1.0, 0.98, 0.96])[None, :] * (sheen[:, None] * 0.04)
    lit += IRIS[None, :] * (((1 - n_dot_v) ** 3)[:, None] * 0.10)

    out[idx, :3] = np.clip(lit, 0, 1)
    out[idx, 3] = 1.0
    return out


# ------------------------------------------------------------------ compositing


def over(dst_p, dst_a, src_p, src_a):
    out_a = src_a + dst_a * (1 - src_a)
    out_p = src_p + dst_p * (1 - src_a)
    return out_p, out_a


def layers(res, aa=2):
    """Object, halo and lens as premultiplied layers, so any backdrop works."""
    premult, alpha = render(res, aa)
    mask_img = Image.fromarray((alpha[..., 0] * 255).astype(np.uint8), "L")

    glow = np.asarray(mask_img.filter(ImageFilter.GaussianBlur(res * 0.030)), np.float32) / 255
    tight = np.asarray(mask_img.filter(ImageFilter.GaussianBlur(res * 0.008)), np.float32) / 255
    halo_a = np.clip(tight * 0.55 + glow * 0.45, 0, 1) * (1 - alpha[..., 0])

    holes = np.asarray(flat.hole_mask(mask_img))
    holes = np.clip(holes.astype(np.float32) / 255, 0, 1)[..., None]

    lens = np.zeros((res, res, 3), np.float32)
    if holes.max() > 0.1:
        ys, xs = np.nonzero(holes[..., 0] > 0.5)
        cy, cx = ys.mean(), xs.mean()
        radius = max(6.0, np.sqrt(((ys - cy) ** 2 + (xs - cx) ** 2).max()))
        gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
        dist = np.sqrt((gy - cy) ** 2 + (gx - cx) ** 2) / radius

        body = IRIS[None, None, :] * (0.30 + 0.62 * np.clip(1 - dist, 0, 1) ** 0.9)[..., None]
        hot = np.exp(-(((gx - (cx - radius * 0.34)) ** 2 + (gy - (cy - radius * 0.36)) ** 2) / (2 * (radius * 0.34) ** 2)))
        rimline = np.clip(1 - np.abs(dist - 0.80) / 0.18, 0, 1)
        seat = np.clip((dist - 0.90) / 0.10, 0, 1)

        lens = body + IRIS[None, None, :] * (rimline[..., None] * 0.30)
        lens += np.array([0.85, 0.83, 0.92])[None, None, :] * (hot[..., None] * 0.55)
        lens *= (1 - 0.60 * seat[..., None])

    return premult, alpha, lens * holes, halo_a[..., None]


def compose(res, background=None, aa=2):
    premult, alpha, lens, halo_a = layers(res, aa)

    if background is None:
        dst_p = np.zeros((res, res, 3), np.float32)
        dst_a = np.zeros((res, res, 1), np.float32)
    else:
        dst_p = np.broadcast_to(background[None, None, :], (res, res, 3)).copy()
        dst_a = np.ones((res, res, 1), np.float32)

    dst_p, dst_a = over(dst_p, dst_a, IRIS[None, None, :] * halo_a, halo_a * 0.75)
    dst_p, dst_a = over(dst_p, dst_a, lens, np.clip(lens.max(-1, keepdims=True) * 3.2, 0, 1))
    dst_p, dst_a = over(dst_p, dst_a, premult, alpha)

    if background is not None:
        return Image.fromarray((np.clip(dst_p, 0, 1) * 255).astype(np.uint8), "RGB")

    rgba = np.dstack([np.clip(dst_p, 0, 1), np.clip(dst_a, 0, 1)])
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


def wall(w, h=None):
    """Flat charcoal with the same gentle falloff the scene uses."""
    h = h or w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fall = 1.0 - 0.30 * (((xx - w * 0.45) / w) ** 2 + ((yy - h * 0.38) / h) ** 2)
    return np.clip(CHARCOAL[None, None, :] * fall[..., None], 0, 1)


# ------------------------------------------------------------------ outputs


def hero_square(res=1240):
    premult, alpha, lens, halo_a = layers(res, aa=2)
    base_p = wall(res, res)
    base_a = np.ones((res, res, 1), np.float32)
    # a halo-lit sign throws light on the wall behind it, and a soft shadow below
    shadow_src = Image.fromarray((alpha[..., 0] * 255).astype(np.uint8), "L")
    shifted = shadow_src.transform(
        shadow_src.size, Image.AFFINE, (1, 0, -res * 0.012, 0, 1, -res * 0.020), resample=Image.BILINEAR
    ).filter(ImageFilter.GaussianBlur(res * 0.020))
    shadow = np.asarray(shifted, np.float32)[..., None] / 255
    base_p = base_p * (1 - 0.55 * shadow)

    p, a = over(base_p, base_a, IRIS[None, None, :] * halo_a, halo_a * 0.85)
    p, a = over(p, a, lens, np.clip(lens.max(-1, keepdims=True) * 3.2, 0, 1))
    p, a = over(p, a, premult, alpha)
    return Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8), "RGB")


def banner(res=1300, glyph_px=300):
    """2560 × 1440: object and wordmark side by side inside the 1546 × 423 safe band."""
    ob = compose(res, background=None, aa=2)
    alpha = ob.getchannel("A")
    bb = alpha.getbbox()
    pad = round((bb[2] - bb[0]) * 0.10)
    crop = ob.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad))
    scale = glyph_px / (bb[3] - bb[1])
    obj = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.LANCZOS)

    word = flat.wordmark(400, flat.SMOKE, flat.IRIS)
    word = flat.fit(word, width=470)

    canvas = Image.new("RGBA", (2560, 1440), (0, 0, 0, 255))
    canvas.paste(Image.fromarray((wall(2560, 1440) * 255).astype(np.uint8), "RGB"), (0, 0))

    # object and name read as one lockup, centred in the 1546 × 423 safe band
    gap = 96
    total = obj.width + gap + word.width
    left = round(1280 - total / 2)
    canvas.alpha_composite(obj, (left, round(715 - obj.height / 2)))
    canvas.alpha_composite(word, (left + obj.width + gap, round(715 - word.height / 2)))
    return canvas.convert("RGB")


def export():
    t0 = time.time()
    hero = hero_square()
    hero.save(OUT / "mark-3d-square.png")
    print(f"  mark-3d-square.png            {hero.size}   {time.time() - t0:.0f}s")

    crop = round(hero.width * 0.80)
    x0 = (hero.width - crop) // 2
    y0 = round((hero.height - crop) / 2 + hero.height * 0.015)
    hero.crop((x0, y0, x0 + crop, y0 + crop)).resize((1024, 1024), Image.LANCZOS).save(
        OUT / "profile-3d-1024.png"
    )

    b = banner()
    b.save(OUT / "youtube-banner-3d-2560x1440.png")

    for f in ("mark-3d-square.png", "profile-3d-1024.png", "youtube-banner-3d-2560x1440.png"):
        im = Image.open(OUT / f)
        print(f"  {f:32} {im.size} {im.mode}")


if __name__ == "__main__":
    if "probe" in sys.argv:
        res = int(sys.argv[sys.argv.index("probe") + 1])
        t0 = time.time()
        hero_square(res).save(LAYERS / "_probe3d.png")
        print(f"probe {res}px in {time.time() - t0:.1f}s")
    else:
        export()
