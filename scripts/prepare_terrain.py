import json, math, sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.prepared import prep
ROOT=Path(__file__).resolve().parents[1]
asc=ROOT/'data/raw/dtm/Whole_HK_DTM_5m.asc'
boundary=shape(json.loads((ROOT/'data/raw/island_geometry.json').read_text(encoding='utf-8')))
tr=Transformer.from_crs('EPSG:4326','EPSG:2326',always_xy=True)
# Transform the OSM boundary bbox to HK1980 metres.
from shapely.ops import transform
b=transform(tr.transform,boundary)
minx,miny,maxx,maxy=b.bounds
# Add a 150m collar for a clean coast context.
minx-=150;miny-=150;maxx+=150;maxy+=150
with rasterio.open(asc) as src:
    win=from_bounds(minx,miny,maxx,maxy,src.transform)
    arr=src.read(1,window=win,out_dtype='float32')
    trans=src.window_transform(win)
print('raw crop',arr.shape,trans)
# DTM is 5m; 25m is a good whole-island working resolution.
step=5
arr=arr[::step,::step]
y=np.array([trans.f + (i*step + 0.5*step)*trans.e for i in range(arr.shape[0])],dtype=np.float32)
x=np.array([trans.c + (j*step + 0.5*step)*trans.a for j in range(arr.shape[1])],dtype=np.float32)
# Convert y ordering to ascending northing; raster rows are north to south.
if y[0] > y[-1]:
    y=y[::-1]; arr=arr[::-1,:]
# Mask cells whose center is on the Hong Kong Island relation.
pg=prep(b)
mask=np.zeros((len(y)-1,len(x)-1),dtype=np.uint8)
for i in range(len(y)-1):
    for j in range(len(x)-1):
        cx=float((x[j]+x[j+1])*0.5);cy=float((y[i]+y[i+1])*0.5)
        mask[i,j]=1 if pg.covers(Point(cx,cy)) else 0
# Clean nodata and clamp for robust mesh generation.
arr=np.where((arr < -1000) | ~np.isfinite(arr),0,arr).astype(np.float32)
# Store local coordinates around the same origin used by the building export.
origin=np.array([840000.,815000.],dtype=np.float32)
np.savez_compressed(ROOT/'data/processed/terrain_hki.npz', x=x-origin[0], y=y-origin[1], z=arr, mask=mask, origin=origin, spacing=25.)
meta={'crs':'EPSG:2326','origin':[840000.,815000.],'spacing_m':25.,'shape':list(arr.shape),'cells_inside':int(mask.sum()),'bbox_hk1980':[float(v) for v in b.bounds]}
(ROOT/'data/processed/terrain_hki_meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta,indent=2))
