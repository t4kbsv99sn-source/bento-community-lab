"""E3 combined image: patched K16 widget APIs plus native SEQ encoder banks."""
from pathlib import Path
import os,sys,json,unittest,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'k16_work'));sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import release
stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes();base,_=release.candidate(stock)
out=Path(os.environ['BENTO_FX_CANDIDATE']);image=(out/'bento1.bin').read_bytes();manifest=json.loads((out/'manifest.json').read_text());UU=manifest['ui_symbols']
release.native.candidate=lambda stock:(image,[])
import importlib.util, kick_build
spec=importlib.util.spec_from_file_location('optimized_kick', ROOT/'eu4_work/drums/kick_build.py')
optimized=importlib.util.module_from_spec(spec);spec.loader.exec_module(optimized);optimized.compile_kick()
kick_build.SYMS.clear();kick_build.SYMS.update(optimized.SYMS)
import unicorn
oldmap=unicorn.Uc.mem_map
def mapping(self,a,n,*args,**kwargs):return oldmap(self,a,0x1c0000 if a==0x08040000 and n==0x180000 else n,*args,**kwargs)
unicorn.Uc.mem_map=mapping
from unicorn.arm_const import *
from unicorn import UC_HOOK_CODE
from test_k16 import SynthUI,NativeWidgetUI,word
from test_kick_ui import UI,KEYS
from step_locks import U_SYMS
class Seq(SynthUI):
 def __init__(self,model=3):
  super().__init__(model);self.u.mem_map(0xc0000000,0x200000);self.next=0xc0100000
  self.w(0x3000004c,self.next);self.w(0x30000048,0xc0200000);self.arrows=[]
  self.u.hook_add(UC_HOOK_CODE,self.newhook,begin=0x08104c08,end=0x08104c08)
  self.u.hook_add(UC_HOOK_CODE,self.newhook,begin=0x0815bc4c,end=0x0815bc4c)
  self.w(self.view+0x113f8,16)
  # Real native project/note-container backing for Euclidean materialization.
  self.project=0xc0040000;self.track=0xc0041000;self.object=0xc0042000;self.vt=0xc0043000
  self.w(self.page,self.project);self.w(self.project,self.track);self.w(self.project+0x30,1);self.w(self.project+0x68,10000)
  self.w(self.track,self.vt);self.w(self.vt+0x14,0x081ff181);self.w(self.object+0x14,self.container-12)
  self.u.mem_write(self.container-4,b'\x02')
  for a in [0x081ff180,0x08133cfc,0x081338dc,0x0810b960,0x08173272]:self.u.hook_add(UC_HOOK_CODE,self.extra,begin=a,end=a)
 def hook(self,u,a,n,d):
  if a==0x08136544:return # Execute real native per-note insert/update.
  super().hook(u,a,n,d)
 def extra(self,u,a,n,d):
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x081ff180:self.w(r[2],self.object);self.ret(1);return
  if a==0x08133cfc:self.w(r[1],80);self.ret(1);return
  if a in [0x081338dc,0x0810b960,0x08173272]:self.ret();return
  if a==0x08133614 and r[2]==0x62:self.w(r[3],16);self.ret(1);return
  if a in [0x0817e174,0x0817e19c,0x0817e1d8,0x0817e1fe]:
   cell=u.reg_read(UC_ARM_REG_R0);value=u.reg_read(UC_ARM_REG_R1)
   if a==0x0817e174:self.w(cell+0x6f0,value)
   else:u.mem_write(cell+{0x0817e19c:0xec,0x0817e1d8:0x6ec,0x0817e1fe:0x6ed}[a],bytes([int(not value) if a==0x0817e19c else value&255]))
   self.ret();return
  if a==0x08170656 and not u.reg_read(UC_ARM_REG_R2):self.screen.append(('caption',''));self.ret();return
  if a==0x08133f7c and self.word(u.reg_read(UC_ARM_REG_R1))==80:self.ret(14);return
  super().extra(u,a,n,d)
 def call(self,a,*args):
  for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,val)
  self.u.reg_write(UC_ARM_REG_SP,0x2003f000);self.u.reg_write(UC_ARM_REG_LR,self.stop|1)
  self.u.emu_start(a|1,self.stop,count=1000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==self.stop,hex(self.u.reg_read(UC_ARM_REG_PC))
 def newhook(self,u,a,n,d):
  if a==0x08104c08:
   if getattr(self,"native_allocator",False):return
   size=u.reg_read(UC_ARM_REG_R0);p=self.word(0x3000004c);self.w(0x3000004c,p+((size+31)&~31));self.ret(p)
  else:self.arrows.append(u.reg_read(UC_ARM_REG_R1));self.ret()
 def arrow(self,id):
  event=0x20028000;self.w(event,0x73);self.w(event+8,id);self.call(UU['seq_eu_arrows'],self.view,event)
 def bank(self):self.call(UU['seq_eu_active'],self.view);return self.u.reg_read(UC_ARM_REG_R0)
 # CH5: the Euclid bank is the Euclidean view tab (header id 1055); arrows are native.
 def tab(self):self.call(UU['seq_eu_tab'],self.view)
 def leave(self):self.call(UU['seq_eu_leave'],self.view)
 def arrow_result(self,id):self.arrow(id);return self.u.reg_read(UC_ARM_REG_R0)
class Tests(unittest.TestCase):
 def test_native_ui_allocator_c6_pool_reaches_euclidean_from_actual_event_entry(self):
  p=Seq();p.u.mem_map(0xc6000000,0x20000)
  p.w(0x3000004c,0xc6000000);p.w(0x30000048,0xc6020000)
  # Use the actual bump allocator, not the fixture's C0 substitute.
  original=p.newhook
  # Registered hook is bound, so suppress via its explicit flag below.
  p.native_allocator=True
  event=0x20028000;p.w(event,0x1055) # Euclidean tab through the patched native SEQ action dispatcher
  p.call(0x0815d600,p.view,event)
  self.assertEqual(p.bank(),1);self.assertEqual(p.word(0x24041fc4),0xc6000000)
  self.assertEqual(p.word(0x3000004c),0xc6000000+46080) # CH3 +16 runtime pitch lines; CH6 +1344 chord audition; CH8 +160 velocity

 def test_euclidean_tab_switches_only_encoder_bank_and_keeps_native_step_sequence_flag(self):
  for flag in [0,1]:
   p=Seq();p.u.mem_write(p.view+0x113e0,bytes([flag]));p.tab();self.assertEqual(p.bank(),1)
   self.assertEqual(p.u.mem_read(p.page+0x12c,1),b'\x27');self.assertEqual(p.u.mem_read(p.view+0x113e0,1),bytes([flag]))
   p.leave();self.assertEqual(p.bank(),0);self.assertEqual(p.u.mem_read(p.view+0x113e0,1),bytes([flag]))
 def test_all_arrows_stay_native_in_both_banks(self):
  # CH5 owner: Left/Right always previous/next event; Up/Down native.
  for bank in [0,1]:
   p=Seq()
   if bank:p.tab()
   self.assertEqual([p.arrow_result(i) for i in [0,1,8,9]],[0,0,0,0]);self.assertEqual(p.bank(),bank)
 def test_normal_step_locks_moved_to_encoders_seven_eight(self):
  p=Seq();p.prepare();self.assertEqual(struct.unpack('<4H',p.u.mem_read(0x300000c4,8)),(0,0,2,0x32))
  p.display();bar=p.view+0xebf0
  self.assertEqual(struct.unpack('<2H',p.u.mem_read(p.view+0x113b8,4)),(2,0x32))
 def test_euclidean_bar_has_six_controls_and_locks_seven_eight(self):
  p=Seq();p.tab();p.prepare();p.call(U_SYMS['locks_header_after'],p.view)
  self.assertEqual(struct.unpack('<8H',p.u.mem_read(p.view+0x113ac,16)),(0x190,0x191,0x192,0x193,0x194,0x195,2,0x32))
  p.encoder(0x191,7);p.encoder(0x192,3);p.call(U_SYMS['locks_header_after'],p.view)
  self.assertEqual(p.word(p.view+0x113c0),7);self.assertEqual(p.word(p.view+0x113c4),3)
 def test_lock_edit_and_target_selection_work_in_both_encoder_banks(self):
  for eu in [False,True]:
   p=Seq();p.press(0)
   if eu:p.arrow(9);p.press(0)
   p.shift();p.encoder(0x1da,8);p.shift(False);p.encoder(KEYS[0],80);self.assertEqual(p.stored(),word(20,80))
   p.display();self.assertIn(('caption','424 Hz'),p.screen)
 def test_synth_lock_displays_same_hz_percent_values_as_instrument_editor(self):
  # P10: the 909 Snare's Tune is 140 Hz x 2^(v/50) (80 -> 424 Hz; was 80+12v).
  for model,k,raw,text in [(1,12,80,'80 Hz'),(3,20,80,'424 Hz'),(5,25,80,'956 Hz')]:
   p=Seq(model);p.press(0);p.shift();p.encoder(0x1da,8);p.shift(False);p.encoder(KEYS[0],raw);p.display()
   self.assertEqual(p.stored(),word(k,raw));self.assertIn(('caption',text),p.screen)
   p.shift();p.encoder(0x1da,9);p.shift(False);p.encoder(KEYS[1],73);p.display();self.assertIn(('caption','73%'),p.screen)
 def test_kick_to_snare_and_hat_explicitly_clear_unused_top_controls(self):
  p=UI();p.prepare();p.event(KEYS[5],77);p.event(KEYS[6],88)
  for filename in ['BENTO_Synth_Snare.wav','BENTO_Synth_HiHat.wav']:
   p.path=filename;p.calls=[];p.prepare()
   for i in [6,7]:
    slot=p.v+0x38+0x38+i*0x468
    self.assertIn(('widget',slot,0,0,1),p.calls);self.assertIn(('title',slot+0x3c8,''),p.calls)
    self.assertIn(('value',p.v+0x38,i,''),p.calls)
 def test_seq_taps_are_never_consumed_by_custom_double_tap(self):
  p=Seq()
  for code,tick in [(0xaf,1000),(0xb0,1050),(0xaf,1200)]:
   p.w(0x3001fe2c,tick);p.call(UU['fx_dispatch'],p.page,code,0,11);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_patched_arrow_site_hands_right_to_native_next_event(self):
  p=Seq();event=0x20028000;p.w(event,0x73);p.w(event+8,9);sp=0x2003e000
  p.u.reg_write(UC_ARM_REG_R0,p.view);p.u.reg_write(UC_ARM_REG_R1,event);p.u.reg_write(UC_ARM_REG_SP,sp)
  p.u.emu_start(0x0815d57f,0x0815d520,count=1000000);self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x0815d520);self.assertEqual(p.bank(),0)
  self.assertEqual(p.arrows,[1])
 def test_proj_left_returns_selected_pad_to_manual_without_erasing_notes(self):
  p=Seq();before=bytes(p.u.mem_read(p.container,72));p.tab();p.w(0x24048d68,1);self.assertEqual(p.arrow_result(0),1)
  self.assertEqual(bytes(p.u.mem_read(p.container,72)),before) # Shift+Left stops generating, notes kept
 def test_actual_native_widgets_clear_kick_values_on_snare_switch(self):
  p=NativeWidgetUI();p.u.reg_write(UC_ARM_REG_R0,0);p.u.reg_write(UC_ARM_REG_SP,0x20030000);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x081639a9,0x081ff200,count=200000)
  p.prepare();p.event(KEYS[5],77);p.event(KEYS[6],88);p.prepare();p.path='BENTO_Synth_Snare.wav';p.prepare()
  for i in [6,7]:
   slot=p.v+0x38+0x38+i*0x468;self.assertEqual(p.text(slot+0x2c8),'');self.assertEqual(struct.unpack('<H',p.u.mem_read(slot+0x9c,2))[0],0)
if __name__=='__main__':unittest.main(verbosity=2)
