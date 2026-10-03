import bpy,json
x=[]
for o in bpy.data.objects:
 if '297109890' in o.name or str(o.get('osm_id',''))=='297109890': x.append({'name':o.name,'type':o.type,'osm':str(o.get('osm_id','')),'collections':[c.name for c in o.users_collection],'parent':o.parent.name if o.parent else None,'hidden':o.hide_render})
print(json.dumps(x,ensure_ascii=False))
