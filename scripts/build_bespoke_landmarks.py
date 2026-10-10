"""Reference-led landmark batch B1. Execute in Blender, not ordinary Python.
All dimensions in metres, local geometry with GIS root transforms.
No external copyrighted photograph is embedded in materials.
"""
import bpy, bmesh, math, json, random
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'<PROJECT_ROOT>')
REV='2026-10-01-B1'
INPUT=json.loads((ROOT/'data/processed/bespoke_landmark_inputs.json').read_text(encoding='utf8'))
SPECS={b['name']:b for b in INPUT['landmarks']}
COL='12_Bespoke_Landmarks_B1'
ARCHIVE='12_PreBespoke_LOD_Archive'

def collection(name):
 c=bpy.data.collections.get(name)
 if not c:
  c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
 return c

def material(name,col,metal=0.,rough=.4,coat=0.):
 name='B1_'+name
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
 m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 p.inputs['Base Color'].default_value=(*col,1)
 p.inputs['Metallic'].default_value=metal
 p.inputs['Roughness'].default_value=rough
 p.inputs['Coat Weight'].default_value=coat
 m.diffuse_color=(*col,1)
 return m

def palette():
 return [material('Pearl_aluminium',(.66,.69,.70),.62,.32),
 material('Shadow_recess',(.022,.036,.045),.25,.35),
 material('Limestone',(.46,.44,.38),.05,.68),
 material('Jardine_satin_silver',(.76,.78,.76),.42,.41),
 material('Jardine_recess_glass',(.075,.17,.20),.48,.20,.45),
 material('IFC_silver_blue_glass',(.19,.31,.40),.53,.24,.3),
 material('IFC_spandrel',(.115,.20,.27),.56,.32),
 material('Lippo_mirror_blue',(.22,.36,.40),.65,.19,.4),
 material('Lippo_silver_spandrel',(.31,.42,.44),.6,.31),
 material('Central_bronze_glass',(.265,.24,.18),.55,.23,.4),
 material('Central_gold_mullions',(.59,.46,.23),.64,.29),
 material('Green_marble',(.038,.092,.073),.15,.28),
 material('Roof_equipment',(.25,.28,.28),.48,.5),
 material('Signage_red',(.5,.024,.024),.3,.38),
 material('Lit_warm_glass',(.40,.37,.28),.5,.26)]

class Mesh:
 def __init__(self): self.v=[]; self.f=[]; self.mi=[]
 def face(self,points,mi=0):
  s=len(self.v); self.v.extend([tuple(p) for p in points]); self.f.append(tuple(range(s,s+len(points)))); self.mi.append(mi)
 def prism(self,ring,z0,z1,mi=0,top=None):
  top=top if top is not None else ring
  if sum(ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))<0:
   ring=list(reversed(ring)); top=list(reversed(top))
  a=[(x,y,z0) for x,y in ring]; b=[(x,y,z1) for x,y in top]
  self.face(a[::-1],mi); self.face(b,mi)
  for i in range(len(a)):
   j=(i+1)%len(a); self.face([a[i],a[j],b[j],b[i]],mi)
 def box(self,x,y,z,w,d,h,mi=0): self.prism(rect(w,d,x,y),z,z+h,mi)
 def beam(self,a,b,width=.12,mi=0,depth=None):
  a,b=Vector(a),Vector(b); axis=b-a
  if axis.length<1e-5:return
  axis.normalize(); ref=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
  u=axis.cross(ref).normalized()*width/2; v=axis.cross(u).normalized()*(depth or width)/2
  r=[-u-v,u-v,u+v,-u+v]
  aa=[a+q for q in r]; bb=[b+q for q in r]
  self.face(aa[::-1],mi); self.face(bb,mi)
  for i in range(4):j=(i+1)%4;self.face([aa[i],aa[j],bb[j],bb[i]],mi)
 def object(self,name,parent):
  me=bpy.data.meshes.new(name+'_Mesh'); me.from_pydata(self.v,[],self.f);me.update()
  for m in palette():me.materials.append(m)
  for p,mi in zip(me.polygons,self.mi):p.material_index=mi
  bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bm.to_mesh(me);bm.free();me.update()
  o=bpy.data.objects.new(name,me);collection(COL).objects.link(o);o.parent=parent;o['bespoke_revision']=REV
  return o

