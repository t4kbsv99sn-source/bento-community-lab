"""K16 real compiled ARM paths; native audio postprocessor; model I/O fixtures."""
import unittest,struct,random
from unicorn.arm_const import *
from test_kick import Kick,FRAMES
from test_kick_ui import UI,KEYS
from test_editable_locks import UIProbe
from test_l7 import SendProbe,pair as legacy_pair
from step_locks import U_SYMS,A_SYMS
from kick_build import SYMS as DSP
N=[1,1081,48001,2001,2001]+[1001]*7+[156]+[101]*17

def word(k,v):return 0x51000000|(k<<16)|(v-25 if k==12 else v)
def pair(a,b):
 ka=(a>>16)&255 if a else 0;kb=(b>>16)&255 if b else 0
 if ka and ka==kb:return 0xffffffff
 if not kb:return a
 code=0
 for extra in [False,True]:
  for i in range(30):
   for j in range(30):
    if (i>11 or j>11)!=extra or i and i==j:continue
    if (i,j)==(ka,kb):return 0x80000000+code+(a&65535)*N[j]+(b&65535)
    code+=N[i]*N[j]
 raise AssertionError()
class SynthUI(UIProbe):
 def __init__(self,model=3):
  self.engine=model;self.path={1:'BENTO_Kick_K2.wav',3:'BENTO_Synth_Snare.wav',5:'BENTO_Synth_HiHat.wav',0:'normal.wav'}[model]
  super().__init__()
 def extra(self,u,a,s,d):
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x0813391a:
   if r[2]<2:self.w(r[3],101+r[2]);self.ret(1)
   else:self.ret(0)
  elif a==0x08133f7c:
   self.ret(14 if r[1]==self.view+0x113e8 else 5 if self.word(r[1])==102 else 1)
  elif a==0x0813390e:u.mem_write(r[3],self.path.encode()+b'\0');self.ret(1)
  else:super().extra(u,a,s,d)
class NativeWidgetUI(UI):
 def native(self,u,a,s,d):
  if a in [0x08171c1c,0x08170656]:return
  if a==0x08171640:self.ret();return # substitute drawing, retain native configuration/text storage
  if a==0x08104c08:self.ret(0x20020000);return
  super().native(u,a,s,d)
