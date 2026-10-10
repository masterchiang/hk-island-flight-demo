import bpy
from mathutils import Vector
from pathlib import Path

ROOT = Path(r'<PROJECT_ROOT>')
OUT = ROOT / 'output'

# ---------- Material helpers ----------
def principled(mat):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    return next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

def socket(node, name):
    return node.inputs.get(name)

def set_input(node, name, value):
    s = socket(node, name)
    if s is not None:
        s.default_value = value

def clear_material(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    return nt.nodes, nt.links

def realistic_shell(mat_name, c0, c1, roughness=0.4, metallic=0.15, scale=18.0, bump_strength=0.08):
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    nodes, links = clear_material(mat)
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 3.0
    noise.inputs['Roughness'].default_value = 0.55
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*c0, 1.0)
    ramp.color_ramp.elements[1].color = (*c1, 1.0)
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = bump_strength
    bump.inputs['Distance'].default_value = 0.08
    set_input(bsdf, 'Roughness', roughness)
    set_input(bsdf, 'Metallic', metallic)
    set_input(bsdf, 'Specular IOR Level', 0.45)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    mat.diffuse_color = (*c1, 1.0)
    mat['realistic_color_pass'] = 'HKCEC/HSBC exterior color pass 2026-10-02'
    return mat

def realistic_glass(mat_name, c0, c1, metallic=0.55, roughness=0.12, scale=4.5):
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    nodes, links = clear_material(mat)
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 2.0
    noise.inputs['Roughness'].default_value = 0.4
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*c0, 1.0)
    ramp.color_ramp.elements[1].color = (*c1, 1.0)
    coat = socket(bsdf, 'Coat Weight')
    if coat: coat.default_value = 0.28
    coat_rough = socket(bsdf, 'Coat Roughness')
    if coat_rough: coat_rough.default_value = 0.12
    set_input(bsdf, 'Roughness', roughness)
    set_input(bsdf, 'Metallic', metallic)
    set_input(bsdf, 'IOR', 1.46)
    trans = socket(bsdf, 'Transmission Weight')
    if trans: trans.default_value = 0.08
    emit = socket(bsdf, 'Emission Color')
    if emit: emit.default_value = (*c1, 1.0)
    estr = socket(bsdf, 'Emission Strength')
    if estr: estr.default_value = 0.025
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    mat.diffuse_color = (*c1, 1.0)
    mat['realistic_color_pass'] = 'HKCEC/HSBC glass color pass 2026-10-02'
    return mat

