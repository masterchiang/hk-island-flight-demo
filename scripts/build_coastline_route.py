"""
【最终版】生成贴合 Unity 真实香港岛海岸线的闭合自动巡航航线。

方法：
  1. OSM 香港岛外轮廓 -> HK1980 -> Unity 世界（刚体变换，残差中位数 55 m）。
  2. 尺度空间(scale-space)：陆地掩膜高斯模糊 sigma，取等值线 = 天然平滑的贴岸线。
     level 用二分法求出，使"离岸距离中位数"= TARGET_OFF。
  3. 自适应曲率限制：只在局部转弯半径 < R_TARGET 的地方做加权平滑（保留其他地方的岸线细节）。
  4. 均匀弧长重采样为 256 个控制点，输出 DemoRoute 资产。
  5. 双重验证：OSM 高精度岸线距离 + Unity 100 m 陆地采样掩膜 + 世界边界 + 闭合性。
"""
import json, math, sys
import numpy as np
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path

ROOT = r"<PROJECT_ROOT>"
OUT_JSON = ROOT + "/My project (1)/Assets/_FlightDemo/Configs/CoastlineRoute_Circuit_v5.json"
OUT_JSON2 = ROOT + "/output/FlightDemo/coastline_route_circuit_v5.json"

SIGMA = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
TARGET_OFF = float(sys.argv[2]) if len(sys.argv) > 2 else 500.0
R_TARGET = float(sys.argv[3]) if len(sys.argv) > 3 else 900.0
N_OUT = 256
ALT = 700.0
LAP = 240.0

# ---------- 1. 真实海岸线 ----------
tr = Transformer.from_crs("EPSG:4326", "EPSG:2326", always_xy=True)
d = json.load(open(ROOT + "/data/raw/island_geometry.json", encoding="utf-8"))
rings = sorted(d["coordinates"], key=lambda p: -len(p[0]))
outer = np.array(rings[0][0], float)
X, Y = tr.transform(outer[:, 0], outer[:, 1])
xl = np.array(X) - 840000.0
yl = np.array(Y) - 815000.0
T = json.load(open(ROOT + "/output/FlightDemo/osm_to_unity_transform.json"))
th = math.radians(T["rot_deg"]); tx, tz = T["translate"]
cc, ss = math.cos(th), math.sin(th)
coast = np.stack([cc * xl - ss * yl + tx, ss * xl + cc * yl + tz], axis=1)
poly = Path(coast)


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
print(f"OSM 海岸线 {len(coast)} 点 / 稠密 {len(dense)} 点；"
      f"bbox x[{coast[:,0].min():.0f},{coast[:,0].max():.0f}] z[{coast[:,1].min():.0f},{coast[:,1].max():.0f}]")

# ---------- 2. 尺度空间等值线 ----------
CELL = 10.0; PAD = 2600.0
gx = np.arange(coast[:, 0].min() - PAD, coast[:, 0].max() + PAD + CELL, CELL)
gz = np.arange(coast[:, 1].min() - PAD, coast[:, 1].max() + PAD + CELL, CELL)
GX, GZ = np.meshgrid(gx, gz, indexing="ij")
inside = poly.contains_points(np.stack([GX.ravel(), GZ.ravel()], 1)).reshape(GX.shape).astype(float)
blur = ndimage.gaussian_filter(inside, sigma=SIGMA / CELL, mode="constant")


def contour(lv):
    fig = plt.figure(); cs = plt.contour(GX, GZ, blur, levels=[lv])
    segs = cs.allsegs[0] if hasattr(cs, "allsegs") else [np.array(p) for p in cs.get_paths()[0]]
    plt.close(fig)
    return sorted([np.array(s) for s in segs], key=lambda a: -len(a))


lo, hi = 0.005, 0.499
for _ in range(26):
    mid = (lo + hi) / 2
    med = float(np.median(tree.query(contour(mid)[0])[0]))
    if med > TARGET_OFF: lo = mid
    else: hi = mid
level = (lo + hi) / 2
C = contour(level)[0]
print(f"sigma={SIGMA:.0f} m  level={level:.4f} -> 离岸中位数 {np.median(tree.query(C)[0]):.0f} m")


def resample(P, sp):
    P2 = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P2, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); tot = cum[-1]
    n = max(8, int(round(tot / sp)))
    tgt = np.linspace(0, tot, n, endpoint=False)
    i = np.clip(np.searchsorted(cum, tgt, "right") - 1, 0, len(seg) - 1)
    f = (tgt - cum[i]) / np.maximum(seg[i], 1e-9)
    return P2[i] + (P2[i + 1] - P2[i]) * f[:, None], float(tot)


def alen(P):
    return float(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1).sum())


