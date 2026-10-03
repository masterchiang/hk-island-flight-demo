import bpy
from mathutils import Vector
r=bpy.data.objects.get('CUSTOM_297109890_IFC1_One_International_Finance_Centre')
pts=[]
for o in [r]+list(r.children_recursive):
 if o.type=='MESH':pts += [o.matrix_world@Vector(v) for v in o.bound_box]
 elif o.type=='CURVE': pts += [o.matrix_world@Vector((p.co.x,p.co.y,p.co.z)) for s in o.data.splines for p in s.points]
print('bbox',min(p.z for p in pts),max(p.z for p in pts),'height',max(p.z for p in pts)-min(p.z for p in pts))
