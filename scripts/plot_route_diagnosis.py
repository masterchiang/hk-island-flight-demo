"""可视化：地形陆地掩膜 + v3/v4 航线，用于诊断与交付说明。"""
import json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"<PROJECT_ROOT>"
CSV = ROOT + "/output/FlightDemo/terrain_land_samples.csv"
CFG = ROOT + "/My project (1)/Assets/_FlightDemo/Configs"

land = np.loadtxt(CSV, delimiter=",")
lx, lz, lh = land[:, 0], land[:, 1], land[:, 2]
STEP = 100.0
X0, Z0 = lx.min(), lz.min()
NX = int(round((lx.max() - X0) / STEP)) + 1
NZ = int(round((lz.max() - Z0) / STEP)) + 1
mask = np.zeros((NX, NZ))
ix = np.rint((lx - X0) / STEP).astype(int)
iz = np.rint((lz - Z0) / STEP).astype(int)
mask[ix, iz] = np.maximum(lh, 1.0)  # 海=0, 陆=高程


def cr(pts, t):
    n = len(pts)
    s = (t % 1.0) * n
    i1 = int(math.floor(s)) % n
    i2 = (i1 + 1) % n
    i0 = (i1 - 1 + n) % n
    i3 = (i2 + 1) % n
    u = s - math.floor(s)
    p0, p1, p2, p3 = (np.array(pts[k], float) for k in (i0, i1, i2, i3))
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def curve(path, N=1500):
    d = json.load(open(path, encoding="utf-8"))
    pts = [(p["x"], p["y"], p["z"]) for p in d["points"]]
    return np.array([cr(pts, k / N) for k in range(N + 1)])


fig, axes = plt.subplots(1, 2, figsize=(22, 10))
for ax, name in zip(axes, ["CoastlineRoute_SheungWan_v3.json", "CoastlineRoute_SheungWan_v4.json"]):
    ax.imshow(mask.T, origin="lower", extent=[X0 - STEP/2, X0 + (NX-0.5)*STEP, Z0 - STEP/2, Z0 + (NZ-0.5)*STEP],
              cmap="terrain", vmin=-50, vmax=600, alpha=0.9)
    c = curve(f"{CFG}/{name}")
    ax.plot(c[:, 0], c[:, 2], "-", color="crimson", lw=1.4, label="route")
    ax.plot(c[::50, 0], c[::50, 2], "o", color="black", ms=2)
    ax.plot(c[0, 0], c[0, 2], "b^", ms=12, label="start")
    ax.set_title(name, fontsize=13)
    ax.set_xlabel("world X (m)"); ax.set_ylabel("world Z (m)")
    ax.legend(); ax.grid(alpha=0.25)
    ax.set_aspect("equal")
plt.tight_layout()
out = ROOT + "/output/FlightDemo/route_diagnosis_v3_v4.png"
plt.savefig(out, dpi=110)
print("saved", out)
