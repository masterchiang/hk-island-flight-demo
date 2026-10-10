import bpy, json, math
from pathlib import Path
from mathutils import Vector
import numpy as np

# One Island East / Taikoo Place - independent batch-2 landmark module.
# Deliberately does not save the current .blend. Run in a disposable copy.
ROOT = Path(r'<PROJECT_ROOT>')
DATA = ROOT / 'data' / 'processed'
OSM_ID = 200915642
records = json.loads((DATA / 'hki_buildings.json').read_text(encoding='utf8'))['buildings']
B = next(b for b in records if int(b['id']) == OSM_ID)
terrain = np.load(DATA / 'terrain_hki.npz')
tx, ty, tz = terrain['x'], terrain['y'], terrain['z']

ring = [Vector((float(x), float(y), 0.0)) for x, y in B['footprint']]
center = Vector((sum(p.x for p in ring) / len(ring), sum(p.y for p in ring) / len(ring), 0.0))
arr = np.array([[p.x - center.x, p.y - center.y] for p in ring], dtype=float)
vals, vecs = np.linalg.eigh(np.cov(arr.T))
axis = vecs[:, np.argmax(vals)]
angle = math.atan2(float(axis[1]), float(axis[0]))
ca, sa = math.cos(angle), math.sin(angle)
local_ring = [Vector(((p.x-center.x)*ca + (p.y-center.y)*sa,
                      -(p.x-center.x)*sa + (p.y-center.y)*ca, 0.0)) for p in ring]
W = max(p.x for p in local_ring) - min(p.x for p in local_ring)
D = max(p.y for p in local_ring) - min(p.y for p in local_ring)
ix = int(np.clip(np.searchsorted(tx, center.x) - 1, 0, len(tx)-1))
iy = int(np.clip(np.searchsorted(ty, center.y) - 1, 0, len(ty)-1))
base = float(tz[iy, ix]) + 0.85
HEIGHT = float(B.get('height') or 298.35)

# Remove only this module's previous output in the currently open disposable scene.
prefix = f'CUSTOM_{OSM_ID}_One_Island_East'
_legacy_oie_collection=bpy.data.collections.get('09_Custom_Landmarks')
if _legacy_oie_collection:
    for o in list(_legacy_oie_collection.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)

