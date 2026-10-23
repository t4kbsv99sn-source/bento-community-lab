"""K3 explicit loader-to-engine assignment, independent of sample-cache PCM."""
import unittest,struct
from unicorn.arm_const import *
from test_kick import Kick
from test_kick_install import Install
from test_plock import Probe
from test_controls import REGS
from kick_build import SYMS

class Tests(unittest.TestCase):
 def test_explicit_assignment_generates_audio_without_any_marker_cache_read(self):
  p=Kick(False);p.ready=False;p.call(SYMS['kick_enable'],p.root,1);p.start()
  ok,audio=p.render();self.assertEqual(ok,1);self.assertGreater(max(abs(x) for x in audio),.001);self.assertEqual(p.reads,0)
 def test_explicit_assignment_reaches_original_native_audio_processing(self):
  p=Kick(False);p.native_postprocess();p.call(SYMS['kick_enable'],p.root,1);p.start()
  for _ in range(8):p.render()
  self.assertGreater(max(abs(v) for channel in p.outputs() for v in channel),.001);self.assertEqual(p.reads,0)
 def test_ordinary_sample_load_disarms_and_discards_synth_voice(self):
  p=Kick(False);p.call(SYMS['kick_enable'],p.root,1);p.start();self.assertEqual(p.render()[0],1)
  p.call(SYMS['kick_enable'],p.root,0);self.assertEqual(p.render()[0],0)
 def test_native_property_command_routes_explicit_assignment_and_consumes_key(self):
  p=Probe();self.assertEqual(p.command(0x7ffc,101,1),0x0808e9e0)
  p.call(SYMS['kick_selected'],p.obj);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),1)
  p.command(0x7ffc,101,0);p.call(SYMS['kick_selected'],p.obj);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_wrong_native_handle_or_engine_class_cannot_be_marked(self):
  for context,vt in [(102,0x080ac66c),(101,0x080ac670)]:
   p=Probe();p.w(p.obj,vt);p.command(0x7ffc,context,1)
   p.call(SYMS['kick_selected'],p.obj);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_128_current_pads_fit_and_reloading_projects_reclaims_prior_assignments(self):
  p=Kick();old=[];new=[]
  for start,roots in [(0x20000000,old),(0x30000000,new)]:
   for i in range(128):
    root=start+i*0x800;p.w(root,0x080ac66c);p.w(root+12,100+i);roots.append(root)
    p.call(SYMS['kick_enable'],root,1)
   for root in roots:
    p.call(SYMS['kick_selected'],root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),1)
  for root in old:
   p.call(SYMS['kick_selected'],root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_changed_handle_does_not_inherit_a_remembered_assignment(self):
  p=Kick();p.call(SYMS['kick_enable'],p.root,1);p.w(p.root+12,9999)
  p.call(SYMS['kick_selected'],p.root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_loader_recognises_only_reserved_kick_names_in_any_directory(self):
  yes=['BENTO_Kick_K2.wav','\\Projects\\BENTO_Kick_K2.wav','./Projects/Packed/bento_kick_k1.WAV','/Projects/BENTO_Kick.wav']
  no=['/Projects/kick.wav','BENTO_Kick_K2.wav.bak','not_BENTO_Kick_K2.wav','BENTO_Kick_K2.wav/normal.wav','x'*256]
  for path in yes+no:
   p=Install();p.u.mem_write(0x2001d000,path.encode()+b'\0')
   self.assertEqual(p.call('kick_path',0x2001d000),int(path in yes),path)
 def test_native_loader_sends_arm_or_disarm_and_ignores_browser_preview(self):
  for path,handle,wanted in [('BENTO_Kick_K2.wav',101,1),('normal.wav',101,0),('BENTO_Kick_K2.wav',0xfffffff9,None)]:
   p=Install();p.w(0x3000f650,0x20028000);p.u.mem_write(0x2001d000,path.encode()+b'\0')
   p.call('kick_sample_loading',0x2001b000,handle,0x2001d000,1)
   self.assertEqual([x for x in p.log if x[0]=='engine'],[])
 def test_native_loader_wrapper_preserves_registers_and_replays_original_push(self):
  for entry,resume,delta in [(0x0810e0b8,0x0810e0bc,32),(0x0810dff4,0x0810dff8,36)]:
   p=Install();sp=0x20030000;p.w(0x3000f650,0x20028000);p.u.mem_write(0x2001d000,b'\\Projects\\BENTO_Kick_K2.wav\0')
   before=[0x11000+i for i in range(13)];before[:4]=[0x2001b000,101,0x2001d000,1]
   for reg,v in zip(REGS,before):p.u.reg_write(reg,v)
   for i in range(32):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*11)
   p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
   p.u.emu_start(entry|1,resume,count=1000000)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),resume);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-delta)
   self.assertEqual([p.u.reg_read(x) for x in REGS],before)
   for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*11)
   self.assertNotIn(('engine',101,0x7ffc,1),p.log)

if __name__=='__main__':unittest.main(verbosity=2)
