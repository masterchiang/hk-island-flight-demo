import requests,concurrent.futures,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
urls={'hong-kong-260929.osm.pbf':'https://download.geofabrik.de/asia/china/hong-kong-260929.osm.pbf','Whole_HK_DTM_5m.zip':'https://www.landsd.gov.hk/landsd_psi_data/SMO/data/Whole_HK_DTM_5m.zip'}
def download(item):
 name,url=item;p=ROOT/'data/raw'/name
 if p.exists():print('CACHED',name,flush=True);return
 try:
  with requests.get(url,stream=True,timeout=(20,120)) as r:
   r.raise_for_status();print('START',name,r.headers.get('Content-Length'),flush=True)
   with p.with_suffix(p.suffix+'.part').open('wb') as f:
    size=0;prev=time.time()
    for chunk in r.iter_content(1024*1024):
     f.write(chunk);size+=len(chunk)
     if time.time()-prev>8:print('PROGRESS',name,round(size/1e6,1),'MB',flush=True);prev=time.time()
   p.with_suffix(p.suffix+'.part').rename(p);print('DONE',name,size,flush=True)
 except Exception as e:print('FAILED',name,str(e),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(download,urls.items()))
