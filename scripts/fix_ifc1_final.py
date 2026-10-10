import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>');DATA=ROOT/'data/processed'
IDS={"590814694":178.8,"2762122396":216.0,"296457776":346.0,"297109890":210.0,"200915642":298.35,"52869536":190.0,"65061120":188.0,"297109906":188.0,"297109900":144.0,"130515428":241.0}
def pts(r):
 out=[]
 for o in [r]+list(r.children_recursive):
  if o.type=='MESH':out += [o.matrix_world@Vector(v) for v in o.bound_box]
  elif o.type=='CURVE':out += [o.matrix_world@Vector((p.co.x,p.co.y,p.co.z)) for s in o.data.splines for p in s.points]
 return out
r=bpy.data.objects.get('CUSTOM_297109890_IFC1_One_International_Finance_Centre')
p=pts(r);lo=min(q.z for q in p);hi=max(q.z for q in p);cur=hi-lo;target=210.0;ground=3.85
r.scale.z*=target/cur
bpy.context.view_layer.update();p=pts(r);lo=min(q.z for q in p);hi=max(q.z for q in p);r.location.z += ground-lo
bpy.context.view_layer.update()
# Rebuild reliable final validation report from world bounds.
reports=[]
for o in bpy.data.objects:
 if o.type!='EMPTY' or str(o.get('osm_id','')) not in IDS or not ('B2' in o.name or o.name.startswith(('BESPOKE_B2_2762122396','CUSTOM_590814694_HSBC','CUSTOM_200915642_One_Island_East','CUSTOM_297109890_IFC1'))):continue
 p=pts(o);lo=min(q.z for q in p);hi=max(q.z for q in p);reports.append({'name':o.get('name',o.name),'root':o.name,'osm_id':str(o['osm_id']),'bbox_min_z':lo,'bbox_max_z':hi,'model_height':hi-lo,'target_height':IDS[str(o['osm_id'])],'children':len(o.children_recursive)})
boc=bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary')
summary={'revision':'2026-10-01-B2-final2','roots':reports,'root_count':len(reports),'expected_root_count':10,'missing_ids':sorted(set(IDS)-{str(o['osm_id']) for o in bpy.data.objects if o.type=='EMPTY' and str(o.get('osm_id','')) in IDS and ('B2' in o.name or o.name.startswith(('BESPOKE_B2_2762122396','CUSTOM_590814694_HSBC','CUSTOM_200915642_One_Island_East','CUSTOM_297109890_IFC1')))}),'boc_exists':bool(boc),'boc_children':len(boc.children_recursive) if boc else -1,'boc_hidden':bool(boc.hide_render) if boc else None}
(DATA/'second_batch_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(json.dumps(summary,ensure_ascii=False))
