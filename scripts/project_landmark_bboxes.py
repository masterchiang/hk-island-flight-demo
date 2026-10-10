import bpy, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sc=bpy.context.scene;cam=bpy.data.objects.get('HKI_Atlas_Camera')
rows=[]
for r in bpy.data.collections['09_Custom_Landmarks'].objects:
 if r.type!='EMPTY':continue
 p=[]
 for c in r.children_recursive:
  if c.type=='MESH':p += [c.matrix_world@Vector(v) for v in c.bound_box]
  elif c.type=='CURVE':p += [c.matrix_world@Vector(v) for v in c.bound_box]
 if not p:continue
 c=sum(p,Vector())/len(p);co=world_to_camera_view(sc,cam,c)
 if 0.35<co.x<0.55 and 0.65<co.y<0.9:
  rows.append((co.x,co.y,r.name,r.get('name'),r.get('osm_id'),tuple(round(x,1) for x in c),tuple(round(x,1) for x in [max(q.z for q in p)-min(q.z for q in p)])))
for x in sorted(rows, key=lambda a:(a[1],a[0])):print(x)
