"""Render the Wavetable page's two wave panes on an Analog track (P4/P6).
The synth page view is built by its native constructor (0815E228); pane
visibility is set as the Wavetable builder does (0815F6DA: +2E90/+31F0 hidden,
+3550/+36C8 shown). Ticks go through each pane's vtable [0]; the whole view
is painted through the native widget tree (render.paint), so only hooks that
the device would reach can draw. Model reads are fixtures."""
import argparse,json,struct
from pathlib import Path
import emu,render
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--shapes',default='0,96,160,240');a=p.parse_args()
e=emu.Emu(str(a.build/'bento1.bin'));render.boot_gfx(e)
TRACK=0x91;V=0xc0400000;KEEP=[]
def service(address,fn):
 def cb(u,addr,size,data):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];v=fn(r)
  u.reg_write(UC_ARM_REG_R0,(v or 0)&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 KEEP.append(cb);e.u.hook_add(UC_HOOK_CODE,cb,begin=address,end=address)
def track(r):e.w(r[1],TRACK);return 1
service(0x08133cfc,track)
service(0x08133f7c,lambda r:18 if e.r(r[1])==TRACK else 0)
e.call(0x0815e228,V)
# Analog track: KickKnobs entry, engine 13.
K=0x24043500;e.w(K,0x35424e4b);e.w(K+4,2);e.w(K+32,2);e.w(K+36,TRACK);e.u.mem_write(K+47,bytes([13]))
for off,hidden in [(0x2e90,1),(0x31f0,1),(0x3550,0),(0x36c8,0)]:e.u.mem_write(V+off+0x30,bytes([hidden]))
e.u.mem_write(V+4,struct.pack('<4i',0,0,1280,424))
panes=[V+0x3550,V+0x36c8];shapes=[int(x) for x in a.shapes.split(',')]
a.out.mkdir(parents=True,exist_ok=True)
for n,s in enumerate(shapes):
 e.w(V+0x10154,s);e.w(V+0x10158,255-s)
 flags=0x24071000;e.u.mem_write(flags,b'\0'*8);e.w(0x3001fe2c,1000+100*n)
 for w in panes:e.call(e.r(e.r(w)),w,flags)
 render.clear(e,0xf1);e.u.mem_write(render.CTX,struct.pack('<II',1,render.SURF))
 render.paint(e,V)
 render.save(e,str(a.out/f'analog_{s}.png'),crop=(0,60,660,380))
 print('shape',s,'label hidden',[e.u.mem_read(w+0x104+0x30,1)[0] for w in panes])
