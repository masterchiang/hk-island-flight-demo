# -*- coding: utf-8 -*-
"""HKCEC bespoke rebuild - master build script (run inside Blender).

    exec(compile(open(r'<PROJECT_ROOT>\\scripts\\build_hkcec.py', encoding='utf-8').read(),
                 'build_hkcec.py', 'exec'), {'__name__': '__main__'})
"""
import sys, math, json
import bpy
from mathutils import Vector

LIB = r'<PROJECT_ROOT>\scripts\hkcec_lib.py'
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'), globals())

# ===================================================================== setup
purge()
coll = get_coll()
foot = load_footprints()
NW = ccw([tuple(p) for p in foot['new_wing']['footprint']])
OW = ccw([tuple(p) for p in foot['old_wing']['footprint']])
AT = ccw([tuple(p) for p in foot['atrium']['footprint']])

M_ROOF = mat('HKCEC_Roof_Aluminium', (0.80, 0.815, 0.835), metallic=0.85, rough=0.26)
M_ROOF_IN = mat('HKCEC_Roof_Underside', (0.52, 0.53, 0.55), metallic=0.55, rough=0.55)
M_FASCIA = mat('HKCEC_Fascia_White', (0.93, 0.935, 0.93), metallic=0.25, rough=0.30)
M_GLASS = mat('HKCEC_Glass_Teal', (0.055, 0.16, 0.175), metallic=0.35, rough=0.055, alpha=0.72)
M_MULL = mat('HKCEC_Mullion_Dark', (0.10, 0.115, 0.125), metallic=0.4, rough=0.45)
M_PANEL = mat('HKCEC_Panel_White', (0.86, 0.865, 0.855), metallic=0.05, rough=0.48)
M_CONC = mat('HKCEC_Concrete', (0.72, 0.715, 0.70), metallic=0.0, rough=0.68)
M_SLOT = mat('HKCEC_Slot_Dark', (0.025, 0.028, 0.032), metallic=0.3, rough=0.30)
M_STEEL = mat('HKCEC_Steel_Grey', (0.60, 0.61, 0.62), metallic=0.8, rough=0.40)

root = bpy.data.objects.new('BESPOKE_HKCEC_Complex', None)
root.empty_display_size = 40
coll.objects.link(root)


def reg(ob):
    ob.parent = root
    return ob


# ===================================================================== frames
u_nw, c_nw = principal_axis(NW)
# force axis to point north (towards the tip)
if math.cos(u_nw) < 0:
    pass
U = Vector((math.sin(u_nw), math.cos(u_nw)))       # (x, y) of the long axis
south_mid = Vector((NW[0][0], NW[0][1]))
# south edge midpoint = midpoint of the two min-y vertices
sy = sorted(NW, key=lambda p: p[1])[:2]
sm = Vector(((sy[0][0] + sy[1][0]) / 2.0, (sy[0][1] + sy[1][1]) / 2.0))
tip = max(NW, key=lambda p: p[1])
U = (Vector((tip[0], tip[1])) - sm).normalized()
V = Vector((U.y, -U.x))                            # points east
O = sm


def uv_of(p):
    d = Vector((p[0], p[1])) - O
    return d.dot(U), d.dot(V)


svals = [uv_of(p)[0] for p in NW]
s0, s1 = min(svals), max(svals)
LEN_NW = s1 - s0

print('[HKCEC] new wing axis %.4f,%.4f  len=%.1f m  origin=(%.1f,%.1f)' % (U.x, U.y, LEN_NW, O.x, O.y))


def axis_point(sn):
    s = s0 + (s1 - s0) * sn
    return O + U * s


def extent(sn):
    P = axis_point(sn)
    ts = ray_extent(NW, (P.x, P.y), (V.x, V.y))
    if len(ts) < 2:
        return (0.0, 0.0)
    return (ts[0], ts[-1])


# ===================================================================== 1. NEW WING
G = GROUND
POD_T = G + 9.0
HALL_T = G + 33.0

