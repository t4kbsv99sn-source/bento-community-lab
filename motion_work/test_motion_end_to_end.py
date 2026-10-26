"""M4 capture -> shared snapshot -> real M7 A-D -> real native modulation sum.
Model/DOM/route configuration on M4 are fixtures, not physical hardware input.
"""
import struct,unittest
import test_native_producer as producer
M4=producer.Probe
from test_native_audio import Probe as M7,CLIP,SEQ
class Tests(unittest.TestCase):
 def replay(self,depth,value):
  m=M4();m.routes[(66,3,0)]=(9,depth);m.base_values[(66,3)]=0;assert m.begin();m.clock(240)
  assert producer.Tests().parameter(m,value)==1;m.clock(3*3840);m.api('motion_ui_end');clip=m.r(m.device()+32)
  audio=M7();audio.u.mem_write(CLIP,bytes(m.u.mem_read(clip,4224)))
  audio.tick(240)
  base=0x20020000;param=base+32
  audio.u.mem_write(base,struct.pack('<If',0,0.0))
  words=bytearray(64);struct.pack_into('<IfIf',words,0,base,1.0,SEQ+0x871c,depth/1000)
  words[0x28:0x2a]=bytes([0,1]);struct.pack_into('<Iff',words,0x30,2,-1.0,1.0)
  audio.u.mem_write(param,bytes(words));audio.call(0x080d1f00,param)
  return audio.f(param+0x3c),m,audio
 def test_normal_parameter_movement_replays_through_native_modulation(self):
  value,m,a=self.replay(1000,500);self.assertAlmostEqual(value,0.5,places=5)
  self.assertEqual(m.base_values[(66,3)],0)
 def test_shallow_existing_depth_keeps_its_value_and_replays_full_gesture(self):
  value,m,a=self.replay(82,500);self.assertLess(abs(value-0.5),0.002)
  self.assertEqual(m.routes[(66,3,0)],(9,82))
 def test_recording_release_holds_value_after_three_bars_until_16_bar_boundary(self):
  value,m,a=self.replay(1000,500)
  for bars in [3,4,8,15]:
   a.w(SEQ+0x240+0x20,(bars//2)*2*3840)
   self.assertAlmostEqual(a.tick(bars*3840)[0],0.5,places=5)
  self.assertAlmostEqual(a.tick(16*3840)[0],0.0,places=5)
if __name__=='__main__':unittest.main(argv=[__file__,'-v'])
