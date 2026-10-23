"""K6 reproduces the provider address and distinct file/sound IDs from the device."""
import unittest,struct
from unicorn.arm_const import *
from test_kick import Kick
from test_kick_install import Install
from kick_build import SYMS
class Tests(unittest.TestCase):
 def alias(self,p):
  p.u.mem_map(0x10040000,0x10000)
  p.u.mem_write(0x100455e0,bytes(p.u.mem_read(p.provider,4)))
  p.provider=0x100455e0;p.w(p.desc,p.provider)
 def test_captured_provider_alias_is_recognised_and_generates_native_processed_audio(self):
  p=Kick();p.native_postprocess();self.alias(p)
  p.u.mem_map(0xc5a20000,0x10000);old=p.root;p.root=0xc5a2afa0
  p.u.mem_write(p.root,bytes(p.u.mem_read(old,0x800)));p.w(p.root+12,0x13e)
  p.u.mem_write(0x24040158,bytes(p.u.mem_read(p.desc,0x2c)));p.desc=0x24040158;p.w(p.voice+12,p.desc)
  ui=Install();ui.u.mem_write(0x2001d000,b'BENTO_Kick_K2.wav\0')
  ui.call('kick_sample_loading',0x2001b000,0x13f,0x2001d000,1)
  p.u.mem_write(0x24043500,bytes(ui.u.mem_read(0x24043500,0x820)))
  p.start()
  for _ in range(8):self.assertEqual(p.render()[0],1)
  self.assertGreater(max(abs(v) for channel in p.outputs() for v in channel),.001)
  self.assertGreater(p.reads,0)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24043e00+25*4,4))[0],0x100455e0)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24043e00+31*4,4))[0],0x13e)
 def test_provider_alias_does_not_bypass_marker_content_checks(self):
  p=Kick(False);self.alias(p);p.start();self.assertEqual(p.render()[0],0)
  self.assertGreater(p.reads,0);self.assertEqual(p.post,[])
 def test_end_of_verified_alias_region_remains_rejected(self):
  p=Kick();p.w(p.desc,0x10050000);p.start();self.assertEqual(p.render()[0],0)
  self.assertEqual(p.reads,0);self.assertEqual(p.post,[])
if __name__=='__main__':unittest.main(verbosity=2)
