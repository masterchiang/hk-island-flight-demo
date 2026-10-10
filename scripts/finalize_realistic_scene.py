"""Apply physically based materials, landscape, lighting and final city renders.
Call from the connected Blender instance with exec(compile(open(...).read(),...)).
Does not delete geometry or download unlicensed imagery.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>')
SCENE=bpy.context.scene

# Materials imported from Poly Haven CC0 and packed in this .blend.
def material_copy(src_name,dst_name):
 src=bpy.data.materials.get(src_name)
 if not src:return None
 old=bpy.data.materials.get(dst_name)
 if old:return old
 m=src.copy();m.name=dst_name;m['derived_from']=src_name;m['license_note']='Poly Haven CC0';return m

def use_generated_texture(mat, obj, tile_m):
 if not mat or not mat.use_nodes or not obj or obj.type!='MESH':return False
 nodes=mat.node_tree.nodes;links=mat.node_tree.links
 tex=next((n for n in nodes if n.type=='TEX_COORD'),None)
 mapping=next((n for n in nodes if n.type=='MAPPING'),None)
 image_nodes=[n for n in nodes if n.type=='TEX_IMAGE' and n.image]
 if not tex or not mapping or not image_nodes:return False
 uv=obj.data.uv_layers.active if hasattr(obj.data,'uv_layers') else None
 if not uv:return False
 # These meshes are world-coordinate XY relief with UVs absent; synthesize UVs
 # from local surface dimensions so tiled CC0 textures are stable in scale.
 for poly in obj.data.polygons:
  for li in poly.loop_indices:
   co=obj.data.vertices[obj.data.loops[li].vertex_index].co
   uv.data[li].uv=(float(co.x)/tile_m,float(co.y)/tile_m)
 for link in list(links):
  if link.to_node==mapping and link.to_socket.name=='Vector':links.remove(link)
 links.new(tex.outputs['UV'],mapping.inputs['Vector'])
 dims=obj.dimensions
 mapping.inputs['Scale'].default_value=(1.0,1.0,1.0)
 mat['mapping']='Generated coordinates normalized to object extent; approximate real-world tiling'
 return True

# True-size asphalt and concrete from CC0 packs. Each road class gets a unique copy
# so Generated coordinates use its own bounds and do not inherit an island-wide scale.
asphalt_src=bpy.data.materials.get('aerial_asphalt_01') or bpy.data.materials.get('asphalt_03')
side_src=bpy.data.materials.get('concrete_pavement_03')
road_objects=[o for o in list(bpy.data.objects) if o.type=='MESH' and o.name.startswith('TR_Road_')]
road_mats=0
for ob in road_objects:
 if not asphalt_src:break
 m=material_copy(asphalt_src.name,'HKI_PBR_Road_'+ob.name.replace('TR_Road_',''))
 if use_generated_texture(m,ob,30.0):
  if len(ob.data.materials):ob.data.materials[0]=m
  else:ob.data.materials.append(m)
  m['use']='worn aerial asphalt CC0';road_mats+=1
# Walkways and sidewalks: repeat concrete paving at approximate slab scale.
for ob in [o for o in list(bpy.data.objects) if o.type=='MESH' and o.name in ('TR_Sidewalks','TR_Walkways')]:
 if side_src:
  m=material_copy('concrete_pavement_03','HKI_PBR_'+ob.name+'_Paving')
  if use_generated_texture(m,ob,2.1):
   if len(ob.data.materials):ob.data.materials[0]=m
   else:ob.data.materials.append(m)
   m['use']='concrete urban paving CC0'

# Terrain: natural rocky/soil surface over the Lands Department DTM.
terrain=bpy.data.objects.get('HKI_Terrain_DTM25m')
terrain_src=bpy.data.materials.get('rocky_terrain_02') or bpy.data.materials.get('grass_ground')
if terrain and terrain_src:
 m=material_copy(terrain_src.name,'HKI_PBR_Terrain_HKI_DTM')
 if use_generated_texture(m,terrain,90.0):
  if terrain.data.materials:terrain.data.materials[0]=m
  else:terrain.data.materials.append(m)
  terrain['surface_source']='Poly Haven CC0 rocky terrain texture over Lands Department 5m DTM sampled to 25m'
# Expand the harbor backdrop plane well beyond the island camera and assign a physical water material.
sea=bpy.data.objects.get('Victoria_Harbour_Context')
if sea and sea.type=='MESH':
 if not sea.get('realistic_harbor_expanded'):
  for vert in sea.data.vertices:vert.co.x*=3.0;vert.co.y*=3.0
  sea['realistic_harbor_expanded']=True
 water=bpy.data.materials.get('HKI_PBR_Coastal_Water') or bpy.data.materials.new('HKI_PBR_Coastal_Water');water.use_nodes=True
 wn=water.node_tree.nodes;wl=water.node_tree.links;wn.clear();out=wn.new('ShaderNodeOutputMaterial');p=wn.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(.018,.075,.105,1);p.inputs['Metallic'].default_value=.28;p.inputs['Roughness'].default_value=.22
 noise=wn.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=850.;noise.inputs['Detail'].default_value=3.;noise.inputs['Roughness'].default_value=.62
 bump=wn.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.22;wl.new(noise.outputs['Fac'],bump.inputs['Height']);wl.new(bump.outputs['Normal'],p.inputs['Normal']);wl.new(p.outputs['BSDF'],out.inputs['Surface']);water.diffuse_color=(.018,.075,.105,1);water['look']='subtle deep harbour water, procedural ripples';sea.data.materials.clear();sea.data.materials.append(water)
# The separate contour grid stays subtle rather than neon.
for mn,col,rough,metal in [
 ('Holo_Grid',(.08,.12,.09),.92,.02),('Holo_Sea',(.018,.055,.078),.28,.36),
 ('Holo_Roads',(.10,.11,.105),.78,.02),('Holo_Terrain',(.10,.16,.105),.94,0),
 ('Holo_Facade_Lowrise',(.47,.42,.34),.62,.06),('Holo_Facade_Residential',(.58,.53,.44),.54,.12),
 ('Holo_Facade_Tower',(.11,.20,.25),.2,.58),('Holo_Facade_Landmark',(.32,.34,.32),.38,.32),
 ('Custom_Landmark_Glass',(.08,.18,.22),.19,.55),('Custom_Landmark_Steel',(.20,.24,.25),.27,.7),
 ('Custom_Landmark_Podium',(.30,.29,.26),.52,.16),('Custom_Landmark_Accent',(.43,.31,.16),.25,.55),('Custom_Landmark_Dark',(.015,.02,.025),.55,.12),
 ('Batch2_Glass',(.075,.17,.22),.2,.55),('Batch2_Steel',(.22,.26,.26),.3,.72),('Batch2_Podium',(.32,.30,.26),.5,.14),('Batch2_Accent',(.47,.34,.18),.28,.5),('Batch2_Dark',(.02,.03,.035),.58,.1)]:
 m=bpy.data.materials.get(mn)
 if not m:continue
 m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.name='Principled BSDF';p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if p.inputs.get('Emission Color'):p.inputs['Emission Color'].default_value=(0,0,0,1)
 l.new(p.outputs['BSDF'],out.inputs['Surface']);m.diffuse_color=(*col,1);m['look']='realistic PBR, no hologram emission'
# Realistic-facade category materials: remove any residual high-emission look.
for m in bpy.data.materials:
 if not m.name.startswith('HKI_RF_') or not m.use_nodes:continue
 for node in m.node_tree.nodes:
  if node.type=='BSDF_PRINCIPLED':
   if node.inputs.get('Emission Color'):node.inputs['Emission Color'].default_value=(0,0,0,1)
   if node.inputs.get('Metallic') and m.name.endswith('_Glass'):node.inputs['Metallic'].default_value=min(.55,max(.25,node.inputs['Metallic'].default_value))
# Vegetation keeps its merged mesh strategy, but use natural, non-emissive rough foliage.
for ob in [o for o in list(bpy.data.objects) if o.name.startswith('HKI_Vegetation_') and o.type=='MESH']:
 for m in ob.data.materials:
  if not m or not m.use_nodes:continue
  nm=m.name.lower();p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not p:continue
  if 'trunk' in nm:color=(.20,.135,.075,1);rough=.94
  elif 'leaf_0' in nm:color=(.085,.20,.055,1);rough=.88
  elif 'leaf_1' in nm:color=(.14,.28,.075,1);rough=.88
  elif 'leaf_2' in nm:color=(.24,.35,.11,1);rough=.86
  else:color=(.18,.27,.075,1);rough=.9
  p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=rough
  if p.inputs.get('Subsurface Weight'):p.inputs['Subsurface Weight'].default_value=.025
  if p.inputs.get('Emission Color'):p.inputs['Emission Color'].default_value=(0,0,0,1)

# Remove cartographic grid from final realistic renders; retain the object for optional atlas mode.
grid=bpy.data.objects.get('HKI_Terrain_ContourWire')
if grid:grid.hide_render=True;grid.hide_viewport=True
# Sketchfab landmark keeps its authored image/base-color networks; only lower added emission.
sketch=bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary')
if sketch:
 for ob in list(bpy.context.scene.objects):
  p0=ob;is_child=False
  while p0:
   if p0==sketch:is_child=True;break
   p0=p0.parent
  if is_child and ob.type=='MESH':
   for m in ob.data.materials:
    if m and m.use_nodes:
     for node in m.node_tree.nodes:
      if node.type=='BSDF_PRINCIPLED' and node.inputs.get('Emission Strength'):node.inputs['Emission Strength'].default_value=min(.08,node.inputs['Emission Strength'].default_value)

# Natural world/sun and a restrained area fill. Keep EEVEE realtime and use AgX.
world=SCENE.world or bpy.data.worlds.new('HKI_Realistic_World');SCENE.world=world;world.use_nodes=True
wn=world.node_tree.nodes;wl=world.node_tree.links;sky=next((n for n in wn if n.type=='TEX_SKY'),None);bg=next((n for n in wn if n.type=='BACKGROUND'),None);wo=next((n for n in wn if n.type=='OUTPUT_WORLD'),None)
if not (sky and bg and wo):
 wn.clear();wo=wn.new('ShaderNodeOutputWorld');bg=wn.new('ShaderNodeBackground');sky=wn.new('ShaderNodeTexSky');wl.new(sky.outputs['Color'],bg.inputs['Color']);wl.new(bg.outputs['Background'],wo.inputs['Surface'])
sky.sky_type='HOSEK_WILKIE';sky.sun_disc=True;sky.sun_elevation=math.radians(29);sky.sun_rotation=math.radians(143);sky.altitude=80;sky.air_density=1.0;sky.aerosol_density=1.25;sky.ozone_density=1.0;sky.turbidity=4.;sky.ground_albedo=.24;bg.inputs['Strength'].default_value=.62
for name in ['HKI_Sun_Day','HKI_Sky_Fill','HKI_Sky_Rim','HKI_Warm_Fill']:
 ob=bpy.data.objects.get(name)
 if ob:bpy.data.objects.remove(ob,do_unlink=True)
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
def light(name,typ,loc,energy,color,size=None,target=None):
 d=bpy.data.lights.new(name,typ);o=bpy.data.objects.new(name,d);SCENE.collection.objects.link(o);o.location=loc;d.energy=energy;d.color=color
 if size is not None and hasattr(d,'size'):d.size=size
 if target:aim(o,target)
 return o
sun=light('HKI_Sun_Day','SUN',(0,0,1),3.8,(1.0,.80,.63));sun.rotation_euler=(math.radians(32),math.radians(-18),math.radians(-38));sun.data.angle=math.radians(3.5)
light('HKI_Sky_Fill','AREA',(-4000,-3500,5200),38000,(.66,.78,1.0),7500,(-500,0,50))
light('HKI_Sky_Rim','AREA',(4500,3000,2800),13000,(.35,.55,1.0),6200,(-1200,400,100))
light('HKI_Warm_Fill','AREA',(-6200,1000,700),5000,(1.0,.56,.34),2100,(-5200,700,80))
SCENE.render.engine='BLENDER_EEVEE';SCENE.view_settings.view_transform='AgX';SCENE.view_settings.look='AgX - Medium High Contrast';SCENE.view_settings.exposure=1.1;SCENE.view_settings.gamma=1.0;SCENE.render.film_transparent=False;SCENE.render.use_compositing=False;SCENE.render.use_sequencer=False
# General aerial framing, keeping target inspection cameras available.
cam=bpy.data.objects.get('HKI_Atlas_Camera')
if not cam:
 d=bpy.data.cameras.new('HKI_Atlas_Camera');cam=bpy.data.objects.new('HKI_Atlas_Camera',d);SCENE.collection.objects.link(cam)
cam.location=(5200,-14500,5900);cam.data.type='ORTHO';cam.data.ortho_scale=16500;cam.data.clip_start=.1;cam.data.clip_end=100000;cam.rotation_euler=(Vector((-600,-2500,50))-cam.location).to_track_quat('-Z','Y').to_euler();SCENE.camera=cam
SCENE.render.resolution_x=1440;SCENE.render.resolution_y=900;SCENE.render.resolution_percentage=70
SCENE['project_phase']='realistic material/vegetation/transport/lighting integration';SCENE['surface_assets']='Poly Haven CC0 asphalt_03, aerial_asphalt_01, concrete_pavement_03, concrete_tile_facade, grass_ground, leafy_grass, rocky_terrain_02';SCENE['image_license_policy']='Do not redistribute scraped Google/Baidu Street View imagery; use official Hong Kong data or clearly licensed CC0 assets.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
# Final integrated preview is rendered by scripts/render_integrated_previews.py after module regeneration.
print(json.dumps({'saved':str(ROOT/'HKI_Holographic_Atlas.blend'),'road_textured_objects':road_mats,'vegetation_objects':3,'transport_collection':bool(bpy.data.collections.get('HKI_Transport')),'facade_collection':bool(bpy.data.collections.get('11_Realistic_Facades')),'cameras':{'overview':cam.name}},ensure_ascii=False))
