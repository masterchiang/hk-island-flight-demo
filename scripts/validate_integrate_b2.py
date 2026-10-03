import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r"<PROJECT_ROOT>")
IDS={"590814694":"HSBC Main Building","2762122396":"Hopewell Centre","296457776":"The Center","297109890":"One International Finance Centre","200915642":"One Island East","52869536":"The Henderson","65061120":"One Exchange Square","297109906":"Two Exchange Square","297109900":"Three Exchange Square","130515428":"Highcliff"}
BOC_PREFIX="SKETCHFAB_Bank_of_China_Tower_Primary"
def world_points(o):
    pts=[]
    if o.type=='MESH':pts=[o.matrix_world@Vector(v) for v in o.bound_box]
    elif o.type=='CURVE':
        pts=[o.matrix_world@Vector(c) for s in o.data.splines for p in s.points for c in [(p.co.x,p.co.y,p.co.z)]]
    for ch in o.children:pts += world_points(ch)
    return pts
roots=[]
for o in bpy.data.objects:
    if o.type=='EMPTY' and str(o.get('osm_id','')) in IDS:
        is_b2=('B2' in o.name or o.name.startswith('BESPOKE_B2_') or o.name.startswith('CUSTOM_590814694_HSBC_Main_Building') or o.name.startswith('CUSTOM_200915642_One_Island_East'))
        if is_b2:roots.append(o)
# Hide old rough/duplicate objects for these ids, never hide BOC.
keep=set()
for r in roots:
    keep.add(r.name);keep.update(x.name for x in r.children_recursive)
for o in bpy.data.objects:
    if str(o.get('osm_id','')) in IDS and o.name not in keep and not o.name.startswith(BOC_PREFIX):
        o.hide_viewport=True;o.hide_render=True;o['superseded_by_second_batch']=True
report=[]
for r in roots:
    pts=world_points(r); name=IDS[str(r.get('osm_id'))]
    if pts:
      mn=[min(p[i] for p in pts) for i in range(3)];mx=[max(p[i] for p in pts) for i in range(3)]
      report.append({'name':name,'root':r.name,'osm_id':str(r['osm_id']),'children':len(r.children_recursive),'bbox_min':mn,'bbox_max':mx,'height_bbox':mx[2]-mn[2],'target_height':float(r.get('height_m',r.get('height_m_osm',0)))})
    else: report.append({'name':name,'root':r.name,'error':'no geometry'})
boc=bpy.data.objects.get(BOC_PREFIX)
report_meta={'revision':'2026-10-01-B2','roots':report,'root_count':len(report),'expected_root_count':10,'boc_exists':bool(boc),'boc_children':len(boc.children_recursive) if boc else -1,'boc_hidden':bool(boc.hide_render) if boc else None,'active_scene':bpy.context.scene.name,'filepath_before_save':bpy.data.filepath}
(ROOT/'data/processed/second_batch_validation.json').write_text(json.dumps(report_meta,ensure_ascii=False,indent=2),encoding='utf8')
bpy.context.scene['second_batch_revision']='2026-10-01-B2';bpy.context.scene['second_batch_root_count']=len(report);bpy.context.scene['second_batch_sources']='OSM/GIS project data + official/architectural references + street/image visual references; no copyrighted images embedded'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print(json.dumps(report_meta,ensure_ascii=False))
