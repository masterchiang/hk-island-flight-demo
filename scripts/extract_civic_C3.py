import osmium,json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape,Polygon
from shapely.ops import transform
ROOT=Path.cwd(); tr=Transformer.from_crs(4326,2326,always_xy=True)
def xy(lon,lat):
 x,y=tr.transform(lon,lat);return x-840000,y-815000
class Scan(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.rows=[];self.factory=osmium.geom.GeoJSONFactory()
 def area(self,a):
  tags=dict(a.tags)
  if not any(t in tags for t in ['building','building:part','amenity','landuse']):return
  try:g=shape(json.loads(self.factory.create_multipolygon(a)))
  except:return
  lon,lat=g.representative_point().coords[0]
  if not 114.154<lon<114.18 or not 22.274<lat<22.289:return
  gg=transform(xy,g)
  for k,p in enumerate([gg] if isinstance(gg,Polygon) else gg.geoms):
   self.rows.append({'area_id':int(a.id),'source_id':a.orig_id(),'source_type':'way' if a.from_way() else 'relation','name':tags.get('name:en',tags.get('name','')),'tags':tags,'centroid':list(p.centroid.coords[0]),'footprint':[list(c) for c in p.exterior.coords[:-1]],'holes':[[list(c) for c in ring.coords[:-1]] for ring in p.interiors],'bbox':list(p.bounds),'area_m2':p.area})
s=Scan();s.apply_file(str(ROOT/'data/raw/hong-kong-260929.osm.pbf'),locations=True)
p=ROOT/'research/harbour_C3';p.mkdir(exist_ok=True)
(p/'osm_civic_features.json').write_text(json.dumps(s.rows,ensure_ascii=False,indent=2),encoding='utf8')
for r in s.rows:
 name=r['name'];tags=r['tags'];x,y=r['centroid']
 if any(t in name.lower() for t in ['convention','performing','government','hopewell','council','arts centre','harcourt','east wing','west wing','chief executive']) or (r['area_m2']>1500 and tags.get('building') and -5300<x<-3700 and 650<y<1500):
  print(r['area_id'],r['source_type'],r['source_id'],name,round(r['area_m2']),[round(x,1),round(y,1)],{k:tags[k] for k in ['building','building:part','height','building:levels','amenity'] if k in tags},len(r['footprint']))
print('total',len(s.rows))
