"""
验证「项目编译源文件」能否被其他人在 Unity 里完整打开/构建。

核心检查：把包内所有资源引用到的 GUID，逐一比对
  (a) 包内自带 .meta 的 GUID 集合
  (b) 原工作工程 Assets/ 的 GUID 集合
凡是被引用、且在原工程里属于 Assets 资源、但包里没有的 → 就是真缺口。
"""
import os, re, json
from collections import defaultdict

SRC = r"<PROJECT_ROOT>"
PKG = os.path.join(SRC, "项目编译源文件")
WORK_ASSETS = os.path.join(SRC, "My project (1)", "Assets")
PKG_ASSETS = os.path.join(PKG, "UnityProject", "Assets")

GUID_RE = re.compile(rb"guid:\s*([0-9a-fA-F]{32})")
TEXT_EXT = {".unity", ".prefab", ".asset", ".mat", ".meta", ".controller", ".anim",
            ".playable", ".overrideController", ".spriteatlas", ".terrainlayer",
            ".shadergraph", ".shadersubgraph", ".renderTexture", ".mixer", ".preset",
            ".inputactions", ".json", ".txt", ".md", ".cs", ".shader", ".hlsl", ".cginc"}

# Unity 内置资源 GUID（不是 Assets 里的文件）
BUILTIN = {
    "0000000000000000e000000000000000", "0000000000000000f000000000000000",
    "0000000000000000d000000000000000", "0000000000000000c000000000000000",
    "00000000000000000000000000000000",
}


def collect_guids(root):
    """返回 {guid: meta路径}"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".meta"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                head = open(p, "rb").read(400)
            except Exception:
                continue
            m = GUID_RE.search(head)
            if m:
                out[m.group(1).decode().lower()] = p
    return out


def collect_refs(root, skip_meta=True):
    """返回 {guid: [引用它的文件...]}"""
    refs = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"Library", "Temp", "obj"}]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            if skip_meta and fn.endswith(".meta"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > 60 * 1024 * 1024:
                    continue
                data = open(p, "rb").read()
            except Exception:
                continue
            for g in set(GUID_RE.findall(data)):
                refs[g.decode().lower()].append(os.path.relpath(p, root))
    return refs


print("收集 GUID ...")
pkg_guids = collect_guids(PKG_ASSETS)
work_guids = collect_guids(WORK_ASSETS)
print(f"  包内  Assets .meta 数: {len(pkg_guids)}")
print(f"  原工程 Assets .meta 数: {len(work_guids)}")

print("收集引用 ...")
refs = collect_refs(PKG)
print(f"  包内被引用的不同 GUID 数: {len(refs)}")

missing_assets = []     # 原工程里属于 Assets、包里没有 → 真缺口
external = []           # 既不在包里也不在原工程 Assets → 视为包/内置
for g, users in refs.items():
    if g in BUILTIN:
        continue
    if g in pkg_guids:
        continue
    if g in work_guids:
        missing_assets.append((g, os.path.relpath(work_guids[g], SRC), users[:4]))
    else:
        external.append((g, users[:3]))

print("\n=== 结论 ===")
print(f"[真缺口] 被引用但在包里找不到的资源: {len(missing_assets)}")
for g, path, users in sorted(missing_assets, key=lambda x: x[1]):
    print(f"   GUID {g}")
    print(f"     原工程: {path}")
    print(f"     被引用于: {users}")

print(f"\n[外部依赖] 不在原工程 Assets 里的 GUID（应为 Package/内置）: {len(external)}")
for g, users in external[:15]:
    print(f"   {g}  <- {users}")
if len(external) > 15:
    print(f"   ... 另有 {len(external)-15} 个")

json.dump({"missing": [(g, p, u) for g, p, u in missing_assets],
           "external_count": len(external)},
          open(os.path.join(SRC, "output/FlightDemo/_pkg_guid_audit.json"), "w"),
          ensure_ascii=False, indent=1)
