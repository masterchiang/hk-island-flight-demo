# -*- coding: utf-8 -*-
"""HKCEC camera + render helper (run inside Blender)."""
import bpy, math, os
from mathutils import Vector

PROJ = r'<PROJECT_ROOT>'
OUT = os.path.join(PROJ, 'output', 'hkcec')
os.makedirs(OUT, exist_ok=True)

CAMS = {
    # name: (location, target, lens_mm)
    'HKCEC_Cam_NW_Eye':   ((-4680, 1430, 48),  (-4125, 1035, 26), 50),
    'HKCEC_Cam_W_Eye':    ((-4830, 980, 40),   (-4130, 1020, 26), 55),
    'HKCEC_Cam_N_Elev':   ((-4180, 1830, 34),  (-4128, 1050, 24), 72),
    'HKCEC_Cam_SW_Aerial':((-4900, 330, 300),  (-4130, 1080, 28), 45),
    'HKCEC_Cam_NE_Aerial':((-3560, 1760, 300), (-4130, 1010, 24), 45),
    'HKCEC_Cam_S_Aerial': ((-4240, 100, 360),  (-4130, 1060, 26), 45),
    'HKCEC_Cam_N_Aerial': ((-4150, 1790, 330), (-4130, 1030, 18), 50),
    'HKCEC_Cam_Top':      ((-4130, 1045, 520), (-4130, 1044, 0),  50),
    'HKCEC_Cam_Detail_N': ((-4380, 1430, 90),  (-4135, 1150, 40), 60),
    'HKCEC_Cam_Detail_SE':((-3830, 640, 80),   (-4120, 900, 30),  55),
    'HKCEC_Cam_Front_Far':((-4130, 2600, 40),  (-4128, 1000, 30), 105),
    'HKCEC_Cam_Hero_W':   ((-4980, 1180, 150), (-4120, 1010, 22), 60),
    'HKCEC_Cam_Hero_NW':  ((-4620, 1560, 120), (-4125, 1040, 26), 55),
}


def make_cam(name, loc, target, lens=50):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cd = bpy.data.cameras.new(name)
        cam = bpy.data.objects.new(name, cd)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.clip_start = 1.0
    cam.data.clip_end = 20000.0
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return cam


def build_all():
    for n, (loc, tgt, lens) in CAMS.items():
        make_cam(n, loc, tgt, lens)
    return list(CAMS)


def render(cam_name, out_name, res=(1000, 700), samples=24, engine='BLENDER_EEVEE'):
    sc = bpy.context.scene
    cam = bpy.data.objects[cam_name]
    sc.camera = cam
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(OUT, out_name)
    bpy.ops.render.render(write_still=True)
    return os.path.join(OUT, out_name + '.png')


if __name__ == '__main__':
    import sys
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build_all()
    names = args if args else ['HKCEC_Cam_SW_Aerial']
    for n in names:
        print('RENDER', n, render(n, 'chk_' + n.replace('HKCEC_Cam_', '')))
