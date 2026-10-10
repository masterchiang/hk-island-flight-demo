import bpy, json, math, re
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>');COLL='15_Bespoke_HKAPA';DATA=ROOT/'data/processed'
# Source OSM relation/way: 865670733, Hong Kong Academy for Performing Arts, 2026-09-29 PBF.
ring=[Vector((x,y,0)) for x,y in [[-4542.059,754.103],[-4525.622,755.243],[-4474.969,759.714],[-4440.63,762.315],[-4411.052,760.387],[-4397.439,744.662],[-4389.555,735.459],[-4388.392,710.456],[-4395.062,661.766],[-4402.379,652.62],[-4412.634,647.737],[-4519.886,653.035],[-4524.277,650.389],[-4577.609,659.992],[-4596.571,674.444],[-4605.557,682.583],[-4611.05,696.182],[-4607.162,729.645],[-4592.682,744.45],[-4567.886,751.934],[-4542.059,754.103]]]
# DTM sample
import numpy as np
t=np.load(DATA/'terrain_hki.npz');tx=t['x'];ty=t['y'];tz=t['z'];c=Vector((sum(p.x for p in ring)/len(ring),sum(p.y for p in ring)/len(ring),0));ix=int(np.clip(np.searchsorted(tx,c.x)-1,0,len(tx)-1));iy=int(np.clip(np.searchsorted(ty,c.y)-1,0,len(ty)-1));base=float(tz[iy,ix])+0.8
# clear previous
old=bpy.data.collections.get(COLL)
if old:
 for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.collections.remove(old)
coll=bpy.data.collections.new(COLL);bpy.context.scene.collection.children.link(coll)
# materials
def pbr(name,color,rough=.5,metal=.0,trans=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();o=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if p.inputs.get('Transmission Weight'):p.inputs['Transmission Weight'].default_value=trans
 l.new(p.outputs['BSDF'],o.inputs['Surface']);m.diffuse_color=(*color,1);return m
mat_con=pbr('HKAPA_Concrete',(.30,.33,.31),.68,.05);mat_glass=pbr('HKAPA_Dark_Glass',(.025,.07,.085),.16,.45,.12);mat_wood=pbr('HKAPA_Warm_Wood',(.34,.18,.07),.55,.0);mat_roof=pbr('HKAPA_Roof',(.08,.10,.095),.62,.18);mat_metal=pbr('HKAPA_Metal',(.22,.26,.25),.25,.72);mat_land=pbr('HKAPA_Landscape',(.13,.22,.09),.88,.0)
# helpers
V=[];F=[];MI=[]
def prism(r,z0,z1,mi):
 s=len(V);V.extend([(p.x,p.y,z0) for p in r]+[(p.x,p.y,z1) for p in r]);n=len(r)
 for i in range(n):j=(i+1)%n;F.append((s+i,s+j,s+n+j,s+n+i));MI.append(mi)
 F.extend([tuple(s+i for i in reversed(range(n))),tuple(s+n+i for i in range(n))]);MI.extend([mi,mi])
def scale(r,fac,center):return [center+(p-center)*fac for p in r]
def box(cx,cy,sx,sy,z0,z1,mi,ang=0):
 u=Vector((math.cos(ang),math.sin(ang),0));v=Vector((-math.sin(ang),math.cos(ang),0));q=Vector((cx,cy,0));r=[q-u*sx/2-v*sy/2,q+u*sx/2-v*sy/2,q+u*sx/2+v*sy/2,q-u*sx/2+v*sy/2];prism(r,z0,z1,mi)
def curve_obj(name,segments,mat,bevel=.04):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=bevel;cu.bevel_resolution=1;cu.materials.append(mat)
 for a,b in segments:
  sp=cu.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*a,1);sp.points[1].co=(*b,1)
 ob=bpy.data.objects.new(name,cu);coll.objects.link(ob);return ob
