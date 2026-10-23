"""Native step edits + note storage + accepted-note/voice lock adapters.
Synthetic UI model and sample voices; full display/filesystem remain device checks.
"""
import unittest,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_holdstep import HoldProbe
from test_plock import AudioProbe
from step_locks import A_SYMS,U_SYMS

TAG=0x51000000

def word(k,value):return TAG|(k<<16)|(int((value+96000)/100) if k==1 else value+24000 if k==2 else value+1000)

class UIProbe(HoldProbe):
 def __init__(self):
  super().__init__();self.page=0x30024b00;self.u.mem_write(self.page+0x12c,b'\x27')
  self.w(self.view+0x113e8,80);self.w(0x30031484,0x20029000)
  self.screen=[];self.xml={};self.xml_value=None;self.parent_type=14;self.bg={2:-6000,3:0,4:0}
  self.u.hook_add(UC_HOOK_CODE,self.extra)
  self.prepare()
 def extra(self,u,a,size,data):
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x08133f7c:self.ret(self.parent_type if r[1]==self.view+0x113e8 else 1)
  elif a==0x0813391a:
   if r[2]==0:self.w(r[3],101);self.ret(1)
   else:self.ret(0)
  elif a==0x08133614:
   self.w(r[3],2 if r[2]==0x73 else self.bg.get(r[2],0));self.ret(1)
  elif a==0x08171c1c:self.screen.append(('value',r[1],r[2] if r[2]<0x80000000 else r[2]-0x100000000));self.ret()
  elif a in [0x0817e85e,0x08170656]:
   ptr=r[1] if a==0x0817e85e else r[2];self.screen.append(('title' if a==0x0817e85e else 'caption',self.text(ptr)));self.ret()
  elif a in [0x08109cdc,0x08109c64]:
   self.xml_key=self.text(r[1]);self.ret(0x20028000 if a==0x08109cdc or self.xml_key in self.xml else 0)
  elif a==0x0810958e:self.xml[self.xml_key]=r[1];self.ret()
  elif a==0x08109566:self.w(r[1],self.xml[self.xml_key]);self.ret(0)
 def text(self,a):return bytes(self.u.mem_read(a,100)).split(b'\0')[0].decode()
 def prepare(self):self.call(U_SYMS['locks_header_before'],self.view)
 def display(self):self.prepare();self.call(U_SYMS['locks_header_after'],self.view);return self.screen[-3:]
 def shift(self,down=True):self.call(0x081b8c00,self.page,int(down));self.prepare()
 def encoder(self,key,value):self.call(0x0815caa0,self.view,key,value&0xffffffff)
 def stored(self,index=0):return self.word(self.container+index*24+20)

class VoiceProbe(AudioProbe):
 def __init__(self):
  super().__init__();self.root=0x20010000;self.voice=0x20018000;self.packet=0x20012000;self.queue=0x20015000
  self.w(self.root,0x080ac66c);self.w(self.root+12,101);self.w(self.root+0x104,0)
  for off in [0x138,0x178,0x2b8]:
   p=self.root+off;self.init_parameter(p);self.f(p-4,.8 if off==0x138 else 0)
   self.base_source(p,p-8)
   self.f(p+0x34,-4 if off==0x2b8 else -1 if off==0x178 else 0)
   self.f(p+0x38,4 if off==0x2b8 else 1.1875 if off==0x138 else 1)
 def payload(self,w):
  self.u.mem_write(self.packet,bytes(24));self.u.mem_write(self.packet,b'\x12');self.w(self.packet+8,101)
  self.call(A_SYMS['lock_pending'],w);self.call(0x08065600,self.queue,self.packet);self.call(A_SYMS['lock_pending'],0)
  out=0x20013000;self.call(0x080655a0,self.queue,0,out)
  self.call(A_SYMS['lock_note'],self.root,out)
  self.w(self.queue+0x600,0)
  return bytes(self.u.mem_read(out,24))
 def voice_start(self,w,voice=None):
  voice=voice or self.voice;self.payload(w)
  for a,b in [(0x138,0x180),(0x178,0x1c0),(0x2b8,0x300)]:self.u.mem_write(voice+b,bytes(self.u.mem_read(self.root+a,64)))
  self.call(A_SYMS['lock_voice'],voice,self.root);return voice
 def fragment(self,start,stop,voice=None):
  self.u.reg_write(UC_ARM_REG_R4,voice or self.voice);self.u.reg_write(UC_ARM_REG_R5,self.root)
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000);self.u.emu_start(start|1,stop,count=20000)
  assert self.u.reg_read(UC_ARM_REG_PC)==stop

