import bpy, json, math, re
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(r'<PROJECT_ROOT>')
DATA=ROOT/'data/processed'
records=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
terrain=np.load(DATA/'terrain_hki.npz'); tx=terrain['x'];ty=terrain['y'];tz=terrain['z']
B=next(b for b in records if b['id']==590814694)
ring=[Vector((float(x),float(y),0)) for x,y in B['footprint']]
c=Vector((sum(p.x for p in ring)/len(ring),sum(p.y for p in ring)/len(ring),0))
arr=np.array([[p.x-c.x,p.y-c.y] for p in ring],dtype=float);cov=np.cov(arr.T);vals,vecs=np.linalg.eigh(cov);axis=vecs[:,np.argmax(vals)];ang=math.atan2(float(axis[1]),float(axis[0]))
uv=[Vector(((p-c).x*math.cos(ang)+(p-c).y*math.sin(ang),-(p-c).x*math.sin(ang)+(p-c).y*math.cos(ang),0)) for p in ring]
W=max(p.x for p in uv)-min(p.x for p in uv);D=max(p.y for p in uv)-min(p.y for p in uv)
base=float(tz[int(np.clip(np.searchsorted(ty,c.y)-1,0,len(ty)-1)),int(np.clip(np.searchsorted(tx,c.x)-1,0,len(tx)-1))])+0.85

# Remove old HSBC custom root and descendants.
for o in list(bpy.data.objects):
    if o.name.startswith('CUSTOM_590814694_HSBC_Main_Building'):
        bpy.data.objects.remove(o,do_unlink=True)
# Keep old generic/independent model hidden. It is not the high-detail HSBC.
for o in bpy.context.scene.objects:
    if str(o.get('osm_id',''))=='590814694' and o.name.startswith('IND_'):
        o.hide_viewport=True;o.hide_render=True

# materials
mat_glass=bpy.data.materials.get('Custom_Landmark_Glass')
mat_steel=bpy.data.materials.get('Custom_Landmark_Steel')
mat_podium=bpy.data.materials.get('Custom_Landmark_Podium')
mat_accent=bpy.data.materials.get('Custom_Landmark_Accent')
mat_dark=bpy.data.materials.get('Custom_Landmark_Dark')

def mat_fallback(name,col,emit):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();o=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=.6;p.inputs['Roughness'].default_value=.25;p.inputs['Emission Color'].default_value=(*emit,1);p.inputs['Emission Strength'].default_value=.5;l.new(p.outputs['BSDF'],o.inputs['Surface']);return m
mat_glass=mat_glass or mat_fallback('HSBC_Glass',(0.008,.06,.12),(0,.18,.35));mat_steel=mat_steel or mat_fallback('HSBC_Steel',(.04,.12,.16),(0,.35,.6));mat_podium=mat_podium or mat_fallback('HSBC_Podium',(.01,.04,.06),(0,.1,.2));mat_accent=mat_accent or mat_fallback('HSBC_Accent',(0.02,.28,.45),(0,.6,1));mat_dark=mat_dark or mat_fallback('HSBC_Dark',(.001,.006,.012),(0,.03,.06))

coll=bpy.data.collections.get('09_Custom_Landmarks') or bpy.data.collections.new('09_Custom_Landmarks')
if coll.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(coll)
root=bpy.data.objects.new('CUSTOM_590814694_HSBC_Main_Building',None);coll.objects.link(root);root.location=(c.x,c.y,base);root.rotation_euler[2]=ang
root['osm_id']='590814694';root['name']='HSBC Main Building';root['profile']='hsbc_suspension_modular_v2';root['height_m']=float(B['height']);root['gis_footprint_m']=[round(W,2),round(D,2)];root['basis']='OSM footprint + 5m DTM + structural references';root['reference_notes']='Eight masts, five double-storey truss levels, open public plaza and atrium-inspired central void.'

