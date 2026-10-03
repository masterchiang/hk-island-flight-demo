import bpy, json, math, re, os
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(r'<PROJECT_ROOT>')
DATA=ROOT/'data/processed'
records=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf-8'))['buildings']
terrain=np.load(DATA/'terrain_hki.npz')
x=terrain['x']; y=terrain['y']; z=terrain['z']

# The generic island mesh remains as a far LOD, but this pass replaces all
# explicitly non-residential high-rises and ambiguous mixed-use towers with
# separate, inspectable building objects.
RESIDENTIAL={'apartments','residential','house','semidetached_house','terrace','dormitory','hut','shed','roof'}
def is_individual(b):
    kind=b.get('kind','yes'); h=float(b.get('height') or 0); name=(b.get('name') or '').strip()
    # Keep every named non-residential / civic / institutional building at
    # >=15m, plus unnamed non-residential high-rises at >=35m. This catches
    # distinctive halls, schools, churches, hotels, offices and podiums that
    # would otherwise disappear into the far LOD.
    named_nonres = bool(name) and kind not in RESIDENTIAL
    if kind in RESIDENTIAL:return False
    if named_nonres and h >= 15:return True
    if h < 35:return False
    # OSM 'yes' is ambiguous; retain tall or named mixed-use buildings instead
    # of assuming they are residential.
    return kind!='yes' or bool(name) or h>=70

selected=[b for b in records if is_individual(b)]
selected_ids={str(b['id']) for b in selected}
print('individual target',len(selected),'remote',len(records)-len(selected))

# Reuse existing project materials; create safe fallbacks only if a user opened
# this script in a blank scene.
def ensure_emission(name,color,strength):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;n.clear();o=n.new('ShaderNodeOutputMaterial');e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=strength;l.new(e.outputs['Emission'],o.inputs['Surface']);m.diffuse_color=(*color,1);return m

def mat(name, fallback):
    return bpy.data.materials.get(name) or ensure_emission(name,*fallback)
mat_low=mat('Holo_Facade_Lowrise',((0.008,0.08,0.14),0.45))
mat_res=mat('Holo_Facade_Residential',((0.008,0.16,0.28),0.65))
mat_tower=mat('Holo_Facade_Tower',((0.004,0.20,0.38),0.85))
mat_special=mat('Holo_Facade_Landmark',((0.02,0.45,0.70),1.1))
mat_grid=mat('Holo_Grid',((0.006,0.12,0.24),0.65))

# Collections
for name in ['06_Individual_NonResidential_Highrises','07_Remote_Residential_LOD']:
    old=bpy.data.collections.get(name)
    if old:
        for o in list(old.objects): bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(old)
ind_coll=bpy.data.collections.new('06_Individual_NonResidential_Highrises');bpy.context.scene.collection.children.link(ind_coll)
remote_coll=bpy.data.collections.new('07_Remote_Residential_LOD');bpy.context.scene.collection.children.link(remote_coll)

# Remove the previous all-in-one city and its duplicate wire overlay. A new
# remote mesh is built below with the selected high-rises omitted.
for name in ['HKI_Buildings_15k_Procedural_Facades','HKI_Building_EdgeGlow','HKI_Landmark_WindowFrames']:
    o=bpy.data.objects.get(name)
    if o:bpy.data.objects.remove(o,do_unlink=True)

origin_x,origin_y=840000.,815000.
def sample_z(px,py):
    ix=int(np.clip(np.searchsorted(x,px)-1,0,len(x)-1));iy=int(np.clip(np.searchsorted(y,py)-1,0,len(y)-1));return float(z[iy,ix])

def clean_ring(r,max_points=32):
    pts=[Vector((float(a),float(b),0)) for a,b in r]
    if len(pts)>max_points:
        step=len(pts)/max_points;pts=[pts[int(i*step)%len(pts)] for i in range(max_points)]
    # remove near duplicates
    out=[]
    for p in pts:
        if not out or (p-out[-1]).length>0.15:out.append(p)
    if len(out)>2 and (out[0]-out[-1]).length<0.15:out.pop()
    return out

def centroid(r):
    return Vector((sum(p.x for p in r)/len(r),sum(p.y for p in r)/len(r),0))

def scaled_ring(r,scale,c=None):
    c=c or centroid(r);return [c+(p-c)*scale for p in r]

