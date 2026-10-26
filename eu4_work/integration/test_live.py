"""EU2 real native timing conversion and note routing; model/XML/queues fixtures."""
import unittest,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_euclidean import Probe,EU,note
from test_integration import AA,UU,IMAGE
KEYS=list(range(0x190,0x198));EC=0x24041fc0
class Live(Probe):
 def __init__(self,notes=None):
  super().__init__(notes=notes);self.clock=0x20028000;self.audioseq=0xc0080000;self.router=0xc0090000;self.clip=self.audioseq+0x240;self.emitted=[];self.locktrace=[];self.absolute=[];self.block=0;self.currentrow=0
  self.w(self.audioseq+12,self.owner);self.u.mem_write(self.audioseq+0x20,b'\x01');self.w(self.audioseq+0x14,0)
  self.w(self.audioseq+0x86c0,self.clip);self.w(self.clip+0x20,0);self.w(self.clip,10);self.u.mem_write(self.clip+0x38,b'\x01');self.u.mem_write(self.audioseq+0x86d2,b'\x01')
  self.f(self.clock+0x18,120);self.f(self.clock+0x14c,.5)
  for i in range(16):self.w(self.audioseq+0x86dc+i*4,1000+i)
  self.u.hook_add(UC_HOOK_CODE,self.route,begin=0x0809f040,end=0x0809f040)
 def native(self,u,a,n,d):
  if a==0x0812dca2 and u.reg_read(UC_ARM_REG_R2)==0x73:
   self.w(u.reg_read(UC_ARM_REG_R3),getattr(self,'currentrow',0));self.ret(1);return
  super().native(u,a,n,d)
 def route(self,u,a,n,d):
  p=u.reg_read(UC_ARM_REG_R1);packet=bytes(u.mem_read(p,24))
  if u.reg_read(UC_ARM_REG_R2)!=0xfffffffc:
   self.emitted.append(packet);self.locktrace.append(self.r(0x24046004));self.absolute.append((struct.unpack_from('<I',packet,8)[0]-1000,self.block+struct.unpack_from('<I',packet,4)[0]))
  self.ret()
 def start(self):return self.call(UU['live_begin'],EU)
 def edit(self,key,value):return self.call(UU['live_edit'],EU,key,value)
 def setpad(self,pad,length,hits,rotate=0,velocity=100,on=1):
  assert self.start();self.edit(0,pad+1)
  for key,v in [(1,length),(2,hits),(3,rotate),(4,velocity),(5,on)]:assert self.edit(key,v)
 def frame(self,tick):
  p=0x2002f000;self.u.mem_write(p,struct.pack('<q',tick));return self.call(0x080a2200,self.clock,p)
 def render(self,start,frames=1024):
  self.block=start;self.w(self.clock,start);self.call(AA['live_render'],self.audioseq,self.clock,0,frames,self.router)
 def hits(self):return [(struct.unpack_from('<I',p,8)[0]-1000,struct.unpack_from('<I',p,4)[0],struct.unpack_from('<I',p,16)[0]) for p in self.emitted if p[0]==0x12 and 1000<=struct.unpack_from('<I',p,8)[0]<1016]
 def across(self,steps):
  for start in range(0,self.frame(steps*240),1024):self.render(start)
