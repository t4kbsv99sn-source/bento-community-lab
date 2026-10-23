"""Run real native track-edit, property setter and engine packet writer.
Only dirty notification, child lookup misses and UI queue delivery are substitutes.
No model-edit or audio-command substitute is used in the corrected mixer path.
"""
import unittest,struct
from test_controls import Fixture,REGS
from unicorn.arm_const import *
class NativeMixer(Fixture):
 def __init__(self):
  super().__init__();self.engine=0x30010000;self.w(0x3000f650,self.engine)
  self.w(self.vtable+0x14,0x081ff021);self.ui=[]
  for t in range(8):
   self.props[(self.obj+t*0x100,0x13d)]=0;self.props[(self.obj+t*0x100,0x13e)]=0
 def hook(self,u,a,size,data):
  if a==0x08131ae0:return # Execute original native track-level handler.
  if a in [0x0813130c,0x081ff020,0x08173272]:
   r=[u.reg_read(x) for x in REGS[:4]]
   if a==0x081ff020:self.w(r[2],0)
   if a==0x08173272:self.ui.append(bytes(u.mem_read(r[1],20)))
   self.ret();return
  super().hook(u,a,size,data)
 def packet(self,i=0):return struct.unpack('<BBh4I2h',self.u.mem_read(self.engine+24*i,24))
 def value(self,track,key):
  self.u.reg_write(UC_ARM_REG_R0,self.obj+track*0x100);self.u.reg_write(UC_ARM_REG_R1,key)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000);self.u.reg_write(UC_ARM_REG_LR,0x0813f2fd)
  self.u.emu_start(0x0812dc75,0,count=100)
  return self.u.reg_read(UC_ARM_REG_R0)
class Tests(unittest.TestCase):
 def test_all_mutes_and_solos_queue_native_track_addressed_audio_commands(self):
  for track in range(8):
   for action,key in [(5,0x13e),(6,0x13d)]:
    f=NativeMixer();f.pad(action,track)
    p=f.packet()
    self.assertEqual(p[0],0x3e);self.assertEqual(p[4],0xfffffffe)
    self.assertEqual(p[5:7],(key,1));self.assertEqual(p[7],track)
    self.assertEqual(f.r(f.engine+0x620),1)
    self.assertEqual(f.value(track,key),1)
    self.assertEqual(struct.unpack('<5I',f.ui[-1]),(0xc3,77+track,key,1,0))
 def test_second_press_sends_native_off_command_and_clears_model(self):
  for action,key in [(5,0x13e),(6,0x13d)]:
   f=NativeMixer();f.pad(action,4);f.pad(action,4)
   self.assertEqual(f.packet(1)[5:8],(key,0,4));self.assertEqual(f.value(4,key),0)
 def test_multiple_solos_do_not_clear_each_other(self):
  f=NativeMixer();f.pad(5,1);f.pad(5,6)
  self.assertEqual(f.value(1,0x13e),1);self.assertEqual(f.value(6,0x13e),1)
  self.assertEqual([f.packet(i)[7] for i in range(2)],[1,6])
 def test_mixer_release_restores_screen_without_reversing_audio_command(self):
  f=NativeMixer();f.event(175,5);f.pad(6,7);f.event(176,5)
  self.assertEqual(f.page(),23);self.assertEqual(f.value(7,0x13d),1)
  self.assertEqual(f.r(f.engine+0x620),1)
if __name__=='__main__':unittest.main(verbosity=2)