def add_side(v,f,mi,r,z0,z1,material):
    s=len(v);v.extend([(p.x,p.y,z0) for p in r]+[(p.x,p.y,z1) for p in r]);n=len(r)
    for i in range(n):j=(i+1)%n;f.append((s+i,s+j,s+n+j,s+n+i));mi.append(material)

def add_cap(v,f,mi,r,zz,material,reverse=False):
    s=len(v);v.extend([(p.x,p.y,zz) for p in r]);idx=tuple(s+i for i in (reversed(range(len(r))) if reverse else range(len(r))));f.append(idx);mi.append(material)

def add_ribbon(v,f,mi,p0,p1,z0,z1,width,normal,material):
    # Thin facade fin/mullion ribbon, offset outward from a wall.
    d=(p1-p0).normalized();q=Vector((-d.y,d.x,0))*width*0.5;off=normal*0.08
    pts=[p0+off-q,p1+off-q,p1+off+q,p0+off+q];s=len(v);v.extend([(p.x,p.y,z0) for p in pts]+[(p.x,p.y,z1) for p in pts])
    f.extend([(s,s+1,s+5,s+4),(s+1,s+2,s+6,s+5),(s+2,s+3,s+7,s+6),(s+3,s,s+4,s+7)]);mi.extend([material]*4)

def add_box(v,f,mi,center,size,material):
    cx,cy,cz=center; sx,sy,sz=[a*0.5 for a in size];s=len(v)
    v.extend([(cx+dx,cy+dy,cz+dz) for dx,dy,dz in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]])
    f.extend([(s,s+1,s+2,s+3),(s+4,s+7,s+6,s+5),(s,s+4,s+5,s+1),(s+1,s+5,s+6,s+2),(s+2,s+6,s+7,s+3),(s+4,s,s+3,s+7)]);mi.extend([material]*6)

def profile_for(b):
    n=(b.get('name') or '').lower();k=b.get('kind','yes')
    if any(q in n for q in ['bank of china','中銀']):return 'triangular_spire'
    if any(q in n for q in ['two international finance','one international finance','ifc','國際金融中心']):return 'ifc_tapered'
    if 'the center' in n or n=='中心':return 'rounded_taper'
    if 'central plaza' in n:return 'spire'
    if any(q in n for q in ['one island east','one taikoo place','two taikoo place']):return 'tapered_crown'
    if 'hopewell' in n:return 'cylinder'
    if 'hsbc' in n:return 'cantilever'
    if 'jardine house' in n:return 'round_window_slab'
    if any(q in n for q in ['lippo','hysan','aia central','cheung kong']):return 'stepped_glass'
    if any(q in n for q in ['government','immigration','revenue','high block']):return 'stepped_civic'
    if k in {'hotel','hospital','university','school','civic','public','government'}:return 'stepped_civic'
    if k in {'industrial','warehouse','parking'}:return 'slab'
    choices=['stepped_glass','tapered_crown','slab','spire','rounded_taper']
    return choices[int(b['id'])%len(choices)]

