"""Hopewell Centre bespoke landmark builder (batch B2).

Run inside Blender's Python environment. The module is intentionally isolated:
- it reads the shared input contract but does not modify it;
- it creates/replaces only its own B2 collection/root;
- it never opens, saves, or edits the main .blend file.

Public interface:
    build(name="Hopewell Centre", input_path=None, collection_name=None) -> dict

The input record is not present in data/processed/bespoke_landmark_inputs.json
(B1 currently contains five other landmarks), so this builder uses the OSM-derived
record in data/processed/hki_buildings.json as an explicitly documented fallback.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import bpy
    from mathutils import Vector
except ImportError:  # Allows syntax/import checks outside Blender.
    bpy = None
    Vector = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/bespoke_landmark_inputs.json"
OSM_BUILDINGS = ROOT / "data/processed/hki_buildings.json"
DEFAULT_COLLECTION = "13_Bespoke_Landmarks_B2_Hopewell"
REVISION = "2026-10-01-B2"
TARGET_NAME = "Hopewell Centre"
TARGET_OSM_ID = 2762122396

# Photo/plan interpretation, all metres. These are deliberately exposed so a
# later official 3D Tiles/GLTF source can replace the inferred values.
PROFILE = {
    "total_height": 216.0,
    "levels": 63,
    "tower_radius": 22.9,
    "tower_sides": 36,
    "base_z": 0.0,
    "podium_height": 28.0,
    "podium_radius": 54.0,
    "podium_floor_to_floor": 4.0,
    "tower_start_z": 27.0,
    "tower_floor_to_floor": 3.34,
    "tower_top_z": 207.0,
    "crown_height": 9.0,
    "crown_radius_bottom": 23.4,
    "crown_radius_top": 18.2,
    "facade_bays": 18,
    "fin_count": 36,
    "fin_width": 0.34,
    "fin_depth": 0.65,
}


class MeshBuilder:
    def __init__(self):
        self.vertices: List[Tuple[float, float, float]] = []
        self.faces: List[Tuple[int, ...]] = []
        self.material_indices: List[int] = []

    def face(self, points: Iterable[Sequence[float]], material: int = 0):
        start = len(self.vertices)
        pts = [tuple(float(v) for v in p) for p in points]
        self.vertices.extend(pts)
        self.faces.append(tuple(range(start, start + len(pts))))
        self.material_indices.append(material)

    def prism(self, ring: Sequence[Tuple[float, float]], z0: float, z1: float, material: int = 0):
        n = len(ring)
        bottom = [(x, y, z0) for x, y in ring]
        top = [(x, y, z1) for x, y in ring]
        self.face(reversed(bottom), material)
        self.face(top, material)
        for i in range(n):
            j = (i + 1) % n
            self.face((bottom[i], bottom[j], top[j], top[i]), material)

    def beam(self, a: Sequence[float], b: Sequence[float], width: float, depth: float, material: int = 0):
        a, b = Vector(a), Vector(b)
        axis = b - a
        if axis.length < 1e-6:
            return
        axis.normalize()
        ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
        u = axis.cross(ref).normalized() * (width * 0.5)
        v = axis.cross(u).normalized() * (depth * 0.5)
        ring = [-u - v, u - v, u + v, -u + v]
        self.face([a + p for p in reversed(ring)], material)
        self.face([b + p for p in ring], material)
        for i in range(4):
            j = (i + 1) % 4
            self.face((a + ring[i], a + ring[j], b + ring[j], b + ring[i]), material)

    def object(self, name: str, parent, materials):
        mesh = bpy.data.meshes.new(name + "_Mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        for material in materials:
            mesh.materials.append(material)
        for polygon, index in zip(mesh.polygons, self.material_indices):
            polygon.material_index = index
        obj = bpy.data.objects.new(name, mesh)
        parent.users_collection[0].objects.link(obj)
        obj.parent = parent
        obj["bespoke_revision"] = REVISION
        obj["generator"] = "scripts/agent_hopewell_b2.py"
        return obj


def _require_blender():
    if bpy is None:
        raise RuntimeError("This build function must run inside Blender's Python environment.")


def _load_record(input_path: Path | str = DEFAULT_INPUT) -> Dict:
    """Load the target record; use the local OSM extraction when B1 lacks it."""
    path = Path(input_path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in data.get("landmarks", []):
            if record.get("name") == TARGET_NAME:
                return dict(record)
    data = json.loads(OSM_BUILDINGS.read_text(encoding="utf-8"))
    candidates = [b for b in data.get("buildings", []) if b.get("id") == TARGET_OSM_ID]
    if not candidates:
        candidates = [b for b in data.get("buildings", []) if b.get("name") == TARGET_NAME]
    if not candidates:
        raise KeyError("Hopewell Centre record was not found in either input source")
    source = candidates[0]
    footprint = source["footprint"]
    cx = sum(p[0] for p in footprint) / len(footprint)
    cy = sum(p[1] for p in footprint) / len(footprint)
    return {
        "name": TARGET_NAME,
        "osm_id": str(source["id"]),
        "osm_url": f"https://www.openstreetmap.org/way/{source['id']}",
        "height_m": float(source.get("height", PROFILE["total_height"])),
        "osm_height_m": float(source.get("height", PROFILE["total_height"])),
        "osm_levels": float(source.get("levels", PROFILE["levels"])),
        "position": [cx, cy, 0.0],
        "rotation_z": 0.0,
        "footprint_local": footprint,
        "width": max(p[0] for p in footprint) - min(p[0] for p in footprint),
        "depth": max(p[1] for p in footprint) - min(p[1] for p in footprint),
        "sources": [
            f"https://www.openstreetmap.org/way/{source['id']}",
            "https://www.hopewellholdings.com/eng/hhl_hopewell_centre.htm",
            "https://www.hopewellcentre.com/",
        ],
        "precision": "OSM footprint + OSM height/levels + reference-led facade interpretation; not photogrammetry",
        "height_note": "Local OSM extraction reports 216 m and 63 levels; upper crown/roof apparatus is simplified.",
        "input_fallback": "data/processed/hki_buildings.json",
    }


def _collection(name: str):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _materials():
    def material(name, color, metallic=0.0, roughness=0.4):
        full = "B2_Hopewell_" + name
        mat = bpy.data.materials.get(full) or bpy.data.materials.new(full)
        mat.use_nodes = True
        principled = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness
        mat.diffuse_color = (*color, 1.0)
        return mat
    return [
        material("BlueGlass", (0.055, 0.16, 0.22), 0.5, 0.22),
        material("DarkSpandrel", (0.018, 0.028, 0.034), 0.35, 0.30),
        material("SilverFins", (0.54, 0.59, 0.60), 0.72, 0.26),
        material("PodiumStone", (0.30, 0.28, 0.23), 0.08, 0.62),
        material("PodiumGlass", (0.06, 0.11, 0.13), 0.42, 0.27),
        material("CrownMetal", (0.38, 0.42, 0.42), 0.72, 0.28),
        material("WarmInterior", (0.26, 0.15, 0.07), 0.1, 0.5),
    ]


def _ring(radius: float, z: float, sides: int = 36, phase: float = math.pi / 36):
    return [(radius * math.cos(2 * math.pi * i / sides + phase),
             radius * math.sin(2 * math.pi * i / sides + phase), z) for i in range(sides)]


def _poly_ring(rx: float, ry: float, sides: int = 36, phase: float = math.pi / 36):
    return [(rx * math.cos(2 * math.pi * i / sides + phase),
             ry * math.sin(2 * math.pi * i / sides + phase)) for i in range(sides)]


def _ring_beams(mesh: MeshBuilder, radius: float, z: float, sides: int, width: float, depth: float, material: int):
    points = _ring(radius, z, sides)
    for i, a in enumerate(points):
        b = points[(i + 1) % sides]
        mesh.beam(a, b, width, depth, material)


def _root(record: Dict, collection_name: str):
    collection = _collection(collection_name)
    prefix = "BESPOKE_B2_2762122396_Hopewell_Centre"
    for old in list(collection.objects):
        if old.name == prefix or old.name.startswith(prefix + "__"):
            bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(prefix, None)
    collection.objects.link(root)
    root.location = tuple(record["position"])
    root.rotation_euler[2] = float(record.get("rotation_z", 0.0))
    root.empty_display_size = 5.0
    for key, value in {
        "landmark_name": TARGET_NAME,
        "osm_id": str(record.get("osm_id", TARGET_OSM_ID)),
        "height_m": float(record.get("height_m", PROFILE["total_height"])),
        "levels": int(record.get("osm_levels", PROFILE["levels"])),
        "bespoke_revision": REVISION,
        "basis": "OSM footprint + OSM height/levels + official/secondary references",
        "detail_status": "Reference-led bespoke reconstruction; not photogrammetry",
        "input_contract": "data/processed/bespoke_landmark_inputs.json; Hopewell fallback documented in research",
        "recognition_features": "circular/36-sided tower, dense vertical fins, broad podium, stepped crown, rooftop ring",
    }.items():
        root[key] = value
    return root


def build(name: str = TARGET_NAME, input_path: Path | str = DEFAULT_INPUT, collection_name: str = DEFAULT_COLLECTION) -> Dict:
    """Build only Hopewell Centre and return a deterministic build summary."""
    _require_blender()
    if name != TARGET_NAME:
        raise ValueError(f"This isolated module only builds {TARGET_NAME!r}, not {name!r}")
    record = _load_record(input_path)
    materials = _materials()
    root = _root(record, collection_name)
    glass, spandrel, fins, stone, podium_glass, crown_metal, warm = materials
    meshes = []

    # 1) Low, broad commercial podium: stepped concentric rings, glazed lower band.
    podium = MeshBuilder()
    podium.prism(_poly_ring(PROFILE["podium_radius"] * 0.72, PROFILE["podium_radius"] * 0.55, 16, 0.0), 0.0, 7.0, 3)
    podium.prism(_poly_ring(PROFILE["podium_radius"] * 0.66, PROFILE["podium_radius"] * 0.50, 16, 0.0), 7.0, 15.0, 4)
    podium.prism(_poly_ring(PROFILE["podium_radius"] * 0.57, PROFILE["podium_radius"] * 0.46, 16, 0.0), 15.0, PROFILE["podium_height"], 3)
    meshes.append(podium.object(root.name + "__Podium", root, materials))

    # 2) Tower shaft: slightly tapered cylindrical polygon with floor bands and glazed panels.
    tower = MeshBuilder()
    tower.prism(_poly_ring(PROFILE["tower_radius"] * 1.035, PROFILE["tower_radius"] * 0.99, PROFILE["tower_sides"]), PROFILE["tower_start_z"], PROFILE["tower_top_z"], 0)
    floor_band = MeshBuilder()
    levels = int(round((PROFILE["tower_top_z"] - PROFILE["tower_start_z"]) / PROFILE["tower_floor_to_floor"]))
    for level in range(levels + 1):
        z = PROFILE["tower_start_z"] + level * PROFILE["tower_floor_to_floor"]
        if z <= PROFILE["tower_top_z"] + 1e-3:
            _ring_beams(floor_band, PROFILE["tower_radius"] * (1.035 - 0.035 * level / max(levels, 1)), z, PROFILE["tower_sides"], 0.12, 0.16, 1)
    meshes.append(tower.object(root.name + "__TowerGlassShell", root, materials))
    meshes.append(floor_band.object(root.name + "__TowerFloorBands", root, materials))

    # 3) Vertical fins: 36 narrow radial fins, the main recognition cue from distance.
    fin_mesh = MeshBuilder()
    for i in range(PROFILE["fin_count"]):
        angle = math.tau * i / PROFILE["fin_count"]
        r0 = PROFILE["tower_radius"] * 1.015
        r1 = r0 + PROFILE["fin_depth"]
        a = (r0 * math.cos(angle), r0 * math.sin(angle), PROFILE["tower_start_z"] - 0.5)
        b = (r1 * math.cos(angle), r1 * math.sin(angle), PROFILE["tower_top_z"] + 0.8)
        fin_mesh.beam(a, b, PROFILE["fin_width"], PROFILE["fin_width"], 2)
    meshes.append(fin_mesh.object(root.name + "__VerticalFins", root, materials))

    # 4) Crown: stepped cap, rooftop circular ring, and a restrained service core.
    crown = MeshBuilder()
    crown.prism(_poly_ring(PROFILE["crown_radius_bottom"], PROFILE["crown_radius_bottom"] * 0.98, 36), PROFILE["tower_top_z"], PROFILE["tower_top_z"] + 3.0, 5)
    crown.prism(_poly_ring(PROFILE["crown_radius_top"], PROFILE["crown_radius_top"] * 0.95, 36), PROFILE["tower_top_z"] + 3.0, PROFILE["tower_top_z"] + PROFILE["crown_height"], 5)
    _ring_beams(crown, PROFILE["crown_radius_top"] * 0.98, PROFILE["tower_top_z"] + PROFILE["crown_height"] - 0.4, 36, 0.22, 0.30, 2)
    crown.prism(_poly_ring(8.6, 7.2, 12, 0.0), PROFILE["tower_top_z"] + PROFILE["crown_height"], PROFILE["total_height"], 5)
    meshes.append(crown.object(root.name + "__SteppedCrown", root, materials))

    # 5) Rooftop ring/plant: a low circular parapet and warm inset disk, not a literal pool.
    roof = MeshBuilder()
    outer = _poly_ring(11.8, 10.0, 36)
    inner = _poly_ring(9.8, 8.2, 36)
    z = PROFILE["total_height"] - 0.35
    for i in range(36):
        j = (i + 1) % 36
        roof.face([(outer[i][0], outer[i][1], z), (outer[j][0], outer[j][1], z),
                   (inner[j][0], inner[j][1], z), (inner[i][0], inner[i][1], z)], 5)
    roof.prism(inner, z - 0.1, z + 0.08, 6)
    meshes.append(roof.object(root.name + "__RoofRing", root, materials))

    # 6) Small podium entrance fins/vertical mullions, enough to read at street scale.
    entry = MeshBuilder()
    for x in (-20.0, -16.0, -12.0, 12.0, 16.0, 20.0):
        entry.beam((x, -PROFILE["podium_radius"] * 0.52, 0.0), (x, -PROFILE["podium_radius"] * 0.52, 16.0), 0.22, 0.28, 2)
    meshes.append(entry.object(root.name + "__PodiumEntryFins", root, materials))

    root["source_record"] = json.dumps(record, ensure_ascii=False)
    root["object_count"] = len(meshes)
    root["estimated_vertices"] = sum(len(obj.data.vertices) for obj in meshes)
    bpy.context.view_layer.update()
    return {
        "name": TARGET_NAME,
        "root": root.name,
        "collection": collection_name,
        "objects": len(meshes),
        "vertices": root["estimated_vertices"],
        "height_m": PROFILE["total_height"],
        "record_source": record.get("input_fallback", "data/processed/bespoke_landmark_inputs.json"),
        "non_destructive": True,
    }


if __name__ == "__main__":
    print(build())
