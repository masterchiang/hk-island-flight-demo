"""扫描尺度空间参数(sigma, level)，找出"贴岸"与"平顺"的最佳折中。"""
import json, math
import numpy as np
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from scipy.special import erfinv

ROOT = r"<PROJECT_ROOT>"
tr = Transformer.from_crs("EPSG:4326", "EPSG:2326", always_xy=True)
d = json.load(open(ROOT + "/data/raw/island_geometry.json", encoding="utf-8"))
rings = sorted(d["coordinates"], key=lambda p: -len(p[0]))
outer = np.array(rings[0][0], float)
X, Y = tr.transform(outer[:, 0], outer[:, 1])
xl = np.array(X) - 840000.0; yl = np.array(Y) - 815000.0
T = json.load(open(ROOT + "/output/FlightDemo/osm_to_unity_transform.json"))
th = math.radians(T["rot_deg"]); tx, tz = T["translate"]
cc, ss = math.cos(th), math.sin(th)
coast = np.stack([cc * xl - ss * yl + tx, ss * xl + cc * yl + tz], axis=1)


def densify(P, sp=4.0):
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    o = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        for t in np.linspace(0, 1, max(1, int(seg[i] // sp)), endpoint=False):
            o.append(a + (b - a) * t)
    return np.array(o)


dense = densify(coast)
tree = cKDTree(dense)
dnear = lambda P: tree.query(P)[0]

CELL = 10.0; PAD = 2600.0
gx = np.arange(coast[:, 0].min()-PAD, coast[:, 0].max()+PAD+CELL, CELL)
gz = np.arange(coast[:, 1].min()-PAD, coast[:, 1].max()+PAD+CELL, CELL)
GX, GZ = np.meshgrid(gx, gz, indexing="ij")
inside = Path(coast).contains_points(np.stack([GX.ravel(), GZ.ravel()], 1)).reshape(GX.shape).astype(float)


def resample(P, sp):
    P2 = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P2, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); tot = cum[-1]
    n = max(8, int(round(tot / sp)))
    tgt = np.linspace(0, tot, n, endpoint=False)
    i = np.clip(np.searchsorted(cum, tgt, 'right') - 1, 0, len(seg) - 1)
    f = (tgt - cum[i]) / np.maximum(seg[i], 1e-9)
    return P2[i] + (P2[i+1] - P2[i]) * f[:, None], float(tot)


def alen(P):
    return float(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1).sum())


def turn300(P):
    n = len(P); b = np.vstack([P, P[:1]])
    tot = float(np.linalg.norm(np.diff(b, axis=0), axis=1).sum())
    K = max(2, int(round(300.0 / (tot / n))))
    v = np.array([P[(i+1) % n] - P[(i-1) % n] for i in range(n)])
    a = np.arctan2(v[:, 1], v[:, 0])
    return max(abs(math.degrees((a[(i+K) % n] - a[i] + math.pi) % (2*math.pi) - math.pi)) for i in range(n))


def radii(P):
    n = len(P); out = []
    for i in range(n):
        a, b, c = P[(i-1) % n], P[i], P[(i+1) % n]
        ab = b-a; bc = c-b; ca = a-c
        la, lb, lc = np.linalg.norm(ab), np.linalg.norm(bc), np.linalg.norm(ca)
        ar = abs(ab[0]*bc[1]-ab[1]*bc[0])/2
        if ar > 1e-9:
            out.append(la*lb*lc/(4*ar))
    return np.array(out)


def level_for_offset(sig, off):
    return 1.0 - 0.5 * (1.0 + math.erf(off / (sig * math.sqrt(2))))


print(f"{'sigma':>6} {'level':>7} {'perim':>7} {'offMin':>7} {'offMed':>7} {'offMax':>7} "
      f"{'Rmin':>7} {'Rp5':>7} {'turn300':>8} {'v@240s':>7} {'bank':>5}")
for sig in [400, 600, 800, 1000, 1300, 1600, 2000, 2500]:
    blur = ndimage.gaussian_filter(inside, sigma=sig/CELL, mode="constant")
    # 数值求解目标离岸
    lo, hi = 0.005, 0.499   # offset 随 level 递减
    for _ in range(24):
        mid = (lo+hi)/2
        fig = plt.figure(); cs = plt.contour(GX, GZ, blur, levels=[mid])
        segs = cs.allsegs[0] if hasattr(cs, "allsegs") else [np.array(p) for p in cs.get_paths()[0]]
        plt.close(fig)
        segs = sorted([np.array(s) for s in segs], key=lambda a: -len(a))
        med = float(np.median(dnear(segs[0])))
        if med > 500.0: lo = mid     # 太靠外 -> 提高 level
        else: hi = mid
    lv = (lo+hi)/2
    fig = plt.figure(); cs = plt.contour(GX, GZ, blur, levels=[lv])
    segs = cs.allsegs[0] if hasattr(cs, "allsegs") else [np.array(p) for p in cs.get_paths()[0]]
    plt.close(fig)
    segs = sorted([np.array(s) for s in segs], key=lambda a: -len(a))
    C = segs[0]
    P, per = resample(C, 60.0)
    dd = dnear(P); R = radii(P); m = turn300(P)
    v = per/240.0
    print(f"{sig:6.0f} {lv:7.4f} {per:7.0f} {dd.min():7.0f} {np.median(dd):7.0f} {dd.max():7.0f} "
          f"{R.min():7.0f} {np.percentile(R,5):7.0f} {m:8.1f} {v:7.1f} {min(25,m*v/300*2):5.1f}")
