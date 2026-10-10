import bpy, json, math
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(r'<PROJECT_ROOT>')
DATA = ROOT / 'data/processed'
B_ID = 297109890


def _mat(name, color, metallic=0.0, roughness=0.3, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes; n.clear(); l = m.node_tree.links
    out = n.new('ShaderNodeOutputMaterial')
    p = n.new('ShaderNodeBsdfPrincipled')
    p.inputs['Base Color'].default_value = (*color, 1.0)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1.0)
        p.inputs['Emission Strength'].default_value = 0.35
    l.new(p.outputs['BSDF'], out.inputs['Surface'])
    return m


def _cube(name, dims, loc, mat, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name; o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat: o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Soft architectural edges', 'BEVEL'); mod.width = bevel; mod.segments = 2
    if parent: o.parent = parent
    return o


def _mesh(name, verts, faces, mat, parent=None):
    me = bpy.data.meshes.new(name + '_Mesh'); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat: me.materials.append(mat)
    if parent: o.parent = parent
    return o


def _ring_mesh(name, poly, z0, z1, mat, parent=None):
    n = len(poly); verts = [(x,y,z0) for x,y in poly] + [(x,y,z1) for x,y in poly]
    faces = []
    for i in range(n):
        j=(i+1)%n; faces.append((i,j,n+j,n+i))
    faces += [tuple(reversed(range(n))), tuple(range(n,2*n))]
    return _mesh(name, verts, faces, mat, parent)


def _local_frame(points):
    c = Vector((sum(p[0] for p in points)/len(points), sum(p[1] for p in points)/len(points), 0))
    arr=np.array([[p[0]-c.x,p[1]-c.y] for p in points], dtype=float)
    cov=np.cov(arr.T); vals,vecs=np.linalg.eigh(cov); axis=vecs[:,np.argmax(vals)]
    ang=math.atan2(float(axis[1]), float(axis[0]))
    ca,sa=math.cos(ang),math.sin(ang)
    local=[((p[0]-c.x)*ca+(p[1]-c.y)*sa, -(p[0]-c.x)*sa+(p[1]-c.y)*ca) for p in points]
    return c, ang, local


def build_ifc1_b2():
    '''Build a standalone One International Finance Centre procedural hero model.

    Returns the created root object. Run in a disposable Blender file; this function
    only touches objects in its own CUSTOM_297109890_IFC1_B2 collection.
    '''
    recs=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
    b=next(x for x in recs if int(x['id'])==B_ID)
    pts=[(float(x),float(y)) for x,y in b['footprint']]
    c,ang,poly=_local_frame(pts)
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    W=max(xs)-min(xs); D=max(ys)-min(ys)
    # OSM ring includes service/entrance articulation. Use its bounding size for GIS metadata
    # and a compact nine-sided envelope for the primary tower mass.
    tower_w=min(W,D)*0.80; tower_d=min(W,D)*0.80
    height=float(b.get('height') or 210.0)
    levels=float(b.get('levels') or 38.0)

    old=bpy.data.collections.get('CUSTOM_297109890_IFC1_B2')
    if old:
        bpy.data.collections.remove(old, do_unlink=True)
    coll=bpy.data.collections.new('CUSTOM_297109890_IFC1_B2'); bpy.context.scene.collection.children.link(coll)
    root=bpy.data.objects.new('CUSTOM_297109890_IFC1_One_International_Finance_Centre', None); coll.objects.link(root)
    root.location=(c.x,c.y,0); root.rotation_euler[2]=ang
    root['osm_id']=B_ID; root['name']='One International Finance Centre'; root['profile']='ifc1_tapered_diagrid_b2'
    root['height_m_osm']=height; root['levels_osm']=levels; root['gis_footprint_bbox_m']=[round(W,2),round(D,2)]
    root['sources']='OSM/Geofabrik project extract; IFC official / official developer material; street-view/image references'
    root['precision_boundary']='GIS-calibrated procedural hero model; facade rhythm and crown are visual approximations, not as-built survey or photogrammetry.'

    glass=_mat('IFC1_B2_Glass',(0.018,0.11,0.16),0.65,0.18,(0.0,0.10,0.16))
    glass2=_mat('IFC1_B2_Glass_Light',(0.04,0.23,0.28),0.55,0.20,(0.0,0.18,0.20))
    steel=_mat('IFC1_B2_Steel',(0.06,0.13,0.15),0.8,0.22)
    dark=_mat('IFC1_B2_Dark',(0.008,0.018,0.022),0.35,0.28)
    podium=_mat('IFC1_B2_Podium',(0.025,0.055,0.065),0.55,0.3)
    accent=_mat('IFC1_B2_Accent',(0.1,0.38,0.42),0.65,0.18,(0.02,0.3,0.32))

    # Low podium/plaza read: the tower rises from a compact waterfront podium.
    _cube('IFC1_B2_Podium', (tower_w*1.32,tower_d*1.18,13.0), (0,0,6.5), podium, 1.2, root)
    _cube('IFC1_B2_Podium_Glass_Lobby', (tower_w*0.82,tower_d*0.72,16.0), (0,0,11.0), glass2, 0.8, root)

    # Main tapered shaft: four corner chamfer planes create the characteristic faceted silhouette.
    z0=14.0; z1=198.0
    def octagon(w,d,ch):
        return [(-w/2+ch,-d/2), (w/2-ch,-d/2), (w/2,-d/2+ch), (w/2,d/2-ch),
                (w/2-ch,d/2), (-w/2+ch,d/2), (-w/2,d/2-ch), (-w/2,-d/2+ch)]
    lower=octagon(tower_w,tower_d,min(tower_w,tower_d)*0.14)
    upper=octagon(tower_w*0.86,tower_d*0.86,min(tower_w,tower_d)*0.12)
    verts=[(x,y,z0) for x,y in lower]+[(x,y,z1) for x,y in upper]
    faces=[]
    for i in range(8):
        j=(i+1)%8; faces.append((i,j,8+j,8+i))
    faces += [tuple(reversed(range(8))),tuple(range(8,16))]
    shaft=_mesh('IFC1_B2_Tapered_Glass_Shaft',verts,faces,glass,root)
    shaft['height_m']=z1-z0; shaft['footprint_envelope_m']=[tower_w,tower_d]

    # Setback/crown cap and mechanical crown, deliberately separate for refinement.
    _ring_mesh('IFC1_B2_Crown_Setback', octagon(tower_w*0.72,tower_d*0.72,min(tower_w,tower_d)*0.10), 198, 207, glass2, root)
    _ring_mesh('IFC1_B2_Crown_Roof', octagon(tower_w*0.60,tower_d*0.60,min(tower_w,tower_d)*0.08), 207, 210, steel, root)

    # Horizontal floor bands and vertical mullions, kept as low-poly strips for performance.
    for i in range(1, int(levels)+1):
        z=14.0 + (198.0-14.0)*i/(levels+1)
        w=tower_w*(1.0-0.14*i/(levels+1)); d=tower_d*(1.0-0.14*i/(levels+1))
        _cube(f'IFC1_B2_FloorBand_{i:02d}', (w+0.5,d+0.5,0.34), (0,0,z), steel, 0.08, root)
    mullion_count=10
    for i in range(-mullion_count,mullion_count+1):
        x=i*tower_w/(2*mullion_count)
        _cube(f'IFC1_B2_Mullion_F_{i:+03d}', (0.16,0.11,184), (x,-tower_d*0.505,106), accent, 0.02, root)
        _cube(f'IFC1_B2_Mullion_B_{i:+03d}', (0.16,0.11,184), (x,tower_d*0.505,106), accent, 0.02, root)
    for i in range(-mullion_count,mullion_count+1):
        y=i*tower_d/(2*mullion_count)
        _cube(f'IFC1_B2_Mullion_L_{i:+03d}', (0.11,0.16,184), (-tower_w*0.505,y,106), accent, 0.02, root)
        _cube(f'IFC1_B2_Mullion_R_{i:+03d}', (0.11,0.16,184), (tower_w*0.505,y,106), accent, 0.02, root)

    # Recessed roof crown fins and a small antenna/plant enclosure abstraction.
    for x in (-tower_w*0.27, tower_w*0.27):
        _cube('IFC1_B2_Crown_Fin', (0.55,tower_d*0.72,8.0), (x,0,204), steel, 0.08, root)
    _cube('IFC1_B2_Roof_Equipment', (tower_w*0.30,tower_d*0.24,2.4), (0,0,208.8), dark, 0.18, root)

    # Metadata on every generated object helps independent assembly/validation.
    for o in list(coll.objects):
        o['landmark']='One International Finance Centre'; o['osm_id']=B_ID; o['agent_batch']='second_batch'; o['source_script']='scripts/agent_ifc1_b2.py'
    return root


if __name__ == '__main__':
    build_ifc1_b2()