# ---- podium deck
reg(prism('HKCEC_NewWing_Podium', NW, G, POD_T, material=M_CONC))
# white banding on the podium
band_poly = inset(NW, 0.15)
for k, zz in enumerate([G + 3.4, G + 6.4]):
    reg(loft('HKCEC_NewWing_Podium_Band_%d' % k,
             [(p[0], p[1], zz) for p in band_poly],
             [(p[0], p[1], zz + 1.1) for p in band_poly],
             material=M_PANEL))

# ---- glazed hall volume
hall_poly = inset(NW, 5.0)
reg(prism('HKCEC_NewWing_Hall_Glass', hall_poly, POD_T, HALL_T, material=M_GLASS))
# floor slab bands
for k in range(5):
    zz = POD_T + 1.0 + k * (HALL_T - POD_T - 2.0) / 4.0
    ob = inset(hall_poly, -0.55)
    reg(loft('HKCEC_NewWing_Hall_Band_%d' % k,
             [(p[0], p[1], zz) for p in ob],
             [(p[0], p[1], zz + 0.95) for p in ob],
             material=M_PANEL))
# vertical mullion fins around the hall
ring = resample(inset(hall_poly, -0.35), 148)
mv, mf = [], []
for p in ring:
    i = len(mv)
    mv += [(p[0], p[1], POD_T), (p[0], p[1], HALL_T)]
    if i + 1 < len(ring) * 2:
        pass
faces = []
for i in range(0, len(ring), 2):
    j = (i + 2) % len(ring)
    a, b = i, j
    faces.append([2 * i, 2 * b, 2 * b + 1, 2 * i + 1])
reg(new_mesh('HKCEC_NewWing_Hall_Mullions', [(p[0], p[1], POD_T) for p in ring] +
             [(p[0], p[1], HALL_T) for p in ring], faces, material=M_MULL))

# ===================================================================== 2. FLYING-BIRD ROOF
# SOM 1997: aluminium-alloy shell "shaped like a bird in flight".  Thin
# double-curved skin, crisp longitudinal ridge, wide white wing-brim along the
# eave, feather scallops and a hooded beak sweeping down over the north tip.
NU, NV = 160, 104
THICK = 1.1
BRIM = 2.6                       # horizontal wing-brim width along the eave
EAVE_BASE = HALL_T - 1.6         # eave level on the flanks
RIDGE_TOP = G + 55.5             # SOM: building height 55 m
SCALLOP_K = 7.0
SCALLOP_AMP = 1.55
LIP = 1.5

NW_SMOOTH = smooth_poly(NW, passes=7, samples=160, alpha=0.6)


def sec_extent(sn):
    P = axis_point(sn)
    ts = ray_extent(NW_SMOOTH, (P.x, P.y), (V.x, V.y))
    if len(ts) < 2 or ts[-1] - ts[0] < 3.0:
        return (-1.5, 1.5)
    return (ts[0], ts[-1])


def roof_geom(sn):
    env = math.sin(math.pi * sn) ** 0.42
    eave_z = EAVE_BASE + 3.2 * env
    g = 0.5 - 0.5 * math.cos(2 * math.pi * SCALLOP_K * sn + 0.25)
    eave_z += SCALLOP_AMP * env * (g ** 0.60 - 0.45)
    rise = (RIDGE_TOP - EAVE_BASE) * (math.sin(math.pi * (0.10 + 0.80 * sn)) ** 0.72)
    ridge_z = eave_z + rise
    # hooded beak - the north end dives and cantilevers over the glass
    hook = smoothstep(0.885, 1.0, sn)
    eave_z -= 9.5 * hook ** 1.5
    ridge_z -= 6.5 * hook ** 1.5
    tl, tr = sec_extent(sn)
    tl += 2.6
    tr -= 2.6
    sc = 1.0
    mid = 0.5 * (tl + tr)
    tl = mid + (tl - mid) * sc
    tr = mid + (tr - mid) * sc
    trg = mid + 0.10 * (tr - tl) * math.sin(math.pi * sn) ** 0.6
    return dict(env=env, eave_z=eave_z, ridge_z=ridge_z, tl=tl, tr=tr, trg=trg,
                tb_l=tl - BRIM, tb_r=tr + BRIM)


