import bpy,json
from mathutils import Vector
for c in bpy.data.collections:
 rows=[]
 for o in c.objects:
  if o.type not in {'MESH','CURVE','EMPTY'}: continue
  pts=[]
  if o.type=='MESH': pts=[o.matrix_world@Vector(v) for v in o.bound_box]
  elif o.type=='CURVE': pts=[o.matrix_world@Vector(v) for v in o.bound_box]
  elif o.type=='EMPTY': pts=[o.matrix_world.translation]
  if not pts:continue
  mn=[min(p[i] for p in pts) for i in range(3)];mx=[max(p[i] for p in pts) for i in range(3)]
  if mx[0]>-150 and mn[0]<150 and mx[1]>1250 and mn[1]<1700:
   rows.append({'o':o.name,'type':o.type,'min':mn,'max':mx,'parent':o.parent.name if o.parent else None,'props':{k:str(o[k]) for k in ['name','osm_id','profile'] if k in o}})
 if rows: print('\nCOL',c.name,json.dumps(rows,ensure_ascii=False))
