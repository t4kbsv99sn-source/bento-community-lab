import sys,struct,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import emu,render
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);args=parser.parse_args();b=args.build;e=emu.Emu(str(b/'bento1.bin'));render.boot_gfx(e);e.call(0x08180198,render.ROOT)
KEEP=[]
def service(a,fn):
 def cb(u,at,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];v=fn(r);u.reg_write(UC_ARM_REG_R0,v or 0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 KEEP.append(cb);e.u.hook_add(UC_HOOK_CODE,cb,begin=a,end=a)
service(0x08133cfc,lambda r:(e.w(r[1],0x91),1)[1]);service(0x08133f7c,lambda r:18)
e.u.mem_write(0x30024b00+0x12c,b'\x17');e.u.mem_write(0x24070000,render.tpl(e,8));e.call(0x0817faf8,render.ROOT,0x24070000)
(b/'screens').mkdir(parents=True,exist_ok=True);render.clear(e,0xf1);e.u.mem_write(render.CTX,struct.pack('<II',1,render.SURF));render.paint(e,render.ROOT);render.save(e,str(b/'screens/euclidean_header.png'),crop=(0,425,1280,480))
print('Native Euclidean button id',hex(e.r(render.ROOT+0x54c+4*0xd0+0x14)))
