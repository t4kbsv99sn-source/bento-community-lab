"""Look directions for the owner (25 Oct 2026: "more sleek and modern, lighter,
less tracker; our own screens are barebones; why not make the EQ visual?").

1. Recolours a real emulator render of the synth page (raw palette indices
   from render_mod.py) with three candidate palettes. Index = level<<4 | colour:
   low nibble is the colour id (1 background, 2 text, 3 lines, 6 accent,
   7 bars, 0 track colour), high nibble the anti-aliasing level over the
   background (F = full). As on the device: encoder values on top, the
   action bar at the bottom.
2. Draws a mockup of the Track FX page with a visual EQ curve, a compressor
   gain-reduction meter and the soft-clip curve, in the same palettes.
Mockups only: the device palette table itself still has to be located."""
import argparse,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
LOOKS={
 'A_refined_dark':dict(bg=(16,18,21),panel=(22,25,30),line=(43,48,56),text=(233,236,239),dim=(140,148,160),accent=(255,138,61),bars=(201,206,214),track=(77,163,255)),
 'B_graphite':dict(bg=(27,31,36),panel=(34,39,46),line=(58,65,76),text=(243,245,247),dim=(150,160,172),accent=(61,214,196),bars=(143,161,179),track=(255,176,84)),
 'C_light':dict(bg=(238,240,243),panel=(255,255,255),line=(201,206,214),text=(27,31,36),dim=(110,118,130),accent=(255,92,31),bars=(89,98,110),track=(36,120,230)),
}
def palette(L):
 base={1:L['bg'],2:L['text'],3:L['line'],6:L['accent'],7:L['bars'],0:L['track']}
 pal=np.zeros((256,3),np.uint8)
 for i in range(256):
  lvl,c=i>>4,i&15;col=base.get(c,L['dim']);t=(lvl+1)/16
  pal[i]=[round(L['bg'][k]*(1-t)+col[k]*t) for k in range(3)]
 return pal
raw=np.frombuffer(a.raw.read_bytes(),dtype=np.uint8).reshape(480,1280)
a.out.mkdir(parents=True,exist_ok=True)
for name,L in LOOKS.items():Image.fromarray(palette(L)[raw]).save(a.out/f'synth_{name}.png')
# Track FX mockup.
F='/usr/share/fonts/opentype/inter/'
def font(w,s):return ImageFont.truetype(F+('Inter-SemiBold.otf' if w else 'Inter-Regular.otf'),s)
def eq_db(f,low,mid,high):
 lf,lg=low;mf,mg,q=mid;hf,hg=high
 shelf=lambda f,fc,g,sign:g/(1+(fc/f)**(2*sign)) if sign>0 else g/(1+(f/fc)**2)
 peak=mg/(1+(q*(f/mf-mf/f))**2)
 return lg/(1+(f/lf)**2)+peak+hg/(1+(hf/f)**2)
