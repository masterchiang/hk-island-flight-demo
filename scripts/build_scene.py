import bpy, json, math, os, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(r"<PROJECT_ROOT>")
DATA=ROOT/'data/processed'
BUILDINGS=json.loads((DATA/'hki_buildings.json').read_text(encoding='utf-8'))
terrain=np.load(DATA/'terrain_hki.npz')

# Reset to an intentional, reproducible scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass
for c in list(bpy.data.collections):
    if c.name != 'Collection': bpy.data.collections.remove(c)

scene=bpy.context.scene
scene.name='HKI_Holographic_Atlas'
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1280
scene.render.resolution_y=720
scene.render.resolution_percentage=70
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(ROOT/'output/hki_hologram_preview.png')
scene.render.use_compositing=False
scene.render.film_transparent=False
scene.render.use_freestyle=False
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=1.8
scene.view_settings.gamma=1

# World and compositor for the cyan hologram / night atlas look.
world=bpy.data.worlds.get('HKI_Night_World') or bpy.data.worlds.new('HKI_Night_World')
scene.world=world; world.use_nodes=True
wn=world.node_tree.nodes; wl=world.node_tree.links; wn.clear()
bg=wn.new('ShaderNodeBackground'); bg.inputs['Color'].default_value=(0.001,0.004,0.012,1); bg.inputs['Strength'].default_value=0.12
wo=wn.new('ShaderNodeOutputWorld'); wl.new(bg.outputs['Background'],wo.inputs['Surface'])
scene.use_nodes=True
# Blender 5.2 native compositor is optional here; emission materials provide the holographic glow.
try:
    cn=scene.node_tree.nodes; cl=scene.node_tree.links; cn.clear()
    rl=cn.new('CompositorNodeRLayers'); glare=cn.new('CompositorNodeGlare'); glare.glare_type='FOG_GLOW'; glare.quality='HIGH'; glare.threshold=0.5; glare.size=7
    comp=cn.new('CompositorNodeComposite'); cl.new(rl.outputs['Image'],glare.inputs['Image']); cl.new(glare.outputs['Image'],comp.inputs['Image'])
except Exception as _compositor_error:
    print('compositor skipped',_compositor_error)


# Collections
def coll(name):
    c=bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in scene.collection.children: scene.collection.children.link(c)
    return c
terrain_coll=coll('01_Terrain'); city_coll=coll('02_HKI_Buildings'); landmark_coll=coll('03_Landmarks'); viz_coll=coll('04_Visualization'); road_coll=coll('05_Roads')

