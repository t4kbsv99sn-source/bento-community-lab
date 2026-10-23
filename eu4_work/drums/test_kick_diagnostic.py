"""K4 compiled-device instrumentation and UI-only report output."""
import struct, unittest
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from test_kick import Kick
from test_kick_install import Install,PATH,REPORT
from test_plock import Probe
from kick_build import SYMS
D=0x24043e00; U=0x24043f00

def words(p):return struct.unpack('<32I',p.u.mem_read(D,128))
class Tests(unittest.TestCase):
 def test_wrong_class_is_recorded_before_voice_and_render_guards(self):
  p=Kick();p.w(p.root,0x080ac670);p.start();p.render();d=words(p)
  self.assertEqual(d[8:13],(1,p.root,0x080ac670,p.desc,1))
  self.assertEqual(d[13:18],(1,p.root,0x080ac670,p.desc,1));self.assertEqual(d[18:20],(0,0))
 def test_failed_marker_exposes_metadata_and_exact_failure_stage(self):
  p=Kick(False);p.start();p.render();d=words(p)
  self.assertEqual(d[12],2);self.assertEqual(d[17],2);self.assertEqual(d[26:29],(144019,48000,0));self.assertEqual(d[30],5)
 def test_success_records_start_block_peak_and_native_buffer_details(self):
  p=Kick();p.start();p.render();d=words(p)
  self.assertEqual(d[18:20],(1,1));self.assertEqual(d[12],0);self.assertEqual(d[17],0)
  self.assertEqual(d[20:24],(64,p.temp,128,p.samples));self.assertGreater(d[24],0)
 def test_command_rejected_by_handle_is_still_visible_in_diagnostics(self):
  p=Probe();p.command(0x7ffc,102,1);d=words(p)
  self.assertEqual(d[:8],(0x3444474b,1,p.obj,0x080ac66c,101,102,1,0))
 def test_enabled_data_cache_cleans_each_m7_diagnostic_cache_line(self):
  p=Kick();p.w(0xe000ed14,1<<16);writes=[]
  def watch(u,access,address,size,value,data):
   if address==0xe000ef68:writes.append(value)
  p.u.hook_add(UC_HOOK_MEM_WRITE,watch);p.start()
  self.assertTrue(writes);self.assertEqual(set(writes),set(range(D,D+128,32)))
 def test_ui_report_includes_snapshot_and_closes_file_without_changing_marker(self):
  p=Install();p.call('kick_install');marker=bytes(p.files[PATH]);p.w(D,0x3444474b);p.w(D+13*4,99)
  p.w(0x3000f650,0x20028000);p.u.mem_write(0x2001d000,b'BENTO_Kick_K2.wav\0')
  p.call('kick_sample_loading',0x2001b000,101,0x2001d000,1)
  p.w(0x2001c000,0x3f);p.call('kick_load_entry',0x2001b000,0x2001c000)
  text=bytes(p.files[REPORT]).decode();self.assertIn('render_entries=0x00000063',text)
  self.assertIn('kick_commands_sent=0x00000000',text);self.assertIn('kick_name_handle=0x00000065',text)
  self.assertEqual(bytes(p.files[PATH]),marker);self.assertEqual(p.open_files,{})
 def test_zero_counters_still_produce_report_and_replace_only_fixed_mod_report(self):
  p=Install();p.files['user.wav']=bytearray(b'keep');p.files[REPORT]=bytearray(b'old diagnostic')
  p.w(0x2001c000,0x3f);p.call('kick_load_entry',0x2001b000,0x2001c000)
  self.assertIn(b'm7_magic=0x00000000',p.files[REPORT]);self.assertIn(b'loader_entries=0x00000000',p.files[REPORT])
  self.assertEqual(p.files['user.wav'],b'keep');self.assertEqual(p.open_files,{})
if __name__=='__main__':unittest.main(verbosity=2)
