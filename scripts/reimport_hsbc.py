"""Export only the two complete HSBC source meshes without changing island geometry.
Run inside the project's live Blender. Keeps a fake-user pre-fix material backup.
"""
import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(bpy.data.filepath).resolve().parent
project = ROOT / ('My project (1)' if (ROOT / 'My project (1)').exists() else 'UnityProject')
out = project / 'Assets/_FlightDemo/Art/World/HSBC/HSBC_MainBuilding_Opaque.glb'
out.parent.mkdir(parents=True, exist_ok=True)
sources = [bpy.data.objects[n] for n in ('B344751569101063A1_Standardmaterial_0', 'B344751569101063A1_Standardmaterial_0.001')]
material = bpy.data.materials['HSBC_Facade_Realistic_2026']
backup_name = 'HSBC_Facade_BeforeOpaqueFix_20261010'
if not bpy.data.materials.get(backup_name):
    backup = material.copy()
    backup.name = backup_name
    backup.use_fake_user = True
p = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
p.inputs['Transmission Weight'].default_value = 0.0
p.inputs['Alpha'].default_value = 1.0
material['hsbc_unity_fix'] = 'Opaque full-facade atlas: no transmission / transparent sorting; geometry and UV unchanged.'
selection = list(bpy.context.selected_objects)
active = bpy.context.view_layer.objects.active
collection = bpy.data.collections.new('__HSBC_ExportOnly__')
bpy.context.scene.collection.children.link(collection)
copies = []
report = {'asset': str(out), 'source': bpy.data.filepath, 'meshes': []}
try:
    bpy.ops.object.select_all(action='DESELECT')
    for i, src in enumerate(sources):
        obj = src.copy()
        obj.data = src.data.copy()
        obj.parent = None
        obj.name = 'HSBC_MainBuilding_Facade_%02d' % (i + 1)
        collection.objects.link(obj)
        obj.matrix_world = src.matrix_world.copy()
        obj.hide_viewport = False
        obj.hide_render = False
        obj.hide_set(False)
        obj.select_set(True)
        copies.append(obj)
        pts = [src.matrix_world @ Vector(v) for v in src.bound_box]
        report['meshes'].append({'source': src.name, 'export': obj.name, 'vertices': len(src.data.vertices), 'polygons': len(src.data.polygons), 'world_bounds': [[min(v[k] for v in pts), max(v[k] for v in pts)] for k in range(3)], 'uv_layers': len(src.data.uv_layers), 'custom_normals': src.data.has_custom_normals})
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB', use_selection=True, export_animations=False, export_yup=True)
finally:
    for obj in copies:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(collection)
    for obj in selection:
        if obj.name in bpy.context.view_layer.objects:
            obj.select_set(True)
    if active and active.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = active
(ROOT / 'output/hsbc_blender_export.json').write_text(json.dumps(report, indent=2), encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'HKI_Holographic_Atlas.blend'))
print(json.dumps(report))