V=[];F=[];MI=[]
def box(x0,x1,y0,y1,z0,z1,mi=0):
    s=len(V);V.extend([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
    F.extend([(s,s+1,s+2,s+3),(s+4,s+7,s+6,s+5),(s,s+4,s+5,s+1),(s+1,s+5,s+6,s+2),(s+2,s+6,s+7,s+3),(s+4,s,s+3,s+7)]);MI.extend([mi]*6)
def prism(poly,z0,z1,mi=0):
    s=len(V);V.extend([(p.x,p.y,z0) for p in poly]+[(p.x,p.y,z1) for p in poly]);n=len(poly)
    for i in range(n):j=(i+1)%n;F.append((s+i,s+j,s+n+j,s+n+i));MI.append(mi)
    F.extend([tuple(s+i for i in reversed(range(n))),tuple(s+n+i for i in range(n))]);MI.extend([mi,mi])

def local_ring(sx,sy):return [Vector((-sx/2,-sy/2,0)),Vector((sx/2,-sy/2,0)),Vector((sx/2,sy/2,0)),Vector((-sx/2,sy/2,0))]
# Local dimensions based on actual GIS footprint (approximately 67 x 58m).
# The ground floor is open; a thin banking-hall/plaza plinth frames the site.
plinth_z=16.0; podium_depth=7.0; atrium_depth=22.0
box(-W/2,W/2,-D/2,-D/2+podium_depth,0,plinth_z,2);box(-W/2,W/2,D/2-podium_depth,D/2,0,plinth_z,2)
box(-W/2,-W/2+8,-D/2+podium_depth,D/2-podium_depth,0,plinth_z,2);box(W/2-8,W/2,-D/2+podium_depth,D/2-podium_depth,0,plinth_z,2)
# Five suspended vertical villages; each has front and rear floor wings leaving a visible atrium void.
levels=[(22,47),(53,78),(84,109),(115,140),(146,171)]
for k,(z0,z1) in enumerate(levels):
    # slightly varied module depths and offsets create the non-template vertical rhythm
    front=8.5+(k%2)*1.2;back=8.5+((k+1)%2)*1.2
    inset=1.3+(k%3)*.7
    box(-W/2+inset,W/2-inset,-D/2+inset,-D/2+inset+front,z0,z1,0)
    box(-W/2+inset,W/2-inset,D/2-inset-back,D/2-inset,z0,z1,0)
    # end service pods / perimeter modules
    box(-W/2+inset,-W/2+10,-D/2+front,D/2-back,z0,z1,1)
    box(W/2-10,W/2-inset,-D/2+front,D/2-back,z0,z1,1)
# top mechanical/crown zone and two shallow roof caps
box(-W/2+4,W/2-4,-D/2+4,D/2-4,171,178.8,1)
box(-W/2+9,W/2-9,-D/2+9,D/2-9,178.8,181.4,2)
mesh=bpy.data.meshes.new('HSBC_v2_Mass_Mesh');mesh.from_pydata(V,[],F);mesh.update();mass=bpy.data.objects.new('HSBC_v2_Suspended_Modules',mesh);coll.objects.link(mass);mass.parent=root
for m in [mat_glass,mat_steel,mat_podium,mat_accent,mat_dark]:mesh.materials.append(m)
for i,p in enumerate(mesh.polygons):p.material_index=MI[i]
mass['detail']='five suspended vertical villages around a central atrium void; open public plaza retained'

# Structural masts and five double-storey truss levels.
cu=bpy.data.curves.new('HSBC_v2_Exposed_Structure','CURVE');cu.dimensions='3D';cu.bevel_depth=.38;cu.bevel_resolution=1;cu.resolution_u=1;cu.materials.append(mat_accent)
def seg(a,b):
    sp=cu.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*a,1);sp.points[1].co=(*b,1)
def local(p,z):return (p[0],p[1],z)
# two rows of four masts, matching the actual suspension concept.
mx=[-W/2+8,-W/6,W/6,W/2-8]; my=[-D/2+8,D/2-8]
for yy in my:
    for xx in mx:
        # mast as a four-sided steel member represented by four lines
        for dx,dy in [(-1.9,-1.9),(1.9,-1.9),(1.9,1.9),(-1.9,1.9)]:
            seg(local((xx+dx,yy+dy),0),local((xx+dx,yy+dy),178.8))
        # mast corner braces
        seg(local((xx-1.9,yy-1.9),0),local((xx+1.9,yy+1.9),178.8));seg(local((xx+1.9,yy-1.9),0),local((xx-1.9,yy+1.9),178.8))
# five double-height truss bands along both long elevations and cross-bay links.
for z0,z1 in [(35,43),(67,75),(99,107),(131,139),(163,171)]:
    for yy in my:
        for xx in mx[:-1]:
            x2=mx[mx.index(xx)+1];seg(local((xx,yy),z0),local((x2,yy),z0));seg(local((xx,yy),z1),local((x2,yy),z1));seg(local((xx,yy),z0),local((x2,yy),z1));seg(local((xx,yy),z1),local((x2,yy),z0))
    for xx in mx:
        seg(local((xx,my[0]),z0),local((xx,my[1]),z1));seg(local((xx,my[0]),z1),local((xx,my[1]),z0))
struct=bpy.data.objects.new('HSBC_v2_Masts_and_Suspension_Trusses',cu);coll.objects.link(struct);struct.parent=root;struct['basis']='eight perimeter masts + five double-storey truss bands based on structural references'

# Floor/curtainwall grid and atrium edges.
fg=bpy.data.curves.new('HSBC_v2_Facade_Grid','CURVE');fg.dimensions='3D';fg.bevel_depth=.055;fg.bevel_resolution=0;fg.resolution_u=1;fg.materials.append(mat_steel)
def fseg(a,b):
    sp=fg.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*a,1);sp.points[1].co=(*b,1)
