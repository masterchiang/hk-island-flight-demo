from __future__ import annotations
import json, os
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(os.environ.get('HKI_PROJECT_ROOT',r'<PROJECT_ROOT>'))
DATA=ROOT/'data'/'processed'
MOD=ROOT/'scripts'/'build_realistic_facades.py'
ns={'__name__':'hki_realistic_facades','__file__':str(MOD)}
exec(compile(MOD.read_text(encoding='utf8'),str(MOD),'exec'),ns)
Batch=ns['Batch']; load_config=ns['load_config']; records=ns['records']; clean_ring=ns['clean_ring']; center=ns['center']; classify=ns['classify']; template_for=ns['template_for']; protected=ns['protected']; height_fn=ns['height']; floor_height=ns['floor_height']; detail_record=ns['detail_record']; add_shell=ns['add_shell']; add_seams=ns['add_seams']; add_windows=ns['add_windows']; add_balconies=ns['add_balconies']; add_ac=ns['add_ac']; add_roof=ns['add_roof']; add_landmark_accents=ns['add_landmark_accents']
import numpy as np
T=np.load(DATA/'terrain_hki.npz');TX=T['x'];TY=T['y'];TZ=T['z']
def sample_z(px,py):
 ix=int(np.clip(np.searchsorted(TX,px)-1,0,len(TX)-1));iy=int(np.clip(np.searchsorted(TY,py)-1,0,len(TY)-1));return float(TZ[iy,ix])+.65

def clear_collection(name):
 c=bpy.data.collections.get(name)
 if c:
  for o in list(c.objects): bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.collections.remove(c)

def make_pbr(name,color,rough=.5,metal=.0,glass=False):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.name='Principled BSDF'
 p.inputs['Base Color'].default_value=tuple(color[:3])+(1,);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if glass:
  if p.inputs.get('Transmission Weight'):p.inputs['Transmission Weight'].default_value=.10
  if p.inputs.get('IOR'):p.inputs['IOR'].default_value=1.45
  if p.inputs.get('Coat Weight'):p.inputs['Coat Weight'].default_value=.18
 if p.inputs.get('Emission Color'):p.inputs['Emission Color'].default_value=(0,0,0,1)
 if name.endswith('_Glass'):
  if p.inputs.get('Transmission Weight'):p.inputs['Transmission Weight'].default_value=.08
  if p.inputs.get('IOR'):p.inputs['IOR'].default_value=1.46
  if p.inputs.get('Coat Weight'):p.inputs['Coat Weight'].default_value=.2
 l.new(p.outputs['BSDF'],out.inputs['Surface']);m.diffuse_color=tuple(color[:3])+(1,);m['realistic_facade_material']=True;return m

cfg=load_config(ROOT);recs=records(ROOT);clear_collection('11_Realistic_Facades');coll=bpy.data.collections.new('11_Realistic_Facades');bpy.context.scene.collection.children.link(coll)
root=bpy.data.objects.new('HKI_Realistic_Facades_ROOT',None);coll.objects.link(root);root['module']='hki_realistic_facades';root['source']='data/processed/hki_buildings.json';root['protected']='Sketchfab Bank of China Tower untouched'
mat_slots={}
for cat,spec in cfg['material_categories'].items():
 mat_slots[cat]={'wall':make_pbr(f'HKI_RF_{cat}_Wall',spec['wall_color'],spec['roughness'],spec['metallic']),'glass':make_pbr(f'HKI_RF_{cat}_Glass',spec['glass_color'],spec['glass_roughness'],min(.65,spec['metallic']+.15),True),'frame':make_pbr(f'HKI_RF_{cat}_Frame',spec['frame_color'],max(.22,spec['roughness']-.12),min(.8,spec['metallic']+.18)),'accent':make_pbr(f'HKI_RF_{cat}_Accent',spec['accent_color'],max(.25,spec['roughness']-.16),min(.75,spec['metallic']+.12)),'roof':make_pbr(f'HKI_RF_{cat}_Roof',tuple(max(0,c*.62) for c in spec['wall_color'][:3])+(1,),min(.78,spec['roughness']+.1),spec['metallic']*.6)}
