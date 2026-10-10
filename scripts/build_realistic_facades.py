"""Standalone realistic facade/material pass for Hong Kong Island.

The module owns only the Blender collection ``11_Realistic_Facades``. It never
saves the .blend, never edits existing objects/materials, and skips the Bank of
China Tower OSM record so the original Sketchfab asset/materials remain intact.
The companion config is data/processed/realistic_facade_manifest.json.

Blender console run:
    import os
    os.environ['HKI_PROJECT_ROOT'] = r'<PROJECT_ROOT>'
    exec(compile(open(r'<PROJECT_ROOT>\\scripts\\build_realistic_facades.py', encoding='utf-8').read(), r'<PROJECT_ROOT>\\scripts\\build_realistic_facades.py', 'exec'), {'__name__': '__main__'})

Optional env: HKI_FACADE_SCOPE=all|landmarks|highrises|far_lod,
HKI_FACADE_REBUILD=0, HKI_FACADE_WRITE_ASSIGNMENTS=0,
HKI_FACADE_MAX_WINDOW_PANELS, HKI_FACADE_MAX_BALCONIES,
HKI_FACADE_MAX_AC_UNITS, HKI_FACADE_MAX_ROOF_UNITS.
"""
from __future__ import annotations
import bisect, json, math, os, re
from collections import Counter
from pathlib import Path
try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None
    Vector = None

MODULE = 'hki_realistic_facades'
COLLECTION = '11_Realistic_Facades'
ROOT_OBJECT = 'HKI_Realistic_Facades_ROOT'
MANIFEST = 'realistic_facade_manifest.json'
ASSIGNMENTS = 'realistic_facade_assignments.json'
PREFIX = 'HKI_RF_'
PROTECTED_TOKENS = ('SKETCHFAB_Bank_of_China_Tower_Primary', 'Bank_of_China_Tower')
RESIDENTIAL_KINDS = {'apartments','residential','house','semidetached_house','terrace','dormitory','flat','bungalow','cabin','hut','shed','roof'}
FALLBACK_CATEGORIES = {
    'residential': {'wall_color':[.29,.34,.36,1], 'glass_color':[.055,.16,.21,1], 'frame_color':[.18,.21,.21,1], 'accent_color':[.52,.40,.25,1], 'roughness':.54, 'glass_roughness':.18, 'metallic':.18, 'default_floor_height_m':2.85, 'feature_flags':['windows','frames','balconies','ac_units','roof_equipment']},
    'old_building': {'wall_color':[.47,.38,.28,1], 'glass_color':[.06,.12,.12,1], 'frame_color':[.16,.13,.10,1], 'accent_color':[.64,.48,.29,1], 'roughness':.68, 'glass_roughness':.27, 'metallic':.08, 'default_floor_height_m':2.75, 'feature_flags':['windows','frames','balconies','ac_units','seams','roof_equipment']},
    'glass_office': {'wall_color':[.10,.17,.20,1], 'glass_color':[.025,.11,.18,1], 'frame_color':[.22,.30,.31,1], 'accent_color':[.36,.47,.48,1], 'roughness':.34, 'glass_roughness':.10, 'metallic':.48, 'default_floor_height_m':3.65, 'feature_flags':['windows','frames','vertical_fins','roof_equipment']},
    'concrete_office': {'wall_color':[.38,.39,.37,1], 'glass_color':[.045,.11,.14,1], 'frame_color':[.16,.18,.17,1], 'accent_color':[.55,.46,.31,1], 'roughness':.62, 'glass_roughness':.22, 'metallic':.24, 'default_floor_height_m':3.35, 'feature_flags':['windows','frames','seams','roof_equipment']},
    'hotel': {'wall_color':[.50,.42,.32,1], 'glass_color':[.045,.14,.18,1], 'frame_color':[.18,.18,.16,1], 'accent_color':[.73,.53,.24,1], 'roughness':.48, 'glass_roughness':.16, 'metallic':.26, 'default_floor_height_m':3.15, 'feature_flags':['windows','frames','balconies','ac_units','podium','roof_equipment']},
    'industrial': {'wall_color':[.31,.33,.31,1], 'glass_color':[.035,.09,.10,1], 'frame_color':[.13,.14,.13,1], 'accent_color':[.55,.25,.08,1], 'roughness':.71, 'glass_roughness':.30, 'metallic':.38, 'default_floor_height_m':4.2, 'feature_flags':['windows','frames','seams','roof_equipment']},
    'school': {'wall_color':[.56,.48,.36,1], 'glass_color':[.04,.13,.16,1], 'frame_color':[.16,.17,.15,1], 'accent_color':[.68,.26,.12,1], 'roughness':.59, 'glass_roughness':.23, 'metallic':.12, 'default_floor_height_m':3.25, 'feature_flags':['windows','frames','balconies','ac_units','podium','roof_equipment']},
    'retail_podium': {'wall_color':[.24,.25,.24,1], 'glass_color':[.025,.15,.18,1], 'frame_color':[.10,.12,.11,1], 'accent_color':[.70,.38,.10,1], 'roughness':.39, 'glass_roughness':.12, 'metallic':.42, 'default_floor_height_m':4.0, 'feature_flags':['windows','frames','podium','seams','roof_equipment']},
}