def radii(P):
    n = len(P); o = np.full(n, np.inf)
    for i in range(n):
        a, b, c = P[(i - 1) % n], P[i], P[(i + 1) % n]
        ab = b - a; bc = c - b; ca = a - c
        la, lb, lc = np.linalg.norm(ab), np.linalg.norm(bc), np.linalg.norm(ca)
        ar = abs(ab[0] * bc[1] - ab[1] * bc[0]) / 2
        if ar > 1e-9:
            o[i] = la * lb * lc / (4 * ar)
    return o


def turn_metric(P, window=300.0):
    n = len(P)
    tot = alen(P)
    K = max(2, int(round(window / (tot / n))))
    v = np.array([P[(i + 1) % n] - P[(i - 1) % n] for i in range(n)])
    a = np.arctan2(v[:, 1], v[:, 0])
    return max(abs(math.degrees((a[(i + K) % n] - a[i] + math.pi) % (2 * math.pi) - math.pi))
               for i in range(n))


def smooth(P, win_m):
    n = len(P)
    k = max(1, int(round(win_m / (alen(P) / n))))
    kern = np.ones(2 * k + 1) / (2 * k + 1)
    Q = np.empty_like(P)
    for j in range(2):
        ext = np.concatenate([P[-k:, j], P[:, j], P[:k, j]])
        Q[:, j] = np.convolve(ext, kern, mode="same")[k:k + n]
    return Q


# ---------- 3. 自适应曲率限制 ----------
Q, _ = resample(C, 50.0)
print(f"基准曲线 {len(Q)} 点 长 {alen(Q):.0f} m；Rmin {radii(Q).min():.0f} m, "
      f"Rp5 {np.percentile(radii(Q),5):.0f} m；300m 航向变化 {turn_metric(Q):.1f}°")
for it in range(60):
    R = radii(Q)
    bad = (R < R_TARGET).astype(float)
    if bad.sum() == 0:
        break
    w = ndimage.gaussian_filter1d(bad, sigma=14, mode="wrap")   # 局部影响范围 ~14 点 = 700 m
    w = np.clip(w / max(w.max(), 1e-9), 0, 1)
    Qs = smooth(Q, 900.0)
    Q = Q + w[:, None] * (Qs - Q)
    Q, _ = resample(Q, 50.0)
print(f"自适应平滑 {it} 轮后：Rmin {radii(Q).min():.0f} m, Rp5 {np.percentile(radii(Q),5):.0f} m；"
      f"300m 航向变化 {turn_metric(Q):.2f}°")

# ---------- 4. 起点与方向 ----------
v3 = json.load(open(ROOT + "/My project (1)/Assets/_FlightDemo/Configs/CoastlineRoute_SheungWan_v3.json", encoding="utf-8"))
v3p0 = np.array([v3["points"][0]["x"], v3["points"][0]["z"]])
n = len(Q)
i0 = int(np.argmin(np.linalg.norm(Q - v3p0, axis=1)))
if (Q[(i0 + 1) % n] - Q[(i0 - 1) % n])[0] < 0:
    Q = Q[::-1]; i0 = (n - 1 - i0) % n
Q = np.roll(Q, -i0, axis=0)
Lout = alen(Q)
Pout, _ = resample(Q, Lout / N_OUT)

payload = {"source": (f"OSM HKI relation 4556901 -> HK1980 -> Unity rigid fit; scale-space coastline "
                      f"sigma {SIGMA:.0f} m level {level:.4f} (~{TARGET_OFF:.0f} m seaward); adaptive "
                      f"curvature limiting R>={R_TARGET:.0f} m; {N_OUT} pts; lap {LAP:.0f}s"),
           "points": [{"x": round(float(a), 1), "y": ALT, "z": round(float(b), 1)} for a, b in Pout]}
for p in (OUT_JSON, OUT_JSON2):
    json.dump(payload, open(p, "w"), separators=(",", ":"))

# ---------- 5. 验证 ----------
V = np.array([[q["x"], q["z"]] for q in payload["points"]])
d_osm = tree.query(V)[0]
onland_osm = poly.contains_points(V)
# Unity 100m 陆地采样掩膜
lan = np.loadtxt(ROOT + "/output/FlightDemo/terrain_land_samples.csv", delimiter=",")
X0m, Z0m = lan[:, 0].min(), lan[:, 1].min()
NXm = int(round((lan[:, 0].max() - X0m) / 100)) + 1
NZm = int(round((lan[:, 1].max() - Z0m) / 100)) + 1
landm = np.zeros((NXm, NZm), bool)
landm[np.rint((lan[:, 0] - X0m) / 100).astype(int), np.rint((lan[:, 1] - Z0m) / 100).astype(int)] = True
ii = np.clip(np.rint((V[:, 0] - X0m) / 100).astype(int), 0, NXm - 1)
jj = np.clip(np.rint((V[:, 1] - Z0m) / 100).astype(int), 0, NZm - 1)
onland_unity = landm[ii, jj]
d_unity = cKDTree(lan[:, :2]).query(V)[0]