class Tests(unittest.TestCase):
 def test_native_registry_has_free_picker_slot_and_native_target_ranges(self):
  p=AudioProbe()
  def allocator(u,a,s,d):
   if a==0x08104c08:
    u.reg_write(UC_ARM_REG_R0,0x20020000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  p.u.hook_add(UC_HOOK_CODE,allocator);p.call(0x081639a8,0)
  self.assertEqual(bytes(p.u.mem_read(0x20020000+0x1da*32,32)),bytes(32))
  for key,lo,hi in [(2,-96000,12000),(3,-24000,24000),(4,-1000,1000)]:
   self.assertEqual(struct.unpack('<ii',p.u.mem_read(0x20020000+key*32+16,8)),(lo,hi))
 def test_actual_native_accepted_note_route_carries_lock_and_clears_pending(self):
  p=VoiceProbe();seq=0x20020000;router=0x20030000;queue=0x20015000
  p.w(router+0x508,1);p.w(router+4,queue);p.w(router+8,101);p.w(router+12,0)
  p.u.mem_write(seq+0x10,struct.pack('<H',101));p.u.mem_write(seq+0x86d2,b'\1')
  p.w(seq+0x86dc+2*4,101)
  sp=0x2003e000;w=word(2,7000)
  p.w(sp,2);p.w(sp+4,router);p.w(sp+0x3c,w)
  for reg,val in [(UC_ARM_REG_R0,seq),(UC_ARM_REG_R1,60),(UC_ARM_REG_R2,100),(UC_ARM_REG_R3,0),(UC_ARM_REG_SP,sp)]:p.u.reg_write(reg,val)
  p.u.emu_start(0x08060b9b,0x08060b9e,count=30000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x08060b9e)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
  raw=bytes(p.u.mem_read(queue,24));self.assertEqual(raw[0:4],bytes([0x12,2,w&255,(w>>8)&255]))
  self.assertEqual(struct.unpack_from('<I',raw,8)[0],101)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24046004,4))[0],0)
 def test_actual_native_sound_dispatch_extracts_the_queued_lock(self):
  p=VoiceProbe();record=p.payload(word(3,500));sp=0x2003e000
  p.u.mem_write(sp+0x28,record);p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_R4,p.root)
  p.u.emu_start(0x0808e9f1,0x0808e9f4,count=30000)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x2404600c,4))[0],word(3,500))
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R3),0x12)
 def test_project_release_after_navigation_does_not_leave_target_mode_stuck(self):
  p=UIProbe();p.shift();p.u.mem_write(p.page+0x12c,b'\x07');p.shift(False)
  self.assertEqual(p.word(0x24048014),0)
 def test_native_audio_event_store_and_reader_keep_lock_word(self):
  p=VoiceProbe();cursor=0x20020000;indices=cursor+0x100;arena=cursor+0x200;records=cursor+0x1000
  p.w(cursor,indices);p.w(cursor+4,1);p.w(cursor+8,0);p.w(cursor+16,arena);p.w(arena,records)
  event=bytearray(24);event[0]=1;struct.pack_into('<IIII',event,4,0,960,77,0)
  p.u.mem_write(records,bytes(event));p.u.mem_write(indices,b'\0\0')
  new=0x20014000;struct.pack_into('<I',event,20,word(2,5000));p.u.mem_write(new,bytes(event))
  p.call(0x080961a0,cursor,new)
  out=new+0x100;p.call(0x08095da0,cursor,out)
  self.assertEqual(bytes(p.u.mem_read(out,24)),bytes(event))
 def test_native_cross_core_note_queue_keeps_the_extension_word(self):
  p=VoiceProbe();interface=0x20020000;record=0x20014000;out=record+0x100
  raw=bytearray(48);raw[0]=1;struct.pack_into('<I',raw,20,word(3,-500));raw[24]=1
  p.u.mem_write(record,bytes(raw));p.call(0x0810b960,interface,record)
  p.call(0x08082340,interface,out)
  self.assertEqual(bytes(p.u.mem_read(out,48)),bytes(raw))
 def test_startup_clears_new_audio_and_ui_regions_with_separate_ownership(self):
  p=VoiceProbe();p.u.mem_write(0x24046000,b'\xa5'*0x2800)
  p.u.reg_write(UC_ARM_REG_SP,0x2003e000);p.u.emu_start(0x080d0801,0x080404ba,count=20000)
  self.assertEqual(bytes(p.u.mem_read(0x24046000,0x2000)),bytes(0x2000))
  self.assertEqual(bytes(p.u.mem_read(0x24048000,0x800)),b'\xa5'*0x800)
  p.u.reg_write(UC_ARM_REG_SP,0x2003e000);p.u.emu_start(0x081b5201,0x081004ba,count=20000)
  self.assertEqual(bytes(p.u.mem_read(0x24048000,0x800)),bytes(0x800))
 def test_xml_adapters_use_the_real_native_stack_event_and_preserve_registers(self):
  p=UIProbe();sp=0x2003e000
  for a,stop,off in [(0x0812f4f0,0x0812f4f4,8),(0x0812fbb4,0x0812fbb8,0x24)]:
   event=bytearray(24);event[0]=1;struct.pack_into('<I',event,20,word(2,-5000))
   p.xml['bento_lock1_v1']=word(2,-5000)
   p.u.mem_write(sp+off,bytes(event));p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_R4,0x20027000)
   p.u.emu_start(a|1,stop,count=30000)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),stop)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
   self.assertEqual(p.word(sp+off+20),word(2,-5000))
  self.assertEqual(p.xml['bento_lock1_v1'],word(2,-5000))
 def test_real_step_value_edit_is_separate_from_velocity_condition_offset(self):
  p=UIProbe();p.press(0);before=bytes(p.u.mem_read(p.container,72));p.encoder(2,-18000)
  self.assertEqual(p.stored(),word(1,-18000));self.assertEqual(p.stored(1),0)
  after=bytes(p.u.mem_read(p.container,72));self.assertEqual(before[:20],after[:20]);self.assertEqual(before[24:],after[24:])
  p.time(5100);p.release(0);self.assertNotIn(('toggle',0),p.log)
 def test_inspected_step_can_be_edited_after_release(self):
  p=UIProbe();p.press(8);p.time(6500);p.release(8);p.encoder(2,-12000)
  self.assertEqual(p.stored(1),word(1,-12000));self.assertEqual(p.stored(),0)
 def test_empty_or_unselected_steps_do_not_create_locks(self):
  p=UIProbe();before=bytes(p.u.mem_read(p.container,72));p.encoder(2,-12000)
  self.assertEqual(bytes(p.u.mem_read(p.container,72)),before)
  p.press(4);p.encoder(2,-12000);self.assertEqual(bytes(p.u.mem_read(p.container,72)),before)
 def test_shift_uses_native_target_enum_and_suppresses_project_tap(self):
  p=UIProbe();p.shift();p.encoder(0x1da,2);p.shift(False);p.display()
  self.assertEqual(p.word(0x24048d6c),1)
  self.assertIn(('value',3,0),p.screen);self.assertIn(('title','Lock Pitch'),p.screen)
  p.press(0);p.encoder(3,7000);self.assertEqual(p.stored(),word(2,7000))
 def test_pan_target_preserves_signed_native_units(self):
  p=UIProbe();p.shift();p.encoder(0x1da,3);p.shift(False);p.press(0);p.encoder(4,-750)
  self.assertEqual(p.stored(),word(3,-750));p.display();self.assertIn(('value',4,-750),p.screen)
 def test_target_choice_does_not_change_a_lock_until_value_is_edited(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.shift();p.encoder(0x1da,2)
  self.assertEqual(p.stored(),word(1,-18000))
  p.shift(False);p.encoder(3,7000);self.assertEqual(p.stored(),word(2,7000))
 def test_remove_choice_clears_only_selected_hit(self):
  p=UIProbe();p.press(0);p.encoder(2,-18000);p.time(6500);p.release(0)
  p.press(8);p.encoder(2,-12000);p.shift();p.encoder(0x1da,0);p.shift(False)
  self.assertEqual(p.stored(),word(1,-18000));self.assertEqual(p.stored(1),0)
 def test_multi_selection_sets_same_value_on_existing_selected_hits(self):
  p=UIProbe();p.press(0);p.press(8);p.encoder(2,-24000)
  self.assertEqual(p.stored(),word(1,-24000));self.assertEqual(p.stored(1),word(1,-24000));self.assertEqual(p.stored(2),0)
 def test_unlocked_value_is_blank_but_starts_from_background(self):
  p=UIProbe();p.press(0);p.display()
  self.assertIn(('value',2,-6000),p.screen);self.assertIn(('caption','--'),p.screen)
 def test_native_note_xml_round_trip_and_missing_damaged_values(self):
  p=UIProbe();e=p.container;p.w(e+20,word(3,-750));native=bytes(p.u.mem_read(e,20))
  p.call(U_SYMS['locks_save'],0x20027000,e);self.assertEqual(p.xml['bento_lock1_v1'],word(3,-750))
  p.w(e+20,0);p.call(U_SYMS['locks_load'],0x20027000,e);self.assertEqual(p.stored(),word(3,-750));self.assertEqual(bytes(p.u.mem_read(e,20)),native)
  for v in [0,0xffffffff,0x511e0000,0x5101ffff]:
   p.xml['bento_lock1_v1']=v;p.call(U_SYMS['locks_load'],0x20027000,e);self.assertEqual(p.stored(),0)
  p.xml.clear();p.call(U_SYMS['locks_load'],0x20027000,e);self.assertEqual(p.stored(),0)
 def test_native_queue_preserves_lock_header_and_other_note_fields(self):
  p=VoiceProbe();w=word(2,7000);record=p.payload(w)
  self.assertEqual(record[0],0x12);self.assertEqual(record[1:4],bytes([2,w&255,(w>>8)&255]));self.assertEqual(struct.unpack_from('<I',record,8)[0],101)
 def test_level_lock_hits_new_voice_only_and_old_tail_keeps_its_value(self):
  p=VoiceProbe();p.voice_start(word(1,-30000));first=p.evaluate(p.voice+0x180)
  p.voice_start(word(1,-6000),p.voice+0x800)
  self.assertAlmostEqual(p.evaluate(p.voice+0x180),first,places=6)
  self.assertAlmostEqual(first,.5,places=6);self.assertAlmostEqual(p.evaluate(p.voice+0x980),.9,places=6)
  self.assertAlmostEqual(p.evaluate(p.root+0x138),.8,places=6)
 def test_pan_lock_and_normal_reused_voice(self):
  p=VoiceProbe();p.voice_start(word(3,-750));self.assertAlmostEqual(p.evaluate(p.voice+0x1c0),-.75,places=6)
  p.voice_start(0);self.assertAlmostEqual(p.evaluate(p.voice+0x1c0),0,places=6)
 def test_pitch_lock_compensates_native_base_pitch(self):
  p=VoiceProbe();p.w(p.root+0x104,2000);p.voice_start(word(2,7000))
  self.assertAlmostEqual(p.evaluate(p.voice+0x300),5/12,places=6)
 def test_pitch_bend_remains_live_on_a_locked_hit(self):
  p=VoiceProbe();p.f(p.root+0x2b4,.1);p.voice_start(word(2,7000))
  self.assertAlmostEqual(p.evaluate(p.voice+0x300),7/12+.1,places=6)
  p.f(p.root+0x2b4,-.1);self.assertAlmostEqual(p.evaluate(p.voice+0x300),7/12-.1,places=6)
 def test_native_voice_initialization_hooks_attach_even_without_a_copy(self):
  for start,stop in [(0x08093cda,0x08093cde),(0x08094ade,0x08094ae2)]:
   p=VoiceProbe();p.voice_start(0);p.payload(word(1,-18000));p.fragment(start,stop)
   self.assertAlmostEqual(p.evaluate(p.voice+0x180),.7,places=6)
 def test_background_automation_stays_live_and_other_modulation_affects_lock(self):
  p=VoiceProbe();src=0x20014000;auto=src+16
  p.f(src+4,.05);p.f(auto+4,.1);p.mod_source(p.root+0x138,src,0);p.mod_source(p.root+0x138,auto,3)
  p.voice_start(word(1,-30000));before=bytes(p.u.mem_read(p.root+0x138,60))
  self.assertAlmostEqual(p.evaluate(p.voice+0x180),.55,places=6)
  p.f(auto+4,.2);p.f(p.root+0x134,.6);self.assertAlmostEqual(p.evaluate(p.voice+0x180),.55,places=6)
  p.voice_start(0,p.voice+0x800);self.assertAlmostEqual(p.evaluate(p.voice+0x980),.85,places=6)
  self.assertEqual(bytes(p.u.mem_read(p.root+0x138,60)),before)
 def test_copied_source_change_disables_stale_voice_entry(self):
  p=VoiceProbe();p.voice_start(word(1,-30000));p.f(0x20014004,.3);p.base_source(p.voice+0x180,0x20014000)
  self.assertAlmostEqual(p.evaluate(p.voice+0x180),.3,places=6)
 def test_voice_hash_collisions_and_reuse_keep_other_tails_independent(self):
  p=VoiceProbe();voices=[p.voice+i*0x800 for i in range(24)]
  for i,v in enumerate(voices):p.voice_start(word(1,-30000+i*500),v)
  for i,v in enumerate(voices):self.assertAlmostEqual(p.evaluate(v+0x180),.5+i/120,places=6)
  for v in voices[::2]:p.voice_start(0,v)
  for i,v in enumerate(voices):self.assertAlmostEqual(p.evaluate(v+0x180),.8 if i%2==0 else .5+i/120,places=6)
 def test_repeated_voice_target_changes_do_not_leave_tombstones_or_stale_locks(self):
  p=VoiceProbe()
  for i in range(80):
   k=i%3+1;p.voice_start(word(k,-12000 if k==1 else 7000 if k==2 else -500))
  p.voice_start(0)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24046010,4))[0],0)
  self.assertEqual([struct.unpack('<I',p.u.mem_read(0x24046020+j*20,4))[0] for j in range(256)],[0]*256)

if __name__=='__main__':unittest.main(verbosity=2)
