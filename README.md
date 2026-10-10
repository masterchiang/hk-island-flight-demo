# 香港岛环岛飞行演示 · Cessna 310

一个用 Unity 制作的展示 DEMO：驾驶 **Cessna 310** 沿香港岛**真实海岸线**自动环岛巡航，
带第三人称跟随相机、可解锁自由驾驶、HUD 与背景音乐。

> **直接玩（Windows 64 位）**：到 [Releases](https://github.com/masterchiang/hk-island-flight-demo/releases) 下载成品压缩包，
> 解压后双击 `HKFlightDemo.exe` 即可，全屏无边框启动，无需安装。

## 本版本要点（2026-10-10）

- 飞机由 J-20 换为 **Cessna 310**，左右螺旋桨**各自独立旋转**（1600 RPM，暂停即停转）。
- 修复中环—上环两处**地下港铁车站被误当作地上建筑**拉伸出的灰色片状几何。
- 恢复**汇丰银行总行大厦**外墙完整高细节模型（去除透射，修正透空与排序异常）。
- 移除自定义启动 Logo 片头，以及 HUD 中的 J-20 与国庆祝贺文字；保留项目作者与代码构建署名。
- 历史 J-20 与启动 Logo 素材已从本源码包移除。

完整变更记录见 [`docs/FlightDemo/修复与替换说明_20261010.md`](docs/FlightDemo/修复与替换说明_20261010.md)。

## 环境

- 引擎版本：**Unity 6000.6.2f1**
- 演示场景：`UnityProject/Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`
- 打包产物：Windows x86_64 独立 EXE（`FullScreenWindow` + 显示器原生分辨率）

## ⚠️ 克隆后第一步：安装 Git LFS

本仓库有 3 个大二进制文件由 **Git LFS** 管理，合计约 305 MB：

| 文件 | 大小 | 说明 |
|---|---|---|
| `UnityProject/Assets/_FlightDemo/Art/World/HongKongIsland_PBR_Draco_FIXED2.glb` | 161 MB | 香港岛地图模型 |
| `.../Art/World/CentralRepairs/HKI_Remote_Residential_and_Lowrise_LOD_Fixed.asset` | 77 MB | 中环修复网格 |
| `.../Art/World/CentralRepairs/HKI_RF_Shells_Fixed.asset` | 66 MB | 中环修复网格 |

```bash
git lfs install
git clone https://github.com/masterchiang/hk-island-flight-demo.git
```

不装 LFS 直接克隆只会拿到指针文件；若直接提交，还会因「单文件超过 100 MB」被 GitHub 拒绝整次 push。

> `CentralRepairs/*_Fixed.asset` 是场景引用的修复网格，**不要删除**：原始压缩 GLB 并未被改写，
> 中环—上环两处修复依赖这两个文件在运行时覆盖。

## 目录结构

| 路径 | 说明 |
|---|---|
| `UnityProject/` | Unity 工程（原工程目录名为 `My project (1)`） |
| `UnityProject/Assets/_FlightDemo/` | 本 DEMO 的全部素材与源码，自成一体 |
| `UnityProject/Packages/manifest.json` | 包依赖（含从 Git URL 引入的 `com.coplaydev.unity-mcp`） |
| `UnityProject/ProjectSettings/` | 工程设置（已脱敏：清除 Unity Cloud / 组织 / 账号标识） |
| `scripts/` | Blender 侧建模与数据处理脚本（地形、建筑、地标、航线等） |
| `docs/FlightDemo/` | 开发与接手文档、验证记录 |
| `data/processed/` | 处理后的 GIS/OSM 中间数据（重新生成地图时需要） |

核心内容都在 `Assets/_FlightDemo/`：

```
_FlightDemo/
├── Scripts/     # DemoStartup(全屏启动) DemoHUD(界面/音乐) DemoRoute(航线)
│                # FlightController(飞控) DemoSafety(保护区) DemoOrbitCamera(相机)
│                # AircraftPropellers(独立螺旋桨)
├── Editor/      # 场景搭建、素材接入、检查脚本
├── Configs/     # 航线数据(JSON 控制点)
├── Art/         # Aircraft/Cessna310、World(地图 GLB、CentralRepairs、HSBC)
├── Materials/ Shaders/   # 程序化材质、海水着色器
├── Resources/   # 运行时加载入口（背景音乐本体未随包提供）
└── Scenes/      # HKFlight_Demo.unity
```

## 打开工程

1. 用 Unity Hub 打开 `UnityProject/` 目录（首次导入较慢，地图网格量较大）。
2. `Packages/manifest.json` 里有一个 Git URL 依赖，需要能访问 GitHub；若不需要
   Unity MCP 编辑器桥，可以把它从 `manifest.json` 删掉。
3. 打开场景 `Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`，进入 Play Mode。

## 构建 Windows EXE

`UnityProject/ProjectSettings/EditorBuildSettings.asset` 里**已经配好了场景顺序**：

| 序号 | 场景 | 启用 |
|---|---|---|
| 0 | `Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`（演示） | ✅ |
| 1 | `Assets/Scenes/SampleScene.unity`（Unity 模板场景） | ❌ |

直接 `File > Build Settings > Build`（Windows / x86_64）即可得到与作者交付版本一致的
可执行文件；玩家设置（全屏无边框、原生分辨率、产品名 `HKFlightDemo`）也已随
`ProjectSettings` 一并提供。

> 唯一差异：本仓库不含背景音乐，自行构建的版本**没有 BGM**。

## 操作

| 按键 | 功能 |
|---|---|
| `Tab` | 解锁 / 锁定手动驾驶 |
| `W` / `S` | 抬头 / 俯冲 |
| `A` / `D` | 左转 / 右转 |
| `Shift` / `Ctrl` | 加速 / 减速 |
| `R` | 复位回自动巡航 |

## 功能要点

- **自动环岛巡航**：闭合航线约 42.8 km，240 秒一圈（约 641 km/h），高度 700 m，
  离岸中位约 567 m / 最大约 1089 m，全程不脱离岛岸。
- **全屏无边框**：以 `FullScreenWindow` + 显示器原生分辨率启动，分辨率自适应
  （HUD 用 `CanvasScaler` 按 1920×1080 参考分辨率缩放）。
- **相机**：第三人称跟随，跟随距离 30 m、最小缩放距离 15 m，适配 Cessna 310 体量。
- **HUD**：速度 / 海拔 / 航向 / 航线进度、POV 视场角滑块、暂停 / 帮助 / 退出、
  背景音乐开关，顶栏含项目署名。
- **背景音乐**：循环播放，可一键开关（本体未随包提供，见下）。

## 素材署名与许可

- 项目作者：<https://github.com/masterchiang>
- 代码构建：Atria Dawn LLM

第三方素材按其自身协议授权，**不受本项目 Apache-2.0 变更**：

- **Cessna 310 Airplane - Low Poly** —— 作者 BorealRiver，许可 **CC BY 4.0**，
  来源 <https://sketchfab.com/3d-models/cessna-310-airplane-low-poly-bbf73d06537c4a2ba86b96a3b97209c1>。
  署名文件：`UnityProject/Assets/_FlightDemo/Art/Aircraft/Cessna310/ATTRIBUTION.txt`。
  再分发必须保留署名。
- **香港岛地形与城市数据** —— OpenStreetMap 贡献者（**ODbL 1.0**）与香港地政总署 DTM。
- **历史素材 J-20**（CC-BY-4.0，作者 42manako）已从本源码包移除，署名信息保留作历史记录。

完整清单见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

> **背景音乐《东方之珠》未包含在本仓库中**：该曲目为第三方版权作品，公开分发存在版权风险，
> 已从快照中剔除。代码中保留加载入口，可自行替换为 CC0 / 自制音频。

## 开源协议

本项目**原创代码与素材**以 **Apache License 2.0** 发布，全文见 [`LICENSE`](LICENSE)，
署名与归属说明见 [`NOTICE`](NOTICE)。

```
Copyright 2026 masterchiang

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```