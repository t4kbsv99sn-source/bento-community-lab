"""Run original mixer LED palette, state builder and changed-color queue writer."""
import unittest,struct
from test_controls import REGS
from test_native_mixer import NativeMixer
from unicorn.arm_const import *
class NativeLights(NativeMixer):
 def __init__(self):
  super().__init__();self.kind=0x16 # A populated native track; no sample-loading dependencies.
  self.u.mem_write(self.m+0x19c4+0x140,b'\x0e') # Native 08125730 constructor default brightness
 def hook(self,u,a,size,data):
  if a in [0x0813bc24,0x081257f0,0x0810b5c8]:return
  if a==0x08133cfc:
   out=u.reg_read(UC_ARM_REG_R1);self.w(out,80);self.ret(1);return
  super().hook(u,a,size,data)
 def drain(self):self.w(self.engine+0x600,self.r(self.engine+0x620))
 def colors(self):return [self.r(self.m+0x19c4+i*16) for i in range(16)]
 def pending(self):
  first=self.r(self.engine+0x600);last=self.r(self.engine+0x620)
  return [bytes(self.u.mem_read(self.engine+24*(i&63),24)) for i in range(first,last)]
class Tests(unittest.TestCase):
 def test_enter_hold_builds_the_native_unsoloed_unmuted_palette(self):
  f=NativeLights();f.event(175,5)
  self.assertEqual(f.colors(),[0x162f2f]*16)
  self.assertEqual(f.u.mem_read(f.m+0x3c7c,1),b'\1')
  self.assertEqual(len([r for r in f.pending() if r[0]==0xb4]),16)
 def test_solo_and_mute_lights_update_while_button_stays_held(self):
  for track in range(8):
   for action,pad,color in [(5,track,0x00ff00),(6,track+8,0xff0000)]:
    f=NativeLights();f.event(175,5);f.drain();f.pad(action,track)
    self.assertEqual(f.colors()[pad],color)
    colors=[r for r in f.pending() if r[0]==0xb4]
    self.assertEqual(len(colors),1)
    self.assertEqual(struct.unpack_from('<I',colors[0],8)[0],16+pad)
    self.assertNotEqual(struct.unpack_from('<I',colors[0],12)[0],0)
    f.drain();f.pad(action,track)
    self.assertEqual(f.colors()[pad],0x162f2f)
 def test_existing_mute_and_solo_appear_immediately_on_hold(self):
  f=NativeLights();f.props[(f.obj+2*0x100,0x13e)]=1;f.props[(f.obj+6*0x100,0x13d)]=1
  f.event(175,5);self.assertEqual(f.colors()[2],0x00ff00);self.assertEqual(f.colors()[14],0xff0000)
 def test_release_returns_previous_mode_and_keeps_audio_property(self):
  f=NativeLights();f.event(175,5);f.drain();f.pad(6,2);f.drain();f.event(176,5)
  self.assertEqual(f.page(),23);self.assertEqual(f.u.mem_read(f.m+0x3c7c,1),b'\0')
  self.assertEqual(f.value(2,0x13d),1)
 def test_plain_tap_preserves_native_mixer_screen_mode(self):
  f=NativeLights();f.event(175,5)
  # Native UI renderer captured an already-enabled Solo/Mute screen.
  f.w(0x24048d20,0x35554942);f.w(0x24048d24,1)
  f.w(0x24048d28,f.r(0x24048cc0+44));f.w(0x24048d2c,1)
  f.drain();f.event(176,5)
  self.assertEqual(f.page(),31);self.assertEqual(f.u.mem_read(f.m+0x3c7c,1),b'\1')
if __name__=='__main__':unittest.main(verbosity=2)
