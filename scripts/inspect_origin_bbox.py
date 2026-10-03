import bpy,json
from mathutils import Vector
for n in ['CUSTOM_1421045158_One_Taikoo_Place','CUSTOM_214672520_Lippo_Centre_Tower_1','CUSTOM_296457776_The_Center','CUSTOM_297109890_One_International_Finance_Centre']:
 o=bpy.data.objects[n]; p=[]
 for c in o.children_recursive:
  if c.type=='MESH':p += [c.matrix_world@Vector(v) for v in c.bound_box]
  elif c.type=='CURVE':p += [c.matrix_world@Vector(corner) for corner in c.bound_box]
 print(n,'bbox', [round(min(q[i] for q in p),1) for i in range(3)], [round(max(q[i] for q in p),1) for i in range(3)],'rootloc',list(o.location))
