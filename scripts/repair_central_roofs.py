import bpy,bmesh,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(bpy.data.filepath).resolve().parent
(ROOT/'output').mkdir(parents=True,exist_ok=True)
plan={'schema':2,'coordinate_conversion':'Unity local = (-Blender X, Blender Z, -Blender Y)','undergroundWays':[248781014,407885736],'meshes':[]}
targets={'HKI_RF_Shells':list(range(8860,8889))+list(range(21964,21993)), 'HKI_Remote_Residential_and_Lowrise_LOD':list(range(9338,9364))+list(range(23375,23401))}
originals={'HKI_RF_Shells':'HKI_RF_Shells_Mesh.004','HKI_Remote_Residential_and_Lowrise_LOD':'HKI_Remote_Residential_LOD_Mesh.001'}
for name,indices in targets.items():
 ob=bpy.data.objects[name]
 old=bpy.data.meshes.get(originals[name])
 if old is None:
  if ob.get('central_roof_repaired_20261010') and '_UndergroundStationsFixed' in ob.data.name:
   print('Already repaired:',name);continue
  raise RuntimeError('Original mesh missing; restore the backed-up blend before applying the repair.')
 old.use_fake_user=True
 faces=[old.polygons[i] for i in indices]
 for p in faces:
  assert (-8350<p.center.x<-7800 and 1000<p.center.y<1400) or (-7410<p.center.x<-7030 and 1150<p.center.y<1580),(p.index,list(p.center))
 ids=set(v for p in faces for v in p.vertices)
 plan['meshes'].append({'name':name,'removedFaces':len(faces),'vertices':[list(ob.matrix_world@old.vertices[v].co) for v in sorted(ids)]})
 if ob.get('central_roof_repaired_20261010') and '_UndergroundStationsFixed' in ob.data.name:
  print('Already repaired:',name);continue
 ob.data=old.copy(); ob.data.name=old.name+'_UndergroundStationsFixed'
 bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in indices],context='FACES');bm.to_mesh(ob.data);bm.free();ob.data.update()
 ob['central_roof_repaired_20261010']=True
 print('fixed',name,len(indices),len(ob.data.polygons))
# Revert the exploratory podium replacement: it was not one of the marked sites.
ob=bpy.data.objects.get('Central_Podium_320984173_Repaired')
if ob:bpy.data.objects.remove(ob,do_unlink=True)
if len(plan['meshes'])==2:
 (ROOT/'output/central_roof_repair_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
bpy.ops.object.select_all(action='DESELECT')
print('Plan written. Only the two underground stations are removed.')