class Tests(unittest.TestCase):
 def test_real_native_c6_allocator_pool_is_readable_by_audio_generator(self):
  p=Live();p.u.mem_map(0xc6000000,0x20000)
  p.w(0x3000004c,0xc6000000);p.w(0x30000048,0xc6020000)
  p.setpad(0,7,3);self.assertEqual(p.r(EC+4),0xc6000000)
  p.across(16);self.assertGreater(len(p.hits()),0)

 def test_native_clock_maps_sixteenths_at_120_bpm(self):
  p=Live();self.assertEqual(p.frame(240),6000);self.assertEqual(p.frame(16*240),96000)
 def test_independent_seven_and_sixteen_step_patterns_continue_across_clip_wrap(self):
  p=Live();p.setpad(0,16,4);p.setpad(1,7,3)
  for start in range(0,p.frame(48*240),1024):
   if start>=96000:p.w(p.clip+0x20,16*240) # native clip start advances; phase must not reset
   p.render(start,min(1024,48*6000-start))
  times={0:[],1:[]}
  for pad,offset,vel in p.hits():times[pad].append(offset)
  self.assertEqual(len(times[0]),12);self.assertEqual(len(times[1]),21)
  actual={pad:[t//6000 for pnum,t in p.absolute if pnum==pad] for pad in [0,1]}
  self.assertEqual(actual[0],list(range(0,48,4)))
  self.assertEqual(actual[1],[i for i in range(48) if (i%7*3)%7<3])
 def test_live_edit_changes_next_step_without_rewriting_notes(self):
  p=Live();before=p.events();p.setpad(2,16,0);p.render(0);self.assertEqual(p.hits(),[])
  p.edit(2,16);p.render(6000);self.assertEqual(len(p.hits()),1);self.assertEqual(p.hits()[0][0],2)
  self.assertEqual(p.events(),before);self.assertEqual(p.undo,[])
 def test_native_hits_suppressed_only_for_enabled_pad_then_return_when_disabled(self):
  p=Live();p.setpad(2,7,3);p.render(0)
  self.assertEqual(p.call(AA['live_skip'],p.audioseq,2),1);self.assertEqual(p.call(AA['live_skip'],p.audioseq,3),0)
  p.edit(5,0);p.render(1024);self.assertEqual(p.call(AA['live_skip'],p.audioseq,2),0)
 def test_stop_and_clip_switch_stop_old_generator(self):
  p=Live();p.setpad(2,7,7);p.render(0);before=len(p.hits());p.u.mem_write(p.audioseq+0x20,b'\0');p.render(6000)
  self.assertEqual(len(p.hits()),before);self.assertEqual(p.call(AA['live_skip'],p.audioseq,2),0)
  p.u.mem_write(p.audioseq+0x20,b'\1');p.w(p.audioseq+0x86c0,p.clip+0x848);p.render(12000);self.assertEqual(len(p.hits()),before)
 def test_launch_resets_phase_but_normal_loop_does_not(self):
  p=Live();p.setpad(2,7,3);p.render(0);p.w(p.audioseq+0x14,15);p.call(AA['live_restart'],p.audioseq)
  bank=p.r(EC+4);runtime=bank+32+128*160*2;self.assertNotEqual(p.r(runtime+8),0)
  p.w(p.audioseq+0x14,0xffffffff);p.call(AA['live_restart'],p.audioseq);self.assertEqual(p.r(runtime+8),0)
 def test_low_memory_refuses_before_native_fatal_allocator(self):
  p=Live();p.w(0x30000048,p.r(0x3000004c)+32);self.assertEqual(p.start(),0);self.assertEqual(p.r(EC),0)
 def test_xml_roundtrip_and_missing_settings_clear_previous_project(self):
  p=Live();p.setpad(2,7,3,2,88);obj=0x20024000;p.u.mem_write(obj+4,b'\x0e');p.w(obj+0x10,80)
  p.call(UU['live_save'],obj,0x20017000);saved=dict(p.attrs);self.assertEqual(saved['bento_eu2_version'],1)
  p.call(UU['live_finish']);p.call(UU['live_load'],0x20025000,obj);p.call(UU['live_finish'])
  ptr=0x20026000;p.call(UU['live_value'],ptr,EU) # struct result uses hidden pointer under ARM ABI
  self.assertEqual(p.r(ptr+4),88)
  self.assertEqual(p.r(ptr)&255,6);self.assertEqual((p.r(ptr)>>8)&511,3)
  p.attrs={};p.call(UU['live_load'],0x20025000,obj);p.call(UU['live_finish']);p.call(UU['live_value'],ptr,EU)
  self.assertEqual((p.r(ptr)>>25)&1,0)

 def test_patched_renderer_forwards_fifth_argument_and_preserves_native_registers(self):
  p=Live();p.setpad(2,7,7);sp=0x2003e000
  for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],[p.audioseq,p.clock,0,1024]):p.u.reg_write(reg,val)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff001);p.w(sp,p.router)
  p.u.reg_write(UC_ARM_REG_S6,0x3fc00000)
  p.u.emu_start(0x08060821,0x08060824,count=100000)
  self.assertEqual(len(p.hits()),1);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),p.audioseq)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R1),p.clock);self.assertEqual(p.u.reg_read(UC_ARM_REG_S6),0x3fc00000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-36)
 def test_patched_gate_skips_generator_pad_and_chains_old_condition_gate_for_other_pads(self):
  for pad,target in [(2,0x080609e2),(3,0x080d2000)]:
   p=Live();p.setpad(2,7,3);p.render(0);sp=0x2003e000;p.u.reg_write(UC_ARM_REG_SP,sp)
   p.u.reg_write(UC_ARM_REG_R8,p.audioseq);p.u.mem_write(sp+0x2a,struct.pack('<H',pad))
   p.u.emu_start(0x08060b65,target,count=100000);self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),target)
   self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
 def test_live_settings_are_distinct_per_pad_and_clip(self):
  p=Live();p.setpad(2,7,3);p.setpad(3,16,4,1,75)
  pointer=0x20026000;p.edit(0,3);p.call(UU['live_value'],pointer,EU);self.assertEqual(p.r(pointer)&255,6)
  p.edit(0,4);p.call(UU['live_value'],pointer,EU);self.assertEqual(p.r(pointer)&255,15);self.assertEqual(p.r(pointer+4),75)
 def test_torn_record_falls_back_without_silencing_native_notes(self):
  p=Live();p.setpad(2,7,3);p.render(0);bank=p.r(EC+4);p.w(bank+32,p.r(bank+32)|1);p.render(1024)
  self.assertEqual(p.call(AA['live_skip'],p.audioseq,2),0)
 def test_repeated_enable_edits_reuse_one_allocation(self):
  p=Live();p.setpad(2,7,3);cursor=p.r(0x3000004c)
  for _ in range(10):p.edit(2,4);p.edit(2,3);p.edit(5,0);p.edit(5,1)
  self.assertEqual(p.r(0x3000004c),cursor)
 def test_corrupt_xml_disables_generator_instead_of_loading_invalid_parameters(self):
  p=Live();p.attrs={'bento_eu2_version':1,'bento_eu2_00_02_0':0xffffffff,'bento_eu2_00_02_1':100}
  obj=0x20024000;p.u.mem_write(obj+4,b'\x0e');p.w(obj+0x10,80)
  p.call(UU['live_load'],0x20025000,obj);p.call(UU['live_finish']);self.assertEqual(p.r(EC),0x324c5545)
  pointer=0x20026000;p.call(UU['live_value'],pointer,EU);self.assertEqual((p.r(pointer)>>25)&1,0)
 def test_two_clip_rows_have_their_own_settings_and_launch_phase(self):
  p=Live();p.setpad(2,7,3);p.currentrow=1;p.setpad(2,16,4,0,77)
  nextclip=p.clip+0x848;p.w(nextclip,10);p.w(nextclip+0x20,16*240)
  p.w(p.audioseq+0x86c0,nextclip);p.render(96000)
  self.assertEqual(p.hits(),[(2,0,77)])
  p.currentrow=0;pointer=0x20026000;p.call(UU['live_value'],pointer,EU)
  self.assertEqual(p.r(pointer)&255,6);self.assertEqual(p.r(pointer+4),100)
 def test_native_step_size_changes_the_generator_cadence(self):
  p=Live();p.setpad(2,16,16);p.w(p.clip,8) # eighth notes: 480 native clock ticks
  p.render(0);p.render(6000);self.assertEqual(len(p.hits()),1)
  p.render(12000);self.assertEqual(len(p.hits()),2)
 def test_repeated_audio_block_does_not_duplicate_generated_hits(self):
  p=Live();p.setpad(2,7,7);p.render(0);p.render(0);self.assertEqual(len(p.hits()),1)
 def test_generated_hits_take_existing_step_locks_and_preserve_native_cursor(self):
  p=Live();p.setpad(2,7,7);cursor=p.clip+8;indices=0xc00a0000;arena=0xc00a1000;records=0xc00a2000
  p.w(cursor,indices);p.w(cursor+4,2);p.w(cursor+8,1);p.w(cursor+16,arena);p.w(arena,records)
  p.u.mem_write(indices,b'\0\0\1\0');lock=0x51140050
  p.u.mem_write(records,note(0,pad=2,ident=500,lock=lock)+note(1,pad=3,ident=501,lock=0x51030010))
  before=bytes(p.u.mem_read(cursor,24));p.render(0);self.assertEqual(p.locktrace,[lock]);self.assertEqual(p.r(0x24046004),0)
  self.assertEqual(bytes(p.u.mem_read(cursor,24)),before);p.render(6000);self.assertEqual(p.locktrace,[lock,0])
 def test_lock_cycle_position_repeats_across_clip_boundary(self):
  p=Live();p.setpad(2,7,7);cursor=p.clip+8;indices=0xc00a0000;arena=0xc00a1000;records=0xc00a2000
  p.w(cursor,indices);p.w(cursor+4,1);p.w(cursor+16,arena);p.w(arena,records);p.u.mem_write(indices,b'\0\0')
  lock=0x510d0049;p.u.mem_write(records,note(2,pad=2,ident=500,lock=lock))
  for start in range(0,20*6000,1024):p.render(start,min(1024,20*6000-start))
  self.assertEqual([i for i,w in enumerate(p.locktrace) if w==lock],[2,9,16])
if __name__=='__main__':unittest.main(verbosity=2)
