import bpy
from mathutils import Vector
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>');sc=bpy.context.scene;CAM='HKI_B2_Central_Hero_Camera'
cam=bpy.data.objects.get(CAM)
if cam is None:
 data=bpy.data.cameras.new(CAM);cam=bpy.data.objects.new(CAM,data);bpy.data.collections['04_Visualization'].objects.link(cam)
target=Vector((-5550,900,185));cam.location=target+Vector((-1250,-1450,560));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=48;cam.data.clip_start=1;cam.data.clip_end=20000
sc.camera=cam;sc.render.resolution_x=1540;sc.render.resolution_y=1060;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=str(ROOT/'output/bespoke_B2'/'b2_central_hero_context.png')
bpy.ops.render.render(write_still=True)
sc.camera=bpy.data.objects.get('HKI_Atlas_Camera');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(sc.render.filepath)
