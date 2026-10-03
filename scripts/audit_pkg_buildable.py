"""源文件包可构建性的其余检查：包引用解析、.meta 配对、C# 差异、包依赖。"""
import os, re, json, filecmp
from collections import defaultdict

SRC = r"<PROJECT_ROOT>"
PKG = os.path.join(SRC, "项目编译源文件")
UNITY_PKG = os.path.join(PKG, "UnityProject")
WORK = os.path.join(SRC, "My project (1)")
PKG_ASSETS = os.path.join(UNITY_PKG, "Assets")
WORK_ASSETS = os.path.join(WORK, "Assets")

GUID_RE = re.compile(rb"guid:\s*([0-9a-fA-F]{32})")
TEXT_EXT = {".unity", ".prefab", ".asset", ".mat", ".controller", ".anim", ".playable",
            ".overrideController", ".spriteatlas", ".terrainlayer", ".mat", ".inputactions"}

# ---------- 1. 外部 GUID 能否由 PackageCache 解析 ----------
def guids_from(root):
    out = set()
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".meta"):
                try:
                    m = GUID_RE.search(open(os.path.join(dirpath, fn), "rb").read(400))
                    if m:
                        out.add(m.group(1).decode().lower())
                except Exception:
                    pass
    return out


pkg_guids = guids_from(PKG_ASSETS)
cache = os.path.join(WORK, "Library", "PackageCache")
cache_guids = guids_from(cache) if os.path.isdir(cache) else set()
print(f"PackageCache GUID 数: {len(cache_guids)}  (目录存在={os.path.isdir(cache)})")

refs = defaultdict(list)
for dirpath, dirnames, filenames in os.walk(PKG):
    dirnames[:] = [d for d in dirnames if d not in {"Library", "Temp", "obj"}]
    for fn in filenames:
        if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
            continue
        p = os.path.join(dirpath, fn)
        try:
            for g in set(GUID_RE.findall(open(p, "rb").read())):
                refs[g.decode().lower()].append(os.path.relpath(p, PKG))
        except Exception:
            pass

unknown = [g for g in refs if g not in pkg_guids and g not in cache_guids]
print(f"\n[1] 被引用 GUID 共 {len(refs)}；包内可解析 {len(refs)-len(unknown)}；"
      f"PackageCache 可解析 {sum(1 for g in unknown if g in cache_guids)}；"
      f"剩余（应为 Unity 内置组件）{len(unknown)}")

# 对照：同一个检查跑一遍原工程，看原工程是不是也有同样多的“未解析”
def audit_project(assets_root, project_root):
    pg = guids_from(assets_root)
    rf = defaultdict(int)
    for dirpath, dirnames, filenames in os.walk(assets_root):
        dirnames[:] = [d for d in dirnames if d not in {"Library", "Temp", "obj"}]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            try:
                for g in set(GUID_RE.findall(open(os.path.join(dirpath, fn), "rb").read())):
                    rf[g.decode().lower()] += 1
            except Exception:
                pass
    unk = [g for g in rf if g not in pg and g not in cache_guids]
    return len(rf), len(unk)


wr, wu = audit_project(WORK_ASSETS, WORK)
print(f"    对照原工程: 引用 {wr} 个 GUID，其中 PackageCache 也未覆盖 {wu} 个")
print(f"    -> 包与原工程的「外部依赖比例」对比: 包 {len(unknown)}/{len(refs)}，原工程 {wu}/{wr}")

# ---------- 2. .meta 配对 ----------
print("\n[2] .meta 配对检查")
missing_meta, orphan_meta = [], []
for dirpath, _, filenames in os.walk(PKG_ASSETS):
    names = set(filenames)
    for fn in filenames:
        if fn.endswith(".meta"):
            base = fn[:-5]
            if base not in names and os.path.splitext(base)[1] != "":
                orphan_meta.append(os.path.relpath(os.path.join(dirpath, fn), PKG))
            elif base not in names and not os.path.isdir(os.path.join(dirpath, base)):
                orphan_meta.append(os.path.relpath(os.path.join(dirpath, fn), PKG))
        else:
            if fn + ".meta" not in names:
                missing_meta.append(os.path.relpath(os.path.join(dirpath, fn), PKG))
print(f"    缺 .meta 的资源: {len(missing_meta)}")
for x in missing_meta[:20]:
    print("      ", x)
print(f"    孤儿 .meta（对应资源已被排除）: {len(orphan_meta)}")
for x in orphan_meta[:20]:
    print("      ", x)

# ---------- 3. C# 差异（应只有路径脱敏）----------
print("\n[3] C# 脚本差异（包 vs 原工程）")
only_pkg, only_work, differ, same = [], [], [], []
pkg_cs = {}
for dirpath, _, filenames in os.walk(PKG_ASSETS):
    for fn in filenames:
        if fn.endswith(".cs"):
            p = os.path.join(dirpath, fn)
            pkg_cs[os.path.relpath(p, PKG_ASSETS)] = p
for rel, p in sorted(pkg_cs.items()):
    w = os.path.join(WORK_ASSETS, rel)
    if not os.path.exists(w):
        only_pkg.append(rel); continue
    a = open(p, "rb").read(); b = open(w, "rb").read()
    if a == b:
        same.append(rel)
    else:
        differ.append((rel, a, b))
for dirpath, _, filenames in os.walk(WORK_ASSETS):
    for fn in filenames:
        if fn.endswith(".cs"):
            rel = os.path.relpath(os.path.join(dirpath, fn), WORK_ASSETS)
            if rel not in pkg_cs:
                only_work.append(rel)
print(f"    相同: {len(same)}；有差异: {len(differ)}；仅包内: {len(only_pkg)}；仅原工程: {len(only_work)}")
for rel, a, b in differ:
    ta, tb = a.decode("utf-8", "replace").splitlines(), b.decode("utf-8", "replace").splitlines()
    import difflib
    d = [l for l in difflib.unified_diff(tb, ta, lineterm="", n=0) if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    print(f"      {rel}: {len(d)} 处行差异")
    for l in d[:6]:
        print("        ", l.strip()[:150])
if only_work:
    print(f"    [注意] 仅存在于原工程的脚本（包内缺失）: {only_work}")

# ---------- 4. 包依赖 ----------
print("\n[4] Packages/manifest.json 依赖")
mf = json.load(open(os.path.join(UNITY_PKG, "Packages", "manifest.json"), encoding="utf-8"))
for k, v in mf.get("dependencies", {}).items():
    if not k.startswith("com.unity.modules"):
        print(f"    {k}: {v}")
lock = os.path.join(UNITY_PKG, "Packages", "packages-lock.json")
print(f"    packages-lock.json 存在: {os.path.exists(lock)}")

# 我们的代码是否直接引用 MCPForUnity
mcp_hits = []
for dirpath, _, filenames in os.walk(PKG_ASSETS):
    for fn in filenames:
        if fn.endswith(".cs"):
            p = os.path.join(dirpath, fn)
            t = open(p, encoding="utf-8", errors="replace").read()
            if "MCPForUnity" in t or "UnityMCP" in t:
                mcp_hits.append(os.path.relpath(p, PKG))
print(f"    我们的脚本中引用 MCPForUnity 的文件: {mcp_hits if mcp_hits else '无'}")

# ---------- 5. Build Settings ----------
print("\n[5] Build Settings（EditorBuildSettings.asset）")
ebs = os.path.join(UNITY_PKG, "ProjectSettings", "EditorBuildSettings.asset")
t = open(ebs, encoding="utf-8", errors="replace").read()
for m in re.finditer(r"path:\s*(\S+)", t):
    print("    场景条目:", m.group(1))
