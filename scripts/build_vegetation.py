"""Standalone Hong Kong Island vegetation module.

Data sources: local Geofabrik OSM snapshot data/raw/hong-kong-260929.osm.pbf
(ODbL; credit OpenStreetMap contributors/Geofabrik), island boundary relation
is discovered from that PBF. Terrain is data/processed/terrain_hki.npz (HK1980
EPSG:2326, local origin 840000,815000 m); road/building buffers use the existing
processed OSM exports. Fixed seed + sorted source IDs make placement repeatable.

Run at repository root (PowerShell):
  .\\.venv\\Scripts\\python.exe scripts\\build_vegetation.py --mode extract
  .\\.venv\\Scripts\\python.exe scripts\\build_vegetation.py --mode sample --seed 260929
  blender --background HKI_Holographic_Atlas.blend --python scripts/build_vegetation.py -- --mode blender --clear --save-as output/HKI_Holographic_Atlas_vegetation.blend
The Blender step touches only HKI_Vegetation_Module and saves a separate copy.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PBF=ROOT/'data/raw/hong-kong-260929.osm.pbf'
VEG=ROOT/'data/processed/hki_vegetation.json'
GEO=ROOT/'data/processed/hki_vegetation.geojson'
PTS=ROOT/'data/processed/hki_vegetation_placements.json'
TERRAIN=ROOT/'data/processed/terrain_hki.npz'
ROADS=ROOT/'data/processed/hki_roads.json'
BUILDINGS=ROOT/'data/processed/hki_buildings.json'
OX,OY=840000.0,815000.0
CLASSES={
 'woodland':(14.,76,'tree',2500),'scrub':(15.,68,'shrub',1100),
 'park':(14.,62,'tree',1000),'golf':(18.,58,'tree',900),
 'grass':(26.,50,'grass',500),'garden':(14.,56,'tree',850),
 'orchard':(12.,54,'tree',900),'wetland':(20.,46,'shrub',700),
 'tree':(9.,100,'tree',1),'tree_row':(8.,96,'tree',240)}

def classify(t):
 n=t.get('natural','').lower(); l=t.get('landuse','').lower()
 q=t.get('leisure','').lower(); c=t.get('landcover','').lower()
 if n=='tree' or t.get('tree','').lower() in ('yes','tree'): return 'tree'
 if n in ('tree_row','tree-row'): return 'tree_row'
 if q=='golf_course': return 'golf'
 if n in ('wood','woodland','forest') or l in ('forest','woodland') or c in ('trees','tree','wood'): return 'woodland'
 if n in ('scrub','shrubbery','heath') or c=='scrub': return 'scrub'
 if n in ('wetland','marsh'): return 'wetland'
 if l in ('orchard','vineyard'): return 'orchard'
 if q in ('park','nature_reserve','common','recreation_ground'): return 'park'
 if q in ('garden','playground') or l in ('garden','allotments','plant_nursery','cemetery','village_green'): return 'garden'
 if n in ('grassland','meadow') or l in ('grass','meadow','greenfield','farmland') or q in ('pitch','sports_centre') or c=='grass': return 'grass'
 return None

def tags_dict(tags): return {str(k):str(v) for k,v in tags}
def json_write(path,obj):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def projected_tools():
 from pyproj import Transformer
 return (Transformer.from_crs('EPSG:4326','EPSG:2326',always_xy=True),Transformer.from_crs('EPSG:2326','EPSG:4326',always_xy=True))
def polygon_parts(g):
 if g.geom_type=='Polygon': return [g]
 if g.geom_type=='MultiPolygon': return list(g.geoms)
 if g.geom_type=='GeometryCollection': return [x for x in g.geoms if x.geom_type=='Polygon']
 return []

def extract(args):
 import osmium
 from shapely.geometry import shape,mapping
 from shapely.ops import transform
 from shapely.prepared import prep
 pbf=Path(args.pbf).resolve()
 if not pbf.is_file(): raise FileNotFoundError(pbf)
 # Discover the named island relation; prefer place=island multipolygon over
 # administrative boundary relation with the same name.
 class Finder(osmium.SimpleHandler):
  def __init__(self): super().__init__(); self.matches=[]
  def relation(self,r):
   t=tags_dict(r.tags); en=t.get('name:en','').lower(); nm=t.get('name','').lower()
   if en=='hong kong island' or ('hong kong island' in nm and t.get('ref')=='HKI'):
    score=(100 if t.get('place')=='island' else 0)+(20 if t.get('type')=='multipolygon' else 0)+(10 if t.get('boundary')=='administrative' else 0)
    self.matches.append((score,int(r.id),t))
 f=Finder(); f.apply_file(str(pbf),locations=False)
 if not f.matches: raise RuntimeError('Hong Kong Island relation not found')
 _,rid,rtags=sorted(f.matches,key=lambda a:(-a[0],a[1]))[0]
 class Boundary(osmium.SimpleHandler):
  def __init__(self): super().__init__(); self.factory=osmium.geom.GeoJSONFactory(); self.geom=None
  def area(self,a):
   if int(a.orig_id())==rid:
    self.geom=shape(json.loads(self.factory.create_multipolygon(a)))
 b=Boundary(); b.apply_file(str(pbf),locations=True)
 if b.geom is None: raise RuntimeError('Boundary relation geometry was not assembled')
 tolocal,togeo=projected_tools(); boundary=transform(tolocal.transform,b.geom); prepared=prep(boundary)
 wanted={'natural','landuse','leisure','landcover','green','vegetation','tree','species','denotation','name','name:en'}
 features=[]; skipped=0
 def add(g,kind,sid,t,veg):
  nonlocal skipped
  try:
   if g.is_empty or not prepared.intersects(g): return
   g=g.intersection(boundary)
   if kind=='area': parts=polygon_parts(g)
   elif g.geom_type in ('MultiLineString','GeometryCollection'): parts=[x for x in g.geoms if x.geom_type in ('LineString','Point')]
   else: parts=[g] if not g.is_empty else []
   for i,part in enumerate(parts):
    if kind=='area' and part.area<2: continue
    if kind=='way' and part.length<1: continue
    local=transform(lambda x,y,z=None:(x-OX,y-OY),part)
    if kind=='area': local=local.simplify(.4,preserve_topology=True)
    wgs=transform(togeo.transform,part)
    features.append({'id':f'{kind}/{sid}/{i}','source_kind':kind,'source_id':int(sid),'part':i,'veg_type':veg,
      'tags':{k:v for k,v in t.items() if k in wanted},'geometry':mapping(local),'geometry_wgs84':mapping(wgs),
      'bbox':[round(float(v),3) for v in local.bounds], 'area_m2':round(float(part.area),2),
      'length_m':round(float(part.length),2),'default_spacing_m':CLASSES[veg][0], 'priority':CLASSES[veg][1], 'mesh_family':CLASSES[veg][2]})
  except Exception: skipped+=1
 class Vegetation(osmium.SimpleHandler):
  def __init__(self): super().__init__(); self.factory=osmium.geom.GeoJSONFactory()
  def area(self,a):
   t=tags_dict(a.tags); veg=classify(t)
   if not veg or veg=='tree': return
   try: add(transform(tolocal.transform,shape(json.loads(self.factory.create_multipolygon(a)))),'area',a.orig_id(),t,veg)
   except Exception: pass
  def node(self,n):
   t=tags_dict(n.tags)
   if classify(t)!='tree' or not n.location.valid(): return
   try:
    from shapely.geometry import Point
    x,y=tolocal.transform(float(n.lon),float(n.lat)); add(Point(x,y),'node',n.id,t,'tree')
   except Exception: pass
  def way(self,w):
   t=tags_dict(w.tags)
   if classify(t)!='tree_row' or w.is_closed(): return
   try:
    from shapely.geometry import LineString
    xy=[]
    for n in w.nodes:
     if n.location.valid(): xy.append(tolocal.transform(float(n.lon),float(n.lat)))
    if len(xy)>1: add(LineString(xy),'way',w.id,t,'tree_row')
   except Exception: pass
 v=Vegetation(); v.apply_file(str(pbf),locations=True)
 features.sort(key=lambda x:(x['veg_type'],x['source_kind'],x['source_id'],x['part']))
 counts=dict(sorted(Counter(x['veg_type'] for x in features).items()))
 meta={'module':'hki_vegetation','version':'1.0.0','source_pbf':pbf.name,'source_sha256':sha256(pbf),
  'source_date':'2026-09-29','license':'OpenStreetMap contributors / Geofabrik; ODbL',
  'boundary_relation_id':rid,'boundary_name':rtags.get('name:en','Hong Kong Island'),
  'boundary_tags':{k:rtags[k] for k in ('name:en','place','type','ref') if k in rtags},
  'crs':'EPSG:2326','wgs84_crs':'EPSG:4326','local_origin':[OX,OY],
  'feature_count':len(features),'feature_counts':counts,'skipped_geometries':skipped,
  'placement_seed_default':260929,'note':'Area features clipped to OSM island multipolygon; OSM attribution required.'}
 local_boundary=mapping(transform(lambda x,y,z=None:(x-OX,y-OY),boundary))
 clean=[{k:x for k,x in f.items() if k!='geometry_wgs84'} for f in features]
 json_write(args.out_json,{'meta':meta,'boundary':local_boundary,'features':clean})
 gj={'type':'FeatureCollection','name':'Hong Kong Island vegetation','crs':{'type':'name','properties':{'name':'EPSG:4326'}},'features':[
  {'type':'Feature','id':f['id'],'properties':{k:f[k] for k in ('veg_type','source_kind','source_id','area_m2','length_m','tags')},'geometry':f['geometry_wgs84']} for f in features]}
 json_write(args.out_geojson,gj)
 print(json.dumps({'boundary_relation_id':rid,'features':len(features),'counts':counts,'json':str(args.out_json),'geojson':str(args.out_geojson)},indent=2))
 return {'meta':meta,'features':clean,'boundary':local_boundary}

class SegmentGrid:
 def __init__(self,cell=80.): self.cell=float(cell); self.cells=defaultdict(list)
 def key(self,x,y): return (math.floor(x/self.cell),math.floor(y/self.cell))
 def add(self,ax,ay,bx,by):
  sx=(ax,ay,bx,by); c0=self.key(min(ax,bx),min(ay,by)); c1=self.key(max(ax,bx),max(ay,by))
  for ix in range(c0[0],c1[0]+1):
   for iy in range(c0[1],c1[1]+1): self.cells[(ix,iy)].append(sx)
 def nearest(self,x,y,r=90.):
  c0=self.key(x-r,y-r); c1=self.key(x+r,y+r); best=r
  for ix in range(c0[0],c1[0]+1):
   for iy in range(c0[1],c1[1]+1):
    for ax,ay,bx,by in self.cells.get((ix,iy),[]):
     dx=bx-ax; dy=by-ay
     if dx==0 and dy==0: d=math.hypot(x-ax,y-ay)
     else:
      q=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
      d=math.hypot(x-(ax+q*dx),y-(ay+q*dy))
     if d<best: best=d
  return best

def load_indexes():
 roads=SegmentGrid(); buildings=SegmentGrid()
 if Path(ROADS).exists():
  for r in json.loads(Path(ROADS).read_text(encoding='utf8')).get('roads',[]):
   for a,b in zip(r.get('points',[]),r.get('points',[])[1:]): roads.add(float(a[0]),float(a[1]),float(b[0]),float(b[1]))
 if Path(BUILDINGS).exists():
  for bld in json.loads(Path(BUILDINGS).read_text(encoding='utf8')).get('buildings',[]):
   ring=bld.get('footprint',[])
   for a,b in zip(ring,ring[1:]+ring[:1]): buildings.add(float(a[0]),float(a[1]),float(b[0]),float(b[1]))
 return roads,buildings

class Terrain:
 def __init__(self,path):
  import numpy as np
  a=np.load(path); self.x=np.asarray(a['x'],float); self.y=np.asarray(a['y'],float); self.z=np.asarray(a['z'],float); self.mask=np.asarray(a['mask'],np.uint8); self.step=float(a['spacing'])
 def idx(self,x,y):
  import numpy as np
  x=max(float(self.x[0]),min(float(self.x[-1]),x)); y=max(float(self.y[0]),min(float(self.y[-1]),y))
  ix=max(0,min(int(np.searchsorted(self.x,x,'right')-1),len(self.x)-2)); iy=max(0,min(int(np.searchsorted(self.y,y,'right')-1),len(self.y)-2))
  tx=(x-self.x[ix])/max(self.x[ix+1]-self.x[ix],1e-6); ty=(y-self.y[iy])/max(self.y[iy+1]-self.y[iy],1e-6)
  return ix,iy,tx,ty
 def inside(self,x,y):
  ix,iy,_,_=self.idx(x,y); return iy<self.mask.shape[0] and ix<self.mask.shape[1] and bool(self.mask[iy,ix])
 def height(self,x,y):
  ix,iy,tx,ty=self.idx(x,y); z=self.z
  return float((1-ty)*((1-tx)*z[iy,ix]+tx*z[iy,ix+1])+ty*((1-tx)*z[iy+1,ix]+tx*z[iy+1,ix+1]))
 def slope(self,x,y):
  s=max(self.step,1.); return math.degrees(math.atan(math.hypot((self.height(x+s,y)-self.height(x-s,y))/(2*s),(self.height(x,y+s)-self.height(x,y-s))/(2*s))))

def ring_inside(x,y,ring):
 inside=False; j=len(ring)-1
 for i in range(len(ring)):
  xi,yi=ring[i][:2]; xj,yj=ring[j][:2]
  if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/max(yj-yi,1e-12)+xi: inside=not inside
  j=i
 return inside
def geom_inside(x,y,g):
 t=g.get('type'); c=g.get('coordinates',[])
 if t=='Point': return math.hypot(x-c[0],y-c[1])<.5
 if t=='Polygon': return bool(c) and ring_inside(x,y,c[0]) and not any(ring_inside(x,y,h) for h in c[1:])
 if t=='MultiPolygon': return any(geom_inside(x,y,{'type':'Polygon','coordinates':p}) for p in c)
 return False
def env_factor(kind,slope,rd,bd):
 rp=max(0.,min(1.,1-rd/70.)); bp=max(0.,min(1.,1-bd/65.))
 if kind in ('park','garden','grass','golf'): f=.84+.20*rp-.62*bp
 elif kind in ('woodland','scrub','wetland','orchard'): f=.92-.18*rp-.70*bp
 else: f=1.
 limit=20. if kind in ('park','garden','grass','golf') else (28. if kind=='orchard' else 42.)
 f*=max(.2,min(1.,1-max(0.,slope-limit)/35.)); return max(.05,min(1.,f))
def spacing_ok(x,y,spacing,grid):
 cell=max(spacing*.65,4.); k=(math.floor(x/cell),math.floor(y/cell))
 for ix in range(k[0]-1,k[0]+2):
  for iy in range(k[1]-1,k[1]+2):
   if any(math.hypot(x-a,y-b)<spacing*.48 for a,b in grid.get((ix,iy), [])): return False
 grid.setdefault(k,[]).append((x,y)); return True

def sample(args,data=None):
 if data is None: data=json.loads(Path(args.vegetation_json).read_text(encoding='utf8'))
 terrain=Terrain(args.terrain); roads,buildings=load_indexes(); rng=random.Random(int(args.seed)); accepted={}; by_type=defaultdict(list); total=0
 budgets={'tree':2500,'tree_row':2800,'woodland':42000,'scrub':9000,'park':4800,'golf':1500,'grass':1800,'garden':2600,'orchard':2200,'wetland':900}
 fs=sorted(data.get('features',[]),key=lambda f:(-int(f.get('priority',0)),f.get('veg_type',''),f.get('id','')))
 for f in fs:
  kind=f['veg_type']; budget=min(budgets.get(kind,500),int(args.max_instances)); left=min(budget-len(by_type[kind]),int(args.max_instances)-total)
  if left<=0: continue
  sp=float(CLASSES.get(kind,(float(f.get('default_spacing_m',30.)),))[0]);
  if kind=='tree': target=1
  elif kind=='tree_row': target=min(int(f.get('length_m',0)/8)+1,int(CLASSES[kind][3]))
  else:
   density={'woodland':.78,'scrub':.62,'park':.32,'golf':.28,'grass':.30,'garden':.25,'orchard':.58,'wetland':.32}.get(kind,.58)
   target=min(int(round(float(f.get('area_m2',0))/(sp*sp)*density*float(args.density_scale))),int(CLASSES[kind][3]))
  target=min(target,left)
  if target<=0: continue
  g=f['geometry']; placed=[]; gtype=g.get('type')
  if f.get('source_kind')=='way' and gtype=='LineString':
   pts=g.get('coordinates',[])
   for a,b in zip(pts,pts[1:]):
    ax,ay=a; bx,by_=b; n=max(1,int(math.ceil(math.hypot(bx-ax,by_-ay)/sp)))
    for i in range(n+1):
     t=(i+.37*rng.random())/n; x=ax+(bx-ax)*t; y=ay+(by_-ay)*t
     if terrain.inside(x,y) and buildings.nearest(x,y)>=7 and spacing_ok(x,y,sp,accepted):
      placed.append((x,y))
  else:
   box=f.get('bbox',[0,0,0,0]); tries=0
   while len(placed)<target and tries<max(80,target*48):
    tries+=1; x=rng.uniform(box[0],box[2]); y=rng.uniform(box[1],box[3])
    if not geom_inside(x,y,g) or not terrain.inside(x,y): continue
    sl=terrain.slope(x,y); rd=roads.nearest(x,y); bd=buildings.nearest(x,y)
    if rng.random()>env_factor(kind,sl,rd,bd) or bd<(7 if kind in ('tree','tree_row') else 4) or not spacing_ok(x,y,sp,accepted): continue
    placed.append((x,y))
  for x,y in placed[:left]:
   sl=terrain.slope(x,y); by_type[kind].append({'x':round(x,3),'y':round(y,3),'z':round(terrain.height(x,y),3),'veg_type':kind,'mesh_family':CLASSES[kind][2],'slope_deg':round(sl,2),'road_distance_m':round(roads.nearest(x,y),2),'building_distance_m':round(buildings.nearest(x,y),2),'source_feature':f['id']}); total+=1
 pts=[]
 for kind in sorted(by_type): pts.extend(by_type[kind])
 pts.sort(key=lambda p:(p['veg_type'],p['x'],p['y'],p['source_feature']))
 result={'meta':{'module':'hki_vegetation','version':'1.0.0','seed':int(args.seed),'density_scale':float(args.density_scale),'max_instances':int(args.max_instances),'placement_count':len(pts),'placement_counts':dict(sorted(Counter(p['veg_type'] for p in pts).items())),'mesh_strategy':'one merged mesh object per vegetation class; no per-tree Blender objects','terrain':str(Path(args.terrain).resolve()),'rules':['terrain mask','slope','road distance','building distance','deterministic spacing']},'placements':pts}
 json_write(args.placements_json,result); print(json.dumps({'placements':len(pts),'counts':result['meta']['placement_counts'],'output':str(args.placements_json)},indent=2)); return result


def mat(bpy,name,color):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True; n=m.node_tree.nodes; l=m.node_tree.links; n.clear(); o=n.new('ShaderNodeOutputMaterial'); p=n.new('ShaderNodeBsdfPrincipled'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=.9; l.new(p.outputs['BSDF'],o.inputs['Surface']); m.diffuse_color=(*color,1); return m

def octa(v,f,mi,x,y,z,rx,ry,rz,ang):
 s=len(v); ca,sa=math.cos(ang),math.sin(ang); v += [(x,y,z+rz),(x,y,z-rz),(x+rx*ca,y+rx*sa,z),(x-rx*ca,y-rx*sa,z),(x-ry*sa,y+ry*ca,z),(x+ry*sa,y-ry*ca,z)]
 f += [(s,s+2,s+4),(s,s+4,s+3),(s,s+3,s+5),(s,s+5,s+2),(s+1,s+4,s+2),(s+1,s+3,s+4),(s+1,s+5,s+3),(s+1,s+2,s+5)]; mi += [0]*8

def prism(v,f,mi,x,y,z,h,r):
 s=len(v); sides=5
 for i in range(sides):
  a=math.tau*i/sides; v.append((x+r*math.cos(a),y+r*math.sin(a),z))
 for i in range(sides):
  a=math.tau*i/sides; v.append((x+r*.72*math.cos(a),y+r*.72*math.sin(a),z+h))
 for i in range(sides):
  j=(i+1)%sides; f.append((s+i,s+j,s+sides+j,s+sides+i)); mi.append(3)

def merged_object(bpy,collection,name,points,family,seed):
 v=[]; f=[]; mi=[]; rng=random.Random(seed)
 if family=='grass': colors=[(.30,.48,.14),(.42,.56,.17),(.22,.39,.11)]; trunk=None
 elif family=='shrub': colors=[(.16,.34,.10),(.25,.44,.12),(.34,.50,.17)]; trunk=None
 else: colors=[(.12,.28,.09),(.18,.38,.12),(.28,.45,.16)]; trunk=mat(bpy,'HKI_Veg_'+name+'_Trunk',(.20,.13,.06))
 mats=[mat(bpy,'HKI_Veg_'+name+'_Leaf_'+str(i),c) for i,c in enumerate(colors)]
 if trunk: mats.append(trunk)
 for p in points:
  x,y,z=float(p['x']),float(p['y']),float(p['z'])
  if family=='grass':
   s=len(v); h=rng.uniform(.35,.9); w=rng.uniform(.1,.22); a=rng.random()*math.tau; ca,sa=math.cos(a),math.sin(a); v += [(x-w*ca,y-w*sa,z+.03),(x+w*ca,y+w*sa,z+.03),(x+.03*ca,y+.03*sa,z+h),(x-w*sa,y+w*ca,z+.03),(x+w*sa,y-w*ca,z+.03),(x-.02*sa,y+.02*ca,z+h*.92)]; f += [(s,s+1,s+2),(s+3,s+4,s+5)]; mi += [int(rng.random()*len(colors))]*2
  elif family=='shrub':
   a=rng.random()*math.tau; s=rng.uniform(.75,1.35); octa(v,f,mi,x,y,z+.85*s,.95*s,.75*s,.75*s,a); octa(v,f,mi,x+.45*s,y-.2*s,z+.72*s,.65*s,.55*s,.6*s,-a)
  else:
   h={'woodland':9,'tree':8,'tree_row':7,'park':6.5,'garden':5.5,'golf':5,'orchard':4.5}.get(p['veg_type'],6)*rng.uniform(.78,1.22); prism(v,f,mi,x,y,z+.12,.48*h,max(.08,.035*h)); a=rng.random()*math.tau; octa(v,f,mi,x,y,z+.12+.58*h,.56*h,.49*h,.45*h,a); octa(v,f,mi,x+math.cos(a)*h*.14,y+math.sin(a)*h*.14,z+.12+.76*h,.48*h,.42*h,.40*h,-a*.7); octa(v,f,mi,x-math.cos(a)*h*.12,y-math.sin(a)*h*.12,z+.12+.90*h,.39*h,.36*h,.34*h,a*.4)
 mesh=bpy.data.meshes.new(name+'_MergedMesh'); mesh.from_pydata(v,[],f); mesh.update()
 for m in mats: mesh.materials.append(m)
 for poly,idx in zip(mesh.polygons,mi): poly.material_index=idx
 obj=bpy.data.objects.new(name,mesh); collection.objects.link(obj); obj['module']='hki_vegetation'; obj['instance_count']=len(points); obj['geometry_strategy']='merged low-poly mesh; no per-instance Blender objects'; obj['source']='OSM clipped features + terrain_hki.npz'; obj['mesh_family']=family; return obj

def clear_module(bpy,scene,name,clear):
 old=bpy.data.collections.get(name)
 if old and clear:
  for o in list(old.objects): bpy.data.objects.remove(o,do_unlink=True)
  for parent in list(bpy.data.collections):
   if any(child.name==old.name for child in parent.children): parent.children.unlink(old)
  bpy.data.collections.remove(old); old=None
 c=old or bpy.data.collections.new(name)
 if all(child is not c for child in scene.collection.children): scene.collection.children.link(c)
 return c

def blender_build(args):
 import bpy
 data=json.loads(Path(args.vegetation_json).read_text(encoding='utf8'))
 placements=sample(args,data)
 c=clear_module(bpy,bpy.context.scene,args.collection_name,args.clear)
 c['module']='hki_vegetation'; c['source_pbf']=data['meta'].get('source_pbf','hong-kong-260929.osm.pbf'); c['terrain']=str(Path(args.terrain).resolve()); c['seed']=int(args.seed); c['placement_count']=len(placements['placements']); c['crs']='EPSG:2326'; c['local_origin']=f'{OX},{OY}'
 by=defaultdict(list)
 for p in placements['placements']: by[CLASSES[p['veg_type']][2]].append(p)
 made=[]
 for fam in ('tree','shrub','grass'):
  if by[fam]: made.append(merged_object(bpy,c,'HKI_Vegetation_'+fam.title()+'_Merged',by[fam],fam,int(args.seed)+len(made)*101))
 summary={'collection':c.name,'objects_created':[o.name for o in made],'placement_count':len(placements['placements']),'placement_counts':placements['meta']['placement_counts'],'placements_json':str(Path(args.placements_json).resolve())}
 if args.save_as:
  out=Path(args.save_as).resolve(); out.parent.mkdir(parents=True,exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(out)); summary['saved_as']=str(out)
 print(json.dumps(summary,indent=2)); return summary

def parser():
 p=argparse.ArgumentParser(); p.add_argument('--mode',choices=('extract','sample','blender','all'),default='extract'); p.add_argument('--pbf',default=str(PBF)); p.add_argument('--out-json',dest='out_json',default=str(VEG)); p.add_argument('--out-geojson',dest='out_geojson',default=str(GEO)); p.add_argument('--vegetation-json',dest='vegetation_json',default=str(VEG)); p.add_argument('--placements-json',dest='placements_json',default=str(PTS)); p.add_argument('--terrain',default=str(TERRAIN)); p.add_argument('--seed',type=int,default=260929); p.add_argument('--density-scale',type=float,default=1.0); p.add_argument('--max-instances',type=int,default=80000); p.add_argument('--collection-name',default='HKI_Vegetation_Module'); p.add_argument('--clear',action='store_true'); p.add_argument('--save-as',default=''); return p

def main():
 argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=parser().parse_args(argv)
 if a.mode=='extract': extract(a)
 elif a.mode=='sample': sample(a)
 elif a.mode=='all': sample(a,extract(a))
 else: blender_build(a)
if __name__=='__main__': main()



