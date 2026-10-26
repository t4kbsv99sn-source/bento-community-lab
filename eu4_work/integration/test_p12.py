"""Device-report regressions: final native header apply, track palette,
queued transport (beyond the scan-site fixture), performance octave routing.
Physical LTDC, transport hardware and SD remain device checks."""
import unittest,struct,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE
from test_mod import Page as SynthPage,V,TRACK
from test_perf import Page as PerfPage,M,LOCK
ROOT=0x30034d48;OUT=0x20032000
KEEP=[]
class Tests(unittest.TestCase):
 def test_mod_buttons_reach_final_native_apply_without_view_tick(self):
  for kind in (18,19):
   p=SynthPage(kind);KEEP.append(p);p.u.mem_write(M+0x12c,b'\x09');p.call(0x08180198,ROOT)
   t=IMAGE[0x8199008+10*0x1c4-0x8040000:][:0x1c4];p.u.mem_write(OUT,t)
   p.call(0x0817faf8,ROOT,OUT)
   for slot,label,key in ((4,'MOD',0x1057),(5,'MATRIX',0x1058)):
    b=ROOT+0x54c+slot*0xd0
    self.assertEqual(p.u.mem_read(b+0x30,1),b'\0')
    self.assertEqual(p.r(b+0x14),key)
    self.assertEqual(p.text(OUT+0x74+slot*48),label)
   # Late native page reset must restore buttons, even with no view callback.
   p.u.mem_write(OUT,t);p.u.mem_write(ROOT+0x117c,b'\0');p.call(0x0817faf8,ROOT,OUT)
   self.assertEqual(p.u.mem_read(ROOT+0x54c+5*0xd0+0x30,1),b'\0')
 def test_polyphonic_euclid_uses_visible_slot_and_no_view_precondition(self):
  for kind in (15,18,19,22):
   p=SynthPage(kind);KEEP.append(p);p.u.mem_write(M+0x12c,b'\x17');p.call(0x08180198,ROOT)
   t=IMAGE[0x8199008+8*0x1c4-0x8040000:][:0x1c4];p.u.mem_write(OUT,t);p.call(0x0817faf8,ROOT,OUT)
   self.assertEqual([p.text(OUT+0x74+i*48) for i in range(6)],['Chord','Euclid','Step','Seq','Select','Clear'])
   for i in range(4):self.assertEqual(p.u.mem_read(ROOT+0xa2c+i*0xd0+0x30,1)[0],0) # P20: native tabs again
 def test_transport_queue_blocks_both_shift_sources_but_plain_play_survives(self):
  p=Fixture();KEEP.append(p);record=0x20030000;producer=0x20031000;posts=[]
  def native(u,a,n,d):posts.append(bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))[0]);p.ret(1)
  p.u.hook_add(UC_HOOK_CODE,native,begin=0x08059980,end=0x08059980)
  p.w(0x2401bd3c,producer)
  # P24 (owner): with the motion layer, shifted RECORD (0x91) is dropped too; plain RECORD still passes.
  import os;from pathlib import Path as _P;shifted_record=not (_P(os.environ['BENTO_FX_CANDIDATE'])/'MOTION_MANIFEST.json').exists()
  for ui,raw,code,want in ((0,0,0x8f,True),(0,0x100,0x8f,False),(1,0,0x8f,False),(1,0x100,0x91,shifted_record),(0,0,0x91,True),(0,0,0x8f,True)):
   p.w(LOCK+8,ui);p.u.mem_write(producer+0x2338,struct.pack('<H',raw));p.u.mem_write(record,bytes([code])+bytes(23));posts.clear();p.call(0x08058600,0x20020000,record)
   self.assertEqual(bool(posts),want,(ui,raw,code))
 def test_performance_arrows_change_native_octave_and_consume_releases(self):
  p=PerfPage();KEEP.append(p);p.open();p.header();octave=[0]
  p.button(0xaf,1);self.assertEqual(p.model_events[-1][2:],(0x178,1));self.assertEqual(p.button(0xb0,1),1)
  p.button(0xaf,8);self.assertEqual(p.model_events[-1][2:],(0x178,0));self.assertEqual(p.button(0xb0,8),1)
 def test_analog_waveform_draws_with_native_track_colour(self):
  from test_analog_ui import UI
  p=UI();KEEP.append(p);p.u.mem_map(0xc0400000,0x40000);p.menu(0x1052);p.call(0x0815e228,V)
  pane=V+0x3550;ctx=0x20033000;p.u.mem_write(pane+4,struct.pack('<4i',0,0,300,100));p.u.mem_write(ctx,struct.pack('<II',1,0x20034000));colours=[]
  def draw(u,a,n,d):
   if a==0x08166ef6:colours.append(u.reg_read(UC_ARM_REG_R1))
   p.ret()
  p.u.hook_add(UC_HOOK_CODE,draw,begin=0x08166ef6,end=0x08166ef6)
  p.u.hook_add(UC_HOOK_CODE,draw,begin=0x08182314,end=0x08182314)
  p.call(UU['analog_wave_paint'],pane,ctx)
  expected=p.call(0x08140ebc,3) # UI fixture's native current-track index
  self.assertGreater(colours.count(expected),200);self.assertNotIn(0xf2,colours)
 def test_palette_is_native_track_mapping(self):
  p=Fixture();KEEP.append(p)
  got=[p.call(0x08140ebc,i) for i in range(8)]
  self.assertEqual(set(got),set(range(0xf7,0xff)))
  # The source drawing must call this native function, rather than pane-grey.
  self.assertIn('analog_wave_tick',UU)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
