import bpy,json
from mathutils import Vector
names=['CUSTOM_1421045158_One_Taikoo_Place','CUSTOM_1421045162_Two_Taikoo_Place','CUSTOM_214672520_Lippo_Centre_Tower_1','CUSTOM_214672526_Lippo_Centre_Tower_2','CUSTOM_296457776_The_Center','CUSTOM_297109890_One_International_Finance_Centre']
for n in names:
 o=bpy.data.objects.get(n); print('\n',n,'loc',list(o.location),'rot',list(o.rotation_euler),'scale',list(o.scale),'parent',o.parent.name if o.parent else None,'coll',[c.name for c in o.users_collection], 'props',{k:str(o[k])[:200] for k in o.keys()})
 for c in o.children:
  print(' child',c.name,c.type,'loc',list(c.location),'dims',list(c.dimensions),'worldloc',list(c.matrix_world.translation))