Rf = radii(Q)
spd = Lout / LAP
print("\n=== 验证 ===")
print(f"控制点        {N_OUT}    周长 {Lout:.0f} m    圈时 {LAP:.0f}s -> 巡航 {spd:.1f} m/s ({spd*3.6:.0f} km/h)")
print(f"平顺度        300m 弧长内最大航向变化 {turn_metric(Q):.2f}°  ->  yaw rate 峰值 "
      f"{turn_metric(Q)/(300/spd):.1f}°/s  bank≈{min(25,turn_metric(Q)/(300/spd)*2):.1f}°")
print(f"转弯半径      min {Rf.min():.0f} m   p5 {np.percentile(Rf,5):.0f} m   median {np.median(Rf):.0f} m")
print(f"离岸(OSM)     min/med/max {d_osm.min():.0f}/{np.median(d_osm):.0f}/{d_osm.max():.0f} m")
print(f"落在 OSM 陆地内的控制点      {int(onland_osm.sum())}/{N_OUT}")
print(f"落在 Unity 陆地采样格内的控制点 {int(onland_unity.sum())}/{N_OUT}  (最近陆地采样点中位 {np.median(d_unity):.0f} m)")
print(f"世界边界      |x|max {np.abs(V[:,0]).max():.0f} (<9980)   |z|max {np.abs(V[:,1]).max():.0f} (<7980)")
print(f"高度          {ALT:.0f} m    首尾闭合 {np.linalg.norm(Q[0]-Q[-1]):.1f} m")

json.dump({"sigma_m": SIGMA, "level": level, "target_offset_m": TARGET_OFF, "r_target_m": R_TARGET,
           "n_points": N_OUT, "perimeter_m": Lout, "lap_seconds": LAP, "target_speed_mps": spd,
           "max_heading_change_per_300m_deg": float(turn_metric(Q)),
           "turn_radius_min_m": float(Rf.min()), "turn_radius_p5_m": float(np.percentile(Rf, 5)),
           "offshore_min_m": float(d_osm.min()), "offshore_median_m": float(np.median(d_osm)),
           "offshore_max_m": float(d_osm.max()),
           "ctrl_pts_inside_osm_land": int(onland_osm.sum()),
           "ctrl_pts_inside_unity_land_cell": int(onland_unity.sum()),
           "max_abs_x": float(np.abs(V[:, 0]).max()), "max_abs_z": float(np.abs(V[:, 1]).max())},
          open(ROOT + "/output/FlightDemo/route_v5_verification.json", "w"), indent=2)


def cr(p, t):
    m = len(p); sc = (t % 1.0) * m
    i1 = int(math.floor(sc)) % m; i2 = (i1 + 1) % m
    i0b = (i1 - 1 + m) % m; i3 = (i2 + 1) % m
    u = sc - math.floor(sc)
    p0, p1, p2, p3 = (np.array([p[k]["x"], p[k]["z"]]) for k in (i0b, i1, i2, i3))
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


fig, axes = plt.subplots(1, 2, figsize=(25, 11.5))
for ax, (name, path) in zip(axes, [
        ("BEFORE  CoastlineRoute_SheungWan_v3  (currently in scene)",
         ROOT + "/My project (1)/Assets/_FlightDemo/Configs/CoastlineRoute_SheungWan_v3.json"),
        ("AFTER  CoastlineRoute_Circuit_v5", OUT_JSON)]):
    ax.plot(coast[:, 0], coast[:, 1], "-", color="black", lw=0.9, label="real coastline (OSM)")
    d2 = json.load(open(path, encoding="utf-8"))
    cur = np.array([cr(d2["points"], k / 1400) for k in range(1401)])
    ax.plot(cur[:, 0], cur[:, 1], "-", color="crimson", lw=1.9, label="auto-cruise route")
    ax.plot(cur[0, 0], cur[0, 1], "b^", ms=13, label="start")
    dv2 = tree.query(cur)[0]
    ax.set_title(f"{name}\noffshore median {np.median(dv2):.0f} m | max {dv2.max():.0f} m | "
                 f"beyond 2 km {np.mean(dv2>2000)*100:.1f}%", fontsize=12)
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend(loc="lower left", fontsize=9)
    ax.set_xlabel("world X (m)"); ax.set_ylabel("world Z (m)")
plt.tight_layout()
plt.savefig(ROOT + "/output/FlightDemo/route_fix_before_after.png", dpi=100)
print("\nsaved", OUT_JSON)
