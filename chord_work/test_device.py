"""CH1 installed ARM UI through actual native widgets and note container.
Navigation, model lookup, fonts, Undo storage and engine queue remain fixtures.
"""
import struct,unittest,gc
from test_native_piano import Piano
from test_integration import UU,IMAGE
import test_eu9 as header_fixture
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
KEYS=[0x196,0x197,0x19a,0x19b,0x19d,0x19e,0x19f,0x1d1,0x1d2,0x1d3,0x128,0x129,0x12a,0x12b,0x12c,0x12d]
KEEP=[]
class Device(Piano):
 def __init__(self):
  super().__init__();KEEP.append(self);self.call(0x081599bc,self.view);self.piano=self.view
  self.u.hook_add(UC_HOOK_CODE,self.nav,begin=0x081420ec,end=0x081420ec)
  self.u.hook_add(UC_HOOK_CODE,self.bubble,begin=0x0816fc34,end=0x0816fc34)
  self.editor=0xc0500000;self.u.mem_map(self.editor,0x20000)
 def nav(self,u,a,n,d):self.navlog.append(u.reg_read(UC_ARM_REG_R1));self.ret()
 def bubble(self,u,a,n,d):
  e=u.reg_read(UC_ARM_REG_R1);code=self.r(e)&65535
  if code in [0xcf,0x1052,0x1053]:
   u.reg_write(UC_ARM_REG_R0,self.editor if self.navlog and self.navlog[-1]==0x1a else self.piano)
   u.reg_write(UC_ARM_REG_PC,0x08145d91 if self.navlog and self.navlog[-1]==0x1a else 0x0815a599)
  else:self.ret()
 def open_editor(self):
  self.action(0x1052,piano=True);self.call(0x08145b7c,self.editor);self.w(0x20016000,42);self.call(0x08145efc,self.editor,0x20016000)
 def action(self,code,piano=False):
  e=0x2002e000;self.w(e,code);return self.call(0x0815a598 if piano else 0x08145d90,self.piano if piano else self.editor,e)
 def edit(self,i,value):
  e=0x2002e000;self.u.mem_write(e,struct.pack('<5I',0xcf,42,KEYS[i],value&0xffffffff,0));return self.call(0x08145d90,self.editor,e)
 def value(self,i):
  arg=0x20016000;out=0x20016010;self.w(arg,42);assert self.call(0x08133614,self.model,arg,KEYS[i],out)==1
  return struct.unpack('<i',self.u.mem_read(out,4))[0]
 def status(self):return self.text(self.r(self.editor+0x93c8+8))
 def toolbar(self):
  out=0x20028000;self.u.mem_write(out,bytes(0x1c4));self.u.mem_write(out+0x74,b'Undo\0');self.w(out+0x74+44,0x1032)
  header_fixture.Tests().native_header(self,out);return out
