"""K5 executes both processor modules with a shared mailbox, without native commands."""
import unittest,struct
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from test_kick import Kick
from test_kick_install import Install,REPORT
from kick_build import SYMS
MAIL=0x24043500;SIZE=0x820
class Tests(unittest.TestCase):
 def copy(self,ui,audio):audio.u.mem_write(MAIL,bytes(ui.u.mem_read(MAIL,SIZE)))
 def load(self,ui,path,handle=157):
  ui.u.mem_write(0x2001d000,path.encode()+b'\0');ui.call('kick_sample_loading',0x2001b000,handle,0x2001d000,1)
 def test_file_handle_is_not_used_as_sound_identity(self):
  ui=Install();p=Kick(False);p.w(p.root+12,157)
  self.load(ui,'BENTO_Kick_K2.wav');self.copy(ui,p);p.start()
  self.assertEqual(p.render()[0],0);self.assertEqual(bytes(ui.u.mem_read(MAIL,SIZE)),bytes(SIZE))
 def test_stale_k5_mailbox_cannot_enable_an_unrelated_normal_sound(self):
  ui=Install();p=Kick(False);p.w(p.root+12,157)
  ui.call('kick_assign',157,1);self.copy(ui,p);p.start();self.assertEqual(p.render()[0],0)
 def test_stale_k5_disable_cannot_suppress_a_genuine_marker(self):
  ui=Install();p=Kick(True);p.w(p.root+12,157)
  ui.call('kick_assign',157,0);self.copy(ui,p);p.start();self.assertEqual(p.render()[0],1)
 def test_assignments_cover_all_current_pads_and_reclaim_old_project_entries(self):
  ui=Install();p=Kick(False)
  for handle in range(1,257):ui.call('kick_assign',handle,1)
  self.copy(ui,p)
  for handle,wanted in [(1,0),(128,0),(129,1),(256,1)]:
   p.w(p.root+12,handle);p.call(SYMS['kick_assignment'],p.root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),wanted)
 def test_torn_update_is_rejected_and_stable_committed_update_is_accepted(self):
  ui=Install();p=Kick(False);p.w(p.root+12,157);ui.call('kick_assign',157,1);self.copy(ui,p)
  p.w(MAIL+32,3);p.call(SYMS['kick_assignment'],p.root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
  p.w(MAIL+32,2);p.call(SYMS['kick_assignment'],p.root);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),1)
 def test_reader_invalidates_only_ui_owned_lines_and_refreshes_after_new_serial(self):
  ui=Install();p=Kick(False);p.w(p.root+12,157);p.w(0xe000ed14,1<<16);writes=[]
  def watch(u,access,a,n,value,d):
   if a==0xe000ef5c:writes.append(value)
  p.u.hook_add(UC_HOOK_MEM_WRITE,watch);ui.call('kick_assign',157,1);self.copy(ui,p)
  p.call(SYMS['kick_assignment'],p.root);self.assertEqual(set(writes),set(range(MAIL,MAIL+SIZE,32)))
  writes.clear();p.call(SYMS['kick_assignment'],p.root);self.assertEqual(writes,[MAIL])
  ui.call('kick_assign',157,0);self.copy(ui,p);writes.clear();p.call(SYMS['kick_assignment'],p.root)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),2);self.assertEqual(set(writes),set(range(MAIL,MAIL+SIZE,32)))
 def test_preview_and_missing_handles_cannot_change_assignments(self):
  ui=Install();self.load(ui,'BENTO_Kick_K2.wav',0xfffffff9);self.load(ui,'BENTO_Kick_K2.wav',0)
  self.assertEqual(bytes(ui.u.mem_read(MAIL,SIZE)),bytes(SIZE))
 def test_k5_report_includes_mailbox_identity_and_update_counter(self):
  ui=Install();self.load(ui,'BENTO_Kick_K2.wav');ui.w(0x2001c000,0x3f);ui.call('kick_load_entry',0x2001b000,0x2001c000)
  self.assertIn(b'assignment_magic=0x00000000',ui.files[REPORT]);self.assertIn(b'assignment_serial=0x00000000',ui.files[REPORT])
if __name__=='__main__':unittest.main(verbosity=2)
