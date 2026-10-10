#!/usr/bin/env python3
# HK Island transport module. Extract with project .venv; build inside Blender.
# Does not open, reset, or save the main .blend. Build owns only HKI_Transport.
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

VERSION = '1.0.0'
ROOT = Path(__file__).resolve().parents[1]
PBF = ROOT/'data/raw/hong-kong-260929.osm.pbf'
BOUNDARY = ROOT/'data/raw/island_geometry.json'
DATA = ROOT/'data/processed/hki_transport.json'
TERRAIN = ROOT/'data/processed/terrain_hki.npz'
CRS, OX, OY = 'EPSG:2326', 840000.0, 815000.0
DRIVE = {'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service','track'}
WALK = {'pedestrian','footway','path','steps','cycleway','bridleway'}
RAIL = {'rail','light_rail','tram','subway','funicular','narrow_gauge','monorail'}
ROUTES = {'bus','tram','train','subway','light_rail','railway','funicular','trolleybus','monorail'}
STOP_ROLES = {'stop','platform','station','stop_entry_only','stop_exit_only','platform_entry_only','platform_exit_only'}
WIDTH = {'motorway':17.5,'motorway_link':8,'trunk':14,'trunk_link':8,'primary':11.5,'primary_link':7,'secondary':9,'secondary_link':6.5,'tertiary':7,'tertiary_link':5.5,'unclassified':6,'residential':5.6,'living_street':5,'service':4.2,'track':3,'pedestrian':4,'footway':2.2,'path':1.5,'steps':1.8,'cycleway':2.8,'bridleway':2}
TAG_KEYS = {'highway','railway','route','type','name','name:en','ref','network','operator','lanes','oneway','width','maxspeed','surface','service','access','foot','bicycle','bridge','tunnel','layer','junction','sidewalk','barrier','route_ref','public_transport','bus','tram','station','wheelchair','colour','colour:hex'}

def num(v):
    if v is None: return None
    m=re.search(r'[-+]?\d+(?:\.\d+)?',str(v).lower().replace(',',''))
    try: return float(m.group()) if m else None
    except (ValueError, AttributeError): return None