class Tests(unittest.TestCase):
 def test_registry_fits_actual_native_allocation_and_preserves_every_other_descriptor(self):
  p=Device();r=p.r(0x30031484);before=bytes(p.u.mem_read(r,0x3e60));p.u.mem_write(r+0x3e60,b'CANARY32');p.open_editor()
  after=bytes(p.u.mem_read(r,0x3e60));self.assertEqual(p.u.mem_read(r+0x3e60,8),b'CANARY32')
  for i in range(499):
   if i in KEYS:self.assertEqual(struct.unpack_from('<H',after,i*32)[0],i)
   else:self.assertEqual(before[i*32:(i+1)*32],after[i*32:(i+1)*32],hex(i))
 def test_real_piano_header_capture_persistent_touch_entry_and_native_three_rows(self):
  p=Device();out=p.toolbar();root=0xc0540000;p.u.mem_map(root,0x10000);p.call(0x08180198,root);p.call(0x0817faf8,root,out)
  button=root+0x54c+0xd0;self.assertEqual(p.text(button+0x3c+0x31),'Chord');self.assertEqual(p.r(button+0x14)&65535,0x1052)
  e=0x2002e000;p.w(e,0x7a);p.w(e+8,0x1052);p.u.mem_write(p.model+0x14c,b'\0');p.call(0x0817fe70,root,e);self.assertEqual(p.navlog,[0x1a])
  p.call(0x08145b7c,p.editor);p.w(0x20016000,42);p.call(0x08145efc,p.editor,0x20016000)
  self.assertEqual(p.u.mem_read(p.editor+0x93c4,1),b'\x03');self.assertEqual(p.text(p.r(p.editor+0x93c8)),'Chord / C3')
  self.assertEqual(struct.unpack('<16H',p.u.mem_read(p.editor+0x93c4+0x14,32)),tuple(KEYS))
 def test_native_encoder_bubbles_to_new_chord_editor(self):
  p=Device();p.open_editor();before=p.value(0);self.assertEqual(p.call(0x08171e44,p.editor+0x70,12800),1);self.assertNotEqual(p.value(0),before)
 def test_insert_single_chord_then_native_piano_projection_and_duplicate_refusal(self):
  p=Device();p.open_editor();p.edit(6,83);p.action(0x1053);self.assertEqual(len(p.events()),3);self.assertEqual(len(p.undo),1)
  self.assertEqual(sorted(struct.unpack_from('<H',e,16)[0] for e in p.events()),[48,52,55]);self.assertEqual({struct.unpack_from('<H',e,18)[0] for e in p.events()},{83})
  before=p.events();p.action(0x1053);self.assertEqual(p.events(),before);self.assertIn('Overlapping',p.status());self.assertEqual(len(p.undo),1)
  p.action(0x1052);self.assertEqual(p.navlog[-1],0x27)
 def test_progression_preset_key_scale_voicing_and_insert(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(9,2);p.edit(11,2);p.edit(0,7);p.edit(1,2);p.edit(2,1);p.action(0x1053)
  self.assertEqual(len(p.events()),10);self.assertEqual(len(p.undo),1);self.assertIn('Inserted',p.status())
  self.assertEqual(sorted({struct.unpack_from('<I',e,4)[0] for e in p.events()}),[0,3840,7680])
 def test_minor_preset_adopts_minor_and_explicit_quality_survives_key_changes(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(9,6);self.assertEqual(p.value(12),1);self.assertEqual(p.value(0),1)
  p.edit(0,6);p.edit(11,2);self.assertEqual(p.value(0),6);p.edit(13,3);self.assertEqual(p.value(0),6)
 def test_outside_clip_edit_is_atomic_and_reports_error_without_silent_replacement(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(13,32);self.assertEqual(p.value(13),4);self.assertIn('Outside clip',p.status());self.assertFalse(p.events());self.assertFalse(p.undo)
  p.action(0x1053);self.assertEqual(len(p.events()),12)
 def test_stale_owner_and_occupied_registry_do_not_modify_music_or_other_owner(self):
  p=Device();r=p.r(0x30031484);p.w(r+KEYS[0]*32,KEYS[0]);p.w(r+KEYS[0]*32+4,0xdeadbeef);p.action(0x1052,piano=True);self.assertFalse(p.navlog);self.assertEqual(p.r(r+KEYS[0]*32+4),0xdeadbeef)
  p=Device();p.open_editor();p.owner+=1;p.action(0x1053);self.assertIn('Sequence changed',p.status());self.assertFalse(p.events());self.assertFalse(p.undo)
 def test_full_toolbar_is_preserved_and_navigation_disarms_custom_actions(self):
  p=Device();out=0x20028000
  for i in range(6):p.w(out+0x74+i*48+44,0x1032+i)
  before=bytes(p.u.mem_read(out,0x1c4));self.assertEqual(p.call(UU['chord_toolbar'],p.model,out,0),0);self.assertEqual(bytes(p.u.mem_read(out,0x1c4)),before)
  p.open_editor();p.call(UU['chord_nav'],p.model,2);self.assertEqual(p.call(UU['chord_event'],p.editor,0x2002e000),0)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
