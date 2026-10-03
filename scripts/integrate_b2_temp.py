import bpy,json,importlib.util,runpy
# This wrapper is executed in Blender; it imports agent modules without invoking their main blocks.
ROOT=r'<PROJECT_ROOT>'
mods=[
 ('hsbc','scripts/agent_hsbc_b2.py','top'),
 ('hopewell','scripts/agent_hopewell_b2.py','build'),
 ('center','scripts/agent_the_center_b2.py','top'),
 ('ifc1','scripts/agent_ifc1_b2.py','build_ifc1_b2'),
 ('oie','scripts/agent_one_island_east_b2.py','top'),
 ('henderson','scripts/agent_henderson_b2.py','build_henderson_b2'),
 ('exchange','scripts/agent_exchange_highcliff_b2.py','build_all'),
]
results=[]
# Run top-level modules only where they are designed as standalone scripts.
for label,rel,fn in mods:
 path=ROOT+'\\'+rel
 ns=runpy.run_path(path,run_name='__b2_'+label)
 if fn and fn != 'top': results.append((label,ns[fn]()))
 else: results.append((label,'top_level_done'))
# Snapshot roots by metadata/name.
rows=[]
for o in bpy.data.objects:
 if o.type=='EMPTY' and (o.get('agent_batch')=='second_batch' or str(o.get('osm_id','')) in {'590814694','200915642','52869536','130515428','65061120','297109906','297109900','2762122396','296457776','297109890'} and ('B2' in o.name or 'IFC1' in o.name or 'HENDERSON' in o.name)):
  rows.append({'name':o.name,'osm_id':str(o.get('osm_id','')),'height':o.get('height_m',o.get('height_m_osm')),'children':len(o.children),'loc':list(o.location)})
print(json.dumps({'results':results,'roots':rows,'boc':[o.name for o in bpy.data.objects if o.name.startswith('SKETCHFAB_Bank_of_China_Tower_Primary')],'boc_children':len(bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary').children_recursive) if bpy.data.objects.get('SKETCHFAB_Bank_of_China_Tower_Primary') else -1},ensure_ascii=False))
