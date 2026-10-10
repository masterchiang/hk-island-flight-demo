# 08 · 自动巡航「飞出大海」BUG 修复（钢线湾段）

日期：2026-10-03
状态：**已修复 + 已在 Unity 内实测验证**
本轮未构建 EXE（遵守构建禁令）。

---

## 1. 现象

自动巡航时，航程约 12%–25% 区间的飞机会一直直线飞向大海、远离岛屿，在海上飞很久才转回来。用户描述位置在钢线湾附近。

## 2. 定位过程与真因

### 2.1 先量化，别猜

复现 `DemoRoute.cs` 的周期 Catmull-Rom 采样，逐点计算到陆地的水平距离：

| 航段 | v3 旧航线离陆中位数 | 最大 |
|---|---|---|
| 15–20% | 1459 m | 1961 m |
| 20–25% | 2771 m | 3806 m |
| 25–30% | 5533 m | 超出搜索范围（远海） |
| 30–35% | 4601 m | 5460 m |

整圈结论：**81% 的采样点离陆 > 400 m**，其中 23.7% 的航程离陆 > 2 km，最远 5316 m。

### 2.2 真因

**v3 航线根本不是贴岸航线。** 它是一条把整个香港岛包在外围的"大圆角矩形"：
- 顶点包围盒约 x∈[-7550,7550]、z∈[-5750,5800]；
- 而岛屿实际只占 x∈[-7462,7486]、z∈[-5584,5585]，
  岛屿是狭长形（北岸在 z≈-5000 一带平直，南岸在 z>0 侧多海湾）。

所以离岛的四个"角"处必然远离海岸。这不是转弯率、不是相机、不是保护罩问题，**是航线资产数据本身错了**。

上一轮（见 03 文档末尾）已经怀疑是"路线资产与导入地图地形轮廓不匹配"，但当时用"从地形网格随手取近海轮廓"生成 v4，产生 121°/采样段的航向跳变而受阻。本轮换了正确的方法。

## 3. 关键突破口：把坐标系钉死

要让航线贴岸，必须先知道"Unity 世界坐标 ↔ 真实地理坐标"的对应关系。

- `data/raw/island_geometry.json` 是 OSM 香港岛 relation `4556901` 的外轮廓（8575 点，**远高于 Unity 地形网格精度**）。
- 该文件按 `EPSG:2326 (HK1980)` 减原点 `(840000, 815000)` 存储。
- 用 ICP 刚体拟合（固定尺度=1，旋转网格搜索 + 平移 ICP）把 OSM 轮廓对齐到
  Unity 地形射线采样的陆地边界，得到：

```
unity_x = -x_local - 2487.49
unity_z = -y_local - 3258.95      (即旋转 180° + 平移)
残差：中位 55 m / 均值 59 m / P90 92 m
```

残差 55 m 恰好是 100 m 网格的量化误差量级，且平移量 `(-2487.49, -3258.95)`
与场景里地图根节点 `World_HongKongIsland_PBR` 的位置 `(-2498.75, 0, -3256.61)` 几乎重合
—— 变换被独立交叉验证。

> 脚本：`scripts/fit_osm_to_unity_rigid.py`，结果存 `output/FlightDemo/osm_to_unity_transform.json`

## 4. 生成新航线的方法（三次迭代的教训）

| 版本 | 做法 | 结果 |
|---|---|---|
| #1 | 对 OSM 岸线做等距偏移，再把平滑后的点**投影回恒定离岸距离** | ✗ 岬角处重新制造尖点 |
| #2 | 等距偏移 + 空间滑动平均 | ✗ 等距偏移线在**凹角**本身带尖点，压平它需要超大窗口，环会塌缩成椭圆 |
| #3 | **尺度空间（scale-space）**：陆地掩膜高斯模糊 σ，再取等值线 | ✓ 曲率天然被 σ 限住，无尖点 |

**为什么 #3 对**：OSM 岸线含 130° 级别的极尖角（码头/礁石，点距仅 5–10 m）。
对二值陆地掩膜做 σ 高斯模糊后，等值线的曲率上界约 1/σ；
用二分法调 level 就能精确控制"离岸距离中位数"。

最后再做**自适应曲率限制**：只对局部转弯半径 < 900 m 的位置做加权平滑，
其余位置保留 σ=1000 m 尺度下的岸线细节。