def roof_profile(q, p):
    return 1.0 - (1.0 - q) ** p


def roof_z(sn, t, gg):
    """z of the aluminium skin at plan coordinate t (includes the brim)."""
    if t < gg['tl']:
        k = (gg['tl'] - t) / BRIM
        return gg['eave_z'] + LIP * (k ** 1.4) + 0.35 * k
    if t > gg['tr']:
        k = (t - gg['tr']) / BRIM
        return gg['eave_z'] + LIP * (k ** 1.4) + 0.35 * k
    if t < gg['trg']:
        q = (gg['trg'] - t) / max(0.001, gg['trg'] - gg['tl'])
        p = 1.78
    else:
        q = (t - gg['trg']) / max(0.001, gg['tr'] - gg['trg'])
        p = 2.05
    q = min(1.0, max(0.0, q))
    z = gg['ridge_z'] - (gg['ridge_z'] - gg['eave_z']) * roof_profile(q, p)
    z -= 1.9 * math.sin(math.pi * q ** 0.85) * gg['env']
    z += 1.6 * smoothstep(0.86, 1.0, q)
    return z


def roof_xy(sn, t):
    s = s0 + (s1 - s0) * sn
    return (O.x + U.x * s + V.x * t, O.y + U.y * s + V.y * t)


grid_out, grid_in, GGEOM = [], [], []
for i in range(NU + 1):
    sn = i / NU
    gg = roof_geom(sn)
    GGEOM.append(gg)
    row_o, row_i = [], []
    for j in range(NV + 1):
        t = lerp(gg['tb_l'], gg['tb_r'], j / NV)
        z = roof_z(sn, t, gg)
        x, y = roof_xy(sn, t)
        row_o.append((x, y, z))
        row_i.append((x, y, z - THICK))
    grid_out.append(row_o)
    grid_in.append(row_i)

reg(loft_grid('HKCEC_NewWing_Roof_Top', grid_out, material=M_ROOF))
reg(loft_grid('HKCEC_NewWing_Roof_Under', grid_in, material=M_ROOF_IN))

loop_pts = ([(0, j) for j in range(NV + 1)] +
            [(i, NV) for i in range(1, NU + 1)] +
            [(NU, j) for j in range(NV - 1, -1, -1)] +
            [(i, 0) for i in range(NU - 1, 0, -1)])
rim_v = [grid_out[i][j] for (i, j) in loop_pts] + [grid_in[i][j] for (i, j) in loop_pts]
rim_f = []
n = len(loop_pts)
for k in range(n):
    k2 = (k + 1) % n
    rim_f.append([k, k2, n + k2, n + k])
reg(new_mesh('HKCEC_NewWing_Roof_Fascia', rim_v, rim_f, material=M_FASCIA))

# snap-line ribs down both slopes (perpendicular to the ridge)
NRB = 15
for band, (sn_a, sn_b) in enumerate([(0.06, 0.90)]):
    rb_v, rb_f = [], []
    for k in range(NRB):
        sn = sn_a + (sn_b - sn_a) * k / (NRB - 1)
        gg = roof_geom(sn)
        top, bot = [], []
        for step in range(NV + 1):
            t = lerp(gg['tb_l'], gg['tb_r'], step / NV)
            z = roof_z(sn, t, gg)
            x, y = roof_xy(sn, t)
            top.append((x, y, z + 0.32))
            bot.append((x, y, z + 0.01))
        iv = len(rb_v)
        rb_v += top + bot
        for step in range(NV):
            a = iv + step
            rb_f.append([a, a + 1, a + NV + 2, a + NV + 1])
    reg(new_mesh('HKCEC_NewWing_Roof_Ribs', rb_v, rb_f, material=M_ROOF, smooth=False))

