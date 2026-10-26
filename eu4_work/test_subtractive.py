"""S1 tests execute the installed ARM engine and real native amp postprocessor.
Filesystem/model services are fixtures; hardware deadlines are not measured.
"""
import unittest,struct,math
import unicorn
# The inherited fixture registered its three substituted services on every
# instruction. Restrict only those known callbacks to their exact addresses;
# synth code and native envelope code still execute without substitution.
_hook_add=unicorn.Uc.hook_add
def _service_hooks(self,kind,callback,*args,**kwargs):
 if kind==unicorn.UC_HOOK_CODE and not args and not kwargs:
  name=getattr(callback,'__qualname__','')
  if name=='Kick.extra':
   for at in (0x081be010,0x081be020,0x08092d00):
    handle=_hook_add(self,kind,callback,begin=at,end=at)
   return handle
  if name=='AudioProbe.__init__.<locals>.<lambda>':
   at=callback.__closure__[0].cell_contents.stop
   return _hook_add(self,kind,callback,begin=at,end=at)
 return _hook_add(self,kind,callback,*args,**kwargs)
unicorn.Uc.hook_add=_service_hooks
from test_engines import engine,run,energy,SYMS,_k16,Synth
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0
DEFAULT=(20,50,35,60,25,35,45)
_KEEP=[]
_synth_init=Synth.__init__
def _retain_synth(self,**kwargs):
 _synth_init(self,**kwargs);_KEEP.append(self)
Synth.__init__=_retain_synth
_ui_init=_k16.UI.__init__
def _retain_ui(self):
 _ui_init(self);_KEEP.append(self)
_k16.UI.__init__=_retain_ui
KEYS=[0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9]
def voice(values=DEFAULT,sync=0):
 p=engine(11,values);p.u.mem_write(0x24043d80,bytes([sync]));return p
