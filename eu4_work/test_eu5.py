"""EU5 generated native-cell states, M7 display phase and extended hat lifetime."""
import unittest,struct,sys,gc
from test_controls_e3 import Seq,UU
from test_kick import Kick,FRAMES
from kick_build import SYMS
# Keep native callback owners alive until process exit, including Kick probes
# whose C-side callbacks can otherwise be destroyed between test methods.
_KEEP=[]
_OriginalKick=Kick
class Kick(_OriginalKick):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);_KEEP.append(self)
_OriginalSeq=Seq
class Seq(_OriginalSeq):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);_KEEP.append(self)
class Tests(unittest.TestCase):
 def setup_grid(self,n=7,k=3,rot=0):
  p=Seq();p.tab() # CH5: Euclidean view tab
  for key,value in [(0x191,n),(0x192,k),(0x193,rot)]:p.encoder(key,value)
  p.call(UU['seq_eu_grid'],p.view,1);return p
 def cells(self,p,field):return [p.word(p.view+0x34+i*0x704+field) if field==0x6f0 else p.u.mem_read(p.view+0x34+i*0x704+field,1)[0] for i in range(32)]
 def phase(self,p,step,valid=1):
  bank=p.word(0x24041fc4);r=bank+32+2*128*160
  for off,value in [(0,0xc0080000),(4,2),(8,p.word(bank)),(12,1),(36,80),(44,step),(48,valid),(52,2)]:p.w(r+off,value)
  return r
 def test_length_visibility_and_generated_hits_match_audio_rule(self):
  p=self.setup_grid(7,3,2);self.assertEqual(self.cells(p,0x30),[0]*7+[1]*25)
  self.assertEqual(self.cells(p,0x6ed),[int(i<7 and (((i+7-2)%7)*3)%7<3) for i in range(32)])
  self.assertEqual(self.cells(p,0x6f0)[:7],list(range(1,8)))
 def test_playhead_comes_from_generator_not_native_clip_event(self):
  p=self.setup_grid();self.phase(p,9);p.call(0x0815bde2,p.view,5)
  self.assertEqual(self.cells(p,0xec),[1,1,0]+[1]*29)
 def test_long_cycle_pages_follow_head_and_hide_trailing_boxes(self):
  p=self.setup_grid(35,9);self.phase(p,34);p.call(UU['seq_eu_grid'],p.view,0)
  self.assertEqual(self.cells(p,0x30),[0]*3+[1]*29)
  self.assertEqual(self.cells(p,0x6f0)[:3],[33,34,35]);self.assertEqual(self.cells(p,0xec)[2],0)
 def test_stop_clears_highlight_and_length_edits_do_not_change_native_notes(self):
  p=self.setup_grid(7,3);before=bytes(p.u.mem_read(p.container,72));self.phase(p,3,0);p.call(UU['seq_eu_grid'],p.view,1)
  self.assertEqual(self.cells(p,0xec),[1]*32);self.assertEqual(p.word(p.view+0x113f8),7)
  self.assertEqual(bytes(p.u.mem_read(p.container,72)),before)
 def test_m4_tick_refreshes_playhead_without_encoder_event(self):
  p=self.setup_grid();self.phase(p,5);p.call(UU['seq_lights_clean'],p.page)
  self.assertEqual(self.cells(p,0xec)[5],0)
 def test_left_normal_edit_bank_keeps_generated_notes_and_cycle_length(self):
  p=self.setup_grid(7,3);before=bytes(p.u.mem_read(p.container,0x3004));p.leave()
  p.call(UU['seq_eu_grid'],p.view,1)
  self.assertEqual(p.bank(),0);self.assertEqual(p.word(p.view+0x113f8),7)
  self.assertEqual(self.cells(p,0x30),[0]*7+[1]*25)
  self.assertEqual(bytes(p.u.mem_read(p.container,0x3004)),before)
 def test_native_hold_selects_generated_hit_and_right_returns_generator_bank(self):
  p=self.setup_grid(7,3);p.press(3);ok,event=p.snapshot();self.assertEqual(ok,1)
  self.assertEqual(struct.unpack_from('<I',event,4)[0],3*960)
  p.time(6500);p.release(3);p.call(UU['seq_eu_header'],p.view)
  self.assertNotEqual(struct.unpack('<H',p.u.mem_read(p.view+0x113ac,2))[0],0x190)
  p.tab();p.call(UU["seq_eu_header"],p.view)
  self.assertEqual(struct.unpack('<H',p.u.mem_read(p.view+0x113ac,2))[0],0x190)
 def test_normal_bank_preserves_native_playhead_and_restores_cells(self):
  p=Seq();p.call(0x0815bde2,p.view,5);self.assertEqual(p.word(p.view+0x11408),5)
 def test_hat_native_carrier_stays_alive_after_three_seconds(self):
  p=Kick();p.w(p.desc+0x24,FRAMES+4);p.w(0x24046000,0x374c5042);p.w(0x24046008,p.root);p.w(0x2404600c,0x511a0064);p.start()
  slot=0x24042000+16
  self.assertEqual(struct.unpack('<I',p.u.mem_read(slot+24,4))[0],48000*8)
  p.w(slot+24,48000*4);p.render();self.assertLess(struct.unpack('<I',p.u.mem_read(p.voice+0x40,4))[0],FRAMES+4)
  self.assertNotEqual(bytes(p.u.mem_read(p.voice,1)),b'\0')
 def test_closed_hat_retains_previous_voice_lifetime(self):
  p=Kick();p.w(p.desc+0x24,FRAMES+4);p.start()
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24042000+16+24,4))[0],FRAMES+4)
if __name__=='__main__':
 gc.disable() # Keep Unicorn callback cycles alive through the suite.
 unittest.main(verbosity=2)
