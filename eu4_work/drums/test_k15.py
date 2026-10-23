"""K15 compiled-engine/UI regressions. No claim of physical device validation."""
import math,struct,unittest,io,wave
from test_kick import Kick,FRAMES
from kick_build import SYMS as DSP
from test_kick_ui import UI,KEYS
from test_kick_install import Install
from unicorn.arm_const import UC_ARM_REG_R0
HAT='\\Projects\\BENTO_Synth_HiHat.wav';CLICK=0x1b0
class Tests(unittest.TestCase):
 def sound(self,u,model):
  k=Kick();k.w(k.root+12,0x13e);k.w(k.desc+0x24,FRAMES+model-1);k.u.mem_write(0x24043500,bytes(u.u.mem_read(0x24043500,0x820)));k.u.mem_write(0x24043d80,bytes(u.u.mem_read(0x24043d80,128)));return k
 def test_hat_identity_rejects_nearby_length(self):
  k=Kick();k.w(k.desc+0x24,FRAMES+4);k.call(DSP['kick_marker'],k.desc);self.assertEqual(k.u.reg_read(UC_ARM_REG_R0),5)
  k.w(k.desc+0x24,FRAMES+3);k.call(DSP['kick_marker'],k.desc);self.assertEqual(k.u.reg_read(UC_ARM_REG_R0),0)
 def test_hat_five_controls_existing_mix_and_no_third_row(self):
  u=UI();u.path=HAT;u.prepare();self.assertEqual(u.values(),[10,70,65,65,30,0,0]);self.assertIn(('title',u.v+0x80b4,'HiHat / Pad 1'),u.calls)
  self.assertEqual(struct.unpack('<8H',u.u.mem_read(u.v+0x703c,16)),(2,*KEYS[:5],0,0));self.assertEqual(bytes(u.u.mem_read(u.v+0x4858,1)),b'\1')
  self.assertIn(('value',u.v+0x38,1,'207 Hz'),u.calls)
 def test_hat_parameters_save_load_with_identity(self):
  u=UI();u.path=HAT;u.prepare();u.event(KEYS[1],74);u.event(KEYS[4],12);u.call('kick_ui_save',u.o,u.params);u.u.mem_write(0x24043500,bytes(0x820));u.call('kick_ui_load',u.params,u.o);self.assertEqual(u.values(),[10,74,65,65,12,0,0]);self.assertEqual(u.attrs['bento_drum_model'],5)
 def test_kick_click_changes_audio_without_changing_other_parameters(self):
  outputs=[]
  for click in [0,100]:
   u=UI();u.prepare();u.event(CLICK,click);self.assertEqual(u.values(),[55,65,45,65,55,25,25]);k=self.sound(u,1);k.start();a=[]
   for _ in range(10):a.extend(k.render()[1])
   outputs.append(a)
  self.assertGreater(sum(abs(x-y) for x,y in zip(*outputs)),.1)
 def test_click_default_and_third_row_binding(self):
  u=UI();u.prepare();self.assertEqual(u.u.mem_read(0x24043d80,1),b'-');self.assertEqual(struct.unpack('<8H',u.u.mem_read(u.v+0x70dc,16)),(CLICK,0,0,0,0,0,0,0));self.assertIn(('value',u.v+0x4828,0,'45%'),u.calls)
 def test_click_roundtrip_and_legacy_tone_migration(self):
  u=UI();u.prepare();u.event(KEYS[2],73);u.event(CLICK,9);u.call('kick_ui_save',u.o,u.params);self.assertEqual(u.attrs['bento_drum_v2_click'],9)
  u.u.mem_write(0x24043500,bytes(0x820));u.call('kick_ui_load',u.params,u.o);self.assertEqual(u.u.mem_read(0x24043d80,1),b'\x09')
  del u.attrs['bento_drum_v2_click'];u.call('kick_ui_load',u.params,u.o);self.assertEqual(u.u.mem_read(0x24043d80,1),b'I')
 def test_click_is_independent_on_two_pads(self):
  u=UI();u.prepare();u.event(CLICK,11);u.w(u.v+0x87bc,0x140);u.prepare();u.event(CLICK,88);self.assertEqual(bytes(u.u.mem_read(0x24043d80,2)),bytes([11,88]))
 def test_tone_does_not_change_saved_click(self):
  u=UI();u.prepare();u.event(CLICK,23);u.event(KEYS[2],100);u.call('kick_ui_save',u.o,u.params);self.assertEqual(u.attrs['bento_drum_v2_click'],23)
 def test_registry_can_switch_between_all_three_engines(self):
  u=UI()
  for name in ['BENTO_Kick_K2.wav','BENTO_Synth_Snare.wav',HAT,'BENTO_Kick_K2.wav']:
   u.path=name;u.prepare();self.assertEqual(u.r(0x24043d28),1)
 def test_hat_native_audio_route(self):
  u=UI();u.path=HAT;u.prepare();k=self.sound(u,5);k.native_postprocess();k.start()
  for _ in range(8):self.assertEqual(k.render()[0],1)
  self.assertTrue(all(math.isfinite(x) for ch in k.outputs() for x in ch));self.assertGreater(max(abs(x) for ch in k.outputs() for x in ch),.001)
 def test_last_hat_slot_does_not_touch_locks_or_ui(self):
  u=UI();u.path=HAT;u.prepare();k=self.sound(u,5);k.start()
  for i in range(15):k.w(0x24042000+16+i*236+24,1000)
  k.w(k.root+12,999);k.w(k.desc+4,99);guards=[(0x24044000,0x1810),(0x24046000,0x1420),(0x24048000,0x800)]
  for a,n in guards:k.u.mem_write(a,b'\xa5'*n)
  k.start();self.assertEqual(k.render()[0],1);self.assertEqual(struct.unpack('<I',k.u.mem_read(0x24047e40+15*4,4))[0],5)
  for a,n in guards:self.assertEqual(bytes(k.u.mem_read(a,n)),b'\xa5'*n)
 def test_hat_and_snare_use_different_audio_in_same_state(self):
  u=UI();u.path=HAT;u.prepare();k=self.sound(u,5);k.start();hat=k.render()[1];k.w(k.desc+0x24,FRAMES+2);k.w(k.desc+4,9);k.start();sn=k.render()[1];self.assertGreater(sum(abs(x-y) for x,y in zip(hat,sn)),.05)
 def test_hat_installer_writes_exact_content_and_preserves_existing(self):
  p=Install();self.assertEqual(p.call('kick_install'),1);data=bytes(p.files[HAT])
  with wave.open(io.BytesIO(data),'rb') as w:self.assertEqual((w.getnframes(),w.getframerate(),w.getnchannels(),w.getsampwidth()),(FRAMES+4,48000,1,2))
  p.io=[];self.assertEqual(p.call('kick_install'),1);self.assertEqual(bytes(p.files[HAT]),data);self.assertFalse(any(x[0]=='write' for x in p.io))
 def test_snappy_above_old_cliff_keeps_distinct_values_and_finite_sound(self):
  outs=[]
  for val in [20,30,60,100]:
   u=UI();u.path='BENTO_Synth_Snare.wav';u.prepare();u.event(KEYS[4],val);k=self.sound(u,3);k.start();a=[]
   for _ in range(12):a.extend(k.render()[1])
   self.assertTrue(all(math.isfinite(x) and abs(x)<=1 for x in a));outs.append(a)
  for a,b in zip(outs,outs[1:]):self.assertGreater(sum(abs(x-y) for x,y in zip(a,b)),.01)