def build_individual(b):
    ring=clean_ring(b['footprint'],40)
    if len(ring)<3:return None
    c=centroid(ring);base=sample_z(c.x,c.y)+0.85;h=max(15.,float(b.get('height') or 15));profile=profile_for(b);kind=b.get('kind','yes');name=b.get('name') or f"OSM_{b['id']}"
    variant=int(str(b['id'])[-3:]) % 17
    # Every building gets a deterministic, data-derived variant rather than a
    # shared prefab: floor rhythm, crown proportion, fin density and podium
    # inset are tied to the OSM feature id and footprint dimensions.
    floor_h=2.75 + (variant % 7)*0.17
    fin_density=2 + (variant % 5)
    crown_bias=0.72 + (variant % 6)*0.055
    # Preserve the source footprint as podium; tower is a controlled inset,
    # so the model reads as a real podium+tower composition, not a stretched box.
    if profile in {'cylinder','round_window_slab'}:
        rx=max(p.x for p in ring)-min(p.x for p in ring);ry=max(p.y for p in ring)-min(p.y for p in ring);rr=min(rx,ry)*0.46;tower=[c+Vector((math.cos(i*math.tau/12)*rr,math.sin(i*math.tau/12)*rr,0)) for i in range(12)]
    else:
        shrink={'ifc_tapered':0.78,'triangular_spire':0.82,'rounded_taper':0.84,'tapered_crown':0.86,'cantilever':0.80}.get(profile,0.91);tower=scaled_ring(ring,shrink,c)
    podium_h=min(max(6.,h*(0.07+0.012*(variant%5))),32.)
    if profile in {'stepped_civic','cantilever'}:podium_h=min(max(12.,h*(0.13+0.01*(variant%4))),42.)
    crown_h=min(max(4.,h*(0.055+0.012*(variant%5))),30.)
    tz=base+podium_h;top=base+h-crown_h
    v=[];f=[];mi=[]
    # podium and floor-banded tower
    base_mat=3 if name and h>=80 else (2 if h>=60 else 1)
    add_side(v,f,mi,ring,base,base+podium_h,base_mat);add_cap(v,f,mi,ring,base+podium_h,base_mat)
    bands=max(1,min(140,int(math.ceil((top-tz)/floor_h))))
    for i in range(bands):
        z0=tz+(top-tz)*i/bands;z1=tz+(top-tz)*(i+1)/bands
        if profile in {'ifc_tapered','tapered_crown','rounded_taper','triangular_spire'}:
            r0=scaled_ring(tower,1.0-(0.035+0.004*(variant%6))*i/bands,c);r1=scaled_ring(tower,1.0-(0.035+0.004*(variant%6))*(i+1)/bands,c)
        else:r0=r1=tower
        # add tapered band between two rings with matching vertex count
        s=len(v);v.extend([(p.x,p.y,z0) for p in r0]+[(p.x,p.y,z1) for p in r1]);n=len(r0)
        for j in range(n):jj=(j+1)%n;f.append((s+j,s+jj,s+n+jj,s+n+j));mi.append(3 if (i%5==0 and profile in {'ifc_tapered','triangular_spire','tapered_crown'}) else 2)
    add_cap(v,f,mi,tower,top,3)
    # Distinct crowns / roof machinery by profile.
    if profile in {'spire','ifc_tapered','triangular_spire'}:
        r1=scaled_ring(tower,0.78,c);r2=scaled_ring(tower,0.40,c);mid=top+crown_h*0.45;add_side(v,f,mi,tower,top,top+crown_h*0.25,3);add_side(v,f,mi,r1,top+crown_h*0.25,mid,3);add_side(v,f,mi,r2,mid,top+crown_h*0.78,3);add_cap(v,f,mi,r2,top+crown_h*0.78,3);add_box(v,f,mi,(c.x,c.y,top+crown_h*0.9),(0.45,0.45,crown_h*0.25),4)
    elif profile in {'stepped_glass','stepped_civic'}:
        for q,sc in enumerate([0.98,0.86,0.70]):
            r=scaled_ring(tower,sc,c);z0=top+crown_h*q/3;z1=top+crown_h*(q+1)/3;add_side(v,f,mi,r,z0,z1,3 if q<2 else 4);add_cap(v,f,mi,r,z1,3 if q<2 else 4)
    elif profile in {'cylinder','round_window_slab'}:
        r=scaled_ring(tower,0.94,c);add_side(v,f,mi,r,top,top+crown_h,3);add_cap(v,f,mi,r,top+crown_h,3)
        # central roof equipment / antenna
        add_box(v,f,mi,(c.x,c.y,top+crown_h+2),(max(1.5,(max(p.x for p in r)-min(p.x for p in r))*0.25),max(1.5,(max(p.y for p in r)-min(p.y for p in r))*0.25),4),4)
    elif profile=='cantilever':
        r=scaled_ring(tower,1.05,c);add_side(v,f,mi,r,top,top+crown_h*0.5,3);add_cap(v,f,mi,r,top+crown_h*0.5,3);add_box(v,f,mi,(c.x,c.y,top+crown_h*0.78),(max(6,(max(p.x for p in ring)-min(p.x for p in ring))*0.7),max(4,(max(p.y for p in ring)-min(p.y for p in ring))*0.7),crown_h*0.35),4)
    else:
        r=scaled_ring(tower,0.94,c);add_side(v,f,mi,r,top,top+crown_h,3);add_cap(v,f,mi,r,top+crown_h,3)
    # Individual vertical mullions/fins on the most important towers.
    if name and (h>=70 or profile in {'ifc_tapered','triangular_spire','rounded_taper','cantilever'}) or h>=120:
        edges=sorted([(ring[i],ring[(i+1)%len(ring)]) for i in range(len(ring))],key=lambda e:(e[1]-e[0]).length,reverse=True)[:min(3,len(ring))]
        for p0,p1 in edges:
            d=p1-p0;L=d.length
            steps=max(1,min(12,int(L/(5.5 + (variant%4)*0.8))))
            midp=(p0+p1)*0.5;normal=Vector((d.y,-d.x,0)).normalized()
            if normal.dot(c-midp)>0:normal=-normal
            for q in range(1,steps):
                pp=p0+d*(q/steps);add_ribbon(v,f,mi,pp,pp+d.normalized()*0.12,base+podium_h*0.8,top+crown_h*0.1,0.16,normal,4)
    mesh=bpy.data.meshes.new('IND_'+str(b['id'])+'_Mesh');mesh.from_pydata(v,[],f);mesh.update()
    ob=bpy.data.objects.new('IND_'+str(b['id'])+'_'+re.sub(r'[^A-Za-z0-9_]+','_',name)[:52],mesh);ind_coll.objects.link(ob)
    for m in [mat_low,mat_res,mat_tower,mat_special,mat_grid]:mesh.materials.append(m)
    for i,p in enumerate(mesh.polygons):p.material_index=mi[i]
    ob['individual_model']=True;ob['osm_id']=str(b['id']);ob['name']=name;ob['kind']=kind;ob['height_m']=round(h,2);ob['profile']=profile;ob['variant']=variant;ob['floor_height_m']=round(floor_h,2);ob['fin_density']=fin_density;ob['source']='OSM footprint/height + deterministic architecture profile';ob['facade_status']='procedural mullions and floor-banded facade; replace with official 3D tile or licensed photos for photo-accurate facade'
    return ob

