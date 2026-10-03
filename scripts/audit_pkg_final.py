"""
源文件包完整性最终审计（干净版）。

判定逻辑：
  对包内每个资源引用到的 GUID，分成三类
    A. 包内自带 .meta（Assets 资源）           -> 自足
    B. 原工作工程的 Library/PackageCache 里有  -> 由 Package Manager 提供
    C. 都不在                                   -> 应为 Unity 内置组件
  关键判据：把同样的统计在原工作工程（已知可用、能构建）上跑一遍，
  两边 C 类的数量/集合应当一致 —— 一致就说明包不缺任何东西。
"""
import os, re, json
from collections import defaultdict

SRC = r"<PROJECT_ROOT>"
PKG = os.path.join(SRC, "项目编译源文件")
UNITY_PKG = os.path.join(PKG, "UnityProject")
WORK = os.path.join(SRC, "My project (1)")

GUID_RE = re.compile(rb"guid:[\s]*([0-9a-fA-F]{32})")
ASSET_EXT = {".unity", ".prefab", ".asset", ".mat", ".controller", ".anim", ".playable",
             ".overrideController", ".spriteatlas", ".terrainlayer", ".inputactions",
             ".preset", ".mixer", ".renderTexture"}


def guids_in_metas(root):
    out = {}
    for dp, _, fns in os.walk(root):
        for f in fns:
            if not f.endswith(".meta"):
                continue
            p = os.path.join(dp, f)
            try:
                m = GUID_RE.search(open(p, "rb").read(512))
            except Exception:
                continue
            if m:
                out[m.group(1).decode().lower()] = os.path.relpath(p, root)
    return out


def refs_in(root, exts):
    out = defaultdict(list)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {"Library", "Temp", "obj"}]
        for f in fns:
            if os.path.splitext(f)[1].lower() not in exts:
                continue
            p = os.path.join(dp, f)
            try:
                if os.path.getsize(p) > 80 * 1024 * 1024:
                    continue
                data = open(p, "rb").read()
            except Exception:
                continue
            for g in set(GUID_RE.findall(data)):
                out[g.decode().lower()].append(os.path.relpath(p, root))
    return out


cache_root = os.path.join(WORK, "Library", "PackageCache")
cache_guids = guids_in_metas(cache_root) if os.path.isdir(cache_root) else {}
print(f"PackageCache 可提供的 GUID: {len(cache_guids)}")


def audit(label, assets_root, scan_root):
    own = guids_in_metas(assets_root)
    refs = refs_in(scan_root, ASSET_EXT)
    a = [g for g in refs if g in own]
    b = [g for g in refs if g not in own and g in cache_guids]
    c = [g for g in refs if g not in own and g not in cache_guids]
    print(f"\n=== {label} ===")
    print(f"  自身 .meta 提供 {len(own)} 个 GUID")
    print(f"  被引用的 GUID 共 {len(refs)}")
    print(f"    A 包/工程内自足      : {len(a)}")
    print(f"    B 由 PackageCache 提供: {len(b)}")
    print(f"    C 未解析(应为内置组件): {len(c)}")
    return set(c), own, refs


c_pkg, own_pkg, refs_pkg = audit("源文件包  UnityProject/Assets", 
                                 os.path.join(UNITY_PKG, "Assets"), 
                                 os.path.join(UNITY_PKG, "Assets"))
c_work, own_work, refs_work = audit("原工作工程 Assets（已知可构建）",
                                    os.path.join(WORK, "Assets"),
                                    os.path.join(WORK, "Assets"))

print("\n=== 交叉判定 ===")
only_pkg = c_pkg - c_work
only_work = c_work - c_pkg
print(f"  包独有的未解析 GUID: {len(only_pkg)}  -> {sorted(only_pkg)}")
print(f"  原工程独有(包里已解析或不存在): {len(only_work)}")

# 真正该查的：包内被引用、原工程里属于 Assets、包里却没有
refs_missing = []
for g, users in refs_pkg.items():
    if g in own_pkg or g in cache_guids:
        continue
    if g in own_work and g not in own_pkg:
        refs_missing.append((g, own_work[g], users[:3]))
print(f"\n  被引用但包里确实缺失的 Assets 资源: {len(refs_missing)}")
for g, path, users in refs_missing:
    print(f"    {g}  <- 原工程 {path}  用于 {users}")

# 反向：包里有 .meta 但对应资源被删（孤儿）
print("\n=== 孤儿 .meta（资源被有意排除）===")
orphan = []
for dp, _, fns in os.walk(os.path.join(UNITY_PKG, "Assets")):
    names = set(fns)
    for f in fns:
        if not f.endswith(".meta"):
            continue
        base = f[:-5]
        if base not in names and not os.path.isdir(os.path.join(dp, base)):
            orphan.append(os.path.relpath(os.path.join(dp, f), UNITY_PKG))
for o in orphan:
    print("   ", o)

json.dump({"pkg_unresolved": sorted(c_pkg), "work_unresolved": sorted(c_work),
           "refs_missing": [(g, p) for g, p, _ in refs_missing],
           "orphan_metas": orphan},
          open(os.path.join(SRC, "output/FlightDemo/_pkg_final_audit.json"), "w"),
          ensure_ascii=False, indent=1)