# skylight slots: a neat row of dark rectangles beside the ridge
NSL = 9
sl_v, sl_f = [], []
for k in range(NSL):
    sn_c = 0.19 + 0.50 * (k + 0.5) / NSL
    hw = 0.5 * (0.50 / NSL) * 0.40
    row = []
    for dsn, dq in ((-hw, 0.10), (hw, 0.10), (hw, 0.235), (-hw, 0.235)):
        gg2 = roof_geom(sn_c + dsn)
        t = lerp(gg2['trg'], gg2['tl'], dq)
        z = roof_z(sn_c + dsn, t, gg2)
        x, y = roof_xy(sn_c + dsn, t)
        row.append((x, y, z + 0.10))
    iv = len(sl_v)
    sl_v += row
    sl_f.append([iv, iv + 1, iv + 2, iv + 3])
reg(new_mesh('HKCEC_NewWing_Roof_Slots', sl_v, sl_f, material=M_SLOT))

# continuous ridge seam
cap_v, cap_f = [], []
for i in range(NU + 1):
    gg = GGEOM[i]
    z = roof_z(i / NU, gg['trg'], gg)
    x, y = roof_xy(i / NU, gg['trg'])
    cap_v.append((x, y, z - 0.06))
for i in range(NU + 1):
    gg = GGEOM[i]
    z = roof_z(i / NU, gg['trg'], gg)
    x, y = roof_xy(i / NU, gg['trg'])
    cap_v.append((x, y, z + 0.38))
for i in range(NU):
    cap_f.append([i, i + 1, NU + 2 + i, NU + 1 + i])
reg(new_mesh('HKCEC_NewWing_Roof_RidgeSeam', cap_v, cap_f, material=M_SLOT))

# ===================================================================== 3. OLD WING
G2 = GROUND
OW_TOP = G2 + 26.0
ow_axis, ow_c = principal_axis(OW)
OU = Vector((math.sin(ow_axis), math.cos(ow_axis)))
Ov = Vector((OU.y, -OU.x))
ow_s = [ (Vector((p[0], p[1])) - ow_c).dot(OU) for p in OW ]
ow_t = [ (Vector((p[0], p[1])) - ow_c).dot(Ov) for p in OW ]
OW_LEN = max(ow_s) - min(ow_s)
OW_WID = max(ow_t) - min(ow_t)
print('[HKCEC] old wing  len=%.1f wid=%.1f' % (OW_LEN, OW_WID))

reg(prism('HKCEC_OldWing_Body', OW, G2, OW_TOP, material=M_GLASS))
# horizontal louvre / slab bands - the signature 1988 elevation
NB = 13
for k in range(NB):
    zz = G2 + 2.6 + k * (OW_TOP - G2 - 3.4) / (NB - 1)
    exp = inset(OW, -0.85)
    reg(loft('HKCEC_OldWing_Louvre_%d' % k,
             [(p[0], p[1], zz) for p in exp],
             [(p[0], p[1], zz + 1.05) for p in exp],
             material=M_PANEL))
# ground floor colonnade / recess
reg(prism('HKCEC_OldWing_Base', inset(OW, -0.4), G2, G2 + 2.2, material=M_PANEL))

# ===================================================================== 4. ATRIUM
A_TOP = GROUND + 24.0
reg(prism('HKCEC_Atrium_Glass', AT, GROUND, A_TOP - 1.0, material=M_GLASS))
ring = resample(inset(AT, -0.3), 96)
faces = []
for i in range(0, len(ring), 2):
    j = (i + 2) % len(ring)
    faces.append([2 * i, 2 * j, 2 * j + 1, 2 * i + 1])
reg(new_mesh('HKCEC_Atrium_Mullions', [(p[0], p[1], GROUND) for p in ring] +
             [(p[0], p[1], A_TOP - 1.0) for p in ring], faces, material=M_MULL))
for k in range(4):
    zz = GROUND + 3.0 + k * (A_TOP - 6.0) / 3.0
    exp = inset(AT, -0.7)
    reg(loft('HKCEC_Atrium_Band_%d' % k, [(p[0], p[1], zz) for p in exp],
             [(p[0], p[1], zz + 0.9) for p in exp], material=M_PANEL))
