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
def tiled(n,k,rot=0,clip=16):return [s for s in range(clip) if ((((s%n)+n-rot)%n)*k)%n<k] # P19: a row repeats across the clip
KEYS=[0x190,0x18d,0x191,0x192,0x193,0x18f,0x194,0x195]
TITLES=['Row','Note','Length','Hits','Rotate','Gate','Vel Mode','Vel Depth']
class PianoEu(Piano):
 def __init__(self,snap=1,grid=10):
  super().__init__();KEEP.append(self);self.snap=snap;self.grid=grid
  # Fixture: Step Len (60) and step-relative timing (61, clip +38) as the native header reads them.
  def prop(u,a,n,d):
   k=u.reg_read(UC_ARM_REG_R2)
   if k in (0x60,0x61):self.w(u.reg_read(UC_ARM_REG_R3),self.grid if k==0x60 else self.snap);self.ret(1)
  self.u.hook_add(UC_HOOK_CODE,prop,begin=0x0812dca2,end=0x0812dca2)
  self.call(0x081599bc,self.view)
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
 def test_hits_write_real_c3_notes_from_the_start(self):
  # P9 (owner): Euclid steps are real clip notes, selectable and editable.
  p=PianoEu();p.event(0x1054);self.assertEqual(p.event(0xcf,0x192,4),1)
  self.assertEqual(p.pitch(48),[0,4,8,12]);rec=self.record(p)
  self.assertEqual(p.r(rec+12)&1,1);self.assertEqual(p.r(rec+16)&0xff,48)
  pattern,vel=self.pad(p,0);self.assertEqual((pattern>>8)&511,4);self.assertEqual((pattern>>25)&1,1);self.assertEqual((pattern>>26)&1,1)
  self.assertEqual(p.values()[1:4],[49,16,4])
  p.event(0xcf,0x191,7);self.assertEqual(self.pad(p,0)[0]&255,6);self.assertEqual(p.pitch(48),tiled(7,4))
  p.event(0xcf,0x193,1);self.assertEqual(p.pitch(48),tiled(7,4,1))
 def test_absolute_tick_clip_places_hits_on_steps_not_quarters(self):
  # P17 (owner on P16: only the first notes played). Without step-relative timing
  # the clip holds absolute ticks (960 per quarter), so a 1/16 step is 240.
  p=PianoEu(snap=0,grid=10);p.event(0x1054);p.event(0xcf,0x192,4)
  starts=sorted(struct.unpack_from('<I',e,4)[0] for e in p.events() if struct.unpack_from('<H',e,16)[0]==48)
  self.assertEqual(starts,[0,960,1920,2880]);self.assertEqual({struct.unpack_from('<I',e,8)[0] for e in p.events()},{240})
 def test_four_rows_maximum(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x190,9);self.assertEqual(p.values()[0],4)
 def test_second_row_is_independent_and_refuses_duplicate_pitch(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x192,2)
  p.event(0xcf,0x190,2);p.event(0xcf,0x18d,49);self.assertEqual(p.values()[1],49) # shows C3 default but not assigned
  self.assertEqual(p.r(self.record(p)+16)>>8&0xff,0)
  p.event(0xcf,0x18d,68);p.event(0xcf,0x191,5);p.event(0xcf,0x192,3)
  self.assertEqual(p.r(self.record(p)+16)>>8&0xff,67);self.assertEqual((self.pad(p,1)[0]>>8)&511,3)
  self.assertEqual(p.pitch(67),tiled(5,3));self.assertEqual(len(p.pitch(48)),2) # row 1 keeps its own notes
  p.event(0xcf,0x18d,49);self.assertEqual(p.pitch(67),tiled(5,3)) # C3 belongs to row 1: refused
 def test_gate_is_stored_on_the_row_and_sets_note_lengths(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x192,2);p.event(0xcf,0x18f,8)
  self.assertEqual((self.pad(p,0)[1]>>24)&63,8)
  lens={struct.unpack_from('<I',e,8)[0] for e in p.events() if struct.unpack_from('<H',e,16)[0]==48}
  self.assertEqual(len(lens),1)
 def test_note_change_moves_the_row_notes(self):
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x192,4);p.event(0xcf,0x18d,61)
  self.assertEqual(p.pitch(48),[]);self.assertEqual(p.pitch(60),[0,4,8,12])
 def test_euclidean_tab_on_the_piano_roll_header(self):
  p=PianoEu();out=header_fixture.Tests().header_data(p,page=0x17);p.call(UU['seq_toolbar'],p.model,out,0)
  self.assertEqual(p.text(out+0x74+48),'Euclid');self.assertEqual(p.u.mem_read(out+0x74+48+0x22,1)[0],1) # P20: native tab again
  self.assertEqual(struct.unpack('<H',p.u.mem_read(out+0x74+48+44,2))[0],0x1061)
  p.event(0x1054);p.call(UU['seq_toolbar'],p.model,out,0);self.assertEqual(p.u.mem_read(out+0x74+48+0x21,1)[0],1)
  self.assertEqual([p.u.mem_read(out+0x74+i*48+0x21,1)[0] for i in [0,2,3]],[0,0,0])
 def test_native_tab_leaves_euclid(self):
  p=PianoEu();native=(p.keys(),p.values());p.event(0x1054);self.assertEqual(p.keys(),KEYS)
  self.assertEqual(p.event(0x4a),0);self.assertNotEqual(p.keys(),KEYS)
 def test_drum_track_gets_no_euclid_header_or_bank(self):
  p=PianoEu();p.type=14;self.assertEqual(p.event(0x1054),0)
  out=header_fixture.Tests().header_data(p,page=0x17);p.call(UU['seq_toolbar'],p.model,out,0)
  self.assertNotIn('Euclid',[p.text(out+0x74+i*48) for i in range(6)])
 def f9(self,p):
  for m in range(20):
   b=0x30030168+m*0xe0
   if p.r(b)==0xf9:return [(p.r(b+4+k*20),p.text(p.r(b+8+k*20)) if p.r(b+8+k*20) else '') for k in range(p.u.mem_read(b+0xcc,1)[0])]
 def test_burger_menu_offers_euclidean_on_the_pitched_piano_roll(self):
  p=PianoEu();p.call(0x081412ec);out=header_fixture.Tests().header_data(p,page=0x17)
  p.call(UU['seq_toolbar'],p.model,out,0);menu=self.f9(p)
  self.assertEqual(len(menu),7);self.assertIn((0x1059,'Automation'),menu);self.assertIn((0x1070,'Motion Settings'),menu)
  self.assertFalse({0x1062,0x1063,0x1064}&{c[0] for c in menu}) # P17: only in the Performance burger
  self.assertNotIn(0x1032,[c[0] for c in menu]);self.assertNotIn(0x1054,[c[0] for c in menu])
 def test_drum_piano_view_keeps_select_in_the_burger_menu(self):
  p=PianoEu();p.type=14;p.call(0x081412ec);out=header_fixture.Tests().header_data(p,page=0x17)
  p.call(UU['seq_toolbar'],p.model,out,0);self.assertIn((0x1051,'Select'),self.f9(p))
 def test_pad_press_on_an_empty_row_shows_the_note_before_any_hits(self):
  # P22 (owner on P21: the Note showed Off until hits were inserted).
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x190,2)
  fn=UU['chord_pad_pitch']&~1;p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:p.ret(62),begin=fn,end=fn)
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',0xb0,0,3,0,0));p.call(0x0815b548,p.view,e)
  self.assertEqual(p.values()[1],63);self.assertEqual(p.text(p.slot(1)+0x2c8),'D4') # MIDI 62, Bento naming; not "Off"
 def test_pad_press_in_euclid_sets_the_row_pitch_not_a_chord(self):
  # P21 (owner on P20: a pad in Euclid inserted a chord).
  p=PianoEu();p.event(0x1054);p.event(0xcf,0x192,4);before=len(p.events())
  fn=UU['chord_pad_pitch']&~1;p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:p.ret(62),begin=fn,end=fn)
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',0xb0,0,3,0,0));p.call(0x0815b548,p.view,e)
  self.assertEqual(p.values()[1],63);self.assertEqual(p.pitch(48),[]);self.assertEqual(len(p.pitch(62)),4);self.assertEqual(len(p.events()),before)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
