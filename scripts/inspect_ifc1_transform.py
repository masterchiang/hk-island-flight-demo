import bpy,json
r=bpy.data.objects.get('CUSTOM_297109890_IFC1_One_International_Finance_Centre')
print(json.dumps({'loc':list(r.location),'scale':list(r.scale),'rot':list(r.rotation_euler),'children':len(r.children_recursive),'sample':[(c.name,c.parent.name if c.parent else None,list(c.location),list(c.scale),list(c.dimensions)) for c in list(r.children)[:5]]},ensure_ascii=False))
