"""The Center (Hong Kong) — Batch 2 bespoke modeling module.

Run inside Blender's Python console or with Blender's --python option.
This module is intentionally standalone: it only creates/replaces objects in
its own collection and does not save or modify the shared/main .blend file.

Evidence hierarchy:
- OSM/GIS footprint + local DTM from this project for placement and ground datum.
- Public building facts for the 346 m / 73-level tower datum.
- Photo/streetscape interpretation for the recognizable tapered 16-sided mass,
  dark faceted curtainwall, vertical LED/light bands, and stepped crown/roof core.

The geometry is a reproducible architectural massing reconstruction, not a
surveyed facade or an authorized photogrammetric copy.
"""
import bpy
import json
import math
import re
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(r"<PROJECT_ROOT>")
DATA = ROOT / "data" / "processed"
REVISION = "2026-10-01-B2-the-center"
COLLECTION_NAME = "13_Bespoke_The_Center_B2"
OSM_ID = 296457776
BUILDING_NAME = "The Center"

# ---------- data / GIS ----------
records = json.loads((DATA / "hki_buildings.json").read_text(encoding="utf8"))["buildings"]
record = next(b for b in records if int(b["id"]) == OSM_ID)
raw_ring = [Vector((float(x), float(y), 0.0)) for x, y in record["footprint"]]
centroid = Vector((sum(p.x for p in raw_ring) / len(raw_ring),
                   sum(p.y for p in raw_ring) / len(raw_ring), 0.0))
arr = np.array([[p.x - centroid.x, p.y - centroid.y] for p in raw_ring], dtype=float)
cov = np.cov(arr.T)
vals, vecs = np.linalg.eigh(cov)
axis = vecs[:, np.argmax(vals)]
angle = math.atan2(float(axis[1]), float(axis[0]))
ca, sa = math.cos(angle), math.sin(angle)

def to_local(p):
    dx, dy = p.x - centroid.x, p.y - centroid.y
    return Vector((dx * ca + dy * sa, -dx * sa + dy * ca, 0.0))

ring = [to_local(p) for p in raw_ring]
# Preserve the OSM 16-sided outline as the authoritative ground plan.
W = max(p.x for p in ring) - min(p.x for p in ring)
D = max(p.y for p in ring) - min(p.y for p in ring)
area_m2 = abs(sum(ring[i].x * ring[(i + 1) % len(ring)].y -
                  ring[(i + 1) % len(ring)].x * ring[i].y
                  for i in range(len(ring))) * 0.5)

terrain = np.load(DATA / "terrain_hki.npz")
tx, ty, tz = terrain["x"], terrain["y"], terrain["z"]
ix = int(np.clip(np.searchsorted(tx, centroid.x) - 1, 0, len(tx) - 1))
iy = int(np.clip(np.searchsorted(ty, centroid.y) - 1, 0, len(ty) - 1))
base_z = float(tz[iy, ix]) + 0.85
TOTAL_HEIGHT = 346.0
PUBLISHED_LEVELS = 73

# ---------- utilities ----------
def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

