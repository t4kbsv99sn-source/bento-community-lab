"""Real P19 type-5 allocation/copy/destruction, using its real heap allocator."""
import argparse, struct, unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB
from unicorn.arm_const import *
from native_node_patches import patches, NODE_BYTES, PREFIX
p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
a,rest=p.parse_known_args();IMAGE=a.image.read_bytes()
ROOT=0xc0001000;PARENT=0xc0002000;DEST=0xc0003000;OUT=0x3003f000;BLOCK=0xc0010000;STOP=0x081ff000
class Probe:
 def __init__(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
  for addr,n in [(0x08040000,0x1c0000),(0x20000000,0x40000),(0x24000000,0x80000),(0x30000000,0x40000),(0xc0000000,0x200000)]:self.u.mem_map(addr,n)
  self.u.mem_write(0x08040000,IMAGE)
  for addr,old,new,reason in patches(IMAGE):self.u.mem_write(addr,new)
  self.w(ROOT+0x58+12,BLOCK)
  self.u.mem_write(BLOCK,struct.pack('<6I',0x5a5a5a5a,0x100000,0,0,0,0))
  self.call(0x0812d8ac,PARENT);self.call(0x0812d8ac,DEST)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def call(self,a,*args):
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000);self.u.reg_write(UC_ARM_REG_LR,STOP|1)
  self.u.emu_start(a|1,STOP,count=2000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==STOP,hex(self.u.reg_read(UC_ARM_REG_PC))
  return self.u.reg_read(UC_ARM_REG_R0)
 def create(self):
  assert self.call(0x0812e7dc,ROOT,5,PARENT,OUT)==1
  return self.r(OUT)
class Tests(unittest.TestCase):
 def test_native_allocator_reserves_and_initializes_entire_extension(self):
  p=Probe();p.u.mem_write(BLOCK+24,b'\xa5'*NODE_BYTES);node=p.create()
  self.assertEqual(p.r(node-16),NODE_BYTES)
  self.assertEqual(p.u.mem_read(node+8,1),b'\5')
  self.assertEqual(p.u.mem_read(node+10,NODE_BYTES-10),bytes(NODE_BYTES-10))
  self.assertEqual(p.r(node+NODE_BYTES),0x5a5a5a5a)
 def test_native_deep_copy_preserves_all_motion_and_original_lane_bytes(self):
  p=Probe();node=p.create();payload=bytes((i*37+11)%256 for i in range(NODE_BYTES-10))
  p.u.mem_write(node+10,payload)
  self.assertEqual(p.call(0x0812e270,PARENT,ROOT+0x58,DEST),1)
  copied=p.r(DEST+20);self.assertNotEqual(node,copied)
  self.assertEqual(p.r(copied-16),NODE_BYTES)
  self.assertEqual(p.u.mem_read(copied+10,len(payload)),payload)
  p.u.mem_write(node+PREFIX,b'changed!')
  self.assertNotEqual(p.u.mem_read(node+PREFIX,8),p.u.mem_read(copied+PREFIX,8))
  self.assertEqual(p.r(copied+NODE_BYTES),0x5a5a5a5a)
 def test_native_free_accepts_enlarged_node(self):
  p=Probe();p.create();p.call(0x0812d978,PARENT,ROOT+0x58)
  self.assertEqual(p.r(PARENT+20),0)
  node=p.create();self.assertGreater(node,0)
 def test_other_native_node_types_keep_their_original_allocation_size(self):
  for kind,size in [(1,24),(2,12304),(3,528),(4,192)]:
   p=Probe();self.assertEqual(p.call(0x0812e7dc,ROOT,kind,PARENT,OUT),1)
   self.assertEqual(p.r(p.r(OUT)-16),size)
if __name__=='__main__':unittest.main(argv=[__file__,*rest])
