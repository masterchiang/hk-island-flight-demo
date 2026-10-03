# HKI Holographic Atlas

## 2026-10-02 — 香港演艺学院（HKAPA）专项建模

- OSM 主校园 way: `865670733` — Hong Kong Academy for Performing Arts.
- 建模集合：`15_Bespoke_HKAPA`。
- 根对象：`HKAPA_Main_Campus`。
- 结构由真实 OSM footprint、Lands Department DTM 高程、公开建筑形态参考共同推断，不宣称为摄影测量结果。
- 形体拆分：混凝土 podium、教学翼、中央剧院/黑盒体块、auditorium core、阶梯屋顶体量、acoustic lantern、入口雨棚、立面竖向 fins、窗带、入口玻璃幕墙和前场景观边界。
- 目标相机：`HKAPA_Check_Camera`，当前场景相机已锁定到香港演艺学院目标。
- 验收图：
  - `output/hkapa_isolated_check.png`
  - `output/hkapa_context_check.png`
  - `output/hkapa_top_check.png`
  - `output/hkapa_side_check.png`

## 数据与许可说明

- OSM / OpenStreetMap 数据仅按其许可使用并保留来源标识。
- GIS/DTM 用于地形与场地高程匹配。
- 公开街景/照片只作为体量、入口、幕墙和材料风格参考；未将 Google/Baidu 图片直接打包为可再分发纹理。
- 常规建筑仍是 OSM/GIS 与程序化外观推断，不等同于逐栋摄影测量。

## 既有工程状态

- 香港岛 OSM 建筑与道路、DTM、植被、交通线路、真实系 PBR 材质和照明系统均保留。
- 已清除异常白色巨型补地面：`VegGroundPatch_02`、`VegGroundPatch_03`。
- 主工程：`HKI_Holographic_Atlas.blend`。

## 2026-10-02 — HKCEC / HSBC 外观着色

- 香港会议展览中心：暖白外壳、银色铝制屋面、青绿色玻璃幕墙、深色竖梃、混凝土与铺装的真实系 PBR 变化。
- 汇丰总行大厦：将已导入的外墙纹理图集打包进工程，调为银蓝色玻璃/金属质感，保留 HSBC 标识，并增加轻微表面细节与涂层反射。
- 检查图：output/hkcec_realistic_color_check.png、output/hsbc_realistic_color_check.png`n
