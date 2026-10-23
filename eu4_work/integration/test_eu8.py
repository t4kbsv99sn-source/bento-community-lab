"""Full native registry/UI visibility and musical velocity integration on ARM."""
import unittest,struct,gc
from test_editable_eu import Edit
from test_live import UU,EU,note
from test_integration import AA
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
class Tests(unittest.TestCase):
 def dyn(self,p,mode,depth):
  self.assertEqual(p.call(UU['live_dynamic'],EU,4,mode),1)
  self.assertEqual(p.call(UU['live_dynamic'],EU,6,depth),1)
  out=0x2002e100;p.call(UU['live_value'],out,EU);p.cycle=(p.r(out)&255)+1
 def velocities(self,p):return [h[2] for i,h in enumerate(p.hits()) if round(p.absolute[i][1]/6000)<p.cycle]
 def full_view(self,p):
  p.registry();p.call(0x0815bf1c,p.seqview);p.u.mem_write(p.seqview+0x113e0,b'\0');p.prepare()
  # Initialize native DTCM Step-key data, normally copied at reset.
  p.u.mem_write(0x300000bc,struct.pack('<8H',0x186,0x183,0x184,0x18c,0,0,0,0))
 def header(self,p):p.call(0x081b7008,p.seqview)
 def test_full_native_registry_preserves_attack_and_binds_lock_condition(self):
  p=Edit();p.registry();reg=p.r(0x30031484);attack=bytes(p.u.mem_read(reg+0x1e5*32,32))
  p.select(0);p.call(UU['locks_header_before'],p.seqview)
  self.assertEqual(p.r(reg+0x198*32)&65535,0x198);self.assertEqual(p.r(reg+0x199*32)&65535,0x199)
  self.assertNotEqual(struct.unpack('<H',p.u.mem_read(0x300000c8,2))[0],0)
  self.assertEqual(bytes(p.u.mem_read(reg+0x1e5*32,32)),attack)
 def test_actual_native_header_shows_condition_then_restores_note_probability(self):
  p=Edit();self.full_view(p);p.select(0);self.header(p)
  self.assertEqual(struct.unpack('<H',p.u.mem_read(p.seqview+0x113ac+10,2))[0],0x199)
  slot=p.seqview+0xebf0+0x38+5*0x468
  self.assertEqual(p.u.mem_read(slot+0x30,1)[0],0)
  self.assertEqual(p.text(slot+0x3c8+0x31),'Locks when')
  p.call(UU['locks_encoder'],p.seqview,2,(-18000)&0xffffffff);p.call(UU['locks_proj'],p.model,1);self.header(p)
  self.assertEqual(struct.unpack('<H',p.u.mem_read(p.seqview+0x113ac+4,2))[0],0x198)
  p.call(UU['locks_encoder'],p.seqview,0x198,101);p.call(UU['locks_proj'],p.model,0);self.header(p)
  self.assertEqual(struct.unpack('<H',p.u.mem_read(p.seqview+0x113ac+4,2))[0],0x184)
  self.assertEqual(p.r(p.seqview+0x113bc+20),101)
 def test_both_native_sequencer_menu_definitions_include_select(self):
  p=Edit();p.call(0x081412ec)
  for offset,count in [(0x8c0,9),(0xfc0,5)]:
   d=0x30030168+offset
   self.assertEqual([p.r(d+4+i*20) for i in [0,4]],[0x1032,0x1051])
   self.assertEqual(p.u.mem_read(d+0xcc,1)[0],count)
 def test_actual_native_menu_creates_visible_select_beside_undo_and_emits_action(self):
  p=Edit();p.registry();p.call(0x081412ec);menu=0xc00d0000;p.call(0x08177d48,menu)
  definition=0x30030168+0x8c0;p.call(0x0817818c,menu,definition)
  self.assertEqual(p.r(menu+0x904),9)
  undo=menu+0x34;select=undo+4*0xd0
  self.assertIn(b'Undo',bytes(p.u.mem_read(undo,0xd0)));self.assertIn(b'Select',bytes(p.u.mem_read(select,0xd0)))
  self.assertEqual(p.r(select+12),p.r(undo+12));self.assertEqual(p.r(select+16),p.r(undo+16))
  self.assertEqual(p.r(select+8),p.r(undo+8));self.assertGreater(p.r(select+4),p.r(undo+4))
  self.assertEqual(p.u.mem_read(select+0x30,1)[0],0)
  emitted=[]
  def bubble(u,a,n,d):
   ptr=u.reg_read(UC_ARM_REG_R1)
   if p.r(ptr)&65535==0x1051:emitted.append(bytes(u.mem_read(ptr,20)))
   p.ret()
  p.u.hook_add(UC_HOOK_CODE,bubble,begin=0x0816fc34,end=0x0816fc34)
  event=0x2002e000;p.w(event,0x7a);p.w(event+8,4);p.call(0x08177ee2,menu,event)
  self.assertEqual(len(emitted),1);p.u.mem_write(event,emitted[0]);p.call(0x0815d600,p.seqview,event)
  self.assertEqual(p.text(p.r(definition+88)),"Select ON")
 def test_alternate_counts_hits_across_gaps_not_grid_positions(self):
  p=Edit(notes=[]);p.generated(7,3);self.dyn(p,1,100);p.sync();p.across(7)
  self.assertEqual([round(t/6000) for pad,t in p.absolute if pad==2 and round(t/6000)<7],[0,3,5])
  self.assertEqual(self.velocities(p),[127,1,127])
 def test_alternate_continues_across_odd_hit_count_loop(self):
  p=Edit(notes=[]);p.generated(7,3);self.dyn(p,1,100);p.sync();p.across(14)
  values=[p.hits()[i][2] for i,(pad,time) in enumerate(p.absolute) if round(time/6000)<14]
  self.assertEqual(values,[127,1,127,1,127,1])
 def test_hit_accent_and_grid_accent_are_distinct(self):
  for mode,want in [(2,[127,1,1]),(3,[127,1,1]),(4,[127,1,1])]:
   p=Edit(notes=[]);p.generated(8,5);self.dyn(p,mode,100);p.sync();p.across(8)
   actual=self.velocities(p)
   positions=[round(t/6000) for pad,t in p.absolute if pad==2 and round(t/6000)<8]
   expected=[127 if (i%(3 if mode==2 else 4)==0 if mode!=4 else step%4==0) else 1 for i,step in enumerate(positions)]
   self.assertEqual(actual,expected)
 def test_depth_zero_and_flat_preserve_saved_individual_velocities(self):
  notes=[note(0,ident=1,vel=42),note(3,ident=2,vel=99),note(5,ident=3,vel=73)]
  for mode,depth in [(0,100),(1,0),(8,0)]:
   p=Edit(notes=notes);p.generated(7,3);before=p.events();self.dyn(p,mode,depth);p.sync();p.across(7)
   self.assertEqual(self.velocities(p),[42,99,73]);self.assertEqual(p.events(),before)
 def test_manual_added_hit_is_included_in_hit_ranking(self):
  p=Edit(notes=[]);p.generated(7,3);p.tap(1);self.dyn(p,1,100);p.sync();p.across(7)
  self.assertEqual(self.velocities(p),[127,1,127,1])
 def test_rise_fall_wave_and_random_are_bounded_and_repeatable(self):
  for mode in range(10):
   p=Edit();vals=[p.call(AA['eu_velocity_value'],100,mode,100,i,8,i*2,8123) for i in range(8)]
   self.assertTrue(all(1<=v<=127 for v in vals))
   again=[p.call(AA['eu_velocity_value'],100,mode,100,i,8,i*2,8123) for i in range(8)]
   self.assertEqual(vals,again)
   if mode==5:self.assertEqual(vals,sorted(vals));self.assertNotEqual(vals[0],vals[-1])
   if mode==6:self.assertEqual(vals,sorted(vals,reverse=True))
 def test_dynamics_roundtrip_xml_keeps_legacy_velocity_word_plain(self):
  p=Edit(notes=[]);p.generated();self.dyn(p,7,63)
  obj=0x2002d000;p.w(obj+0x10,p.owner);p.u.mem_write(obj+4,b'\x0e');p.call(UU['live_save'],obj,0x20017000)
  self.assertEqual(p.attrs['bento_eu2_00_02_1'],100)
  self.assertEqual(p.attrs['bento_eu2_00_02_2'],7);self.assertEqual(p.attrs['bento_eu2_00_02_3'],63)
  p.call(UU['live_load'],0x20017000,obj);p.call(UU['live_finish']);out=0x2002e000;p.call(UU['live_value'],out,EU)
  self.assertEqual(p.r(out+4),100|(7<<8)|(63<<16))
 def test_generated_new_notes_default_100_without_overwriting_retained_edits(self):
  p=Edit(notes=[note(0,ident=1,vel=43)]);p.generated();self.dyn(p,1,80);p.generate(2,4)
  vals=[struct.unpack_from('<H',e,18)[0] for e in p.events()]
  self.assertEqual(vals[0],43);self.assertTrue(all(v==100 for v in vals[1:]))
 def test_mode_and_depth_change_no_native_notes_or_undo(self):
  p=Edit(notes=[]);p.generated();before=p.events();undo=len(p.undo);self.dyn(p,9,75)
  self.assertEqual(p.events(),before);self.assertEqual(len(p.undo),undo)
 def test_velocity_symbol_uses_five_native_palette_bars(self):
  p=Edit(notes=[]);self.full_view(p);p.generated();p.call(UU['seq_eu_tab'],p.seqview);event=0x2002e000;self.dyn(p,1,80);self.header(p)
  paints=[]
  def fill(u,a,n,d):
   ptr=u.reg_read(UC_ARM_REG_R0);paints.append((tuple(p.r(ptr+i*4) for i in range(4)),u.reg_read(UC_ARM_REG_R1)));p.ret()
  p.u.hook_add(UC_HOOK_CODE,fill,begin=0x08166e9e,end=0x08166e9e)
  context=0x2002f000;p.w(context,1);p.w(context+4,0x20020000);p.call(UU['eu_glyph_paint'],p.seqview,context)
  self.assertEqual(len(paints),6);self.assertEqual([rect[3] for rect,color in paints[1:]],[12,3,12,3,12])
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
