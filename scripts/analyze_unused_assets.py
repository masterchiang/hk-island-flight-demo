"""
分析「新-项目编译源文件」里哪些资源已经不再被场景引用（= 可视为废弃）。

做法：从场景出发做 GUID 引用图遍历。
  · 除已知二进制类型外，所有文件都尝试按字节搜 GUID（YAML 资产才是引用来源）
  · 排除文件自身的 GUID
  · Resources/ 是运行时按名加载，GUID 遍历扫不到 → 单独标注为"保留"
  · *.cs 一律会被 Unity 编译 → 单独标注，不参与"废弃"判定
"""
import os, re, json
from collections import defaultdict, deque

PKG = r"<PROJECT_ROOT>/新-项目编译源文件"
ASSETS = os.path.join(PKG, "UnityProject", "Assets")
GUID_RE = re.compile(rb"guid:\s*([0-9a-fA-F]{32})")

BINARY_EXT = {".glb", ".gltf", ".png", ".jpg", ".jpeg", ".tga", ".psd", ".wav", ".mp3",
              ".fbx", ".obj", ".bin", ".zip", ".ttf", ".otf", ".exr", ".hdr", ".dll",
              ".so", ".bundle", ".cubemap", ".gif", ".bmp", ".tif", ".tiff"}


def read(p, limit=None):
    try:
        with open(p, "rb") as f:
            return f.read() if limit is None else f.read(limit)
    except Exception:
        return b""


def walk_files(root):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            yield os.path.join(dp, f)


# ---- 1. GUID -> 资源路径 ----
meta_guid = {}          # meta路径 -> guid
guid2target = {}        # guid -> 资源路径
for p in walk_files(ASSETS):
    if not p.endswith(".meta"):
        continue
    m = GUID_RE.search(read(p, 512))
    if not m:
        continue
    g = m.group(1).decode().lower()
    meta_guid[p] = g
    t = p[:-5]
    if os.path.exists(t):
        guid2target[g] = t

assets = [p for p in walk_files(ASSETS) if not p.endswith(".meta")]
print(f"资源 {len(assets)} 个；有 guid 的 {len(guid2target)} 个")

# ---- 2. 每个资源引用了哪些 GUID ----
refgraph = {}
for p in assets:
    ext = os.path.splitext(p)[1].lower()
    own = meta_guid.get(p + ".meta")
    if ext in BINARY_EXT:
        refgraph[p] = set()
        continue
    data = read(p)
    gs = set(g.decode().lower() for g in GUID_RE.findall(data))
    gs.discard(own)
    refgraph[p] = gs

# ---- 3. 从场景出发遍历 ----
scenes = [p for p in assets if p.lower().endswith(".unity")]
print("起点场景:", [os.path.relpath(s, ASSETS) for s in scenes])

seen, q = set(), deque(scenes)
while q:
    cur = q.popleft()
    if cur in seen:
        continue
    seen.add(cur)
    for g in refgraph.get(cur, ()):
        t = guid2target.get(g)
        if t and t not in seen:
            q.append(t)

print(f"可达（被引用）资源: {len(seen)} / {len(assets)}")

# ---- 4. 分类未引用项 ----
def classify(p):
    rel = os.path.relpath(p, ASSETS)
    ext = os.path.splitext(p)[1].lower()
    parts = rel.split(os.sep)
    if ext == ".cs":
        return "代码（Unity 总会编译，不能当废弃）"
    if "Resources" in parts:
        return "Resources 运行时按名加载（保留）"
    if rel.startswith("Scenes") and "SampleScene" in rel:
        return "Unity 模板场景（可留可删）"
    if ext == ".shader":
        return "着色器（可能被材质以名引用）"
    return "★ 未被场景引用"

groups = defaultdict(list)
for p in assets:
    if p in seen:
        continue
    groups[classify(p)].append(p)

for k in sorted(groups):
    items = sorted(groups[k], key=lambda x: -os.path.getsize(x))
    tot = sum(os.path.getsize(x) for x in items)
    print(f"\n=== {k}   共 {len(items)} 项 / {tot/1048576:.1f} MB ===")
    for p in items:
        print(f"   {os.path.getsize(p)/1048576:8.2f} MB  {os.path.relpath(p, ASSETS)}")

# ---- 5. 孤儿 .meta ----
print("\n=== 孤儿 .meta（对应资源已不在包里）===")
for dp, dn, fn in os.walk(ASSETS):
    names = set(fn)
    for f in fn:
        if f.endswith(".meta"):
            b = f[:-5]
            if b not in names and not os.path.isdir(os.path.join(dp, b)):
                print("   ", os.path.relpath(os.path.join(dp, f), ASSETS))
