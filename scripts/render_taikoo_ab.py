import bpy
from mathutils import Vector
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>');sc=bpy.context.scene
cam=bpy.data.objects.get('HKI_Taikoo_Bug_Check');sc.camera=cam
for i,n in enumerate(['baseline','no_remote_lod','no_realistic_facades','no_remote_no_realistic']):
 for cname in ['07_Remote_Residential_LOD','11_Realistic_Facades']:
  c=bpy.data.collections.get(cname)
  if c:c.hide_render=(cname=='07_Remote_Residential_LOD' and n in ['no_remote_lod','no_remote_no_realistic']) or (cname=='11_Realistic_Facades' and n in ['no_realistic_facades','no_remote_no_realistic'])
 sc.render.resolution_x=800;sc.render.resolution_y=600;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=str(ROOT/'output'/f'taikoo_{n}.png');bpy.ops.render.render(write_still=True)
for cname in ['07_Remote_Residential_LOD','11_Realistic_Facades']:
 c=bpy.data.collections.get(cname)
 if c:c.hide_render=False
