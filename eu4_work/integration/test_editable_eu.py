"""EU6 native notes are generated, edited through native APIs, then sounded by M7.
Project lookup/undo allocation/engine queue are fixtures; native note mutation,
selected-note reading, velocity edit and ARM playback run on the candidate.
"""
import unittest,struct,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_live import Live,UU,EU,EC,note
class Edit(Live):
 def __init__(self,notes=None):
  super().__init__(notes=notes)
  self.u.hook_add(UC_HOOK_CODE,self.ui,begin=0x0815c27c,end=0x0815c27c)
  self.u.hook_add(UC_HOOK_CODE,self.ui,begin=0x0815c4b8,end=0x0815c4b8)
  self.u.hook_add(UC_HOOK_CODE,self.bubble,begin=0x0816fc34,end=0x0816fc34)
  self.w(self.seqview+0x113fc,6);self.messages=[]
  self.u.hook_add(UC_HOOK_CODE,self.no_synth,begin=0x081bb080,end=0x081bb080)
  self.w(0x30031484,0xc00c0000)
 def bubble(self,u,a,n,d):
  ptr=u.reg_read(UC_ARM_REG_R1);code=struct.unpack('<H',u.mem_read(ptr,2))[0]
  if code in [0xe7,0xe9]:self.messages.append(struct.unpack('<5I',u.mem_read(ptr,20)))
  self.ret()
 def tap(self,step):
  # Stock view produces the real E7/E9 message; model-parent routing is a
  # fixture using the same native bulk-note APIs as the generator.
  self.messages=[];self.call(0x0815d114,self.seqview,step)
  temp=0xc00e0000;handle=0x2002c000;raw=0x2002c100;self.w(handle,self.seq)
  for message in self.messages:
   self.call(0x0810d16c,temp)
   if message[0]&65535==0xe7:
    event=next(e for e in self.events() if struct.unpack_from('<I',e,12)[0]==message[2])
    self.u.mem_write(raw,event);self.call(0x0810d176,temp,raw);self.call(0x08136fb4,self.model,handle,temp)
   else:
    event=struct.pack('<6I',1|(message[3]<<16),message[2],message[4],0,100<<16,0)
    self.u.mem_write(raw,event);self.call(0x081338dc,self.model,handle)
    ident=self.call(0x0812e070,self.project,self.seq,raw);self.w(raw+12,ident)
    self.call(0x0810d176,temp,raw);self.call(0x08136544,self.model,handle,temp)
 def no_synth(self,*args):self.ret(0)
 def ui(self,*args):self.ret()
 def generate(self,key,value):return self.call(UU['live_generate'],EU,key,value)
 def sync(self):
  cursor=self.clip+8;indices=0xc00a0000;arena=0xc00a1000;records=0xc00a2000;events=self.events()
  self.w(cursor,indices);self.w(cursor+4,len(events));self.w(cursor+8,0);self.w(cursor+16,arena);self.w(arena,records)
  self.u.mem_write(indices,struct.pack('<%dH'%len(events),*range(len(events))))
  if events:self.u.mem_write(records,b''.join(events))
 def generated(self,n=7,k=3):
  assert self.generate(1,n);assert self.generate(2,k);self.prepare();self.w(self.seqview+0x113f8,n);self.sync()
 def select(self,step):
  self.w(0x30035f40,5000);self.call(0x0815d1ec,self.seqview,step)
  out=0x2002c000;ok=self.call(0x0815ba04,self.seqview,out);return ok,bytes(self.u.mem_read(out,24))
class Tests(unittest.TestCase):
 def test_native_generation_keeps_other_drums_and_creates_real_editable_notes(self):
  p=Edit();other=[e for e in p.events() if struct.unpack_from('<H',e,2)[0]==3];p.generated()
  selected=[e for e in p.events() if struct.unpack_from('<H',e,2)[0]==2]
  self.assertEqual([struct.unpack_from('<I',e,4)[0]//960 for e in selected],[0,3,5])
  self.assertEqual([e for e in p.events() if struct.unpack_from('<H',e,2)[0]==3],other)
  ok,event=p.select(3);self.assertEqual(ok,1);self.assertEqual(struct.unpack_from('<I',event,4)[0],3*960)
 def test_native_tap_add_and_remove_affect_next_generated_cycle(self):
  p=Edit(notes=[]);p.generated()
  p.tap(0);p.tap(1);p.sync();p.across(7)
  steps=[round(time/6000) for pad,time in p.absolute if pad==2]
  self.assertEqual(steps[:3],[1,3,5])
 def test_native_velocity_and_step_lock_reach_generated_note(self):
  p=Edit(notes=[]);p.generated();p.select(3);p.call(0x0815c7c4,p.seqview,43)
  lock=0x5101030c
  p.call(UU['locks_header_before'],p.seqview);p.call(UU['locks_encoder'],p.seqview,2,(-18000)&0xffffffff)
  p.sync();p.across(7)
  hit=[i for i,(pad,time) in enumerate(p.absolute) if pad==2 and round(time/6000)==3][0]
  self.assertEqual(p.hits()[hit][2],43);self.assertEqual(p.locktrace[hit],lock)
 def test_regeneration_preserves_retained_step_values_and_shrink_removes_outside_notes(self):
  lock=0x5101030c;p=Edit(notes=[note(0,pad=2,ident=101,vel=37,lock=lock),note(20,pad=2,ident=102)])
  self.assertEqual(p.generate(1,7),1);self.assertEqual(p.generate(2,3),1)
  hit=[e for e in p.events() if struct.unpack_from('<I',e,4)[0]==0][0]
  self.assertEqual(struct.unpack_from('<H',hit,18)[0],37);self.assertEqual(struct.unpack_from('<I',hit,20)[0],lock)
  self.assertTrue(all(struct.unpack_from('<I',e,4)[0]<7*960 for e in p.events()))
 def test_global_velocity_updates_native_notes_in_one_gesture(self):
  p=Edit(notes=[]);p.generated();before=len(p.undo);self.assertEqual(p.generate(4,74),1)
  self.assertEqual([struct.unpack_from('<H',e,18)[0] for e in p.events()],[74]*3);self.assertEqual(len(p.undo),before+1)
 def test_capacity_failure_changes_neither_notes_nor_generator_settings(self):
  p=Edit(notes=[note(0,pad=3,ident=i+1) for i in range(511)]);before=p.events();self.assertEqual(p.generate(2,1),0)
  self.assertEqual(p.events(),before);out=0x2002c000;p.call(UU['live_value'],out,EU);self.assertEqual((p.r(out)>>26)&1,0)
 def test_manual_freezes_edited_notes_and_disables_duplicate_suppression(self):
  p=Edit(notes=[]);p.generated();before=p.events();self.assertEqual(p.generate(5,0),1)
  self.assertEqual(p.events(),before);self.assertEqual(p.call(UU['live_begin'],EU),1)
 def test_per_drum_lengths_remain_independent_with_native_templates(self):
  p=Edit(notes=[]);p.generated(7,3);p.w(EU+8,3);p.pad=3;self.assertEqual(p.generate(1,5),1);self.assertEqual(p.generate(2,2),1);p.sync();p.across(35)
  a=[round(t/6000) for pad,t in p.absolute if pad==2];b=[round(t/6000) for pad,t in p.absolute if pad==3]
  self.assertEqual(a[:6],[0,3,5,7,10,12]);self.assertEqual(b[:6],[0,3,5,8,10,13])
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