class Tests(unittest.TestCase):
 def test_marker_is_exact_and_ordinary_samples_still_fall_back(self):
  p=voice();p.call(SYMS['kick_marker'],p.desc);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),11)
  p.marker=False;p.start();self.assertEqual(p.render()[0],0)
 def test_finite_audible_audio_at_parameter_extremes(self):
  for values,sync in [(DEFAULT,0),((0,0,0,0,0,0,0),0),((100,100,100,100,100,100,100),100)]:
   a=run(voice(values,sync),24)
   self.assertTrue(all(math.isfinite(x) and abs(x)<=1 for x in a));self.assertGreater(energy(a),1e-6)
 def test_each_sound_control_changes_the_audio(self):
  a=run(voice(),20)
  for j in range(7):
   v=list(DEFAULT);v[j]=95 if v[j]<80 else 10
   self.assertNotEqual(run(voice(tuple(v)),20),a,j)
 def test_sync_and_sync_sweep_are_audible(self):
  v=(0,65,30,85,20,0,40)
  a=run(voice(v,0),30);b=run(voice(v,1),30);c=run(voice(v,90),30)
  self.assertNotEqual(a,b);self.assertNotEqual(b,c)
 def test_sync_can_be_turned_off_during_a_note(self):
  p=voice(sync=85);p.start()
  for _ in range(4):p.render()
  p.u.mem_write(0x24043d80,b'\0');a=p.render()[1]
  q=voice(sync=85);q.start()
  for _ in range(4):q.render()
  self.assertNotEqual(a,q.render()[1])
 def test_native_pitch_scales_the_oscillators(self):
  import numpy as np
  def fundamental(ratio):
   p=voice((0,50,0,100,0,0,0));p.f(p.voice+0x48,ratio);a=run(p,40)
   a=np.asarray(a[512:]);spectrum=abs(np.fft.rfft(a*np.hanning(len(a))))
   return np.argmax(spectrum[2:50])+2
  self.assertAlmostEqual(fundamental(2)/fundamental(1),2,delta=.25)
 def test_high_keyboard_notes_do_not_fall_back_to_the_root_pitch(self):
  low=voice((0,50,0,100,0,0,0));high=voice((0,50,0,100,0,0,0))
  high.f(high.voice+0x48,16)
  self.assertNotEqual(run(low,12),run(high,12))
 def test_overlapping_native_voices_have_independent_synth_state(self):
  p=voice();p.start();first=p.voice;p.render();second=first+0x800
  p.w(second+12,p.desc);p.f(second+0x48,2);p.f(second+0xb8,1);p.u.mem_write(second,b'\1')
  p.w(p.root+0x60,2);p.w(p.root+0x24,second);p.call(SYMS['kick_voice'],second,p.root)
  self.assertEqual(p.u.mem_read(first,1),b'\1')
  p.voice=second;second_audio=p.render()[1];p.voice=first;first_audio=p.render()[1]
  self.assertNotEqual(second_audio,first_audio)
 def test_held_voice_does_not_stop_at_carrier_end(self):
  p=voice();p.start();p.render()
  p.w(0x24042000+16+24,0x7fffffff-144029-64)
  self.assertGreater(energy(p.render()[1]),0);self.assertEqual(p.u.mem_read(p.voice,1),b'\1')
  self.assertLess(p.r(p.voice+0x40),144029)
 def test_real_native_adsr_sustains_and_noteoff_releases(self):
  p=voice();p.native_postprocess();p.start()
  for _ in range(12):p.render()
  self.assertGreater(sum(energy(c) for c in p.outputs()),1e-6)
  # Native envelope NoteOff, not a fixture replacing the envelope math.
  p.call(0x08063960,p.voice+0x58)
  for _ in range(40):p.render()
  self.assertLess(sum(energy(c) for c in p.outputs()),1e-9)
  self.assertEqual(p.u.mem_read(p.voice,1),b'\0')
 def test_native_mute_and_pan_remain_in_the_audio_path(self):
  p=voice();p.native_postprocess();p.start()
  for _ in range(8):p.render()
  self.assertGreater(sum(energy(c) for c in p.outputs()),1e-6)
  p.u.mem_write(p.root+0x600,b'\1')
  for _ in range(8):p.render()
  self.assertLess(sum(energy(c) for c in p.outputs()),1e-9)
 def test_mod_matrix_reaches_cutoff_and_sync_without_mutating_knobs(self):
  for key in [KEYS[3],0x1b0]:
   p=voice();p.route(key,13,800);a=run(p,20)
   self.assertNotEqual(a,run(voice(),20));self.assertEqual(bytes(p.u.mem_read(0x24043528,7)),bytes(DEFAULT))
 def test_control_page_has_sync_and_native_amp_adsr(self):
  p=_k16.UI();p.path='\\Projects\\BENTO_Synth_Subtractive.wav';p.prepare()
  top=list(struct.unpack('<8H',p.u.mem_read(p.v+0x703c,16)))
  third=list(struct.unpack('<8H',p.u.mem_read(p.v+0x703c+0xa0,16)))
  self.assertEqual(top,[2]+KEYS);self.assertEqual(third,[0x1b0,0x1e,0x1f,0x20,0x21,0,0,0])
  titles=[c[2] for c in p.calls if c[0]=='title']
  for name in ['Subtractive / Pad 1','Shape','Osc2 Semi','Fat','Cutoff','Resonance','Env Amt','Env Decay','Sync']:self.assertIn(name,titles)
  self.assertIn('Off',[c[3] for c in p.calls if c[0]=='value'])
 def test_engine_and_sync_save_and_reload(self):
  p=_k16.UI();p.path='BENTO_Synth_Subtractive.wav';p.prepare()
  p.event(0x1b0,77);p.event(KEYS[2],83)
  p.call('kick_ui_save',p.o,p.params)
  self.assertEqual(p.attrs.get('bento_drum_model'),11)
  self.assertEqual(p.attrs.get('bento_drum_v2_click'),77)
  p.u.mem_write(0x24043500,bytes(0x900));p.call('kick_ui_load',p.params,p.o)
  self.assertEqual(p.values()[2],83)
  self.assertEqual(p.u.mem_read(0x2404352f,1),b'\x0b')
  self.assertEqual(p.u.mem_read(0x24043d80,1),bytes([77]))
 def test_instruction_cost_is_bounded(self):
  costs=[]
  for sync in (0,75):
   p=voice(sync=sync);run(p,12,costs)
  print('S1 emulated instructions/sample, plain/sync:',costs,flush=True)
  self.assertLess(max(costs),2200)
if __name__=='__main__':unittest.main(verbosity=2)
