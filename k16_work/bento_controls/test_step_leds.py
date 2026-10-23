"""Execute native empty/active step branches and original per-pad LED setter."""
import unittest
from test_controls import Fixture,STOCK,IMAGE,BASE
from unicorn.arm_const import *
class Tests(unittest.TestCase):
 def branch(self,pad,active,color=0,original=False):
  f=Fixture()
  if original:f.u.mem_write(BASE,STOCK)
  led=f.m+0x19c4;sp=0x20030000
  # Sentinels prove only the addressed pad changes.
  for i in range(16):f.w(led+i*16,0x123456)
  f.w(sp+4,led);f.w(sp+12,color)
  f.u.reg_write(UC_ARM_REG_SP,sp);f.u.reg_write(UC_ARM_REG_R9,pad)
  f.u.emu_start((0x08139976 if active else 0x081398fe)|1,0x0813990a,count=100)
  self.assertEqual(f.u.reg_read(UC_ARM_REG_PC),0x0813990a)
  for i in range(16):
   if i!=pad:self.assertEqual(f.r(led+i*16),0x123456)
  return f.r(led+pad*16)
 def test_stock_reproduces_cyan_empty_steps(self):
  for pad in range(16):self.assertEqual(self.branch(pad,False,original=True),0x162f2f)
 def test_empty_steps_are_unlit_on_all_pads(self):
  for pad in range(16):self.assertEqual(self.branch(pad,False),0)
 def test_active_steps_preserve_track_color(self):
  for color in [0x7f0000,0x007f00,0x00007f,0x7f7f00,0x7f007f,0x007f7f,0x7f4000,0x40007f]:
   for pad in range(16):self.assertEqual(self.branch(pad,True,color),color)
 def test_active_instruction_path_is_unchanged(self):
  self.assertEqual(IMAGE[0x08139976-BASE:0x0813997e-BASE],STOCK[0x08139976-BASE:0x0813997e-BASE])
if __name__=='__main__':unittest.main(verbosity=2)
