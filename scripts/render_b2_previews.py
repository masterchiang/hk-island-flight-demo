import bpy
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>');out=ROOT/'output/bespoke_B2';out.mkdir(parents=True,exist_ok=True)
sc=bpy.context.scene
# Preserve project camera choice; render an overview and a CBD close context if available.
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1540;sc.render.resolution_y=1060;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for cam_name,file in [('HKI_Atlas_Camera','b2_overview.png'),('HKI_Realistic_CBD_Camera','b2_cbd_context.png')]:
 cam=bpy.data.objects.get(cam_name)
 if not cam:continue
 sc.camera=cam;sc.render.filepath=str(out/file);bpy.ops.render.render(write_still=True);print(sc.render.filepath)
# Restore atlas camera.
if bpy.data.objects.get('HKI_Atlas_Camera'):sc.camera=bpy.data.objects['HKI_Atlas_Camera']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
