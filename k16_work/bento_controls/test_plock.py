"""Execute L1's patched M7 instructions. Synthetic objects; no real audio/device."""
import sys,struct,unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
from test_controls import IMAGE,Fixture,REGS
from test_input import Input
from build import BASE,STATE

LOCK=0x24048c60
class AudioProbe:
 def __init__(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
  self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  for a,n in [(0xe000e000,0x2000),(BASE,0x180000),(0x20000000,0x40000),(0x24000000,0x50000),(0x30000000,0x40000)]:self.u.mem_map(a,n)
  self.u.mem_write(BASE,IMAGE);self.stop=0x081b0000
  self.u.hook_add(UC_HOOK_CODE,lambda u,a,s,d:u.emu_stop() if a==self.stop else None)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def f(self,a,v=None):
  if v is not None:self.u.mem_write(a,struct.pack('<f',v))
  return struct.unpack('<f',self.u.mem_read(a,4))[0]
 def call(self,a,*args):
  for r,v in zip(REGS,args):self.u.reg_write(r,v)
  self.u.reg_write(UC_ARM_REG_SP,0x2003f000);self.u.reg_write(UC_ARM_REG_LR,self.stop|1)
  self.u.emu_start(a|1,0,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==self.stop
 def init_parameter(self,p):self.call(0x0809ffa0,p)
 def base_source(self,p,s):
  self.u.reg_write(UC_ARM_REG_S0,0x3f800000);self.call(0x0809fca0,p,s)
 def mod_source(self,p,s,i):
  self.u.reg_write(UC_ARM_REG_S0,0x3f800000);self.call(0x0809fd00,p,s,i)
 def evaluate(self,p):self.call(0x0809fd80,p);return self.f(p+0x3c)

class Probe(AudioProbe):
 def __init__(self):
  super().__init__();self.u.mem_write(BASE,IMAGE)
  self.obj=0x20024000;self.param=self.obj+0x138;self.seq=0x20028000
  self.w(self.obj,0x080ac66c);self.w(self.obj+12,101)
  self.w(self.seq+12,77);self.u.mem_write(self.seq+0x20,b'\1')
  self.init_parameter(self.param)
  self.f(0x20022004,.8);self.base_source(self.param,0x20022000)
  self.f(0x20022104,.1);self.mod_source(self.param,0x20022100,3)
  self.f(0x20022204,.05);self.mod_source(self.param,0x20022200,0)
 def command(self,key=0x7ffe,context=101,owner=77):
  sp=0x2003e000
  self.u.mem_write(sp+0x28,struct.pack('<6I',0x3e,0,context,key,owner,0))
  before=[0x1010+i for i in range(13)];before[4]=self.obj
  for reg,v in zip(REGS,before):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x20035001)
  self.u.reg_write(UC_ARM_REG_APSR,0xa0000000)
  reached=[]
  def stop(u,a,s,d):
   if a in (0x0808e9e0,0x0808f3a0):reached.append(a);u.emu_stop()
  h=self.u.hook_add(UC_HOOK_CODE,stop)
  try:self.u.emu_start(0x0808f39d,0,count=100000)
  finally:self.u.hook_del(h)
  assert len(reached)==1
  assert self.u.reg_read(UC_ARM_REG_SP)==sp
  assert self.u.reg_read(UC_ARM_REG_APSR)&0xf8000000==0xa0000000
  if key not in (0x7ffe,0x7ffd,0x7ffc):before[2:4]=[key,key&65535]
  assert [self.u.reg_read(r) for r in REGS]==before
  return reached[0]
 def capture(self):
  self.u.reg_write(UC_ARM_REG_R0,self.seq)
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  self.u.reg_write(UC_ARM_REG_APSR,0x60000000)
  self.u.emu_start(0x08061041,0x08061044,count=10000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x08061044
  assert self.u.reg_read(UC_ARM_REG_R0)==self.seq
  assert self.u.reg_read(UC_ARM_REG_R3)==1
  assert self.u.reg_read(UC_ARM_REG_SP)==0x2003e000
  assert self.u.reg_read(UC_ARM_REG_APSR)&0xf8000000==0x60000000

class Tests(unittest.TestCase):
 def native_copy(self,p,voice=0x2002a000):
  # Execute the actual native voice-copy prologue and first complete 64-byte
  # copy, through 0x08092FD6. Later code copies other parameters.
  p.u.reg_write(UC_ARM_REG_R0,p.obj);p.u.reg_write(UC_ARM_REG_R1,voice)
  p.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  p.u.emu_start(0x08092f21,0x08092fda,count=1000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x08092fda)
  self.assertEqual(bytes(p.u.mem_read(voice+0x180,64)),bytes(p.u.mem_read(p.param,64)))
  return voice+0x180
 def test_native_voice_copy_receives_lock_and_returns_float_in_s0(self):
  p=Probe();p.command();p.capture();param=self.native_copy(p)
  root=bytes(p.u.mem_read(p.param,64));sources=bytes(p.u.mem_read(0x20022000,0x300))
  for step in range(16):
   p.w(p.seq+0x14,step);expected=.30 if step%4==0 else .95
   self.assertAlmostEqual(p.evaluate(param),expected,places=6)
   self.assertAlmostEqual(struct.unpack('<f',struct.pack('<I',p.u.reg_read(UC_ARM_REG_S0)))[0],expected,places=6)
  self.assertEqual(bytes(p.u.mem_read(p.param,64)),root)
  self.assertEqual(bytes(p.u.mem_read(0x20022000,0x300)),sources)
 def test_voice_copy_resumes_current_background_after_disarm(self):
  p=Probe();p.command();p.capture();param=self.native_copy(p)
  self.assertAlmostEqual(p.evaluate(param),.30,places=6)
  p.f(0x20022004,.5);p.f(0x20022104,.2);p.command(0x7ffd)
  self.assertAlmostEqual(p.evaluate(param),.75,places=6)
 def test_native_constructor_binds_unique_level_source_used_by_voice_copy(self):
  p=Probe();p.u.reg_write(UC_ARM_REG_R4,p.obj)
  p.u.reg_write(UC_ARM_REG_S16,0x3f800000)
  p.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  p.u.emu_start(0x080956c9,0x080956d8,count=1000)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(p.param,4))[0],p.obj+0x130)
  p.f(p.obj+0x134,.8);p.command();p.capture();param=self.native_copy(p)
  self.assertAlmostEqual(p.evaluate(param),.30,places=6)
 def test_other_sound_base_source_is_not_locked(self):
  p=Probe();p.command();p.capture();param=self.native_copy(p)
  p.f(0x20022304,.6);p.base_source(param,0x20022300)
  self.assertAlmostEqual(p.evaluate(param),.75,places=6)
 def test_native_command_wrapper_preserves_registers_and_consumes_extension(self):
  p=Probe();self.assertEqual(p.command(),0x0808e9e0)
  self.assertEqual(struct.unpack('<8I',p.u.mem_read(LOCK,32)),(0x314c5042,1,77,p.param,0,101,0,0))
 def test_ordinary_property_replays_original_instructions(self):
  p=Probe();self.assertEqual(p.command(2),0x0808f3a0);self.assertEqual(p.u.mem_read(LOCK,32),bytes(32))
 def test_unknown_class_and_wrong_context_cannot_arm(self):
  for vt,ctx in [(0x080ac66c,102),(0x080ac670,101)]:
   p=Probe();p.w(p.obj,vt);p.command(context=ctx);self.assertEqual(p.r(LOCK+4) if hasattr(p,'r') else struct.unpack('<I',p.u.mem_read(LOCK+4,4))[0],0)
 def test_callback_captures_only_owner(self):
  p=Probe();p.command();p.w(p.seq+12,78);p.capture();self.assertEqual(bytes(p.u.mem_read(LOCK+16,4)),bytes(4))
  p.w(p.seq+12,77);p.capture();self.assertEqual(struct.unpack('<I',p.u.mem_read(LOCK+16,4))[0],p.seq)
 def test_actual_patched_evaluator_fixed_pattern_and_no_model_source_mutation(self):
  p=Probe();p.command();p.capture()
  sources=bytes(p.u.mem_read(0x20022000,0x300));param=bytes(p.u.mem_read(p.param,60))
  for step in range(16):
   p.w(p.seq+0x14,step);self.assertAlmostEqual(p.evaluate(p.param),.30 if step%4==0 else .95,places=6)
   self.assertEqual(bytes(p.u.mem_read(p.param,60)),param)
   self.assertEqual(bytes(p.u.mem_read(0x20022000,0x300)),sources)
 def test_disarm_stop_wrong_owner_and_invalid_position_use_current_background(self):
  for mode in ['off','stop','owner','position']:
   p=Probe();p.command();p.capture();p.f(0x20022004,.5);p.f(0x20022104,.2)
   if mode=='off':p.command(0x7ffd)
   elif mode=='stop':p.u.mem_write(p.seq+0x20,b'\0')
   elif mode=='owner':p.w(p.seq+12,78)
   else:p.w(p.seq+0x14,256)
   self.assertAlmostEqual(p.evaluate(p.param),.75,places=6)
 def test_no_arm_is_native(self):
  p=Probe();self.assertAlmostEqual(p.evaluate(p.param),.95,places=6)
 def test_project_arm_targets_selected_drum_and_release_stays(self):
  f=Fixture();f.event(175,7);f.pad(7);f.event(176,7)
  self.assertIn(('engine',11,0x7ffe,80),f.log);self.assertEqual(f.page(),23)
 def test_non_drum_arm_targets_track_and_off_is_sent(self):
  f=Fixture();f.kind=0x10;f.event(175,7);f.pad(7);f.event(176,7)
  self.assertIn(('engine',80,0x7ffe,80),f.log)
  f.event(175,7);self.assertNotIn(('engine',80,0x7ffd,0),f.log)
  f.pad(8);self.assertIn(('engine',80,0x7ffd,0),f.log);f.event(176,7)
 def test_unused_project_tap_is_a_pure_modifier(self):
  f=Fixture();f.event(175,7);f.event(176,7)
  self.assertEqual(f.log,[]);self.assertEqual(f.page(),23)
 def test_project_pads_no_longer_arm_the_legacy_fixed_pattern(self):
  for pad in range(16):
   f=Input();v=[0]*16;v[pad]=1000;f.packet(0x100,v)
   self.assertTrue(f.events());self.assertEqual(f.custom(),[])
 def test_startup_clears_lock_state_and_leaves_ui_owned_state(self):
  f=Input();f.u.mem_write(LOCK,bytes([0xa5])*320);f.u.reg_write(UC_ARM_REG_SP,0x2407e000)
  f.u.emu_start(0x080d0801,0x080404ba,count=200000)
  self.assertEqual(bytes(f.u.mem_read(LOCK,32)),bytes(32))
  self.assertEqual(bytes(f.u.mem_read(STATE+32,224)),bytes([0xa5])*224)

if __name__=='__main__':unittest.main(verbosity=2)
