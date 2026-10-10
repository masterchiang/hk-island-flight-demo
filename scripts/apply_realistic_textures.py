"""Attach packed Poly Haven CC0 PBR maps to road, sidewalk, terrain and facades.
World-coordinate UVs are generated in metre-based tiling; materials are copied,
never overwriting source Poly Haven downloads or Sketchfab-authored shaders.
"""
import bpy, json, math
from pathlib import Path
ROOT=Path(r'<PROJECT_ROOT>')

def make_tinted_copy(src_name,dst_name,tint=(1,1,1,1),roughness=None,metallic=None):
 src=bpy.data.materials.get(src_name)
 if not src:return None
 old=bpy.data.materials.get(dst_name)
 if old:
  p=next((n for n in old.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if old.use_nodes else None
  mix=next((n for n in old.node_tree.nodes if n.type=='MIX_RGB' and n.label=='Category tint (PBR)'),None) if old.use_nodes else None
  if mix:mix.inputs['Color2'].default_value=tint
  elif p:p.inputs['Base Color'].default_value=tint
  if p and roughness is not None:p.inputs['Roughness'].default_value=roughness
  if p and metallic is not None:p.inputs['Metallic'].default_value=metallic
  old.diffuse_color=tint;return old
 m=src.copy();m.name=dst_name;m['derived_from']=src_name;m['license']='Poly Haven CC0';m['image_space']='UV metre tiling'
 p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if not p:return m
 diffuse=next((n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and 'Diffuse' in n.image.name),None)
 # Tinted multiply retains the measured albedo map while allowing surface class variation.
 if diffuse:
  old=[ln for ln in list(m.node_tree.links) if ln.to_node==p and ln.to_socket==p.inputs['Base Color']]
  for ln in old:m.node_tree.links.remove(ln)
  mix=m.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs['Fac'].default_value=1.;mix.inputs['Color2'].default_value=tint;mix.label='Category tint (PBR)'
  m.node_tree.links.new(diffuse.outputs['Color'],mix.inputs['Color1']);m.node_tree.links.new(mix.outputs['Color'],p.inputs['Base Color'])
 else:p.inputs['Base Color'].default_value=tint
 if roughness is not None:p.inputs['Roughness'].default_value=roughness
 if metallic is not None:p.inputs['Metallic'].default_value=metallic
 m.diffuse_color=tint
 return m

def uv_map_mesh(obj,tile_m,wall_faces=False):
 if obj.type!='MESH':return 0
 me=obj.data
 uv=me.uv_layers.active or me.uv_layers.new(name='HKI_WorldMeters_UV')
 count=0
 for poly in me.polygons:
  loops=list(poly.loop_indices); verts=[me.vertices[me.loops[li].vertex_index].co for li in loops]
  wall=wall_faces and poly.loop_total==4 and abs(poly.normal.z)<.65
  if wall:
   zmin=min(v.z for v in verts);bottom=[v for v in verts if abs(v.z-zmin)<.02]
   if len(bottom)<2:wall=False
  if wall:
   p0=bottom[0];p1=max(bottom[1:],key=lambda v:(v-p0).length);d=p1-p0;ll=max(.001,math.hypot(d.x,d.y))
   for li,v in zip(loops,verts):
    u=((v.x-p0.x)*d.x+(v.y-p0.y)*d.y)/(ll*tile_m); vv=(v.z-zmin)/tile_m;uv.data[li].uv=(u,vv)
  else:
   for li,v in zip(loops,verts):uv.data[li].uv=(v.x/tile_m,v.y/tile_m)
  count+=1
 return count

# Roads and pavements
road_src='aerial_asphalt_01' if bpy.data.materials.get('aerial_asphalt_01') else 'asphalt_03'
road_count=side_count=0
for o in list(bpy.data.objects):
 if o.type!='MESH':continue
 if o.name.startswith('TR_Road_'):
  m=make_tinted_copy(road_src,'HKI_PBR_'+o.name+'_Asphalt',(.50,.53,.54,1),.88,.02)
  if m:
   o.data.materials.clear();o.data.materials.append(m);uv_map_mesh(o,30.0);o['surface']='CC0 aerial asphalt; approximately 30m texture tile';road_count+=1
 elif o.name in ('TR_Sidewalks','TR_Walkways'):
  src='concrete_pavement_03';m=make_tinted_copy(src,'HKI_PBR_'+o.name+'_Concrete',(.80,.80,.76,1),.82,.02)
  if m:
   o.data.materials.clear();o.data.materials.append(m);uv_map_mesh(o,2.1);o['surface']='CC0 concrete pavement; approximately 2.1m texture tile';side_count+=1
# DTM - earthy aerial rocky cover with a subdued green/brown bias.
terrain=bpy.data.objects.get('HKI_Terrain_DTM25m')
if terrain and bpy.data.materials.get('rocky_terrain_02'):
 m=make_tinted_copy('rocky_terrain_02','HKI_PBR_HKI_Terrain_RockGrass',(.72,.82,.62,1),.93,.0)
 terrain.data.materials.clear();terrain.data.materials.append(m);uv_map_mesh(terrain,90.0);terrain['surface']='Lands Department DTM + Poly Haven CC0 90m rocky grass material'
# Semantic wall/roof material assignment for the far LOD.
facade_src='concrete_tile_facade'
facade_tints={'residential':(.66,.68,.64,1),'old_building':(.76,.63,.46,1),'glass_office':(.60,.70,.73,1),'concrete_office':(.72,.70,.63,1),'hotel':(.80,.69,.52,1),'industrial':(.72,.74,.68,1),'school':(.82,.71,.52,1),'retail_podium':(.56,.62,.60,1)}
def scanned_facade(cat):
 return make_tinted_copy(facade_src,'HKI_PBR_Facade_'+cat.title(),facade_tints.get(cat,(.75,.75,.7,1)),.58,.12)

remote=bpy.data.objects.get('HKI_Remote_Residential_and_Lowrise_LOD')
if remote and remote.type=='MESH':
 old_indices=[poly.material_index for poly in remote.data.polygons]
 uv_map_mesh(remote,2.09,wall_faces=True)
 cats=['old_building','residential','glass_office','concrete_office']
 wallmats=[];roofmats=[]
 for cat in cats:
  wallmats.append(bpy.data.materials.get('HKI_RF_'+cat+'_Wall') if cat=='glass_office' else scanned_facade(cat))
  roofmats.append(bpy.data.materials.get('HKI_RF_'+cat+'_Roof'))
 remote.data.materials.clear()
 for mat in wallmats+roofmats:remote.data.materials.append(mat)
 for poly,old_i in zip(remote.data.polygons,old_indices):
  ci=min(max(0,int(old_i)),3)
  poly.material_index=ci+4 if poly.normal.z>.62 else ci
 remote['appearance']='physical PBR wall/roof classes by original OSM LOD material index'

# Category by OSM feature id for independently generated towers.
import json as _json
_building_records=_json.loads((ROOT/'data'/'processed'/'hki_buildings.json').read_text(encoding='utf8'))['buildings']
_kind_by_id={str(x['id']):str(x.get('kind','yes')).lower() for x in _building_records}
_name_by_id={str(x['id']):str(x.get('name','')).lower() for x in _building_records}
category_map={'apartments':'residential','residential':'residential','house':'residential','semidetached_house':'residential','terrace':'residential','dormitory':'residential','hotel':'hotel','commercial':'retail_podium','retail':'retail_podium','industrial':'industrial','warehouse':'industrial','school':'school','university':'school','office':'glass_office','civic':'concrete_office','public':'concrete_office','government':'concrete_office'}
def category_for_oid(oid):
 kind=_kind_by_id.get(str(oid),'yes');name=_name_by_id.get(str(oid),'');cat=category_map.get(kind,'glass_office')
 if 'hotel' in name:cat='hotel'
 elif any(q in name for q in ('school','university','hospital')):cat='school'
 elif any(q in name for q in ('government','revenue','immigration','civic')):cat='concrete_office'
 elif any(q in name for q in ('mall','shopping','retail','podium')):cat='retail_podium'
 return cat
for ob in list(bpy.data.objects):
 if ob.type!='MESH' or not ob.name.startswith('IND_'):continue
 oid=str(ob.get('osm_id',''))
 if not oid:continue
 cat=category_for_oid(oid)
 semantic=[]
 for sn in [f'HKI_RF_{cat}_Wall',f'HKI_RF_{cat}_Glass',f'HKI_RF_{cat}_Frame',f'HKI_RF_{cat}_Accent',f'HKI_RF_{cat}_Roof']:
  m=bpy.data.materials.get(sn)
  if m:semantic.append(m)
 if not semantic:continue
 oldslots=list(ob.data.materials)
 ob.data.materials.clear()
 for m in semantic:ob.data.materials.append(m)
 for poly in ob.data.polygons:poly.material_index=min(max(poly.material_index,0),len(semantic)-1)
 ob['realistic_category']=cat;ob['appearance']='PBR wall/glass/frame/accent/roof slots by OSM type and use'

# Custom landmark profile meshes: map material roles to the same realistic categories.
for coll_name in ('09_Custom_Landmarks','10_Custom_Landmarks_Batch2'):
 c=bpy.data.collections.get(coll_name)
 if not c:continue
 for ob in list(c.objects):
  if ob.type!='MESH' or not ob.parent:continue
  cat=category_for_oid(str(ob.parent.get('osm_id','')))
  old=list(ob.data.materials);new=[]
  for oldm in old:
   low=oldm.name.lower() if oldm else ''
   if 'podium' in low: m=scanned_facade('retail_podium')
   elif 'dark' in low: m=bpy.data.materials.get(f'HKI_RF_{cat}_Roof')
   elif 'accent' in low: m=bpy.data.materials.get(f'HKI_RF_{cat}_Accent')
   elif 'steel' in low or 'frame' in low: m=bpy.data.materials.get(f'HKI_RF_{cat}_Frame')
   else: m=bpy.data.materials.get(f'HKI_RF_{cat}_Glass')
   if m is None:m=oldm
   new.append(m)
  ob.data.materials.clear()
  for m in new:ob.data.materials.append(m)
  ob['realistic_category']=cat;ob['appearance']='PBR profile materials with CC0 concrete podium facade where appropriate'

# Use real facade texture only for wall materials. Roofs remain category-specific PBR.
facade_src='concrete_tile_facade';facade_count=0;facade_tints={
 'residential':(.66,.68,.64,1),'old_building':(.76,.63,.46,1),'glass_office':(.60,.70,.73,1),'concrete_office':(.72,.70,.63,1),'hotel':(.80,.69,.52,1),'industrial':(.72,.74,.68,1),'school':(.82,.71,.52,1),'retail_podium':(.56,.62,.60,1)}
shell=bpy.data.objects.get('HKI_RF_Shells')
if shell:
 uv_map_mesh(shell,2.09,wall_faces=True)
 for i,old in enumerate(list(shell.data.materials)):
  if not old:continue
  # The facade pass may already have been run; accept either semantic or prior PBR material names.
  if old.name.startswith('HKI_RF_') and old.name.endswith('_Wall'):
   cat=old.name[len('HKI_RF_'):-len('_Wall')]
  elif old.name.startswith('HKI_PBR_Facade_'):
   cat=old.name[len('HKI_PBR_Facade_'):].lower()
  else:continue
  # Apply the scanned CC0 panel texture to residential/masonry/civic/retail.
  # Glass offices retain their blue-gray PBR backing so the procedural curtainwall cells read as glazing.
  if cat=='glass_office':
   pbr=bpy.data.materials.get('HKI_RF_'+cat+'_Wall')
   if pbr:shell.data.materials[i]=pbr
   continue
  tint=facade_tints.get(cat,(.8,.8,.8,1));m=make_tinted_copy(facade_src,'HKI_PBR_Facade_'+cat.title(),tint,.58,.12)
  if m:shell.data.materials[i]=m;facade_count+=1
# Podiums of custom landmarks can use concrete tile PBR too; preserve each frame/accent material.
for coll_name in ['09_Custom_Landmarks','10_Custom_Landmarks_Batch2']:
 c=bpy.data.collections.get(coll_name)
 if not c:continue
 for ob in list(c.objects):
  if ob.type!='MESH':continue
  uv_map_mesh(ob,2.09,wall_faces=True)
  for i,mold in enumerate(list(ob.data.materials)):
   if not mold:continue
   low=mold.name.lower()
   if 'podium' in low:
    mat=make_tinted_copy(facade_src,'HKI_PBR_'+coll_name+'_Podium',(.72,.68,.58,1),.64,.08)
    if mat:ob.data.materials[i]=mat
# Metadata only
bpy.context.scene['pbr_texture_credits']='Poly Haven CC0: Aerial Asphalt 01, Concrete Pavement 03, Concrete Tile Facade, Rocky Terrain 02.'
bpy.context.scene['pbr_uv_note']='Road/terrain/facade UVs are world-meter projected; procedural tiling may differ from exact surveyed facade panel dimensions.'
print(json.dumps({'road_objects_textured':road_count,'paving_objects_textured':side_count,'facade_wall_slots_textured':facade_count,'terrain_textured':bool(terrain),'texture_names':[road_src,'concrete_pavement_03','concrete_tile_facade','rocky_terrain_02']},ensure_ascii=False,indent=2))
