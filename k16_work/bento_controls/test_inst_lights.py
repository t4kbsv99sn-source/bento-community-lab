"""Native playback flags, SEQ palette rebuild and hardware LED queue regression.
Navigation's non-LED UI work and unloaded-sample lookup are substitutes.
Playback snapshots, LED flags, palette loop, flush and queue writer are native.
"""
import struct,unittest
from test_mixer_lights import NativeLights
from unicorn.arm_const import *

class InstLights(NativeLights):
 def __init__(self):
  super().__init__();self.kind=14;self.led=self.m+0x19c4
  self.props[(self.globalobj,0x189)]=2
  self.engine_status=self.engine+0x51ac
  # Synthetic INST palette; native updater chooses these colours for playing pads.
  for pad in range(16):self.w(self.led+pad*16+4,0x7f0000)
  self.w(self.m+0x1b08,0xffffffff)
  self.w(self.m+0x144,0)
  self.w(self.m+0x148,0)
  self.w(self.m+0x3c80+0x3000,2)
  for i,step in enumerate([2,8]):
   raw=bytearray(24);raw[0]=1
   struct.pack_into('<HIII',raw,2,2,step*960,960,i+1)
   self.u.mem_write(self.m+0x3c80+i*24,bytes(raw))
 def hook(self,u,a,size,data):
  if a==0x081353a2:self.ret(0);return # Sample not loaded in synthetic model.
  if a==0x081420ec:
   self.page(u.reg_read(UC_ARM_REG_R1));self.log.append(('nav',self.page()))
   # Run the complete original LED builder after the synthetic view transition.
   u.reg_write(UC_ARM_REG_PC,0x08139139);return
  super().hook(u,a,size,data)
 def call(self,a,ptr=None):
  self.u.reg_write(UC_ARM_REG_R0,self.m if ptr is None else ptr)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000)
  self.u.reg_write(UC_ARM_REG_LR,0x0813f2fd)
  self.u.emu_start(a|1,0,count=30000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x0813f2fc
 def playback(self,pads):
  statuses=bytearray(16)
  for pad in pads:statuses[pad]=3
  self.u.mem_write(self.engine_status,bytes(statuses))
  self.call(0x0813c318)
 def flags(self):return [self.u.mem_read(self.led+i*16+12,1)[0] for i in range(16)]
 def begin(self):
  self.page(0x27);self.event(175,10);assert self.page()==7
 def finish(self):self.choose(2);self.event(176,10)
 def flush(self):self.call(0x081257f0,self.led)

class Tests(unittest.TestCase):
 def test_seq_refresh_clears_stale_instrument_playing_flags(self):
  f=InstLights();f.page(7);f.playback([0,5,15])
  self.assertEqual(f.flags(),[int(i in [0,5,15]) for i in range(16)])
  f.page(0x27);f.call(0x08139138);f.playback([])
  self.assertEqual(f.flags(),[0]*16)
  self.assertEqual([i for i,c in enumerate(f.colors()) if c],[2,8])
 def test_inst_return_clears_stale_playing_flags_on_each_pad(self):
  for pad in range(16):
   f=InstLights();f.begin();f.playback([pad]);self.assertEqual(f.flags()[pad],1)
   f.finish();self.assertEqual(f.page(),0x27);self.assertEqual(f.flags(),[0]*16)
   self.assertEqual([i for i,c in enumerate(f.colors()) if c],[2,8])
 def test_return_sends_black_for_stale_empty_pads_and_keeps_active_steps(self):
  f=InstLights();f.begin();f.playback(range(16));f.flush();f.drain()
  f.finish()
  packets={struct.unpack_from('<I',p,8)[0]-16:p for p in f.pending() if p[0]==0xb4}
  for pad in range(16):
   if pad in [2,8]:continue
   self.assertIn(pad,packets)
   self.assertEqual(struct.unpack_from('<I',packets[pad],12)[0],0)
  self.assertTrue(f.colors()[2]);self.assertTrue(f.colors()[8])
  self.assertEqual(f.flags(),[0]*16)
 def test_no_selection_stays_on_inst_and_keeps_live_feedback(self):
  f=InstLights();f.begin();f.playback([1,7]);before=f.flags();f.event(176,10)
  self.assertEqual(f.page(),7);self.assertEqual(f.flags(),before)
  f.playback([]);self.assertEqual(f.flags(),[0]*16)
 def test_cancelled_return_does_not_clear_another_views_lights(self):
  f=InstLights();f.begin();f.playback([1,7]);f.choose(2);f.page(0x13)
  before=f.flags();f.event(176,10)
  self.assertEqual(f.page(),0x13);self.assertEqual(f.flags(),before)
 def test_repeated_sound_selection_returns_do_not_accumulate_lights(self):
  f=InstLights()
  for pads in [[0,3],[4,9,11],list(range(16)),[]]:
   f.begin();f.playback(pads);f.finish()
   self.assertEqual(f.flags(),[0]*16)
   self.assertEqual([i for i,c in enumerate(f.colors()) if c],[2,8])

if __name__=='__main__':unittest.main(verbosity=2)
