"""
分析 Unity 航线(Configs/*.json)与真实地形陆地点采样(terrain_land_samples.csv)的匹配度。
复现 DemoRoute.cs 的周期 Catmull-Rom 采样，逐点计算"离最近陆地"的距离，
定位自动巡航飞出海岸的区段。
"""
import json, math, sys
import numpy as np

ROOT = r"<PROJECT_ROOT>"
CSV = ROOT + "/output/FlightDemo/terrain_land_samples.csv"
CFG = ROOT + "/My project (1)/Assets/_FlightDemo/Configs"

# ---------- 1. 陆地网格 ----------
land = []
with open(CSV) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        x, z, h = (float(v) for v in line.split(","))
        land.append((x, z, h))
land = np.array(land, dtype=float)
lx, lz, lh = land[:, 0], land[:, 1], land[:, 2]
print(f"陆地采样点 {len(land)} 个; x[{lx.min():.0f},{lx.max():.0f}] z[{lz.min():.0f},{lz.max():.0f}]")

STEP = 100.0
X0, Z0 = lx.min(), lz.min()
NX = int(round((lx.max() - X0) / STEP)) + 1
NZ = int(round((lz.max() - Z0) / STEP)) + 1
mask = np.zeros((NX, NZ), dtype=bool)
grid_h = np.full((NX, NZ), -1.0)
ix = np.rint((lx - X0) / STEP).astype(int)
iz = np.rint((lz - Z0) / STEP).astype(int)
mask[ix, iz] = True
grid_h[ix, iz] = lh
print(f"陆地掩膜 {NX} x {NZ} (100m), 陆地占比 {mask.mean()*100:.1f}%")


def dist_to_land(px, pz):
    """点到最近陆地格点的水平距离(米)。"""
    i = int(round((px - X0) / STEP))
    j = int(round((pz - Z0) / STEP))
    if 0 <= i < NX and 0 <= j < NZ and mask[i, j]:
        return 0.0
    # 搜索附近范围
    R = 40
    i0, i1 = max(0, i - R), min(NX, i + R + 1)
    j0, j1 = max(0, j - R), min(NZ, j + R + 1)
    sub = np.argwhere(mask[i0:i1, j0:j1])
    if len(sub) == 0:
        return 1e9
    cx = X0 + (sub[:, 0] + i0) * STEP
    cz = Z0 + (sub[:, 1] + j0) * STEP
    return float(np.min(np.hypot(cx - px, cz - pz)))


# ---------- 2. 复现 Catmull-Rom ----------
def load_points(path):
    d = json.load(open(path, encoding="utf-8"))
    return d, [(p["x"], p["y"], p["z"]) for p in d["points"]]


def catmull_rom(pts, t):
    """t in [0,1) -> 世界坐标(x,y,z)，与 DemoRoute.Point 一致。"""
    n = len(pts)
    scaled = (t % 1.0) * n
    i1 = int(math.floor(scaled)) % n
    i2 = (i1 + 1) % n
    i0 = (i1 - 1 + n) % n
    i3 = (i2 + 1) % n
    u = scaled - math.floor(scaled)
    p0, p1, p2, p3 = (np.array(pts[k], float) for k in (i0, i1, i2, i3))
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u +
                  (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def analyse(path, label):
    d, pts = load_points(path)
    N = 2000
    samples = [catmull_rom(pts, k / N) for k in range(N)]
    # 弧长
    cum = [0.0]
    for k in range(1, N + 1):
        cum.append(cum[-1] + np.linalg.norm(samples[k % N] - samples[k - 1]))
    total = cum[-1]
    print(f"\n===== {label} =====")
    print(f"控制点 {len(pts)}; 周期长度 {total:.0f} m")
    worst = []
    for k in range(N):
        p = samples[k]
        along = cum[k] / total * 100.0
        dland = dist_to_land(p[0], p[2])
        worst.append((dland, along, p))
    worst.sort(reverse=True)
    print("离陆地最远的 15 个采样点:")
    for dland, along, p in worst[:15]:
        print(f"  进度 {along:5.1f}%  离陆 {dland:7.0f} m  位置 ({p[0]:.0f},{p[1]:.0f},{p[2]:.0f})")
    # 分区间统计
    print("区间离陆中位数/最大值:")
    for a in range(0, 100, 5):
        seg = [w for w in worst if a <= w[1] < a + 5]
        if seg:
            ds = [s[0] for s in seg]
            print(f"  {a:3d}-{a+5:3d}%: median {np.median(ds):7.0f}  max {max(ds):7.0f}")
    over = sum(1 for w in worst if w[0] > 400)
    print(f"离陆 >400m 的采样点占比: {over/N*100:.1f}%  (调参判断用)")
    return dict(label=label, total=total, worst=worst)


for name in ["CoastlineRoute_SheungWan_v3.json", "CoastlineRoute_SheungWan_v4.json",
             "CoastlineRoute_Current.json", "CoastlineRoute_SheungWan_v2.json"]:
    try:
        analyse(f"{CFG}/{name}", name)
    except Exception as e:
        print(f"{name}: {e}")
