"""Execute original receiver and original producer queue with C2 input bytes."""
import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bento_mods/tests'))
from receiver_fixture import Receiver,B,UIQUEUE
from build import candidate,INPUT,STATE
from unicorn.arm_const import *
IMAGE,_=candidate(B)
class Input(Receiver):
 def __init__(self):
  super().__init__(False);self.u.mem_map(0x30000000,0x40000);self.u.mem_write(0x08040000,IMAGE)
  self.word(STATE,0x31534d42);self.u.mem_write(STATE+12,b'\1');self.u.mem_write(STATE+16,bytes(range(16)))
 def callback(self,u,a,size,data):
  if a==0x0808d1fe:return # Actual firmware branch executes.
  super().callback(u,a,size,data)
 def custom(self):return [struct.unpack('<6I',r) for d,r in self.records if d=='ui' and r[0]==254]
class Tests(unittest.TestCase):
 def test_all_buttons_rows_columns(self):
  for mask,base in [(0x2000,1),(0x1000,3),(0x400,5)]:
   for pad in range(16):
    with self.subTest(mask=hex(mask),pad=pad):
     f=Input();pads=[0]*16;pads[pad]=1000;f.packet(mask,pads)
     self.assertEqual(f.events(),[])
     self.assertEqual(f.custom(),[(254,0x314d5442,0xfffffffe,pad%8,base+(pad//8),0x31525442)])
 def test_pressure_release_orders(self):
  for mask in [0x2000,0x1000,0x400]:
   for pad in [0,7,8,15]:
    for button_first in [False,True]:
     f=Input();pads=[0]*16;pads[pad]=1000;f.packet(mask,pads)
     pads[pad]=1500;f.packet(mask,pads);self.assertEqual(f.custom(),[]);self.assertEqual(f.events(),[])
     if button_first:f.packet(0,pads);self.assertEqual(f.events(),[])
     f.packet(0 if button_first else mask);self.assertEqual(f.events(),[]);self.assertEqual(f.readword(STATE+4)&65535,0)
 def test_preheld_notes_released(self):
  f=Input();f.packet(0,[1000]+[0]*15);self.assertEqual(f.events(),[(172,0,1000),(174,0,1000)])
  f.packet(0x1000,[1200]+[0]*15);self.assertEqual(f.custom(),[]);self.assertEqual(f.events(),[(174,0,1200)])
  f.packet(0x1000);self.assertEqual(f.events(),[(173,0,0),(174,0,0)])
 def test_full_queue_claims_silent_without_overwrite(self):
  f=Input();f.packet(0x400);f.word(UIQUEUE+0x21a0,225);f.word(UIQUEUE+0x2180,1)
  before=bytes(f.u.mem_read(UIQUEUE+0x980,256*24));f.packet(0x400,[1000]+[0]*15)
  self.assertEqual(f.events(),[]);self.assertEqual(f.readword(STATE+8),1);self.assertEqual(bytes(f.u.mem_read(UIQUEUE+0x980,256*24)),before)
 def test_ambiguous_modifiers_do_not_trigger_notes_or_actions(self):
  for mask in [0x3000,0x2400,0x1400,0x3400]:
   f=Input();f.packet(mask,[1000]+[0]*15);self.assertEqual(f.events(),[]);self.assertEqual(f.custom(),[])
   f.packet(0,[1500]+[0]*15);self.assertEqual(f.events(),[])
   f.packet();self.assertEqual(f.events(),[])
 def test_disabled_preserves_note_input(self):
  f=Input();f.u.mem_write(STATE+12,b'\0');f.packet(0x2000,[1000]+[0]*15);self.assertEqual(f.events(),[(172,0,1000),(174,0,1000)]);self.assertEqual(f.custom(),[])
 def test_startup_zeroes_only_m7_cache_line(self):
  f=Input();f.u.mem_write(STATE,bytes([0xa5])*256);f.u.reg_write(UC_ARM_REG_SP,0x2407e000)
  f.u.emu_start(0x080d0801,0x080404ba,count=200000)
  self.assertEqual(f.u.reg_read(UC_ARM_REG_PC),0x080404ba)
  self.assertEqual(bytes(f.u.mem_read(STATE+32,224)),bytes([0xa5])*224)
  self.assertEqual(bytes(f.u.mem_read(STATE+16,16)),bytes(range(16)))
if __name__=='__main__':unittest.main(verbosity=2)
