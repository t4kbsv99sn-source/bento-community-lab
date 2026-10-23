"""EU1 compiled code, real native note containers/IDs/delete/publish routines.
Undo allocation, model properties, UI services and engine queue are fixtures.
"""
import unittest,struct,random,hashlib
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE,K16_IMAGE
EU=0x24041f6c
KEYS=[0x190,0x191,0x192,0x193,0x194,0x195]
def note(step,pad=2,ident=1,vel=90,cond=0,lock=0,offset=0,kind=1):
 return struct.pack('<BBHIIIHHI',kind,cond,pad,(step*960+offset)&0xffffffff,960,ident,0,vel,lock)
class Probe(Fixture):
 def __init__(self,steps=16,notes=None):
  super().__init__();self.steps=steps;self.owner=80;self.seq=77;self.pad=2;self.undo=[];self.commands=[];self.notifications=[]
  self.project=0x20002000;self.track=0x20003000;self.object=0x20004000;self.vtable=0x20005000
  self.node=0xc0040000;self.container=self.node+12;self.seqview=0xc0060000;self.model=0x30024b00
  self.w(self.model,self.project);self.w(self.project,self.track);self.w(self.project+0x30,1);self.w(self.project+0x68,10000)
  self.w(self.track,self.vtable);self.w(self.vtable+0x14,0x081ff181);self.w(self.object+0x14,self.node)
  self.u.mem_write(self.node+8,b'\x02');self.w(0x3000004c,self.next);self.w(0x30000048,0xc0200000)
  self.w(self.model+0x13c,101);self.w(self.model+0x140,102);self.w(self.model+0x144,self.seq);self.w(self.model+0x148,103)
  self.u.mem_write(self.model+0x12c,b'\x27');self.setnotes(notes if notes is not None else [note(0,ident=101),note(4,pad=3,ident=102)])
  for a in [0x081ff180,0x08133cfc,0x08133f7c,0x0812dca2,0x081338dc,0x0810b960,0x08173272]:
   self.u.hook_add(UC_HOOK_CODE,self.native,begin=a,end=a)
  self.call(UU['fx_dispatch'],self.model,0xaf,0,11) # initializes private UI state
  self.prepare()
 def native(self,u,a,n,d):
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x081ff180:
   if r[1]==self.seq:self.w(r[2],self.object);self.ret(1)
   else:self.ret(0)
  elif a==0x08133cfc:self.w(r[1],self.owner);self.ret(1)
  elif a==0x08133f7c:self.ret(14 if self.r(r[1])==self.owner else 24)
  elif a==0x0812dca2:
   if r[1]==self.seq and r[2] in [0x62,0x73]:self.w(r[3],self.steps if r[2]==0x62 else 0);self.ret(1)
   else:self.ret(0)
  elif a==0x081338dc:self.undo.append((self.events(),self.r(self.project+0x68)));self.ret()
  elif a==0x0810b960:self.commands.append(bytes(u.mem_read(r[1],48)));self.ret()
  elif a==0x08173272:self.notifications.append(tuple(self.r(r[1]+i*4) for i in range(5)));self.ret()
 def hook(self,u,a,n,d):
  if a==0x08104c08 and not self.force_registry:
   size=u.reg_read(UC_ARM_REG_R0);p=self.r(0x3000004c);self.w(0x3000004c,p+((size+31)&~31));self.ret(p);return
  super().hook(u,a,n,d)
 def setnotes(self,notes):
  self.u.mem_write(self.container,b''.join(notes));self.w(self.container+0x3000,len(notes))
 def events(self):return [bytes(self.u.mem_read(self.container+i*24,24)) for i in range(self.r(self.container+0x3000))]
 def prepare(self):
  for off,val in [(0x113dc,self.container),(0x113e4,self.seq),(0x113e8,self.owner),(0x11400,self.pad),(0x113f8,self.steps)]:self.w(self.seqview+off,val)
  self.call(UU['eu_view_capture'],self.seqview)
 def config(self,hits,rotate=0,vel=100):
  self.w(EU+16,hits);self.w(EU+20,rotate);self.w(EU+24,vel)
 def apply(self):return self.call(UU['eu_apply'],EU,self.model)
 def open_eu(self):
  self.registry()
  def nav(u,a,n,d):self.navlog.append(u.reg_read(UC_ARM_REG_R1));self.ret()
  self.u.hook_add(UC_HOOK_CODE,nav,begin=0x081420ec,end=0x081420ec)
  for code,t in [(0xaf,1000),(0xb0,1050),(0xaf,1200)]:
   self.w(0x3001fe2c,t);self.call(UU['fx_dispatch'],self.model,code,0,11)
  self.view=0xc0000000;self.call(0x08145b7c,self.view);arg=0x20016000;self.w(arg,42);self.call(0x08145efc,self.view,arg)
  return self.view
