"""Execute the new M7 adapter with the real native A-D constructor/update.

This installs the linked module only in an emulator's memory. It neither
patches an installation image nor establishes hardware/cache behaviour.
"""
import argparse, struct, unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *

def elf(path):
 b=path.read_bytes();off=struct.unpack_from('<I',b,32)[0];step,n=struct.unpack_from('<HH',b,46)
 sections=[struct.unpack_from('<10I',b,off+i*step) for i in range(n)];chunks=[];symbols={}
 for s in sections:
  if s[2]&2:chunks.append((s[3],b[s[4]:s[4]+s[5]]))
  if s[1]!=2:continue
  st=sections[s[6]];strings=b[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   name,value,size,info,_,idx=struct.unpack_from('<IIIBBH',b,s[4]+i)
   if info&15==2:symbols[strings[name:].split(b'\0')[0].decode()]=value&~1
 return chunks,symbols

parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--elf',type=Path,required=True)
args,remaining=parser.parse_known_args();IMAGE=args.image.read_bytes();CHUNKS,SYMS=elf(args.elf)
SEQ=0xc0080000;EU=0xc0100000;DEVICE=0xc0110000;CLIP=0xc0140000;TIME=0x20030000;STOP=0x081ff000
LANE_BYTES=1048;CLIP_BYTES=4224;RUNTIME_BYTES=8448;DEVICE_BYTES=544+8*RUNTIME_BYTES
KEEP=[]
class Probe:
 def __init__(self,device=True):
  KEEP.append(self);self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
  for p,n in [(0x08040000,0x1c0000),(0x20000000,0x40000),(0x24000000,0x80000),(0x30000000,0x40000),(0xc0000000,0x200000),(0xe000e000,0x2000)]:self.u.mem_map(p,n)
  self.u.mem_write(0x08040000,IMAGE)
  for p,b in CHUNKS:self.u.mem_write(p,b)
  self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  self.call(0x08062a80,SEQ) # real native constructor, including source pointers
  self.w(SEQ+12,100);self.w(SEQ+0x14,0);self.u.mem_write(SEQ+0x20,b'\1')
  self.w(SEQ+0x86c0,SEQ+0x240);self.w(SEQ+0x244,32)
  self.w(0x24041fc0,0x324c5545);self.w(0x24041fc4,EU);self.w(0x24041fc8,45920)
  if device:
   self.w(EU+20,DEVICE)
   self.u.mem_write(DEVICE,struct.pack('<8I',0x31444d50,DEVICE_BYTES,1,1,2,0,0,0))
   self.w(DEVICE+32,CLIP)
   self.u.mem_write(CLIP,struct.pack('<8I',2,100,0,1,0,0,0,0))
   for i in range(4):self.lane(i,[],active=0)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def f(self,a):return struct.unpack('<f',self.u.mem_read(a,4))[0]
 def call(self,addr,*args):
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000);self.u.reg_write(UC_ARM_REG_LR,STOP|1)
  self.u.emu_start(addr|1,STOP,count=2000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==STOP,hex(self.u.reg_read(UC_ARM_REG_PC))
 def lane(self,index,points,bars=16,origin=0,active=1):
  p=CLIP+32+index*LANE_BYTES
  self.u.mem_write(p,bytes(LANE_BYTES))
  for i,(tick,value) in enumerate(points):self.w(p+4*i,tick//10|value<<20)
  self.w(p+1024,15360);self.u.mem_write(p+1032,struct.pack('<QHHBB2x',origin,len(points),bars,active,1))
 def tick(self,t,native=False):
  self.u.mem_write(TIME,struct.pack('<q',t));self.call(0x08061040 if native else SYMS['motion_native_automation'],SEQ,TIME)
  return [self.f(SEQ+0x8740+8*i) for i in range(4)]
 def bump(self,serial=4):self.w(CLIP,serial)

class Tests(unittest.TestCase):
 def test_unpublished_bank_keeps_exact_native_output(self):
  a=Probe(device=False);b=Probe(device=False)
  self.assertEqual(a.tick(0),b.tick(0,native=True))
  self.assertEqual(bytes(a.u.mem_read(SEQ+0x871c,64)),bytes(b.u.mem_read(SEQ+0x871c,64)))
 def test_native_constructor_source_pointers_are_the_traced_objects(self):
  p=Probe();self.assertEqual(p.r(SEQ+0x875c),SEQ+0x873c);self.assertEqual(p.r(SEQ+0x8760),SEQ+0x871c)
 def test_two_independent_lanes_hold_and_wrap_at_their_own_lengths(self):
  p=Probe();p.lane(0,[(0,500),(3*15360,1000)],16);p.lane(1,[(0,0),(15360,1000)],32)
  self.assertEqual(p.tick(0)[:2],[0.,-1.])
  self.assertAlmostEqual(p.tick(3840)[0],1/3,places=2)
  p.w(SEQ+0x240+0x20,2*3840) # musical clip origin advances, motion does not
  self.assertEqual(p.tick(10*3840)[:2],[1.,1.])
  self.assertEqual(p.tick(16*3840)[:2],[0.,1.])
  self.assertEqual(p.tick(32*3840)[:2],[0.,-1.])
 def test_clip_switch_does_not_leak_previous_motion(self):
  p=Probe();p.lane(0,[(0,1000)]);self.assertEqual(p.tick(0)[0],1.)
  p.w(SEQ+0x86c0,SEQ+0x240+0x848)
  # Selected row is now 1; only row 0 has a published motion clip.
  value=p.tick(100)[0];control=Probe(device=False);control.w(SEQ+0x86c0,SEQ+0x240+0x848)
  self.assertEqual(value,control.tick(100,native=True)[0])
 def test_shortening_hides_tail_without_retiming_or_erasing(self):
  p=Probe();p.lane(0,[(0,0),(7*15360,1000)],4);before=bytes(p.u.mem_read(CLIP,CLIP_BYTES))
  self.assertEqual(p.tick(3*3840)[0],-1.);self.assertEqual(bytes(p.u.mem_read(CLIP,CLIP_BYTES)),before)
  p.lane(0,[(0,0),(7*15360,1000)],8);p.bump();self.assertEqual(p.tick(7*3840)[0],1.)
 def test_odd_serial_uses_last_complete_snapshot(self):
  p=Probe();p.lane(0,[(0,1000)]);self.assertEqual(p.tick(0)[0],1.)
  p.bump(3);p.lane(0,[(0,0)]);self.assertEqual(p.tick(1)[0],1.)
  p.bump(4);self.assertEqual(p.tick(2)[0],-1.)
 def test_rewind_and_explicit_launch_reset_only_the_clip_phase(self):
  p=Probe();p.lane(0,[(0,500),(15360,1000)]);p.tick(0);self.assertEqual(p.tick(3840)[0],1.)
  self.assertEqual(p.tick(0)[0],0.)
  p.tick(3840);p.w(SEQ+0x14,0xffffffff);p.call(SYMS['motion_native_restart'],SEQ)
  p.w(SEQ+0x14,0);self.assertEqual(p.tick(2*3840)[0],0.)
 def test_clips_are_never_written_by_audio_and_cache_publication_is_disjoint(self):
  p=Probe();p.lane(0,[(0,1000)]);writes=[]
  p.u.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,addr,size,val,d:writes.append((addr,size)),begin=CLIP,end=CLIP+CLIP_BYTES-1)
  p.w(0xe000ed14,1<<16);p.tick(0);self.assertEqual(writes,[])
 def gate(self,p,down,shift=0,ui=0,kind=0x91):
  packet=TIME+64;p.u.mem_write(packet,struct.pack('<5I',kind,0,0,0,down))
  raw=0x24010000;p.w(0x2401bd3c,raw);p.u.mem_write(raw+0x2338,struct.pack('<H',0x100 if shift else 0))
  p.w(0x24048d68,ui);p.call(SYMS['motion_native_record_gate'],packet)
  return p.u.reg_read(UC_ARM_REG_R0)
 def test_record_packets_are_dropped_while_proj_is_held_whatever_word_16_says(self):
  # P24: owner on P23 saw PROJ+RECORD start the normal recorder; same rule as P12 PLAY.
  p=Probe()
  for down in (0,1,7):
   self.assertEqual(self.gate(p,down,shift=1),1);self.assertEqual(self.gate(p,down,ui=1),1)
   self.assertEqual(self.gate(p,down),0)
 def test_unrelated_transport_packets_pass_even_with_shift(self):
  p=Probe();self.assertEqual(self.gate(p,1,shift=1,ui=1,kind=0x90),0);self.assertEqual(self.gate(p,1,shift=1,kind=0x8f),0)
 def test_reader_rejects_a_racing_copy_without_damaging_accepted_audio(self):
  p=Probe();p.lane(0,[(0,1000)]);self.assertEqual(p.tick(0)[0],1.)
  p.lane(0,[(0,0)]);p.bump(4);fired=[]
  def race(u,kind,addr,size,value,data):
   if not fired:fired.append(1);p.bump(5)
  handle=p.u.hook_add(UC_HOOK_MEM_READ,race,begin=CLIP+32,end=CLIP+32+LANE_BYTES-1)
  self.assertEqual(p.tick(1)[0],1.);self.assertEqual(fired,[1]);p.u.hook_del(handle)
  p.bump(6);self.assertEqual(p.tick(2)[0],-1.)
 def test_other_native_automation_lanes_remain_native(self):
  p=Probe();control=Probe(device=False);p.lane(0,[(0,1000)]);clip=SEQ+0x240
  for fixture in (p,control):
   fixture.u.mem_write(clip+0x23c,struct.pack('<h',-500));fixture.u.mem_write(clip+0x43c,b'\1')
  # Native smoothing is intentionally retained; it does not jump to -.5.
  expected=control.tick(0,native=True);actual=p.tick(0)
  self.assertEqual(actual[0],1.);self.assertEqual(actual[1:],expected[1:])

if __name__=='__main__':unittest.main(argv=['test_native_audio.py',*remaining])
