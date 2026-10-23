"""L8 raw receiver ownership and real native model/engine mute parity."""
import unittest,struct
from unicorn.arm_const import *
from test_input import Input
from test_controls import Fixture,REGS
from test_plock import AudioProbe
from build import CONSUMER

class DrumInput(Input):
 def __init__(self,page=7):
  super().__init__()
  self.u.mem_write(0x30024c2c,bytes([page]));self.word(0x30024c3c,501)

class Mute(Fixture):
 def __init__(self):
  super().__init__();self.engine=0x30010000;self.w(0x3000f650,self.engine)
  self.page(7);self.contexts([501,80,33,44]);self.ui=[];self.dirty=0;self.refresh=0
  self.cells=[0x20018000+i*0x80 for i in range(16)];self.childvt=0x20012a00
  self.w(self.vtable+0x14,0x081ff051);self.w(self.vtable+0x18,0x081ff031);self.w(self.childvt,0x081ff041)
  for i,o in enumerate(self.cells):
   self.w(o,self.childvt);self.w(o+16,501+i)
   self.props[(o,0x73)]=i;self.props[(o,0x1e0)]=0
 def hook(self,u,a,size,data):
  r=[u.reg_read(x) for x in REGS[:4]]
  if a==0x081ff050:
   self.w(r[2],self.cells[r[1]-501] if 501<=r[1]<517 else 0);self.ret(int(501<=r[1]<517))
  elif a==0x081ff030:
   if r[1]<len(self.cells):self.w(r[2],self.cells[r[1]]);self.ret(1)
   else:self.ret(0)
  elif a==0x081ff040:self.ret(1)
  elif a==0x0812d80e and 501<=r[1]<517:self.w(r[2],self.cells[r[1]-501]);self.ret(1)
  elif a==0x0813130c:self.dirty+=1;self.ret()
  elif a==0x08133df8:self.w(r[1],80);self.ret(1)
  elif a==0x08139138:self.refresh+=1;self.ret()
  elif a==0x08173272:self.ui.append(bytes(u.mem_read(r[1],20)));self.ret()
  elif a==0x0810b5c8:return # Actual native packet writer, not a command substitute.
  else:super().hook(u,a,size,data)
 def request(self,pad,context=501,valid=True):
  sp=0x20030000;vals=[254,0x314d5442 if valid else 0,context,pad,9,0x31525442]
  self.u.mem_write(sp+0x220,struct.pack('<6I',*vals))
  before=[0x1010+i for i in range(13)];before[4:8]=[self.m,254,context,pad]
  for reg,v in zip(REGS,before):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x20035001)
  self.u.emu_start(CONSUMER|1,0,count=50000)
  self.assert_end=(self.u.reg_read(UC_ARM_REG_SP)==sp)
  if self.u.reg_read(UC_ARM_REG_PC)==0x0813f990:before[3]=254-17
  assert [self.u.reg_read(r) for r in REGS]==before
 def value(self,pad):
  self.u.reg_write(UC_ARM_REG_R0,self.cells[pad]);self.u.reg_write(UC_ARM_REG_R1,0x1e0)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000);self.u.reg_write(UC_ARM_REG_LR,0x0813f2fd)
  self.u.emu_start(0x0812dc75,0,count=1000);return self.u.reg_read(UC_ARM_REG_R0)
 def packet(self,i=0):return struct.unpack('<6I',self.u.mem_read(self.engine+24*i,24))
 def screen(self,pad,value):
  ptr=0x2002a000;self.u.mem_write(ptr,struct.pack('<5I',0xcf,501+pad,0x1e0,value,0))
  self.u.reg_write(UC_ARM_REG_R0,self.m);self.u.reg_write(UC_ARM_REG_R1,ptr)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000);self.u.reg_write(UC_ARM_REG_LR,0x0813f2fd)
  self.u.emu_start(0x0813bfb1,0,count=50000)

