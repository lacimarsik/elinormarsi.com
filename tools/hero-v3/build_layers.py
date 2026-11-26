"""Build the Dřevo a erb v3 hero layers from the project's own artwork.

Writes assets/v3/plank.png + plank.webp (carved plank cut out of forest-header.jpg, rebuilt behind
the shield, 74 source rows slimmer) and assets/v3/hero-forest.jpg (the same forest frame with the
old plank area filled from the photo's own pixels).

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
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
A = os.path.join(ROOT, "assets")
OUT = os.path.join(A, "v3")
OUT_SCALE = 2  # plank is written at 3840 px wide

H1, W1 = 300, 1920
CAP_L, CAP_R = 195, 1713     # board end caps; columns outside them are the ends (ivy, wing)
BOARD = (16, 150)            # rows of the top board, barrel-shaped caps included
BAND = (70, 144)             # plain board rows removed
DELTA = BAND[1] - BAND[0]
MOSS_FADE = (12, 21)         # the moss strip along the top fades out between these rows
LEAF = (1232, 1338, 58, 94)  # the one ivy leaf that hangs into the cut band stays in place
PLANK_SCALE_MIN = 0.75       # lowest plank-to-photo scale ratio the hero produces (wide-short screens = 1)


def cap_left(y):   # barrel-shaped left end of the board, x of its outer edge per source row
    return 197 + 0.0018 * (y - 65) ** 2


def cap_right(y):
    return 1715 - 0.0018 * (y - 65) ** 2


def hsv(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    mx, mn = img.max(-1), img.min(-1)
    d = mx - mn + 1e-6
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return hue, (mx - mn) / (mx + 1e-6), mx


def plank_boundary(hdr):
    """Row per column where the plank ends and the photo starts (plank above), refined to sub-pixel."""
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
    return ndi.binary_dilation(hole > 0.04, iterations=2)


def over(top, bot):
    ta, ba = top[..., 3:4], bot[..., 3:4]
    oa = ta + ba * (1 - ta)
    oc = (top[..., :3] * ta + bot[..., :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.concatenate([oc, oa], -1)


def with_alpha(img, m):
    return np.concatenate([img[..., :3], img[..., 3:4] * m[..., None]], -1)


def shift_up(img, n):
    return np.concatenate([img[n:], np.zeros_like(img[:n])], 0)


def build_plank(hdr, ysub, hole1, strip, S):
    hue, sat, val = hsv(hdr[:H1])
    ivy1 = (hue > 50) & (hue < 120) & (sat > 0.22) & (val > 0.18)
    ivy1 = ndi.binary_dilation(ndi.binary_closing(ivy1, iterations=1), iterations=1).astype(np.float32)
    # photo fringe baked into the carved edge: light or green/blue pixels just inside the contour
    rows1 = np.arange(H1)[:, None]
    near = (rows1 >= np.floor(ysub)[None, :] - 3) & (rows1 <= np.floor(ysub)[None, :] + 1)
    warm = ((hue <= 48) | (hue >= 335)) & (sat >= 0.15)
    whitish = (sat < 0.18) & (val > 0.45)
    fringe1 = (near & (~warm | whitish) & (val > 0.3)).astype(np.float32)

    H, W = H1 * S, W1 * S
    up = lambda m: m.astype(np.float32) if S == 1 else np.asarray(
        Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    xs = (np.arange(W) + 0.5) / S - 0.5
    rows = np.arange(H, dtype=np.float32)[:, None]

    st = strip.copy()
    yS = S * (np.interp(xs, np.arange(W1), ysub) - 0.35)
    alpha = ndi.gaussian_filter(np.clip(yS[None, :] - rows, 0, 1), 0.45 * S)
    alpha = alpha * (1 - ndi.gaussian_filter(up(fringe1), 0.5 * S))
    inner = np.vstack([st[:3 * S], st[:-3 * S]])  # edge pixels take the wood colour from inside
    edge = (alpha > 0.002) & (rows >= (yS[None, :] - 4 * S))
    st[edge] = inner[edge]
    P = np.dstack([st, alpha])

    # rebuild the wood behind the shield: mirror both neighbours inward and cross-fade in the middle;
    # above the rail the mirror axes are fixed at the shield's full width so grain and ivy stay straight
    hole = ndi.binary_dilation(up(hole1[:H1].astype(np.float32)) > 0.5, iterations=S)
    hx = np.where(hole.any(0))[0]
    box = (int(hx.min()), int(hx.max()))
    pre = P.copy(); pre[..., :3] *= pre[..., 3:4]
    for y in range(H):
        xr_ = np.where(hole[y])[0]
        if len(xr_) == 0:
            continue
        xa, xb = (box if y < 150 * S else (int(xr_.min()), int(xr_.max())))
        x = np.arange(xa, xb + 1)
        t = (x - xa) / max(xb - xa, 1)
        wl = 0.5 * (1 + np.cos(np.pi * np.clip((t - 0.44) / 0.12, 0, 1)))[:, None]
        pre[y, xa:xb + 1] = wl * pre[y, np.clip(2 * xa - 1 - x, 0, W - 1)] + (1 - wl) * pre[y, np.clip(2 * xb + 1 - x, 0, W - 1)]
    a = pre[..., 3:4]
    P = np.concatenate([np.where(a > 1e-4, pre[..., :3] / np.maximum(a, 1e-4), 0), a], -1)

    # split into the board (with its barrel-shaped end caps) and the ends (ivy, moss, wings)
    ysrc = (rows + 0.5) / S - 0.5
    xsrc = xs[None, :]
    in_board_rows = (ysrc >= BOARD[0]) & (ysrc <= BOARD[1])
    mb = ((xsrc >= CAP_L) & (xsrc <= CAP_R)).astype(np.float32) * np.ones_like(ysrc)
    capl = np.clip((xsrc - cap_left(ysrc)) * S + 0.5, 0, 1)
    capr = np.clip((cap_right(ysrc) - xsrc) * S + 0.5, 0, 1)
    zone_l = (xsrc >= CAP_L - 10) & (xsrc <= 222)
    zone_r = (xsrc >= 1690) & (xsrc <= CAP_R + 8)
    mb = np.where(in_board_rows & zone_l, capl, mb)
    mb = np.where(in_board_rows & zone_r, capr, mb)
    ends = (xsrc < 230) | (xsrc > 1683)
    B = with_alpha(P, mb)
    E = with_alpha(P, (1 - mb) * ends)

    b1, b2, dl = BAND[0] * S, BAND[1] * S, DELTA * S
    Bc = np.zeros_like(B)
    Bc[:b1] = B[:b1]
    Bc[b1:H - dl] = B[b2:]
    # caps: squeeze the whole board height into the slimmer board so the barrel ends stay rounded
    top, bot = BOARD[0] * S, BOARD[1] * S
    new_bot = bot - dl
    yo = np.arange(top, new_bot + 1)
    yi = top + (yo - top) * (bot - top) / (new_bot - top)
    y0i = np.floor(yi).astype(int); fy = (yi - y0i)[:, None, None]
    Bpre = B.copy(); Bpre[..., :3] *= Bpre[..., 3:4]
    C = Bpre[y0i] * (1 - fy) + Bpre[np.minimum(y0i + 1, H - 1)] * fy
    wx = np.clip(np.maximum((246 - xs) / 30.0, (xs - 1662) / 30.0), 0, 1)[None, :, None]
    Bcp = Bc.copy(); Bcp[..., :3] *= Bcp[..., 3:4]
    Bcp[top:new_bot + 1] = Bcp[top:new_bot + 1] * (1 - wx) + C * wx
    a = Bcp[..., 3:4]
    Bf = np.concatenate([np.where(a > 1e-4, Bcp[..., :3] / np.maximum(a, 1e-4), 0), a], -1)

    Es = shift_up(E, dl)
    # behind the cap edges, carry the shifted ivy/wing a few pixels further in so no gap opens
    for x0, x1, step in ((int(185 * S), int(214 * S), 1), (int(1716 * S), int(1694 * S), -1)):
        for x in range(x0, x1, step):
            m = (Es[:, x, 3] < 0.5) & (Es[:, x - step, 3] >= 0.5) & (np.arange(H) < 90 * S)
            Es[m, x] = Es[m, x - step]
    # the moss strip stays where it is across the full width, behind the raised ivy and the board;
    # above the caps it also lies in front of the ivy, so the ivy's edge that the cap used to hide fades into it
    fade = np.clip((MOSS_FADE[1] * S - rows) / ((MOSS_FADE[1] - MOSS_FADE[0]) * S), 0, 1)
    moss = with_alpha(P, fade.repeat(W, 1))
    reach = np.clip(np.minimum((xs - 178) / 18.0, (1735 - xs) / 18.0), 0, 1)[None, :]
    moss_front = with_alpha(P, fade * reach)
    body = with_alpha(Bf, (rows >= BOARD[0] * S).astype(np.float32).repeat(W, 1))
    O = over(body, over(moss_front, over(Es, moss)))

    lx0, lx1, ly0, ly1 = [v * S for v in LEAF]
    leaf = np.zeros_like(P)
    lm = ndi.gaussian_filter(up(ivy1)[ly0:ly1, lx0:lx1][..., None], (0.6 * S, 0.6 * S, 0))
    leaf[ly0:ly1, lx0:lx1] = np.concatenate([P[ly0:ly1, lx0:lx1, :3], P[ly0:ly1, lx0:lx1, 3:4] * lm], -1)
    O = over(leaf, O)
    bottom = int(np.where(O[..., 3].max(1) > 0.02)[0].max()) + 2 * S
    return O[:bottom]


def poisson_fill(frame, known, omega, guide):
    """Fill omega so its gradients follow guide and it meets the known pixels without a seam."""
    H, W = known.shape
    idx = -np.ones((H, W), np.int64)
    ys, xs = np.where(omega)
    n = len(ys)
    idx[ys, xs] = np.arange(n)
    diag = np.zeros(n)
    rr, cc = [], []
    b = np.zeros((n, 3))
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        yy, xx = ys + dy, xs + dx
        ins = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        yyc, xxc = np.clip(yy, 0, H - 1), np.clip(xx, 0, W - 1)
        nb_o = ins & (idx[yyc, xxc] >= 0)
        nb_k = ins & known[yyc, xxc] & ~nb_o
        valid = nb_o | nb_k
        diag += valid
        p = np.where(nb_o)[0]
        rr.append(p); cc.append(idx[yyc[p], xxc[p]])
        b[nb_k] += frame[yyc[nb_k], xxc[nb_k]]
        b[valid] += guide[ys[valid], xs[valid]] - guide[yyc[valid], xxc[valid]]
    rr = np.concatenate([np.arange(n)] + rr); cc = np.concatenate([np.arange(n)] + cc)
    vals = np.concatenate([diag, -np.ones(len(rr) - n)])
    M = coo_matrix((vals, (rr, cc)), shape=(n, n)).tocsr()
    out = frame.copy()
    for ch in range(3):
        x0 = guide[ys, xs, ch]
        sol, _ = cg(M, b[:, ch], x0=x0, rtol=1e-5, maxiter=3000)
        out[ys, xs, ch] = sol
    return out


def build_photo(hdr, ysub, hole1):
    """The header frame with the old plank (and the shield's shadow) replaced by forest from the photo."""
    H, W = hdr.shape[:2]
    yy = np.arange(H)[:, None]
    unknown = (yy < np.ceil(ysub)[None, :] + 3) | hole1[:H]
    unknown[330:] = False
    known = ~unknown
    # the part of the old plank area that can show under the new plank on any screen
    ymin = np.maximum(0, PLANK_SCALE_MIN * (ysub - DELTA) - 12)
    omega = unknown & (yy >= ymin[None, :])
    need = ysub + 3 - ymin
    T = ndi.gaussian_filter1d(ndi.maximum_filter1d(need, 81), 30) + 6
    x = np.arange(W)
    # forest copied up from below; around the client's head it comes from beside her instead
    beta = np.clip(np.minimum((x - 800) / 50.0, (1210 - x) / 50.0), 0, 1)
    ys_ = np.clip(yy + T[None, :].astype(int), 0, H - 1)
    side = hdr[ys_, x[None, :]]
    ysc = np.clip(yy + 130, 0, H - 1)
    centre = hdr[ysc, np.clip(x + 420, 0, W - 1)[None, :]]
    guide = side * (1 - beta[None, :, None]) + centre * beta[None, :, None]
    out = poisson_fill(hdr.astype(np.float64), known, omega, guide.astype(np.float64))
    hidden = unknown & ~omega
    out[hidden] = guide[hidden] * 0.35 + 0.02
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))


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
    ysub = plank_boundary(hdr)
    hole1 = shield_hole(hdr)
    O = build_plank(hdr, ysub, hole1, st, OUT_SCALE)
    im = Image.fromarray((np.clip(O, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    im.save(os.path.join(OUT, "plank.png"), optimize=True)
    im.save(os.path.join(OUT, "plank.webp"), quality=90, method=6, alpha_quality=100)
    build_photo(hdr, ysub, hole1).save(os.path.join(OUT, "hero-forest.jpg"), quality=92, optimize=True, progressive=True)
    print("plank", im.size, "-> assets/v3/plank.{png,webp}; photo -> assets/v3/hero-forest.jpg")


if __name__ == "__main__":
    main()
