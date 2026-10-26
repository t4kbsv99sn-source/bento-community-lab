"""Native MPU enforcement and early startup with the FPU disabled.
This checks the known F1/K8 failure classes; it is not a full device emulator.
"""
from pathlib import Path
import json,os,struct,unittest
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ['BENTO_FX_CANDIDATE']);IMAGE=(OUT/'bento1.bin').read_bytes()
BASELINE=Path(os.environ['BENTO_K16_IMAGE']).read_bytes();MAN=json.loads((OUT/'manifest.json').read_text())
BASE=0x08040000
class Machine:
 def __init__(self,core,image=IMAGE):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);self.core=core
  self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4 if core==4 else UC_CPU_ARM_CORTEX_M7)
  for a,n in [(BASE,0x1c0000),(0x20000000,0x40000),(0x24000000,0x80000),(0x30000000,0x40000),(0xe000e000,0x2000)]:self.u.mem_map(a,n)
  self.u.mem_write(BASE,image);self.regions={};self.control=0;self.enforce=False;self.accesses=[]
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.mpu,begin=0xe000ed94,end=0xe000eda3)
  self.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,self.access,begin=0x24000000,end=0x2407ffff)
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def mpu(self,u,kind,a,size,value,data):
  if a==0xe000ed94:self.control=value
  if a==0xe000eda0:self.regions[self.r(0xe000ed98)]=(self.r(0xe000ed9c),value)
 def allowed(self,a,execute=False):
  if not self.control&1:return True
  for _,(base,r) in sorted(self.regions.items(),reverse=True):
   size=1<<(((r>>1)&31)+1);base&=~(size-1)
   if not r&1 or not base<=a<base+size:continue
   if size>=256 and r&(1<<(8+(a-base)*8//size)):continue
   return (r>>24)&7==3 and (not execute or not r&(1<<28))
  return bool(self.control&4)
 def access(self,u,kind,a,size,value,data):
  if self.enforce:
   assert self.allowed(a) and self.allowed(a+size-1),f'MPU denied {a:08x}'
   self.accesses.append((a,size))
 def call(self,a,end=0x3003f000):
  self.u.reg_write(UC_ARM_REG_SP,0x3003e000);self.u.reg_write(UC_ARM_REG_LR,0x3003f001)
  self.u.emu_start(a|1,end,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==end,hex(self.u.reg_read(UC_ARM_REG_PC))
 def configure(self):self.call(0x08114d74 if self.core==4 else 0x0804fa00)
class Tests(unittest.TestCase):
 def test_native_c6_ui_heap_is_privileged_accessible_without_mpu_change(self):
  # Initial data copied by native reset sets allocator end/start at offsets48/4c.
  import struct
  stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes()
  self.assertEqual(struct.unpack_from('<2I',stock,0x081b3e38-BASE+0x48),(0xc8000000,0xc6000000))
  for core in [4,7]:
   p=Machine(core);p.configure()
   self.assertTrue(p.allowed(0xc6000000));self.assertTrue(p.allowed(0xc7ffffff))

 def test_native_mpu_unchanged_and_all_new_state_permitted_on_both_cores(self):
  for core in [4,7]:
   old=Machine(core,BASELINE);old.configure();p=Machine(core);p.configure()
   self.assertEqual((p.regions,p.control),(old.regions,old.control))
   for a in range(0x24040000,0x24042000,32):self.assertTrue(p.allowed(a),hex(a))
   code=(0x081c0000,BASE+len(IMAGE)) if core==4 else (0x080dc000,0x080e0000)
   for a in range(*code,32):self.assertTrue(p.allowed(a,True),hex(a))
   if core==4:self.assertFalse(p.allowed(0x2403a400))
 def test_ui_startup_no_fpu_and_permissions_enforced_and_owner_boundaries(self):
  p=Machine(4);p.configure();p.enforce=True
  p.u.mem_write(0x24040000,b'\xa5'*0x2000);p.u.mem_write(0x24042000,b'\x6b'*32)
  p.u.reg_write(UC_ARM_REG_R4,0x12345678);p.call(0x081004b6,0x081004ba)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R4),0x12345678)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0x081891fc)
  self.assertEqual(bytes(p.u.mem_read(0x24041440,0x280)),bytes(0x280))
  self.assertEqual(bytes(p.u.mem_read(0x24041a00,0x600)),bytes(0x600))
  self.assertEqual(bytes(p.u.mem_read(0x24040000,0x1440)),b'\xa5'*0x1440)
  self.assertEqual(bytes(p.u.mem_read(0x240416c0,0x340)),b'\xa5'*0x340)
  self.assertEqual(bytes(p.u.mem_read(0x24042000,32)),b'\x6b'*32)
 def test_audio_startup_no_fpu_preserves_mailbox_and_k16_startup(self):
  p=Machine(7);p.configure();p.enforce=True
  p.u.mem_write(0x24040000,b'\xa5'*0x2000);p.call(0x080404b6,0x080404ba)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0x080a5f9c)
  self.assertEqual(bytes(p.u.mem_read(0x24040000,0x1440)),bytes(0x1440))
  self.assertEqual(bytes(p.u.mem_read(0x240416c0,0x340)),bytes(0x340))
  self.assertEqual(bytes(p.u.mem_read(0x24041440,0x280)),b'\xa5'*0x280)
  self.assertEqual(bytes(p.u.mem_read(0x24041a00,0x600)),b'\xa5'*0x600)
 def test_new_ui_code_contains_no_floating_point_instructions(self):
  # Limit disassembly to executable ELF symbol sizes (exclude string literals).
  # P1: only FUNC symbols are code (data such as label tables can decode as
  # anything); the next symbol of any kind still bounds each function.
  from build_fx import R
  b=(R/'ui.elf').read_bytes();off=struct.unpack_from('<I',b,32)[0];step,n=struct.unpack_from('<HH',b,46)
  ss=[struct.unpack_from('<10I',b,off+i*step) for i in range(n)];funcs=set();starts=set()
  for sh in ss:
   if sh[1]!=2:continue
   for i in range(0,sh[5],sh[9]):
    _,value,size,info,_,_=struct.unpack_from('<IIIBBH',b,sh[4]+i)
    if info&15==2:funcs.add(value&~1);starts.add(value&~1)
    elif info&15==1:starts.add(value)
  starts=sorted(starts);c=Cs(CS_ARCH_ARM,CS_MODE_THUMB);self.assertGreater(len(funcs),100)
  for start in sorted(funcs):
   end=next((a for a in starts if a>start),start+20)
   for i in c.disasm(IMAGE[start-BASE:end-BASE],start):self.assertFalse(i.mnemonic.startswith('v'),str(i))
 def test_native_millisecond_counter_used_by_gesture(self):
  p=Machine(4);p.u.mem_write(0x3001fe2c,struct.pack('<I',0xfffffff0));p.call(0x081152c0)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0xfffffff0)
 def test_patch_reversal_alignment_vectors_recovery_and_heap_guards(self):
  pre=IMAGE
  if (OUT/'MOTION_MANIFEST.json').exists():
   # P22: the motion layer is applied to the complete Playground image (fx/).
   pre=(OUT/'fx/bento1.bin').read_bytes();layer=bytearray(IMAGE)
   for w in reversed(json.loads((OUT/'MOTION_MANIFEST.json').read_text())['writes']):
    a=w['address']-BASE;self.assertEqual(IMAGE[a:a+w['size']].hex(),w['replacement_hex'])
    layer[a:a+w['size']]=bytes.fromhex(w['original_hex'])
   self.assertEqual(bytes(layer[:len(pre)]),pre);self.assertFalse(any(layer[len(pre):]))
  restored=bytearray(pre)
  for w in reversed(MAN['writes']):
   a=w['address']-BASE;self.assertEqual(pre[a:a+w['size']].hex(),w['replacement_hex'])
   restored[a:a+w['size']]=bytes.fromhex(w['original_hex'])
  self.assertEqual(bytes(restored[:len(BASELINE)]),BASELINE);self.assertEqual(len(IMAGE)%4,0)
  motion_manifest=OUT/'MOTION_MANIFEST.json'
  if motion_manifest.exists():
   motion=json.loads(motion_manifest.read_text())
   for w in motion['writes']:
    self.assertFalse(0x080e0000<=w['address']<0x08100000) # P22b: never the 080E0000 program sector
  for a,n in [(BASE,0x400),(0x080e0000,0x20000),(0x08100000,0x400),(0x08114d74,0x180),(0x0804fa00,0x200)]:
   self.assertEqual(IMAGE[a-BASE:a-BASE+n],BASELINE[a-BASE:a-BASE+n])
  for a in [0x08040588,0x080a3bdc,0x080a3e94]:self.assertEqual(struct.unpack_from('<I',IMAGE,a-BASE)[0],0x24040000)
if __name__=='__main__':unittest.main(verbosity=2)
