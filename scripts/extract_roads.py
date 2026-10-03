import json,re
from pathlib import Path
import osmium
from shapely.geometry import shape, LineString
from shapely.ops import transform
from shapely.prepared import prep
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'data/processed/hki_roads.json'
tr=Transformer.from_crs('EPSG:4326','EPSG:2326',always_xy=True); b=transform(tr.transform,shape(json.loads((ROOT/'data/raw/island_geometry.json').read_text(encoding='utf8')))); pg=prep(b); ox,oy=840000.,815000.
keep={'motorway','trunk','primary','secondary','tertiary','unclassified','residential','living_street','service','pedestrian','track','cycleway'}
class H(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.items=[];self.skip=0
 def way(self,w):
  hw=w.tags.get('highway');
  if hw not in keep:return
  pts=[]
  try:
   for n in w.nodes:
    if n.location.valid():
     x,y=tr.transform(n.lon,n.lat);pts.append((x-ox,y-oy))
  except Exception:self.skip+=1;return
  if len(pts)<2:return
  line_abs=LineString([(x+ox,y+oy) for x,y in pts])
  if not pg.intersects(line_abs):return
  inter=line_abs.intersection(b)
  geoms=list(getattr(inter,'geoms',[inter]))
  for g in geoms:
   if getattr(g,'length',0)<3:continue
   coords=[[round(x-ox,2),round(y-oy,2)] for x,y in g.coords]
   self.items.append({'id':int(w.id),'kind':hw,'name':w.tags.get('name:en') or w.tags.get('name') or '','points':coords})
h=H();h.apply_file(str(ROOT/'data/raw/hong-kong-260929.osm.pbf'),locations=True);out.write_text(json.dumps({'count':len(h.items),'roads':h.items},ensure_ascii=False,separators=(',',':')),encoding='utf8');print('roads',len(h.items),'skips',h.skip,'size',out.stat().st_size)

