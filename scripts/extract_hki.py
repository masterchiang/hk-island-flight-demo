import json, math, re, sys
from collections import Counter
from pathlib import Path
import osmium
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import transform
from shapely.prepared import prep
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
PBF=ROOT/'data/raw/hong-kong-260929.osm.pbf'
BOUNDARY=ROOT/'data/raw/island_geometry.json'
OUT=ROOT/'data/processed/hki_buildings.json'
OUT.parent.mkdir(parents=True, exist_ok=True)
origin_x, origin_y = 840000.0, 815000.0
tr=Transformer.from_crs('EPSG:4326','EPSG:2326',always_xy=True)
raw=shape(json.loads(BOUNDARY.read_text(encoding='utf-8')))
boundary=transform(tr.transform,raw)
prepared=prep(boundary)

def fnum(s):
    if s is None:return None
    s=str(s).strip().lower().replace('m','').replace(',','')
    m=re.search(r'[-+]?\d+(?:\.\d+)?',s)
    try:return float(m.group(0)) if m else None
    except:return None

def levels(t):
    for k in ('building:levels','levels','building:levels:aboveground'):
        v=fnum(t.get(k))
        if v is not None and 0 < v < 300:return v
    return None

def height(t):
    for k in ('height','building:height','building:levels:height'):
        v=fnum(t.get(k))
        if v is not None and 1 <= v <= 1000:return v
    return None

def estimate(t, area):
    h=height(t)
    lv=levels(t)
    if h is not None:return max(2.5,min(500.0,h))
    if lv is not None:return max(3.0,min(450.0,lv*3.15))
    typ=t.get('building','yes')
    base={'house':7.5,'semidetached_house':7.5,'terrace':9,'hut':3.5,'shed':3.5,'roof':3,
          'apartments':36,'residential':18,'dormitory':30,'hotel':35,'office':24,'commercial':15,
          'retail':10,'industrial':9,'warehouse':8,'school':10,'hospital':14,'university':14,
          'civic':12,'public':12,'church':15,'temple':12,'stadium':14}.get(typ,8.0)
    # Approximate untagged buildings by footprint; this is intentionally conservative.
    if typ in ('yes','residential') and area>2000: base=max(base,18)
    if typ in ('yes','residential') and area>8000: base=max(base,28)
    return base

def clean_ring(poly):
    # exterior only; preserve the source outline but remove repeated last point
    pts=[]
    for x,y in list(poly.exterior.coords)[:-1]:
        if math.isfinite(x) and math.isfinite(y): pts.append([round(x-origin_x,3),round(y-origin_y,3)])
    if len(pts)>=3:
        return pts
    return None

class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.items=[]; self.count=0; self.skipped=0; self.types=Counter(); self.named=[]
        self.factory=osmium.geom.GeoJSONFactory()
    def area(self,a):
        t=dict(a.tags)
        if 'building' not in t:return
        try:
            gj=json.loads(self.factory.create_multipolygon(a)); g=shape(gj)
        except Exception:
            self.skipped+=1; return
        if g.is_empty:return
        g=transform(tr.transform,g)
        geoms=[]
        if isinstance(g,Polygon): geoms=[g]
        elif isinstance(g,MultiPolygon): geoms=list(g.geoms)
        else:
            geoms=[x for x in getattr(g,'geoms',[]) if isinstance(x,Polygon)]
        for p in geoms:
            if p.is_empty or p.area < 1:continue
            rp=p.representative_point()
            if not prepared.covers(rp):continue
            pp=p
            area=pp.area
            if area < 4:continue
            # Keep manageable but detailed outlines; 0.25m tolerance is below the visual scale.
            pp=pp.simplify(0.25,preserve_topology=True)
            ring=clean_ring(pp)
            if not ring:continue
            levels_v=levels(t); height_v=estimate(t,area)
            rec={'id':int(a.id),'footprint':ring,'height':round(height_v,2),'levels':round(levels_v,1) if levels_v else None,
                 'kind':t.get('building','yes'),'area':round(area,2)}
            if t.get('name:en') or t.get('name'):
                rec['name']=(t.get('name:en') or t.get('name'))[:120]
            self.items.append(rec); self.types[t.get('building','yes')]+=1; self.count+=1
            if rec.get('name') and len(self.named)<100:self.named.append(rec)

h=Handler(); print('Reading',PBF,flush=True);h.apply_file(str(PBF),locations=True);print('Raw HKI buildings',h.count,'skipped',h.skipped,flush=True)
# Stable sort gives deterministic output and easier chunking.
h.items.sort(key=lambda x:(x['footprint'][0][0],x['footprint'][0][1],x['id']))
meta={'source_pbf':'hong-kong-260929.osm.pbf','source_date':'2026-09-29','boundary':'OSM Hong Kong Island relation 4556901','crs':'EPSG:2326 local HK1980 metres','origin':[origin_x,origin_y],'count':len(h.items),'types':h.types.most_common(30),'named':h.named}
OUT.write_text(json.dumps({'meta':meta,'buildings':h.items},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False,indent=2))
print('Wrote',OUT,OUT.stat().st_size/1e6,'MB',flush=True)