def project_root():
    candidates=[]
    if os.environ.get('HKI_PROJECT_ROOT'): candidates.append(Path(os.environ['HKI_PROJECT_ROOT']))
    if globals().get('__file__'): candidates.append(Path(__file__).resolve().parents[1])
    candidates += [Path.cwd(), Path(r'<PROJECT_ROOT>')]
    for p in candidates:
        if (p/'data'/'processed'/'hki_buildings.json').exists(): return p.resolve()
    return candidates[0].resolve()


def read_json(path, fallback):
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError): return fallback


def load_config(root):
    fallback={'material_categories':FALLBACK_CATEGORIES,'classification_rules':{'name_keywords':{},'kind_map':{}},'landmark_templates':{},'run_options':{}}
    cfg=read_json(root/'data'/'processed'/MANIFEST, fallback)
    for k,v in fallback.items(): cfg.setdefault(k,v)
    return cfg


def records(root):
    payload=read_json(root/'data'/'processed'/'hki_buildings.json', {'buildings':[]})
    rows=payload.get('buildings',[]) if isinstance(payload,dict) else payload
    return [r for r in rows if isinstance(r,dict) and r.get('footprint')]


class Terrain:
    def __init__(self,path):
        self.x=[]; self.y=[]; self.z=None
        try:
            import numpy as np
            a=np.load(str(path)); self.x=[float(v) for v in a['x']]; self.y=[float(v) for v in a['y']]; self.z=a['z']
        except Exception: pass
    def sample(self,x,y):
        if self.z is None or not self.x or not self.y: return 0.0
        ix=max(0,min(len(self.x)-1,bisect.bisect_right(self.x,x)-1)); iy=max(0,min(len(self.y)-1,bisect.bisect_right(self.y,y)-1))
        try: return float(self.z[iy,ix])
        except Exception: return 0.0


def clean_ring(raw,max_points=28):
    pts=[Vector((float(p[0]),float(p[1]),0)) for p in raw if len(p)>=2]
    if len(pts)>max_points:
        step=len(pts)/max_points; pts=[pts[int(i*step)%len(pts)] for i in range(max_points)]
    out=[]
    for p in pts:
        if not out or (p-out[-1]).length>.12: out.append(p)
    if len(out)>2 and (out[0]-out[-1]).length<.12: out.pop()
    return out


