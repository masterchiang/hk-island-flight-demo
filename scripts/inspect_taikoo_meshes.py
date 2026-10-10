import bpy,json
from mathutils import Vector
for c in bpy.data.collections:
 rows=[]
 for o in c.objects:
  if o.type=='MESH':
   p=[o.matrix_world@Vector(v) for v in o.bound_box];mn=[min(q[i] for q in p) for i in range(3)];mx=[max(q[i] for q in p) for i in range(3)]
   if mx[0]>-180 and mn[0]<100 and mx[1]>1250 and mn[1]<1700:
    rows.append((o.name,tuple(round(v,1) for v in mn),tuple(round(v,1) for v in mx),o.parent.name if o.parent else None,o.hide_viewport,o.hide_render))
 if rows:
  print('\n'+c.name)
  for x in rows: print(x)
