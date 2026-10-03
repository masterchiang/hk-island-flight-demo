import bpy, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(r'<PROJECT_ROOT>')
DATA = ROOT / 'data/processed'
B_ID = 52869536
COLL_NAME = 'CUSTOM_52869536_HENDERSON_B2'
ROOT_NAME = 'CUSTOM_52869536_The_Henderson_B2'


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
        p.inputs['Emission Strength'].default_value = 0.25
    l.new(p.outputs['BSDF'], out.inputs['Surface'])
    return m


def _mesh(name, verts, faces, mat=None, parent=None):
    me = bpy.data.meshes.new(name + '_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat: me.materials.append(mat)
    if parent: o.parent = parent
    return o


def _ring(name, poly, z0, z1, mat, parent=None, cap=True):
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [(i, (i+1)%n, n+(i+1)%n, n+i) for i in range(n)]
    if cap:
        faces += [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    return _mesh(name, verts, faces, mat, parent)


def _curve(name, points, bevel, mat, parent=None, cyclic=False):
    cu = bpy.data.curves.new(name + '_Curve', 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = bevel; cu.bevel_resolution = 2; cu.resolution_u = 2
    sp = cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points): p.co = (*co, 1.0)
    sp.use_cyclic_u = cyclic
    cu.materials.append(mat)
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    if parent: o.parent = parent
    return o


def _ellipse_poly(rx, ry, count=48, skew=0.0, nose=0.0):
    pts=[]
    for i in range(count):
        a=2*math.pi*i/count
        x=rx*math.cos(a)
        y=ry*math.sin(a)
        # Slightly pointed / ship-like ends and asymmetric ZHA envelope.
        x += nose * math.copysign(abs(math.cos(a))**2.2, math.cos(a))
        y += skew * math.sin(2*a) * 0.10
        pts.append((x,y))
    return pts


def build_henderson_b2():
    """Standalone The Henderson hero model; only touches its own collection."""
    recs = json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
    b = next(x for x in recs if int(x['id']) == B_ID)
    pts = [(float(x), float(y)) for x,y in b['footprint']]
    cx = sum(x for x,y in pts)/len(pts); cy = sum(y for x,y in pts)/len(pts)
    # GIS bounds establish placement and scale; visual envelope is a smooth oval/ship plan.
    minx,maxx=min(x for x,y in pts),max(x for x,y in pts)
    miny,maxy=min(y for x,y in pts),max(y for x,y in pts)
    W,D=maxx-minx,maxy-miny
    ang = math.atan2(0.5*(maxy-miny), 0.5*(maxx-minx)) * 0.0
    old=bpy.data.collections.get(COLL_NAME)
    if old: bpy.data.collections.remove(old, do_unlink=True)
    coll=bpy.data.collections.new(COLL_NAME); bpy.context.scene.collection.children.link(coll)
    root=bpy.data.objects.new(ROOT_NAME,None); coll.objects.link(root)
    root.location=(cx,cy,0); root.rotation_euler[2]=ang
    root['osm_id']=B_ID; root['name']='The Henderson'; root['profile']='zha_continuous_glass_elliptical_taper_b2'
    root['height_m_osm']=float(b.get('height') or 190.0); root['levels_osm']=float(b.get('levels') or 36.0)
    root['gis_footprint_bbox_m']=[round(W,2),round(D,2)]
    root['sources']='OSM/Geofabrik project extract; Zaha Hadid Architects project material; Henderson Land developer material; reliable architectural photography and street-view references'
    root['precision_boundary']='GIS-placed procedural hero model. Continuous glass curvature, crown geometry and facade spacing are visual approximations, not an as-built survey or photogrammetry.'

    glass=_mat('HENDERSON_B2_Glass',(0.025,0.12,0.17),0.68,0.16,(0.01,0.08,0.12))
    glass_hi=_mat('HENDERSON_B2_Glass_High',(0.08,0.30,0.36),0.58,0.13,(0.02,0.18,0.20))
    frame=_mat('HENDERSON_B2_Frame',(0.07,0.12,0.14),0.82,0.20)
    crown=_mat('HENDERSON_B2_Crown',(0.16,0.34,0.36),0.70,0.17,(0.03,0.18,0.18))
    podium=_mat('HENDERSON_B2_Podium',(0.035,0.07,0.075),0.40,0.28)
    dark=_mat('HENDERSON_B2_Dark',(0.004,0.012,0.016),0.30,0.24)

    # Local dimensions preserve the OSM aspect while producing the recognizable compact ship/oval mass.
    base_z=0.0; h=float(b.get('height') or 190.0)
    rx=max(16.0, min(W,D)*0.43); ry=max(13.0, min(W,D)*0.34)
    # Low public podium, softly elliptical.
    _ring('Henderson_B2_Podium', _ellipse_poly(rx*1.18,ry*1.12,64,skew=0.4,nose=3.5), base_z, 9.5, podium, root)
    _ring('Henderson_B2_Lobby_Glass', _ellipse_poly(rx*1.05,ry*1.02,64,skew=0.5,nose=3.0), 9.5, 21.0, glass_hi, root)

    # Continuous curved tower envelope: stacked rings taper, rotate and subtly bow to a pinched crown.
    layers=26
    for i in range(layers):
        z0=20.0 + i*(h-30.0)/layers
        z1=20.0 + (i+1)*(h-30.0)/layers
        t=(i+0.5)/layers
        taper=1.0 - 0.18*t + 0.045*math.sin(math.pi*t)
        twist=math.radians(4.0)*math.sin(math.pi*t)
        poly=_ellipse_poly(rx*taper, ry*(1.0-0.11*t), 64, skew=0.7*(1-t), nose=4.0*(1-t))
        c,s=math.cos(twist),math.sin(twist)
        poly=[(x*c-y*s,x*s+y*c) for x,y in poly]
        _ring('Henderson_B2_Curved_Glass_%02d'%i, poly, z0, z1, glass if i%3 else glass_hi, root)

    # Crown: compressed, lifted glass petals/elliptical cap with a narrow mechanical crown.
    _ring('Henderson_B2_Crown_Transition', _ellipse_poly(rx*0.82,ry*0.77,64,nose=2.0), h-15.0, h-5.0, crown, root)
    _ring('Henderson_B2_Crown_Cap', _ellipse_poly(rx*0.62,ry*0.55,56,nose=1.2), h-5.0, h, dark, root)

    # Vertical mullion/rib lines follow the curved envelope, emphasizing continuous glass.
    rib_pts=[]
    for i in range(24):
        a=2*math.pi*i/24
        line=[]
        for j in range(20):
            t=j/19; z=20.0+t*(h-30.0)
            taper=1.0-0.18*t+0.045*math.sin(math.pi*t)
            x=rx*taper*math.cos(a); y=ry*(1-0.11*t)*math.sin(a)
            line.append((x,y,z))
        rib_pts.extend(line)
        _curve('Henderson_B2_Mullion_%02d'%i, line, 0.075, frame, root)

    # Horizontal floor bands and crown ring accents.
    for level in range(1,37):
        z=20.0 + (h-30.0)*level/38.0
        t=(z-20.0)/(h-30.0); taper=1.0-0.18*t+0.045*math.sin(math.pi*t)
        poly=_ellipse_poly(rx*taper*1.006,ry*(1-0.11*t)*1.006,64,nose=4*(1-t))
        _curve('Henderson_B2_FloorBand_%02d'%level, [(x,y,z) for x,y in poly], 0.045, frame, root, cyclic=True)
    for z in (h-15.0,h-9.0,h-4.5):
        poly=_ellipse_poly(rx*(0.84 if z<h-10 else 0.68),ry*(0.78 if z<h-10 else 0.60),64)
        _curve('Henderson_B2_CrownBand_%s'%str(round(z,1)).replace('.','_'), [(x,y,z) for x,y in poly], 0.10, crown, root, cyclic=True)

    # Softly curved vertical crown fins suggest the architectural crown's folded silhouette.
    for i in range(10):
        a=-math.pi*0.75 + i*(math.pi*1.5/9)
        pts=[]
        for j in range(10):
            t=j/9; z=h-18+t*18
            r=1.01*(rx*(0.82-0.20*t)); q=ry*(0.77-0.18*t)
            pts.append((r*math.cos(a),q*math.sin(a),z))
        _curve('Henderson_B2_Crown_Fin_%02d'%i,pts,0.16,crown,root)

    # Entry / public-realm canopy indication.
    _ring('Henderson_B2_Entry_Canopy', _ellipse_poly(rx*0.70,ry*0.60,48,nose=1.5), 9.5, 11.0, frame, root)
    return root


if __name__ == '__main__':
    build_henderson_b2()
