"""EU9 device-feedback regressions: actual widget turns and persistent header."""
import gc,struct,unittest
import test_eu8
from test_editable_eu import Edit
from test_live import UU
from unicorn.arm_const import *
from unicorn import UC_HOOK_CODE
KEEP=[]
class Native(Edit):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);KEEP.append(self)
 def ui(self,u,a,n,d):
  if a!=0x0815c27c:self.ret()
 def bubble(self,u,a,n,d):
  ptr=u.reg_read(UC_ARM_REG_R1);code=self.r(ptr)&65535
  if code in [0xcf,0x1051]:
   u.reg_write(UC_ARM_REG_R0,self.seqview);u.reg_write(UC_ARM_REG_PC,0x0815d601);return
  super().bubble(u,a,n,d)
class Tests(unittest.TestCase):
 def view(self):
  p=Native();test_eu8.Tests().full_view(p);p.select(0);p.call(0x0815c27c,p.seqview);return p
 def turn(self,p,index,delta):
  p.w(0x30035f40,p.r(0x30035f40)+20)
  return p.call(0x08171e44,p.seqview+0xebf0+0x38+index*0x468,delta&0xffffffff)
 def test_condition_can_be_set_before_any_lock_and_entire_range_is_reachable_by_native_turns(self):
  p=self.view();p.call(UU['locks_proj'],p.model,1);slot=p.seqview+0xebf0+0x38+2*0x468
  for i in range(80):self.turn(p,2,-12800)
  self.assertEqual(p.r(slot+0xa0),0)
  for i in range(90):self.turn(p,2,12800)
  self.assertEqual(p.r(slot+0xa0),134)
  e=p.events()[0];word=struct.unpack_from('<I',e,20)[0]
  self.assertEqual(p.call(UU['locks_condition_get'],word),134)
  self.assertEqual(p.call(UU['locks_slot'],word,0),0)
 def test_adding_lock_retains_previously_selected_condition_and_xml_roundtrips(self):
  p=self.view();p.call(UU['locks_proj'],p.model,1);p.call(UU['locks_encoder'],p.seqview,0x198,103);p.call(UU['locks_proj'],p.model,0)
  word=struct.unpack_from('<I',p.events()[0],20)[0];self.assertEqual(p.call(UU['locks_condition_get'],word),103)
  raw=0x2002e000;p.u.mem_write(raw,p.events()[0]);p.call(UU['locks_save'],0x20017000,raw)
  self.assertEqual(p.attrs['bento_lock_condition_v1'],103)
  p.call(UU['locks_load'],0x20017000,raw);self.assertEqual(p.call(UU['locks_condition_get'],p.r(raw+20)),103)
  p.call(UU['locks_encoder'],p.seqview,2,(-18000)&0xffffffff)
  word=struct.unpack_from('<I',p.events()[0],20)[0];self.assertEqual(p.call(UU['locks_condition_get'],word),103);self.assertNotEqual(p.call(UU['locks_slot'],word,0),0)
 def header_data(self,p):
  out=0x20028000;p.u.mem_write(out,bytes(0x1c4));p.u.mem_write(out+0x74,b'Undo\0');p.u.mem_write(out+0x74+44,struct.pack('<H',0x1032));p.u.mem_write(out+0x1c3,b'\xff');return out
 def native_header(self,p,out):
  # Native copy and patched return run; clock/metronome display is a fixture.
  p.u.mem_write(p.model+0x3a00,bytes(p.u.mem_read(out,0x1c4)))
  p.u.mem_write(p.model+0x14c,b'\x01');p.w(p.model+0xb19c,1);p.w(p.model+0x3c60,1)
  def after_copy(u,a,n,d):u.reg_write(UC_ARM_REG_R6,1);u.reg_write(UC_ARM_REG_PC,0x081349dd)
  h=p.u.hook_add(UC_HOOK_CODE,after_copy,begin=0x081348dc,end=0x081348dc)
  self.assertEqual(p.call(0x08134800,p.model,out,0,0),1);p.u.hook_del(h)
 def test_actual_header_entry_inserts_persistent_select_and_preserves_other_actions(self):
  p=self.view();out=self.header_data(p);p.u.mem_write(out+0xa4,b'Duplicate\0');p.u.mem_write(out+0xa4+44,struct.pack('<H',0x102c))
  self.native_header(p,out)
  self.assertEqual(p.text(out+0xa4),'Select');self.assertEqual(p.text(out+0xd4),'Duplicate')
  self.assertEqual(struct.unpack('<H',p.u.mem_read(out+0xa4+44,2))[0],0x1051)
  self.assertEqual(p.call(UU['seq_toolbar'],p.model,out,0),0)
  event=0x2002e000;p.w(event,0x1051);p.call(0x0815d600,p.seqview,event)
  self.assertEqual(p.call(UU['seq_toolbar'],p.model,out,0),1);self.assertEqual(p.text(out+0xa4),'Select ON')
 def test_native_persistent_header_renders_select_and_touch_action_reaches_selection(self):
  p=self.view();out=self.header_data(p);self.native_header(p,out)
  root=0xc00d0000;p.call(0x08180198,root);p.call(0x0817faf8,root,out)
  # Native normal header buttons are +54C, each D0 bytes; second follows Undo.
  undo=root+0x54c;select=undo+0xd0
  self.assertEqual(p.text(undo+0x3c+0x31),'Undo');self.assertEqual(p.text(select+0x3c+0x31),'Select')
  self.assertEqual(p.u.mem_read(select+0x30,1)[0],0)
  self.assertEqual(p.r(select+16),p.r(undo+16));self.assertEqual(p.r(select+12),p.r(undo+12));self.assertGreater(p.r(select+4),p.r(undo+4))
  self.assertEqual(p.r(select+0x14)&65535,0x1051)
  # Header routes the native release to the active SEQ view; parent is a fixture.
  p.u.mem_write(p.model+0x14c,b'\x00');event=0x2002e000;p.w(event,0x7a);p.w(event+8,0x1051)
  p.call(0x0817fe70,root,event);self.assertEqual(p.text(p.r(0x30030168+0x8c0+88)),"Select ON")

 def test_depth_increment_is_five_times_faster_without_speeding_other_controls(self):
  p=self.view();slot=p.seqview+0xebf0+0x38+5*0x468
  p.u.mem_write(slot+0x9c,struct.pack('<H',0x195))
  self.assertEqual(p.call(UU['kick_ui_increment'],slot,160),800)
  self.assertEqual(p.call(UU['kick_ui_increment'],slot,(-160)&0xffffffff),(-800)&0xffffffff)
  p.u.mem_write(slot+0x9c,struct.pack('<H',0x191));self.assertEqual(p.call(UU['kick_ui_increment'],slot,160),160)
 def test_glyph_replaces_value_text_at_native_size_white_on_black(self):
  p=self.view();p.call(UU['seq_selection_reset'],p.seqview);p.w(0x24048d80+20,0)
  for i in range(32):p.w(p.seqview+0x11420+i*4,0)
  event=0x2002e000;p.w(event,0x73);p.w(event+8,9);p.call(UU['seq_eu_arrows'],p.seqview,event);p.call(0x0815c27c,p.seqview)
  paints=[]
  def fill(u,a,n,d):
   ptr=u.reg_read(UC_ARM_REG_R0);paints.append((tuple(p.r(ptr+i*4) for i in range(4)),u.reg_read(UC_ARM_REG_R1)));p.ret()
  p.u.hook_add(UC_HOOK_CODE,fill,begin=0x08166e9e,end=0x08166e9e)
  ctx=0x2002f000;p.w(ctx,1);p.w(ctx+4,0x20020000);p.call(UU['eu_glyph_paint'],p.seqview,ctx)
  self.assertEqual(len(paints),6);self.assertEqual([c for r,c in paints],[0xf1]+[0xf2]*5)
  self.assertEqual(paints[0][0][3],16)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