def rect(w,d,x=0.,y=0.):return [(x-w/2,y-d/2),(x+w/2,y-d/2),(x+w/2,y+d/2),(x-w/2,y+d/2)]
def scaled(r,s):return [(x*s,y*s) for x,y in r]
def circle(rx,ry,n=32):return [(math.cos(i*math.tau/n)*rx,math.sin(i*math.tau/n)*ry) for i in range(n)]
def octagon(w,d,cut):return [(-w/2+cut,-d/2),(w/2-cut,-d/2),(w/2,-d/2+cut),(w/2,d/2-cut),(w/2-cut,d/2),(-w/2+cut,d/2),(-w/2,d/2-cut),(-w/2,-d/2+cut)]
def blend(a,b,t):return [(x*(1-t)+u*t,y*(1-t)+v*t) for (x,y),(u,v) in zip(a,b)]
def ringbeam(mesh,ring,z,width=.14,mi=0):
 for i,a in enumerate(ring):b=ring[(i+1)%len(ring)];mesh.beam((*a,z),(*b,z),width,mi)

def curtain(glass,frames,r0,r1,z0,z1,floors,gm=5,sm=6,fm=0,pitch=2.5,hw=.12,vw=.11,spandrel=.52,panel_style=None):
 """Panelised facades follow the *same* tapered geometry as the floor shell."""
 for level in range(floors):
  z=z0+(z1-z0)*level/floors; zt=z0+(z1-z0)*(level+1)/floors
  ra=blend(r0,r1,level/floors); rb=blend(r0,r1,(level+1)/floors)
  rc=blend(ra,rb,min(spandrel/(zt-z),.4))
  ringbeam(frames,ra,z,hw,fm)
  for i in range(len(ra)):
   j=(i+1)%len(ra); count=max(1,round(math.dist(ra[i],ra[j])/pitch))
   for k in range(count):
    ta,tb=k/count,(k+1)/count
    def P(r,t,zz):return (r[i][0]*(1-t)+r[j][0]*t,r[i][1]*(1-t)+r[j][1]*t,zz)
    pa,pb=P(ra,ta,z),P(ra,tb,z); qa,qb=P(rc,ta,z+spandrel),P(rc,tb,z+spandrel); ua,ub=P(rb,ta,zt),P(rb,tb,zt)
    chosen=panel_style(i,k,count,level,floors) if panel_style else gm
    glass.face([pa,pb,qb,qa],0 if panel_style and chosen==5 else sm)
    # restrained alternate panels: daylight reflection, not a lit checkerboard
    glass.face([qa,qb,ub,ua],chosen)
    frames.beam(pa,ua,vw,fm)
 ringbeam(frames,r1,z1,hw,fm)

def new_root(name):
 b=SPECS[name]; c=collection(COL)
 old=[o for o in c.objects if o.get('landmark_name')==name and o.type=='EMPTY']
 for o in old:
  for x in [*o.children_recursive,o]:
   data=x.data if x.type=='MESH' else None
   bpy.data.objects.remove(x,do_unlink=True)
   if data and data.users==0:bpy.data.meshes.remove(data)
 slug=name.replace(' ','_')
 root=bpy.data.objects.new('BESPOKE_'+b['osm_id']+'_'+slug,None); c.objects.link(root)
 root.location=b['position'];root.rotation_euler[2]=b['rotation_z']
 root.empty_display_size=4
 for k,v in {'landmark_name':name,'name':name,'osm_id':b['osm_id'],'height_m':b['height_m'],'bespoke_revision':REV,'basis':b['precision'],'height_note':b['height_note'],'references':json.dumps(b['sources']),'footprint_source':b['osm_url'],'crs':'EPSG:2326; origin=(840000,815000)','detail_status':'Reference-led bespoke reconstruction; not photogrammetry'}.items():root[k]=v
 return root,b