# Material helpers.
def emission_mat(name, color, strength=1.0, alpha=1.0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear()
    out=n.new('ShaderNodeOutputMaterial'); em=n.new('ShaderNodeEmission'); em.inputs['Color'].default_value=(*color,alpha); em.inputs['Strength'].default_value=strength
    l.new(em.outputs['Emission'],out.inputs['Surface'])
    m.diffuse_color=(*color,alpha)
    if alpha<1:
        m.surface_render_method='DITHERED'
    return m

def holo_mat(name, base, accent, scale=1.0, strength=1.2):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear()
    out=n.new('ShaderNodeOutputMaterial')
    tex=n.new('ShaderNodeTexCoord')
    brick=n.new('ShaderNodeTexBrick'); brick.offset=0.0; brick.offset_frequency=2
    brick.inputs['Color1'].default_value=(*base,1); brick.inputs['Color2'].default_value=(*accent,1); brick.inputs['Mortar'].default_value=(0.0,0.55,0.9,1)
    brick.inputs['Scale'].default_value=scale; brick.inputs['Mortar Size'].default_value=0.035; brick.inputs['Mortar Smooth'].default_value=0.008
    ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=0.18; ramp.color_ramp.elements[0].color=(0.003,0.012,0.03,1); ramp.color_ramp.elements[1].position=0.78; ramp.color_ramp.elements[1].color=(0.01,0.42,0.75,1)
    em=n.new('ShaderNodeEmission'); em.inputs['Strength'].default_value=strength
    l.new(tex.outputs['UV'],brick.inputs['Vector']); l.new(brick.outputs['Color'],ramp.inputs['Fac']); l.new(ramp.outputs['Color'],em.inputs['Color']); l.new(em.outputs['Emission'],out.inputs['Surface'])
    m.diffuse_color=(*accent,1)
    m['material_role']='procedural hologram facade with window grid'; m['source']='procedural, no external image license'
    return m

def wire_mat(name, color=(0.01,0.75,1.0), strength=2.0, thickness=0.003):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear(); out=n.new('ShaderNodeOutputMaterial'); em=n.new('ShaderNodeEmission'); wf=n.new('ShaderNodeWireframe'); wf.inputs['Size'].default_value=thickness; em.inputs['Color'].default_value=(*color,1); em.inputs['Strength'].default_value=strength; l.new(wf.outputs['Fac'],em.inputs['Strength']); l.new(em.outputs['Emission'],out.inputs['Surface']); return m

mat_low=holo_mat('Holo_Facade_Lowrise',(0.008,0.12,0.22),(0.01,0.38,0.58),scale=3.0,strength=0.55)
mat_res=holo_mat('Holo_Facade_Residential',(0.008,0.16,0.28),(0.01,0.68,0.85),scale=4.8,strength=0.75)
mat_tower=holo_mat('Holo_Facade_Tower',(0.004,0.10,0.28),(0.01,0.82,1.0),scale=7.0,strength=0.95)
mat_special=holo_mat('Holo_Facade_Landmark',(0.02,0.18,0.32),(0.25,0.95,1.0),scale=9.0,strength=1.25)
mat_terrain=emission_mat('Holo_Terrain',(0.006,0.028,0.055),0.35)
mat_sea=emission_mat('Holo_Sea',(0.001,0.008,0.02),0.4)
mat_grid=emission_mat('Holo_Grid',(0.006,0.12,0.24),0.7)
mat_road=emission_mat('Holo_Roads',(0.0,0.12,0.25),0.55)

# Terrain mesh, sampled from Lands Department 5 m DTM at 25 m for whole-island context.
x=terrain['x']; y=terrain['y']; z=terrain['z']; mask=terrain['mask']
verts=[(float(xj),float(yi),float(z[i,j])) for i,yi in enumerate(y) for j,xj in enumerate(x)]
terrain_faces=[]
for i in range(mask.shape[0]):
    for j in range(mask.shape[1]):
        if mask[i,j]:
            a=i*len(x)+j; terrain_faces.append((a,a+1,a+1+len(x),a+len(x)))
mesh=bpy.data.meshes.new('HKI_Terrain_DTM25m'); mesh.from_pydata(verts,[],terrain_faces); mesh.update()
obj=bpy.data.objects.new('HKI_Terrain_DTM25m',mesh); terrain_coll.objects.link(obj); obj.data.materials.append(mat_terrain)
obj['source']='Hong Kong Lands Department Whole_HK_DTM_5m.zip'; obj['derived_resolution_m']=25; obj['crs']='EPSG:2326'; obj['coverage']='Hong Kong Island OSM relation 4556901'
# subtle terrain wire overlay
wire=obj.copy(); wire.data=obj.data.copy(); wire.name='HKI_Terrain_ContourWire'; terrain_coll.objects.link(wire); wire.data.materials.clear(); wire.data.materials.append(mat_grid)
mod=wire.modifiers.new('Subtle terrain grid','WIREFRAME'); mod.thickness=0.35; mod.use_replace=True

# Sea/background plane.
bpy.ops.mesh.primitive_plane_add(size=32000, location=(0,0,-5))
sea=bpy.context.object; sea.name='Victoria_Harbour_Context';
for c in list(sea.users_collection): c.objects.unlink(sea)
terrain_coll.objects.link(sea); sea.data.materials.append(mat_sea); sea['source']='context plane; not a bathymetry model'

# DTM sampler for building bases.
def sample_z(px,py):
    ix=int(np.clip(np.searchsorted(x,px)-1,0,len(x)-1)); iy=int(np.clip(np.searchsorted(y,py)-1,0,len(y)-1));
    return float(z[iy,ix])

# Road network from the same OSM extract, rendered as thin luminous linework.
try:
    roads=json.loads((DATA/'hki_roads.json').read_text(encoding='utf-8'))['roads']
    widths={'motorway':2.5,'trunk':2.0,'primary':1.6,'secondary':1.35,'tertiary':1.0,'unclassified':0.75,'residential':0.55,'living_street':0.5,'service':0.35,'pedestrian':0.3,'track':0.28,'cycleway':0.25}
    groups={}
    for rd in roads:
        k=rd.get('kind','residential'); groups.setdefault(widths.get(k,0.35),[]).append(rd)
    for width,rows in groups.items():
        cu=bpy.data.curves.new('HKI_Roads_'+str(width),'CURVE'); cu.dimensions='3D'; cu.bevel_depth=width; cu.bevel_resolution=0; cu.resolution_u=1
        for rd in rows:
            pts=rd.get('points',[])
            if len(pts)<2: continue
            sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
            for pnt,co in zip(sp.points,pts):
                px,py=co; pnt.co=(px,py,sample_z(px,py)+1.2,1)
        ob=bpy.data.objects.new('HKI_Roads_width_'+str(width),cu); road_coll.objects.link(ob); cu.materials.append(mat_road); ob['source']='OSM highway ways, 2026-09-29'; ob['width_class_m']=width
except Exception as _road_error:
    print('roads skipped',_road_error)

# Generate one optimized mesh for all island buildings with per-building UVs.
records=BUILDINGS['buildings']; V=[]; F=[]; UV=[]; MI=[]; centers=[]
for bi,b in enumerate(records):
    ring=b['footprint']; n=len(ring)
    if n<3:continue
    cx=sum(p[0] for p in ring)/n; cy=sum(p[1] for p in ring)/n; base=sample_z(cx,cy); h=float(b['height'])
    # Bring buildings slightly above the DTM to avoid z-fighting; retain real relative heights.
    base+=0.6
    start=len(V)
    V.extend([(float(px),float(py),base) for px,py in ring]); V.extend([(float(px),float(py),base+h) for px,py in ring])
    faces=[]; uvs=[]
    faces.append(tuple(start+i for i in reversed(range(n)))); uvs.append([(0,0)]*n)
    faces.append(tuple(start+n+i for i in range(n))); uvs.append([(0, h/3.0)]*n)
    # stable perimeter distance for facade windows
    per=[]; total=0.0
    for i in range(n):
        p0=ring[i];p1=ring[(i+1)%n]; per.append(total); total+=math.hypot(p1[0]-p0[0],p1[1]-p0[1])
    for i in range(n):
        j=(i+1)%n; faces.append((start+i,start+j,start+n+j,start+n+i));
        u0=per[i]/4.0;u1=(per[i]+math.hypot(ring[j][0]-ring[i][0],ring[j][1]-ring[i][1]))/4.0; v1=h/3.0
        uvs.append([(u0,0),(u1,0),(u1,v1),(u0,v1)])
    F.extend(faces);UV.extend(uvs)
    kind=b.get('kind','yes');
    if b.get('name') and (h>=40 or 'tower' in kind or 'office' in kind): mat_index=3
    elif h>=90: mat_index=2
    elif h>=20 or kind in ('apartments','residential','hotel','dormitory'): mat_index=1
    else: mat_index=0
    MI.extend([mat_index]*len(faces)); centers.append((cx,cy,base,h,b))

bmesh=bpy.data.meshes.new('HKI_Buildings_Procedural_Facades'); bmesh.from_pydata(V,[],F); bmesh.update()
city=bpy.data.objects.new('HKI_Buildings_15k_Procedural_Facades',bmesh); city_coll.objects.link(city)
for m in (mat_low,mat_res,mat_tower,mat_special):bmesh.materials.append(m)
for i,p in enumerate(bmesh.polygons):p.material_index=MI[i]
uv=bmesh.uv_layers.new(name='BuildingFacadeUV')
for p,coords in zip(bmesh.polygons,UV):
    for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
city['source']='OpenStreetMap Geofabrik Hong Kong extract 2026-09-29'; city['source_license']='ODbL 1.0; attribution required'; city['building_count']=len(records); city['height_method']='OSM height/building:levels, conservative procedural fallback when missing'; city['facade_method']='procedural UV brick/window shader; not photo-identical'
# Luminous edge overlay makes dense blocks legible in the game-like atlas view without duplicating building geometry.
bmesh.materials.append(mat_grid)
edge=city.copy(); edge.name='HKI_Building_EdgeGlow'; city_coll.objects.link(edge); edge.data=city.data; edge_mod=edge.modifiers.new('Building edge glow','WIREFRAME'); edge_mod.thickness=0.18; edge_mod.use_replace=True; edge_mod.material_offset=len(bmesh.materials)-1

# Named / tall landmarks as metadata empties: useful for inspection and later high-detail replacements.
for idx,(cx,cy,base,h,b) in enumerate(sorted(centers,key=lambda q:q[3],reverse=True)[:120]):
    name=b.get('name') or f"OSM_Building_{b['id']}"
    e=bpy.data.objects.new('Landmark_'+name[:70].replace('/','_'),None); landmark_coll.objects.link(e); e.empty_display_type='CUBE'; e.empty_display_size=max(3,min(25,h*0.06)); e.location=(cx,cy,base+h)
    e['osm_id']=str(b['id']); e['name']=name; e['height_m']=float(h); e['kind']=b.get('kind','yes'); e['detail_status']='OSM footprint + procedural height/facade; verify against official 3D tiles before claiming photo-accuracy'

# Near-field window mullion linework for named/tall buildings.
# This is deliberately limited to the landmark set; the rest of the island stays lightweight.
try:
    cu=bpy.data.curves.new('HKI_Landmark_WindowFrames','CURVE'); cu.dimensions='3D'; cu.bevel_depth=0.035; cu.bevel_resolution=0; cu.resolution_u=1
    line_count=0
    for cx,cy,base,h,b in sorted(centers,key=lambda q:q[3],reverse=True)[:80]:
        if h < 24: continue
        ring=b['footprint']; n=len(ring)
        floors=min(int(h/3.2),120)
        for i in range(n):
            p0=Vector((ring[i][0],ring[i][1],0)); p1=Vector((ring[(i+1)%n][0],ring[(i+1)%n][1],0)); edgev=p1-p0; L=max(edgev.length,0.5); mid=(p0+p1)*0.5
            normal=Vector((edgev.y,-edgev.x,0)).normalized()
            if normal.dot(Vector((cx,cy,0))-mid)>0: normal=-normal
            offset=normal*0.09
            for k in range(floors):
                zz=base+1.5+k*3.2
                sp=cu.splines.new('POLY'); sp.points.add(1); sp.points[0].co=(p0.x+offset.x,p0.y+offset.y,zz,1); sp.points[1].co=(p1.x+offset.x,p1.y+offset.y,zz,1); line_count+=1
            steps=max(1,int(L/4.0))
            for q in range(1,steps):
                t=q/steps; pp=p0+edgev*t+offset
                sp=cu.splines.new('POLY'); sp.points.add(1); sp.points[0].co=(pp.x,pp.y,base+0.6,1); sp.points[1].co=(pp.x,pp.y,base+h-0.6,1); line_count+=1
            if line_count>70000: break
        if line_count>70000: break
    winob=bpy.data.objects.new('HKI_Landmark_WindowFrames',cu); landmark_coll.objects.link(winob); cu.materials.append(mat_grid); winob['line_count']=line_count; winob['source']='procedural mullions on OSM landmark footprints'
except Exception as _window_error:
    print('window frames skipped',_window_error)

# A visual bounding frame / grid at city level.
# Create large origin axes using curves for orientation.
def line_obj(name, pts, material, bevel=0.8, collection=viz_coll):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=bevel;cu.bevel_resolution=1
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*co,1)
    ob=bpy.data.objects.new(name,cu);collection.objects.link(ob);ob.data.materials.append(material);return ob
