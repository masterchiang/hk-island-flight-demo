"""刚体(无缩放)拟合 OSM 岛屿轮廓 -> Unity 世界(x,z)。旋转网格搜索 + 平移 ICP。"""
import json, numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT = r"<PROJECT_ROOT>"

land = np.loadtxt(ROOT + "/output/FlightDemo/terrain_land_samples.csv", delimiter=",")
STEP = 100.0; X0 = land[:, 0].min(); Z0 = land[:, 1].min()
NX = int(round((land[:, 0].max() - X0) / STEP)) + 1
NZ = int(round((land[:, 1].max() - Z0) / STEP)) + 1
m = np.zeros((NX, NZ), bool)
m[np.rint((land[:, 0] - X0) / STEP).astype(int),
  np.rint((land[:, 1] - Z0) / STEP).astype(int)] = True
er = m.copy()
er[1:, :] &= m[:-1, :]; er[:-1, :] &= m[1:, :]
er[:, 1:] &= m[:, :-1]; er[:, :-1] &= m[:, 1:]
bi, bj = np.nonzero(m & ~er)
A = np.stack([X0 + bi * STEP, Z0 + bj * STEP], axis=1)

tr = Transformer.from_crs("EPSG:4326", "EPSG:2326", always_xy=True)
d = json.load(open(ROOT + "/data/raw/island_geometry.json", encoding="utf-8"))
rings = sorted(d["coordinates"], key=lambda p: -len(p[0]))
outer = np.array(rings[0][0], float)
X, Y = tr.transform(outer[:, 0], outer[:, 1])
B = np.stack([np.array(X) - 840000.0, np.array(Y) - 815000.0], axis=1)
treeA = cKDTree(A)


def rot(P, th):
    c, s = np.cos(th), np.sin(th)
    return P @ np.array([[c, s], [-s, c]])


def fit(P, Q, th, flip, iters=40):
    t = P.mean(0) - rot(Q, th).mean(0)
    for _ in range(iters):
        Qt = rot(Q, th) + t
        dist, idx = treeA.query(Qt)
        delta = A[idx] - Qt
        t = t + np.median(delta, axis=0)
    Qt = rot(Q, th) + t
    dist, idx = treeA.query(Qt)
    return t, dist, Qt


best = None
for flip in (False, True):
    Q = B * np.array([-1.0, 1.0]) if flip else B
    for deg in np.arange(0, 360, 2.0):
        th = np.radians(deg)
        t, dist, Qt = fit(P=A, Q=Q, th=th, flip=flip, iters=25)
        sc = np.median(dist)
        if best is None or sc < best[0]:
            best = (sc, flip, th, t, dist, Qt)
    print(f"flip={flip} 已搜索")

sc, flip, th, t, dist, Qt = best
# 细化
for _ in range(3):
    for ddeg in np.arange(-2, 2.01, 0.1):
        thr = th + np.radians(ddeg)
        tt, dd, QQ = fit(A, B * np.array([-1.0, 1.0]) if flip else B, thr, flip, 30)
        s2 = np.median(dd)
        if s2 < sc:
            sc, th, t, dist, Qt = s2, thr, tt, dd, QQ
print("\n最佳刚体拟合:")
print(f"  flip={flip}  rot={np.degrees(th):.3f} deg  translate=({t[0]:.2f},{t[1]:.2f})")
print(f"  残差 median={np.median(dist):.1f} mean={dist.mean():.1f} p90={np.percentile(dist,90):.1f} max={dist.max():.1f}")
json.dump({"flip": bool(flip), "rot_deg": float(np.degrees(th)),
           "translate": [float(t[0]), float(t[1])],
           "residual_median_m": float(np.median(dist)), "residual_mean_m": float(dist.mean()),
           "residual_p90_m": float(np.percentile(dist, 90)),
           "model": "unity_xz = R(th) @ (flip*x', y') + t"},
          open(ROOT + "/output/FlightDemo/osm_to_unity_transform.json", "w"), indent=2)

# 可视化
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(14, 11))
ax.scatter(A[:, 0], A[:, 1], s=4, c="gray", label="Unity land border (100m grid)")
ax.plot(Qt[:, 0], Qt[:, 1], "-", color="crimson", lw=1.2, label="OSM island fitted")
ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend()
ax.set_title(f"OSM->Unity rigid fit  rot={np.degrees(th):.2f}deg flip={flip} median={np.median(dist):.0f}m")
plt.tight_layout(); plt.savefig(ROOT + "/output/FlightDemo/osm_unity_fit.png", dpi=110)
print("saved fit png")
