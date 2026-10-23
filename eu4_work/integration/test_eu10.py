"""Engine-specific p-lock target filtering; note data must stay lossless."""
import unittest,struct,gc
from test_eu9 import Native
import test_eu8
from test_live import UU
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
KEEP=[]
class Targets(Native):
 def __init__(self,engine):
  self.engine=engine;super().__init__();KEEP.append(self)
 def no_synth(self,*args):self.ret(self.engine)
 def names(self):
  reg=self.r(0x30031484);d=reg+0x1da*32;n=self.r(d+12);a=self.r(d+8);return [self.text(self.r(a+4*i)) for i in range(n)]
class Tests(unittest.TestCase):
 def view(self,engine):
  p=Targets(engine);test_eu8.Tests().full_view(p);p.select(0);p.call(0x0815c27c,p.seqview);return p
 def test_all_synths_hide_sample_adsr_but_keep_sends_and_their_own_parameters(self):
  for engine,first,total in [(1,'Kick Tune',16),(3,'Snare Tune',13),(5,'HiHat Tune',13)]:
   p=self.view(engine);names=p.names();self.assertEqual(len(names),total);self.assertEqual(names[6:9],['Delay Send','Reverb Send',first]);self.assertFalse({'Attack','Decay','Sustain','Release'}&set(names));self.assertEqual(p.names()[:6],['Remove lock','Level','Pitch','Pan','Filter','Resonance'])
 def test_sample_keeps_unchanged_native_targets(self):
  p=self.view(0);self.assertEqual(p.names(),['Remove lock','Level','Pitch','Pan','Filter','Resonance','Attack','Decay','Sustain','Release','Delay Send','Reverb Send'])
 def test_synth_picker_first_and_last_targets_encode_correct_kinds(self):
  for engine,first,last,idx in [(1,12,19,15),(3,20,24,12),(5,25,29,12)]:
   p=self.view(engine)
   for pick,kind,key in [(8,first,0x1a0),(idx,last,0x1b0 if engine==1 else 0x1a5)]:
    p.call(UU['locks_proj'],p.model,1);p.call(UU['locks_encoder'],p.seqview,0x1da,pick);p.call(UU['locks_proj'],p.model,0);p.call(UU['locks_encoder'],p.seqview,key,80)
    w=struct.unpack_from('<I',p.events()[0],20)[0];slot=p.call(UU['locks_slot'],w,0);self.assertEqual(slot>>16&255,kind)
 def test_reduced_picker_maps_both_sends_without_touching_sample_adsr(self):
  for engine in [1,3,5]:
   for pick,kind,key in [(6,10,0x36),(7,11,0x37)]:
    p=self.view(engine);p.call(UU['locks_proj'],p.model,1);p.call(UU['locks_encoder'],p.seqview,0x1da,pick);p.call(UU['locks_proj'],p.model,0);p.call(UU['locks_encoder'],p.seqview,key,350)
    w=struct.unpack_from('<I',p.events()[0],20)[0];slot=p.call(UU['locks_slot'],w,0);self.assertEqual(slot>>16&255,kind)
 def test_switching_to_sample_restores_adsr_and_hides_all_synth_targets(self):
  p=self.view(3);p.engine=0;p.call(0x0815c27c,p.seqview);self.assertIn('Attack',p.names());self.assertFalse(any('Snare' in n for n in p.names()))
 def test_existing_adsr_lock_is_preserved_in_notes_and_xml_but_not_exposed_as_synth_encoder(self):
  p=self.view(0);p.call(UU['locks_encoder'],p.seqview,0x1e,350) # default is Level; write a legacy saved lock directly.
  e=bytearray(p.events()[0]);struct.pack_into('<I',e,20,0x5106015e);raw=0x2002e000;p.u.mem_write(raw,bytes(e));p.call(0x0810d1aa,p.container,raw)
  # Fixture uses the actual native temporary/note mutation path, as other tests.
  p.engine=3;before=p.events();p.call(0x0815c27c,p.seqview);self.assertEqual(p.events(),before)
  self.assertNotIn(0x1e,struct.unpack('<2H',p.u.mem_read(p.seqview+0x113b8,4)))
  p.call(UU['locks_save'],0x20017000,raw);self.assertEqual(p.attrs['bento_lock1_v1'],0x5106015e)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
