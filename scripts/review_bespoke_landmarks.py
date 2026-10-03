"""Isolated review scene; never changes main-world lighting or GIS root transforms."""
import bpy,math
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(r'<PROJECT_ROOT>')
OUT=ROOT/'output/bespoke_B1';OUT.mkdir(parents=True,exist_ok=True)

def studio(names,slug,before=False):
 # Re-use a transient scene. Meshes remain linked to the editable main assets.
 prior=bpy.data.scenes.get('B1_Review_Studio')
 if prior:
  for o in list(prior.objects):
   data=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if data and data.users==0:
    if isinstance(data,bpy.types.Camera):bpy.data.cameras.remove(data)
    elif isinstance(data,bpy.types.Light):bpy.data.lights.remove(data)
    elif isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
  bpy.data.scenes.remove(prior)
 sc=bpy.data.scenes.new('B1_Review_Studio')
 source=[o for o in bpy.data.collections['12_Bespoke_Landmarks_B1'].objects if o.type=='EMPTY' and o.get('landmark_name') in names]
 h=max(o['height_m'] for o in source)
 anchor=sum((o.location for o in source),Vector())/len(source)
 for root in source:
  original=next((o for o in bpy.data.collections['12_PreBespoke_LOD_Archive'].objects if o.type=='EMPTY' and str(o.get('osm_id'))==str(root['osm_id'])),None) if before else root
  assert original is not None
  for child in original.children:
   du=child.copy();du.data=child.data;sc.collection.objects.link(du)
   du.parent=None;du.hide_render=False;du.hide_viewport=False;du.hide_set(False)
   if before:
    if len(source)==1:
     du.matrix_world=root.matrix_world.inverted() @ child.matrix_world
    else:
     du.matrix_world=Matrix.Translation((-anchor.x,-anchor.y,-min(o.location.z for o in source))) @ child.matrix_world
   elif len(source)==1:
    du.location=(0,0,0);du.rotation_euler=(0,0,0)
   else:
    du.matrix_world=child.matrix_world.copy();du.location-=Vector((anchor.x,anchor.y,min(o.location.z for o in source)))
 world=bpy.data.worlds.get('B1_Studio_World') or bpy.data.worlds.new('B1_Studio_World')
 world.use_nodes=False;world.color=(.36,.40,.47);sc.world=world
 # Broad ground gives clean contact shadows and an unobtrusive backdrop.
 me=bpy.data.meshes.new('B1_StudioGround');me.from_pydata([(-3000,-3000,-1.0),(3000,-3000,-1.0),(3000,3000,-1.0),(-3000,3000,-1.0)],[],[(0,1,2,3)])
 go=bpy.data.objects.new('B1_StudioGround',me);sc.collection.objects.link(go)
 ma=bpy.data.materials.get('B1_StudioFloor') or bpy.data.materials.new('B1_StudioFloor');ma.diffuse_color=(.17,.19,.22,1);ma.use_nodes=True
 p=next(n for n in ma.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.17,.19,.22,1);p.inputs['Roughness'].default_value=.72;me.materials.append(ma)
 def light(name,kind,loc,power,size,color):
  d=bpy.data.lights.new(name,kind);d.energy=power;d.color=color
  if kind=='AREA':d.shape='DISK';d.size=size
  if kind=='SUN':d.angle=.10
  o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,h*.45))-o.location).to_track_quat('-Z','Y').to_euler()
 light('B1_Key','SUN',(-200,-400,500),2.6,0,(1.,.93,.82))
 light('B1_Fill','AREA',(150,-120,h*.65),1500000,200,(.70,.83,1.))
 light('B1_Rim','AREA',(-150,160,h*.85),2500000,190,(.85,.92,1.))
 cam=bpy.data.cameras.new('B1_StudioCamera');co=bpy.data.objects.new('B1_StudioCamera',cam);sc.collection.objects.link(co)
 co.location=(h*1.05,-h*1.55,h*.90);co.rotation_euler=(Vector((0,0,h*.48))-co.location).to_track_quat('-Z','Y').to_euler()
 cam.type='ORTHO';cam.ortho_scale=h*1.13;cam.clip_end=10000;sc.camera=co
 sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=720;sc.render.resolution_y=940;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG';sc.render.filepath=str(OUT/(slug+'.png'))
 sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.25
 sc.render.film_transparent=False
 return sc

def render(names,slug,before=False):
 sc=studio(names,slug,before);bpy.ops.render.render(scene=sc.name,write_still=True);return str(OUT/(slug+'.png'))
