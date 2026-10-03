import bpy, runpy, json
ROOT=r'<PROJECT_ROOT>'
# Clean only identifiable failed B2 artifacts from a prior attempt.
runpy.run_path(ROOT+r'\\scripts\\cleanup_b2_temp.py',run_name='cleanup_b2')
# Group 1: Hopewell, The Center, IFC1, Henderson.
ns=runpy.run_path(ROOT+r'\\scripts\\agent_hopewell_b2.py',run_name='b2_hopewell'); print(ns['build']())
runpy.run_path(ROOT+r'\\scripts\\agent_the_center_b2.py',run_name='b2_center')
ns=runpy.run_path(ROOT+r'\\scripts\\agent_ifc1_b2.py',run_name='b2_ifc1'); print(ns['build_ifc1_b2']().name)
ns=runpy.run_path(ROOT+r'\\scripts\\agent_henderson_b2.py',run_name='b2_henderson'); print(ns['build_henderson_b2']().name)
# Group 2: HSBC, One Island East, Exchange Square and Highcliff.
runpy.run_path(ROOT+r'\\scripts\\agent_hsbc_b2.py',run_name='b2_hsbc')
runpy.run_path(ROOT+r'\\scripts\\agent_one_island_east_b2.py',run_name='b2_oie')
ns=runpy.run_path(ROOT+r'\\scripts\\agent_exchange_highcliff_b2.py',run_name='b2_exchange'); print(ns['build_all']())
# Validate and save.
runpy.run_path(ROOT+r'\\scripts\\validate_integrate_b2.py',run_name='validate_b2')
print('FULL B2 PIPELINE COMPLETE', bpy.data.filepath)
