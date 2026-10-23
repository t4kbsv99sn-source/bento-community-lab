"""Shift+physical step clearing and preservation of the native moving playhead."""
import unittest
from test_editable_locks import UIProbe,word
from test_controls import IMAGE,STOCK,BASE
from step_locks import U_SYMS

class Tests(unittest.TestCase):
 def shifted(self,p,down):
  p.w(0x24048d68,int(down));p.shift(down)
 def test_shift_tap_clears_only_pressed_lock_and_keeps_the_trigger(self):
  p=UIProbe();p.w(p.container+20,word(1,-18000));p.w(p.container+24+20,word(3,-500))
  first=bytes(p.u.mem_read(p.container,20));self.shifted(p,True)
  p.press(0);self.assertEqual(p.stored(),0);self.assertEqual(p.stored(1),word(3,-500))
  self.assertEqual(bytes(p.u.mem_read(p.container,20)),first)
  self.shifted(p,False);p.time(5100);p.release(0)
  self.assertNotIn(('toggle',0),p.log);self.assertEqual(p.word(0x24048d6c),1)
 def test_shift_tap_empty_and_unlocked_steps_never_toggle_notes(self):
  for pad in [0,4]:
   for shift_first in [True,False]:
    p=UIProbe();before=bytes(p.u.mem_read(p.container,0x3004));self.shifted(p,True);p.press(pad)
    p.time(5100)
    if shift_first:self.shifted(p,False);p.release(pad)
    else:p.release(pad);self.shifted(p,False)
    self.assertEqual(bytes(p.u.mem_read(p.container,0x3004)),before)
    self.assertFalse(any(x[0]=='toggle' for x in p.log))
 def test_shift_clear_uses_native_bank_scroll_and_current_drum(self):
  p=UIProbe();p.notes([(20,2,101,64),(20,3,100,90),(24,2,102,80)])
  for i in range(3):p.w(p.container+i*24+20,word(3,-500))
  p.w(p.view+0x11404,16);p.w(p.view+0x113f4,8);self.shifted(p,True);p.press(4)
  self.assertEqual(p.stored(),0);self.assertEqual(p.stored(1),word(3,-500));self.assertEqual(p.stored(2),word(3,-500))
 def test_shift_clear_does_not_clear_another_held_steps_lock(self):
  p=UIProbe();p.w(p.container+20,word(1,-18000));p.w(p.container+24+20,word(1,-9000))
  p.press(0);self.shifted(p,True);p.press(8)
  self.assertEqual(p.stored(),word(1,-18000));self.assertEqual(p.stored(1),0)
 def test_unshifted_short_tap_keeps_original_toggle(self):
  p=UIProbe();p.press(0);p.time(5100);p.release(0)
  self.assertIn(('toggle',0),p.log)
 def test_original_playhead_function_is_byte_exact_and_marker_refresh_never_moves_it(self):
  a=0x0815bde2-BASE;self.assertEqual(IMAGE[a:a+0x52],STOCK[a:a+0x52])
  p=UIProbe();p.w(p.view+0x11408,0xffffffff);p.call(0x0815bde2,p.view,5)
  p.w(p.container+20,word(3,-500));p.press(0);p.call(U_SYMS['locks_grid'],p.view)
  self.assertEqual(p.word(p.view+0x11408),5);self.assertIn(('title','[1*]'),p.screen)
  p.call(0x0815bde2,p.view,6);self.assertEqual(p.word(p.view+0x11408),6)
  outlined=[i for i in range(32) if p.u.mem_read(p.view+0x34+i*0x704+0xec,1)==b'\0']
  self.assertEqual(outlined,[6])

if __name__=='__main__':unittest.main(verbosity=2)
