"""Persistent SEQ instrument-overlay isolation, with original playback colors."""
import unittest,struct
from test_inst_lights import InstLights
from test_controls import REGS
from unicorn.arm_const import *

class Tests(unittest.TestCase):
 def test_late_highlights_after_inst_return_are_removed_on_next_seq_refresh(self):
  f=InstLights();f.begin();f.playback([1,6]);f.finish();f.drain()
  # Reproduce an instrument-layer update after the one-shot return cleanup.
  for pad in [1,6,15]:f.u.mem_write(f.led+pad*16+12,b'\1')
  f.flush();f.drain();f.playback([1,6,15])
  self.assertEqual(f.flags(),[0]*16)
  packets={struct.unpack_from('<I',p,8)[0]-16:p for p in f.pending() if p[0]==0xb4}
  for pad in [1,6,15]:self.assertEqual(struct.unpack_from('<I',packets[pad],12)[0],0)
 def test_seq_refresh_preserves_playhead_layer_and_base_step_palette(self):
  f=InstLights();f.begin();f.finish();before=f.colors()
  for pad in range(16):
   f.u.mem_write(f.led+pad*16+12,b'\1')
   f.u.mem_write(f.led+pad*16+13,bytes([pad%2]))
  f.playback(range(16))
  self.assertEqual(f.flags(),[0]*16);self.assertEqual(f.colors(),before)
  self.assertEqual([f.u.mem_read(f.led+i*16+13,1)[0] for i in range(16)],[i%2 for i in range(16)])
 def test_seq_without_stale_overlays_does_not_queue_extra_led_traffic(self):
  f=InstLights();f.begin();f.finish();f.drain()
  for i in range(10):f.playback(range(16))
  self.assertEqual(f.pending(),[])
 def test_inst_still_has_live_playback_feedback_after_repeat_returns(self):
  f=InstLights()
  for pad in [0,5,15]:
   f.begin();f.playback([pad]);self.assertEqual(f.flags()[pad],1)
   f.finish();self.assertEqual(f.flags(),[0]*16)
 def test_seq_early_return_keeps_native_private_registers_stack_and_flags(self):
  f=InstLights();f.page(0x27)
  f.u.mem_write(f.led+12,b'\1')
  before=[0x1010+i for i in range(13)];before[0]=f.m;before[3]=0x27
  for reg,val in zip(REGS,before):f.u.reg_write(reg,val)
  sp=0x20030000;f.u.reg_write(UC_ARM_REG_SP,sp);f.u.reg_write(UC_ARM_REG_LR,0x0813f2fd)
  f.u.emu_start(0x0813c319,0,count=30000)
  self.assertEqual([f.u.reg_read(r) for r in REGS],before)
  self.assertEqual(f.u.reg_read(UC_ARM_REG_SP),sp)
  self.assertEqual(f.u.reg_read(UC_ARM_REG_APSR)&0xf0000000,0x60000000)
  self.assertEqual(f.flags(),[0]*16)

if __name__=='__main__':unittest.main(verbosity=2)
