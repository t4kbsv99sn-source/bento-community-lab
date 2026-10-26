"""Standalone ARM adapter -> real native note IDs, containers and publish path.
Model/owner lookup, Undo storage and engine queue are controlled fixtures.
No claim of hardware playback or installed UI hooks.
"""
import os,sys,struct,json,ctypes as C,unittest,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'eu4_work/integration'))
from test_euclidean import Probe,note
from test_chords import Progression,generate
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
OUT=Path(os.environ['BENTO_CHORD_BUILD']);SYMS=json.loads((OUT/'symbols.json').read_text());KEEP=[]
class Native(Probe):
 def __init__(self,steps=16,notes=None):
  super().__init__(steps=steps,notes=notes or []);KEEP.append(self);self.type=18
  self.u.mem_write(int(os.environ.get('BENTO_CHORD_TEST_ORIGIN','0x081e0000'),0),(OUT/'chords.bin').read_bytes());self.state=0x20026000;self.phrase=0x20027000
  self.u.mem_write(self.state,struct.pack('<4I',self.seq,self.owner,self.steps*960,0)+bytes(388));self.u.mem_write(self.phrase,bytes(generate()))
 def native(self,u,a,n,d):
  if a==0x08133f7c:
   ptr=u.reg_read(UC_ARM_REG_R1);self.ret(getattr(self,'type',14) if self.r(ptr)==self.owner else 24)
  else:super().native(u,a,n,d)
 def insert(self,p=None):
  if p is not None:self.u.mem_write(self.phrase,bytes(p))
  return self.call(SYMS['chord_native_insert'],self.state,self.model,self.phrase)
class Tests(unittest.TestCase):
 def test_insert_native_pitch_velocity_time_ids_and_one_undo(self):
  p=Native();phrase=generate();self.assertEqual(p.insert(phrase),0);events=p.events();self.assertEqual(len(events),12);self.assertEqual(len(p.undo),1);self.assertEqual(p.undo[0][0],[])
  self.assertEqual(p.r(p.project+0x68),10012);self.assertEqual(p.r(p.state+400),12)
  for e in events:self.assertEqual(e[0],1);self.assertEqual(struct.unpack_from('<H',e,2)[0],0);self.assertEqual(struct.unpack_from('<H',e,18)[0],100);self.assertEqual(struct.unpack_from('<I',e,20)[0],0)
  first=[struct.unpack_from('<H',e,16)[0] for e in events if struct.unpack_from('<I',e,4)[0]==0];self.assertEqual(sorted(first),[48,52,55]);self.assertEqual(len(p.commands),12)
  self.assertEqual({struct.unpack_from('<I',c,12)[0] for c in p.commands},set(range(10000,10012)));self.assertIn((0xc7,77,0,0,0),p.notifications)
 def test_existing_notes_and_lock_payloads_are_unchanged(self):
  e=note(0,ident=300,vel=31,lock=0x51030010);p=Native(notes=[e]);self.assertEqual(p.insert(),0);self.assertIn(e,p.events());self.assertEqual(p.undo[0][0],[e])
 def test_overlap_refuses_entire_insert_but_adjacent_note_is_allowed(self):
  e=struct.pack('<BBHIIIHHI',1,0,0,0,960,300,48,100,0);p=Native(notes=[e]);before=p.events();self.assertEqual(p.insert(),4);self.assertEqual(p.events(),before);self.assertFalse(p.undo)
  phrase=generate(start=960,duration=960);self.assertEqual(p.insert(phrase),0)
 def test_full_clip_stale_context_wrong_track_and_bad_ids_are_atomic(self):
  for cause in ['capacity','owner','seq','length','type','ids','heap']:
   p=Native(notes=[note(i%16,pad=1,ident=i+1) for i in range(500)] if cause=='capacity' else [])
   before=p.events()
   if cause=='owner':p.owner+=1
   if cause=='seq':p.w(p.model+0x144,999)
   if cause=='length':p.steps=32
   if cause=='type':p.type=14
   if cause=='ids':p.w(p.project+0x68,0)
   if cause=='heap':p.w(0x30000048,p.r(0x3000004c)+8)
   self.assertNotEqual(p.insert(),0,cause);self.assertEqual(p.events(),before,cause);self.assertFalse(p.undo,cause);self.assertFalse(p.commands,cause)
 def test_strummed_native_events_keep_matching_pitch_and_id(self):
  p=Native();phrase=generate();phrase.count=1;phrase.chords[0].strum=-120;self.assertEqual(p.insert(phrase),0)
  self.assertEqual(sorted((struct.unpack_from('<H',e,16)[0],struct.unpack_from('<I',e,4)[0]) for e in p.events()),[(48,240),(52,120),(55,0)])
  self.assertEqual(len({struct.unpack_from('<I',e,12)[0] for e in p.events()}),3)
 def test_scratch_is_reused_without_another_bump_allocation(self):
  p=Native();phrase=generate(duration=960);self.assertEqual(p.insert(phrase),0);cursor=p.r(0x3000004c)
  phrase=generate(start=3840,duration=960);self.assertEqual(p.insert(phrase),0);self.assertEqual(p.r(0x3000004c),cursor);self.assertEqual(len(p.undo),2)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
