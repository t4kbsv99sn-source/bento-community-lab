"""C2 binary guards, startup ownership, and configured native MPU permissions."""
import sys,unittest,struct
from pathlib import Path
from build import candidate,restore,BASE,STATE,HEAP_END,INPUT,STARTUP,CONSUMER,C_CODE,UI_STARTUP
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bento_mods/tests'))
from test_mpu import configuration,executable
from test_controls import STOCK,IMAGE,WRITES,Fixture
from unicorn.arm_const import *
class Tests(unittest.TestCase):
 def test_exact_restore(self):self.assertEqual(restore(IMAGE,WRITES),STOCK)
 def test_modified_input_rejected(self):
  bad=bytearray(STOCK);bad[0x100]^=1
  with self.assertRaises(ValueError):candidate(bad)
 def test_manifest_accounts_for_all_bytes(self):
  reconstructed=bytearray(STOCK)
  for w in sorted(WRITES,key=lambda x:x['address']):
   off=w['address']-BASE;self.assertGreaterEqual(off,0)
   reconstructed[off:off+w['size']]=bytes.fromhex(w['replacement_hex'])
  self.assertEqual(bytes(reconstructed),IMAGE)
 def test_app_headers_disk_unchanged(self):
  for a in [BASE,0x080e0000,0x08100000]:self.assertEqual(IMAGE[a-BASE:a-BASE+0x400],STOCK[a-BASE:a-BASE+0x400])
  self.assertEqual(IMAGE[0xa0000:0xc0000],STOCK[0xa0000:0xc0000])
 def test_heap_reserves_entire_state_and_stack_stays(self):
  for a in [0x08040588,0x080a3bdc,0x080a3e94]:self.assertEqual(struct.unpack_from('<I',IMAGE,a-BASE)[0],HEAP_END)
  self.assertEqual(STOCK[:4],IMAGE[:4]);self.assertEqual(STATE+256,0x24048da0);self.assertEqual(HEAP_END+28064,0x24048da0)
 def test_code_executable_in_native_mpu_regions(self):
  c,r=configuration(0x0804fa00)
  for a in [INPUT,STARTUP,0x080d1000,0x080d1080,0x080d1100,0x080d1400,0x080d1f00,0x080d2000,0x080d2100,0x080d2400,0x080d3000,0x080d3400]:self.assertTrue(executable(a,c,r))
  c,r=configuration(0x08114d74)
  for a in [CONSUMER,C_CODE,0x081b5000,UI_STARTUP,0x081b5300,0x081b5800,0x081b6600,0x081b6800,0x081b7000,0x081b7400,0x081b8c00,0x081ba000,0x081ba100,0x081bb000,0x081bb400]:self.assertTrue(executable(a,c,r))
  # Highest-priority matching UI state region is AP=3, non-cacheable.
  s=r[0];self.assertEqual((s['rasr']>>24)&7,3);self.assertFalse(s['rasr']&(1<<17))
  self.assertLess(STATE+256,0x24080000);self.assertGreaterEqual(STATE,0x24040000)
 def test_ui_startup_clears_warm_state_without_touching_input(self):
  f=Fixture();f.u.mem_write(STATE,bytes([0xa5])*256);f.u.reg_write(UC_ARM_REG_SP,0x20030000)
  f.u.emu_start(UI_STARTUP|1,0x081004ba,count=20000)
  self.assertEqual(bytes(f.u.mem_read(STATE,32)),bytes([0xa5])*32)
  self.assertEqual(bytes(f.u.mem_read(STATE+32,224)),bytes(224))
  self.assertEqual(f.u.reg_read(UC_ARM_REG_R0),0x081891fc);self.assertEqual(f.u.reg_read(UC_ARM_REG_R1),0x08189258)
 def test_renderer_binding_only_expected_entry(self):
  self.assertEqual(struct.unpack_from('<I',IMAGE,0x0819dd20-BASE)[0],0x081b5001)
  self.assertEqual(len(WRITES),70)
  for address in [0x08152144,0x08152c50,0x0812f5ea,0x0812faac]:
   self.assertTrue(any(w['address']==address for w in WRITES))
if __name__=='__main__':unittest.main(verbosity=2)