def finish(root,meshes,features):
 for suffix,mesh in meshes.items():
  if mesh.v:mesh.object(root.name+'__'+suffix,root)
 root['recognition_features']=features
 bpy.context.view_layer.update()
 return {'name':root['landmark_name'],'objects':len(root.children),'vertices':sum(len(o.data.vertices) for o in root.children if o.type=='MESH')}

def build_jardine():
 root,b=new_root('Jardine House'); w,d=b['width']*.97,b['depth']*.97
 wall=Mesh(); glass=Mesh(); rim=Mesh(); base=Mesh(); roof=Mesh(); joints=Mesh()
 # Thin silver panels with an actual circular opening, a sloped reveal and an
 # inset glass disk. No thousands of boolean modifiers, and no window decals.
 z0,z1=10.8,169.2; rows=46; count=0
 sides=[((-w/2,-d/2),(1,0,0),(0,-1,0),w,12),((w/2,-d/2),(0,1,0),(1,0,0),d,7),((w/2,d/2),(-1,0,0),(0,1,0),w,12),((-w/2,d/2),(0,-1,0),(-1,0,0),d,7)]
 for origin,u,n,length,cols in sides:
  U,N=Vector(u),Vector(n); pw=length/cols; ph=(z1-z0)/rows
  for row in range(rows):
   z=z0+(row+.5)*ph
   for col in range(cols):
    center=Vector((origin[0],origin[1],z))+U*((col+.5)*pw)
    outer=[]; hole=[]; lip=[]; inner=[]
    radius=1.10
    for k in range(24):
     a=math.tau*k/24; ca,sa=math.cos(a),math.sin(a)
     f=min((pw/2-.025)/max(abs(ca),1e-9),(ph/2-.025)/max(abs(sa),1e-9))
     def at(x,y,off=0):return center+U*x+Vector((0,0,y))+N*off
     outer.append(at(ca*f,sa*f));hole.append(at(ca*(radius+.07),sa*(radius+.07)))
     lip.append(at(ca*radius,sa*radius,-.12));inner.append(at(ca*(radius-.04),sa*(radius-.04),-.42))
    for k in range(24):
     j=(k+1)%24
     wall.face([outer[k],outer[j],hole[j],hole[k]],3)
     rim.face([hole[k],hole[j],lip[j],lip[k]],0)
     rim.face([lip[k],lip[j],inner[j],inner[k]],3)
    glass.face(inner,4);count+=1
  for row in range(rows+1):
   a=(*origin,z0+row*(z1-z0)/rows);p=Vector(a);joints.beam(p,p+U*length,.027,1)
  for col in range(cols+1):
   p=Vector((origin[0],origin[1],z0))+U*(col*pw);joints.beam(p,(p.x,p.y,z1),.027,1)
 # Tucked-back lobby, green stone plinth and inclined silver columns,
 # informed by the street-level reference; no unsupported long skybridge.
 base.box(0,0,-.85,w*.98,d*.98,1.1,11)
 base.box(0,0,.25,w*.83,d*.81,8.55,4)
 for x in [-w*.42,0,w*.42]:
  for y in [-d*.40,d*.40]:
   base.beam((x,y,.3),(x*1.13,y*1.13,10.6),1.25,3)
 base.box(0,0,9.4,w,d,1.4,3)
 for side in [-1,1]:
  base.box(0,side*(d*.39),3.3,w*.92,1.8,.65,3)
  for j in range(10):base.box(0,side*(d*.4+2.2-j*.2),j*.16,12.,.24,.16,2)
 # Hipped, louvred mechanical roof visible in complete-building photographs.
 roof.box(0,0,169.2,w+.2,d+.2,1.4,3)
 hip0=rect(w*.97,d*.97);hip1=rect(w*.71,d*.64)
 roof.prism(hip0,170.6,178.54,3,hip1)
 for zz in range(171,178):ringbeam(roof,blend(hip0,hip1,(zz-170.6)/7.94),zz,.13,12)
 roof.box(0,0,178.1,w*.66,d*.58,.4,12)
 root['modelled_porthole_count']=count
 root['facade_layout_note']='46 repeated facade rows, 12/7 bays on long/short faces, visually interpreted. Not a measured as-built window schedule.'
 return finish(root,{'Silver_Perforated_Panels':wall,'Recessed_Round_Glazing':glass,'Circular_Reveals':rim,'Panel_Seams':joints,'Lobby_and_Entry':base,'Hipped_Louvred_Roof':roof},'Rectangular slab; recessed round portholes; panel seams; hipped roof; open glazed lobby')

