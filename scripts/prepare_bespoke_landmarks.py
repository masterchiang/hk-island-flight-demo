"""Create auditable per-landmark GIS inputs; run with project .venv Python."""
import ast, json, math
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data/processed'
rows=json.loads((D/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
T=np.load(D/'terrain_hki.npz')
transform=Transformer.from_crs(2326,4326,always_xy=True)
SOURCES={
 'Jardine House':['https://www.hkland.com/en/properties/hong-kong/jardine-house','https://en.wikipedia.org/wiki/Jardine_House'],
 'Two International Finance Centre':['https://pcparch.com/work/ifc-hong-kong','https://en.wikipedia.org/wiki/International_Finance_Centre_(Hong_Kong)'],
 'Central Plaza':['https://www.centralplaza.com.hk/','https://en.wikipedia.org/wiki/Central_Plaza_(Hong_Kong)'],
 'Lippo Centre Tower 1':['https://www.paulrudolph.institute/198406-lippo'],
 'Lippo Centre Tower 2':['https://www.paulrudolph.institute/198406-lippo']}
HEIGHT={'Jardine House':178.54,'Two International Finance Centre':415.8,'Central Plaza':374.,'Lippo Centre Tower 1':172.,'Lippo Centre Tower 2':186.}
result=[]
for name,sources in SOURCES.items():
 b=next(b for b in rows if b.get('name')==name)
 p=orient(Polygon(b['footprint']),1)
 cx,cy=p.centroid.x,p.centroid.y
 rect=list(p.minimum_rotated_rectangle.exterior.coords)[:4]
 edges=[(rect[(i+1)%4][0]-a[0],rect[(i+1)%4][1]-a[1]) for i,a in enumerate(rect)]
 dx,dy=max(edges,key=lambda v:v[0]**2+v[1]**2)
 angle=math.atan2(dy,dx)%math.pi
 if name.startswith('Lippo'):
  # Cardinal octagon faces, not the unstable minimum rectangle of an octagon.
  edge_candidates=[]
  rr=list(p.exterior.coords)
  for a,bp in zip(rr,rr[1:]):
   dx,dy=bp[0]-a[0],bp[1]-a[1]
   aa=(math.atan2(dy,dx)+math.pi/2)%math.pi-math.pi/2
   edge_candidates.append((abs(aa),aa))
  angle=min(edge_candidates)[1]
 c,s=math.cos(angle),math.sin(angle)
 local=[[(x-cx)*c+(y-cy)*s,-(x-cx)*s+(y-cy)*c] for x,y in list(p.exterior.coords)[:-1]]
 ix=int(np.clip(np.searchsorted(T['x'],cx)-1,0,len(T['x'])-1)); iy=int(np.clip(np.searchsorted(T['y'],cy)-1,0,len(T['y'])-1))
 base=float(T['z'][iy,ix])+.85
 lon,lat=transform.transform(cx+840000,cy+815000)
 result.append(dict(name=name,osm_id=str(b['id']),osm_url=f"https://www.openstreetmap.org/way/{b['id']}",osm_height_m=b['height'],height_m=HEIGHT[name],osm_levels=b['levels'],position=[cx,cy,base],rotation_z=angle,lon_lat=[lon,lat],footprint_local=local,footprint_world=list(p.exterior.coords)[:-1],width=max(v[0] for v in local)-min(v[0] for v in local),depth=max(v[1] for v in local)-min(v[1] for v in local),sources=sources,precision='OSM footprint + 25m-sampled government DTM; heights sourced separately; facade proportions photo-interpreted, not surveyed',height_note='OSM 309m retained as roof datum; official 374m includes mast' if name=='Central Plaza' else 'Architect page gives rounded 420m; retain OSM 415.8m. 88 advertised stories is not a floor-by-floor survey.' if 'International' in name else 'Lippo source fact table reverses tower labels; its narrative agrees with OSM: Tower 2=186m, Tower 1=172m.' if name.startswith('Lippo') else '52 total levels per owner; facade bay layout derived visually.'))
(D/'bespoke_landmark_inputs.json').write_text(json.dumps({'revision':'2026-10-01-B1','crs':'EPSG:2326','origin':[840000,815000],'terrain':'Lands Department DTM, 25m working sample','landmarks':result},indent=2,ensure_ascii=False),encoding='utf8')
queue=[]
for file in ['build_custom_landmarks.py','build_landmark_batch2.py']:
 tree=ast.parse((ROOT/'scripts'/file).read_text(encoding='utf8'))
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TARGETS' for t in node.targets):
   for n in ast.literal_eval(node.value):
    queue.append({'name':n,'status':'building_bespoke_B1' if n in SOURCES else 'needs_reference_and_bespoke_rebuild','source_script':file})
(D/'landmark_upgrade_queue.json').write_text(json.dumps(queue,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps([{'name':b['name'],'height':b['height_m'],'base':b['position'][2],'w':round(b['width'],2),'d':round(b['depth'],2)} for b in result],indent=2))
