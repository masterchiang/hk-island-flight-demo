import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(bpy.data.filepath).resolve().parent
(ROOT/'output').mkdir(parents=True,exist_ok=True)
if bpy.data.collections.get('18_Cessna310_Animated'):
 raise RuntimeError('Cessna preparation already exists. Reuse the existing animated collection; do not duplicate it.')
original=bpy.data.objects['Sketchfab_model.001']; meshes=[o for o in original.children_recursive if o.type=='MESH']
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)]);center=(lo+hi)*.5
coll=bpy.data.collections.new('18_Cessna310_Animated');bpy.context.scene.collection.children.link(coll)
root=bpy.data.objects.new('Cessna310',None);coll.objects.link(root)
pivots={}
for side,x in [('Left',-1.9029),('Right',1.90255)]:
 p=bpy.data.objects.new('Propeller_'+side,None);coll.objects.link(p);p.parent=root;p.location=Vector((x,-2.15684,1.461))-center;p.empty_display_type='ARROWS';p.empty_display_size=.35;pivots[side]=p
for src in meshes:
 points=[src.matrix_world@Vector(c) for c in src.bound_box]; cx=sum(p.x for p in points)/8
 prop='Prop' in src.name
 par=pivots['Right' if cx>0 else 'Left'] if prop else root
 pivot=par.location.copy() if prop else Vector((0,0,0))
 mesh=src.data.copy();mesh.transform(Matrix.Translation(-center-pivot)@src.matrix_world)
 # Mirrored source basis must keep outward-facing winding.
 if src.matrix_world.determinant()<0:mesh.flip_normals()
 obj=bpy.data.objects.new(src.name+'_Cessna',mesh);coll.objects.link(obj);obj.parent=par
for p in pivots.values():
 p.rotation_mode='XYZ';p.rotation_euler.y=0;p.keyframe_insert(data_path='rotation_euler',index=1,frame=1)
 p.rotation_euler.y=math.tau*(1600/60)*(60/(bpy.context.scene.render.fps/bpy.context.scene.render.fps_base));p.keyframe_insert(data_path='rotation_euler',index=1,frame=61)
 action=p.animation_data.action
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for kp in fc.keyframe_points:kp.interpolation='LINEAR'
     fc.modifiers.new('CYCLES')
 p.rotation_euler.y=0
bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in [root]+list(root.children_recursive):o.select_set(True)
bpy.context.view_layer.objects.active=root
project=ROOT/('My project (1)' if (ROOT/'My project (1)').exists() else 'UnityProject')
out=project/'Assets/_FlightDemo/Art/Aircraft/Cessna310/Cessna310.glb';out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)
# Retain download intact, but do not display two aircraft on top of one another.
for o in [original]+list(original.children_recursive):o.hide_set(True);o.hide_render=True
report={'dimensions':list(hi-lo),'center':list(center),'meshCount':len(meshes),'propellerMeshes':[(p.name,len(p.children)) for p in pivots.values()], 'rpm':1600}
(ROOT/'output/cessna_preparation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(report)
