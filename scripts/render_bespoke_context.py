"""Cameras and reproducible in-context renders; original scene lighting retained."""
import bpy
from mathutils import Vector
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>')
SCENE='HKI_Holographic_Atlas'

def camera(name,loc,target,lens=52):
 sc=bpy.data.scenes[SCENE];o=bpy.data.objects.get(name)
 if not o:
  d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d)
  bpy.data.collections['04_Visualization'].objects.link(o)
 o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
 o.data.lens=lens;o.data.clip_start=1.;o.data.clip_end=50000.
 return o

def setup():
 return [camera('HKI_B1_Central_Context',(-6170,1960,505),(-5430,985,152),47),camera('HKI_B1_Wanchai_Context',(-3520,1355,350),(-4065,677,170),55),camera('HKI_B1_Lippo_Context',(-4940,940,143),(-5110,610,88),53),camera('HKI_B1_Jardine_Detail',(-5740,1300,110),(-5558,1013,89),56)]

def render_context(index,slug):
 sc=bpy.data.scenes[SCENE];cams=setup();sc.camera=cams[index]
 sc.render.resolution_x=1540;sc.render.resolution_y=1060;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG';sc.render.filepath=str(ROOT/'output/bespoke_B1'/f'{slug}.png')
 bpy.ops.render.render(scene=sc.name,write_still=True)
 return sc.render.filepath
