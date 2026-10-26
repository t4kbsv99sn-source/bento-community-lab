"""CH3 melodic Euclidean rows: real native note containers, IDs, bulk edits and
the real M7 renderer/note emitter. Model lookups and transport remain fixtures."""
import unittest,struct,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_editable_eu import Edit
from test_euclidean import EU
from test_integration import UU,AA
KEEP=[]
PITCHED=18 # multisampler-type owner
def pnote(step,pitch,ident,vel=90,length=960,lock=0):
 return struct.pack('<BBHIIIHHI',1,0,0,step*960,length,ident,pitch,vel,lock)
class Mel(Edit):
 def __init__(self,notes=None):
  super().__init__(notes=notes if notes is not None else [pnote(1,62,101)]);KEEP.append(self)
 def native(self,u,a,n,d):
  if a==0x08133f7c:self.ret(PITCHED if self.r(u.reg_read(UC_ARM_REG_R1))==self.owner else 24);return
  super().native(u,a,n,d)
 def melodic(self,pitch,gate=4,row=0):
  for off,v in [(0,self.seq),(4,self.owner),(8,row),(12,self.steps),(16,0),(20,0),(24,100),(28,0x10000|(gate<<8)|pitch),(36,1)]:self.w(EU+off,v)
  assert self.call(UU['live_begin'],EU)
  assert self.call(UU['live_assign_pitch'],EU,pitch)
 def pitched(self,pitch):return [e for e in self.events() if struct.unpack_from('<H',e,16)[0]==pitch]
 def at(self,pitch):return [struct.unpack_from('<I',e,4)[0]//960 for e in self.pitched(pitch)]
 def on_times(self):return [round(a/6000) for (pad,a),pk in zip(self.absolute,[q for q in self.emitted]) if pk[0]==0x12]
 def notes_on(self):return [(struct.unpack_from('<I',p,12)[0],struct.unpack_from('<I',p,4)[0],struct.unpack_from('<I',p,16)[0]) for p in self.emitted if p[0]==0x12]
class Tests(unittest.TestCase):
 def test_generation_writes_real_pitched_notes_with_gate_and_keeps_other_pitches(self):
  p=Mel();p.melodic(60,gate=8);other=p.pitched(62)
  self.assertEqual(p.generate(1,8),1);self.assertEqual(p.generate(2,3),1)
  self.assertEqual(p.at(60),[0, 3, 6, 8, 11, 14]) # P19: the 8-step row repeats across the 16-step clip
  for e in p.pitched(60):
   self.assertEqual(struct.unpack_from('<H',e,2)[0],0);self.assertEqual(struct.unpack_from('<I',e,8)[0],1920)
  self.assertEqual(p.pitched(62),other);self.assertEqual(len(p.undo),1) # Length with no hits changes no notes
 def test_playback_sends_pitch_and_registers_native_note_off_at_gate_length(self):
  p=Mel(notes=[]);p.melodic(60,gate=8);p.generate(1,8);p.generate(2,3);p.sync()
  p.render(0);on=p.notes_on();self.assertEqual(len(on),1);self.assertEqual(on[0][0],60)
  table=p.audioseq;self.assertEqual(p.r(table+0x238),1)
  self.assertEqual(p.u.mem_read(table+0x38,1)[0],1);self.assertEqual(p.r(table+0x3c),60);self.assertEqual(struct.unpack('<H',p.u.mem_read(table+0x3a,2))[0],0)
  end=struct.unpack('<q',p.u.mem_read(table+0x40,8))[0];self.assertEqual(end,2*240) # two sixteenths in native clock ticks
  for start in range(1024,8*6000,1024):p.render(start,min(1024,8*6000-start))
  self.assertEqual(p.on_times(),[0,3,6]);self.assertEqual([n for n,t,v in p.notes_on()],[60,60,60])
 def test_independent_melodic_cycle_steps_and_velocity_from_real_notes(self):
  p=Mel(notes=[]);p.melodic(60);p.generate(1,5);p.generate(2,2);p.sync()
  for start in range(0,10*6000,1024):p.render(start,min(1024,10*6000-start))
  self.assertEqual(p.on_times(),[i for i in range(10) if (i%5*2)%5<2])
 def test_melodic_rows_repeat_over_multiple_clip_wraps(self):
  p=Mel(notes=[]);p.melodic(60);p.generate(1,7);p.generate(2,3);p.sync()
  for start in range(0,48*6000,1024):
   p.w(p.clip+0x20,(start//96000)*3840)
   p.render(start,min(1024,48*6000-start))
  self.assertEqual(p.on_times(),[i for i in range(48) if ((i%7)*3)%7<3])
 def test_installed_native_renderer_repeats_rows_and_handles_note_offs(self):
  p=Mel(notes=[]);p.melodic(60);p.generate(1,7);p.generate(2,3);p.sync()
  for start in range(0,48*6000,1024):
   p.block=start;p.w(p.clock,start);p.w(p.clip+0x20,(start//96000)*3840)
   p.call(0x08060820,p.audioseq,p.clock,0,min(1024,48*6000-start),p.router)
  # P19: the native renderer plays the tiled row (fixture cursor: one clip pass).
  self.assertEqual(p.on_times(),[i for i in range(16) if (i%7*3)%7<3])
  self.assertLessEqual(p.r(p.audioseq+0x238),1)
 def test_free_snap_mode_uses_native_unscaled_time_and_repeats(self):
  # P17 (owner on P16: only the first notes played). Without step-relative timing
  # (clip +38 clear) notes are absolute ticks: the UI writes a 1/16 step as 240
  # (preview unit bits = Step Len 10 + 1) and M7 steps at the Step Len.
  p=Mel(notes=[]);p.melodic(60);p.w(EU+28,p.r(EU+28)|11<<20);p.generate(1,4);p.generate(2,2);p.sync()
  self.assertEqual(sorted(struct.unpack_from('<I',e,4)[0] for e in p.pitched(60)),[0,480])
  p.u.mem_write(p.clip+0x38,b'\0');p.w(p.clip,0) # P18: absolute clips keep no grid in clip +0
  for start in range(0,12*6000,1024):p.render(start,min(1024,12*6000-start))
  self.assertEqual(p.on_times(),[0,2,4,6,8,10])
 def test_rewound_transport_restarts_melodic_rows(self):
  p=Mel(notes=[]);p.melodic(60);p.generate(1,4);p.generate(2,2);p.sync()
  for start in range(0,4*6000,1024):p.render(start,min(1024,4*6000-start))
  before=len(p.notes_on());p.render(0)
  self.assertEqual(len(p.notes_on()),before+1)
 def test_retrigger_of_held_pitch_sends_native_note_off_first(self):
  p=Mel(notes=[]);p.melodic(60,gate=32);p.generate(1,4);p.generate(2,4);p.sync()
  for start in range(0,2*6000,1024):p.render(start,min(1024,2*6000-start))
  kinds=[(pk[0],struct.unpack_from('<I',pk,12)[0]) for pk in p.emitted if pk[0] in (0x12,0x13)]
  self.assertEqual(kinds,[(0x12,60),(0x13,60),(0x12,60)]);self.assertEqual(p.r(p.audioseq+0x238),1)
 def test_native_events_suppressed_by_pitch_only(self):
  # P9 (owner): rows are real clip notes again (CH3); M7 plays a row's own
  # notes on the row cycle, so the native player skips that pitch only.
  p=Mel(notes=[]);p.melodic(60);p.generate(1,8);p.generate(2,3);p.sync();p.render(0)
  self.assertEqual(p.call(AA['live_skip'],p.audioseq,0,60),1);self.assertEqual(p.call(AA['live_skip'],p.audioseq,0,61),0)
 def test_repitch_moves_row_notes_in_one_undo_and_refuses_occupied_pitch(self):
  p=Mel();p.melodic(60);p.generate(1,8);p.generate(2,3);undo=len(p.undo)
  self.assertEqual(p.call(UU['eu_repitch'],EU,p.model,64),0);self.assertEqual(p.at(64),[0, 3, 6, 8, 11, 14]);self.assertEqual(p.at(60),[])
  self.assertEqual(len(p.undo),undo+1)
  p.w(EU+28,0x10000|(4<<8)|64);self.assertEqual(p.call(UU['eu_repitch'],EU,p.model,62),6) # EU_USED: manual note at 62
  self.assertEqual(p.at(64),[0, 3, 6, 8, 11, 14])
 def test_gate_edit_updates_existing_row_notes(self):
  p=Mel();p.melodic(60);p.generate(1,8);p.generate(2,3)
  self.assertEqual(p.call(UU['live_set_gate'],EU,2),1);p.w(EU+28,0x10000|(2<<8)|60)
  self.assertEqual(p.call(UU['eu_gate_notes'],EU,p.model),0)
  self.assertEqual({struct.unpack_from('<I',e,8)[0] for e in p.pitched(60)},{480})
 def test_xml_roundtrip_keeps_pitch_and_gate_for_pitched_track(self):
  p=Mel();p.melodic(67,gate=6,row=3);p.generate(1,8);p.generate(2,3);p.call(UU['live_set_gate'],EU,6)
  obj=0x20024000;p.u.mem_write(obj+4,bytes([PITCHED]));p.w(obj+0x10,p.owner)
  p.call(UU['live_save'],obj,0x20017000);self.assertEqual(p.attrs['bento_eu2_00_03_4'],67);self.assertEqual(p.attrs['bento_eu2_00_03_5'],6)
  p.call(UU['live_finish']);p.call(UU['live_load'],0x20025000,obj);p.call(UU['live_finish'])
  out=0x20026000;self.assertEqual(p.call(UU['live_row_pitch'],EU,3,out),1);self.assertEqual(p.r(out),67)
 def test_rows_write_editable_clip_notes_and_play_them(self):
  # P9: generation writes native notes at the row pitch; an edited note's
  # velocity is what plays.
  p=Mel(notes=[]);p.melodic(60,gate=8)
  for k,v in [(1,8),(2,3)]:self.assertEqual(p.call(UU['live_generate'],EU,k,v),1)
  self.assertEqual(p.at(60),[0, 3, 6, 8, 11, 14]);p.sync()
  # P19 (owner video: M7 melodic playback was silent on hardware): the row's notes
  # are ordinary clip notes; M7 neither plays nor suppresses them.
  for start in range(0,8*6000,1024):p.render(start,min(1024,8*6000-start))
  self.assertEqual(p.on_times(),[]);self.assertEqual(p.call(AA['live_skip'],p.audioseq,0,60),0)
 def test_drum_track_records_unchanged_and_not_melodic(self):
  p=Edit();p.generated();bank=p.r(0x24041fc0+4);rec=bank+32
  self.assertEqual(p.r(rec+12),0);self.assertEqual([p.r(rec+16+i*4) for i in range(4)],[0,0,0,0])
# P19: melodic rows no longer run on the M7 Euclid clock (silent on hardware);
# these M7-only melodic playback checks are retired, drum rows keep theirs (test_live).
for _n in ['test_playback_sends_pitch_and_registers_native_note_off_at_gate_length','test_independent_melodic_cycle_steps_and_velocity_from_real_notes','test_melodic_rows_repeat_over_multiple_clip_wraps','test_free_snap_mode_uses_native_unscaled_time_and_repeats','test_rewound_transport_restarts_melodic_rows','test_retrigger_of_held_pitch_sends_native_note_off_first','test_native_events_suppressed_by_pitch_only']:delattr(Tests,_n)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