coll = collection(COLLECTION_NAME)
# Remove only this agent's previous result. No shared/main objects are touched.
for obj in list(coll.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


def material(name, color, metallic=0.0, roughness=0.4, emission=None, emission_strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        m.node_tree.nodes.clear()
        out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if bsdf.inputs.get("Emission Color") is not None:
        bsdf.inputs["Emission Color"].default_value = (*((emission or color)), 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    m.diffuse_color = (*color, 1.0)
    return m

mat_glass = material("B2_Center_DarkBlueGlass", (0.025, 0.075, 0.115), 0.55, 0.20)
mat_glass_alt = material("B2_Center_BlueGlassAlt", (0.055, 0.16, 0.23), 0.50, 0.23)
mat_spandrel = material("B2_Center_Spandrel", (0.075, 0.105, 0.12), 0.65, 0.31)
mat_steel = material("B2_Center_Steel", (0.15, 0.19, 0.21), 0.78, 0.28)
mat_crown = material("B2_Center_CrownSteel", (0.21, 0.25, 0.27), 0.72, 0.30)
mat_roof = material("B2_Center_RoofCore", (0.055, 0.07, 0.075), 0.45, 0.38)
mat_led = material("B2_Center_LED_RedBlue", (0.12, 0.20, 0.24), 0.35, 0.20,
                  emission=(0.08, 0.22, 0.40), emission_strength=1.2)
mat_plinth = material("B2_Center_Podium", (0.10, 0.12, 0.13), 0.45, 0.38)
materials = [mat_glass, mat_glass_alt, mat_spandrel, mat_steel, mat_crown,
             mat_roof, mat_led, mat_plinth]

# ---------- mesh helpers ----------
class MeshBuilder:
    def __init__(self):
        self.v, self.f, self.mi = [], [], []
    def face(self, points, mi=0):
        s = len(self.v)
        self.v.extend([tuple(p) for p in points])
        self.f.append(tuple(range(s, s + len(points))))
        self.mi.append(mi)
    def prism(self, bottom, top, z0, z1, mi=0):
        b = [Vector((p.x, p.y, z0)) for p in bottom]
        t = [Vector((p.x, p.y, z1)) for p in top]
        self.face(list(reversed(b)), mi)
        self.face(t, mi)
        for i in range(len(b)):
            j = (i + 1) % len(b)
            self.face([b[i], b[j], t[j], t[i]], mi)
    def object(self, name, parent):
        me = bpy.data.meshes.new(name + "_Mesh")
        me.from_pydata(self.v, [], self.f)
        me.update()
        for m in materials:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.mi):
            poly.material_index = mi
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        obj.parent = parent
        obj["revision"] = REVISION
        return obj


def scale_ring(points, scale):
    return [Vector((p.x * scale, p.y * scale, 0.0)) for p in points]


def ring_for_fraction(frac):
    """Vertical profile: near-full base, gently tapered shaft, stepped crown."""
    if frac < 0.08:
        t = frac / 0.08
        s = 1.0 - 0.035 * t
    elif frac < 0.86:
        t = (frac - 0.08) / 0.78
        s = 0.965 - 0.115 * t
    elif frac < 0.925:
        t = (frac - 0.86) / 0.065
        s = 0.85 - 0.11 * t
    elif frac < 0.975:
        t = (frac - 0.925) / 0.05
        s = 0.74 - 0.14 * t
    else:
        s = 0.60
    return scale_ring(ring, s)

# ---------- root / massing ----------
root = bpy.data.objects.new("CUSTOM_%d_The_Center_B2" % OSM_ID, None)
coll.objects.link(root)
root.location = (centroid.x, centroid.y, base_z)
root.rotation_euler[2] = angle
root["osm_id"] = str(OSM_ID)
root["name"] = BUILDING_NAME
root["profile"] = "16-sided tapered curtainwall tower with stepped crown and roof core"
root["height_m"] = TOTAL_HEIGHT
root["published_levels"] = PUBLISHED_LEVELS
root["gis_footprint_m"] = [round(W, 3), round(D, 3)]
root["gis_area_m2"] = round(area_m2, 2)
root["base_elevation_m"] = round(base_z, 3)
root["basis"] = "OSM 16-sided footprint + project DTM + public height/floor facts + photo-interpreted crown/LED bands"
root["limitations"] = "Facade bay count, roof equipment and exact crown framing are interpretive, not surveyed."

mass = MeshBuilder()
# 5-metre podium/plinth, matching footprint; no oversized generic box.
mass.prism(ring, ring_for_fraction(0.015), 0.0, 5.0, 7)
# Main tapered shaft as 8 stacked frusta; stacked sections make the changing taper explicit.
sections = [0.015, 0.10, 0.22, 0.34, 0.46, 0.58, 0.70, 0.82, 0.86,
            0.925, 0.975, 1.0]
for a, b in zip(sections[:-1], sections[1:]):
    mass.prism(ring_for_fraction(a), ring_for_fraction(b), TOTAL_HEIGHT * a,
               TOTAL_HEIGHT * b, 0 if a < 0.86 else (3 if a < 0.925 else 4))
mass_obj = mass.object("The_Center_B2_Massing", root)
mass_obj["detail"] = "16-sided GIS plan; tapered shaft; stepped crown fractions 0.86/0.925/0.975"

# A small roof service core, intentionally separated from the outer crown.
core = MeshBuilder()
core.prism(scale_ring(ring, 0.20), scale_ring(ring, 0.13), TOTAL_HEIGHT * 0.975,
           TOTAL_HEIGHT * 1.0, 5)
core_obj = core.object("The_Center_B2_Roof_Core", root)

# ---------- facade grid ----------
def curve_object(name, bevel, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 0
    cu.resolution_u = 1
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    ob.parent = root
    return cu, ob

def segment(cu, a, b):
    sp = cu.splines.new("POLY")
    sp.points.add(1)
    sp.points[0].co = (*a, 1.0)
    sp.points[1].co = (*b, 1.0)

# Horizontal floor/slab lines at the 73-level datum, with a restrained service interval.
grid_cu, grid_obj = curve_object("The_Center_B2_Facade_Grid", 0.035, mat_steel)
for level in range(PUBLISHED_LEVELS + 1):
    z = TOTAL_HEIGHT * level / PUBLISHED_LEVELS
    r = ring_for_fraction(level / PUBLISHED_LEVELS)
    for i, a in enumerate(r):
        b = r[(i + 1) % len(r)]
        segment(grid_cu, (a.x, a.y, z), (b.x, b.y, z))
# Vertical mullions on every second facade bay; interpolate along each tapered edge.
for i in range(len(ring)):
    a0, b0 = ring_for_fraction(0.04)[i], ring_for_fraction(0.04)[(i + 1) % len(ring)]
    for bay in range(1, 4):
        t = bay / 4.0
        u = Vector((a0.x * (1 - t) + b0.x * t, a0.y * (1 - t) + b0.y * t, 0))
        # Individual straight mullion is a visual approximation on the tapered facade.
        segment(grid_cu, (u.x, u.y, TOTAL_HEIGHT * 0.04),
                (u.x * 0.84, u.y * 0.84, TOTAL_HEIGHT * 0.86))

# Distinctive luminous vertical strips: sparse, full-height, concentrated on alternating corners.
led_cu, led_obj = curve_object("The_Center_B2_Architectural_LED_Bands", 0.16, mat_led)
for i in range(0, len(ring), 2):
    p = ring_for_fraction(0.06)[i]
    q = ring_for_fraction(0.86)[i]
    segment(led_cu, (p.x, p.y, TOTAL_HEIGHT * 0.06),
            (q.x, q.y, TOTAL_HEIGHT * 0.86))
# Four crown ribs emphasize the stepped/triangular roof silhouette.
crown_cu, crown_obj = curve_object("The_Center_B2_Crown_Ribs", 0.11, mat_crown)
for i in range(0, len(ring), 4):
    p = ring_for_fraction(0.86)[i]
    q = ring_for_fraction(0.925)[i]
    r = ring_for_fraction(0.975)[i]
    segment(crown_cu, (p.x, p.y, TOTAL_HEIGHT * 0.86), (q.x, q.y, TOTAL_HEIGHT * 0.925))
    segment(crown_cu, (q.x, q.y, TOTAL_HEIGHT * 0.925), (r.x, r.y, TOTAL_HEIGHT * 0.975))

# Lower-level lobby / podium reading: a dark glazed collar and recessed entrance markers.
lobby = MeshBuilder()
lobby_ring = ring_for_fraction(0.015)
lobby.prism(scale_ring(lobby_ring, 0.985), scale_ring(lobby_ring, 0.985), 5.0, 13.5, 1)
lobby_obj = lobby.object("The_Center_B2_Lobby_Collar", root)
entrance_cu, entrance_obj = curve_object("The_Center_B2_Entrance_Traces", 0.07, mat_led)
for i in range(0, len(ring), 4):
    p = ring_for_fraction(0.04)[i]
    segment(entrance_cu, (p.x * 0.94, p.y * 0.94, 5.0),
            (p.x * 0.94, p.y * 0.94, 13.5))

# ---------- validation metadata ----------
root["validation"] = json.dumps({
    "footprint_vertices": len(ring),
    "footprint_area_m2": round(area_m2, 2),
    "footprint_bbox_m": [round(W, 3), round(D, 3)],
    "height_m": TOTAL_HEIGHT,
    "levels": PUBLISHED_LEVELS,
    "top_profile": "86% shaft -> 92.5% shoulder -> 97.5% crown -> 100% roof core",
}, ensure_ascii=False)
root["reference_checklist"] = "OSM footprint; DTM base; 346m height; 73 levels; 16-sided taper; dark faceted facade; vertical LED bands; stepped crown"

# Deliberately no save_as_mainfile here. The host decides whether/where to save.
print({
    "root": root.name,
    "collection": COLLECTION_NAME,
    "osm_id": OSM_ID,
    "footprint_m": [round(W, 3), round(D, 3)],
    "area_m2": round(area_m2, 2),
    "base_z": round(base_z, 3),
    "height_m": TOTAL_HEIGHT,
    "levels": PUBLISHED_LEVELS,
    "objects": [o.name for o in coll.objects],
})