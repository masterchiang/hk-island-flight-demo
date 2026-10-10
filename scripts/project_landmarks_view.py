import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sc=bpy.context.scene;cam=bpy.data.objects.get('HKI_Atlas_Camera')
for o in sorted(bpy.data.objects,key=lambda x:x.name):
 if o.type=='EMPTY' and (o.get('name') or o.get('landmark_name') or o.get('osm_id')):
  c=o.matrix_world.translation; co=world_to_camera_view(sc,cam,c)
  if 0.25<co.x<0.75 and 0.55<co.y<0.95:
   print(o.name, o.get('name',o.get('landmark_name')), o.get('osm_id'), tuple(round(v,3) for v in (co.x,co.y,co.z)), tuple(round(v,1) for v in c))
