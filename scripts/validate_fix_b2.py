import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>')
IDS={"590814694":"HSBC Main Building","2762122396":"Hopewell Centre","296457776":"The Center","297109890":"One International Finance Centre","200915642":"One Island East","52869536":"The Henderson","65061120":"One Exchange Square","297109906":"Two Exchange Square","297109900":"Three Exchange Square","130515428":"Highcliff"}
def b2root(o):
 n=o.name
 return o.type=='EMPTY' and (('B2' in n) or n.startswith('BESPOKE_B2_2762122396') or n.startswith('CUSTOM_590814694_HSBC') or n.startswith('CUSTOM_200915642_One_Island_East'))
def pts(o):
 out=[]
 if o.type=='MESH':out += [o.matrix_world@Vector(v) for v in o.bound_box]
 elif o.type=='CURVE':
  out += [o.matrix_world@Vector((p.co.x,p.co.y,p.co.z)) for s in o.data.splines for p in s.points]
 for c in o.children:out+=pts(c)
 return out
roots=[o for o in bpy.data.objects if b2root(o) and str(o.get('osm_id','')) in IDS]
keep=set()
for r in roots:keep.update([r.name]+[x.name for x in r.children_recursive])
for o in bpy.data.objects:
 if str(o.get('osm_id','')) in IDS and o.name not in keep:
  for x in [o]+list(o.children_recursive):
   x.hide_viewport=True;x.hide_render=True;x['superseded_by_second_batch']=True
report=[]
for r in roots:
 p=pts(r);mn=[min(q[i] for q in p) for i in range(3)];mx=[max(q[i] for q in p) for i in range(3)]
 report.append({'name':IDS[str(r['osm_id'])],'root':r.name,'osm_id':str(r['osm_id']),'children':len(r.children_recursive),'bbox_min':mn,'bbox_max':mx,'height_bbox':mx[2]-mn[2],'target_height':float(r.get('height_m',r.get('height_m_osm',0)))})
boc=bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary')
data={'revision':'2026-10-01-B2','roots':report,'root_count':len(report),'expected_root_count':10,'all_targets_present':len(report)==10,'boc_exists':bool(boc),'boc_children':len(boc.children_recursive) if boc else -1,'boc_hidden':bool(boc.hide_render) if boc else None,'hidden_old_objects':sum(1 for o in bpy.data.objects if o.get('superseded_by_second_batch'))}
(ROOT/'data/processed/second_batch_validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
bpy.context.scene['second_batch_revision']='2026-10-01-B2';bpy.context.scene['second_batch_root_count']=len(report);bpy.context.scene['second_batch_validation']='10 target roots; legacy matching ids hidden recursively; Bank of China Tower preserved'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(json.dumps(data,ensure_ascii=False))
