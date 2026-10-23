"""Two-lock codec, native note transport, editor migration, and shared sends."""
import unittest,struct,random
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_editable_locks import UIProbe,VoiceProbe,word as oldword
from test_l4 import flt
from step_locks import A_SYMS,U_SYMS
N=[1,1081,48001,2001,2001]+[1001]*7

def word(k,v):return oldword(k,v) if k<4 else 0x51000000|(k<<16)|(v+1000 if k==4 else v)
def pair(a,b):
 ka=(a>>16)&255 if a else 0;kb=(b>>16)&255 if b else 0
 if ka and ka==kb:return 0xffffffff
 if not kb:return a
 at=0
 for i in range(12):
  for j in range(12):
   if i==j and i:continue
   if (i,j)==(ka,kb):return 0x80000000+at+(a&65535)*N[j]+(b&65535)
   at+=N[i]*N[j]
 raise AssertionError()

class SendProbe(VoiceProbe):
 def __init__(self):
  super().__init__();self.seq=0x20020000;self.router=0x20030000;self.route_queue=self.queue
  self.w(self.seq+12,80);self.w(self.seq+0x14,3);self.u.mem_write(self.seq+0x20,b'\1')
  self.w(self.seq+0x86c0,77);self.w(self.seq+0x86dc+8,101)
  self.w(self.router+0x508,2);self.w(self.router+4,self.queue)
  self.w(self.router+8,101);self.w(self.router+12,0)
  self.w(self.router+16,0xfffffffc);self.w(self.router+20,1)
  self.f(self.root+0x608,.1);self.f(self.root+0x60c,.2)
 def payload(self,w):
  self.u.mem_write(self.packet,bytes(24));self.u.mem_write(self.packet,b'\x12');self.w(self.packet+8,101)
  self.w(self.packet+12,60);self.w(self.packet+16,100)
  self.call(A_SYMS['lock_pending'],w);self.call(A_SYMS['lock_route'],self.seq,self.router,2)
  self.call(0x08065600,self.queue,self.packet);self.call(A_SYMS['lock_pending'],0)
  out=0x20013000;self.call(0x080655a0,self.queue,0,out);raw=bytes(self.u.mem_read(out,24))
  self.call(A_SYMS['lock_note'],self.root,out);self.w(self.queue+0x600,0);return raw
 def begin(self):self.call(A_SYMS['sends_begin'],self.root)
 def end(self):self.call(A_SYMS['sends_end'],self.root)

