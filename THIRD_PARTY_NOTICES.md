# 第三方素材署名与许可

本项目**自身的原创代码与素材**以 **Apache License 2.0** 发布（见 [`LICENSE`](LICENSE)、[`NOTICE`](NOTICE)）。

下面列出的第三方素材**按其自身协议授权，不受本项目 Apache-2.0 变更**。
**如果你再分发本项目，请保留本文件。**

---

## 1. J-20 战斗机模型 —— CC-BY-4.0

- 标题：Chinese Chengdu J-20
- 作者：**42manako**（<https://sketchfab.com/42manako>）
- 来源：<https://sketchfab.com/3d-models/chinese-chengdu-j-20-b9e81062c94545ffb0232d3ac6b7adc5>
- 许可：**CC-BY-4.0**（<http://creativecommons.org/licenses/by/4.0/>）—— 允许商用，**必须署名**

署名文本（原样保留自模型附带的 `license.txt`）：

> This work is based on "Chinese Chengdu J-20"
> (<https://sketchfab.com/3d-models/chinese-chengdu-j-20-b9e81062c94545ffb0232d3ac6b7adc5>)
> by 42manako (<https://sketchfab.com/42manako>) licensed under CC-BY-4.0
> (<http://creativecommons.org/licenses/by/4.0/>).

文件位置：`UnityProject/Assets/_FlightDemo/Art/Aircraft/J20_ChineseChengdu_CC_BY_4_0/license.txt`
（另有原始下载副本于 `J-20/license.txt`）

**已知缺失**：源 GLTF 引用以下两张图片，原素材中即已缺失，未用占位图冒充：

- `textures/27_66_0ec19d06f12efab_baseColor.jpeg`
- `textures/27_66_0ec19d06f12efab_4_baseColor.jpeg`

---

## 2. 香港岛地形与城市数据 —— ODbL / 政府公开资料

地形的几何与属性来自以下来源，经脚本处理后在 Blender 中重建：

- **OpenStreetMap**：建筑轮廓、道路、交通线路、植被等。
  数据 © OpenStreetMap 贡献者，许可 **ODbL 1.0**（<https://www.openstreetmap.org/copyright>）。
  香港岛边界取自 OSM relation 4556901。
- **香港地政总署 DTM**（数码地形模型，5 m / 25 m 网格）：用于地形高程匹配。
  属政府公开资料，使用请遵守其条款。
- 公开街景/照片仅用于体量、材质风格的**参考**，未将 Google / 百度等图片直接打包为纹理。

处理脚本见 `scripts/`（`extract_hki.py`、`prepare_terrain.py`、`build_*` 等）。

---