batches={k:Batch(k) for k in ('shells','windows','frames','balconies','ac','seams','roof','landmark')}
opt=cfg.get('run_options',{});limits={'max_window_panels':int(opt.get('max_window_panels_per_building',96)),'max_balconies':int(opt.get('max_balconies_per_building',8)),'max_ac_units':int(opt.get('max_ac_units_per_building',24)),'max_roof_units':int(opt.get('max_roof_units_per_building',4))}
# Scene-scale performance caps: residential silhouettes cover all dwellings, while
# repeatable window/AC/roof details are concentrated on named homes and larger estates.
detail_budget=24000;detail_used=0
landmark_names=set(cfg.get('landmark_templates',{}));custom_osm_ids=set()
for _cn in ('09_Custom_Landmarks','10_Custom_Landmarks_Batch2'):
 _cc=bpy.data.collections.get(_cn)
 if _cc:
  custom_osm_ids.update(str(_o.get('osm_id')) for _o in _cc.objects if _o.type=='EMPTY' and _o.get('osm_id'))
# Independent high-rises keep their custom massing mesh; this pass adds realistic
# glazing/frames/balconies/AC without a duplicate wall shell.
_ind=bpy.data.collections.get('06_Individual_NonResidential_Highrises')
_ind_ids=set()
if _ind:
 _ind_ids.update(str(_o.get('osm_id')) for _o in _ind.objects if _o.get('osm_id'))
stats={'processed':0,'details':0,'skipped_protected':0,'skipped_custom_landmarks':0,'categories':{}}
assign=[]
for rec in recs:
 tpl=template_for(rec,cfg)
 if protected(rec,tpl):stats['skipped_protected']+=1;continue
 ring=clean_ring(rec.get('footprint',[]),28)
 if len(ring)<3:continue
 rid=str(rec.get('id'))
 if rec.get('name') in landmark_names or rid in custom_osm_ids:
  stats['skipped_custom_landmarks']+=1;continue
 cat=classify(rec,cfg,tpl);h=height_fn(rec,cat,cfg);fh=floor_height(rec,cat,h,cfg);c=center(ring);base=sample_z(c.x,c.y);top=base+h;spec=cfg['material_categories'].get(cat,cfg['material_categories']['concrete_office']);flags=spec.get('feature_flags',[])
 if rid not in _ind_ids: add_shell(batches,ring,base,top,cat)
 det=detail_record(rec,h,tpl)
 if det:
  add_windows(batches,ring,base,top,cat,fh,flags,limits,tpl);add_seams(batches,ring,base,top,h,cat,True);add_balconies(batches,ring,base,top,cat,fh,flags,limits);add_ac(batches,ring,base,top,cat,fh,flags,limits,rec.get('id'));add_roof(batches,c,ring,top,cat,limits,rec.get('id'));add_landmark_accents(batches,ring,base,top,cat,tpl);stats['details']+=1
 stats['processed']+=1;stats['categories'][cat]=stats['categories'].get(cat,0)+1;assign.append({'id':str(rec.get('id')),'name':rec.get('name',''),'kind':rec.get('kind','yes'),'category':cat,'height':round(h,2),'detail':det})

def emit(key,batch):
 if not batch.faces:return None
 me=bpy.data.meshes.new('HKI_RF_'+key.title()+'_Mesh');me.from_pydata(batch.vertices,[],batch.faces);me.update();ob=bpy.data.objects.new('HKI_RF_'+key.title(),me);coll.objects.link(ob);ob.parent=root;names=[]
 for tag in batch.mats:
  if tag not in names:names.append(tag)
 for tag in names:
  cat,slot=tag.split(':',1);me.materials.append(mat_slots[cat][slot])
 for i,p in enumerate(me.polygons):p.material_index=names.index(batch.mats[i])
 ob['module']='hki_realistic_facades';ob['feature_family']=key;ob['material_count']=len(names);return ob
made=[emit(k,batches[k]) for k in batches];made=[o for o in made if o]
(DATA/'realistic_facade_assignments.json').write_text(json.dumps({'module':'hki_realistic_facades','count':len(assign),'stats':stats,'assignments':assign},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'collection':coll.name,'objects_created':[o.name for o in made],'assignment_count':len(assign),'stats':stats},ensure_ascii=False,indent=2))
