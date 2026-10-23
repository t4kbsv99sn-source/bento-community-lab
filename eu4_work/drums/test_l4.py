"""L4 private native ABI, shift transport, grid feedback and added voice targets.
Native code executes in Unicorn; screen drawing and audio hardware remain device checks.
"""
import unittest,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_controls import Fixture,REGS
from test_editable_locks import VoiceProbe,UIProbe,word as oldword
from step_locks import A_SYMS,U_SYMS

def word(k,v):return oldword(k,v) if k<4 else 0x51000000|(k<<16)|(v+1000 if k==4 else v)
def flt(u,r):return struct.unpack('<f',struct.pack('<I',u.reg_read(r)))[0]

class Tests(unittest.TestCase):
 def test_new_evaluator_preserves_native_private_r12_and_s1_to_s12(self):
  for w in [word(3,-1000),word(3,1000),word(1,-18000)]:
   p=VoiceProbe();p.voice_start(w)
   for param in [p.voice+0x1c0,p.voice+0x180,p.root+0x178]:
    p.u.reg_write(UC_ARM_REG_R12,0x12345678)
    for i in range(1,13):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*1000)
    p.evaluate(param)
    self.assertEqual(p.u.reg_read(UC_ARM_REG_R12),0x12345678)
    for i in range(1,13):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*1000)
 def test_native_stereo_gain_paths_match_original_pan_with_identical_level(self):
  for start,end in [(0x08094c46,0x08094cb6),(0x08093dc2,0x08093e22)]:
   for value in [-1000,-750,-500,-250,0,250,500,750,1000]:
    results=[]
    for locked in [False,True]:
     p=VoiceProbe();p.f(p.root+0x12c,0 if locked else value/1000)
     p.base_source(p.root+0x178,p.root+0x128);p.voice_start(word(3,value) if locked else 0)
     gains=[]
     def setter(u,a,s,d):
      if a==0x08071220:
       gains.append((u.reg_read(UC_ARM_REG_R0)-p.voice,flt(u,UC_ARM_REG_S0),flt(u,UC_ARM_REG_S1)))
       u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
     p.u.hook_add(UC_HOOK_CODE,setter)
     p.u.reg_write(UC_ARM_REG_R0,p.voice+0x1c0);p.u.reg_write(UC_ARM_REG_S16,0)
     p.fragment(start,end);results.append(gains)
    self.assertEqual(results[0],results[1],(start,value))
    self.assertEqual([x[0] for x in results[1]],[0xcc,0x94,0xa4])
    self.assertTrue(all(0<=x[1]<=1 for x in results[1]))
 def test_project_play_cycles_native_pages_and_consumes_transport_release(self):
  f=Fixture()
  for expected in [13,26,25,13]:
   f.event(175,7);f.event(175,15);f.event(176,7);f.event(176,15)
   self.assertEqual(f.page(),expected)
  self.assertEqual(f.log,[('button',7)]*4)
 def test_project_plain_taps_have_no_navigation(self):
  f=Fixture()
  for i in range(3):f.event(175,7);f.event(176,7)
  self.assertEqual(f.log,[]);self.assertEqual(f.page(),23)
 def test_clear_shortcut_preserves_transport_and_both_release_orders(self):
  for proj_first in [True,False]:
   f=Fixture();f.event(175,7);f.event(175,14)
   if proj_first:f.event(176,7);f.event(176,14)
   else:f.event(176,14);f.event(176,7)
   self.assertEqual(f.log,[]);self.assertEqual(f.page(),23)
 def test_direct_clear_removes_selected_locks_and_keeps_native_hit_data(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.time(6500);p.release(0)
  p.press(8);p.encoder(2,-9000);native=bytes(p.u.mem_read(p.container+24,20))
  p.call(U_SYMS['locks_clear'],p.page)
  self.assertEqual(p.stored(1),0);self.assertEqual(p.stored(),word(1,-18000))
  self.assertEqual(bytes(p.u.mem_read(p.container+24,20)),native)
  p.time(6600);p.release(8);self.assertNotIn(('toggle',8),p.log)
 def test_grid_marker_only_matches_current_drum_existing_locks_and_scroll(self):
  p=UIProbe();p.w(p.container+20,word(3,-500));p.w(p.container+48+20,word(3,500))
  p.call(U_SYMS['locks_grid'],p.view)
  titles=[v for t,v,*_ in p.screen if t=='title']
  self.assertEqual(titles[:3],['1*','2','3']);self.assertNotIn('9*',titles)
  p.screen=[];p.w(p.view+0x113f4,8);p.w(p.container+24+20,word(3,500))
  p.call(U_SYMS['locks_grid'],p.view)
  self.assertEqual(p.screen[0],('title','9*'))
 def test_native_playhead_and_text_selection_are_independent(self):
  p=UIProbe();p.w(p.view+0x11408,0xffffffff)
  def playhead():
   return [i for i in range(32) if p.u.mem_read(p.view+0x34+i*0x704+0xec,1)==b'\0']
  p.call(0x0815bde2,p.view,3);self.assertEqual(playhead(),[3])
  p.press(0);p.press(8);p.call(U_SYMS['locks_grid'],p.view)
  self.assertIn(('title','[1]'),p.screen);self.assertIn(('title','[9]'),p.screen)
  self.assertEqual(playhead(),[3]);self.assertEqual(p.word(p.view+0x11408),3)
  p.call(0x0815bde2,p.view,4);self.assertEqual(playhead(),[4])
  p.time(6500);p.release(0);p.release(8);p.screen=[];p.call(U_SYMS['locks_grid'],p.view)
  self.assertIn(('title','[9]'),p.screen);self.assertNotIn(('title','[1]'),p.screen)
  self.assertEqual(playhead(),[4])
 def test_new_targets_use_native_property_ids_ranges_and_note_storage(self):
  for k,key,value in [(4,0x32,-750),(5,0x33,600),(6,0x1e,250),(7,0x1f,800),(8,0x20,350),(9,0x21,400)]:
   p=UIProbe();p.shift();p.encoder(0x1da,k);p.shift(False);p.press(0);p.encoder(key,value)
   self.assertEqual(p.stored(),word(k,value));p.display();self.assertIn(('value',key,value),p.screen)
 def test_native_voice_copy_and_evaluator_support_filter_resonance_attack_decay_release(self):
  for k,root_offset,voice_offset,value in [(4,0x340,0x388,-500),(5,0x388,0x3d0,400),(6,0x3e8,0x430,250),(7,0x428,0x470,700),(9,0x468,0x4b0,350)]:
   p=VoiceProbe();src=0x20014000;p.f(src+4,.1)
   p.init_parameter(p.root+root_offset);p.base_source(p.root+root_offset,src)
   p.f(p.root+root_offset+0x34,-1 if k==4 else 0);p.f(p.root+root_offset+0x38,1)
   p.call(0x08092f20,p.root,p.voice)
   self.assertEqual(bytes(p.u.mem_read(p.root+root_offset,64)),bytes(p.u.mem_read(p.voice+voice_offset,64)))
   p.payload(word(k,value));p.call(A_SYMS['lock_voice'],p.voice,p.root)
   self.assertAlmostEqual(p.evaluate(p.voice+voice_offset),value/1000,places=6)
   p.payload(0);p.call(A_SYMS['lock_voice'],p.voice,p.root)
   self.assertAlmostEqual(p.evaluate(p.voice+voice_offset),.1,places=6)
 def test_sustain_is_voice_owned_and_restores_on_unlocked_reuse(self):
  p=VoiceProbe();p.f(p.root+0x3e0,.8);p.voice_start(word(8,250))
  self.assertAlmostEqual(p.f(p.voice+0x428),.25)
  p.f(p.root+0x3e0,.6);p.voice_start(word(8,900),p.voice+0x800)
  self.assertAlmostEqual(p.f(p.voice+0x428),.25)
  p.voice_start(0);self.assertAlmostEqual(p.f(p.voice+0x428),.6)

 def test_different_steps_can_lock_different_targets_in_same_drum(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.time(6500);p.release(0)
  p.press(8);p.shift();p.encoder(0x1da,4);p.shift(False);p.encoder(0x32,-500)
  self.assertEqual(p.stored(),word(1,-18000));self.assertEqual(p.stored(1),word(4,-500))
  p.time(6600);p.release(8);p.press(0);p.display();self.assertIn(('title','Lock Level'),p.screen)
 def test_new_lock_targets_round_trip_native_xml_adapters(self):
  for k,value in [(4,-750),(5,600),(6,250),(7,800),(8,350),(9,400)]:
   p=UIProbe();p.w(p.container+20,word(k,value));p.call(U_SYMS['locks_save'],0x20027000,p.container)
   p.w(p.container+20,0);p.call(U_SYMS['locks_load'],0x20027000,p.container)
   self.assertEqual(p.stored(),word(k,value))
 def test_native_envelope_constructor_and_attack_trigger_use_lock(self):
  lengths=[]
  for value in [0,250,500]:
   p=VoiceProbe();p.call(0x080638c0,p.root+0x3c8)
   p.f(p.root+0x3cc,.1);p.f(p.root+0x3e0,.8)
   def lfo_clock_stub(u,a,s,d):
    if a==0x08064ac0:u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   p.u.hook_add(UC_HOOK_CODE,lfo_clock_stub)
   p.call(0x08072a00,p.voice);p.call(0x08092f20,p.root,p.voice)
   p.payload(word(6,value));p.call(A_SYMS['lock_voice'],p.voice,p.root)
   p.call(0x080639a0,p.voice+0x58)
   lengths.append(struct.unpack('<I',p.u.mem_read(p.voice+0x68,4))[0])
  self.assertEqual(lengths[0],0);self.assertLess(lengths[1],lengths[2]);self.assertEqual(lengths[2],54000)

if __name__=='__main__':unittest.main(verbosity=2)