> 脚本：`scripts/build_coastline_route.py`
> 用法：`python build_coastline_route.py [sigma] [目标离岸距离] [目标最小转弯半径]`
> 实测采用：σ=1000 m，离岸中位 500 m，局部最小转弯半径 ≥900 m

## 5. 改动清单

| 文件 | 改动 |
|---|---|
| `Assets/_FlightDemo/Configs/CoastlineRoute_Circuit_v5.json` | **新增**，256 点闭合贴岸航线 |
| `Assets/_FlightDemo/Configs/CoastlineRoute_Circuit_v5.json.meta` | **新增**，guid `7d4b2ca6f1e94c3a9b52d80e6f3c1a47` |
| `Assets/_FlightDemo/Scenes/HKFlight_Demo.unity` | `Route` 节点 `coastlineRouteAsset` 指向 v5（已由 Unity 保存） |
| `CoastlineRoute_SheungWan_v3.json` / v4 / v2 / Current | **原样保留未动**（含 03 文档"不得把 v4 当已修复版本"的约束） |
| 代码（FlightController / DemoSafety / DemoRoute / DemoHUD / DemoOrbitCamera） | **一行未改** |
| `lapDurationSeconds` / `altitude` | 保持 240 s / 700 m 不变 |

备份：`output/FlightDemo/BACKUP_coastline_route_sheungwan_v3.json`

## 6. 验证证据（全部在 Unity 内实测）

### 6.1 路线数据检查（Unity 内 `DemoRoute`）
- `Length = 42762.0 m`，`TargetSpeed = 178.17 m/s (641 km/h)` @ 240 s 一圈
- 采样 2048 点：`max|x| = 7660 < 9980`、`max|z| = 5967 < 7980`、`minY = 700`（世界边界内、海面以上）
- `DemoSafety.SegmentSafe` 失败段数 **0 / 2048**
- 即使**重新打开岛内保护罩**（`HitsShield` 用 10800×7900 / 顶 660 m），
  航线段命中 **0 / 2048**、相机段命中 **0 / 2048**（700 m 高于罩顶 660 m）
- Unity 侧采样最小转弯半径 **900 m**

### 6.2 Unity 真实地形射线检测（权威）
给 `HongKongIsland_PBR_Draco_FIXED2` 下 2730 个网格临时挂 MeshCollider，
在 169×138 的 100 m 网格上向下投射 23322 条射线（命中 7876 个陆地格点），
再用这份掩膜计算两条航线的离陆距离（各 3000 采样）：

| 指标 | BEFORE v3 | AFTER v5 |
|---|---|---|
| 离陆中位数 | 897 m | **567 m** |
| 离陆最大值 | 5316 m | **1089 m** |
| >2 km 占比 | 23.7% | **0.0%** |
| >3 km 占比 | 16.6% | **0.0%** |
| 12%–25% 区间中位 | 2092 m | **563 m** |
| 12%–25% 区间最大 | 4669 m | **748 m** |

数据：`output/FlightDemo/unity_raycast_v5.json`、`route_fix_report.json`
图表：`output/FlightDemo/route_fix_report.png`

### 6.3 Play Mode 实机跑圈
`Time.timeScale = 8` 加速跑满一整圈（进度 1.2% → 100%）：

- `ResetCount = 0`、`RejectedMoves = 0`、`ProtectionCount = 0`、`Protecting = False`
- 高度恒为 `700 m`，速度恒为 `178.2 m/s`，HUD Notice 恒为「自动环岛巡航」
- 实时轨迹离陆中位 555 m / 最大 952 m
- **12%–25% 区间离陆中位 573 m / 最大 730 m**
- Unity Console：0 error / 0 warning

轨迹：`output/FlightDemo/playmode_track_v5.json`
截图（问题区间实拍）：`output/FlightDemo/route_v5_progress_{135,175,215,245}.png`

## 7. 遗留与注意

- 新航线在 4 处岬角尖端会轻微掠入 OSM 陆界内（256 个控制点中 15 个，Unity 100 m 掩膜判定 16 个）。
  均在 700 m 高空通过，海拔裕度 >150 m，属有意为之的"掠过岬角"效果。
- 若要求"全程严格在水面上方"，把 `build_coastline_route.py` 的目标离岸距离从 500 提到 700 再生成即可。
- v2 / v3 / v4 / Current 四个历史航线文件仍留在 Configs 目录，属历史版本，未被引用。