# Fine horizontal lines across the front/rear wings and vertical panel lines.
for z in [22,27,32,37,42,53,58,63,68,73,78,84,89,94,99,104,109,115,120,125,130,135,140,146,151,156,161,166,171,178]:
    fseg((-W/2+5,-D/2+7,z),(W/2-5,-D/2+7,z));fseg((-W/2+5,D/2-7,z),(W/2-5,D/2-7,z))
for xx in np.linspace(-W/2+6,W/2-6,16):
    fseg((float(xx),-D/2+7,16),(float(xx),-D/2+7,178));fseg((float(xx),D/2-7,16),(float(xx),D/2-7,178))
# Atrium edge lines and stylized escalator/walkway traces inside the void.
for z in [22,53,84,115,146,171]:
    fseg((-W/2+9,-D/2+podium_depth,z),(W/2-9,-D/2+podium_depth,z));fseg((-W/2+9,D/2-podium_depth,z),(W/2-9,D/2-podium_depth,z))
for xx in [-W/4,0,W/4]:
    fseg((xx,-D/2+podium_depth,22),(xx,D/2-podium_depth,22))
frames=bpy.data.objects.new('HSBC_v2_Curtainwall_and_Atrium_Frames',fg);coll.objects.link(frames);frames.parent=root
# Sunscoop blades on the harbour-facing side (front elevation), as angled mirror fins.
sc=bpy.data.curves.new('HSBC_v2_Sunscoop_Blades','CURVE');sc.dimensions='3D';sc.bevel_depth=.16;sc.bevel_resolution=1;sc.resolution_u=1;sc.materials.append(mat_accent)
for z in np.linspace(30,168,12):
    y0=-D/2+5.2; y1=-D/2-2.0
    segpts=[(-W*.40,y0,z),(W*.40,y0,z+2.5),(-W*.40,y0,z+5.0)]
    sp=sc.splines.new('POLY');sp.points.add(2)
    for p,q in zip(sp.points,segpts):p.co=(*q,1)
scoop=bpy.data.objects.new('HSBC_v2_Sunscoop_and_Sunshades',sc);coll.objects.link(scoop);scoop.parent=root

# metadata and save
root['rendering_note']='Separate mass, eight exposed masts, five suspension truss levels, open plaza/atrium and sunshade fins.'
bpy.context.scene['hsbc_version']='v2 structural massing upgrade';bpy.context.scene['hsbc_reference_sources']='HSBC official 2026 architecture description; HKIE structural project detail; OSM/GIS footprint and Lands Department DTM.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print({'root':root.name,'footprint_m':[round(W,2),round(D,2)],'base':base,'height':178.8,'children':len(root.children),'objects':['HSBC_v2_Suspended_Modules','HSBC_v2_Masts_and_Suspension_Trusses','HSBC_v2_Curtainwall_and_Atrium_Frames','HSBC_v2_Sunscoop_and_Sunshades']})