def signed_area(r): return .5*sum(r[i].x*r[(i+1)%len(r)].y-r[(i+1)%len(r)].x*r[i].y for i in range(len(r)))
def area(r): return abs(signed_area(r))
def center(r): return Vector((sum(p.x for p in r)/len(r),sum(p.y for p in r)/len(r),0))
def norm_name(v): return re.sub(r'\s+',' ',str(v or '').strip()).lower()
def stable_int(v):
    s=re.sub(r'\D','',str(v)); return int(s[-8:]) if s else sum(map(ord,str(v)))
def edge_normal(a,b,r):
    d=b-a; n=Vector((d.y,-d.x,0)) if signed_area(r)>=0 else Vector((-d.y,d.x,0))
    return n.normalized() if n.length else Vector((0,1,0))


def template_for(record,cfg):
    name=str(record.get('name') or '').strip(); low=norm_name(name)
    for k,v in cfg.get('landmark_templates',{}).items():
        if norm_name(k)==low: return v
    if 'bank of china' in low and 'tower' in low: return {'template':'protected_sketchfab','category':'glass_office','features':['protected_sketchfab']}
    return None


def protected(record,tpl):
    low=norm_name(record.get('name'))
    return bool(tpl and tpl.get('template')=='protected_sketchfab') or ('bank of china' in low and 'tower' in low)


def height(record,category,cfg):
    h=float(record.get('height') or 0)
    if h>.1: return max(3.,h)
    levels=float(record.get('levels') or 0); spec=cfg.get('material_categories',{}).get(category,{})
    floor=float(spec.get('default_floor_height_m',3.0))
    if levels>0: return max(3.,levels*floor)
    return max(3.,min(45.,3.+math.sqrt(max(1.,float(record.get('area') or 1)))*.42))


def floor_height(record,category,h,cfg):
    levels=float(record.get('levels') or 0)
    if levels>=1 and h>0: return max(2.4,min(5.2,h/levels))
    return max(2.4,min(5.2,float(cfg.get('material_categories',{}).get(category,{}).get('default_floor_height_m',3.))))


def classify(record,cfg,tpl=None):
    if tpl and tpl.get('category'): return str(tpl['category'])
    name=norm_name(record.get('name')); kind=norm_name(record.get('kind') or 'yes'); rules=cfg.get('classification_rules',{})
    kws=rules.get('name_keywords',{})
    for cat in ('school','hotel','industrial','concrete_office','retail_podium','glass_office','old_building','residential'):
        if any(norm_name(w) in name for w in kws.get(cat,[])): return cat
    if kind in rules.get('kind_map',{}): return str(rules['kind_map'][kind])
    if kind in RESIDENTIAL_KINDS: return 'residential'
    return 'concrete_office' if height(record,'concrete_office',cfg)>=18 else 'old_building'


def detail_record(record,h,tpl):
    if tpl: return True
    kind=norm_name(record.get('kind') or 'yes'); name=str(record.get('name') or '').strip()
    # User requested reusable residential windowsills. Add repeatable window,
    # frame, balcony, AC and roof details to every residential block above 5m.
    if kind in RESIDENTIAL_KINDS: return h>=5.0
    if name and h>=15: return True
    if h>=35 and kind!='yes': return True
    return kind=='yes' and (bool(name) or h>=70)


class Batch:
    def __init__(self,name): self.name=name; self.vertices=[]; self.faces=[]; self.mats=[]
    def face(self,vs,mat):
        s=len(self.vertices); self.vertices += [tuple(v) for v in vs]; self.faces.append(tuple(s+i for i in range(len(vs)))); self.mats.append(mat)


def wall_quad(batch,a,b,z0,z1,n,mat,offset=.04):
    a=a+n*offset; b=b+n*offset; batch.face([(a.x,a.y,z0),(b.x,b.y,z0),(b.x,b.y,z1),(a.x,a.y,z1)],mat)


