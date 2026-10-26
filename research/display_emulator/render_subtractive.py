"""Render S1's native sample-editor widgets; model/file reads are fixtures.
Native constructors, descriptor configuration, fonts, widgets and paint run.
"""
import argparse,json,sys
from pathlib import Path
import emu,render
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
e=emu.Emu(str(a.build/'bento1.bin'));render.boot_gfx(e)
symbols=json.loads((a.build/'manifest.json').read_text())['ui_symbols']
V=0xc0400000
_keep=[]
def service(address,fn):
 def callback(u,addr,size,data):
  regs=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  value=fn(regs);u.reg_write(UC_ARM_REG_R0,value or 0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 _keep.append(callback);e.u.hook_add(UC_HOOK_CODE,callback,begin=address,end=address)
service(0x08133f7c,lambda r:1)
def path(r):e.u.mem_write(r[3],b'\\Projects\\BENTO_Synth_Subtractive.wav\0');return 1
service(0x0813390e,path)
def value(r):e.w(r[3],{0x1e:10,0x1f:200,0x20:800,0x21:120}.get(r[2],0));return 1
service(0x08133614,value)
e.call(0x08153560,V)
e.call(0x081639a8,0)
e.w(V+0x87bc,0x13e);e.w(V+0x87c4,0x13f);e.u.mem_write(V+0x87cc,b'\x0e')
e.call(0x08152144,V)
e.w(V+0x87bc,0x13e);e.w(V+0x87c4,0x13f);e.u.mem_write(V+0x87cc,b'\x0e')
e.call(symbols['kick_ui_before'],V);e.call(symbols['kick_ui_after'],V)
e.u.mem_write(0x30024b00+0x14c,b'\x01')
flags=0x24071000;e.u.mem_write(flags,b'\x01\x01'+bytes(6))
for off in [0x38,0x2430,0x4828]:
 bar=V+off
 e.call(e.r(e.r(bar)),bar,flags)
# Native layout uses a 1280x424 content area above the persistent header.
rect=0x24070000
e.u.mem_write(V+4,__import__('struct').pack('<4i',0,0,1280,424))
render.clear(e,0xf1);e.w(render.CTX,0x101);render.paint(e,V)
a.out.parent.mkdir(parents=True,exist_ok=True);render.save(e,str(a.out))
print('Native sample editor render:',a.out)
