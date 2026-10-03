# -*- coding: utf-8 -*-
"""HKCEC (香港会议展览中心) bespoke model - shared helpers.

Run inside Blender.  Coordinates are the project local frame:
    X = east  (EPSG:2326 X - 840000)
    Y = north (EPSG:2326 Y - 815000)
    Z = up    (metres, DTM)
"""
import bpy, bmesh, math, json, os
from mathutils import Vector, Matrix

PROJ = r'<PROJECT_ROOT>'
FOOT_FILE = os.path.join(PROJ, 'data', 'processed', 'hkcec_footprints.json')
COLL_NAME = '14_Bespoke_HKCEC'
GROUND = 5.6


# ---------------------------------------------------------------- collection
def get_coll(name=COLL_NAME):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def purge(name=COLL_NAME):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)


# ---------------------------------------------------------------- materials
def mat(name, base, metallic=0.0, rough=0.5, alpha=1.0, emission=None, emis_str=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf is None:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
    bsdf.inputs['Base Color'].default_value = (base[0], base[1], base[2], 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = rough
    if 'Alpha' in bsdf.inputs:
        bsdf.inputs['Alpha'].default_value = alpha
    if alpha < 1.0:
        m.blend_method = 'BLEND'
    if emission is not None:
        if 'Emission Color' in bsdf.inputs:
            bsdf.inputs['Emission Color'].default_value = (emission[0], emission[1], emission[2], 1.0)
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emis_str
    return m


# ---------------------------------------------------------------- mesh utils
def new_mesh(name, verts, faces, coll=None, material=None, smooth=False, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [list(f) for f in faces])
    me.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    (coll or get_coll()).objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def prism(name, pts, z0, z1, coll=None, material=None, cap=True):
    n = len(pts)
    verts = [(p[0], p[1], z0) for p in pts] + [(p[0], p[1], z1) for p in pts]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    if cap:
        faces.append(list(range(n))[::-1])
        faces.append(list(range(n, 2 * n)))
    return new_mesh(name, verts, faces, coll, material)


def loft(name, ringA, ringB, coll=None, material=None, closed=True, smooth=False):
    """ring* = list of (x, y, z)."""
    n = len(ringA)
    verts = list(ringA) + list(ringB)
    faces = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return new_mesh(name, verts, faces, coll, material, smooth=smooth)


def loft_grid(name, grid, coll=None, material=None, smooth=True, close_u=False):
    """grid[i][j] = (x, y, z); i along u, j along v."""
    nu = len(grid)
    nv = len(grid[0])
    verts = []
    idx = {}
    for i in range(nu):
        for j in range(nv):
            idx[(i, j)] = len(verts)
            verts.append(grid[i][j])
    faces = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            faces.append([idx[(i, j)], idx[(i, j + 1)], idx[(i + 1, j + 1)], idx[(i + 1, j)]])
    return new_mesh(name, verts, faces, coll, material, smooth=smooth)


# ---------------------------------------------------------------- polygon maths
def area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s * 0.5


def centroid(pts):
    a = area(pts)
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cr = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    return (cx / (6 * a), cy / (6 * a))


def ccw(pts):
    return pts if area(pts) > 0 else pts[::-1]


def inset(pts, d, keep_shape=True):
    """Offset every vertex along the inward angle bisector by d."""
    pts = ccw(pts)
    n = len(pts)
    out = []
    for i in range(n):
        p = Vector(pts[i])
        a = Vector(pts[(i - 1) % n])
        b = Vector(pts[(i + 1) % n])
        e1 = (p - a)
        e2 = (b - p)
        if e1.length < 1e-9:
            e1 = e2
        if e2.length < 1e-9:
            e2 = e1
        e1.normalize()
        e2.normalize()
        # inward normals for CCW polygon: (dy, -dx) is outward, so inward = (-dy, dx)
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        bis = (n1 + n2)
        if bis.length < 1e-9:
            bis = n1
        bis.normalize()
        cosh = max(0.30, bis.dot(n1))
        out.append((p.x + bis.x * d / cosh, p.y + bis.y * d / cosh))
    return out


def resample(pts, n):
    """Resample a closed polygon to n points evenly by arclength."""
    lst = list(pts) + [pts[0]]
    segs = []
    total = 0.0
    for i in range(len(lst) - 1):
        a = Vector(lst[i])
        b = Vector(lst[i + 1])
        L = (b - a).length
        segs.append((a, b, L, total))
        total += L
    out = []
    for k in range(n):
        s = total * k / n
        for a, b, L, acc in segs:
            if s <= acc + L or L == 0:
                t = 0.0 if L == 0 else (s - acc) / L
                p = a.lerp(b, min(1.0, max(0.0, t)))
                out.append((p.x, p.y))
                break
    return out


def principal_axis(pts):
    """Area-weighted principal axis of a closed polygon -> (angle_rad, half_len_hint)."""
    a = area(pts)
    c = Vector(centroid(pts))
    n = len(pts)
    Ixx = Iyy = Ixy = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cr = x1 * y2 - x2 * y1
        Ixx += (y1 * y1 + y1 * y2 + y2 * y2) * cr
        Iyy += (x1 * x1 + x1 * x2 + x2 * x2) * cr
        Ixy += (x1 * y2 + 2 * x1 * y1 + 2 * x2 * y2 + x2 * y1) * cr
    Ixx /= 12.0
    Iyy /= 12.0
    Ixy /= 24.0
    theta = 0.5 * math.atan2(2 * Ixy, Ixx - Iyy)
    return theta, c


def smooth_poly(pts, passes=6, samples=140, alpha=0.55):
    """Resample then Laplacian-smooth a closed polygon (keeps it a simple loop)."""
    ps = [Vector(p) for p in resample(pts, samples)]
    n = len(ps)
    for _ in range(passes):
        new = []
        for i in range(n):
            a = ps[(i - 1) % n]
            b = ps[i]
            c = ps[(i + 1) % n]
            m = (a + c) * 0.5
            new.append(b.lerp(m, alpha))
        ps = new
    return [(p.x, p.y) for p in ps]


def ray_extent(pts, P, d):
    """Intersect the infinite line P + t*d with the closed polygon, return sorted t's."""
    ts = []
    n = len(pts)
    dx, dy = d[0], d[1]
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        det = ex * (-dy) - (-dx) * ey
        if abs(det) < 1e-9:
            continue
        rx, ry = P[0] - ax, P[1] - ay
        k = (rx * (-dy) - (-dx) * ry) / det
        t = (ex * ry - rx * ey) / det
        if -1e-6 <= k <= 1 + 1e-6:
            ts.append(t)
    ts.sort()
    return ts


def smoothstep(a, b, x):
    t = (x - a) / (b - a) if b != a else 0.0
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hide_old(names):
    for n in names:
        o = bpy.data.objects.get(n)
        if o:
            def rec(x, v=False):
                x.hide_viewport = v
                x.hide_render = v
                for ch in x.children:
                    rec(ch, v)
            rec(o, True)


def load_footprints():
    with open(FOOT_FILE, encoding='utf-8') as f:
        return json.load(f)