class Tests(unittest.TestCase):
 def test_pattern_counts_rotation_balanced_gaps_and_edge_cases_on_arm(self):
  p=Probe(notes=[]);rng=random.Random(904)
  for steps,hits in [(1,0),(1,1),(16,0),(16,16),(16,5),(7,3),(256,127)]+[(rng.randint(1,256),-1) for _ in range(20)]:
   if hits<0:hits=rng.randint(0,steps)
   rotate=rng.randrange(steps)
   pattern=[p.call(UU['eu_hit'],i,steps,hits,rotate) for i in range(steps)]
   self.assertEqual(sum(pattern),hits)
   if hits:
    positions=[i for i,x in enumerate(pattern) if x];gaps=[(positions[(i+1)%hits]-positions[i])%steps or steps for i in range(hits)]
    self.assertLessEqual(max(gaps)-min(gaps),1)
   for i in [0,steps-1]:self.assertEqual(pattern[i],p.call(UU['eu_hit'],(i-rotate)%steps,steps,hits,0))
  self.assertEqual(p.call(UU['eu_hit'],0,0,0,0),0);self.assertEqual(p.call(UU['eu_hit'],0,257,5,0),0)
 def test_capture_counts_unique_selected_notes_and_respects_clip_length(self):
  p=Probe(notes=[note(0,ident=1),note(0,ident=2),note(4,ident=3),note(8,pad=3,ident=4),note(30,ident=5)])
  self.assertEqual(p.r(EU+16),2);self.assertEqual(p.r(EU+12),16)
 def test_replace_only_selected_pad_retains_full_existing_hit_metadata(self):
  locked=note(0,ident=11,vel=44,cond=103,lock=0x510c0005,offset=20)
  other=note(3,pad=5,ident=13,lock=0x51030010);outside=note(20,ident=14)
  p=Probe(notes=[locked,note(1,ident=12),other,outside]);p.config(4)
  self.assertEqual(p.apply(),0);events=p.events();self.assertIn(locked,events);self.assertIn(other,events);self.assertIn(outside,events)
  self.assertNotIn(note(1,ident=12),events)
  target=[struct.unpack_from('<I',n,4)[0]//960 for n in events if n[2:4]==b'\x02\x00' and struct.unpack_from('<I',n,4)[0]<16*960]
  self.assertEqual(sorted(target),[0,4,8,12]);self.assertEqual(len(p.undo),1)
 def test_new_hits_have_native_ids_always_velocity_and_no_locks(self):
  p=Probe(notes=[]);p.config(5,rotate=2,vel=75);self.assertEqual(p.apply(),0)
  events=p.events();self.assertEqual(len(events),5);self.assertEqual(p.r(p.project+0x68),10005)
  for i,n in enumerate(events):
   self.assertEqual(n[0:2],b'\x01\x00');self.assertEqual(struct.unpack_from('<I',n,12)[0],10000+i)
   self.assertEqual(struct.unpack_from('<HHI',n,16),(0,75,0))
  self.assertEqual([c[24] for c in p.commands],[1]*5)
  for c,n in zip(p.commands,events):self.assertEqual(c[:24],n)
  self.assertIn((0xc7,77,0,0,0),p.notifications)
 def test_clear_selected_pad_sends_native_delete_and_one_snapshot(self):
  p=Probe();p.config(0);before=p.events();self.assertEqual(p.apply(),0)
  self.assertEqual(p.events(),[before[1]]);self.assertEqual(len(p.undo),1);self.assertEqual(p.commands[0][24],2)
  self.assertEqual(p.undo[0][0],before)
 def test_no_change_avoids_allocation_and_undo(self):
  p=Probe(notes=[note(0,ident=1),note(8,ident=2)]);p.config(2);cursor=p.r(0x3000004c)
  self.assertEqual(p.apply(),5);self.assertEqual(p.r(0x3000004c),cursor);self.assertEqual(p.undo,[])
 def test_capacity_preflight_refuses_entire_apply(self):
  p=Probe(notes=[note(i%16,pad=3,ident=i+1) for i in range(511)]);before=p.events();p.config(1)
  self.assertEqual(p.apply(),2);self.assertEqual(p.events(),before);self.assertEqual(p.undo,[])
 def test_deletion_can_make_room_before_creating_new_hits(self):
  p=Probe(notes=[note(0,ident=1)]+[note(i%16,pad=3,ident=i+2) for i in range(510)]);p.config(1,rotate=1)
  self.assertEqual(p.apply(),0);self.assertEqual(len(p.events()),511);self.assertEqual(len(p.undo),1)
 def test_native_bump_allocator_is_checked_and_reused(self):
  p=Probe(notes=[]);p.config(4);self.assertEqual(p.apply(),0);cursor=p.r(0x3000004c);self.assertNotEqual(p.r(EU+32),0)
  p.config(2);self.assertEqual(p.apply(),0);self.assertEqual(p.r(0x3000004c),cursor)
 def test_low_memory_and_stale_or_invalid_context_leave_notes_untouched(self):
  for fail in ['heap','owner','length','ids','hits']:
   p=Probe();p.config(5);before=p.events()
   if fail=='heap':p.w(0x30000048,p.r(0x3000004c)+8)
   if fail=='owner':p.owner=81
   if fail=='length':p.steps=32
   if fail=='ids':p.w(p.project+0x68,0)
   if fail=='hits':p.w(EU+16,17)
   self.assertIn(p.apply(),[1,3,4],fail);self.assertEqual(p.events(),before);self.assertEqual(p.undo,[],fail)
 def test_real_native_generic_page_has_preview_and_encoder_edits_only_preview(self):
  p=Probe();before=p.events();v=p.open_eu();self.assertEqual(p.navlog,[0x1a])
  self.assertEqual(bytes(p.u.mem_read(v+0x93c4,1)),b'\x02')
  self.assertIn('Pad 3 / 16 steps',p.text(p.r(v+0x93c8)))
  p.event(KEYS[0],5);p.event(KEYS[1],2);p.event(KEYS[2],65)
  self.assertEqual(p.value(KEYS[0]),5);self.assertEqual(p.events(),before)
  self.assertIn('X',p.text(p.r(v+0x93cc)));self.assertEqual(p.undo,[])
 def test_apply_from_native_widget_event_returns_to_seq_and_preserves_context(self):
  p=Probe();p.open_eu();p.event(KEYS[0],4);p.event(KEYS[4],1)
  self.assertEqual(p.navlog[-1],0x27);self.assertEqual(p.r(p.model+0x144),77)
  self.assertEqual(len(p.undo),1);self.assertEqual(len([n for n in p.events() if n[2:4]==b'\x02\x00']),4)
 def test_cancel_changes_nothing_and_return_is_context_aware(self):
  p=Probe();p.open_eu();before=p.events();p.event(KEYS[0],12);p.event(KEYS[5],1)
  self.assertEqual(p.navlog[-1],0x27);self.assertEqual(p.events(),before);self.assertEqual(p.undo,[])
 def test_double_tap_needs_seq_capture_and_cannot_mix_tracks_and_seq_taps(self):
  p=Probe();p.registry();p.w(EU+36,0)
  for code,t in [(0xaf,1000),(0xb0,1050),(0xaf,1200)]:
   p.w(0x3001fe2c,t);result=p.call(UU['fx_dispatch'],p.model,code,0,11)
  self.assertEqual(result,0)
  p=Probe();p.registry()
  for index,code,t in [(2,0xaf,1000),(2,0xb0,1050),(11,0xaf,1200)]:
   p.w(0x3001fe2c,t);result=p.call(UU['fx_dispatch'],p.model,code,0,index)
  self.assertEqual(result,0)
 def test_preview_window_and_registry_ownership(self):
  p=Probe(steps=256,notes=[]);p.open_eu();p.event(KEYS[0],128);p.event(KEYS[3],8)
  self.assertTrue(p.text(p.r(p.view+0x93cc)).startswith('225: '))
  registry=p.r(0x30031484)
  for key in KEYS:self.assertEqual(p.r(registry+key*32)&65535,key)
 def test_sequence_capture_is_chained_before_actual_native_header_adapter(self):
  # Enter the actual patched site; stop before the inherited header implementation.
  p=Probe();p.w(EU+36,0);p.u.reg_write(UC_ARM_REG_R0,p.seqview);p.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  p.u.emu_start(0x0815c27d,0x081b7008,count=100000)
  self.assertEqual(p.r(EU+36),1);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),p.seqview)
 def test_m7_image_and_native_automation_processing_are_identical_to_tf2(self):
  self.assertEqual(hashlib.sha256(IMAGE[:0xc0000]).hexdigest(),'748bcbc3e9c338d46f592fed438e31e1190f043c0a2f0e5aa78484ecdec8859c')
if __name__=='__main__':unittest.main(verbosity=2)
