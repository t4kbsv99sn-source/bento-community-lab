"""K15 snare, shared-RAM isolation, carrier persistence and synth encoder scaling."""
import unittest,struct,math,io,wave
from test_kick import Kick,FRAMES
from kick_build import SYMS as DSP
from test_kick_ui import UI,KEYS
from test_kick_install import Install
from kick_ui_build import SYMS as UI_SYMS
from test_controls import REGS
from unicorn.arm_const import *
SNARE='\\Projects\\BENTO_Synth_Snare.wav'
class Tests(unittest.TestCase):
 def snare(self):
  k=Kick();k.w(k.desc+0x24,FRAMES+2);return k
 def test_snare_carrier_recognised_as_distinct_engine(self):
  k=self.snare();k.call(DSP['kick_marker'],k.desc);self.assertEqual(k.u.reg_read(UC_ARM_REG_R0),3)
 def test_real_snare_has_finite_nonzero_audio_and_native_post_route(self):
  k=self.snare();k.start();audio=[]
  for _ in range(24):ok,a=k.render();self.assertEqual(ok,1);audio.extend(a)
  self.assertTrue(all(math.isfinite(x) for x in audio));self.assertGreater(max(abs(x) for x in audio),.005);self.assertLessEqual(max(abs(x) for x in audio),1)
  self.assertEqual(k.post[-1],(k.root,k.voice,k.temp,k.output))
 def test_snare_and_kick_have_different_sound(self):
  k=Kick();s=self.snare();k.start();s.start();self.assertGreater(sum(abs(x-y) for x,y in zip(k.render()[1],s.render()[1])),.1)
 def test_snare_with_real_native_postprocessing(self):
  k=self.snare();k.native_postprocess();k.start()
  for _ in range(6):self.assertEqual(k.render()[0],1)
  self.assertTrue(all(math.isfinite(v) for c in k.outputs() for v in c));self.assertGreater(max(abs(v) for c in k.outputs() for v in c),.001)
 def test_snare_ui_uses_five_sound_controls_and_existing_mix_row(self):
  u=UI();u.path=SNARE;u.prepare();self.assertEqual(u.values(),[10,45,10,65,70,0,0]);self.assertEqual(u.u.mem_read(0x2404352f,1),b'\3')
  self.assertEqual(struct.unpack('<8H',u.u.mem_read(u.v+0x703c,16)),(2,*KEYS[:5],0,0))
  self.assertIn(('title',u.v+0x80b4,'Snare / Pad 1'),u.calls)
  self.assertIn(('value',u.v+0x38,1,'200 Hz'),u.calls)
 def test_switching_kick_snare_resets_per_handle_model_without_crossing_other_pads(self):
  u=UI();u.prepare();u.event(KEYS[0],77);u.w(u.v+0x87bc,0x140);u.path=SNARE;u.prepare();u.event(KEYS[0],60)
  self.assertEqual(u.values()[0],77);self.assertEqual(list(u.u.mem_read(0x24043538,7))[:2],[60,45])
  u.path='bento_kick_k2.wav';u.w(u.v+0x87bc,0x13e);u.prepare();self.assertEqual(u.values()[0],77)
 def test_snare_values_save_and_reload_with_model_identity(self):
  u=UI();u.path=SNARE;u.prepare();u.event(KEYS[0],2);u.event(KEYS[4],93);u.call('kick_ui_save',u.o,u.params)
  self.assertEqual(u.attrs['bento_drum_model'],3);u.u.mem_write(0x24043500,bytes(0x820));u.call('kick_ui_load',u.params,u.o);self.assertEqual(u.values(),[2,45,10,65,93,0,0]);self.assertEqual(u.u.mem_read(0x2404352f,1),b'\3')
 def test_snare_knob_values_change_rendered_audio(self):
  outs=[]
  for val in [0,100]:
   u=UI();u.path=SNARE;u.prepare();u.event(KEYS[4],val);k=self.snare();k.w(k.root+12,0x13e);k.u.mem_write(0x24043500,bytes(u.u.mem_read(0x24043500,0x820)));k.start();a=[]
   for _ in range(4):a.extend(k.render()[1])
   outs.append(a)
  self.assertGreater(sum(abs(x-y) for x,y in zip(*outs)),.1)
 def test_both_carriers_created_without_overwriting_existing_files(self):
  p=Install();self.assertEqual(p.call('kick_install'),1)
  with wave.open(io.BytesIO(bytes(p.files[SNARE])),'rb') as w:self.assertEqual((w.getnframes(),w.getframerate(),w.getnchannels()),(FRAMES+2,48000,1))
  before={k:bytes(v) for k,v in p.files.items()};p.io=[];p.call('kick_install');self.assertEqual(before,{k:bytes(v) for k,v in p.files.items()});self.assertFalse(any(x[0]=='write' for x in p.io))
 def test_occupied_native_send_and_lock_tables_survive_snare_initialization(self):
  k=self.snare();s=b'\xa5'*0x1810;a=b'\x5a'*0x1420;k.u.mem_write(0x24044000,s);k.u.mem_write(0x24046000,a);k.start();k.render();self.assertEqual(bytes(k.u.mem_read(0x24044000,len(s))),s);self.assertEqual(bytes(k.u.mem_read(0x24046000,len(a))),a)
 def test_last_snare_slot_fits_reserved_gap(self):
  k=self.snare();k.call(DSP['kick_voice'],k.voice,k.root)
  # Fill old slot metadata as occupied to force allocation of slot 15.
  for i in range(15):k.w(0x24042000+16+i*236+24,1000)
  k.w(k.root+12,999);k.w(k.desc+4,99);k.start();self.assertEqual(k.render()[0],1)
  self.assertEqual(struct.unpack('<I',k.u.mem_read(0x24047e40+15*4,4))[0],3)
 def test_actual_encoder_wrapper_scales_only_synth_keys_and_preserves_native_prologue(self):
  for key,delta in [(KEYS[0],1),(KEYS[1],-2),(KEYS[2],12800),(4,2),(0x1aa,1),(0x1ad,1)]:
   u=UI();slot=u.v+0x70;u.u.mem_write(slot+0x9c,struct.pack('<H',key));u.u.reg_write(UC_ARM_REG_R0,slot);u.u.reg_write(UC_ARM_REG_R1,delta&0xffffffff);u.u.reg_write(UC_ARM_REG_SP,0x20030000);u.u.reg_write(UC_ARM_REG_LR,0x081ff201)
   u.u.emu_start(0x08171e45,0x08171e48,count=200000);expected=delta*5 if key in KEYS else delta
   self.assertEqual(u.u.reg_read(UC_ARM_REG_R1),expected&0xffffffff);self.assertEqual(u.u.reg_read(UC_ARM_REG_SP),0x20030000-48)

 def test_private_synth_load_button_creates_snare_before_browser(self):
  class Both(UI):
   def __init__(self):
    super().__init__();self.real_install=True;self.files={};self.open_files={};self.io=[];self.fail_open=None;self.fail_write=self.short_write=self.fail_close=False
    self.u.hook_add(__import__('unicorn').UC_HOOK_CODE,lambda u,a,n,d:Install.filesystem(self,u,a,n,d))
   cstr=Install.cstr
  p=Both();p.prepare();p.event(0x1ad,1);self.assertIn(SNARE,p.files);self.assertTrue(any(c[:3]==('native',0x08152bb0,p.v) for c in p.calls))
 def test_mixed_kick_and_snare_play_in_one_engine_state(self):
  p=Kick();p.start();old=(p.root,p.voice,p.desc);root,voice,desc=0x2001c000,0x2001d000,0x2001e000
  p.u.mem_write(root,bytes(p.u.mem_read(p.root,0x800)));p.u.mem_write(voice,bytes(p.u.mem_read(p.voice,0x400)));p.u.mem_write(desc,bytes(p.u.mem_read(p.desc,0x2c)))
  p.w(root+12,202);p.w(root+0x20,voice);p.w(voice+12,desc);p.w(desc+0x24,FRAMES+2);p.w(desc+4,8)
  p.root,p.voice,p.desc=root,voice,desc;p.start();ok,sn=p.render();self.assertEqual(ok,1)
  p.root,p.voice,p.desc=old;ok,ki=p.render();self.assertEqual(ok,1);self.assertGreater(max(abs(x) for x in sn),.001);self.assertGreater(max(abs(x) for x in ki),.001)
  models=struct.unpack('<16I',p.u.mem_read(0x24047e40,64));self.assertIn(1,models);self.assertIn(3,models)
 def test_snare_extreme_parameters_are_finite(self):
  for vals in [[0,0,0,0,0,0,0],[100,100,100,100,100,0,0]]:
   u=UI();u.path=SNARE;u.prepare()
   for key,val in zip(KEYS,vals):u.event(key,val)
   k=self.snare();k.w(k.root+12,0x13e);k.u.mem_write(0x24043500,bytes(u.u.mem_read(0x24043500,0x820)));k.start()
   for _ in range(8):ok,a=k.render();self.assertEqual(ok,1);self.assertTrue(all(math.isfinite(x) and abs(x)<=1 for x in a))
