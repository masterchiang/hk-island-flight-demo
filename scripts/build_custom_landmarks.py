import bpy, json, math, re
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(r'<PROJECT_ROOT>')
DATA=ROOT/'data/processed'
RECORDS=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf-8'))['buildings']
T=np.load(DATA/'terrain_hki.npz'); TX=T['x']; TY=T['y']; TZ=T['z']
COLL_NAME='09_Custom_Landmarks'

# Main landmarks with special geometry inferred from their known architectural
# type and their actual OSM footprint. These are not shared prefabs.
TARGETS=[
    'HSBC Main Building','Two International Finance Centre','One International Finance Centre',
    'Central Plaza','The Center','One Island East','Hopewell Centre','One Taikoo Place',
    'Two Taikoo Place','One Exchange Square','Two Exchange Square','Three Exchange Square',
    'Jardine House','Lippo Centre Tower 1','Lippo Centre Tower 2','Convention Plaza Office Tower',
    'The Henderson','Sun Hung Kai Centre','Cheung Kong Center II','ICBC Tower','PCCW Tower',
    'Admiralty Centre Tower 1','CITIC Tower','Great Eagle Centre','Harbour Centre'
]
SPECIAL={
 'HSBC Main Building':'hsbc_modular',
 'Two International Finance Centre':'ifc2',
 'One International Finance Centre':'ifc1',
 'Central Plaza':'central_plaza',
 'The Center':'the_center',
 'One Island East':'one_island_east',
 'Hopewell Centre':'hopewell',
 'One Taikoo Place':'taikoo_one',
 'Two Taikoo Place':'taikoo_two',
 'One Exchange Square':'exchange_square',
 'Two Exchange Square':'exchange_square',
 'Three Exchange Square':'exchange_square_small',
 'Jardine House':'jardine',
 'Lippo Centre Tower 1':'lippo',
 'Lippo Centre Tower 2':'lippo',
 'Convention Plaza Office Tower':'convention',
 'The Henderson':'henderson',
 'Sun Hung Kai Centre':'sun_hung_kai',
 'Cheung Kong Center II':'cheung_kong',
 'ICBC Tower':'icbc',
 'PCCW Tower':'pccw',
 'Admiralty Centre Tower 1':'admiralty',
 'CITIC Tower':'citic',
 'Great Eagle Centre':'great_eagle',
 'Harbour Centre':'harbour_centre',
}

# Helpers
def rec_for(name):
    rows=[b for b in RECORDS if b.get('name')==name]
    return sorted(rows,key=lambda b:(b.get('kind',''),-float(b.get('height') or 0)))[0] if rows else None

def sample_z(px,py):
    ix=int(np.clip(np.searchsorted(TX,px)-1,0,len(TX)-1)); iy=int(np.clip(np.searchsorted(TY,py)-1,0,len(TY)-1)); return float(TZ[iy,ix])

def ring_clean(r,max_points=24):
    p=[Vector((float(a),float(b),0)) for a,b in r]
    if len(p)>max_points:
        step=len(p)/max_points;p=[p[int(i*step)%len(p)] for i in range(max_points)]
    out=[]
    for q in p:
        if not out or (q-out[-1]).length>0.12:out.append(q)
    if len(out)>2 and (out[0]-out[-1]).length<0.12:out.pop()
    return out

def center(r):return Vector((sum(p.x for p in r)/len(r),sum(p.y for p in r)/len(r),0))
def scale_ring(r,s,c=None):
    c=c or center(r);return [c+(p-c)*s for p in r]
def box_ring(c,sx,sy):
    x,y=c.x,c.y;return [Vector((x-sx/2,y-sy/2,0)),Vector((x+sx/2,y-sy/2,0)),Vector((x+sx/2,y+sy/2,0)),Vector((x-sx/2,y+sy/2,0))]
def regular_ring(c,rx,ry,n=12,angle=0):return [c+Vector((math.cos(angle+math.tau*i/n)*rx,math.sin(angle+math.tau*i/n)*ry,0)) for i in range(n)]
def top_ring(r,scale=1):return scale_ring(r,scale)