def set_simple(mat_name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    p = principled(mat)
    set_input(p, 'Base Color', (*color, 1.0))
    set_input(p, 'Metallic', metallic)
    set_input(p, 'Roughness', roughness)
    set_input(p, 'Specular IOR Level', 0.45)
    mat.diffuse_color = (*color, 1.0)
    mat['realistic_color_pass'] = 'HKCEC/HSBC exterior color pass 2026-10-02'
    return mat

# ---------- HKCEC ----------
hkcec_shell = realistic_shell('HKCEC_Panel_White', (0.68, 0.69, 0.67), (0.94, 0.93, 0.89), roughness=0.38, metallic=0.08, scale=13.0, bump_strength=0.055)
hkcec_fascia = realistic_shell('HKCEC_Fascia_White', (0.70, 0.71, 0.70), (0.98, 0.97, 0.93), roughness=0.26, metallic=0.22, scale=10.0, bump_strength=0.035)
hkcec_roof = realistic_shell('HKCEC_Roof_Aluminium', (0.40, 0.44, 0.48), (0.82, 0.85, 0.88), roughness=0.24, metallic=0.88, scale=7.5, bump_strength=0.035)
hkcec_under = realistic_shell('HKCEC_Roof_Underside', (0.018, 0.022, 0.028), (0.10, 0.12, 0.14), roughness=0.55, metallic=0.45, scale=8.0, bump_strength=0.03)
hkcec_glass = realistic_glass('HKCEC_Glass_Teal', (0.008, 0.035, 0.050), (0.025, 0.22, 0.25), metallic=0.62, roughness=0.105, scale=5.0)
hkcec_mullion = set_simple('HKCEC_Mullion_Dark', (0.018, 0.030, 0.036), metallic=0.78, roughness=0.24)
hkcec_slot = set_simple('HKCEC_Slot_Dark', (0.004, 0.007, 0.010), metallic=0.35, roughness=0.28)
hkcec_concrete = realistic_shell('HKCEC_Concrete', (0.28, 0.30, 0.30), (0.63, 0.64, 0.61), roughness=0.78, metallic=0.0, scale=9.0, bump_strength=0.12)
hkcec_paving = realistic_shell('HKCEC_Paving', (0.34, 0.33, 0.31), (0.70, 0.69, 0.64), roughness=0.82, metallic=0.0, scale=12.0, bump_strength=0.14)
hkcec_steel = realistic_shell('HKCEC_Steel_Grey', (0.22, 0.25, 0.28), (0.62, 0.65, 0.69), roughness=0.28, metallic=0.85, scale=6.0, bump_strength=0.025)

for obj in bpy.data.objects:
    if not hasattr(obj.data, 'materials'):
        continue
    for i, old in enumerate(list(obj.data.materials)):
        if not old:
            continue
        n = old.name
        replacement = None
        if n == 'HKCEC_Panel_White': replacement = hkcec_shell
        elif n == 'HKCEC_Fascia_White': replacement = hkcec_fascia
        elif n == 'HKCEC_Roof_Aluminium': replacement = hkcec_roof
        elif n == 'HKCEC_Roof_Underside': replacement = hkcec_under
        elif n == 'HKCEC_Glass_Teal': replacement = hkcec_glass
        elif n == 'HKCEC_Mullion_Dark': replacement = hkcec_mullion
        elif n == 'HKCEC_Slot_Dark': replacement = hkcec_slot
        elif n == 'HKCEC_Concrete': replacement = hkcec_concrete
        elif n == 'HKCEC_Paving': replacement = hkcec_paving
        elif n == 'HKCEC_Steel_Grey': replacement = hkcec_steel
        if replacement is not None:
            obj.data.materials[i] = replacement

# ---------- HSBC imported high-detail model ----------
hsbc_meshes = [bpy.data.objects.get('B344751569101063A1_Standardmaterial_0'), bpy.data.objects.get('B344751569101063A1_Standardmaterial_0.001')]
source = bpy.data.materials.get('Standardmaterial')
img = bpy.data.images.get('Standardmaterial_baseColor.jpeg')
if img and not img.packed_file:
    try: img.pack()
    except Exception: pass

hsbc_mat = bpy.data.materials.get('HSBC_Facade_Realistic_2026') or bpy.data.materials.new('HSBC_Facade_Realistic_2026')
nodes, links = clear_material(hsbc_mat)
out = nodes.new('ShaderNodeOutputMaterial')
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
tex = nodes.new('ShaderNodeTexImage')
tex.image = img
tex.interpolation = 'Linear'
mix = nodes.new('ShaderNodeMixRGB')
mix.blend_type = 'MULTIPLY'
mix.inputs[0].default_value = 0.68
mix.inputs[2].default_value = (0.68, 0.80, 0.90, 1.0)
noise = nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 11.0
noise.inputs['Detail'].default_value = 2.5
noise.inputs['Roughness'].default_value = 0.42
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.07
bump.inputs['Distance'].default_value = 0.035
set_input(bsdf, 'Metallic', 0.42)
set_input(bsdf, 'Roughness', 0.28)
set_input(bsdf, 'IOR', 1.48)
set_input(bsdf, 'Specular IOR Level', 0.52)
trans = socket(bsdf, 'Transmission Weight')
if trans: trans.default_value = 0.035
coat = socket(bsdf, 'Coat Weight')
if coat: coat.default_value = 0.24
coat_r = socket(bsdf, 'Coat Roughness')
if coat_r: coat_r.default_value = 0.13
links.new(tex.outputs['Color'], mix.inputs[1])
links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
links.new(noise.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
hsbc_mat.diffuse_color = (0.44, 0.56, 0.68, 1.0)
hsbc_mat['realistic_color_pass'] = 'HSBC source facade atlas tinted silver-blue; logo preserved from source texture; 2026-10-02'
for obj in hsbc_meshes:
    if obj:
        obj.data.materials.clear()
        obj.data.materials.append(hsbc_mat)

# Keep a clearly named color-pass collection without removing original organization.
pass_coll = bpy.data.collections.get('16_Realistic_Color_Passes') or bpy.data.collections.new('16_Realistic_Color_Passes')
if pass_coll.name not in [c.name for c in bpy.context.scene.collection.children]:
    bpy.context.scene.collection.children.link(pass_coll)
for obj in hsbc_meshes:
    if obj and obj.name not in [x.name for x in pass_coll.objects]:
        pass_coll.objects.link(obj)

# Scene metadata
bpy.context.scene['realistic_color_pass_date'] = '2026-10-02'
bpy.context.scene['realistic_color_pass_targets'] = 'Hong Kong Convention and Exhibition Centre; HSBC Main Building'
bpy.context.scene['realistic_color_pass_notes'] = 'HKCEC warm white shell, silver aluminium roofs, teal curtain wall and dark mullions; HSBC tinted silver-blue source facade texture with preserved logo and structural contrast.'

# ---------- Inspection renders ----------
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1000
sc.render.resolution_y = 760
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.film_transparent = False

def make_camera(name, pos, target, lens=55):
    camd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, camd)
    if cam.name not in [o.name for o in sc.collection.objects]:
        sc.collection.objects.link(cam)
    cam.location = pos
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    camd.lens = lens
    return cam

out_dir = str(OUT).replace('\\', '/') + '/'
cam_hsbc = make_camera('HKSI_HSBC_Realistic_Color_Check', (-5730, 380, 125), (-5517, 713, 90), 58)
sc.camera = cam_hsbc
sc.render.filepath = out_dir + 'hsbc_realistic_color_check.png'
bpy.ops.render.render(write_still=True)
cam_hkcec = make_camera('HKSI_HKCEC_Realistic_Color_Check', (-4520, 760, 190), (-4140, 1030, 24), 52)
sc.camera = cam_hkcec
sc.render.filepath = out_dir + 'hkcec_realistic_color_check.png'
bpy.ops.render.render(write_still=True)
# restore HSBC camera as active target for direct inspection
sc.camera = cam_hsbc
sc.render.filepath = out_dir + 'hsbc_realistic_color_check.png'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'HKI_Holographic_Atlas.blend'))
print({'hsbc_material': hsbc_mat.name, 'hsbc_meshes': [o.name for o in hsbc_meshes if o], 'hkcec_materials': [m.name for m in [hkcec_shell, hkcec_fascia, hkcec_roof, hkcec_glass]], 'renders': ['output/hsbc_realistic_color_check.png', 'output/hkcec_realistic_color_check.png']})
