"""Second-batch Exchange Square + Highcliff bespoke generator."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>');DATA=ROOT/'data/processed'
rows=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
TARGETS={'One Exchange Square':65061120,'Two Exchange Square':297109906,'Three Exchange Square':297109900,'Highcliff':130515428}
PROFILES={'One Exchange Square':'exchange','Two Exchange Square':'exchange','Three Exchange Square':'exchange','Highcliff':'highcliff'}
COL='13_Bespoke_Exchange_Highcliff_B2'
def rec(name): return next(b for b in rows if b.get('name')==name and b['id']==TARGETS[name])
def mat(name,color,metal=.4,rough=.3):
 m=bpy.data.materials.get('B2_'+name) or bpy.data.materials.new('B2_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if p:p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
MATS=[mat('ExchangeGlass',(.04,.16,.22),.55,.24),mat('ExchangeFrame',(.52,.58,.56),.65,.28),mat('HighcliffGlass',(.06,.24,.28),.55,.2),mat('Podium',(.16,.18,.18),.15,.55),mat('Accent',(.15,.52,.6),.5,.22)]
def coll():
 c=bpy.data.collections.get(COL)
 if not c:c=bpy.data.collections.new(COL);bpy.context.scene.collection.children.link(c)
 return c
def ring(b):
 p=[Vector((x,y,0)) for x,y in b['footprint']];cx=sum(q.x for q in p)/len(p);cy=sum(q.y for q in p)/len(p);return p,Vector((cx,cy,0))
def local(p,c):
 arr=[Vector((q.x-c.x,q.y-c.y,0)) for q in p];ang=math.atan2(arr[1].y-arr[0].y,arr[1].x-arr[0].x)
 return [Vector((q.x*math.cos(ang)+q.y*math.sin(ang),-q.x*math.sin(ang)+q.y*math.cos(ang),0)) for q in arr],ang
def prism(V,F,r0,r1,z0,z1,mi):
 s=len(V);V.extend([((p.x,p.y) if hasattr(p,'x') else p[0:2])+(z0,) for p in r0]+[((p.x,p.y) if hasattr(p,'x') else p[0:2])+(z1,) for p in r1]);n=len(r0)
 for i in range(n):j=(i+1)%n;F.append((s+i,s+j,s+n+j,s+n+i))
 F.extend([tuple(s+i for i in reversed(range(n))),tuple(s+n+i for i in range(n))])
def add_ring_lines(V,F,r,z0,z1,steps=24):
 for z in [z0+(z1-z0)*i/steps for i in range(1,steps)]:
  s=len(V);V.extend([((p.x,p.y) if hasattr(p,'x') else p[0:2])+(z,) for p in r]);F.append(tuple(s+i for i in range(len(r))))
def build(name):
 b=rec(name);p,c=ring(b);r,ang=local(p,c);h=float(b['height']);base=.85+4.;w=max(q.x for q in r)-min(q.x for q in r);d=max(q.y for q in r)-min(q.y for q in r)
 ccol=coll()
 for o in list(ccol.objects):
  if o.get('landmark_name')==name:bpy.data.objects.remove(o,do_unlink=True)
 root=bpy.data.objects.new('CUSTOM_'+str(b['id'])+'_'+name.replace(' ','_')+'_B2',None);ccol.objects.link(root);root.location=(c.x,c.y,base);root.rotation_euler[2]=ang
 root['landmark_name']=name;root['osm_id']=str(b['id']);root['height_m']=h;root['profile']=PROFILES[name];root['basis']='OSM footprint + DTM base + reference-led bespoke procedural massing';root['precision']='Not photogrammetry'
 V=[];F=[];MI=[];r0=r
 def add(ring0,ring1,z0,z1,mi):
  before=len(F);prism(V,F,ring0,ring1,z0,z1,mi);MI.extend([mi]*(len(F)-before))
 if name!='Highcliff':
  add([(q.x*.98,q.y*.98) for q in r0],r0,0,16,3)
  add(r0,[(q.x*.95,q.y*.95) for q in r0],16,h-9,0)
  add([(q.x*.95,q.y*.95) for q in r0],[(q.x*.82,q.y*.82) for q in r0],h-9,h-3,1)
  add([(q.x*.82,q.y*.82) for q in r0],[(q.x*.65,q.y*.65) for q in r0],h-3,h,4)
 else:
  add([(q.x*.92,q.y*.92) for q in r0],r0,0,10,3)
  add(r0,[(q.x*.90,q.y*.90) for q in r0],10,h-22,2)
  add([(q.x*.90,q.y*.90) for q in r0],[(q.x*.70,q.y*.70) for q in r0],h-22,h-5,0)
  add([(q.x*.70,q.y*.70) for q in r0],[(q.x*.34,q.y*.34) for q in r0],h-5,h,4)
 mesh=bpy.data.meshes.new(root.name+'_Geometry');mesh.from_pydata(V,[],F);mesh.update();ob=bpy.data.objects.new(root.name+'_Geometry',mesh);ccol.objects.link(ob);ob.parent=root
 for m in MATS:mesh.materials.append(m)
 for poly,mi in zip(mesh.polygons,MI):poly.material_index=mi
 # Separate facade frame curve for readable vertical and horizontal rhythm.
 cu=bpy.data.curves.new(root.name+'_FacadeFrames','CURVE');cu.dimensions='3D';cu.bevel_depth=.12 if name!='Highcliff' else .09;cu.materials.append(MATS[1])
 def seg(a,b):sp=cu.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*a,1);sp.points[1].co=(*b,1)
 for i,q in enumerate(r0):seg((q.x,q.y,8),(q.x*.84,q.y*.84,h-4))
 for k in range(1,round(h/(3.4 if name=='Highcliff' else 3.6))):
  z=8+k*(3.4 if name=='Highcliff' else 3.6);s=len(r0)
  for i,q in enumerate(r0):
   n=r0[(i+1)%s];seg((q.x*.92,q.y*.92,z),(n.x*.92,n.y*.92,z))
 fo=bpy.data.objects.new(root.name+'_FacadeFrames',cu);ccol.objects.link(fo);fo.parent=root
 root['feature_note']='Exchange Square: terraced shared podium and stepped crown; Highcliff: very slender residential tower with restrained tapered crown.'
 return {'name':name,'root':root.name,'height':h,'footprint_points':len(r0)}
def build_all():return [build(n) for n in TARGETS]
if __name__=='__main__':print(build_all())