reg(loft('HKCEC_Atrium_RoofSlab', [(p[0], p[1], A_TOP - 1.0) for p in AT],
         [(p[0], p[1], A_TOP + 0.5) for p in AT], material=M_STEEL))


# =============================================== 5. generic curved shell roof
def wing_shell(prefix, poly, eave_z, ridge_z, brim=2.4, thick=0.9,
               n_u=88, n_v=72, scallop_k=5.0, scallop_amp=1.1, inset_m=1.2,
               mat_top=None, mat_in=None):
    tgt = centroid(poly)
    axis, _ = principal_axis(poly)
    ax = Vector((math.sin(axis), math.cos(axis)))
    ay = Vector((ax.y, -ax.x))
    sp = [(Vector((q[0], q[1])) - Vector(tgt)).dot(ax) for q in poly]
    a0, a1 = min(sp), max(sp)
    sm = smooth_poly(poly, passes=5, samples=110, alpha=0.55)
    sm = inset(sm, inset_m)

    def ext(sn):
        P = Vector(tgt) + ax * (a0 + (a1 - a0) * sn)
        ts = ray_extent(sm, (P.x, P.y), (ay.x, ay.y))
        if len(ts) < 2 or ts[-1] - ts[0] < 3.0:
            return (-1.5, 1.5)
        return (ts[0], ts[-1])

    def geo(sn):
        env = math.sin(math.pi * sn) ** 0.42
        e = eave_z + 1.6 * env
        g = 0.5 - 0.5 * math.cos(2 * math.pi * scallop_k * sn + 0.25)
        e += scallop_amp * env * (g ** 0.6 - 0.45)
        r = e + (ridge_z - eave_z) * (math.sin(math.pi * (0.10 + 0.80 * sn)) ** 0.75)
        tl, tr = ext(sn)
        return dict(e=e, r=r, tl=tl + 1.0, tr=tr - 1.0)

    def zz(sn, t, gg):
        if t < gg['tl']:
            k = (gg['tl'] - t) / brim
            return gg['e'] + 1.2 * k ** 1.4 + 0.3 * k
        if t > gg['tr']:
            k = (t - gg['tr']) / brim
            return gg['e'] + 1.2 * k ** 1.4 + 0.3 * k
        trg = 0.5 * (gg['tl'] + gg['tr'])
        if t < trg:
            q = (trg - t) / max(0.001, trg - gg['tl'])
            pr = 1.75
        else:
            q = (t - trg) / max(0.001, gg['tr'] - trg)
            pr = 1.95
        q = min(1.0, max(0.0, q))
        z = gg['r'] - (gg['r'] - gg['e']) * (1.0 - (1.0 - q) ** pr)
        z += 1.2 * smoothstep(0.86, 1.0, q)
        return z

    def xy(sn, t):
        sv = a0 + (a1 - a0) * sn
        return (tgt[0] + ax.x * sv + ay.x * t, tgt[1] + ax.y * sv + ay.y * t)

    gout, gin = [], []
    for i in range(n_u + 1):
        sn = i / n_u
        g = geo(sn)
        ro, ri = [], []
        for j in range(n_v + 1):
            t = lerp(g['tl'] - brim, g['tr'] + brim, j / n_v)
            z = zz(sn, t, g)
            x, y = xy(sn, t)
            ro.append((x, y, z))
            ri.append((x, y, z - thick))
        gout.append(ro)
        gin.append(ri)
    reg(loft_grid(prefix + '_Top', gout, material=mat_top or M_ROOF))
    reg(loft_grid(prefix + '_Under', gin, material=mat_in or M_ROOF_IN))
    loop = ([(0, j) for j in range(n_v + 1)] + [(i, n_v) for i in range(1, n_u + 1)] +
            [(n_u, j) for j in range(n_v - 1, -1, -1)] + [(i, 0) for i in range(n_u - 1, 0, -1)])
    rv = [gout[i][j] for (i, j) in loop] + [gin[i][j] for (i, j) in loop]
    rf = []
    nn = len(loop)
    for k in range(nn):
        k2 = (k + 1) % nn
        rf.append([k, k2, nn + k2, nn + k])
    reg(new_mesh(prefix + '_Fascia', rv, rf, material=M_FASCIA))
    return dict(ax=ax, ay=ay, a0=a0, a1=a1, tgt=tgt, geo=geo, zz=zz, xy=xy)