class Tests(unittest.TestCase):
 def test_receiver_all_sixteen_pads_create_one_silent_mute_request(self):
  for pad in range(16):
   p=DrumInput();levels=[0]*16;levels[pad]=1000;p.packet(0x100,levels)
   self.assertEqual(p.events(),[]);self.assertEqual(p.custom(),[(254,0x314d5442,501,pad,9,0x31525442)])
 def test_receiver_pressure_and_both_release_orders_are_consumed(self):
  for proj_first in [False,True]:
   p=DrumInput();p.packet(0x100,[1000]+[0]*15);p.packet(0x100,[1500]+[0]*15)
   self.assertEqual(p.custom(),[]);self.assertEqual(p.events(),[])
   if proj_first:p.packet(0,[1500]+[0]*15);self.assertEqual(p.events(),[])
   p.packet(0 if proj_first else 0x100);self.assertEqual(p.events(),[])
   self.assertEqual(p.readword(0x24048ca4)&65535,0)
 def test_receiver_other_pages_preserve_proj_pad_for_native_and_lock_clear(self):
  for page in [0x27,0x17,2,9,0x14,31]:
   p=DrumInput(page);p.packet(0x100,[1000]+[0]*15)
   self.assertEqual(p.custom(),[]);self.assertEqual(p.events(),[(172,0,1000),(174,0,1000)])
 def test_receiver_note_started_before_proj_gets_normal_note_off(self):
  p=DrumInput();p.packet(0,[1000]+[0]*15);p.packet(0x100,[1500]+[0]*15)
  self.assertEqual(p.custom(),[]);p.packet(0x100);self.assertEqual(p.events(),[(173,0,0),(174,0,0)])
 def test_full_queue_silences_shifted_press_without_overwrite_and_releases_cleanly(self):
  from test_input import UIQUEUE
  p=DrumInput();p.packet(0x100);p.word(UIQUEUE+0x21a0,225);p.word(UIQUEUE+0x2180,1)
  before=bytes(p.u.mem_read(UIQUEUE+0x980,256*24));p.packet(0x100,[1000]+[0]*15)
  self.assertEqual(p.custom(),[]);self.assertEqual(p.events(),[]);self.assertEqual(p.readword(0x24048ca8),1)
  self.assertEqual(bytes(p.u.mem_read(UIQUEUE+0x980,256*24)),before)
  p.packet();self.assertEqual(p.events(),[]);self.assertEqual(p.readword(0x24048ca4)&65535,0)
 def test_native_all_pad_toggles_update_model_engine_and_screen_notification(self):
  for pad in range(16):
   f=Mute();f.request(pad);self.assertTrue(f.assert_end);self.assertEqual(f.value(pad),1)
   self.assertEqual(f.packet()[:5],(0x3e,0,501+pad,0x1e0,1))
   self.assertEqual(struct.unpack('<5I',f.ui[-1]),(0xc3,501+pad,0x1e0,1,0))
   self.assertEqual(f.dirty,1);self.assertEqual(f.refresh,1);self.assertEqual(f.contexts(),[501,80,33,44])
   f.request(pad);self.assertEqual(f.value(pad),0);self.assertEqual(f.packet(1)[4],0)
 def test_touchscreen_and_shortcut_alternate_the_same_native_state(self):
  f=Mute();f.screen(12,1);self.assertEqual(f.value(12),1)
  f.request(12);self.assertEqual(f.value(12),0)
  f.screen(12,1);self.assertEqual(f.value(12),1)
  self.assertEqual([f.packet(i)[4] for i in range(3)],[1,0,1])
 def test_scope_and_stale_context_requests_do_not_change_other_views_or_instruments(self):
  for page,kind,context,pad in [(0x27,14,501,0),(7,17,501,0),(7,14,502,0),(7,14,501,16)]:
   f=Mute();f.page(page);f.kind=kind;f.request(pad,context)
   self.assertEqual(f.r(f.engine+0x620),0);self.assertEqual(f.ui,[])
 def test_native_audio_property_dispatch_uses_existing_per_sound_mute_byte(self):
  p=AudioProbe();root=0x20010000;sp=0x2003e000
  for value in [1,0,1]:
   p.w(sp+0x38,value);p.u.reg_write(UC_ARM_REG_R4,root);p.u.reg_write(UC_ARM_REG_R3,0x1e0);p.u.reg_write(UC_ARM_REG_SP,sp)
   p.u.emu_start(0x08091047,0x0808e9e0,count=1000)
   self.assertEqual(bytes(p.u.mem_read(root+0x600,1)),bytes([value]))

if __name__=='__main__':unittest.main(verbosity=2)