def build_ifc():
 root,b=new_root('Two International Finance Centre'); ring=b['footprint_local']
 glass=Mesh(); frames=Mesh(); crown=Mesh(); base=Mesh(); equipment=Mesh()
 # Close-spaced but distinct setbacks, not a continuously shrinking pyramid.
 sections=[(11.,230.,1.,.99,48),(230.,287.,.965,.947,12),(287.,325.,.92,.90,8),(325.,359.,.862,.842,7),(359.,383.,.799,.777,5),(383.,397.,.734,.704,3)]
 for i,(a,z,s0,s1,n) in enumerate(sections):
  ra,rb=scaled(ring,s0),scaled(ring,s1)
  curtain(glass,frames,ra,rb,a,z,n,5,6,0,2.35,.14,.12,.62)
  if i:
   equipment.prism(scaled(ring,s0+0.018),a-.7,a+.55,0)
  # paired pearl mullions frame eight major facet seams from base to crown
  for j,(x,y) in enumerate(ra):
   if j%3 in [0,1]:frames.beam((x,y,a),(*rb[j],z),.26,0)
 # Ground entrance remains inside OSM outline, podium beyond is existing city mesh.
 base.prism(scaled(ring,.92),0,2.2,2)
 base.prism(scaled(ring,.87),2.2,11.,5)
 for p in ring[::2]:base.beam((p[0]*.88,p[1]*.88,1.4),(p[0],p[1],12.),.9,0)
 ringbeam(base,ring,11.,.8,0)
 # Screened crown: dark inner mechanical volume, eight upward lobes,
 # dense silver blades on the broad faces; central skyline height=415.8m.
 crown.prism(scaled(ring,.66),397.,405.1,6)
 rr=scaled(ring,.71)
 for i,(x,y) in enumerate(rr):
  nxt=rr[(i+1)%len(rr)];L=math.dist((x,y),nxt);n=max(2,round(L/.85))
  for k in range(n):
   t=k/n;px=x*(1-t)+nxt[0]*t;py=y*(1-t)+nxt[1]*t
   # Four paired prongs interleave high/lower rounded crown screens.
   top=415.8 if i%3 in [0,1] else 412.1
   crown.beam((px,py,397.),(px*.94,py*.94,top),.21,0,.34)
  crown.beam((x,y,405.7),(nxt[0],nxt[1],405.7),.24,0)
 for z in [399,401,403,405]:ringbeam(crown,scaled(ring,.672),z,.19,0)
 for x in [-6,6]:equipment.box(x,0,400,7,10,4,12)
 return finish(root,{'Panelised_Curtainwall':glass,'Pearl_Mullions_and_Fins':frames,'Eight_Lobed_Screen_Crown':crown,'Recessed_Entrance':base,'Mechanical_Setbacks':equipment},'Tapered obelisk; six proportional setbacks; pearl mullions; open screened crown with paired prongs')

