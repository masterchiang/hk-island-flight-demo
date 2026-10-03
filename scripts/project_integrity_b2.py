import bpy,json
print(json.dumps({'file':bpy.data.filepath,'objects':len(bpy.data.objects),'collections':[(c.name,len(c.objects)) for c in bpy.data.collections],'images':[(i.name,bool(i.packed_file)) for i in bpy.data.images if i.source=='FILE'][:15],'packed_images':sum(1 for i in bpy.data.images if i.packed_file)},ensure_ascii=False))