# 1988 Old Wing : shallow curving hall roof over the Gloucester Road block
shell = wing_shell('HKCEC_OldWing_Roof', OW, GROUND + 26.5, GROUND + 39.0,
                   brim=2.2, thick=0.85, n_u=72, n_v=64, scallop_k=5.0,
                   scallop_amp=1.0, inset_m=1.6)
# panel seams across the old wing roof
for k in range(11):
    sn = 0.06 + 0.88 * k / 10.0
    g = shell['geo'](sn)
    top, bot = [], []
    for step in range(65):
        t = lerp(g['tl'] - 2.2, g['tr'] + 2.2, step / 64.0)
        z = shell['zz'](sn, t, g)
        x, y = shell['xy'](sn, t)
        top.append((x, y, z + 0.22))
        bot.append((x, y, z + 0.01))
    iv = len(bot) * 0 + k * 130
    if k == 0:
        globals()['_ow_rib_v'], globals()['_ow_rib_f'] = [], []
    top_arr = globals()['_ow_rib_v']
    idx = len(top_arr)
    globals()['_ow_rib_v'] += top + bot
    for step in range(64):
        globals()['_ow_rib_f'].append([idx + step, idx + step + 1,
                                       idx + step + 66, idx + step + 65])
reg(new_mesh('HKCEC_OldWing_Roof_Seams', globals()['_ow_rib_v'],
             globals()['_ow_rib_f'], material=M_ROOF, smooth=False))


# ================================================== 6. waterfront podium deck
def convex_hull(pts):
    ps = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(ps) < 3:
        return ps

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo = []
    for q in ps:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    up = []
    for q in reversed(ps):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


deck_src = (inset(NW, -26.0) + inset(AT, -22.0) + inset(OW, -22.0) +
            [(-4160, 1268), (-4080, 1272), (-4225, 1230), (-4280, 1120),
             (-4295, 950), (-4290, 800), (-4260, 720), (-4150, 700),
             (-4040, 706), (-3985, 760), (-3975, 880), (-3990, 1010),
             (-4010, 1150), (-4060, 1240)])
deck = convex_hull(deck_src)
deck = smooth_poly(deck, passes=4, samples=120, alpha=0.5)
reg(prism('HKCEC_Waterfront_Deck', deck, GROUND - 1.2, GROUND + 2.4, material=M_CONC))
reg(loft('HKCEC_Waterfront_Parapet', [(q[0], q[1], GROUND + 2.4) for q in deck],
         [(q[0], q[1], GROUND + 3.2) for q in inset(deck, 0.9)], material=M_PANEL))
# planted terrace band in front of the glazed halls
for off, zz0 in ((13.0, GROUND + 2.4),):
    pl = smooth_poly(inset(NW, -(off)), passes=3, samples=110, alpha=0.5)
    reg(loft('HKCEC_Promenade_Garden', [(q[0], q[1], zz0) for q in pl],
             [(q[0], q[1], zz0 + 0.5) for q in inset(pl, 3.0)], material=M_PANEL))

# ===================================================================== housekeeping
hide_old(['IND_52980022_New_Wing', 'IND_52980322_Old_Wing', 'IND_158889020_Atrium'])

bpy.context.view_layer.update()
print('[HKCEC] objects in %s: %d' % (COLL_NAME, len(coll.objects)))
for o in coll.objects:
    print('   ', o.name, 'polys', len(o.data.polygons) if o.type == 'MESH' else '-')
