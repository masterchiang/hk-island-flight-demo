import bpy
from mathutils import Vector
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>');sc=bpy.context.scene
name='HKI_Taikoo_Bug_Check';cam=bpy.data.objects.get(name)
if not cam:
 d=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,d);bpy.data.collections['04_Visualization'].objects.link(cam)
target=Vector((-20,1450,95));cam.location=target+Vector((0,0,1800));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=520;cam.data.clip_end=10000;sc.camera=cam;sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.filepath=str(ROOT/'output'/'taikoo_bug_check.png');sc.render.image_settings.file_format='PNG';bpy.ops.render.render(write_still=True);sc.camera=bpy.data.objects.get('HKI_Atlas_Camera');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'));print(sc.render.filepath)
