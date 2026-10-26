"""P27: render the synth page with its native encoder strip, then with the
macro strip pulled in (swipe left) and macro 3 armed. Based on render_p12_mod.
Original note: Render the synth page in P8 mod mode: header (MOD/MATRIX), orange source
outlines and depth on the encoders. The view is built by its native
constructor; mod mode is driven through the hooked vtable entries and the
header through mod_toolbar + the native header apply (0817FAF8). Model reads,
the route store and the track tree are fixtures."""
import argparse,json,struct
from pathlib import Path
import emu,render
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
uu=json.loads((a.build/'manifest.json').read_text())['ui_symbols']
e=emu.Emu(str(a.build/'bento1.bin'));render.boot_gfx(e);e.call(0x08180198,render.ROOT)
TRACK=0x91;V=0xc0400000;KEEP=[]
KIDS=[(0x200,6),(0x201,6),(0x202,8),(0x203,9),(0x204,9),(0x205,10),(0x206,10),(0x207,11),(0x208,11)]
routes={}
def service(address,fn):
 def cb(u,addr,size,data):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];v=fn(r)
  u.reg_write(UC_ARM_REG_R0,(v or 0)&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 KEEP.append(cb);e.u.hook_add(UC_HOOK_CODE,cb,begin=address,end=address)
def track(r):e.w(r[1],TRACK);return 1
service(0x08133cfc,track)
service(0x08133f7c,lambda r:18 if e.r(r[1])==TRACK else dict(KIDS).get(e.r(r[1]),0))
def kids(r):
 if e.r(r[1])==TRACK and r[2]<len(KIDS):e.w(r[3],KIDS[r[2]][0]);return 1
 return 0
service(0x0813391a,kids)
def lookup(r):
 x=routes.get((e.r(r[1]),r[2]&0xffff,r[3]))
 if not x:return 0
 out=e.r(e.u.reg_read(UC_ARM_REG_SP));e.w(out,x[1]);e.w(out+4,x[0]);e.w(out+8,r[3]);return 1
service(0x08131244,lookup)
def model_event(r):
 ev=struct.unpack('<5I',e.u.mem_read(r[1],20))
 if ev[0]==0xd1:
  src=ev[3]&0xffff;key=(ev[1],ev[2]&0xffff,ev[3]>>16)
  if src:routes[key]=(src,struct.unpack('<i',struct.pack('<I',ev[4]))[0])
  else:routes.pop(key,None)
 return 0
service(0x081403ec,model_event)
service(0x08133614,lambda r:(e.w(r[3],500),1)[1])
service(0x0813130c,lambda r:0)
e.call(0x0815e228,V);e.w(V+0x2430,TRACK)
for off,hidden in [(0x2e90,1),(0x31f0,1),(0x3550,0),(0x36c8,0)]:e.u.mem_write(V+off+0x30,bytes([hidden]))
e.u.mem_write(V+4,struct.pack('<4i',0,0,1280,424))
e.u.mem_write(V+0x10238,bytes([5]))
# Registry for slot keys (native descriptors).
e.call(0x081639a8,0)
for i,k in enumerate([0xce,0x33]):e.call(0x08171c1c,V+0x70+i*0x468,k,500,1)
PT=0x24070900;BAR=V+0x38
def touch(fn,x,y):e.w(PT,x);e.w(PT+4,y);e.call(uu[fn],BAR,PT,0)
def shot(name):
 buf=0x24070000;e.u.mem_write(buf,render.tpl(e,10));e.call(uu['macro_periodic'],buf)
 render.page_reset(e);e.call(0x0817FAF8,render.ROOT,buf)
 render.clear(e,0xf1);e.u.mem_write(render.CTX,struct.pack('<II',1,render.SURF))
 render.paint(e,V);render.paint(e,render.ROOT);a.out.mkdir(parents=True,exist_ok=True);render.save(e,str(a.out/name))
shot('p27_native_strip.png')
touch('macro_bar_down',700,440)
for k in range(1,6):touch('macro_bar_move',700-40*k,440)
touch('macro_bar_up',500,440)
shot('p27_macro_strip.png')
x=e.r(BAR+0x38+2*0x468+4)+20;touch('macro_bar_down',x,440);touch('macro_bar_up',x,440)
shot('p27_macro3_armed.png')
print('slot rects',[(e.r(BAR+0x38+i*0x468+4),e.r(BAR+0x38+i*0x468+8)) for i in range(8)],'bar',[e.r(BAR+4+4*i) for i in range(4)])
