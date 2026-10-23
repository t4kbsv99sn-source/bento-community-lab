"""EU7 native selected-note editing and immutable conditional payloads."""
import unittest,struct,gc
from test_editable_eu import Edit
from test_live import UU,note
from unicorn.arm_const import UC_ARM_REG_R0
class Tests(unittest.TestCase):
 def event(self,p):
  e=0x2002e000;p.w(e,0x1051);return p.call(UU['seq_select_event'],p.seqview,e)
 def selected(self,p,n):return p.call(0x0815b9c0,p.seqview,n)
 def test_select_mode_taps_never_toggle_notes_and_persist_after_release(self):
  p=Edit(notes=[]);p.generated();before=p.events();self.assertEqual(self.event(p),1)
  for n in [0,3]:
   p.call(0x0815d1ec,p.seqview,n);p.call(0x0815d23c,p.seqview,n)
  self.assertEqual(p.events(),before);self.assertEqual([self.selected(p,n) for n in [0,1,3,5]],[1,0,1,0])
  p.call(0x0815d1ec,p.seqview,0);p.call(0x0815d23c,p.seqview,0)
  self.assertEqual(self.selected(p,0),0);self.assertEqual(self.selected(p,3),1)
  p.call(0x0815d1ec,p.seqview,1);p.call(0x0815d23c,p.seqview,1)
  self.assertEqual(p.events(),before);self.assertEqual(self.selected(p,1),0)
 def test_multi_selection_native_velocity_and_locks_edit_only_selected_notes(self):
  p=Edit(notes=[]);p.generated();self.event(p)
  for n in [0,3]:p.call(0x0815d1ec,p.seqview,n);p.call(0x0815d23c,p.seqview,n)
  p.call(0x0815c7c4,p.seqview,39);p.call(UU['locks_header_before'],p.seqview)
  p.call(UU['locks_encoder'],p.seqview,2,(-18000)&0xffffffff)
  self.assertEqual([struct.unpack_from('<H',e,18)[0] for e in p.events()],[39,39,100])
  self.assertEqual([struct.unpack_from('<I',e,20)[0] for e in p.events()],[0x5101030c,0x5101030c,0])
 def test_conditional_lock_on_every_second_cycle_keeps_all_notes(self):
  w=0x5101030c;p=Edit(notes=[]);p.generated();token=p.call(UU['locks_condition_word'],w,101)
  self.assertEqual(p.call(UU['locks_condition_get'],token),101)
  # Select one generated note, then use actual PROJ+encoder3 handler.
  p.select(0);p.call(UU['locks_header_before'],p.seqview);p.call(UU['locks_encoder'],p.seqview,2,(-18000)&0xffffffff)
  p.call(UU['locks_proj'],p.model,1);p.call(UU['locks_encoder'],p.seqview,0x198,101);p.call(UU['locks_proj'],p.model,0)
  self.assertEqual(p.call(UU['locks_condition_get'],struct.unpack_from('<I',p.events()[0],20)[0]),101)
  p.sync();p.across(21)
  hits=[(round(t/6000),p.locktrace[i]) for i,(pad,t) in enumerate(p.absolute) if pad==2 and round(t/6000)%7==0]
  self.assertEqual(hits[:3],[(0,0),(7,w),(14,0)])
 def test_immutable_payloads_preserve_prior_values_and_deduplicate(self):
  p=Edit();a=p.call(UU['locks_condition_word'],0x5101030c,100);b=p.call(UU['locks_condition_word'],0x5101030d,100)
  self.assertNotEqual(a,b);self.assertEqual(p.call(UU['locks_condition_word'],0x5101030c,100),a)
  self.assertEqual(p.call(UU['locks_slot'],a,0),0x5101030c);self.assertEqual(p.call(UU['locks_slot'],b,0),0x5101030d)
  self.assertEqual(p.call(UU['locks_condition_word'],a,0),0x5101030c)
 def test_native_manual_condition_filter_uses_native_loop_and_keeps_hit(self):
  p=Edit();w=0x5101030c;t=p.call(UU['locks_condition_word'],w,101)
  import json,os
  from pathlib import Path
  aa=json.loads((Path(os.environ['BENTO_FX_CANDIDATE'])/'manifest.json').read_text())['audio_symbols']
  c=0x24048a60
  for off,val in [(0,p.audioseq),(4,p.r(p.audioseq+12)),(8,p.clip),(12,0)]:p.w(c+off,val)
  self.assertEqual(p.call(aa['locks_native_filter'],p.audioseq,t),0);p.w(c+12,1)
  self.assertEqual(p.call(aa['locks_native_filter'],p.audioseq,t),w)
 def test_selection_survives_mode_off_but_context_change_resets_it(self):
  p=Edit(notes=[]);p.generated();self.event(p);p.call(0x0815d1ec,p.seqview,0);p.call(0x0815d23c,p.seqview,0);self.event(p)
  self.assertEqual(self.selected(p,0),1);p.w(p.seqview+0x11400,3);self.assertEqual(self.selected(p,0),0)
 def test_native_undo_menu_has_select_next_to_undo_without_losing_actions(self):
  p=Edit();p.call(0x081412ec);d=0x30030168+0xfc0
  self.assertEqual([p.r(d+4+i*20) for i in range(5)],[0x1032,0x1041,0x1042,0x102c,0x1051])
  self.assertEqual(p.text(p.r(d+88)),"Select")
  event=0x2002e000;p.w(event,0x1051);self.assertEqual(p.call(0x0815d600,p.seqview,event),0)
  self.assertEqual(p.text(p.r(d+88)),"Select ON")
 def test_touch_select_uses_native_hitboxes_without_editing_notes(self):
  p=Edit(notes=[]);p.generated();self.event(p);before=p.events()
  for i in range(7):p.u.mem_write(p.seqview+0x38+i*0x704,struct.pack('<4I',i*100,319,95,80))
  point=0x2002e040;p.w(point,320);p.w(point+4,340)
  p.call(0x0815d29c,p.seqview,point);p.call(0x0815d444,p.seqview)
  self.assertEqual(self.selected(p,3),1);self.assertEqual(p.events(),before)
 def test_save_reload_condition_and_both_locks_without_pointer_serialization(self):
  p=Edit();a=0x5101030c;b=0x51030025;pair=p.call(UU['locks_pack'],a,b)
  token=p.call(UU['locks_condition_word'],pair,103);raw=0x2002d000;p.u.mem_write(raw,note(0,lock=token))
  p.call(UU['locks_save'],0x20017000,raw)
  self.assertEqual(p.attrs,{'bento_lock1_v1':a,'bento_lock2_v1':b,'bento_lock_condition_v1':103})
  p.w(raw+20,0);p.call(UU['locks_load'],0x20017000,raw);w=p.r(raw+20)
  self.assertEqual(p.call(UU['locks_condition_get'],w),103);self.assertEqual(p.call(UU['locks_slot'],w,1),b)
  del p.attrs['bento_lock_condition_v1'];p.w(raw+20,0);p.call(UU['locks_load'],0x20017000,raw)
  self.assertEqual(p.r(raw+20),pair)
 def test_condition_memory_failure_does_not_change_selected_notes(self):
  p=Edit(notes=[note(0,lock=0x5101030c),note(3,lock=0x5101030d,ident=2)]);self.event(p)
  for n in [0,3]:p.call(0x0815d1ec,p.seqview,n);p.call(0x0815d23c,p.seqview,n)
  before=p.events();p.w(0x30000048,p.r(0x3000004c));p.call(UU['locks_proj'],p.model,1);p.call(UU['locks_encoder'],p.seqview,0x198,101)
  self.assertEqual(p.events(),before)
 def test_native_accepted_note_adapter_resolves_only_payload_and_preserves_stack(self):
  from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_R8,UC_ARM_REG_LR,UC_ARM_REG_PC
  p=Edit();w=0x5101030c;token=p.call(UU['locks_condition_word'],w,100)
  sp=0x2003d000;p.w(sp+60,token)
  p.u.reg_write(UC_ARM_REG_R8,p.audioseq);p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,p.stop|1)
  p.u.emu_start(0x08060b9b,0x080d3000,count=100000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x080d3000);self.assertEqual(p.r(sp+60),w);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