def fx(L,path):
 W,H=1280,480;im=Image.new('RGB',(W,H),L['bg']);d=ImageDraw.Draw(im)
 # header
 d.text((14,451),'Track 2',font=font(1,22),fill=L['track'],anchor='lm')
 for i,(t,act) in enumerate([('EQ',1),('Compressor',0),('Soft Clip',0)]):
  x=322+i*159;d.rounded_rectangle((x,434,x+150,468),8,fill=L['panel'] if act else None,outline=L['accent'] if act else L['line'])
  d.text((x+75,451),t,font=font(act,18),fill=L['text'] if act else L['dim'],anchor='mm')
 d.text((1186,451),'120.0',font=font(0,18),fill=L['dim'],anchor='mm')
 # EQ graph
 gx0,gy0,gx1,gy1=16,140,860,424;d.rounded_rectangle((gx0,gy0,gx1,gy1),10,fill=L['panel'])
 fx_=lambda f:gx0+(math.log10(f)-math.log10(20))/3*(gx1-gx0);fy=lambda db:(gy0+gy1)/2-db*(gy1-gy0)/2/15
 for f,lab in [(50,'50'),(100,'100'),(200,''),(500,'500'),(1000,'1k'),(2000,''),(5000,'5k'),(10000,'10k')]:
  x=fx_(f);d.line((x,gy0+8,x,gy1-8),fill=L['line']);lab and d.text((x,gy1-12),lab,font=font(0,13),fill=L['dim'],anchor='mb')
 for db in (-12,-6,6,12):d.line((gx0+8,fy(db),gx1-8,fy(db)),fill=L['line'])
 d.line((gx0+8,fy(0),gx1-8,fy(0)),fill=L['dim'])
 low,mid,high=(120,4.5),(1800,-3.5,1.4),(8000,5)
 pts=[(fx_(f),fy(eq_db(f,low,mid,high))) for f in np.logspace(math.log10(20),math.log10(20000),400)]
 fill=[(gx0+8,fy(0))]+pts+[(gx1-8,fy(0))];
 ov=Image.new('RGBA',(W,H));od=ImageDraw.Draw(ov);od.polygon(fill,fill=L['accent']+(46,));im.paste(ov,(0,0),ov);d=ImageDraw.Draw(im)
 d.line(pts,fill=L['accent'],width=3,joint='curve')
 for (f,g),lab in [((low[0],eq_db(low[0],low,mid,high)),'L'),((mid[0],eq_db(mid[0],low,mid,high)),'M'),((high[0],eq_db(high[0],low,mid,high)),'H')]:
  x,y=fx_(f),fy(g);d.ellipse((x-11,y-11,x+11,y+11),fill=L['bg'],outline=L['accent'],width=3);d.text((x,y),lab,font=font(1,13),fill=L['text'],anchor='mm')
 # compressor + clip panel
 cx0,cx1=876,1264;d.rounded_rectangle((cx0,gy0,cx1,gy1),10,fill=L['panel'])
 d.text((cx0+18,gy0+16),'Compressor',font=font(1,16),fill=L['text']);d.text((cx1-18,gy0+16),'GR −4.5 dB',font=font(0,15),fill=L['accent'],anchor='ra')
 # transfer curve
 tx0,ty0,tx1,ty1=cx0+18,gy0+48,cx0+200,gy1-18;d.rectangle((tx0,ty0,tx1,ty1),outline=L['line'])
 th,ratio=-18,4
 cur=[];
 for i in range(101):
  xin=-48+i*0.48;yo=xin if xin<th else th+(xin-th)/ratio;cur.append((tx0+(xin+48)/48*(tx1-tx0),ty1-(yo+48)/48*(ty1-ty0)))
 d.line([(tx0,ty1),(tx1,ty0)],fill=L['line']);d.line(cur,fill=L['accent'],width=3)
 # GR meter
 mx=cx0+226;d.text((mx,ty0-2),'GR',font=font(0,13),fill=L['dim'])
 for i in range(12):
  y=ty0+16+i*((ty1-ty0-16)/12);on=i<5;d.rounded_rectangle((mx,y,mx+22,y+((ty1-ty0-16)/12)-4),3,fill=L['accent'] if on else L['line'])
 d.text((mx+40,ty0),'Soft Clip',font=font(1,15),fill=L['text'])
 sx0,sy0,sx1,sy1=mx+40,ty0+26,cx1-18,ty1;d.rectangle((sx0,sy0,sx1,sy1),outline=L['line'])
 sc=[(sx0+(i/100)*(sx1-sx0),sy1-(math.tanh(2.2*(i/100*2-1))/math.tanh(2.2)*0.5+0.5)*(sy1-sy0)) for i in range(101)];d.line(sc,fill=L['accent'],width=3)
 # encoder row
 vals=[('EQ','On'),('Low Hz','120'),('Low dB','+4.5'),('Mid Hz','1.8k'),('Mid dB','−3.5'),('Mid Q','1.4'),('High Hz','8k'),('High dB','+5.0')]
 for i,(t,v) in enumerate(vals):
  x=16+i*157;d.rounded_rectangle((x,8,x+149,128),10,fill=L['panel'])
  d.text((x+75,26),t,font=font(0,16),fill=L['dim'],anchor='mm')
  cxx,cyy=x+75,82;d.arc((cxx-30,cyy-30,cxx+30,cyy+30),135,405,fill=L['line'],width=5)
  frac=[1,.3,.65,.55,.38,.4,.75,.67][i];d.arc((cxx-30,cyy-30,cxx+30,cyy+30),135,135+270*frac,fill=L['accent'],width=5)
  d.text((cxx,cyy),v,font=font(1,17),fill=L['text'],anchor='mm')
 im.save(path)
for name,L in LOOKS.items():fx(L,a.out/f'trackfx_{name}.png')
print('wrote',sorted(x.name for x in a.out.iterdir()))
