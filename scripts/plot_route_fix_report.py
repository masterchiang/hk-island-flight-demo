"""生成最终交付图：v3/v5 航线对比 + 离岸距离-航程曲线（基于 Unity 真实地形射线扫描）。"""
import json, math, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["Microsoft YaHei","SimHei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"]=False
from scipy.spatial import cKDTree

ROOT = r"<PROJECT_ROOT>"
CFG = ROOT + "/My project (1)/Assets/_FlightDemo/Configs"

# --- Unity 权威陆地掩膜 ---
g = json.load(open(ROOT + "/output/FlightDemo/unity_raycast_v5.json"))
X0, Z0, STEP, NX, NZ = g["X0"], g["Z0"], g["STEP"], g["NX"], g["NZ"]
mask = np.array([c == '1' for c in g["mask"]], bool).reshape(NZ, NX)
land = np.array([[X0 + i * STEP, Z0 + j * STEP] for j in range(NZ) for i in range(NX) if mask[j, i]])
tree = cKDTree(land)

# --- 赛道分界 ---
split = {}
for t in range(0, 101, 10):
    split[t] = t / 100.0


def cr(p, t):
    m = len(p); sc = (t % 1.0) * m
    i1 = int(math.floor(sc)) % m; i2 = (i1 + 1) % m
    i0 = (i1 - 1 + m) % m; i3 = (i2 + 1) % m
    u = sc - math.floor(sc)
    p0, p1, p2, p3 = (np.array([p[k]["x"], p[k]["z"]]) for k in (i0, i1, i2, i3))
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


N = 3000
curves = {}
for key, fn in [("v3", "CoastlineRoute_SheungWan_v3.json"), ("v5", "CoastlineRoute_Circuit_v5.json")]:
    rj = json.load(open(f"{CFG}/{fn}", encoding="utf-8"))
    c = np.array([cr(rj["points"], k / N) for k in range(N)])
    d = tree.query(c)[0]
    curves[key] = (c, d)

fig = plt.figure(figsize=(23, 12))
gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.22, wspace=0.14)

for col, (key, title) in enumerate([("v3", "BEFORE  —  CoastlineRoute_SheungWan_v3"),
                                    ("v5", "AFTER  —  CoastlineRoute_Circuit_v5")]):
    ax = fig.add_subplot(gs[0, col])
    c, d = curves[key]
    ax.scatter(land[:, 0], land[:, 1], s=0.4, c="#8a7f6a", marker="s", label="Unity terrain (raycast)")
    sc = ax.scatter(c[:, 0], c[:, 1], c=np.clip(d, 0, 4000), s=3, cmap="turbo_r", vmin=0, vmax=4000)
    ax.plot(c[0, 0], c[0, 1], "b^", ms=13, label="start")
    bad = d > 2000
    if bad.any():
        ax.scatter(c[bad, 0], c[bad, 1], s=6, facecolors="none", edgecolors="magenta",
                   linewidths=0.5, label="> 2 km offshore")
    ax.set_aspect("equal"); ax.grid(alpha=.25)
    ax.set_title(f"{title}\noffshore: median {np.median(d):.0f} m | max {d.max():.0f} m | "
                 f">2 km = {np.mean(d>2000)*100:.1f}% of lap", fontsize=12)
    ax.legend(loc="lower left", fontsize=9); ax.set_xlabel("world X (m)"); ax.set_ylabel("world Z (m)")
    if col == 1:
        cb = plt.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)

ax = fig.add_subplot(gs[1, :])
for key, col, lbl in [("v3", "#d62728", "v3 (was in scene)"), ("v5", "#1f77b4", "v5 (fixed)")]:
    c, d = curves[key]
    ax.plot(np.linspace(0, 100, N), d, "-", color=col, lw=1.4, label=lbl)
ax.axhline(2000, color="magenta", ls="--", lw=1.2, label="2 km 警戒线")
ax.axvspan(12, 25, color="orange", alpha=0.16, label="用户报障区间 12%–25%")
ax.set_xlabel("航程进度 (%)"); ax.set_ylabel("离岛陆地水平距离 (m)")
ax.set_title("离岸距离 vs 航程进度（Unity 真实地形射线检测，3000 采样）")
ax.grid(alpha=.3); ax.legend(loc="upper right"); ax.set_xlim(0, 100); ax.set_ylim(0, 5600)
plt.savefig(ROOT + "/output/FlightDemo/route_fix_report.png", dpi=95, bbox_inches="tight")
print("saved route_fix_report.png")

# 简要文本报告
rep = {}
for key in ("v3", "v5"):
    c, d = curves[key]
    rep[key] = {
        "offshore_min_m": float(d.min()), "offshore_median_m": float(np.median(d)),
        "offshore_max_m": float(d.max()),
        "pct_over_2km": float(np.mean(d > 2000) * 100),
        "pct_over_3km": float(np.mean(d > 3000) * 100),
        "seg_12_25_median_m": float(np.median(d[int(0.12 * N):int(0.25 * N)])),
        "seg_12_25_max_m": float(d[int(0.12 * N):int(0.25 * N)].max()),
    }
print(json.dumps(rep, indent=1, ensure_ascii=False))
json.dump(rep, open(ROOT + "/output/FlightDemo/route_fix_report.json", "w"), indent=2, ensure_ascii=False)
