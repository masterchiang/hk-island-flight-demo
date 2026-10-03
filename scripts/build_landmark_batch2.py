import bpy,json,math,re
from pathlib import Path
from mathutils import Vector
import numpy as np
ROOT=Path(r'<PROJECT_ROOT>');DATA=ROOT/'data/processed'
records=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings'];T=np.load(DATA/'terrain_hki.npz');TX=T['x'];TY=T['y'];TZ=T['z']
TARGETS={
 'Highcliff':'needle_hill','The Summit':'needle_hill','Two Pacific Place':'stepped_office','Lee Garden One':'rounded_commercial','Champion Tower':'champion','High Block':'civic_twin','Queensway Government Offices High Block':'civic_twin','Conrad Hong Kong':'hotel_podium','Hysan Place':'retail_tower','AIA Central':'retail_tower','Three Pacific Place':'stepped_office','Revenue Tower':'civic_twin','Immigration Tower':'civic_twin','China Resources Building':'slab_crown','Far East Finance Centre':'slab_crown','JW Marriott Hotel Hong Kong':'hotel_podium','One Pacific Place':'stepped_office','Gloucester Tower':'slab_crown','Hopewell Centre II':'hopewell_annex','New World Tower':'slab_crown','Dorset House':'slab_crown','LKF Tower':'retail_tower','Renaissance Hong Kong Harbour View Hotel':'hotel_podium','Dah Sing Financial Centre':'slab_crown','Bank of America Tower':'champion'}
COLL='10_Custom_Landmarks_Batch2'

def getrec(name):
 rows=[b for b in records if b.get('name')==name]
 return sorted(rows,key=lambda b:-float(b.get('height') or 0))[0] if rows else None
def sample_z(px,py):
 ix=int(np.clip(np.searchsorted(TX,px)-1,0,len(TX)-1));iy=int(np.clip(np.searchsorted(TY,py)-1,0,len(TY)-1));return float(TZ[iy,ix])
def poly_local(r,c,ang):
 u=Vector((math.cos(ang),math.sin(ang),0));v=Vector((-math.sin(ang),math.cos(ang),0));return [Vector(((p.x-c.x)*u.x+(p.y-c.y)*u.y,(p.x-c.x)*v.x+(p.y-c.y)*v.y,0)) for p in r]
def center(r):return Vector((sum(p.x for p in r)/len(r),sum(p.y for p in r)/len(r),0))
def scale_ring(r,s):
 c=center(r);return [c+(p-c)*s for p in r]
def clean(r):
 p=[Vector((float(x),float(y),0)) for x,y in r];out=[]
 for q in p:
  if not out or (q-out[-1]).length>.15:out.append(q)
 return out[:36]
def prism(V,F,M,r0,r1,z0,z1,mi=0):
 s=len(V);V.extend([(p.x,p.y,z0) for p in r0]+[(p.x,p.y,z1) for p in r1]);n=len(r0)
 for i in range(n):j=(i+1)%n;F.append((s+i,s+j,s+n+j,s+n+i));M.append(mi)
 F.extend([tuple(s+i for i in reversed(range(n))),tuple(s+n+i for i in range(n))]);M.extend([mi,mi])
def box(V,F,M,c,sx,sy,z0,z1,mi=0):
 r=[Vector((c.x-sx/2,c.y-sy/2,0)),Vector((c.x+sx/2,c.y-sy/2,0)),Vector((c.x+sx/2,c.y+sy/2,0)),Vector((c.x-sx/2,c.y+sy/2,0))];prism(V,F,M,r,r,z0,z1,mi)
def line(cu,a,b):
 sp=cu.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*a,1);sp.points[1].co=(*b,1)
