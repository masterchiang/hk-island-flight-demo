# -*- coding: utf-8 -*-
"""HKCEC v2 rebuild - frame helpers + reliable offscreen renderer.

Exec inside Blender:
    LIB = r'<PROJECT_ROOT>\\scripts\\hkv2_lib.py'
    exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'), globals())

Rendering uses the standard EEVEE pipeline through camera objects.
    Do NOT create GPUOffScreen contexts and do NOT save 2-vertex loops as faces:
    both crash Blender 5.2 when driven via MCP (see edge_mesh/safe_save).
"""
import bpy, math, json, os
from mathutils import Matrix, Vector

# reuse all geometry / material helpers
_LIB1 = r'<PROJECT_ROOT>\scripts\hkcec_lib.py'
exec(compile(open(_LIB1, encoding='utf-8').read(), _LIB1, 'exec'), globals())

OUTDIR = r'<PROJECT_ROOT>\output\hkcec'


# ---------------------------------------------------------------- frame setup
def build_frame():
    foot = load_footprints()
    NW = ccw([tuple(p) for p in foot['new_wing']['footprint']])
    OW = ccw([tuple(p) for p in foot['old_wing']['footprint']])
    AT = ccw([tuple(p) for p in foot['atrium']['footprint']])
    sy = sorted(NW, key=lambda p: p[1])[:2]
    sm = Vector(((sy[0][0] + sy[1][0]) / 2.0, (sy[0][1] + sy[1][1]) / 2.0))
    tip = max(NW, key=lambda p: p[1])
    U = (Vector((tip[0], tip[1])) - sm).normalized()
    V = Vector((U.y, -U.x))
    O = sm

    def uv_of(p):
        d = Vector((p[0], p[1])) - O
        return d.dot(U), d.dot(V)

    svals = [uv_of(p)[0] for p in NW]
    s0, s1 = min(svals), max(svals)
    return dict(NW=NW, OW=OW, AT=AT, U=U, V=V, O=O, s0=s0, s1=s1,
                LEN=s1 - s0, GROUND=GROUND)


def axis_point(F, sn):
    return F['O'] + F['U'] * (F['s0'] + (F['s1'] - F['s0']) * sn)


def section_extent(F, poly, sn):
    P = axis_point(F, sn)
    ts = ray_extent(poly, (P.x, P.y), (F['V'].x, F['V'].y))
    if len(ts) < 2 or ts[-1] - ts[0] < 3.0:
        return (-1.5, 1.5)
    return (ts[0], ts[-1])


# ---------------------------------------------------------------- mesh utils
def edge_mesh(name, edges_vert, material=None, smooth=False):
    """Build a mesh made ONLY of edges. edges_vert = list of ((x,y,z),(x,y,z)).
    Never feed 2-vertex loops to from_pydata as faces - that creates an invalid
    polygon kind that crashes the draw cache (mesh_render_data_faces_sorted)."""
    verts = []
    edges = []
    for a, b in edges_vert:
        i = len(verts)
        verts += [tuple(a), tuple(b)]
        edges.append([i, i + 1])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    me.update()
    if smooth:
        pass
    ob = bpy.data.objects.new(name, me)
    get_coll().objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def safe_save():
    """Save without rendering a .blend preview thumbnail. Thumbnail rendering
    runs an offscreen draw immediately after fresh geometry is created; combined
    with a large depsgraph it crashes mesh batch cache generation."""
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    bpy.ops.wm.save_mainfile()
    return bpy.data.filepath


# ---------------------------------------------------------------- rendering
# Render sizes are per-camera so the orthographic framing (sensor_fit=HORIZONTAL)
# shows the full subject on both axes.
RENDER_SIZES = {
    'TV_Front': (820, 560),
    'TV_Side':  (820, 340),
    'TV_Top':   (620, 860),
}


def render_cam(cam_name, filename, width=None):
    """Render through a camera using the standard EEVEE pipeline (stable under
    MCP automation - no GPUOffScreen contexts). Restores prior render setup."""
    sc = bpy.context.scene
    cam = bpy.data.objects[cam_name]
    cam.data.sensor_fit = 'HORIZONTAL'
    old = dict(cam=sc.camera, x=sc.render.resolution_x, y=sc.render.resolution_y,
               pct=sc.render.resolution_percentage, fmt=sc.render.image_settings.file_format)
    w, h = RENDER_SIZES.get(cam_name, (820, 560))
    if width:
        h = int(h * width / w)
        w = width
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, filename)
    bpy.ops.render.render(write_still=False)
    img = bpy.data.images.get('Render Result')
    img.save_render(path)
    # restore
    sc.camera = old['cam']
    sc.render.resolution_x = old['x']
    sc.render.resolution_y = old['y']
    sc.render.resolution_percentage = old['pct']
    sc.render.image_settings.file_format = old['fmt']
    return path


def three_view(tag, cams=('TV_Front', 'TV_Side', 'TV_Top'), maxw=820):
    """Render the three orthographic views; returns (front, side, top) paths."""
    paths = []
    for cam, suffix in zip(cams, ('front', 'side', 'top')):
        paths.append(render_cam(cam, '%s_%s.png' % (tag, suffix), maxw))
    return paths


# ---------------------------------------------------------------- TV cameras
def ensure_tv_cameras(elevation=30.0):
    foot = load_footprints()
    allpts = []
    for key in ('new_wing', 'old_wing', 'atrium'):
        allpts += [tuple(p) for p in foot[key]['footprint']]
    xs = [p[0] for p in allpts]
    ys = [p[1] for p in allpts]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    Wd = max(xs) - min(xs)
    Hd = max(ys) - min(ys)
    P = GROUND

    def make(name, loc, scale):
        c = bpy.data.objects.get(name)
        if c:
            bpy.data.objects.remove(c, do_unlink=True)
        cd = bpy.data.cameras.new(name)
        cd.type = 'ORTHO'
        cd.ortho_scale = scale
        cd.sensor_fit = 'HORIZONTAL'
        cd.clip_start = 0.5
        cd.clip_end = 20000.0
        c = bpy.data.objects.new(name, cd)
        c.location = loc
        bpy.context.scene.collection.objects.link(c)
        return c

    cF = make('TV_Front', (cx, cy + 900, P + elevation), Wd + 110)
    cS = make('TV_Side', (cx - 900, cy, P + elevation), Hd + 110)
    cT = make('TV_Top', (cx, cy, P + 900), Wd + 110)
    for c, tgt in ((cF, (cx, cy, P + elevation - 2)),
                   (cS, (cx, cy, P + elevation - 2)),
                   (cT, (cx, cy, 0))):
        c.rotation_euler = (Vector(tgt) - c.location).to_track_quat('-Z', 'Y').to_euler()
    return dict(cx=cx, cy=cy)