def tags_keep(t): return {str(k):str(v) for k,v in t.items() if k in TAG_KEYS and v not in (None,'')}
def name_of(t): return str(t.get('name:en') or t.get('name') or '')[:160]
def local(x,y): return [round(float(x)-OX,2),round(float(y)-OY,2)]
def file_hash(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def extract(pbf=PBF,boundary_file=BOUNDARY,out=DATA):
    import osmium
    from pyproj import Transformer
    from shapely.geometry import shape, LineString, Point
    from shapely.ops import transform
    from shapely.prepared import prep
    tr=Transformer.from_crs('EPSG:4326',CRS,always_xy=True)
    boundary=transform(tr.transform,shape(json.loads(Path(boundary_file).read_text(encoding='utf8')))); prepared=prep(boundary)
    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways={}; self.stops={}; self.routes=[]; self.hw=Counter(); self.rw=Counter(); self.skips=0
        def node(self,n):
            t=dict(n.tags)
            if not n.location.valid() or not (t.get('highway')=='bus_stop' or t.get('bus')=='yes' or t.get('public_transport') in {'platform','stop_position','station'} or t.get('railway') in {'station','halt','tram_stop','stop','subway_entrance'} or t.get('tram')=='yes'): return
            x,y=tr.transform(n.lon,n.lat)
            if not prepared.covers(Point(x,y)): return
            typ='tram' if t.get('railway')=='tram_stop' or t.get('tram')=='yes' else ('rail' if t.get('railway') in {'station','halt','stop','subway_entrance'} else 'bus')
            self.stops[int(n.id)]={'id':int(n.id),'type':typ,'name':name_of(t),'ref':str(t.get('ref') or t.get('local_ref') or ''),'point':local(x,y),'source_tags':tags_keep(t)}
        def way(self,w):
            t=dict(w.tags); hw=str(t.get('highway') or ''); rw=str(t.get('railway') or ''); barrier=str(t.get('barrier') or '')
            if not (hw in DRIVE|WALK or rw in RAIL or barrier=='guard_rail'): return
            if hw:self.hw[hw]+=1
            if rw:self.rw[rw]+=1
            coords=[]; ids=[]
            try:
                for n in w.nodes:
                    ids.append(int(n.ref))
                    if n.location.valid(): coords.append(tr.transform(n.lon,n.lat))
            except Exception: self.skips+=1; return
            if len(coords)<2:return
            line=LineString(coords)
            if not prepared.intersects(line):return
            clipped=line.intersection(boundary); parts=[]
            geoms=[clipped] if clipped.geom_type=='LineString' else list(getattr(clipped,'geoms',[]))
            for g in geoms:
                if g.geom_type!='LineString' or g.length<0.5:continue
                pts=[]
                for x,y in g.coords:
                    q=local(x,y)
                    if not pts or math.dist(q,pts[-1])>=0.05:pts.append(q)
                if len(pts)>=2:parts.append(pts)
            if not parts:return
            explicit=num(t.get('width')); lanes=num(t.get('lanes'))
            width=explicit if explicit and 1<=explicit<=60 else (max(WIDTH.get(hw,5),lanes*3.25+0.45) if lanes and 1<=lanes<=12 else WIDTH.get(hw,WIDTH.get(rw,5)))
            self.ways[int(w.id)]={'id':int(w.id),'highway':hw or None,'railway':rw or None,'guardrail':barrier=='guard_rail','name':name_of(t),'width_m':round(width,2),'lanes':int(lanes) if lanes and lanes>0 else None,'oneway':str(t.get('oneway','')) in {'yes','true','1'},'bridge':str(t.get('bridge','')) in {'yes','true','1'},'tunnel':str(t.get('tunnel','')) in {'yes','true','1'},'layer':num(t.get('layer')) or 0,'parts':parts,'node_ids':ids,'source_tags':tags_keep(t)}
        def relation(self,r):
            t=dict(r.tags); rt=str(t.get('route') or '')
            if t.get('type')!='route' or rt not in ROUTES:return
            members=[int(m.ref) for m in r.members if m.type=='w']
            stopids=[int(m.ref) for m in r.members if m.type=='n' and str(m.role or '') in STOP_ROLES]
            color=str(t.get('colour:hex') or t.get('colour') or '')
            if not re.fullmatch(r'#[0-9A-Fa-f]{6}',color):color=''
            self.routes.append({'id':int(r.id),'route':rt,'name':name_of(t),'ref':str(t.get('ref') or ''),'network':str(t.get('network:en') or t.get('network') or ''),'colour':color,'member_way_ids':members,'stop_node_ids':stopids,'source_tags':tags_keep(t)})
    h=Handler(); print('[transport] reading PBF...',flush=True); h.apply_file(str(pbf),locations=True)
    roads=[]; walks=[]; rails=[]; guards=[]; index={}
    for wid,row in sorted(h.ways.items()):
        common={'id':wid,'name':row['name'],'parts':row['parts'],'node_ids':row['node_ids'],'bridge':row['bridge'],'tunnel':row['tunnel'],'layer':row['layer'],'source_tags':row['source_tags']}
        if row['highway'] in DRIVE:
            r={**common,'highway':row['highway'],'width_m':row['width_m'],'lanes':row['lanes'],'oneway':row['oneway']}; roads.append(r); index[wid]=r
        if row['highway'] in WALK:
            r={**common,'highway':row['highway'],'width_m':row['width_m']}; walks.append(r); index[wid]=r
        if row['railway'] in RAIL:
            r={**common,'railway':row['railway']}; rails.append(r); index[wid]=r
        if row['guardrail']:
            r={**common}; guards.append(r); index[wid]=r
    routes=[]
    for r in sorted(h.routes,key=lambda x:x['id']):
        inside=[wid for wid in r['member_way_ids'] if wid in index]
        stops=[nid for nid in r['stop_node_ids'] if nid in h.stops]
        if inside or stops:r['member_way_ids']=inside;r['stop_node_ids']=stops;routes.append(r)
    # Endpoint clusters with >=3 distinct road ways become cheap crosswalk anchors.
    clusters=defaultdict(lambda:{'x':[],'y':[],'ids':set(),'angles':[]})
    for r in roads:
        for part in r['parts']:
            if len(part)<2:continue
            for i,j in ((0,1),(-1,-2)):
                x,y=part[i]; q=clusters[(round(x/2),round(y/2))];q['x'].append(x);q['y'].append(y);q['ids'].add(r['id']);q['angles'].append(math.atan2(y-part[j][1],x-part[j][0]))
    junctions=[]
    for q in clusters.values():
        if len(q['ids'])>=3:
            junctions.append({'x':round(sum(q['x'])/len(q['x']),2),'y':round(sum(q['y'])/len(q['y']),2),'radius_m':6.0,'road_ids':sorted(q['ids']),'angles_rad':[round(a,4) for a in q['angles'][:6]]})
    junctions.sort(key=lambda x:(x['x'],x['y']))
    dataset={'meta':{'schema':'hki_transport_v1','extractor':'scripts/build_transport.py','version':VERSION,'source_pbf':Path(pbf).name,'source_date':'2026-09-29','source_boundary':Path(boundary_file).name,'source_hashes':{'pbf_sha256':file_hash(Path(pbf)),'boundary_sha256':file_hash(Path(boundary_file))},'crs':CRS,'origin_hk1980':[OX,OY],'coordinate_units':'metres','counts':{'roads':len(roads),'walkways':len(walks),'railways':len(rails),'guardrails':len(guards),'transit_routes':len(routes),'stops':len(h.stops),'junctions':len(junctions),'skipped_ways':h.skips},'highway_counts_in_pbf':h.hw.most_common(),'railway_counts_in_pbf':h.rw.most_common()},'roads':roads,'walkways':walks,'railways':rails,'guardrails':guards,'transit_routes':routes,'stops':[h.stops[k] for k in sorted(h.stops)],'junctions':junctions}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dataset,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    print(json.dumps({'output':str(out),'bytes':out.stat().st_size,'counts':dataset['meta']['counts']},ensure_ascii=False,indent=2),flush=True)
    return dataset

# Blender-only helpers: mesh batches keep the scene object count low.
def build(data_path=DATA,terrain_path=TERRAIN):
    import bpy
    d=json.loads(Path(data_path).read_text(encoding='utf8')); meta=d['meta']
    def remove_tree(c):
        for child in list(c.children):remove_tree(child)
        for ob in list(c.objects):bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.collections.remove(c)
    old=bpy.data.collections.get('HKI_Transport')
    if old:remove_tree(old)
    root=bpy.data.collections.new('HKI_Transport');bpy.context.scene.collection.children.link(root)
    groups={}
    for nm in ('RoadSurfaces','Sidewalks_Curbs','Markings','Intersections','Rail_Tram','Stops_Guardrails','Metadata'):
        c=bpy.data.collections.new(nm);root.children.link(c);groups[nm]=c
    def mat(name,color,rough=.85,metal=0):
        m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF') or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;m['transport_generated']=True;return m
    asphalt=mat('TR_Asphalt_Natural',(0.075,.078,.078),.94); walkmat=mat('TR_Concrete',(0.34,.34,.32)); white=mat('TR_Marking_White',(.9,.9,.86),.6); yellow=mat('TR_Marking_Yellow',(.95,.64,.08),.6); steel=mat('TR_Rail_Steel',(.22,.24,.26),.4,.7); transit=mat('TR_Transit_Route',(.75,.16,.08),.6); stopmat=mat('TR_Stop_Marker',(.95,.5,.08),.6)
    try:
        import numpy as np
        t=np.load(str(terrain_path)); tx=t['x'];ty=t['y'];tz=t['z']
        def ground(x,y):
            ix=max(0,min(len(tx)-1,round((x-float(tx[0]))/float(tx[1]-tx[0]))));iy=max(0,min(len(ty)-1,round((y-float(ty[0]))/float(ty[1]-ty[0]))));return float(tz[iy,ix])
    except Exception:
        def ground(x,y):return 0.0
    def make_mesh(name,collection,verts,faces,material,props=None):
        if not faces:return None
        me=bpy.data.meshes.new(name+'Mesh');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);collection.objects.link(ob);me.materials.append(material)
        for k,v in (props or {}).items():ob[k]=v
        return ob
    class Batch:
        def __init__(self):self.v=[];self.f=[]
        def quad(self,pts):
            n=len(self.v);self.v.extend(pts);self.f.append(tuple(range(n,n+len(pts))))
        def strip(self,pts,width,offset=0,zadd=.1):
            if len(pts)<2:return
            left=[];right=[];half=width/2
            for i,(x,y,z) in enumerate(pts):
                a=pts[max(0,i-1)];b=pts[min(len(pts)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];ll=math.hypot(dx,dy) or 1;nx=-dy/ll;ny=dx/ll
                left.append((x+nx*(offset+half),y+ny*(offset+half),z+zadd));right.append((x+nx*(offset-half),y+ny*(offset-half),z+zadd))
            for i in range(len(pts)-1):self.quad((left[i],left[i+1],right[i+1],right[i]))
        def box(self,x,y,z,sx,sy,sz,angle=0):
            ux=(math.cos(angle),math.sin(angle));uy=(-ux[1],ux[0]);base=len(self.v)
            for zz in (z,z+sz):
                for yy in (-sy/2,sy/2):
                    for xx in (-sx/2,sx/2):self.v.append((x+ux[0]*xx+uy[0]*yy,y+ux[1]*xx+uy[1]*yy,zz))
            self.f.extend([(base,base+1,base+3,base+2),(base+4,base+6,base+7,base+5),(base,base+4,base+5,base+1),(base+1,base+5,base+7,base+3),(base+3,base+7,base+6,base+2),(base+2,base+6,base+4,base)])
    def points(rec,part,z=.12):
        out=[]
        for x,y in part:
            x=float(x);y=float(y);extra=(.25+float(rec.get('layer') or 0)*3.5) if rec.get('bridge') else (-.3 if rec.get('tunnel') else 0)
            out.append((x,y,ground(x,y)+extra+z))
        return out
    def offset_line(p, amount):
        out=[]
        for i,(x,y,z) in enumerate(p):
            a=p[max(0,i-1)];b=p[min(len(p)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];ll=math.hypot(dx,dy) or 1
            nx=-dy/ll;ny=dx/ll;out.append((x+nx*amount,y+ny*amount,z))
        return out
    def dash_line(p,dash_len=3.0,gap=6.0):
        out=[];pattern=dash_len+gap;carry=0.0
        for a,b in zip(p,p[1:]):
            dx=b[0]-a[0];dy=b[1]-a[1];dz=b[2]-a[2];length=math.sqrt(dx*dx+dy*dy+dz*dz)
            if length<.05:continue
            pos=0.0
            while pos<length:
                phase=(carry+pos)%pattern;step=min(pattern-phase,length-pos)
                if phase<dash_len:
                    end=min(length,pos+min(dash_len-phase,length-pos))
                    if end-pos>.05:
                        f0=pos/length;f1=end/length
                        out.append([(a[0]+(b[0]-a[0])*f0,a[1]+(b[1]-a[1])*f0,a[2]+(b[2]-a[2])*f0+.025),(a[0]+(b[0]-a[0])*f1,a[1]+(b[1]-a[1])*f1,a[2]+(b[2]-a[2])*f1+.025)])
                pos+=max(step,.05)
            carry=(carry+length)%pattern
        return out
    road_batches=defaultdict(Batch);side=Batch();walk=Batch();edgewhite=[];edgyellow=[];dash=[]
    roadparts={}
    for r in d.get('roads',[]):
        hw=r['highway'];w=float(r.get('width_m') or WIDTH.get(hw,5));roadparts[r['id']]=r
        for part in r['parts']:
            p=points(r,part);road_batches[hw].strip(p,w);sw=1.25 if hw in {'trunk','primary','secondary','tertiary','unclassified','residential','living_street','service'} else 0
            if sw:
                side.strip(p,sw,(w+sw)/2,.18);side.strip(p,sw,-(w+sw)/2,.18)
            if hw in {'motorway','trunk','primary','secondary','tertiary'}:
                for sign in (-1,1):
                    shoulder=offset_line(p,sign*(w/2-.18));edgewhite.append([(x,y,z+.015) for x,y,z in shoulder])
                    if hw in {'primary','secondary','tertiary'}:
                        kerb=offset_line(p,sign*(w/2+.10));edgyellow.append([(x,y,z+.02) for x,y,z in kerb])
                if len(p)>1 and int(r.get('lanes') or 0)>=2:
                    dash.extend(dash_line(p))
    for hw,b in sorted(road_batches.items()):make_mesh('TR_Road_'+hw,groups['RoadSurfaces'],b.v,b.f,asphalt,{'source':'OpenStreetMap highway','highway':hw})
    make_mesh('TR_Sidewalks',groups['Sidewalks_Curbs'],side.v,side.f,walkmat,{'source':'procedural offsets from OSM road widths'})
    for w in d.get('walkways',[]):
        for part in w['parts']:walk.strip(points(w,part,.16),float(w.get('width_m') or 2))
    make_mesh('TR_Walkways',groups['Sidewalks_Curbs'],walk.v,walk.f,walkmat,{'source':'OpenStreetMap pedestrian ways'})
    def curve_obj(name,collection,lines,material,bevel,props=None):
        if not lines:return
        c=bpy.data.curves.new(name+'Curve','CURVE');c.dimensions='3D';c.bevel_depth=bevel;c.bevel_resolution=0;c.resolution_u=1
        for line in lines:
            if len(line)<2:continue
            s=c.splines.new('POLY');s.points.add(len(line)-1)
            for q,p in zip(s.points,line):q.co=(*p,1)
        c.materials.append(material);o=bpy.data.objects.new(name,c);collection.objects.link(o)
        for k,v in (props or {}).items():o[k]=v
    curve_obj('TR_EdgeLines_White',groups['Markings'],edgewhite,white,.025,{'source':'OSM road edges'})
    curve_obj('TR_CenterLines_Yellow',groups['Markings'],edgyellow,yellow,.022,{'source':'procedural urban yellow curb/edge markings'})
    curve_obj('TR_LaneLines_Dashed_White',groups['Markings'],dash,white,.020,{'source':'OSM lanes + procedural dashed lane separators'})
    # Crosswalk bars only at clustered multi-road endpoints.
    cross=Batch()
    for j in d.get('junctions',[]):
        x,y=float(j['x']),float(j['y']);z=ground(x,y)+.24
        for i in range(5):cross.box(x+(i-2)*.85,y,z,5.5,.38,.025,0)
    make_mesh('TR_Crosswalks',groups['Intersections'],cross.v,cross.f,white,{'source':'derived from clustered OSM road endpoints'})
    rail_lines=[];route_lines=[]
    for r in d.get('railways',[]):
        for part in r['parts']:
            p=points(r,part,.28);rail_lines.append(p)
    curve_obj('TR_RailAndTram_Centerlines',groups['Rail_Tram'],rail_lines,steel,.065,{'source':'OpenStreetMap railway ways'})
    wayparts=defaultdict(list)
    for r in d.get('roads',[])+d.get('walkways',[])+d.get('railways',[]):
        for part in r['parts']:wayparts[r['id']].append((r,part))
    # Route geometry is capped for display cost; full relation inventory stays in JSON.
    selected=defaultdict(list);seen=Counter()
    for rt in sorted(d.get('transit_routes',[]),key=lambda r:(r['route'],r['id'])):
        mode=rt['route'];cap={'bus':30,'tram':20,'train':16,'subway':20,'light_rail':12,'railway':8,'funicular':4}.get(mode,8)
        if seen[mode]>=cap:continue
        seen[mode]+=1
        for wid in rt['member_way_ids']:
            for rec,part in wayparts.get(wid,[]):selected[mode].append(points(rec,part,.38))
    for mode,lines in selected.items():curve_obj('TR_Route_'+mode,groups['Rail_Tram'],lines,transit,.035,{'source':'OpenStreetMap route relation','mode':mode,'displayed_relations':seen[mode]})
    # Low-poly stop markers and OSM guardrail beams, instanced into two meshes.
    stopb=Batch()
    for s in d.get('stops',[]):
        x,y=s['point'];z=ground(x,y)+.22;stopb.box(x,y,z,.22,.22,.8)
    make_mesh('TR_Stops_Batched',groups['Stops_Guardrails'],stopb.v,stopb.f,stopmat,{'source':'OpenStreetMap bus_stop/public_transport/railway nodes','count':len(d.get('stops',[]))})
    gb=Batch()
    for r in d.get('guardrails',[]):
        for part in r['parts']:
            p=points(r,part,.2)
            for a,b in zip(p,p[1:]):
                dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
                if length>.25:gb.box((a[0]+b[0])/2,(a[1]+b[1])/2,max(a[2],b[2])+.8,length,.09,.12,math.atan2(dy,dx))
    make_mesh('TR_Guardrails_Batched',groups['Stops_Guardrails'],gb.v,gb.f,steel,{'source':'OpenStreetMap barrier=guard_rail'})
    metaob=bpy.data.objects.new('HKI_Transport_Metadata',None);groups['Metadata'].objects.link(metaob)
    for k,v in {'module':'independent HK Island transport','generator':'scripts/build_transport.py','version':VERSION,'source_pbf':meta.get('source_pbf',''),'source_pbf_sha256':meta.get('source_hashes',{}).get('pbf_sha256',''),'source_boundary':meta.get('source_boundary',''),'crs':meta.get('crs',''),'roads':len(d.get('roads',[])),'railways':len(d.get('railways',[])),'transit_routes':len(d.get('transit_routes',[])),'stops':len(d.get('stops',[])),'terrain_drape':'terrain_hki.npz when available','geometry_note':'widths, sidewalks and lane markings are visualization estimates, not survey data'}.items():metaob[k]=v
    for k,v in {'source_pbf_sha256':meta.get('source_hashes',{}).get('pbf_sha256',''),'data_schema':meta.get('schema',''),'road_count':len(d.get('roads',[]))}.items():root[k]=v
    summary={'collection':root.name,'roads':len(d.get('roads',[])),'walkways':len(d.get('walkways',[])),'railways':len(d.get('railways',[])),'routes':len(d.get('transit_routes',[])),'stops':len(d.get('stops',[])),'junctions':len(d.get('junctions',[])),'saved_main_blend':False}
    print(json.dumps(summary,ensure_ascii=False,indent=2));return summary

def main():
    av=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    ap=argparse.ArgumentParser(description='Extract OSM transport or build isolated Blender collection')
    g=ap.add_mutually_exclusive_group();g.add_argument('--extract',action='store_true');g.add_argument('--build',action='store_true')
    ap.add_argument('--pbf',type=Path,default=PBF);ap.add_argument('--boundary',type=Path,default=BOUNDARY);ap.add_argument('--data',type=Path,default=DATA);ap.add_argument('--terrain',type=Path,default=TERRAIN)
    a=ap.parse_args(av)
    if a.extract:extract(a.pbf,a.boundary,a.data)
    elif a.build:build(a.data,a.terrain)
    elif 'bpy' in sys.modules:build(a.data,a.terrain)
    else:ap.print_help()
if __name__=='__main__':main()