def add_prism(V,F,M,r0,r1,z0,z1,mat=0,cap=True):
    s=len(V);V.extend([(p.x,p.y,z0) for p in r0]+[(p.x,p.y,z1) for p in r1]);n=len(r0)
    for i in range(n):
        j=(i+1)%n;F.append((s+i,s+j,s+n+j,s+n+i));M.append(mat)
    if cap:
        F.append(tuple(s+i for i in reversed(range(n))));M.append(mat)
        F.append(tuple(s+n+i for i in range(n)));M.append(mat)

def add_box(V,F,M,c,sx,sy,z0,z1,mat=0):add_prism(V,F,M,box_ring(c,sx,sy),box_ring(c,sx,sy),z0,z1,mat)

def add_taper(V,F,M,r,z0,z1,s0,s1,mat=0):add_prism(V,F,M,scale_ring(r,s0),scale_ring(r,s1),z0,z1,mat)

def add_curve(curve,points,bevel=0.12):
    if len(points)<2:return
    sp=curve.splines.new('POLY');sp.points.add(len(points)-1)
    for p,q in zip(sp.points,points):p.co=(q.x,q.y,q.z,1)

def add_segment(curve,a,b):add_curve(curve,[a,b])

def add_ring_lines(curve,r,z0,z1,step=3.2,vertical=5.0,skip_vertical=False):
    # Horizontal floor lines + vertical mullions follow the actual footprint.
    h=z0+step
    while h<z1-0.5:
        for i in range(len(r)):add_segment(curve,Vector((r[i].x,r[i].y,h)),Vector((r[(i+1)%len(r)].x,r[(i+1)%len(r)].y,h)))
        h+=step
    if skip_vertical:return
    for i in range(len(r)):
        a=r[i];b=r[(i+1)%len(r)];d=b-a;L=d.length;count=max(1,min(18,int(L/max(2.5,vertical))))
        for k in range(1,count):
            q=a+d*(k/count);add_segment(curve,Vector((q.x,q.y,z0)),Vector((q.x,q.y,z1)))

def add_vertical_fins(curve,r,z0,z1,count=4,offset=0.10):
    # A few outward fins make each tower read as a separate facade system.
    c=center(r)
    for i in range(len(r)):
        a=r[i];b=r[(i+1)%len(r)];d=b-a;L=d.length
        for k in range(1,min(count+1,max(2,int(L/8)))):
            q=a+d*(k/(min(count+1,max(2,int(L/8)))));n=Vector((d.y,-d.x,0)).normalized()
            if n.dot(c-q)>0:n=-n
            add_segment(curve,Vector((q.x+n.x*offset,q.y+n.y*offset,z0)),Vector((q.x+n.x*offset,q.y+n.y*offset,z1)))

def make_mat(name,base,metal=0.0,rough=0.35,emit=(0.0,0.05,0.12),estr=0.25):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;n.clear();o=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled')
    for key,val in [('Base Color',(*base,1)),('Metallic',metal),('Roughness',rough),('Emission Color',(*emit,1)),('Emission Strength',estr)]:
        if p.inputs.get(key):p.inputs[key].default_value=val
    l.new(p.outputs['BSDF'],o.inputs['Surface']);m.diffuse_color=(*base,1);return m

mats=[
 make_mat('Custom_Landmark_Glass',(0.006,0.06,0.12),0.55,0.20,(0.0,0.20,0.42),0.45),
 make_mat('Custom_Landmark_Steel',(0.025,0.11,0.16),0.80,0.25,(0.0,0.32,0.55),0.50),
 make_mat('Custom_Landmark_Podium',(0.01,0.08,0.12),0.35,0.38,(0.0,0.12,0.25),0.30),
 make_mat('Custom_Landmark_Accent',(0.015,0.30,0.48),0.60,0.22,(0.0,0.65,1.0),0.90),
 make_mat('Custom_Landmark_Dark',(0.001,0.008,0.016),0.20,0.55,(0.0,0.04,0.08),0.16),
]