def build_central():
 root,b=new_root('Central Plaza');ring=b['footprint_local']
 glass=Mesh();frames=Mesh();base=Mesh();crown=Mesh();spire=Mesh()
 # Retain every surveyed footprint corner; do not expand a regular triangle
 # using bbox width as a radius (the previous mass was almost twice as wide).
 base.prism(scaled(ring,.86),0,2.1,2)
 base.prism(scaled(ring,.73),2.1,26.9,9)
 for p in ring[::2]:base.beam((p[0]*.78,p[1]*.78,2),(*p,30.5),1.05,10)
 base.prism(ring,27.5,30.5,10)
 def central_style(i,k,n,level,nf):
  length=math.dist(ring[i],ring[(i+1)%len(ring)])
  t=(k+.5)/n
  return 5 if length<25 or t<.19 or t>.81 or level>nf-4 else 9
 curtain(glass,frames,ring,ring,30.5,265.9,62,9,9,10,2.2,.12,.15,.46,central_style)
 for z in [112,190,246,265.9]:
  base.prism(scaled(ring,1.001),z-.8,z+.4,10)
  ringbeam(frames,scaled(ring,1.008),z,.28,10)
 # Three face-centre gold pilasters and the clipped vertices.
 for i,p in enumerate(ring):
  if i%4 in [0,3]:frames.beam((*p,30.5),(*p,275.),.42,10)
 curtain(glass,frames,ring,scaled(ring,.97),265.9,274.,2,5,0,10,2.8,.16,.22,.55)
 curtain(glass,frames,scaled(ring,.70),scaled(ring,.15),274.,306.,7,5,0,10,2.8,.18,.22,.60)
 crown.prism(scaled(ring,.15),306,309,10,scaled(ring,.10))
 for i,p in enumerate(ring):
  if i%4 in [0,3]:crown.beam((p[0]*.97,p[1]*.97,274.),(p[0]*.1,p[1]*.1,309.),.95,10)
 # 102m mast includes the section within the crown; do not add it above 309m.
 spire.prism(circle(2.7,2.7,12),272,321,10,circle(1.65,1.65,12))
 spire.prism(circle(1.65,1.65,12),321,348,10,circle(.68,.68,12))
 spire.prism(circle(.68,.68,12),348,374.,0,circle(.07,.07,12))
 for z in [310,314,318,322]:
  spire.prism(circle(2.05,2.05,12),z,z+.6,3)
 for ang in [0,math.tau/3,2*math.tau/3]:
  a=(math.cos(ang)*9,math.sin(ang)*9,299)
  spire.beam(a,(0,0,333),.22,10)
 root['roof_height_m']=309.;root['mast_top_m']=374.;root['mast_note']='Four Lightime bands modelled; no claim of a functioning time animation.'
 return finish(root,{'Bronze_Curtainwall':glass,'Gold_Mullions':frames,'Public_Base_and_Mechanical_Bands':base,'Triangular_Pyramidal_Crown':crown,'374m_Mast_and_Lightime_Bands':spire},'OSM truncated triangular plan; bronze glass/gold mullions; 309m roof; 374m mast; four Lightime bands')

def build_lippo(name):
 root,b=new_root(name);h=b['height_m'];w,d=b['width']*.94,b['depth']*.94
 core=octagon(w*.81,d*.81,9.2)
 glass=Mesh();frames=Mesh();soffits=Mesh();base=Mesh();roof=Mesh()
 curtain(glass,frames,core,core,16.,h-3.0,round((h-19)/3.95),7,8,0,2.35,.12,.095,.57)
 base.prism(octagon(w*.98,d*.98,10.0),0,3.2,2)
 base.prism(octagon(w*.90,d*.90,9.0),3.2,14.,7)
 ringbeam(base,octagon(w*.95,d*.95,9.5),14.,1.0,0)
 # Four glazed, chamfered projecting shoulders repeated in three vertical
 # villages, staggered by one floor on alternate faces. Broad black reveals
 # and sloping soffits give the characteristic koala/cantilever silhouette.
 for level,(a,zt) in enumerate([(26.,62.),(72.,111.),(121.,h-4.8)]):
  for side in range(4):
   offset=(3.95 if side%2 else 0.)
   z0=a+offset;z1=min(zt+offset,h-4.8)
   if z1-z0<8:continue
   theta=side*math.pi/2
   width=(w if side%2==0 else d)*(.48 if level==1 else .46)
   near=(d if side%2==0 else w)*.32;far=(d if side%2==0 else w)*.526
   # Face parallel to X, projects toward -Y. Rotation produces the other faces.
   pr=[(-width/2,-near),(width/2,-near),(width/2,-far+2.3),(width/2-2.6,-far),(-width/2+2.6,-far),(-width/2,-far+2.3)]
   def rot(rr):return [(x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta)) for x,y in rr]
   pr=rot(pr);pr=list(reversed(pr))
   small=scaled(pr,.91)
   soffits.prism(small,z0,z0+4.,1,pr)
   curtain(glass,frames,pr,pr,z0+4.,z1,max(1,round((z1-z0-4)/3.95)),7,8,0,2.1,.13,.1,.57)
   soffits.prism(pr,z1-.5,z1+.15,1)
   # stepped dark notch midway up one side of each projecting block
   for z in [z0+7.9,z1-3.95]:
    p0=pr[1];p1=pr[2];soffits.beam((*p0,z),(*p1,z),.62,1)
 for z in [64.,114.]:
  ringbeam(soffits,core,z,1.05,1)
 roof.prism(core,h-3.,h,1)
 for z in [h-2.4,h-1.8,h-1.2]:ringbeam(roof,core,z,.14,0)
 # Low-profile roof plant sits inside the screen, never taller than the source height.
 roof.box(0,0,h-5,10,12,3.4,12)
 root['floor_to_floor_reference_m']=3.95
 root['projection_note']='Suspended facade village positions interpreted from photographs, not as-built structural drawings; existing shared podium remains separately in city mesh.'
 return finish(root,{'Octagonal_and_Projected_Curtainwall':glass,'Silver_Mullions':frames,'Cantilevered_Shoulders_and_Black_Reveals':soffits,'Podium_Entry':base,'Roof_Screen':roof},'Octagonal shaft; three staggered cantilever villages; blue mirror glazing; chamfered shoulders; recessed black bands')

