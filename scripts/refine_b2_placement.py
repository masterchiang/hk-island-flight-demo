import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>'); DATA=ROOT/'data/processed'
records=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings'];T=np.load(DATA/'terrain_hki.npz');TX,TY,TZ=T['x'],T['y'],T['z']
IDS=['590814694','2762122396','296457776','297109890','200915642','52869536','65061120','297109906','297109900','130515428']

def source(oid):return next(b for b in records if str(b['id'])==oid)
def centroid_and_height(b):
 pts=np.array(b['footprint'],dtype=float)
 a=pts[:,0]*np.roll(pts[:,1],-1)-np.roll(pts[:,0],-1)*pts[:,1]
 ar=a.sum()/2.0
 if abs(ar)<1e-6: x,y=pts[:,0].mean(),pts[:,1].mean()
 else: x=((pts[:,0]+np.roll(pts[:,0],-1))*a).sum()/(6*ar); y=((pts[:,1]+np.roll(pts[:,1],-1))*a).sum()/(6*ar)
 ix=int(np.clip(np.searchsorted(TX,x)-1,0,len(TX)-1));iy=int(np.clip(np.searchsorted(TY,y)-1,0,len(TY)-1))
 return x,y,float(TZ[iy,ix])+.85,pts

def points(o):
 out=[]
 if o.type=='MESH':out.extend(o.matrix_world@Vector(v) for v in o.bound_box)
 elif o.type=='CURVE':
  for sp in o.data.splines:
   if sp.type=='POLY':out.extend(o.matrix_world@Vector((p.co.x,p.co.y,p.co.z)) for p in sp.points)
 for c in o.children:out.extend(points(c))
 return out

def refresh():bpy.context.view_layer.update()
roots=[]
for o in bpy.data.objects:
 oid=str(o.get('osm_id',''))
 nm=o.name
 isroot=o.type=='EMPTY' and oid in IDS and ('B2' in nm or nm.startswith(('BESPOKE_B2_2762122396','CUSTOM_590814694_HSBC','CUSTOM_200915642_One_Island_East','CUSTOM_297109890_IFC1_')))
 if isroot:roots.append(o)

reports=[]
for r in roots:
 oid=str(r['osm_id']);b=source(oid);x,y,ground,poly=centroid_and_height(b)
 # Enforce survey centroid placement; building's custom profile orientation remains intact.
 r.location.x=x;r.location.y=y
 # Bring legacy models to cadastral terrain elevation before controlling roof height.
 r.location.z=0.0;refresh();p=points(r)
 lo=min(q.z for q in p);hi=max(q.z for q in p);current=hi-lo;target=float(b.get('height') or r.get('height_m') or r.get('height_m_osm') or current)
 if oid=='2762122396':
  # Circular Hopewell shaft: enlarge its undersized custom shell to the GIS envelope.
  r.scale.x*=1.16;r.scale.y*=1.29
 if oid=='296457776':
  # The Center’s first pass used bbox radii, overshooting its GIS envelope.
  r.scale.x*=.77;r.scale.y*=.77
 if oid=='297109890':
  # IFC1 tower envelope in first pass was only 80% of its footprint; use 94%.
  r.scale.x*=1.175;r.scale.y*=1.175
 if oid=='52869536':
  # Fit the curved Henderson hero form to the OSM principal-axis rectangle.
  pts=poly-np.array([x,y]);cov=np.cov(pts.T);vals,vecs=np.linalg.eigh(cov);axis=vecs[:,np.argmax(vals)];angle=math.atan2(float(axis[1]),float(axis[0]))
  # GIS principal-axis envelope for Henderson is approximately 47.0m x 39.29m.
  r.rotation_euler[2]=angle;r.scale.x*=47.0/53.63;r.scale.y*=39.29/34.99
 # Fix roof datum precisely, including modules whose modeled cap extended past nominal height.
 p=points(r);lo=min(q.z for q in p);hi=max(q.z for q in p);cur=hi-lo
 if cur>1e-6:r.scale.z*=target/cur
 refresh();p=points(r);lo=min(q.z for q in p);hi=max(q.z for q in p)
 r.location.z += ground-lo;refresh();p=points(r);lo=min(q.z for q in p);hi=max(q.z for q in p)
 r.hide_render=False;r.hide_viewport=False;r.hide_set(False)
 for child in r.children_recursive:child.hide_render=False;child.hide_viewport=False;child.hide_set(False)
 r['height_m']=target;r['dtm_ground_m']=ground;r['placement_refined']='OSM polygon area centroid + Lands Department 25m DTM sample + 0.85m clearance';r['roof_height_check_m']=hi-lo
 # visible GIS scale bounds
 xs=[q.x for q in p];ys=[q.y for q in p]
 reports.append({'name':r.get('name',r.get('landmark_name',b.get('name'))),'osm_id':oid,'root':r.name,'ground':ground,'roof':hi,'model_height':hi-lo,'target_height':target,'xy_scale':[r.scale.x,r.scale.y],'world_bbox':[max(xs)-min(xs),max(ys)-min(ys)],'children':len(r.children_recursive)})

# Hide every replaced old independent/prior custom hierarchy, recursively; BOC remains protected.
keep=set()
for r in roots:keep.add(r.name);keep.update(c.name for c in r.children_recursive)
for o in list(bpy.data.objects):
 if str(o.get('osm_id','')) in IDS and o.name not in keep:
  for q in [o]+list(o.children_recursive):
   if q.name.startswith('SKETCHFAB_Bank_of_China_Tower_Primary'):continue
   q.hide_render=True;q.hide_viewport=True;q.hide_set(True);q['superseded_by_second_batch']=True

summary={'revision':'2026-10-01-B2-final','roots':reports,'root_count':len(roots),'expected_root_count':10,'missing_ids':sorted(set(IDS)-{str(o['osm_id']) for o in roots}),'boc_exists':bool(bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary')),'boc_hidden':bool(bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary').hide_render) if bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary') else None}
(DATA/'second_batch_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
bpy.context.scene['second_batch_revision']='2026-10-01-B2-final';bpy.context.scene['second_batch_root_count']=len(roots);bpy.context.scene['second_batch_validation']='Final roots aligned to polygon centroids and DTM; old duplicates hidden recursively; BOC preserved.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(json.dumps(summary,ensure_ascii=False))