def wall_strip(batch,a,b,u0,u1,z0,z1,n,mat,offset=.08):
    d=b-a; L=d.length
    if L<.1: return
    t=d.normalized(); p0=a+t*max(0.,u0)+n*offset; p1=a+t*min(L,u1)+n*offset
    batch.face([(p0.x,p0.y,z0),(p1.x,p1.y,z0),(p1.x,p1.y,z1),(p0.x,p0.y,z1)],mat)


def oriented_box(batch,cxy,length,depth,z0,z1,tangent,outward,mat):
    if length<=.05 or depth<=.05 or z1<=z0: return
    t=tangent.normalized() if tangent.length else Vector((1,0,0)); n=outward.normalized() if outward.length else Vector((0,1,0)); c=Vector((cxy.x,cxy.y,0)); hl,hd=length*.5,depth*.5
    q=[c-t*hl-n*hd,c+t*hl-n*hd,c+t*hl+n*hd,c-t*hl+n*hd]
    batch.face([(p.x,p.y,z0) for p in q],mat); batch.face([(p.x,p.y,z1) for p in reversed(q)],mat)
    for i in range(4):
        j=(i+1)%4; batch.face([(q[i].x,q[i].y,z0),(q[j].x,q[j].y,z0),(q[j].x,q[j].y,z1),(q[i].x,q[i].y,z1)],mat)


def diagonal_strip(batch,a,b,u0,u1,z0,z1,n,width,mat,offset=.1):
    d=b-a
    if d.length<.1: return
    t=d.normalized(); du=max(.01,u1-u0); dz=z1-z0; L=math.sqrt(du*du+dz*dz); pu=-dz/L*width*.5; pz=du/L*width*.5
    p=a+t*u0+n*offset+Vector((0,0,z0)); q=a+t*u1+n*offset+Vector((0,0,z1))
    vs=[p+t*pu+Vector((0,0,pz)),q+t*pu+Vector((0,0,pz)),q-t*pu-Vector((0,0,pz)),p-t*pu-Vector((0,0,pz))]
    batch.face([(v.x,v.y,v.z) for v in vs],mat)

def add_shell(batches,r,base,top,cat):
    b=batches['shells']; wall=f'{cat}:wall'; roof=f'{cat}:roof'
    for i,a in enumerate(r): wall_quad(b,a,r[(i+1)%len(r)],base,top,edge_normal(a,r[(i+1)%len(r)],r),wall,.025)
    b.face([(p.x,p.y,top) for p in reversed(r)],roof)


def enabled(flags,*names): return any(n in set(flags or []) for n in names)


def add_seams(batches,r,base,top,h,cat,detailed):
    b=batches['seams']; mat=f'{cat}:frame'; order=sorted(range(len(r)),key=lambda i:(r[(i+1)%len(r)]-r[i]).length,reverse=True); keep=set(order[:min(4,len(r))])
    step=max(7.,min(16.,h/(3. if detailed else 2.)))
    z=base+step
    while z<top-.3:
        for i,a in enumerate(r):
            bpt=r[(i+1)%len(r)]
            if detailed or i in keep: wall_strip(b,a,bpt,0,(bpt-a).length,z-.028,z+.028,edge_normal(a,bpt,r),mat,.065)
        z+=step
    if detailed:
        for i in keep:
            a,bpt=r[i],r[(i+1)%len(r)]; L=(bpt-a).length; wall_strip(b,a,bpt,L*.5-.025,L*.5+.025,base+.15,top-.15,edge_normal(a,bpt,r),mat,.065)


