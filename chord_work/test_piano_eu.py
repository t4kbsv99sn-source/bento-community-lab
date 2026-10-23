"""CH3 piano-roll Euclid bank through the actual piano view constructor, native
header builder 081599BC (patched entry), native encoder slot configuration and
the patched piano event entry. Model lookup/undo/engine queue are fixtures."""
import struct,unittest,gc
from test_native_piano import Piano
from test_integration import UU
import test_eu9 as header_fixture
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
KEEP=[]
KEYS=[0x190,0x18d,0x191,0x192,0x193,0x18f,0x194,0x195]
TITLES=['Row','Note','Length','Hits','Rotate','Gate','Vel Mode','Vel Depth']
class PianoEu(Piano):
 def __init__(self):
  super().__init__();KEEP.append(self);self.call(0x081599bc,self.view)
 def event(self,code,key=0,value=0):
  e=0x2002e000;self.u.mem_write(e,struct.pack('<5I',code,0,key,value&0xffffffff,0));return self.call(UU['piano_event'],self.view,e)
 def keys(self):return list(struct.unpack('<8H',self.u.mem_read(self.view+0x11bcc0,16)))
 def values(self):return list(struct.unpack('<8I',self.u.mem_read(self.view+0x11bcd0,32)))
 def slot(self,i):return self.view+0x55f0+0x38+i*0x468
 def pitch(self,p):return sorted(struct.unpack_from('<I',e,4)[0]//960 for e in self.events() if struct.unpack_from('<H',e,16)[0]==p)
class Tests(unittest.TestCase):
 def test_native_piano_keys_are_untouched_until_euclid_is_enabled(self):
  p=PianoEu();native=(p.keys(),p.values());p.call(0x081599bc,p.view);self.assertEqual((p.keys(),p.values()),native)
  p.event(0x1054);self.assertEqual(p.keys(),KEYS);p.event(0x1054);self.assertEqual((p.keys(),p.values()),native)
 def record(self,p):
  bank=p.r(0x24041fc0+4);rec=bank+32;return rec
 def pad(self,p,row):rec=self.record(p);return p.r(rec+32+row*8),p.r(rec+32+row*8+4)
 def test_header_action_toggles_euclid_bank_on_native_encoder_slots(self):
  p=PianoEu();self.assertEqual(p.event(0x1054),1);self.assertEqual(p.keys(),KEYS)
  for i,t in enumerate(TITLES):self.assertEqual(p.text(p.slot(i)+0x3c8+0x31),t)
  self.assertEqual(p.values()[:3],[1,49,16]) # owner: default C3 = MIDI 48 (Bento naming)
 def test_hits_start_a_c3_row_on_top_of_clip_without_writing_notes(self):
  p=PianoEu();before=p.events();p.event(0x1054);self.assertEqual(p.event(0xcf,0x192,4),1)
  self.assertEqual(p.events(),before);rec=self.record(p)
  self.assertEqual(p.r(rec+12)&1,1);self.assertEqual(p.r(rec+16)&0xff,48)
  pattern,vel=self.pad(p,0);self.assertEqual((pattern>>8)&511,4);self.assertEqual((pattern>>25)&1,1);self.assertEqual((pattern>>26)&1,0)
  self.assertEqual(p.values()[1:4],[49,16,4])
  p.event(0xcf,0x191,7);self.assertEqual(self.pad(p,0)[0]&255,6);self.assertEqual(p.events(),before)
 def test_four_rows_maximum(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x190,9);self.assertEqual(p.values()[0],4)
 def test_second_row_is_independent_and_refuses_duplicate_pitch(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x192,2)
  p.event(0xcf,0x190,2);p.event(0xcf,0x18d,49);self.assertEqual(p.values()[1],49) # shows C3 default but not assigned
  self.assertEqual(p.r(self.record(p)+16)>>8&0xff,0)
  p.event(0xcf,0x18d,68);p.event(0xcf,0x191,5);p.event(0xcf,0x192,3)
  self.assertEqual(p.r(self.record(p)+16)>>8&0xff,67);self.assertEqual((self.pad(p,1)[0]>>8)&511,3)
 def test_gate_is_stored_on_the_row_and_clip_notes_untouched(self):
  p=PianoEu();before=p.events();p.event(0x1054);p.event(0xcf,0x192,2);p.event(0xcf,0x18f,2)
  self.assertEqual((self.pad(p,0)[1]>>24)&63,2);self.assertEqual(p.events(),before)
 def test_euclid_button_removed_from_piano_roll_header(self):
  # CH8 (owner): hidden for now; the native header stays unchanged.
  p=PianoEu();out=header_fixture.Tests().header_data(p,page=0x17);p.call(UU['seq_toolbar'],p.model,out,0)
  self.assertNotIn('Euclid',[p.text(out+0x74+i*48) for i in range(6)])
 def test_drum_track_gets_no_euclid_header_or_bank(self):
  p=PianoEu();p.type=14;self.assertEqual(p.event(0x1054),0)
  out=header_fixture.Tests().header_data(p,page=0x17);p.call(UU['seq_toolbar'],p.model,out,0)
  self.assertNotIn('Euclid',[p.text(out+0x74+i*48) for i in range(6)])
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