# main campus shell: substantial lower concrete podium, stepped teaching wings, and a taller acoustic/theatre core.
# footprint in OSM already includes the distinctive multi-wing outline.
prism(ring,base,base+12,0)
# south and north classroom wings, stepped to follow the campus massing.
box(c.x-10,c.y-29,128,18,base+12,base+30,0)
box(c.x+42,c.y+4,28,78,base+12,base+42,0)
box(c.x-34,c.y+30,46,26,base+12,base+26,0)
# central performance/theatre mass with black box and auditorium crown
box(c.x+4,c.y+2,64,48,base+12,base+44,1)
box(c.x+4,c.y+7,48,34,base+44,base+66,0)
# two stepped roof terraces / fly-tower-like volumes
box(c.x-24,c.y+1,22,30,base+26,base+55,0)
box(c.x+29,c.y+2,20,26,base+26,base+58,0)
# angular roof wedges, thin roof slabs and acoustic lantern core
box(c.x+5,c.y+5,56,44,base+66,base+70,3)
box(c.x+5,c.y+5,34,26,base+70,base+76,1)
# side roof box with a sloped/stepped sequence
box(c.x-37,c.y+17,22,24,base+55,base+61,3)
box(c.x+39,c.y-17,18,22,base+58,base+64,3)
# entrance forecourt, two canopy slabs
box(c.x-39,c.y-38,52,10,base+1,base+5,1)
box(c.x+29,c.y-39,28,8,base+1,base+4,1)
mesh=bpy.data.meshes.new('HKAPA_Mass_Mesh');mesh.from_pydata(V,[],F);mesh.update();root=bpy.data.objects.new('HKAPA_Main_Campus',None);coll.objects.link(root);root.location=(0,0,0);root['osm_way_id']='865670733';root['name']='The Hong Kong Academy for Performing Arts';root['source']='OSM 2026-09-29 footprint + Lands Department DTM + official campus/theatre typology references';root['note']='Complex campus massing: stepped teaching wings, concrete podium, black-box/auditorium core, theatre roof volumes, entrance canopies; not photogrammetry.'
geo=bpy.data.objects.new('HKAPA_Main_Campus_Geometry',mesh);coll.objects.link(geo);geo.parent=root
for m in [mat_con,mat_glass,mat_wood,mat_roof,mat_metal,mat_land]:mesh.materials.append(m)
for i,p in enumerate(mesh.polygons):p.material_index=MI[i]
# detail facade rhythm: vertical fins/windows on long elevations, walkway rails and acoustic facade seams
segs=[]
for z in [base+16,base+24,base+32,base+40,base+48,base+56,base+64]:
 segs += [((c.x-72,c.y-38,z),(c.x+50,c.y-38,z)),((c.x+56,c.y-34,z),(c.x+56,c.y+42,z))]
for xx in [c.x-62,c.x-50,c.x-38,c.x-26,c.x-14,c.x-2,c.x+10,c.x+22,c.x+34,c.x+46]:segs.append(((xx,c.y-38,base+13),(xx,c.y-38,base+66)))
frames=curve_obj('HKAPA_Facade_Fins_and_Window_Bands',segs,mat_metal,.055);frames.parent=root
# entrance glass curtainwall and the main pedestrian bridge/atrium line
curves=[((c.x-25,c.y-43,base+5),(c.x+26,c.y-43,base+5)),((c.x-25,c.y-43,base+5),(c.x-25,c.y-43,base+16)),((c.x+26,c.y-43,base+5),(c.x+26,c.y-43,base+16))]
entry=curve_obj('HKAPA_Entrance_Canopy_Frame',curves,mat_metal,.12);entry.parent=root
# landscaped forecourt strips and a grid of low trees/planters
ground_segments=[]
for yoff in [-35,-29,-23]:ground_segments.append(((c.x-76,c.y+yoff,base+1),(c.x+66,c.y+yoff,base+1)))
land=curve_obj('HKAPA_Forecourt_Landscape_Edges',ground_segments,mat_land,.20);land.parent=root
# set materials physically; add glazing panes as slim front planes
V2=[];F2=[]
def panel(cx,cy,z0,z1,w,d,mi):
 s=len(V2);V2.extend([(cx-w/2,cy-d/2,z0),(cx+w/2,cy-d/2,z0),(cx+w/2,cy-d/2,z1),(cx-w/2,cy-d/2,z1)]);F2.append((s,s+1,s+2,s+3))
for xx in [c.x-56,c.x-44,c.x-32,c.x-20,c.x-8,c.x+4,c.x+16,c.x+28,c.x+40]:panel(xx,c.y-38.18,base+17,base+62,6,.12,0)
gm=bpy.data.meshes.new('HKAPA_Glass_Panels_Mesh');gm.from_pydata(V2,[],F2);gm.update();go=bpy.data.objects.new('HKAPA_Glass_Panels',gm);coll.objects.link(go);go.parent=root;gm.materials.append(mat_glass)
# save
bpy.context.scene['hkapa_complex_model']='OSM way 865670733; stepped campus and performance blocks with facade fins and entrance canopy';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print({'root':root.name,'base':base,'footprint_centroid':tuple(c),'height':round(max(p[2] for p in V)-base,2),'objects':[o.name for o in coll.objects]})