# cardinal grid and title-like scan lines over the harbor plane
for coord in range(-12000,12001,2000):
    line_obj('Grid_EW_'+str(coord),[(-12000,coord,-4),(12000,coord,-4)],mat_grid,0.22)
    line_obj('Grid_NS_'+str(coord),[(coord,-10000,-4),(coord,10000,-4)],mat_grid,0.22)

# Camera and sparse lights.
def look_at(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(5200,-14500,5900));cam=bpy.context.object;cam.name='HKI_Atlas_Camera';cam.data.lens=47;cam.data.sensor_width=36;cam.data.clip_end=100000;cam.data.clip_start=0.1;look_at(cam,(-2500,-3200,280));scene.camera=cam
for c in list(cam.users_collection):c.objects.unlink(cam)
viz_coll.objects.link(cam)
bpy.ops.object.light_add(type='AREA', location=(-3500,-5000,5000));light=bpy.context.object;light.name='Moon_Rim';light.data.energy=450;light.data.shape='DISK';light.data.size=5000;look_at(light,(-2500,-3200,0));
for c in list(light.users_collection):c.objects.unlink(light)
viz_coll.objects.link(light)

# Render settings and metadata.
scene['project']='Hong Kong Island holographic atlas'
scene['date']='2026-09-30'
scene['osm_source_date']='2026-09-29'
scene['official_3d_source']='Hong Kong Lands Department Open3Dhk / 3D Spatial Data API; not bulk-imported into this first local build'
scene['terrain_source']='Whole_HK_DTM_5m.zip; downsampled to 25m'
scene['coverage']='Hong Kong Island OSM relation 4556901'
scene['limitations']='Only OSM-tagged footprints and available height/levels are represented; missing facade detail is procedural, not a claim of exact survey reconstruction.'
# Save and render preview.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
bpy.context.view_layer.objects.active=city;city.select_set(True)
print({'buildings':len(records),'vertices':len(V),'building_faces':len(F),'terrain_vertices':len(verts),'terrain_faces':len(terrain_faces),'blend':str(ROOT/'HKI_Holographic_Atlas.blend')})
scene.render.resolution_percentage=55
scene.render.use_compositing=False
scene.render.use_sequencer=False
# Frame the full island/building envelope for the preview instead of relying on an arbitrary close view.
from mathutils import Vector
cam.data.type='ORTHO'; cam.data.ortho_scale=22500
look_at(cam,(-600, -2500, 50))
scene.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
scene.render.resolution_percentage=70
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HKI_Holographic_Atlas.blend'))
print('rendered',scene.render.filepath)






