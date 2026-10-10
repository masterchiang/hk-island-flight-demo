"""拟合 OSM 岛屿轮廓 -> Unity 世界(x,z) 的相似变换，用于验证坐标系与获得高精度海岸线。"""
import json, numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT = r"<PROJECT_ROOT>"

# --- Unity 陆地掩膜的边界点 ---
land = np.loadtxt(ROOT + "/output/FlightDemo/terrain_land_samples.csv", delimiter=",")
STEP = 100.0; X0 = land[:, 0].min(); Z0 = land[:, 1].min()
NX = int(round((land[:, 0].max() - X0) / STEP)) + 1
NZ = int(round((land[:, 1].max() - Z0) / STEP)) + 1
m = np.zeros((NX, NZ), bool)
m[np.rint((land[:, 0] - X0) / STEP).astype(int),
  np.rint((land[:, 1] - Z0) / STEP).astype(int)] = True
# 边界 = 陆地且四邻有海
er = m.copy()
er[1:, :] &= m[:-1, :]; er[:-1, :] &= m[1:, :]
er[:, 1:] &= m[:, :-1]; er[:, :-1] &= m[:, 1:]
border = m & ~er
bi, bj = np.nonzero(border)
A = np.stack([X0 + bi * STEP, Z0 + bj * STEP], axis=1)
print("Unity 边界点", len(A), "bbox", A[:, 0].min(), A[:, 0].max(), A[:, 1].min(), A[:, 1].max())

# --- OSM 主环 -> HK1980 local ---
tr = Transformer.from_crs("EPSG:4326", "EPSG:2326", always_xy=True)
d = json.load(open(ROOT + "/data/raw/island_geometry.json", encoding="utf-8"))
rings = sorted(d["coordinates"], key=lambda p: -len(p[0]))
outer = np.array(rings[0][0], float)
X, Y = tr.transform(outer[:, 0], outer[:, 1])
B = np.stack([np.array(X) - 840000.0, np.array(Y) - 815000.0], axis=1)
print("OSM 外环点", len(B), "bbox", B[:, 0].min(), B[:, 0].max(), B[:, 1].min(), B[:, 1].max())

treeA = cKDTree(A)
treeB = cKDTree(B)


def apply(P, s, c, sn, t, flip):
    Q = P.copy()
    if flip:
        Q = Q * np.array([-1.0, 1.0])
    R = np.array([[c, -sn], [sn, c]])
    return s * (Q @ R.T) + t


def icp(P, Q, s, th, t, flip, iters=60):
    """把 Q 对齐到 P（P 固定）。"""
    for it in range(iters):
        c, sn = np.cos(th), np.sin(th)
        Qt = apply(Q, s, c, sn, t, flip)
        dist, idx = treeA.query(Qt)
        target = P[idx]
        # 在 (可能翻转的) Q 坐标系中解最小二乘 : target = s R Q' + t
        Qc = Q * np.array([-1.0, 1.0]) if flip else Q
        # 去质心
        qm = Qc.mean(0); tm = target.mean(0)
        Qz = Qc - qm; Tz = target - tm
        # 最优旋转
        H = Qz.T @ Tz
        U, S, Vt = np.linalg.svd(H)
        D = np.eye(2); D[1, 1] = np.sign(np.linalg.det(Vt.T @ U.T))
        R = Vt.T @ D @ U.T
        s = (S * np.array([1, D[1, 1]])).sum() / (Qz ** 2).sum()
        t = tm - s * (R @ qm)
        th = np.arctan2(R[1, 0], R[0, 0])
    c, sn = np.cos(th), np.sin(th)
    Qt = apply(Q, s, c, sn, t, flip)
    dist = np.linalg.norm(Qt - P[treeA.query(Qt)[1]], axis=1)
    return s, th, t, dist, Qt


best = None
for flip in (False, True):
    # 初值：质心对齐 + 主成分方向
    Pc = A.mean(0); Qc = B.mean(0)
    th0 = 0.0
    s0 = 1.0
    t0 = Pc - s0 * Qc
    res = icp(A, B, s0, th0, t0, flip)
    s, th, t, dist, Qt = res
    score = np.median(dist)
    print(f"flip={flip}  s={s:.4f} theta={np.degrees(th):7.2f}deg  t=({t[0]:.1f},{t[1]:.1f})  "
          f"median={score:.1f}m  mean={dist.mean():.1f}m  p90={np.percentile(dist,90):.1f}")
    if best is None or score < best[0]:
        best = (score, flip, s, th, t, dist, Qt)

score, flip, s, th, t, dist, Qt = best
print("\n最佳拟合:")
print(f"  flip={flip}  scale={s:.5f}  rot={np.degrees(th):.3f} deg  translate=({t[0]:.2f},{t[1]:.2f})")
print(f"  残差 median={np.median(dist):.1f} mean={dist.mean():.1f} p90={np.percentile(dist,90):.1f} max={dist.max():.1f}")

json.dump({"flip": bool(flip), "scale": float(s), "rot_deg": float(np.degrees(th)),
           "translate": [float(t[0]), float(t[1])],
           "residual_median_m": float(np.median(dist)),
           "residual_mean_m": float(dist.mean()),
           "residual_p90_m": float(np.percentile(dist, 90)),
           "model": "unity_xy = s * R(th) @ (flip(x') , y') + t"},
          open(ROOT + "/output/FlightDemo/osm_to_unity_transform.json", "w"), indent=2)
print("saved transform json")
