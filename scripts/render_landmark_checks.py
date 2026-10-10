import bpy, math, os
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>')
scene=bpy.context.scene
TARGETS=[
 ('CUSTOM_590814694_HSBC_Main_Building','hki_hsbc_v2_front_check.png'),
 ('CUSTOM_51179190_Two_International_Finance_Centre','hki_ifc2_target_check.png'),
 ('CUSTOM_54174036_Central_Plaza','hki_central_plaza_target_check.png'),
 ('CUSTOM_65061120_One_Exchange_Square','hki_exchange_square_target_check.png'),
]
def descendants(root):
 out=[]
 for o in scene.objects:
  p=o
  while p:
   if p==root:out.append(o);break
   p=p.parent
 return out
def bounds(objs):
 pts=[]
 for o in objs:
  if o.type!='MESH':continue
  pts.extend([o.matrix_world@Vector(v) for v in o.bound_box])
 if not pts:return None
 return [(min(p[i] for p in pts),max(p[i] for p in pts)) for i in range(3)]
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.get('HKI_Landmark_Check_CameraData') or bpy.data.cameras.new('HKI_Landmark_Check_CameraData')
cam=bpy.data.objects.get('HKI_Landmark_Check_Camera') or bpy.data.objects.new('HKI_Landmark_Check_Camera',data)
if cam.name not in scene.collection.objects:scene.collection.objects.link(cam)
original={o:(o.hide_viewport,o.hide_render) for o in scene.objects}
results=[]
for root_name,file_name in TARGETS:
 root=bpy.data.objects.get(root_name)
 if not root:continue
 ds=descendants(root);bb=bounds(ds)
 if not bb:continue
 center=Vector(((bb[0][0]+bb[0][1])/2,(bb[1][0]+bb[1][1])/2,(bb[2][0]+bb[2][1])/2))
 radius=max(bb[0][1]-bb[0][0],bb[1][1]-bb[1][0],bb[2][1]-bb[2][0])
 for o in scene.objects:
  o.hide_viewport=True;o.hide_render=True
 for o in ds:
  o.hide_viewport=False;o.hide_render=False
 cam.location=center+Vector((-radius*1.05,-radius*2.8,radius*0.42));cam.data.type='PERSP';cam.data.lens=58;cam.data.clip_start=.1;cam.data.clip_end=max(500,radius*10);look(cam,center)
 scene.camera=cam;scene.view_settings.exposure=.45;scene.render.resolution_x=820;scene.render.resolution_y=980;scene.render.resolution_percentage=80;scene.render.filepath=str(ROOT/'output'/file_name);scene.render.use_compositing=False;scene.render.use_sequencer=False
 bpy.ops.render.render(write_still=True)
 results.append({'root':root_name,'file':str(ROOT/'output'/file_name),'center':tuple(center),'radius':radius})
for o,(hv,hr) in original.items():o.hide_viewport=hv;o.hide_render=hr
# Leave the HSBC inspection camera active.
scene.camera=cam;scene.view_settings.exposure=.3;scene.render.resolution_x=1000;scene.render.resolution_y=760;scene.render.resolution_percentage=80;scene.render.filepath=str(ROOT/'output/hki_hsbc_target_check.png')
scene['landmark_check_files']=[r['file'] for r in results]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(results)