# Build every selected high-rise separately.
made=[]
for b in selected:
    ob=build_individual(b)
    if ob:made.append(ob)
print('individual objects',len(made))

# Rebuild remote LOD without the individual buildings.
rv=[];rf=[];rmi=[]
for b in records:
    if str(b['id']) in selected_ids:continue
    r=clean_ring(b['footprint'],24)
    if len(r)<3:continue
    c=centroid(r);base=sample_z(c.x,c.y)+0.55;h=float(b.get('height') or 8);s=len(rv);rv.extend([(p.x,p.y,base) for p in r]+[(p.x,p.y,base+h) for p in r]);n=len(r);rf.append(tuple(s+i for i in reversed(range(n))));rmi.append(0)
    rf.append(tuple(s+n+i for i in range(n)));rmi.append(2 if h>=55 else (1 if h>=18 else 0))
    for i in range(n):j=(i+1)%n;rf.append((s+i,s+j,s+n+j,s+n+i));rmi.append(2 if h>=55 else (1 if h>=18 else 0))
rm=bpy.data.meshes.new('HKI_Remote_Residential_LOD_Mesh');rm.from_pydata(rv,[],rf);rm.update();ro=bpy.data.objects.new('HKI_Remote_Residential_and_Lowrise_LOD',rm);remote_coll.objects.link(ro)
for m in [mat_low,mat_res,mat_tower,mat_special]:rm.materials.append(m)
for i,p in enumerate(rm.polygons):p.material_index=rmi[i]
ro['source']='OSM Hong Kong Island 2026-09-29';ro['excluded_individual_count']=len(made);ro['purpose']='far LOD; non-residential high-rises are separate objects in collection 06'
# Make the individual collection visible but keep remote LOD as normal.
ind_coll.hide_render=False;ind_coll.hide_viewport=False;remote_coll.hide_render=False;remote_coll.hide_viewport=False
scene=bpy.context.scene;scene['individual_highrise_count']=len(made);scene['individual_highrise_selection']='named non-residential/civic/institutional >= 15m, plus unnamed explicit non-residential >= 35m and tall ambiguous OSM yes buildings';scene['remote_lod_excludes_individuals']=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print({'individual':len(made),'remote_vertices':len(rv),'remote_faces':len(rf),'blend':str(ROOT/'HKI_Holographic_Atlas.blend')})
