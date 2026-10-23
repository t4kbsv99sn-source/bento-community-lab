"""Compiled double-tap timing; native page construction is tested separately."""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1
from test_integration import Fixture,UU,KEYS
class Gesture(Fixture):
 def __init__(self):
  super().__init__();self.registry();self.m=0x30024b00
  self.u.mem_write(self.m+0x12c,b'\x17')
  def nav(u,a,n,d):
   page=u.reg_read(UC_ARM_REG_R1);self.navlog.append(page);self.u.mem_write(self.m+0x12c,bytes([page]));self.ret()
  self.u.hook_add(UC_HOOK_CODE,nav,begin=0x081420ec,end=0x081420ec)
 def evt(self,code,index,ms):
  self.w(0x3001fe2c,ms)
  result=self.call(UU['fx_dispatch'],self.m,code,0,index)
  if code==0xaf and index==2 and not result:self.u.mem_write(self.m+0x12c,b'\x02')
  return result
 def tap(self,start):
  self.assert_pass=self.evt(0xaf,2,start)
  return self.evt(0xb0,2,start+50)
class Tests(unittest.TestCase):
 def test_first_tap_is_immediate_native_second_tap_opens_fx_and_eats_release(self):
  p=Gesture();self.assertEqual(p.tap(1000),0);self.assertEqual(p.assert_pass,0);self.assertEqual(p.navlog,[])
  self.assertEqual(p.evt(0xaf,2,1200),1);self.assertEqual(p.navlog,[0x1a])
  self.assertEqual(p.evt(0xb0,2,1250),1)
  self.assertEqual(p.evt(0xaf,2,1500),0)
 def test_slow_second_tap_does_not_open(self):
  p=Gesture();p.tap(1000);self.assertEqual(p.evt(0xaf,2,1500),0);self.assertEqual(p.navlog,[])
 def test_long_hold_cannot_count_as_first_tap(self):
  p=Gesture();p.evt(0xaf,2,1000);p.evt(0xb0,2,1600)
  self.assertEqual(p.evt(0xaf,2,1700),0);self.assertEqual(p.navlog,[])
 def test_hold_pad_shift_other_button_or_page_change_cancel_double_tap(self):
  for action in ['pad','used','shift','button','page']:
   p=Gesture();p.evt(0xaf,2,1000)
   if action=='pad':p.evt(0xfe,0,1020)
   if action=='used':p.w(0x24048cc8,1)
   p.evt(0xb0,2,1050)
   if action=='shift':p.w(0x24048d68,1)
   if action=='button':p.evt(0xaf,5,1100)
   if action=='page':p.u.mem_write(p.m+0x12c,b'\x07')
   self.assertEqual(p.evt(0xaf,2,1200),0,action);self.assertEqual(p.navlog,[],action)
 def test_tick_wrap_and_non_user_messages(self):
  p=Gesture();p.tap(0xffffffb0);p.evt(0x3f,0,0xfffffff0)
  self.assertEqual(p.evt(0xaf,2,30),1)
 def test_registry_refuses_collision_without_altering_existing_definition(self):
  p=Gesture();key=KEYS[0];p.w(0x20020000+key*32,0xabcd);p.w(0x20020000+key*32+4,0x12345678)
  p.tap(1000);self.assertEqual(p.evt(0xaf,2,1200),1);self.assertEqual(p.navlog,[])
  self.assertEqual(p.r(0x20020000+key*32+4),0x12345678)
if __name__=='__main__':unittest.main(verbosity=2)