class Tests(unittest.TestCase):
 def test_codec_all_ordered_target_pairs_at_range_edges_are_lossless(self):
  p=UIProbe();total=0
  for a in range(12):
   for b in range(12):
    if a and a==b:continue
    total+=N[a]*N[b]
    for va,vb in [(0,0),(N[a]-1,N[b]-1),(N[a]//2,N[b]//2)]:
     x=0x51000000|(a<<16)|va if a else 0;y=0x51000000|(b<<16)|vb if b else 0
     expected=pair(x,y);p.call(U_SYMS['locks_pack'],x,y);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),expected)
     for i,w in [(0,x),(1,y)]:p.call(U_SYMS['locks_slot'],expected,i);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),w)
  self.assertEqual(total,1290761893);self.assertLess(total,2**31)
 def test_codec_random_native_precision_and_invalid_payloads(self):
  p=UIProbe();rng=random.Random(17)
  for _ in range(300):
   a,b=rng.sample(range(1,12),2);x=0x51000000|(a<<16)|rng.randrange(N[a]);y=0x51000000|(b<<16)|rng.randrange(N[b])
   packed=pair(x,y)
   for i,w in [(0,x),(1,y)]:p.call(U_SYMS['locks_slot'],packed,i);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),w)
  for value in [0xffffffff,0x80000000+1519176901,0x12345678]:
   for i in [0,1]:p.call(U_SYMS['locks_slot'],value,i);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_sixth_registry_slot_is_free_in_complete_native_constructor(self):
  from test_plock import AudioProbe
  p=AudioProbe()
  def alloc(u,a,s,d):
   if a==0x08104c08:u.reg_write(UC_ARM_REG_R0,0x20020000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  p.u.hook_add(UC_HOOK_CODE,alloc);p.call(0x081639a8,0)
  for k in [0x1da,0x1e4]:self.assertEqual(bytes(p.u.mem_read(0x20020000+k*32,32)),bytes(32))
 def test_two_encoders_edit_independently_on_the_same_hit(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.encoder(0x32,-500)
  self.assertEqual(p.stored(),pair(word(1,-18000),word(4,-500)))
  p.encoder(2,-9000);self.assertEqual(p.stored(),pair(word(1,-9000),word(4,-500)))
  p.display();self.assertIn(('value',2,-9000),p.screen);self.assertIn(('value',0x32,-500),p.screen)
 def test_target_pick_on_encoder_six_and_remove_only_that_slot(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.shift();p.encoder(0x1e4,3);p.shift(False);p.encoder(4,750)
  self.assertEqual(p.stored(),pair(word(1,-18000),word(3,750)))
  p.shift();p.encoder(0x1e4,0);p.shift(False);self.assertEqual(p.stored(),word(1,-18000))
 def test_remove_first_preserves_second_only_lock(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.encoder(0x32,-500)
  p.shift();p.encoder(0x1da,0);p.shift(False);self.assertEqual(p.stored(),pair(0,word(4,-500)))
 def test_old_l6_lock_loads_into_encoder_five_without_changing_value(self):
  p=UIProbe();p.xml={'bento_lock1_v1':word(2,7001)};p.call(U_SYMS['locks_load'],0x20027000,p.container)
  self.assertEqual(p.stored(),word(2,7001));p.press(0);p.display()
  self.assertIn(('value',3,7001),p.screen);self.assertIn(('caption','--'),p.screen)
 def test_two_xml_attributes_round_trip_and_clearing_overwrites_old_attributes(self):
  p=UIProbe();w=pair(word(2,7001),word(11,750));p.w(p.container+20,w)
  p.call(U_SYMS['locks_save'],0x20027000,p.container)
  self.assertEqual(p.xml,{'bento_lock1_v1':word(2,7001),'bento_lock2_v1':word(11,750)})
  p.w(p.container+20,0);p.call(U_SYMS['locks_load'],0x20027000,p.container);self.assertEqual(p.stored(),w)
  p.w(p.container+20,0);p.call(U_SYMS['locks_save'],0x20027000,p.container);p.call(U_SYMS['locks_load'],0x20027000,p.container)
  self.assertEqual(p.stored(),0);self.assertEqual(p.xml,{'bento_lock1_v1':0,'bento_lock2_v1':0})
 def test_duplicate_saved_target_drops_second_and_ui_refuses_duplicate(self):
  p=UIProbe();p.xml={'bento_lock1_v1':word(1,-6000),'bento_lock2_v1':word(1,-12000)}
  p.call(U_SYMS['locks_load'],0x20027000,p.container);self.assertEqual(p.stored(),word(1,-6000))
  p.press(0);p.shift();p.encoder(0x1e4,1);self.assertEqual(p.stored(),word(1,-6000));p.display()
  self.assertIn(('caption','Target already used'),p.screen)
 def test_proj_pad_clears_both_locks_without_toggling_the_hit(self):
  p=UIProbe();p.w(p.container+20,pair(word(1,-6000),word(11,900)));before=bytes(p.u.mem_read(p.container,20))
  p.w(0x24048d68,1);p.shift();p.press(0);p.time(5100);p.release(0);p.shift(False)
  self.assertEqual(p.stored(),0);self.assertEqual(bytes(p.u.mem_read(p.container,20)),before);self.assertNotIn(('toggle',0),p.log)
 def test_two_locks_survive_native_cross_core_queue_and_event_store(self):
  p=SendProbe();w=pair(word(2,7001),word(3,-751));record=0x20014000;out=record+0x100;interface=0x20028000
  raw=bytearray(48);raw[0]=1;struct.pack_into('<I',raw,20,w);raw[24]=1
  p.u.mem_write(record,bytes(raw));p.call(0x0810b960,interface,record);p.call(0x08082340,interface,out)
  self.assertEqual(bytes(p.u.mem_read(out,48)),bytes(raw))
 def test_two_locks_reach_same_native_voice_and_reused_voice_clears_both(self):
  p=SendProbe();w=pair(word(1,-30000),word(3,-750));raw=p.payload(w)
  self.assertEqual(raw[1],0xb7);self.assertEqual(struct.unpack_from('<I',raw,20)[0],w)
  p.voice_start(w);self.assertAlmostEqual(p.evaluate(p.voice+0x180),.5);self.assertAlmostEqual(p.evaluate(p.voice+0x1c0),-.75)
  p.voice_start(0);self.assertAlmostEqual(p.evaluate(p.voice+0x180),.8);self.assertAlmostEqual(p.evaluate(p.voice+0x1c0),0)
 def test_old_tail_keeps_both_values_after_different_new_hit(self):
  p=SendProbe();p.voice_start(pair(word(1,-30000),word(3,-750)))
  p.voice_start(pair(word(1,-6000),word(3,750)),p.voice+0x800)
  self.assertAlmostEqual(p.evaluate(p.voice+0x180),.5);self.assertAlmostEqual(p.evaluate(p.voice+0x1c0),-.75)
  self.assertAlmostEqual(p.evaluate(p.voice+0x980),.9);self.assertAlmostEqual(p.evaluate(p.voice+0x9c0),.75)
 def test_extended_payload_does_not_overwrite_midi_forwarding_tail_word(self):
  p=SendProbe();p.call(A_SYMS['lock_pending'],pair(word(1,-30000),word(3,-750)));p.call(A_SYMS['lock_route'],p.seq,p.router,2)
  p.u.mem_write(p.packet,bytes(24));p.u.mem_write(p.packet,b'\x12');p.w(p.packet+8,101);p.w(p.packet+20,0x12345678)
  p.call(0x08065600,p.queue+0x604,p.packet)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(p.queue+0x604+20,4))[0],0x12345678)
 def test_delay_and_reverb_both_apply_for_step_and_restore_native_values(self):
  p=SendProbe();before=bytes(p.u.mem_read(p.root+0x608,8));p.payload(pair(word(10,1000),word(11,0)))
  p.begin();self.assertAlmostEqual(p.f(p.root+0x608),1);self.assertEqual(p.f(p.root+0x60c),0)
  self.assertEqual(p.u.mem_read(p.root+0x624,1),b'\1');p.end()
  self.assertEqual(bytes(p.u.mem_read(p.root+0x608,8)),before);self.assertEqual(p.u.mem_read(p.root+0x624,1),b'\0')
 def test_send_expires_on_next_empty_step_without_requiring_another_hit(self):
  p=SendProbe();p.payload(word(11,1000));p.begin();self.assertAlmostEqual(p.f(p.root+0x60c),1);p.end()
  p.w(p.seq+0x14,4);p.begin();self.assertAlmostEqual(p.f(p.root+0x60c),.2);p.end()
 def test_send_expires_on_one_step_loop_when_next_pass_has_no_trigger(self):
  p=SendProbe();counter=0x24048a60
  for offset,value in [(0,p.seq),(4,80),(8,77),(12,0)]:p.w(counter+offset,value)
  p.payload(word(10,1000));p.begin();self.assertAlmostEqual(p.f(p.root+0x608),1);p.end()
  p.w(counter+12,1);p.begin();self.assertAlmostEqual(p.f(p.root+0x608),.1);p.end()
 def test_send_cancels_on_stop_clip_owner_or_row_change(self):
  for offset,value in [(0x20,0),(12,81),(0x86c0,78)]:
   p=SendProbe();p.payload(word(10,1000))
   if offset==0x20:p.u.mem_write(p.seq+offset,b'\0')
   else:p.w(p.seq+offset,value)
   p.begin();self.assertAlmostEqual(p.f(p.root+0x608),.1)
 def test_background_send_changes_remain_live_between_render_overrides(self):
  p=SendProbe();p.payload(word(10,1000));p.begin();p.end();p.f(p.root+0x608,.3)
  p.begin();self.assertAlmostEqual(p.f(p.root+0x608),1);p.end();self.assertAlmostEqual(p.f(p.root+0x608),.3)
 def test_voice_lock_and_send_lock_both_operate_without_changing_root_level(self):
  p=SendProbe();p.voice_start(pair(word(1,-30000),word(11,1000)));base=p.f(p.root+0x134)
  self.assertAlmostEqual(p.evaluate(p.voice+0x180),.5);p.begin();self.assertAlmostEqual(p.f(p.root+0x60c),1)
  self.assertEqual(p.f(p.root+0x134),base);p.end()
 def test_native_send_conversion_matches_original_property_gain_scale(self):
  p=SendProbe()
  for value in [0,100,500,999,1000]:
   p.u.reg_write(UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',value/1000))[0]);p.call(0x080503e0);expected=flt(p.u,UC_ARM_REG_S0)
   p.call(0x080d33c0,value);actual=struct.unpack('<f',struct.pack('<I',p.u.reg_read(UC_ARM_REG_R0)))[0]
   self.assertAlmostEqual(actual,expected,places=6);self.assertGreaterEqual(actual,0);self.assertLessEqual(actual,1)
 def test_native_render_wrappers_preserve_registers_and_restore_at_both_exits(self):
  from test_controls import REGS
  for exit,stop in [(0x0808ed22,0x0808ed26),(0x0808fcc2,0x0808fcc6)]:
   p=SendProbe();p.payload(word(10,1000));sp=0x2003e000
   before=[0x1100+i for i in range(13)];before[4]=p.root;before[5]=0x20027000
   for reg,value in zip(REGS,before):p.u.reg_write(reg,value)
   for i in range(32):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*100)
   p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_APSR,0xa0000000)
   p.u.emu_start(0x0808fc41,0x0808fc44,count=100000)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x0808fc44);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
   before[8]=before[5]+0xe1c
   self.assertEqual([p.u.reg_read(r) for r in REGS],before)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_APSR)&0xf8000000,0xa0000000)
   self.assertAlmostEqual(p.f(p.root+0x608),1)
   for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*100)
   p.u.emu_start(exit|1,stop,count=100000)
   before[0]=1;self.assertEqual([p.u.reg_read(r) for r in REGS],before)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp+0x44)
   self.assertAlmostEqual(p.f(p.root+0x608),.1)
   for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*100)
 def test_actual_native_accepted_note_generator_carries_both_locks(self):
  p=SendProbe();p.u.mem_write(p.seq+0x10,struct.pack('<H',101));p.u.mem_write(p.seq+0x86d2,b'\1')
  sp=0x2003e000;w=pair(word(2,7001),word(11,900))
  p.w(sp,2);p.w(sp+4,p.router);p.w(sp+0x3c,w)
  for r,v in [(UC_ARM_REG_R0,p.seq),(UC_ARM_REG_R1,60),(UC_ARM_REG_R2,100),(UC_ARM_REG_R3,0),(UC_ARM_REG_SP,sp)]:p.u.reg_write(r,v)
  p.u.emu_start(0x08060b9b,0x08060b9e,count=100000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x08060b9e);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
  raw=bytes(p.u.mem_read(p.queue,24));self.assertEqual(raw[:2],b'\x12\xb7')
  self.assertEqual(struct.unpack_from('<I',raw,20)[0],w)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24046004,4))[0],0)

 def test_new_send_state_is_cleared_on_m7_startup(self):
  p=SendProbe();p.u.mem_write(0x24044000,b'\xa5'*0x4000);p.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  p.u.emu_start(0x080d0801,0x080404ba,count=30000)
  self.assertEqual(bytes(p.u.mem_read(0x24044000,0x4000)),bytes(0x4000))

if __name__=='__main__':unittest.main(verbosity=2)
