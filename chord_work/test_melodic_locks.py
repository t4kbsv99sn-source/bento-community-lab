"""P14 real native note selection, encoder widgets, Undo and lock payloads.
Audio checks run the new guarded ARM paths with real native filter parameters.
Device timing and hardware playback remain outside these fixtures.
"""
import unittest,struct,gc,json,os
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_device import Device
from test_integration import UU,AA,Fixture
KEEP=[]
EV=0x2002e000
class Page(Device):
 def __init__(self):
  super().__init__();KEEP.append(self);self.insert();self.call(0x0815abb8,self.view,0,0)
  self.u.mem_write(self.view+0x125dac,b'\0');self.call(0x081599bc,self.view)
  self.select_ids([self.ids()[0]])
 def ids(self):return [struct.unpack_from('<I',e,12)[0] for e in self.events()]
 def select_ids(self,ids):
  self.call(0x08174bac,self.view+0x38,0)
  for ident in ids:self.call(0x08174c4e,self.view+0x38,ident,0)
  self.call(0x081599bc,self.view)
 def event(self,key,value):
  self.u.mem_write(EV,struct.pack('<5I',0xcf,0,key,value&0xffffffff,0));return self.call(UU['piano_event'],self.view,EV)
 def shift(self,down):return self.call(UU['locks_proj'],self.model,down)
 def keys(self):return list(struct.unpack('<8H',self.u.mem_read(self.view+0x11bcc0,16)))
 def word(self,i=0):return struct.unpack_from('<I',self.events()[i],20)[0]
 def slot(self,i):return self.view+0x55f0+0x38+i*0x468
 def title(self,i):return self.text(self.slot(i)+0x3c8+0x31)
 def label(self,i):return self.text(self.slot(i)+0x2c8)
class Audio(Fixture):
 def hook(self,u,a,n,d):
  super().hook(u,a,n,d)
  if a==0x08104c08:self.w(0x3000004c,self.next)
 def __init__(self):
  super().__init__();KEEP.append(self);self.u.mem_map(0,0x1000);self.owner=80;self.root=0xc00a0000;self.voice=0xc00b0000;self.other=0xc00b1000;self.record=0x20026000
  self.w(0x3000004c,self.next);self.w(0x30000048,0xc0200000);self.call(UU['mel_audio_prepare'],self.owner);self.bank=self.r(0x24041fc4);self.state=self.r(self.bank+16)
  self.w(self.root,0x080ac798);self.w(self.root+12,101)
  for v in [self.voice,self.other]:self.call(0x0807f3c0,v)
 def pack(self,a,b=0):return self.call(UU['locks_pack'],a,b)
 def note(self,word,voice=None):
  self.u.mem_write(self.record,struct.pack('<BBH5I',0x12,0xb8,0x4d4c,0,101,60,100,word))
  self.call(AA['mel_note'],self.root,self.record);self.call(AA['mel_attach'],self.root,voice or self.voice)
 def context(self,voice=None):self.call(AA['mel_context'],self.root,voice or self.voice)
 def evaluate(self,offset=0x5c4,voice=None):
  ptr=(voice or self.voice)+offset;self.call(0x0809fd80,ptr);return struct.unpack('<f',self.u.mem_read(ptr+0x3c,4))[0]
 def gain(self,values):
  buf=0x20027000;data=0x20028000;self.w(buf,len(values));self.w(buf+4,len(values));self.w(buf+8,data);self.w(buf+12,0x20029000);self.u.mem_write(buf+16,b'\0\0')
  self.u.mem_write(data,struct.pack('<%df'%len(values),*values));self.call(AA['mel_level'],self.voice,buf)
  return struct.unpack('<%df'%len(values),self.u.mem_read(data,4*len(values)))
