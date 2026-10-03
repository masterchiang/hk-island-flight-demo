"""对比若干 sigma 下的航线形状，并检查是否切入陆地。"""
import json, math
import numpy as np
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path

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
coast = np.stack([cc*xl - ss*yl + tx, ss*xl + cc*yl + tz], axis=1)


def densify(P, sp=4.0):
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    o = []
    for i in range(len(P)):
        a, b = P[i], P[(i+1) % len(P)]
        for t in np.linspace(0, 1, max(1, int(seg[i]//sp)), endpoint=False):
            o.append(a + (b-a)*t)
    return np.array(o)


dense = densify(coast); tree = cKDTree(dense)
poly = Path(coast)

CELL = 10.0; PAD = 2600.0
gx = np.arange(coast[:,0].min()-PAD, coast[:,0].max()+PAD+CELL, CELL)
gz = np.arange(coast[:,1].min()-PAD, coast[:,1].max()+PAD+CELL, CELL)
GX, GZ = np.meshgrid(gx, gz, indexing="ij")
inside = poly.contains_points(np.stack([GX.ravel(), GZ.ravel()], 1)).reshape(GX.shape).astype(float)


def contour(blur, lv):
    fig = plt.figure(); cs = plt.contour(GX, GZ, blur, levels=[lv])
    segs = cs.allsegs[0] if hasattr(cs, "allsegs") else [np.array(p) for p in cs.get_paths()[0]]
    plt.close(fig)
    return sorted([np.array(s) for s in segs], key=lambda a: -len(a))[0]


fig, axes = plt.subplots(1, 3, figsize=(30, 11))
for ax, sig in zip(axes, [1000, 1300, 1600]):
    blur = ndimage.gaussian_filter(inside, sigma=sig/CELL, mode="constant")
    lo, hi = 0.005, 0.499
    for _ in range(24):
        mid = (lo+hi)/2
        med = float(np.median(tree.query(contour(blur, mid))[0]))
        if med > 500: lo = mid
        else: hi = mid
    lv = (lo+hi)/2
    C = contour(blur, lv)
    onland = int(poly.contains_points(C).sum())
    dd = tree.query(C)[0]
    ax.plot(coast[:,0], coast[:,1], "-", color="black", lw=0.8, label="real coastline")
    ax.plot(C[:,0], C[:,1], "-", color="crimson", lw=1.7, label="route")
    ax.plot(C[0,0], C[0,1], "b^", ms=12)
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_xlim(-8200, 8600); ax.set_ylim(-6800, 6600)
    ax.legend(loc="lower left", fontsize=9)
    Rl = []
    n = len(C)
    for i in range(n):
        a, b, c2 = C[(i-1) % n], C[i], C[(i+1) % n]
        ab = b-a; bc = c2-b; ca = a-c2
        la, lb, lc = np.linalg.norm(ab), np.linalg.norm(bc), np.linalg.norm(ca)
        ar = abs(ab[0]*bc[1]-ab[1]*bc[0])/2
        if ar > 1e-9: Rl.append(la*lb*lc/(4*ar))
    Rl = np.array(Rl)
    ax.set_title(f"sigma={sig} m  level={lv:.4f}\noffshore min/med/max {dd.min():.0f}/{np.median(dd):.0f}/{dd.max():.0f} m | "
                 f"on-land pts {onland}\nRmin={Rl.min():.0f} Rp5={np.percentile(Rl,5):.0f}", fontsize=11)
plt.tight_layout()
plt.savefig(ROOT + "/output/FlightDemo/route_sigma_compare.png", dpi=95)

# 找出最靠岸的位置
sig = 1300
blur = ndimage.gaussian_filter(inside, sigma=sig/CELL, mode="constant")
lo, hi = 0.005, 0.499
for _ in range(24):
    mid = (lo+hi)/2
    med = float(np.median(tree.query(contour(blur, mid))[0]))
    if med > 500: lo = mid
    else: hi = mid
C = contour(blur, (lo+hi)/2)
dd = tree.query(C)[0]
k = np.argsort(dd)[:8]
print("sigma=1300 最靠岸的 8 个点 (离岸 m, 世界坐标, 是否在陆地内):")
for i in k:
    print(f"  {dd[i]:7.1f} m  ({C[i,0]:8.1f},{C[i,1]:8.1f})  onLand={bool(poly.contains_point(C[i]))}")
print("saved route_sigma_compare.png")
