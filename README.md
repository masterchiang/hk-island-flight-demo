# 香港岛 J-20 飞行演示 · 源码与素材

一个 Unity 制作的展示 DEMO：驾驶 J-20 沿着**香港岛真实海岸线**自动环岛巡航，
带第三人称跟随相机、可解锁自由驾驶、HUD、背景音乐与国庆祝贺片头。

- 引擎版本：**Unity 6000.6.2f1**
- 演示场景：`UnityProject/Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`
- 打包产物：Windows64 独立 EXE（全屏无边框、跟随显示器原生分辨率）

> ## ⚠️ 克隆后第一步：`git lfs install`
>
> 仓库里的香港岛地图模型（161 MB）由 **Git LFS** 管理。请先在仓库根目录执行一次：
> ```
> git lfs install
> ```
> 否则该文件不会被正确拉取/提交，push 也会被 GitHub 以「单文件超过 100 MB」拒绝。
>
> 本仓库是**预备上传用的脱敏快照**：已剔除编辑器缓存、构建产物与本机绝对路径。
> 地图模型**已包含**；唯一缺失的是第三方版权音频《东方之珠》——
> 详见 [`缺失素材与补回说明.md`](缺失素材与补回说明.md)。

---

## 目录结构

| 路径 | 说明 |
|---|---|
| `UnityProject/` | Unity 工程（原工程目录名为 `My project (1)`） |
| `UnityProject/Assets/_FlightDemo/` | 本 DEMO 的全部素材与源码，自成一体 |
| `UnityProject/Packages/manifest.json` | 包依赖（含从 Git URL 引入的 `com.coplaydev.unity-mcp`） |
| `UnityProject/ProjectSettings/` | 工程设置（已脱敏：清除 Unity Cloud / 组织 / 账号标识） |
| `scripts/` | Blender 侧建模与数据处理脚本（香港岛地形、建筑、地标、航线等） |
| `docs/FlightDemo/` | 开发与接手文档、验证记录 |
| `data/processed/` | 处理后的 GIS/OSM 中间数据（重新生成地图时需要） |
| `LOGO.jpg` | 片头 LOGO 设计源图（同一张图也在 `UnityProject/.../Resources/LOGO.jpg`） |
| `J-20/` | J-20 模型的原始下载（与 Unity 工程内那份一致） |

`UnityProject/Assets/` 下保留了 Unity 工程自身的目录层级；核心内容都在
`Assets/_FlightDemo/`：

```
_FlightDemo/
├── Scripts/     # DemoStartup(片头+全屏)、DemoHUD(界面/音乐)、DemoRoute(航线)、
│                # FlightController(飞控)、DemoSafety(保护区)、DemoOrbitCamera(相机)
├── Editor/      # 场景搭建、素材接入、检查脚本
├── Configs/     # 航线数据(JSON 控制点)
├── Art/         # 世界与飞机模型、材质（含 161 MB 香港岛地图 GLB，走 Git LFS）
├── Materials/ Meshes/ Shaders/   # 程序化材质、网格、海水着色器
├── Resources/   # 运行时加载：片头 LOGO
└── Scenes/      # HKFlight_Demo.unity
```

## 打开工程

1. 用 Unity Hub 打开 `UnityProject/` 目录（首次导入需要较长时间，地图网格量较大）。
2. `Packages/manifest.json` 里有一个 Git URL 依赖，需要能访问 GitHub；若不需要
   Unity MCP 编辑器桥，可以把它从 `manifest.json` 删掉。
3. 打开场景 `Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`。
4. 进入 Play Mode。

## 构建 Windows EXE

`UnityProject/ProjectSettings/EditorBuildSettings.asset` 里**已经配好了场景顺序**：

| 序号 | 场景 | 启用 |
|---|---|---|
| 0 | `Assets/_FlightDemo/Scenes/HKFlight_Demo.unity`（演示） | ✅ |
| 1 | `Assets/Scenes/SampleScene.unity`（Unity 模板场景） | ❌ |

所以直接 `File > Build Settings > Build` 或 `Build And Run`（Windows / x86_64）即可得到
与本项目作者交付版本一致的可执行文件；玩家设置（全屏无边框、原生分辨率、产品名
`HKFlightDemo`）也已随 `ProjectSettings` 一并提供。

> 唯一差异：本仓库不含背景音乐，构建出来的版本**没有 BGM**。
> 补回方式见 [`缺失素材与补回说明.md`](缺失素材与补回说明.md)。

## 功能要点

- **自动环岛巡航**：闭合航线约 42.8 km，240 秒一圈（约 641 km/h），高度 700 m，
  离岸中位约 567 m / 最大约 1089 m，全程不脱离岛岸。
- **片头**：Unity 官方启动画面之后，全屏展示 `LOGO.jpg` 保持 2.5 秒（+0.3 秒淡出），
  期间飞行暂停，结束即进入 DEMO。
- **全屏无边框**：Player 以 `FullScreenWindow` + 显示器原生分辨率启动，分辨率自适应
  （HUD 用 `CanvasScaler` 按 1920×1080 参考分辨率缩放）。
- **手动驾驶**：`Tab` 解锁；`W/S` 抬头/俯冲，`A/D` 转向，`Shift/Ctrl` 加减速，
  `R` 复位回自动巡航。
- **HUD**：速度/海拔/航向/航线进度、POV 视场角滑块、暂停/帮助/退出、
  背景音乐开关；顶栏含项目署名与国庆祝贺文字。
- **背景音乐**：循环播放，可一键开关（见下方版权说明）。

## 署名

- 项目作者：<https://github.com/masterchiang>
- 代码构建：Atria Dawn LLM

第三方素材的授权与出处见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 开源协议

本项目源码以 **Apache License 2.0** 发布，全文见 [`LICENSE`](LICENSE)。

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

> ⚠️ Apache-2.0 只覆盖**本项目的原创代码与素材**。
> 仓库内引用的第三方素材按其自身协议授权，**不受 Apache-2.0 变更**——
> 尤其是 J-20 模型（CC-BY-4.0，**必须保留署名**）。
> 详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