class Tests(unittest.TestCase):
 def test_event_encoders_7_and_8_are_locks_and_native_first_six_stay(self):
  p=Page();self.assertEqual(p.keys(),[0x17e,0x181,0x185,0x182,0x183,0x184,0x32,0x33]);self.assertIn('Filter',p.title(6));self.assertIn('Resonance',p.title(7))
 def test_two_locks_are_note_owned_and_keep_ids_pitches_and_other_notes(self):
  p=Page();before=p.events();undo=len(p.undo);p.event(0x32,500);p.event(0x33,750)
  self.assertEqual(p.call(UU['locks_slot'],p.word(),0),0x510405dc);self.assertEqual(p.call(UU['locks_slot'],p.word(),1),0x510502ee)
  self.assertEqual(p.events()[0][:20],before[0][:20]);self.assertEqual(p.events()[1:],before[1:]);self.assertEqual(len(p.undo),undo+2);self.assertTrue(p.title(6).endswith('*'))
 def test_native_multi_selection_locks_only_selected_chord_tones(self):
  p=Page();p.select_ids(p.ids()[:2]);p.event(0x32,350);self.assertTrue(p.word(0));self.assertTrue(p.word(1));self.assertEqual(p.word(2),0)
 def test_proj_picker_and_remove_one_lock_preserve_the_other(self):
  p=Page();p.event(0x32,500);p.event(0x33,700);p.shift(1);self.assertEqual(p.keys()[6:],[0x1da,0x1e4]);p.event(0x1da,0);p.shift(0)
  self.assertEqual(p.call(UU['locks_slot'],p.word(),0),0);self.assertEqual(p.call(UU['locks_slot'],p.word(),1),0x510502bc)
 def test_picker_targets_level_and_pan_and_keeps_base_values(self):
  p=Page();p.shift(1);p.event(0x1da,1);p.event(0x1e4,2);p.shift(0);self.assertEqual(p.keys()[6:],[2,4]);p.event(2,-6000);p.event(4,-500)
  self.assertEqual(p.call(UU['locks_slot'],p.word(),0),0x51010384);self.assertEqual(p.call(UU['locks_slot'],p.word(),1),0x510301f4)
 def test_no_note_selection_does_not_mutate_and_has_clear_prompt(self):
  p=Page();p.select_ids([]);before=p.events();p.event(0x32,500);self.assertEqual(p.events(),before);self.assertEqual(p.label(6),'Select note')
 def test_sequence_and_euclidean_banks_keep_their_encoders(self):
  p=Page();p.u.mem_write(p.view+0x125dac,b'\x01');p.call(0x081599bc,p.view);self.assertNotEqual(p.keys()[6:], [0x32,0x33])
  p.u.mem_write(EV,struct.pack('<5I',0x1054,0,0,0,0));p.call(UU['piano_event'],p.view,EV);self.assertEqual(p.keys()[6:],[0x194,0x195])
 def test_saved_lock_payload_roundtrip_is_exact(self):
  p=Page();p.event(0x32,620);p.event(0x33,420);word=p.word();p.u.mem_write(EV,p.events()[0]);p.call(UU['locks_save'],0x20017000,EV);p.w(EV+20,0);p.call(UU['locks_load'],0x20017000,EV);self.assertEqual(p.r(EV+20),word)
 def test_burger_moves_automation_toggle_without_losing_actions(self):
  p=Page();p.call(0x081412ec);p.call(UU['melodic_locks_menu'],1)
  menus=[]
  for m in range(20):
   d=0x30030168+m*0xe0
   if p.r(d)==0xf9:
    n=p.u.mem_read(d+0xcc,1)[0];ids=[p.r(d+4+i*20) for i in range(n)];self.assertIn(0x1059,ids);self.assertIn(0x1032,ids);self.assertLessEqual(n,9);menus.append(d)
  self.assertTrue(menus);p.call(UU['melodic_locks_menu'],0)
  for d in menus:self.assertNotIn(0x1059,[p.r(d+4+i*20) for i in range(p.u.mem_read(d+0xcc,1)[0])])
 def test_per_voice_filter_and_resonance_run_native_evaluator(self):
  p=Audio();p.note(p.pack(0x510405dc,0x510502ee));p.context();self.assertAlmostEqual(p.evaluate(),.5,places=5);self.assertAlmostEqual(p.evaluate(0x60c),.75,places=5)
 def test_overlapping_voice_has_independent_values_and_unlocked_reuse_clears(self):
  p=Audio();p.note(0x510405dc);p.note(0x510406a4,p.other);p.context();self.assertAlmostEqual(p.evaluate(),.5,places=5)
  p.context(p.other);self.assertAlmostEqual(p.evaluate(voice=p.other),.7,places=5)
  p.note(0);p.context();self.assertNotEqual(p.evaluate(),.5)
 def test_level_scales_audio_without_changing_velocity_or_other_voice(self):
  p=Audio();p.note(0x51010384);p.context();out=p.gain([1.,-.5,.25,0.]);self.assertAlmostEqual(out[0],10**(-6/20),places=5);self.assertAlmostEqual(out[1],-.5*out[0],places=6)
  p.note(0,p.other);p.context(p.other);self.assertEqual(p.gain([1.,.5]),(1.,.5))
 def test_pan_is_native_voice_local(self):
  p=Audio();p.note(0x510301f4);self.assertAlmostEqual(struct.unpack('<f',p.u.mem_read(p.voice+0x18,4))[0],.25);self.assertNotEqual(p.u.mem_read(p.voice+0x18,4),p.u.mem_read(p.other+0x18,4))
 def test_queue_payload_is_only_written_to_the_primary_destination(self):
  p=Audio();seq=0xc00c0000;router=0xc00d0000;queue=0xc00e0000
  p.w(seq+12,p.owner);p.u.mem_write(seq+0x10,struct.pack('<H',101));p.w(seq+0x86dc,0xffffff00)
  p.w(router+4,queue);p.w(router+8,101);p.w(router+12,0);p.w(router+0x508,1)
  word=p.pack(0x510405dc,0x510502ee);p.call(AA['mel_pending'],seq,router,0,word)
  for q,expected in [(queue+0x604,0),(queue,word)]:
   p.u.mem_write(p.record,struct.pack('<6I',0x12,0,101,60,100,0));p.call(AA['mel_queue'],q,p.record);self.assertEqual(p.r(p.record+20),expected)
  p.call(AA['mel_pending_clear']);p.u.mem_write(p.record,struct.pack('<6I',0x12,0,101,60,100,0));p.call(AA['mel_queue'],queue,p.record);self.assertEqual(p.r(p.record+20),0)
 def test_physical_encoder_path_edits_the_selected_note(self):
  p=Page();p.call(0x08171e44,p.slot(6),(-12800)&0xffffffff)
  self.assertEqual(p.call(UU['locks_slot'],p.word(),0)>>16&255,4)
 def test_automation_burger_action_opens_native_automation_editor(self):
  p=Page();p.w(EV,0x1059);p.call(UU['piano_event'],p.view,EV);self.assertEqual(p.u.mem_read(p.view+0x125dac,1)[0],2)
 def test_installed_native_wavetable_note_entry_attaches_filter_lock(self):
  p=Audio();p.call(0x0809bf20,p.root);p.w(p.root+12,101)
  p.u.mem_write(p.record,struct.pack('<BBH5I',0x12,0xb8,0x4d4c,0,101,60,100,0x510405dc))
  router=0x20029000;clock=0x2002a000;p.w(router,clock);p.f(clock+0x18,120);p.f(clock+0x14c,.5);p.u.reg_write(UC_ARM_REG_S1,0x3f000000)
  p.call(0x0807ebe0,p.root,p.record,router,fp=0.0);voice=p.r(p.root+0x14)
  p.call(AA['mel_context'],p.root,voice);self.assertAlmostEqual(p.evaluate(voice=voice),.5,places=5)
 def test_locked_note_edits_are_kept_when_selecting_another_note(self):
  p=Page();p.event(0x32,500);old=p.word();p.select_ids([p.ids()[1]]);p.event(0x33,700)
  self.assertEqual(p.word(0),old);self.assertNotEqual(p.word(1),0);self.assertEqual(p.word(2),0)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
