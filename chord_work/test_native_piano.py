"""Actual stock piano-roll construction and projection of inserted native notes.
Font/model services are fixtures; this is not a rendered device screenshot.
"""
import unittest,gc
from test_native_insert import Native
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
class Piano(Native):
 def __init__(self):
  super().__init__();self.registry();self.view=0xc0200000;self.u.mem_map(self.view,0x200000);self.call(0x0815930c,self.view)
  for off,value in [(0x11cd00,self.seq),(0x11cd08,self.owner),(0x11cd18,16),(0x11cd10,0),(0x11cd14,4)]:self.w(self.view+off,value)
  self.u.mem_write(self.view+0x125dae,b'\0') # native pitched projection branch
  self.u.mem_write(self.model+0x12c,b'\x17') # native SEQ handler 08142D58: pitched tracks use page 17
class Tests(unittest.TestCase):
 def test_native_piano_constructs_all_eight_encoder_slots(self):
  p=Piano();self.assertEqual(p.r(p.view),0x0819e7b0);p.call(0x081599bc,p.view)
  rects=[[p.r(p.view+0x55f0+0x38+i*0x468+off) for off in [4,8,12,16]] for i in range(8)]
  self.assertEqual([r[0] for r in rects],sorted(r[0] for r in rects));self.assertTrue(all(r[2]>140 and r[3]==70 for r in rects))
 def test_inserted_chords_project_through_actual_piano_roll_using_pitch_field(self):
  p=Piano();self.assertEqual(p.insert(),0);seen=[]
  def project(u,a,n,d):seen.append(tuple(u.reg_read(r) for r in [UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]))
  p.u.hook_add(UC_HOOK_CODE,project,begin=0x08176708,end=0x08176708);p.call(0x0815abb8,p.view,0,0)
  self.assertEqual(len(seen),12);self.assertEqual(seen[:3],[(0,3840,48),(0,3840,52),(0,3840,55)])
  self.assertEqual(sorted(t for t,n,pitch in seen),[0]*3+[3840]*3+[7680]*3+[11520]*3)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