class Tests(unittest.TestCase):
 def test_actual_native_widget_configuration_and_override_are_restored(self):
  p=NativeWidgetUI();p.u.reg_write(UC_ARM_REG_R0,0);p.u.reg_write(UC_ARM_REG_SP,0x20030000);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x081639a9,0x081ff200,count=200000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x081ff200)
  p.path='BENTO_Synth_Snare.wav';p.prepare();slot=p.v+0x38+0x38+0x468
  self.assertEqual(p.text(slot+0x2c8),'200 Hz')
  p.path='normal.wav';p.call('kick_ui_before',p.v)
  self.assertEqual(p.text(slot+0x2c8),'')
  self.assertEqual(struct.unpack('<H',p.u.mem_read(slot+0x9c,2))[0],2)
  self.assertIn(('title',slot+0x3c8,'Level'),p.calls)

 def test_synth_to_sample_forces_native_rebind_and_clears_every_text_override(self):
  for name in ['BENTO_Kick_K2.wav','BENTO_Synth_Snare.wav','BENTO_Synth_HiHat.wav']:
   p=UI();p.path=name;p.prepare();p.event(KEYS[2],77);p.calls=[];p.path='normal.wav';p.call('kick_ui_before',p.v)
   for row in range(3):
    for i in range(8):
     bar=p.v+0x38+row*0x23f8
     self.assertIn(('value',bar,i,''),p.calls)
     self.assertIn(('widget',bar+0x38+i*0x468,row*8+i+1,0,1),p.calls)
   before=len(p.calls);p.call('kick_ui_after',p.v);self.assertEqual(len(p.calls),before)
 def test_real_native_note_initialization_sets_normalized_velocity_source(self):
  p=Kick();sp=0x2003e000
  for velocity in [1,32,64,100,127]:
   p.w(sp+0x60,velocity);p.w(sp+8,60);p.f(sp+0xc,1)
   p.u.reg_write(UC_ARM_REG_R4,p.voice);p.u.reg_write(UC_ARM_REG_SP,sp)
   p.u.emu_start(0x08094bbf,0x08094be8,count=50)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x08094be8)
   self.assertAlmostEqual(p.f(p.voice+0xb8),velocity/127,places=6)
 def test_velocity_scales_output_only_for_all_engines(self):
  for engine in [1,3,5]:
   outputs=[]
   for vel in [1,.5,0]:
    p=Kick();p.w(p.desc+0x24,FRAMES+engine-1);p.f(p.voice+0xb8,vel);p.start();a=[]
    for _ in range(4):a.extend(p.render()[1])
    outputs.append(a)
   self.assertGreater(max(map(abs,outputs[0])),.001)
   self.assertLess(max(abs(x*.5-y) for x,y in zip(outputs[0],outputs[1])),1e-7)
   self.assertEqual(max(map(abs,outputs[2])),0)
 def test_velocity_survives_native_postprocessing_without_changing_timbre(self):
  outputs=[]
  for vel in [1,.25]:
   p=Kick();p.native_postprocess();p.f(p.voice+0xb8,vel);p.start();p.render();outputs.append(p.outputs()[0])
  self.assertLess(max(abs(x*.25-y) for x,y in zip(*outputs)),1e-7)
 def test_all_new_ordered_pairs_match_reference_and_roundtrip(self):
  p=UIProbe()
  for a in range(30):
   for b in range(30):
    if a and a==b or a<12 and b<12:continue
    x=0x51000000|(a<<16)|(N[a]-1) if a else 0;y=0x51000000|(b<<16)|(N[b]-1) if b else 0
    packed=pair(x,y);p.call(U_SYMS['locks_pack'],x,y);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),packed)
    for i,w in enumerate([x,y]):p.call(U_SYMS['locks_slot'],packed,i);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),w)
 def test_model_specific_picker_and_two_edits_roundtrip_clear(self):
  for model,first,total in [(1,12,20),(3,20,17),(5,25,17)]:
   p=SynthUI(model);p.press(0);p.shift();self.assertEqual(p.word(0x20029000+0x1da*32+12),total)
   p.encoder(0x1da,12);p.shift(False);p.encoder(KEYS[0],80)
   p.shift();p.encoder(0x1e4,13);p.shift(False);p.encoder(KEYS[1],90)
   expected=pair(word(first,80),word(first+1,90));self.assertEqual(p.stored(),expected)
   p.call(U_SYMS['locks_save'],0x20027000,p.container);p.w(p.container+20,0);p.call(U_SYMS['locks_load'],0x20027000,p.container);self.assertEqual(p.stored(),expected)
   p.call(U_SYMS['locks_clear'],p.page);self.assertEqual(p.stored(),0)
 def test_replacing_synth_does_not_leave_duplicate_encoder_targets(self):
  p=SynthUI(3);p.press(0);p.shift();p.encoder(0x1da,12);p.encoder(0x1e4,1);p.shift(False)
  p.encoder(KEYS[0],80);p.path='normal.wav';p.prepare()
  self.assertEqual(struct.unpack('<2H',p.u.mem_read(0x300000bc+8,4)),(2,0x32))
 def test_normal_sample_picker_has_only_original_targets(self):
  p=SynthUI(0);p.shift();self.assertEqual(p.word(0x20029000+0x1da*32+12),12)
 def test_new_locks_do_not_write_reverb_send(self):
  p=SendProbe();packed=pair(word(20,80),word(21,90));raw=p.payload(packed);self.assertEqual(struct.unpack_from('<I',raw,20)[0],packed);self.assertEqual(struct.unpack('<I',p.u.mem_read(0x2404600c,4))[0],packed);old=bytes(p.u.mem_read(p.root+0x608,8));p.begin();self.assertEqual(bytes(p.u.mem_read(p.root+0x608,8)),old);p.end()
 def test_synth_lock_changes_hit_and_next_unlocked_hit_resumes_background(self):
  for model,k in [(1,12),(3,20),(5,25)]:
   outputs=[]
   for packed in [0,word(k,100)]:
    p=Kick();p.w(p.desc+0x24,FRAMES+model-1);p.w(0x24046000,0x374c5042);p.w(0x24046008,p.root);p.w(0x2404600c,packed);p.start();a=[]
    for _ in range(4):a.extend(p.render()[1])
    outputs.append(a)
   self.assertGreater(sum(abs(x-y) for x,y in zip(*outputs)),.01)
   p.w(0x2404600c,0);p.start();self.assertEqual(p.render()[0],1)
   self.assertEqual(struct.unpack('<2I',p.u.mem_read(0x24047e80,8)),(0,0))
 def test_two_synth_locks_match_manual_knobs_without_changing_background(self):
  for model,k,path in [(1,12,'BENTO_Kick_K2.wav'),(3,20,'BENTO_Synth_Snare.wav'),(5,25,'BENTO_Synth_HiHat.wav')]:
   outputs=[]
   for locked in [False,True]:
    ui=UI();ui.path=path;ui.prepare()
    if not locked:ui.event(KEYS[0],100);ui.event(KEYS[1],90)
    p=Kick();p.w(p.root+12,0x13e);p.w(p.desc+0x24,FRAMES+model-1)
    mailbox=bytes(ui.u.mem_read(0x24043500,0x820));p.u.mem_write(0x24043500,mailbox);p.u.mem_write(0x24043d80,bytes(ui.u.mem_read(0x24043d80,128)))
    if locked:
     p.w(0x24046000,0x374c5042);p.w(0x24046008,p.root);p.w(0x2404600c,pair(word(k,100),word(k+1,90)))
    p.start();a=[]
    for _ in range(4):a.extend(p.render()[1])
    self.assertEqual(bytes(p.u.mem_read(0x24043500,0x820)),mailbox);outputs.append(a)
   self.assertEqual(*outputs)
 def test_lock_for_other_engine_is_ignored(self):
  outputs=[]
  for packed in [0,word(24,100)]:
   p=Kick();p.w(0x24046000,0x374c5042);p.w(0x24046008,p.root);p.w(0x2404600c,packed);p.start();outputs.append(p.render()[1])
  self.assertEqual(*outputs)