def add_windows(batches,r,base,top,cat,fh,flags,limits,tpl):
    if not enabled(flags,'windows','window_grid','curtainwall'): return
    glass=batches['windows']; frames=batches['frames']; gmat=f'{cat}:glass'; fmat=f'{cat}:frame'
    podium=min(max(3.,(top-base)*(.15 if enabled(flags,'podium') else .10)),34.)
    lo,hi=base+podium+.25,top-min(2.,max(.5,(top-base)*.025))
    if hi<=lo: return
    rows=max(1,int(round((hi-lo)/max(2.4,fh)))); target=min(14 if tpl else 12,rows)
    edges=sorted([(a,r[(i+1)%len(r)]) for i,a in enumerate(r)],key=lambda ab:(ab[1]-ab[0]).length,reverse=True)[:min(6,len(r))]
    bays=[min(10,max(1,int((b-a).length/(4. if cat=='old_building' else 5.)))) for a,b in edges]
    raw=sum(bays)*target; budget=max(8,int(limits['max_window_panels'])); scale=min(1.,math.sqrt(float(budget)/max(1,raw))); row_step=max(1,int(math.ceil(1./max(scale,1e-4))))
    for (a,b),bay_count in zip(edges,bays):
        d=b-a; L=d.length
        if L<1.: continue
        n=edge_normal(a,b,r); count=max(1,min(bay_count,int(math.ceil(bay_count*scale))))
        for row in range(0,rows,row_step):
            z0=lo+row*fh+fh*.18; z1=min(hi,lo+row*fh+fh*.78)
            if z1-z0<.15: continue
            for bay in range(count):
                u0=L*bay/count+min(.18,L*.02); u1=L*(bay+1)/count-min(.18,L*.02)
                if u1<=u0+.12: continue
                wall_strip(glass,a,b,u0,u1,z0,z1,n,gmat,.075)
                wall_strip(frames,a,b,u0,u1,z0-.035,z0+.035,n,fmat,.11); wall_strip(frames,a,b,u0,u1,z1-.035,z1+.035,n,fmat,.11)
                wall_strip(frames,a,b,u0-.035,u0+.035,z0,z1,n,fmat,.11)
        if enabled(flags,'curtainwall','vertical_fins'):
            for bay in range(count+1):
                u=L*bay/count; wall_strip(frames,a,b,u-.035,u+.035,lo,hi,n,fmat,.13)


def add_balconies(batches,r,base,top,cat,fh,flags,limits):
    if not enabled(flags,'balconies'): return
    b=batches['balconies']; mat=f'{cat}:accent'; rows=max(1,int((top-base)/max(2.4,fh))); interval=max(2,int(round(9./max(2.4,fh)))); made=0
    edges=sorted([(a,r[(i+1)%len(r)]) for i,a in enumerate(r)],key=lambda ab:(ab[1]-ab[0]).length,reverse=True)[:min(3,len(r))]
    for a,bpt in edges:
        d=bpt-a; L=d.length
        if L<5.: continue
        t=d.normalized(); n=edge_normal(a,bpt,r); bays=max(1,min(3,int(L/12.)))
        for row in range(1,rows,interval):
            for bay in range(bays):
                if made>=limits['max_balconies']: return
                u0=L*(bay+.10)/bays; u1=L*(bay+.90)/bays; c=a+t*((u0+u1)*.5)+n*.52; z=base+row*fh+.1
                oriented_box(b,c,max(1.2,u1-u0),1.05,z,z+.16,t,n,mat); made+=1


def add_ac(batches,r,base,top,cat,fh,flags,limits,rid):
    if not enabled(flags,'ac_units'): return
    b=batches['ac']; mat=f'{cat}:frame'; seed=stable_int(rid); made=0; rows=max(1,int((top-base)/max(2.4,fh)))
    edges=sorted([(a,r[(i+1)%len(r)]) for i,a in enumerate(r)],key=lambda ab:(ab[1]-ab[0]).length,reverse=True)[:min(4,len(r))]
    for ei,(a,bpt) in enumerate(edges):
        d=bpt-a
        if d.length<2.: continue
        t=d.normalized(); n=edge_normal(a,bpt,r); step=2+(seed+ei)%2
        for row in range(1+(seed+ei)%2,rows,step):
            if made>=limits['max_ac_units']: return
            f=.22+.56*(((seed+row*7+ei*11)%100)/100.); c=a+d*f+n*.16; z=base+row*fh+.18
            oriented_box(b,c,.62,.28,z,z+.34,t,n,mat); made+=1


