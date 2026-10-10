import bpy,json
from mathutils import Vector
prefixes=['BESPOKE_B2_2762122396','CUSTOM_130515428','CUSTOM_200915642','CUSTOM_296457776','CUSTOM_297109890','CUSTOM_297109900','CUSTOM_297109906','CUSTOM_52869536','CUSTOM_590814694','CUSTOM_65061120']
for r in bpy.data.objects:
 if r.type=='EMPTY' and any(r.name.startswith(p) for p in prefixes):
  pts=[]
  for o in [r]+list(r.children_recursive):
   if o.type=='MESH':pts += [o.matrix_world@Vector(v) for v in o.bound_box]
   elif o.type=='CURVE':pts += [o.matrix_world@Vector((p.co.x,p.co.y,p.co.z)) for s in o.data.splines for p in s.points]
  if pts:print(r.name, round(min(p.z for p in pts),3),round(max(p.z for p in pts),3),round(max(p.z for p in pts)-min(p.z for p in pts),3),list(r.location),list(r.scale))