BUILDERS={'Jardine House':build_jardine,'Two International Finance Centre':build_ifc,'Central Plaza':build_central}
def build(name):
 return BUILDERS[name]() if name in BUILDERS else build_lippo(name)

def commit_replacements():
 """Archive complete original hierarchies ONLY after all replacements exist."""
 roots=[o for o in collection(COL).objects if o.type=='EMPTY' and o.get('landmark_name') in SPECS]
 assert len(roots)==5 and all(len(o.children)>=4 for o in roots),'incomplete batch; originals NOT touched'
 archive=collection(ARCHIVE); saved=json.loads(archive.get('original_state','{}'))
 ids={b['osm_id'] for b in SPECS.values()}; names=set(SPECS)
 candidates=[]
 for o in list(bpy.context.scene.objects):
  if o.name.startswith('BESPOKE_') or o.name.startswith('SKETCHFAB_'):continue
  if str(o.get('osm_id','')) in ids or (o.name.startswith('Landmark_') and o.get('name') in names):
   candidates.extend([o,*o.children_recursive])
 for o in set(candidates):
  if o.name not in saved:
   saved[o.name]={'collections':[c.name for c in o.users_collection],'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'hide_set':o.hide_get()}
  for c in list(o.users_collection):c.objects.unlink(o)
  if o.name not in archive.objects:archive.objects.link(o)
  o.hide_render=True;o.hide_viewport=True;o['superseded_by_revision']=REV
 archive['original_state']=json.dumps(saved);archive.hide_render=True;archive.hide_viewport=True
 bpy.context.scene['bespoke_landmarks_revision']=REV
 bpy.context.scene['bespoke_landmarks_notes']='5 reference-led models. Earlier 50 custom masses are not all completed bespoke models. See landmark_upgrade_queue.json.'
 return {'archived_objects':len(saved),'new_roots':len(roots)}

def restore_originals():
 """Non-destructive rollback: retains B1 work but hides it; restores saved flags."""
 archive=bpy.data.collections.get(ARCHIVE)
 if not archive:return
 for name,state in json.loads(archive.get('original_state','{}')).items():
  o=bpy.data.objects.get(name)
  if not o:continue
  for c in list(o.users_collection):c.objects.unlink(o)
  for name2 in state['collections']:collection(name2).objects.link(o)
  o.hide_render=state['hide_render'];o.hide_viewport=state['hide_viewport'];o.hide_set(state['hide_set'])
 collection(COL).hide_render=True;collection(COL).hide_viewport=True

if __name__=='__main__':
 for name in SPECS:print(build(name))
 print(commit_replacements())

