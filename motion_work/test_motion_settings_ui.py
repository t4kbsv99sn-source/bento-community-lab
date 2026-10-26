"""Installed motion settings through actual native GenericProperties widgets.
Track lookup, fonts and navigation dispatch remain controlled fixtures.
"""
import json,struct,unittest,os
from pathlib import Path
from test_device import Device
from unicorn.arm_const import *
OUT=Path(os.environ['BENTO_FX_CANDIDATE']);MS=json.loads((OUT/'MOTION_MANIFEST.json').read_text())['ui_symbols']
class Tests(unittest.TestCase):
 def test_native_settings_page_exposes_length_and_mode_and_restores_descriptors(self):
  p=Device();registry=p.r(0x30031484);before=bytes(p.u.mem_read(registry,0x3e60))
  p.w(0x3000004c,p.next);p.w(0x30000048,0xc0200000)
  event=0x2002e000;p.u.mem_write(event,struct.pack('<5I',0x1070,0,0,0,0))
  p.call(0x081403ec,p.model,event);self.assertEqual(p.navlog[-1],0x1a)
  p.u.mem_write(p.model+0x12c,b'\x1a');p.call(0x08145b7c,p.editor)
  handle=0x20016000;p.w(handle,42);p.call(0x08145efc,p.editor,handle)
  out=0x20016010
  self.assertEqual(p.call(0x08133614,p.model,handle,0x190,out),1);self.assertEqual(p.r(out),3)
  p.u.mem_write(event,struct.pack('<5I',0xcf,42,0x190,5,0));p.call(0x08145d90,p.editor,event)
  p.call(0x08133614,p.model,handle,0x190,out);self.assertEqual(p.r(out),5)
  p.u.mem_write(event,struct.pack('<5I',0xcf,42,0x191,1,0));p.call(0x08145d90,p.editor,event)
  p.call(0x08133614,p.model,handle,0x191,out);self.assertEqual(p.r(out),1)
  self.assertEqual(p.text(p.r(registry+0x190*32+4)),'Length')
  p.call(MS['motion_controls_nav'],p.model,0x17)
  self.assertEqual(bytes(p.u.mem_read(registry,0x3e60)),before)
if __name__=='__main__':unittest.main(verbosity=2)