# Reuse project materials where present; create restrained fallbacks otherwise.
def fallback(name, color, metallic=0.0, roughness=0.3, emission=(0,0,0), emission_strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes; l = m.node_tree.links; n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    bs = n.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = (*color, 1.0)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    if 'Emission Color' in bs.inputs:
        bs.inputs['Emission Color'].default_value = (*emission, 1.0)
        bs.inputs['Emission Strength'].default_value = emission_strength
    l.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return m

glass = bpy.data.materials.get('Custom_Landmark_Glass') or fallback('OIE_Glass', (0.025,0.12,0.18), 0.55, 0.18, (0.0,0.08,0.16), 0.25)
steel = bpy.data.materials.get('Custom_Landmark_Steel') or fallback('OIE_Steel', (0.10,0.18,0.22), 0.75, 0.22, (0.03,0.18,0.24), 0.18)
stone = bpy.data.materials.get('Custom_Landmark_Podium') or fallback('OIE_Podium', (0.16,0.20,0.21), 0.25, 0.38)
dark = bpy.data.materials.get('Custom_Landmark_Dark') or fallback('OIE_Dark', (0.008,0.018,0.025), 0.5, 0.23)
accent = bpy.data.materials.get('Custom_Landmark_Accent') or fallback('OIE_Accent', (0.35,0.46,0.48), 0.75, 0.2)

coll = bpy.data.collections.get('09_Custom_Landmarks') or bpy.data.collections.new('09_Custom_Landmarks')
if coll.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(coll)
root = bpy.data.objects.new(prefix, None)
coll.objects.link(root)
root.location = (center.x, center.y, base)
root.rotation_euler[2] = angle
root['osm_id'] = OSM_ID
root['name'] = 'One Island East'
root['profile'] = 'one_island_east_splayed_glass_v2'
root['height_m'] = HEIGHT
root['levels'] = float(B.get('levels') or 69)
root['gis_footprint_m'] = [round(W,2), round(D,2)]
root['terrain_base_m'] = round(base,2)
root['basis'] = 'Local OSM/GIS footprint + terrain_hki.npz + public architectural/photo references'
root['reference_notes'] = 'Tall rounded-rectangular blue-glass office tower with chamfered/splayed corners, podium/plaza transition, repeated horizontal floor bands, vertical corner fins, and a restrained crown.'

V, F, MI = [], [], []
def box(x0,x1,y0,y1,z0,z1,mi=0):
    s=len(V); V.extend([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
    F.extend([(s,s+1,s+2,s+3),(s+4,s+7,s+6,s+5),(s,s+4,s+5,s+1),(s+1,s+5,s+6,s+2),(s+2,s+6,s+7,s+3),(s+4,s,s+3,s+7)])
    MI.extend([mi]*6)
def prism(poly,z0,z1,mi=0):
    s=len(V); n=len(poly); V.extend([(p.x,p.y,z0) for p in poly] + [(p.x,p.y,z1) for p in poly])
    for i in range(n):
        j=(i+1)%n; F.append((s+i,s+j,s+n+j,s+n+i)); MI.append(mi)
    F.extend([tuple(s+i for i in reversed(range(n))), tuple(s+n+i for i in range(n))]); MI.extend([mi,mi])
def poly_rect(x0,x1,y0,y1,cut=0):
    return [Vector((x0+cut,y0,0)),Vector((x1-cut,y0,0)),Vector((x1,y0+cut,0)),Vector((x1,y1-cut,0)),Vector((x1-cut,y1,0)),Vector((x0+cut,y1,0)),Vector((x0,y1-cut,0)),Vector((x0,y0+cut,0))]
def cyl_part(name, verts, faces, mats, material_list, parent=root):
    me=bpy.data.meshes.new(name+'_Mesh'); me.from_pydata(verts, [], faces); me.update()
    ob=bpy.data.objects.new(name, me); coll.objects.link(ob); ob.parent=parent
    for m in material_list: me.materials.append(m)
    for i,p in enumerate(me.polygons): p.material_index=mats[i] if i < len(mats) else 0
    return ob

# 1) Base mass: public/podium transition and dark recessed tower plinth.
podium_h = 18.0
pod = prism(poly_rect(-W/2, W/2, -D/2, D/2, cut=7.0), 0, podium_h, 2)
# central glazed lobby / sky-terrace cut is represented by a darker inset volume
box(-W*0.34, W*0.34, -D*0.28, D*0.28, podium_h-0.4, podium_h+5.5, 3)
# podium setbacks provide the stepped street/plaza silhouette
box(-W*0.42, W*0.42, -D*0.42, D*0.42, podium_h, podium_h+6.0, 2)

# 2) Tower body: faceted 8-sided plan, tapering slightly and with rounded/splayed corners.
def tower_poly(z, sx, sy, cut):
    return poly_rect(-sx/2, sx/2, -sy/2, sy/2, cut)
body_z0, body_z1 = 24.0, HEIGHT-16.0
# Four tapered sections avoid a single monotonous box and preserve the crown rhythm.
sections = [(body_z0, 82.0, W*0.93, D*0.93, 6.0),
            (82.0, 150.0, W*0.98, D*0.98, 7.0),
            (150.0, 230.0, W*0.96, D*0.96, 8.0),
            (230.0, body_z1, W*0.91, D*0.91, 7.0)]
for z0,z1,sx,sy,cut in sections:
    prism(tower_poly(z0,sx,sy,cut), z0, z1, 0)
# dark top mechanical / crown cap
prism(tower_poly(body_z1, W*0.92, D*0.92, 7.0), body_z1, HEIGHT-4.0, 3)
prism(tower_poly(HEIGHT-4.0, W*0.62, D*0.62, 4.0), HEIGHT-4.0, HEIGHT, 1)

mesh=bpy.data.meshes.new('OIE_v2_Mass_Mesh'); mesh.from_pydata(V,[],F); mesh.update()
mass=bpy.data.objects.new('OIE_v2_Podium_and_Tower_Mass',mesh); coll.objects.link(mass); mass.parent=root
for m in [glass,steel,stone,dark,accent]: mesh.materials.append(m)
for i,p in enumerate(mesh.polygons): p.material_index=MI[i]
mass['detail']='GIS-shaped podium plus tapered faceted tower with crown abstraction'

# 3) Curtain-wall horizontal bands and vertical fins.
fac=bpy.data.curves.new('OIE_v2_Facade_Bands','CURVE'); fac.dimensions='3D'; fac.bevel_depth=0.11; fac.bevel_resolution=1; fac.resolution_u=1; fac.materials.append(steel)
def seg(a,b):
    sp=fac.splines.new('POLY'); sp.points.add(1); sp.points[0].co=(*a,1); sp.points[1].co=(*b,1)
# 69-storey rhythm: 4.25 m floor-to-floor; band thickness is visual abstraction.
for z in np.arange(24.0, body_z1+0.1, 4.25):
    sx = W*(0.93 if z<82 else 0.98 if z<150 else 0.96 if z<230 else 0.91)
    sy = D*(0.93 if z<82 else 0.98 if z<150 else 0.96 if z<230 else 0.91)
    for x0,x1,y in [(-sx/2+6,sx/2-6,-sy/2),(-sx/2+6,sx/2-6,sy/2)]: seg((x0,y,z),(x1,y,z))
    for y0,y1,x in [(-sy/2+6,sy/2-6,-sx/2),( -sy/2+6,sy/2-6,sx/2)]: seg((x,y0,z),(x,y1,z))
# corner/edge fins create the recognizable vertical striation and catch light.
for side in (-1,1):
    for xx in np.linspace(-W*0.36,W*0.36,9):
        seg((xx,side*D*0.47,24),(xx,side*D*0.47,body_z1))
    for yy in np.linspace(-D*0.36,D*0.36,9):
        seg((side*W*0.47,yy,24),(side*W*0.47,yy,body_z1))
frames=bpy.data.objects.new('OIE_v2_Horizontal_Bands_and_Vertical_Fins',fac); coll.objects.link(frames); frames.parent=root

# 4) Strong corner piers / splayed vertical blade accents.
bl=bpy.data.curves.new('OIE_v2_Corner_Blades','CURVE'); bl.dimensions='3D'; bl.bevel_depth=0.28; bl.bevel_resolution=1; bl.resolution_u=1; bl.materials.append(accent)
for sx in (-1,1):
    for sy in (-1,1):
        x=sx*(W*0.46); y=sy*(D*0.46)
        for off in (-2.2,2.2):
            sp=bl.splines.new('POLY'); sp.points.add(1); sp.points[0].co=(x+off*sy,y-off*sx,22,1); sp.points[1].co=(x+off*sy*0.72,y-off*sx*0.72,body_z1,1)
blades=bpy.data.objects.new('OIE_v2_Splayed_Corner_Blades',bl); coll.objects.link(blades); blades.parent=root

# 5) Entry canopy and podium plaza traces.
pl=bpy.data.curves.new('OIE_v2_Plaza_and_Entry','CURVE'); pl.dimensions='3D'; pl.bevel_depth=0.18; pl.bevel_resolution=1; pl.resolution_u=1; pl.materials.append(stone)
for x in np.linspace(-W*0.33,W*0.33,7):
    sp=pl.splines.new('POLY'); sp.points.add(1); sp.points[0].co=(float(x),-D*0.51,0.4,1); sp.points[1].co=(float(x),-D*0.18,0.4,1)
# canopy roof and vertical entry mullions
for x in (-W*0.24,-W*0.08,W*0.08,W*0.24):
    sp=pl.splines.new('POLY'); sp.points.add(1)
    sp.points[0].co=(float(x),-D*0.47,18.0,1); sp.points[1].co=(float(x),-D*0.47,27.0,1)
sp=pl.splines.new('POLY'); sp.points.add(3)
for pt,co in zip(sp.points,[(-W*0.30,-D*0.50,27.0),(W*0.30,-D*0.50,27.0),(W*0.30,-D*0.36,27.0),(-W*0.30,-D*0.36,27.0)]):
    pt.co=(*co,1)
canopy=bpy.data.objects.new('OIE_v2_Entry_Plaza_Traces',pl); coll.objects.link(canopy); canopy.parent=root

# Metadata for downstream review and independent handoff.
root['rendering_note']='One Island East profile: GIS footprint, blue-glass faceted tower, dense floor-band rhythm, vertical corner blades, podium/public-realm transition, restrained crown.'
root['precision_boundary']='Visual/procedural landmark model, not a fabrication or surveyed as-built model; facade mullion spacing, interior, signage and exact crown geometry are approximate.'
root['source_data']='OSM/GIS local record, terrain_hki.npz, official/architectural/photo references summarized in research/landmarks_20261001/one_island_east_b2.md'
print({'root':root.name,'osm_id':OSM_ID,'gis_footprint_m':[round(W,2),round(D,2)],'terrain_base_m':round(base,2),'height_m':HEIGHT,'levels':root['levels'],'objects':[o.name for o in root.children]})
