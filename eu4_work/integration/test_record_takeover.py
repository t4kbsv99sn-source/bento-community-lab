"""CH7 recording takes over a Euclid pad (owner choice). Real generator, native
note IDs/containers and the patched check; recorded notes are added through the
same native add path the step view uses (project next-ID counter advances)."""
import unittest,struct,gc
from test_editable_eu import Edit
from test_live import UU,EC,note
KEEP=[]
class Rec(Edit):
 def __init__(self):
  super().__init__(notes=[note(1,pad=0,ident=50)]);KEEP.append(self);self.generated(7,3)
  self.call(UU['live_record_check']) # remember the current note-ID counter
 def record(self,pad,tick):
  temp=0xc00e0000;handle=0x2002c000;raw=0x2002c100;self.w(handle,self.seq)
  self.call(0x0810d16c,temp);self.u.mem_write(raw,struct.pack('<6I',1|(pad<<16),tick,480,0,100<<16,0))
  self.call(0x081338dc,self.model,handle);ident=self.call(0x0812e070,self.project,self.seq,raw);self.w(raw+12,ident)
  self.call(0x0810d176,temp,raw);self.call(0x08136544,self.model,handle,temp)
 def enabled(self,pad):bank=self.r(EC+4);return (self.r(bank+32+32+pad*8)>>25)&1
 def check(self):return self.call(UU['live_record_check'])
class Tests(unittest.TestCase):
 def test_nothing_changed_nothing_done(self):
  p=Rec();self.assertEqual(p.check(),0);self.assertEqual(p.enabled(p.pad),1)
 def test_recorded_off_pattern_hit_switches_pad_to_manual_and_keeps_notes(self):
  p=Rec();before=len(p.events());p.record(p.pad,960*1) # step 1 is not one of E(3,7)'s hits 0,2,4
  self.assertEqual(p.check(),1<<p.pad);self.assertEqual(p.enabled(p.pad),0);self.assertEqual(len(p.events()),before+1)
 def test_unquantised_hit_counts_even_on_a_pattern_step(self):
  p=Rec();p.record(p.pad,130);self.assertEqual(p.check(),1<<p.pad)
 def test_quantised_hit_on_a_pattern_step_or_other_pad_keeps_euclid(self):
  p=Rec();p.record(p.pad,0);self.assertEqual(p.check(),0);self.assertEqual(p.enabled(p.pad),1)
  p.record(5,960*3);self.assertEqual(p.check(),0);self.assertEqual(p.enabled(p.pad),1) # pad 5 has no generator
 def test_regeneration_itself_is_not_a_recording(self):
  p=Rec();self.assertTrue(p.generate(2,4));p.prepare();p.sync();self.assertEqual(p.check(),0);self.assertEqual(p.enabled(p.pad),1)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
