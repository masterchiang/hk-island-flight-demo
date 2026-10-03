import bpy,runpy,json
ROOT=r'<PROJECT_ROOT>'
results=[]
ns=runpy.run_path(ROOT+r'\scripts\agent_hopewell_b2.py',run_name='b2_hopewell');results.append(('hopewell',ns['build']()))
runpy.run_path(ROOT+r'\scripts\agent_the_center_b2.py',run_name='b2_center');results.append(('center','top_level'))
ns=runpy.run_path(ROOT+r'\scripts\agent_ifc1_b2.py',run_name='b2_ifc1');results.append(('ifc1',ns['build_ifc1_b2']().name))
ns=runpy.run_path(ROOT+r'\scripts\agent_henderson_b2.py',run_name='b2_henderson');results.append(('henderson',ns['build_henderson_b2']().name))
print(json.dumps(results,ensure_ascii=False))