def add_roof(batches,c,r,top,cat,limits,rid):
    b=batches['roof']; mat=f'{cat}:roof'; seed=stable_int(rid); span=max(2.,min(max(p.x for p in r)-min(p.x for p in r),max(p.y for p in r)-min(p.y for p in r))); count=min(1+seed%max(1,min(3,limits['max_roof_units'])),limits['max_roof_units'])
    offsets=[(0.,0.),(.28,.16),(-.22,.25),(.18,-.27)]
    for i in range(count):
        ox,oy=offsets[(seed+i)%len(offsets)]; p=c+Vector((ox*span,oy*span,0)); length=max(1.2,min(5.,span*(.16 if i else .24))); depth=max(.9,min(3.,span*(.10 if i else .16))); hh=max(.6,min(3.,1.+top*.008))
        oriented_box(b,p,length,depth,top+.05,top+.05+hh,Vector((1,0,0)),Vector((0,1,0)),mat)


def add_landmark_accents(batches,r,base,top,cat,tpl):
    if not tpl: return
    flags=set(tpl.get('features',[])); b=batches['landmark']; amat=f'{cat}:accent'; fmat=f'{cat}:frame'; edges=sorted([(a,r[(i+1)%len(r)]) for i,a in enumerate(r)],key=lambda ab:(ab[1]-ab[0]).length,reverse=True)[:min(3,len(r))]
    if 'vertical_fins' in flags or 'faceted_fins' in flags:
        for a,bpt in edges:
            d=bpt-a; n=edge_normal(a,bpt,r); count=max(2,min(7,int(d.length/7.)))
            for i in range(1,count): wall_strip(b,a,bpt,d.length*i/count-.055,d.length*i/count+.055,base+1.,top-1.,n,amat,.16)
    if flags.intersection({'horizontal_bands','crown_bands','horizontal_trusses'}):
        levels=[.18,.38,.58,.78,.94] if 'horizontal_trusses' in flags else [.35,.67,.93]
        for q in levels:
            z=base+(top-base)*q
            for a,bpt in edges: wall_strip(b,a,bpt,0,(bpt-a).length,z-.1,z+.1,edge_normal(a,bpt,r),fmat,.17)
    if 'diagonal_braces' in flags:
        for a,bpt in edges[:2]:
            L=(bpt-a).length; n=edge_normal(a,bpt,r); diagonal_strip(b,a,bpt,L*.08,L*.92,base+(top-base)*.12,top-(top-base)*.12,n,.18,amat,.20); diagonal_strip(b,a,bpt,L*.08,L*.92,top-(top-base)*.12,base+(top-base)*.12,n,.18,amat,.20)
    if 'projecting_bays' in flags:
        for a,bpt in edges[:2]:
            d=bpt-a; t=d.normalized(); n=edge_normal(a,bpt,r)
            for q in (.28,.52,.76): oriented_box(b,a+d*q+n*.35,min(5.,max(1.5,d.length*.16)),.7,base+(top-base)*.33,top-.7,t,n,amat)
    if flags.intersection({'stepped_crown','needle_crown'}):
        for q,depth in ((.84,.60),(.91,.42),(.96,.26)):
            z=base+(top-base)*q
            for a,bpt in edges[:2]:
                d=bpt-a; n=edge_normal(a,bpt,r); oriented_box(b,(a+bpt)*.5+n*depth,d.length*.82,depth,z,z+.16,d,n,amat)
    if 'podium' in flags:
        z=base+min(max(6.,(top-base)*.14),30.)
        for a,bpt in edges: wall_strip(b,a,bpt,0,(bpt-a).length,z-.22,z+.22,edge_normal(a,bpt,r),amat,.20)
