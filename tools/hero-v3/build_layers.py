"""Build the Dřevo a erb v3 hero layers from the project's own artwork.

Writes assets/v3/plank.png + plank.webp (carved plank cut out of forest-header.jpg, rebuilt behind
the shield, 74 source rows slimmer) and assets/v3/hero-forest.jpg (forest-only.jpg in its original
place, with the rows above it filled from its own top rows).

usage (from the repo root):
  python3 tools/hero-v3/build_layers.py                  # Lanczos 2x plank
  python3 tools/hero-v3/build_layers.py STRIP.png 4      # sharper upscale of header rows 0-299 at 4x
Needs numpy, scipy and Pillow. All geometry is in 1920-px source pixels, scaled by the strip factor.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
A = os.path.join(ROOT, "assets")
OUT = os.path.join(A, "v3")
OUT_SCALE = 2  # plank is written at 3840 px wide

H1, W1 = 300, 1920
CAP_L, CAP_R = 195, 1713     # board end caps; columns outside them are the ends (ivy, wing)
BAND = (70, 144)             # plain board rows removed in board columns
DELTA = BAND[1] - BAND[0]
END_BACK_SHIFT = 40          # the ends' top rows are backed by the same columns moved up this much
MOSS_FADE = (14, 24)         # ...fading out between these rows, so the moss strip runs full width
LEAF = (1232, 1338, 58, 94)  # the one ivy leaf that hangs into the cut band stays in place


def hsv(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    mx, mn = img.max(-1), img.min(-1)
    d = mx - mn + 1e-6
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return hue, (mx - mn) / (mx + 1e-6), mx


def plank_boundary(hdr):
    """Row per column where the plank ends and the photo starts (plank above), plus a sub-pixel refine."""
    H = 330
    rgb = hdr[:H]
    hue, sat, _ = hsv(rgb)
    r, g = rgb[..., 0], rgb[..., 1]
    gray = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    lap = ndi.laplace(ndi.gaussian_filter(gray, 0.7))
    sharp = np.sqrt(ndi.uniform_filter(lap ** 2, 7))
    sharp_n = np.clip(sharp / np.percentile(sharp[:60], 50), 0, 1.5) / 1.5  # moss rows define "crisp"
    brown = ((hue < 40) | (hue > 345)) & (r > g * 1.08) & (sat > 0.22)
    p = np.clip(np.maximum(ndi.uniform_filter(brown.astype(np.float32), 3), sharp_n * 0.9), 0, 1)
    above = np.vstack([np.zeros((1, W1), np.float32), np.cumsum(1 - p, axis=0)])
    below = np.vstack([np.cumsum(p[::-1], axis=0)[::-1], np.zeros((1, W1), np.float32)])
    cost = above + below
    K, lam = 14, 0.35
    acc = cost[:, 0].copy()
    back = np.zeros((H + 1, W1), np.int16)
    ys = np.arange(H + 1)
    for x in range(1, W1):
        best = np.full(H + 1, np.inf, np.float32)
        arg = np.zeros(H + 1, np.int16)
        for dy in range(-K, K + 1):
            src = np.clip(ys + dy, 0, H)
            cand = acc[src] + lam * abs(dy)
            m = cand < best
            best[m] = cand[m]
            arg[m] = src[m]
        acc = best + cost[:, x]
        back[:, x] = arg
    yb = np.zeros(W1, np.int32)
    yb[-1] = int(np.argmin(acc))
    for x in range(W1 - 1, 0, -1):
        yb[x - 1] = back[yb[x], x]
    # refine to the strongest vertical colour change near the path
    sm = ndi.gaussian_filter(hdr[:H1], sigma=(0.7, 0.7, 0))
    gy = np.abs(np.diff(sm, axis=0)).sum(-1)
    ysub = np.empty(W1, np.float32)
    for x in range(W1):
        k0 = int(np.clip(yb[x] - 4, 0, H1 - 3)); k1 = int(np.clip(yb[x] + 2, k0 + 2, H1 - 2))
        seg = gy[k0:k1, x]
        k = int(np.argmax(seg))
        off = 0.0
        if 0 < k < len(seg) - 1:
            a, b, c = seg[k - 1], seg[k], seg[k + 1]
            den = a - 2 * b + c
            off = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5)) if den != 0 else 0.0
        ysub[x] = k0 + k + 1 + off
    return ndi.median_filter(ysub, size=3)


def shield_hole(hdr):
    """Mask of the baked shield (and its shadow), found by fitting shield.png into the header."""
    sh = Image.open(os.path.join(A, "shield.png")).convert("RGBA")
    best = None
    for sc in np.arange(0.262, 0.292, 0.002):
        w, h = round(sh.size[0] * sc), round(sh.size[1] * sc)
        s = np.asarray(sh.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
        core = s[..., 3] > 0.97
        ox0, oy0 = int(825 - 119 * sc), int(6 - 33 * sc)
        for ox in range(ox0 - 8, ox0 + 9):
            for oy in range(oy0 - 8, oy0 + 9):
                if ox < 0:
                    continue
                y0 = max(oy, 0)
                sub = hdr[y0:oy + h, ox:ox + w]
                ss = s[y0 - oy:, :, :3][: sub.shape[0]]
                cm = core[y0 - oy:][: sub.shape[0]]
                err = np.abs(sub - ss)[cm].mean()
                if best is None or err < best[0]:
                    best = (err, sc, ox, oy, w, h)
    _, sc, ox, oy, w, h = best
    s = np.asarray(sh.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
    hole = np.zeros(hdr.shape[:2], np.float32)
    y0 = max(oy, 0)
    hole[y0:oy + h, ox:ox + w] = s[y0 - oy:, :, 3]
    return ndi.binary_dilation(hole > 0.04, iterations=2)[:H1]


def over(top, bot):
    ta, ba = top[..., 3:4], bot[..., 3:4]
    oa = ta + ba * (1 - ta)
    oc = (top[..., :3] * ta + bot[..., :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.concatenate([oc, oa], -1)


def build_plank(hdr, strip, S):
    ysub = plank_boundary(hdr)
    hole1 = shield_hole(hdr)
    hue, sat, mx = hsv(hdr[:H1])
    ivy1 = ((hue > 50) & (hue < 120) & (sat > 0.22) & (mx > 0.18))
    ivy1 = ndi.binary_dilation(ndi.binary_closing(ivy1, iterations=1), iterations=1).astype(np.float32)

    H, W = H1 * S, W1 * S
    st = strip.copy()
    up = lambda m: m.astype(np.float32) if S == 1 else np.asarray(
        Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255

    xs = (np.arange(W) + 0.5) / S - 0.5
    yS = S * (np.interp(xs, np.arange(W1), ysub) - 0.35)  # sit just inside the carved edge
    rows = np.arange(H, dtype=np.float32)[:, None]
    alpha = ndi.gaussian_filter(np.clip(yS[None, :] - rows, 0, 1), 0.45 * S)
    inner = np.vstack([st[:2 * S], st[:-2 * S]])  # edge pixels take the wood colour from inside
    edge = (alpha > 0.002) & (alpha < 0.995)
    st[edge] = inner[edge]
    P = np.dstack([st, alpha])

    # rebuild the wood behind the shield: mirror both neighbours inward and cross-fade
    hole = ndi.binary_dilation(up(hole1) > 0.5, iterations=S)
    pre = P.copy(); pre[..., :3] *= pre[..., 3:4]
    for y in range(H):
        xr_ = np.where(hole[y])[0]
        if len(xr_) == 0:
            continue
        xa, xb = int(xr_.min()), int(xr_.max())
        x = np.arange(xa, xb + 1)
        t = (x - xa) / max(xb - xa, 1)
        wl = 0.5 * (1 + np.cos(np.pi * np.clip((t - 0.3) / 0.4, 0, 1)))[:, None]
        pre[y, xa:xb + 1] = wl * pre[y, np.clip(2 * xa - 1 - x, 0, W - 1)] + (1 - wl) * pre[y, np.clip(2 * xb + 1 - x, 0, W - 1)]
    a = pre[..., 3:4]
    P = np.concatenate([np.where(a > 1e-4, pre[..., :3] / np.maximum(a, 1e-4), 0), a], -1)

    shift_up = lambda img, n: np.concatenate([img[n:], np.zeros_like(img[:n])], 0)
    O = np.zeros_like(P)
    cl, cr = CAP_L * S, CAP_R * S
    b1, b2, dl, bs = BAND[0] * S, BAND[1] * S, DELTA * S, END_BACK_SHIFT * S
    O[:b1, cl:cr + 1] = P[:b1, cl:cr + 1]
    O[b1:H - dl, cl:cr + 1] = P[b2:, cl:cr + 1]
    fade = np.clip((MOSS_FADE[1] * S - rows) / ((MOSS_FADE[1] - MOSS_FADE[0]) * S), 0, 1)[..., None]
    for sl in (np.s_[:, :cl], np.s_[:, cr + 1:]):
        seg = P[sl]
        back = shift_up(seg, bs)
        back = np.concatenate([back[..., :3], back[..., 3:4] * fade], -1)
        O[sl] = over(shift_up(seg, dl), back)
    lx0, lx1, ly0, ly1 = [v * S for v in LEAF]
    leaf = np.zeros_like(P)
    lm = ndi.gaussian_filter(up(ivy1)[ly0:ly1, lx0:lx1][..., None], (0.6 * S, 0.6 * S, 0))
    leaf[ly0:ly1, lx0:lx1] = np.concatenate([P[ly0:ly1, lx0:lx1, :3], P[ly0:ly1, lx0:lx1, 3:4] * lm], -1)
    O = over(leaf, O)
    bottom = int(np.where(O[..., 3].max(1) > 0.02)[0].max()) + 2 * S
    return O[:bottom]


def build_photo():
    fo = np.asarray(Image.open(os.path.join(A, "forest-only.jpg")).convert("RGB")).astype(np.float32) / 255
    TOP = 280
    src = fo[:TOP].copy()
    # swap the client's head (top of forest-only, x ~850-1180) for forest beside it before mirroring
    x = np.arange(W1)
    wx = np.clip(np.minimum(x - 820, 1210 - x) / 40.0, 0, 1)
    wy = np.clip((np.arange(TOP) - 22) / 14.0, 0, 1)[:, None]
    w = (wy * wx[None, :])[..., None]
    left, right = np.roll(fo[:TOP], 400, axis=1), np.roll(fo[:TOP], -400, axis=1)
    side = np.where((x < 1015)[None, :, None], left, right)
    seam = np.clip(1 - np.abs(x - 1015) / 30.0, 0, 1)[None, :, None]
    side = side * (1 - seam) + 0.5 * (left + right) * seam
    src = src * (1 - w) + side * w
    # mirrored and stretched 2.5x upward, blurring and darkening with distance from the seam
    d = (TOP - 1 - np.arange(TOP)).astype(np.float32)
    s = d * 0.4
    s0 = np.floor(s).astype(int); f = (s - s0)[:, None, None]
    band = src[s0] * (1 - f) + src[np.minimum(s0 + 1, TOP - 1)] * f
    levels = [0, 1.5, 3, 5, 8]
    blurred = [band if v == 0 else ndi.gaussian_filter(band, (v, v * 0.6, 0)) for v in levels]
    sig = np.clip(d / 16.0, 0, 8)
    outb = np.zeros_like(band)
    for i in range(len(levels) - 1):
        lo, hi = levels[i], levels[i + 1]
        t = np.clip((sig - lo) / (hi - lo), 0, 1)[:, None, None]
        m = ((sig >= lo) & (sig <= hi))[:, None, None] if i < len(levels) - 2 else (sig >= lo)[:, None, None]
        outb = np.where(m, blurred[i] * (1 - t) + blurred[i + 1] * t, outb)
    u = np.clip(d / 150.0, 0, 1)
    k = (1 - 0.7 * u * u * (3 - 2 * u))[:, None, None]
    outb = outb * k + np.array([0.055, 0.045, 0.03], np.float32) * (1 - k) * 0.6
    frame = np.concatenate([outb, fo], 0)
    return Image.fromarray((np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8))


def main():
    os.makedirs(OUT, exist_ok=True)
    hdr_img = Image.open(os.path.join(A, "forest-header.jpg")).convert("RGB")
    hdr = np.asarray(hdr_img).astype(np.float32) / 255
    if len(sys.argv) > 2:
        S_in = int(sys.argv[2])
        strip = Image.open(sys.argv[1]).convert("RGB")
        assert strip.size == (W1 * S_in, H1 * S_in), strip.size
        if S_in != OUT_SCALE:
            strip = strip.resize((W1 * OUT_SCALE, H1 * OUT_SCALE), Image.LANCZOS)
    else:
        strip = hdr_img.crop((0, 0, W1, H1)).resize((W1 * OUT_SCALE, H1 * OUT_SCALE), Image.LANCZOS)
        strip = strip.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    st = np.asarray(strip).astype(np.float32) / 255
    O = build_plank(hdr, st, OUT_SCALE)
    im = Image.fromarray((np.clip(O, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    im.save(os.path.join(OUT, "plank.png"), optimize=True)
    im.save(os.path.join(OUT, "plank.webp"), quality=90, method=6, alpha_quality=100)
    build_photo().save(os.path.join(OUT, "hero-forest.jpg"), quality=92, optimize=True, progressive=True)
    print("plank", im.size, "-> assets/v3/plank.{png,webp}; photo -> assets/v3/hero-forest.jpg")


if __name__ == "__main__":
    main()