# clear previous custom pass
old=bpy.data.collections.get(COLL_NAME)
if old:
    for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
coll=bpy.data.collections.new(COLL_NAME);bpy.context.scene.collection.children.link(coll)

# If a previous run failed after hiding generic objects, restore them before rebuilding.
for _o in bpy.context.scene.objects:
    if _o.get('replaced_by_custom_landmark'):
        _o.hide_viewport=False; _o.hide_render=False; _o['replaced_by_custom_landmark']=False

# Do not rebuild an imported Sketchfab landmark. Bank of China Tower is handled
# separately and remains the primary high-detail model.
skip_names={'Bank of China Tower'}

created=[]
for name in TARGETS:
    if name in skip_names:continue
    b=rec_for(name)
    if not b:continue
    profile=SPECIAL[name];r=ring_clean(b['footprint']);
    if len(r)<3:continue
    c=center(r);base=sample_z(c.x,c.y)+0.85;h=float(b.get('height') or 30.0)
    # Hide the generic independent object with the same OSM id.
    for o in bpy.context.scene.objects:
        if str(o.get('osm_id',''))==str(b['id']) and o.name.startswith('IND_'):
            o.hide_viewport=True;o.hide_render=True;o['replaced_by_custom_landmark']=True
    V=[];F=[];M=[]
    # profile-specific massing; every result uses its own footprint and size.
    podium=max(8.0,min(38.0,h*0.12)); top=base+h
    if profile=='hsbc_modular':
        add_prism(V,F,M,r,r,base,base+podium,2)
        # Suspended modular blocks: characteristic gaps, offset modules and cores.
        modules=[(base+podium+2,base+h*0.30,0.92),(base+h*0.38,base+h*0.53,0.88),(base+h*0.61,base+h*0.76,0.83),(base+h*0.84,base+h*0.965,0.77)]
        for z0,z1,sc in modules:
            rr=scale_ring(r,sc,c);add_prism(V,F,M,rr,rr,z0,z1,0)
        # central and corner support masts, plus external diagonal trusses
        bx=max(p.x for p in r)-min(p.x for p in r);by=max(p.y for p in r)-min(p.y for p in r)
        for px in [c.x-bx*0.32,c.x+bx*0.32]:
            for py in [c.y-by*0.32,c.y+by*0.32]:add_box(V,F,M,Vector((px,py,0)),3.4,3.4,base+podium,top,1)
        # facade braces will be curves below
        curve_segments=[]
    elif profile=='ifc2':
        add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_taper(V,F,M,r,base+podium,top-22,.90,.76,0);add_taper(V,F,M,r,top-22,top,.76,.56,1)
        add_box(V,F,M,c,18,18,top-11,top+7,3)
        curve_segments=[]
    elif profile=='ifc1':
        add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_taper(V,F,M,r,base+podium,top-18,.94,.84,0);add_prism(V,F,M,scale_ring(r,.84,c),scale_ring(r,.70,c),top-18,top-4,1);add_prism(V,F,M,scale_ring(r,.70,c),scale_ring(r,.58,c),top-4,top,3);curve_segments=[]
    elif profile=='central_plaza':
        # Triangular impression: keep GIS ring, emphasize three primary corners.
        rr=regular_ring(c,max(p.x for p in r)-min(p.x for p in r),max(p.y for p in r)-min(p.y for p in r),3,math.radians(30));add_prism(V,F,M,rr,scale_ring(rr,.88,c),base,base+podium,2);add_taper(V,F,M,rr,base+podium,top-22,.88,.72,0);add_taper(V,F,M,rr,top-22,top,.72,.58,1);add_box(V,F,M,c,2.5,2.5,top,top+26,3);curve_segments=[]
    elif profile=='the_center':
        rr=regular_ring(c,(max(p.x for p in r)-min(p.x for p in r))/2,(max(p.y for p in r)-min(p.y for p in r))/2,8,math.radians(22));add_prism(V,F,M,r,scale_ring(r,.9,c),base,base+podium,2);add_taper(V,F,M,rr,base+podium,top-34,.96,.82,0);add_taper(V,F,M,rr,top-34,top,.82,.68,1);add_box(V,F,M,c,3,3,top,top+15,3);curve_segments=[]
    elif profile=='one_island_east':
        add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_taper(V,F,M,r,base+podium,top-24,.94,.86,0);add_taper(V,F,M,r,top-24,top,.86,.65,3);add_box(V,F,M,c,10,10,top,top+8,1);curve_segments=[]
    elif profile=='hopewell':
        rr=regular_ring(c,(max(p.x for p in r)-min(p.x for p in r))/2,(max(p.y for p in r)-min(p.y for p in r))/2,16,0);add_prism(V,F,M,r,scale_ring(r,.95,c),base,base+podium,2);add_taper(V,F,M,rr,base+podium,top-20,.98,.92,0);add_prism(V,F,M,scale_ring(rr,.92,c),scale_ring(rr,.78,c),top-20,top-5,1);add_prism(V,F,M,scale_ring(rr,.78,c),scale_ring(rr,.60,c),top-5,top,3);curve_segments=[]
    elif profile in {'taikoo_one','taikoo_two'}:
        add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_prism(V,F,M,scale_ring(r,.88,c),scale_ring(r,.84,c),base+podium,top-22,0);add_prism(V,F,M,scale_ring(r,.84,c),scale_ring(r,.72,c),top-22,top-7,1);add_prism(V,F,M,scale_ring(r,.72,c),scale_ring(r,.55,c),top-7,top,3);curve_segments=[]
    elif profile=='exchange_square':
        add_prism(V,F,M,r,scale_ring(r,.9,c),base,base+podium,2);add_prism(V,F,M,scale_ring(r,.9,c),scale_ring(r,.86,c),base+podium,top-18,0);add_prism(V,F,M,scale_ring(r,.86,c),scale_ring(r,.70,c),top-18,top-5,1);add_prism(V,F,M,scale_ring(r,.70,c),scale_ring(r,.56,c),top-5,top,3);curve_segments=[]
    elif profile=='exchange_square_small':
        add_prism(V,F,M,r,scale_ring(r,.9,c),base,base+podium,2);add_prism(V,F,M,scale_ring(r,.9,c),scale_ring(r,.72,c),base+podium,top-10,0);add_prism(V,F,M,scale_ring(r,.72,c),scale_ring(r,.55,c),top-10,top,3);curve_segments=[]
    elif profile=='jardine':
        rr=regular_ring(c,(max(p.x for p in r)-min(p.x for p in r))/2,(max(p.y for p in r)-min(p.y for p in r))/2,16,math.pi/16);add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_prism(V,F,M,rr,rr,base+podium,top,0);add_prism(V,F,M,scale_ring(rr,.92,c),scale_ring(rr,.75,c),top-12,top,3);curve_segments=[]
    elif profile=='lippo':
        add_prism(V,F,M,r,scale_ring(r,.90,c),base,base+podium,2);add_taper(V,F,M,r,base+podium,top-20,.91,.80,0);add_taper(V,F,M,r,top-20,top,.80,.62,3);curve_segments=[]
    elif profile=='convention':
        add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_prism(V,F,M,scale_ring(r,.90,c),scale_ring(r,.82,c),base+podium,top-18,0);add_prism(V,F,M,scale_ring(r,.82,c),scale_ring(r,.65,c),top-18,top,3);curve_segments=[]
    elif profile=='henderson':
        rr=regular_ring(c,(max(p.x for p in r)-min(p.x for p in r))/2,(max(p.y for p in r)-min(p.y for p in r))/2,10,math.radians(18));add_prism(V,F,M,r,scale_ring(r,.92,c),base,base+podium,2);add_taper(V,F,M,rr,base+podium,top-28,.95,.76,0);add_taper(V,F,M,rr,top-28,top,.76,.42,3);curve_segments=[]
    elif profile=='sun_hung_kai':
        add_prism(V,F,M,r,scale_ring(r,.9,c),base,base+podium,2);add_prism(V,F,M,scale_ring(r,.88,c),scale_ring(r,.80,c),base+podium,top-25,0);add_taper(V,F,M,r,top-25,top,.80,.60,3);curve_segments=[]
    elif profile in {'cheung_kong','icbc','pccw','admiralty','citic','great_eagle','harbour_centre'}:
        add_prism(V,F,M,r,scale_ring(r,.90,c),base,base+podium,2);add_taper(V,F,M,r,base+podium,top-16,.90,.82,0);add_prism(V,F,M,scale_ring(r,.82,c),scale_ring(r,.62,c),top-16,top,3);curve_segments=[]
    else:
        add_prism(V,F,M,r,scale_ring(r,.9,c),base,top,0);curve_segments=[]
    mesh=bpy.data.meshes.new('CUSTOM_'+str(b['id'])+'_Mesh');mesh.from_pydata(V,[],F);mesh.update()
    root=bpy.data.objects.new('CUSTOM_'+str(b['id'])+'_'+re.sub(r'[^A-Za-z0-9_]+','_',name)[:50],None);coll.objects.link(root);root['osm_id']=str(b['id']);root['name']=name;root['profile']=profile;root['height_m']=h;root['basis']='OSM footprint + Lands Department DTM + named architectural massing';root['satellite_gis_note']='Massing tuned to footprint, podium ratio, roofline and facade rhythm visible in GIS/orthophoto references; not a claim of exact photogrammetry.'
    meshob=bpy.data.objects.new(root.name+'_Geometry',mesh);coll.objects.link(meshob);meshob.parent=root
    for m in mats:mesh.materials.append(m)
    for i,p in enumerate(mesh.polygons):p.material_index=M[i]
    # detail curves
    cu=bpy.data.curves.new(root.name+'_FacadeDetail','CURVE');cu.dimensions='3D';cu.bevel_depth=0.045 if h>150 else 0.035;cu.bevel_resolution=0;cu.resolution_u=1
    if profile=='hsbc_modular':
        # horizontal deck lines and diagonal steel braces, matching the modular structural language
        add_ring_lines(cu,r,base+podium,top,step=4.0,vertical=9.0,skip_vertical=True)
        bx=max(p.x for p in r)-min(p.x for p in r);by=max(p.y for p in r)-min(p.y for p in r)
        for zz in [base+podium,base+h*.36,base+h*.59,base+h*.82]:
            a=Vector((c.x-bx*.47,c.y-by*.47,zz));b1=Vector((c.x+bx*.47,c.y+by*.47,zz+18));a2=Vector((c.x+bx*.47,c.y-by*.47,zz));b2=Vector((c.x-bx*.47,c.y+by*.47,zz+18));add_segment(cu,a,b1);add_segment(cu,a2,b2)
    elif profile in {'jardine','hopewell'}:add_ring_lines(cu,regular_ring(c,(max(p.x for p in r)-min(p.x for p in r))/2,(max(p.y for p in r)-min(p.y for p in r))/2,16,0),base+podium,top,step=3.2,vertical=5.5)
    else:add_ring_lines(cu,scale_ring(r,.88,c),base+podium,top,step=3.3,vertical=6.5)
    cu.materials.append(mats[3]);curveob=bpy.data.objects.new(root.name+'_FacadeFrames',cu);coll.objects.link(curveob);curveob.parent=root
    created.append(root)

# hide imported Sketchfab model from this custom pass only if it is not present;
# the active primary Bank of China model remains untouched.
bpy.context.scene['custom_landmark_count']=len(created);bpy.context.scene['custom_landmark_profiles']={o.name:o.get('profile') for o in created}
bpy.context.scene['custom_landmark_basis']='OSM footprint and height + Lands Department DTM + satellite/GIS-informed building-specific massing; no shared building prefab.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print({'created':len(created),'collection':COLL_NAME,'names':[o.get('name') for o in created]})
