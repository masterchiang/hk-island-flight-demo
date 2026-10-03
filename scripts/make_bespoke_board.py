from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
O=Path('output/bespoke_B1')
F=lambda n,b=False:ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if b else 'C:/Windows/Fonts/msyh.ttc',n)
w,h=1640,1460
im=Image.new('RGB',(w,h),'#0d1925');d=ImageDraw.Draw(im)
d.text((36,23),'香港岛  /  地标专属重建',font=F(34,True),fill='#f4f2ec')
d.text((36,76),'批次 01   ·   5 栋建筑   ·   OSM / GIS 定位 + 建筑资料与照片解读',font=F(18),fill='#aac4cb')
d.text((1250,38),'01 OCT 2026  |  B1',font=F(20,True),fill='#73d6cb')
items=[('怡和大厦','178.54 m','before_01_Jardine.png','01_Jardine_House.png','矩形塔身 · 凹入圆窗 · 斜面机房顶'),('国际金融中心二期','415.8 m','before_02_IFC.png','02_Two_IFC.png','收分与退台 · 银色竖框 · 镂空冠顶'),('中环广场','374 m  含尖顶','before_03_Central.png','03_Central_Plaza.png','截角三角形 · 蓝金立面 · 完整尖顶'),('力宝中心一座 / 二座','172 m / 186 m','before_04_Lippo.png','04_Lippo_Twins.png','八角塔身 · 错层悬挑 · 黑色凹槽')]
for i,(title,height,old,new,note) in enumerate(items):
 x=36+i*400
 d.text((x,115),title,font=F(22,True),fill='#f3f4f1')
 d.text((x,150),height,font=F(16),fill='#8ab8c2')
 for y,f,label in [(183,old,'原有体量模型'),(745,new,'本轮专属模型')]:
  a=Image.open(O/f).convert('RGB').resize((376,491),Image.Resampling.LANCZOS)
  im.paste(a,(x,y))
  d.rectangle((x,y,x+375,y+34),fill='#203140')
  d.text((x+11,y+4),label,font=F(17,True),fill='#dde9eb' if '原' in label else '#85efe0')
 d.text((x,1254),note,font=F(15),fill='#bad2d5')
d.line((36,1310,1604,1310),fill='#304450',width=2)
d.text((36,1332),'验证口径：每列前后采用相同相机与尺度；不同列为独立构图，不代表建筑间的相同比例。',font=F(18),fill='#dbe4e7')
d.text((36,1370),'精度边界：建筑专属重建，非逐面摄影测量；照片仅作形态参考，未作为可分发贴图。',font=F(18),fill='#91aeb8')
im.save(O/'B1_Before_After_Board.png')
print(O/'B1_Before_After_Board.png')