def mat(name,col,emit):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();o=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=.55;p.inputs['Roughness'].default_value=.28;p.inputs['Emission Color'].default_value=(*emit,1);p.inputs['Emission Strength'].default_value=.55;l.new(p.outputs['BSDF'],o.inputs['Surface']);m.diffuse_color=(*col,1);return m
mats=[mat('Batch2_Glass',(.005,.055,.11),(0,.18,.4)),mat('Batch2_Steel',(.02,.13,.18),(0,.36,.65)),mat('Batch2_Podium',(.01,.055,.08),(0,.12,.26)),mat('Batch2_Accent',(.02,.35,.55),(0,.75,1)),mat('Batch2_Dark',(.001,.006,.012),(0,.04,.08))]
old=bpy.data.collections.get(COLL)
if old:
 for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.collections.remove(old)
coll=bpy.data.collections.new(COLL);bpy.context.scene.collection.children.link(coll)
made=[]
for name,profile in TARGETS.items():
 b=getrec(name)
 if not b:continue
 r0=clean(b['footprint']);c=center(r0);arr=np.array([[p.x-c.x,p.y-c.y] for p in r0]);cov=np.cov(arr.T);vals,vecs=np.linalg.eigh(cov);axis=vecs[:,np.argmax(vals)];ang=math.atan2(float(axis[1]),float(axis[0]));r=poly_local(r0,c,ang);base=sample_z(c.x,c.y)+.85;h=float(b.get('height') or 70);W=max(p.x for p in r)-min(p.x for p in r);D=max(p.y for p in r)-min(p.y for p in r);c0=center(r);top=base+h
 # remove old named empty and hide generic mesh
 for _o in list(bpy.data.objects):
  try:
   _name=_o.name; _oid=str(_o.get('osm_id',''))
  except ReferenceError:
   continue
  if _name.startswith('Landmark_'+name):bpy.data.objects.remove(_o,do_unlink=True);continue
  if _oid==str(b['id']) and _name.startswith('IND_'):
   _o.hide_viewport=True;_o.hide_render=True;_o['replaced_by_batch2']=True
 V=[];F=[];M=[];pod=min(max(12,h*.11),34)
 if profile=='needle_hill':
  prism(V,F,M,r,r,base,base+pod,2);box(V,F,M,c0,W*.76,D*.75,base+pod,top-22,0);prism(V,F,M,scale_ring(r,.76),scale_ring(r,.62),top-22,top-7,1);box(V,F,M,c0,W*.2,D*.2,top-7,top+16,3)
 elif profile=='stepped_office':
  prism(V,F,M,r,scale_ring(r,.92),base,base+pod,2);prism(V,F,M,scale_ring(r,.9),scale_ring(r,.84),base+pod,top-24,0);prism(V,F,M,scale_ring(r,.84),scale_ring(r,.68),top-24,top-8,1);prism(V,F,M,scale_ring(r,.68),scale_ring(r,.52),top-8,top,3)
 elif profile=='rounded_commercial':
  prism(V,F,M,r,scale_ring(r,.92),base,base+pod,2);prism(V,F,M,scale_ring(r,.9),scale_ring(r,.9),base+pod,top-14,0);prism(V,F,M,scale_ring(r,.9),scale_ring(r,.68),top-14,top-4,1);prism(V,F,M,scale_ring(r,.68),scale_ring(r,.56),top-4,top,3)
 elif profile=='champion':
  prism(V,F,M,r,scale_ring(r,.92),base,base+pod,2);prism(V,F,M,scale_ring(r,.89),scale_ring(r,.78),base+pod,top-18,0);prism(V,F,M,scale_ring(r,.78),scale_ring(r,.64),top-18,top-5,1);prism(V,F,M,scale_ring(r,.64),scale_ring(r,.48),top-5,top,3)
 elif profile=='civic_twin':
  prism(V,F,M,r,scale_ring(r,.9),base,base+pod,2);mid=base+pod;half=W*.33;gap=max(5,D*.15);left=Vector((-W*.22,0,0));right=Vector((W*.22,0,0));box(V,F,M,c0+left,W*.44,D*.72,mid,top-10,0);box(V,F,M,c0+right,W*.44,D*.72,mid,top-10,0);box(V,F,M,c0,W*.25,D*.5,top-10,top+10,3)
 elif profile=='hotel_podium':
  prism(V,F,M,r,scale_ring(r,.92),base,base+pod,2);prism(V,F,M,scale_ring(r,.88),scale_ring(r,.8),base+pod,top-18,0);prism(V,F,M,scale_ring(r,.8),scale_ring(r,.7),top-18,top-5,1);box(V,F,M,c0,W*.52,D*.52,top-5,top+7,3)
 elif profile=='retail_tower':
  prism(V,F,M,r,scale_ring(r,.94),base,base+pod,2);prism(V,F,M,scale_ring(r,.92),scale_ring(r,.88),base+pod,top-14,0);prism(V,F,M,scale_ring(r,.88),scale_ring(r,.68),top-14,top,3)
 elif profile=='slab_crown':
  prism(V,F,M,r,scale_ring(r,.92),base,base+pod,2);prism(V,F,M,scale_ring(r,.9),scale_ring(r,.86),base+pod,top-10,0);prism(V,F,M,scale_ring(r,.86),scale_ring(r,.62),top-10,top,3)
 elif profile=='hopewell_annex':
  prism(V,F,M,r,scale_ring(r,.94),base,base+pod,2);prism(V,F,M,scale_ring(r,.9),scale_ring(r,.85),base+pod,top-14,0);prism(V,F,M,scale_ring(r,.85),scale_ring(r,.7),top-14,top-4,1);prism(V,F,M,scale_ring(r,.7),scale_ring(r,.5),top-4,top,3)
 mesh=bpy.data.meshes.new('BATCH2_'+str(b['id'])+'_Mesh');mesh.from_pydata(V,[],F);mesh.update();root=bpy.data.objects.new('BATCH2_'+str(b['id'])+'_'+re.sub(r'[^A-Za-z0-9_]+','_',name)[:48],None);coll.objects.link(root);root.location=(c.x,c.y,base);root.rotation_euler[2]=ang;root['osm_id']=str(b['id']);root['name']=name;root['profile']=profile;root['height_m']=h;root['gis_footprint_m']=[round(W,2),round(D,2)];root['basis']='OSM footprint + Lands Department DTM + satellite/GIS-informed massing';me=bpy.data.objects.new(root.name+'_Geometry',mesh);coll.objects.link(me);me.parent=root
 for m in mats:mesh.materials.append(m)
 for i,p in enumerate(mesh.polygons):p.material_index=M[i]
 cu=bpy.data.curves.new(root.name+'_FacadeGrid','CURVE');cu.dimensions='3D';cu.bevel_depth=.045;cu.bevel_resolution=0;cu.materials.append(mats[3])
 for zf in np.arange(base+pod+3,top,3.5):
  for j in range(len(r)):line(cu,(r[j].x,r[j].y,zf),(r[(j+1)%len(r)].x,r[(j+1)%len(r)].y,zf))
 for j in range(len(r)):
  a=r[j];bb=r[(j+1)%len(r)];d=bb-a;cnt=max(2,min(14,int(d.length/6)))
  for q in range(1,cnt):p=a+d*q/cnt;line(cu,(p.x,p.y,base+pod),(p.x,p.y,top))
 co=bpy.data.objects.new(root.name+'_FacadeFrames',cu);coll.objects.link(co);co.parent=root;made.append(root)
# remove any remaining duplicate legacy empties for this batch
ids={str(b['id']) for b in records if b.get('name') in TARGETS}
for o in list(bpy.data.objects):
 if o.name.startswith('Landmark_') and str(o.get('osm_id')) in ids:bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene['batch2_landmark_count']=len(made);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'));print({'created':len(made),'collection':COLL,'names':[o.get('name') for o in made]})
