import bpy, json, math
from pathlib import Path
from mathutils import Vector
import bmesh
ROOT=Path(r'<PROJECT_ROOT>'); DATA=ROOT/'data/processed'
rows=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf8'))['buildings']; byid={str(b['id']):b for b in rows}
# Named/tall bespoke roots define protected cadastral footprints.
ids=set()
for c in bpy.data.collections:
 if c.name in {'09_Custom_Landmarks','10_Custom_Landmarks_Batch2','12_Bespoke_Landmarks_B1','12_Bespoke_Landmarks_B2','13_Bespoke_Landmarks_B2_Hopewell','13_Bespoke_The_Center_B2','13_Bespoke_Exchange_Highcliff_B2','CUSTOM_297109890_IFC1_B2','CUSTOM_52869536_HENDERSON_B2'}:
  for o in c.objects:
   if o.type=='EMPTY' and o.get('osm_id') is not None: ids.add(str(o['osm_id']))
# Include Sketchfab BOC footprint and the named 24m BOC building only if their geometry is not the primary model.
ids.update(['51209520','51209520'])

def xy(points): return [(float(x),float(y)) for x,y in points]
def inside(x,y,poly):
 hit=False;j=len(poly)-1
 for i,(xi,yi) in enumerate(poly):
  xj,yj=poly[j]
  if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/(yj-yi+1e-12)+xi: hit=not hit
  j=i
 return hit
def segdist(x,y,a,b):
 ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay;den=dx*dx+dy*dy
 t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/den)) if den else 0
 qx=ax+t*dx;qy=ay+t*dy
 return math.hypot(x-qx,y-qy)
protected=[]
for oid in ids:
 b=byid.get(oid)
 if b and b.get('footprint'): protected.append((oid,xy(b['footprint'])))

def blocked(x,y):
 for oid,p in protected:
  if inside(x,y,p) or any(segdist(x,y,p[i],p[(i+1)%len(p)])<2.5 for i in range(len(p))): return oid
 return None
changed={}
for cname in ['07_Remote_Residential_LOD','11_Realistic_Facades']:
 c=bpy.data.collections.get(cname)
 if not c: continue
 for o in list(c.objects):
  if o.type!='MESH': continue
  me=o.data;bm=bmesh.new();bm.from_mesh(me);delete=[]
  for f in bm.faces:
   co=o.matrix_world @ f.calc_center_median()
   oid=blocked(co.x,co.y)
   if oid: f.select=True;delete.append(f)
  if delete:
   bmesh.ops.delete(bm,geom=delete,context='FACES');bm.to_mesh(me);me.update();changed[o.name]=len(delete)
  bm.free()
# Hide exact duplicates in 06 whose osm ids are protected and still visible, while keeping non-target independent context.
for o in bpy.data.collections.get('06_Individual_NonResidential_Highrises').objects if bpy.data.collections.get('06_Individual_NonResidential_Highrises') else []:
 oid=str(o.get('osm_id',''))
 if oid in ids and oid not in {'51209520'}:
  o.hide_render=True;o.hide_viewport=True;o['superseded_by_bespoke_overlay_fix']=True
bpy.context.scene['overlay_bug_fix_revision']='2026-10-01';bpy.context.scene['overlay_bug_fix_protected_footprints']=len(protected);bpy.context.scene['overlay_bug_fix_removed_faces']=sum(changed.values())
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print({'protected':len(protected),'changed':changed,'removed_faces':sum(changed.values())})
