"""Execute T1 native gate, loop wrapper, editor and event XML byte paths.
Synthetic sequence objects and XML dependencies; no real-time device emulation.
"""
import unittest,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_plock import Probe,REGS
from test_controls import IMAGE,STOCK
from conditions import STATE,TABLE,LABELS

class ConditionProbe(Probe):
 def __init__(self):
  super().__init__();self.w(self.seq+0x86c0,0x2002c000)
 def boundary(self,step=15):
  self.w(self.seq+0x14,step)
  before=[0x100+i for i in range(13)];before[0]=self.seq
  for reg,value in zip(REGS,before):self.u.reg_write(reg,value)
  sp=0x2003c000;self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x20035001)
  self.u.reg_write(UC_ARM_REG_APSR,0xa0000000)
  self.u.emu_start(0x08061741,0x08061744,count=10000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x08061744
  assert self.u.reg_read(UC_ARM_REG_SP)==sp-28
  assert [self.u.reg_read(r) for r in REGS]==before
  assert self.u.reg_read(UC_ARM_REG_APSR)&0xf8000000==0xa0000000
 def gate(self,cond,roll=0,velocity=100):
  sp=0x2003c000;self.u.mem_write(sp,bytes(0x100));self.u.mem_write(sp+0x29,bytes([cond]));self.u.mem_write(sp+0x3a,struct.pack('<H',velocity))
  before=[0x200+i for i in range(13)];before[8]=self.seq;before[11]=velocity
  for reg,value in zip(REGS,before):self.u.reg_write(reg,value)
  self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x20035001)
  reached=[];rolls=[]
  def hook(u,a,s,d):
   if a in (0x08060b7c,0x080609e2):reached.append(a);u.emu_stop()
   elif a==0x080a40b8:
    rolls.append(roll);u.reg_write(UC_ARM_REG_R0,roll);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  h=self.u.hook_add(UC_HOOK_CODE,hook)
  try:self.u.emu_start(0x08060b65,0,count=10000)
  finally:self.u.hook_del(h)
  assert len(reached)==1
  assert self.u.reg_read(UC_ARM_REG_SP)==sp
  assert [self.u.reg_read(r) for r in REGS[4:11]]==before[4:11]
  assert self.u.mem_read(sp+0x29,1)[0]==cond
  return reached[0]==0x08060b7c,rolls
 def fragment(self,a,stop,registers=None):
  self.u.reg_write(UC_ARM_REG_SP,0x2003c000)
  for reg,v in (registers or {}).items():self.u.reg_write(reg,v)
  self.u.emu_start(a|1,stop,count=10000)
  assert self.u.reg_read(UC_ARM_REG_PC)==stop
 def word(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]

class Tests(unittest.TestCase):
 def test_all_35_ratios_across_16_native_loop_boundaries(self):
  p=ConditionProbe()
  for loop in range(16):
   p.boundary(-1 if loop==0 else 15)
   for i,label in enumerate(LABELS):
    a,b=map(int,label.split(':'));played,rolls=p.gate(100+i)
    self.assertEqual(played,loop%b==a-1,(loop,label));self.assertEqual(rolls,[])
 def test_native_chances_and_always_are_unchanged(self):
  p=ConditionProbe()
  for cond in [0,1,25,50,98,99,135,255]:
   for roll in [0,1,25,50,99]:
    played,rolls=p.gate(cond,roll)
    self.assertEqual(played,True if cond==0 or cond>=100 else roll<=cond)
    self.assertEqual(len(rolls),1 if 1<=cond<=99 else 0)
 def test_restart_clip_switch_and_owner_change_reset_counter(self):
  p=ConditionProbe();p.boundary(-1);p.boundary();self.assertFalse(p.gate(100)[0])
  p.boundary(-1);self.assertTrue(p.gate(100)[0])
  p.boundary();p.w(p.seq+0x86c0,0x2002d000);p.boundary();self.assertTrue(p.gate(100)[0])
  p.boundary();p.w(p.seq+12,78);p.boundary();self.assertTrue(p.gate(100)[0])
 def test_tracks_count_independently_and_one_step_loops_advance(self):
  p=ConditionProbe();first=p.seq;p.boundary(-1);p.boundary(0)
  second=0x20030000;p.seq=second;p.w(second+12,88);p.w(second+0x86c0,0x2002d000);p.boundary(-1)
  self.assertTrue(p.gate(100)[0]);p.seq=first;self.assertFalse(p.gate(100)[0])
 def test_gate_keeps_native_default_velocity(self):
  p=ConditionProbe();self.assertTrue(p.gate(100,velocity=0)[0]);self.assertEqual(p.u.reg_read(UC_ARM_REG_R11),100)
 def test_state_full_falls_back_to_native_always(self):
  p=ConditionProbe()
  for i in range(16):p.w(STATE+i*32,0x20010000+i*0x100)
  self.assertTrue(p.gate(100)[0])
 def test_on_screen_table_preserves_native_entries_and_appends_labels(self):
  self.assertEqual(IMAGE[TABLE-0x08040000:TABLE-0x08040000+400],STOCK[0x0819f30c-0x08040000:0x0819f30c-0x08040000+400])
  for i,label in enumerate(LABELS):
   ptr=struct.unpack_from('<I',IMAGE,TABLE-0x08040000+(100+i)*4)[0]
   self.assertEqual(IMAGE[ptr-0x08040000:].split(b'\0')[0].decode(),label)
 def test_drum_and_piano_display_the_correct_condition_index(self):
  p=ConditionProbe();sp=0x2003c000;dest=0x20027000
  for raw in range(135):
   expected=99 if raw==0 else raw-1 if raw<100 else raw
   p.u.mem_write(sp+0x49,bytes([raw]));p.fragment(0x08159b74,0x08159b18,{UC_ARM_REG_R6:dest});self.assertEqual(p.word(dest),expected)
   p.u.mem_write(sp+1,bytes([raw]));p.fragment(0x0815c3bc,0x0815c352,{UC_ARM_REG_R1:dest});self.assertEqual(p.word(dest),expected)
 def test_drum_edit_stores_the_visible_condition_without_offset(self):
  p=ConditionProbe()
  for pos in range(135):
   p.fragment(0x0815c8b4,0x0815c8be,{UC_ARM_REG_R1:pos})
   expected=0 if pos==99 else pos+1 if pos<99 else pos
   self.assertEqual(p.u.reg_read(UC_ARM_REG_R6),expected)
 def test_piano_edit_and_reference_match_for_existing_and_new_values(self):
  p=ConditionProbe();sp=0x2003c000
  for raw in range(135):
   p.u.mem_write(sp+0x25,bytes([raw]));p.fragment(0x08158f1c,0x08158f26)
   current=p.u.reg_read(UC_ARM_REG_R3)
   self.assertEqual(current,100 if raw==0 else raw if raw<100 else raw+1)
   for target in [0,1,98,99,100,101,134]:
    delta=target+1-current
    p.u.mem_write(sp+0x19,bytes([raw]));p.w(sp+0x84,delta)
    p.fragment(0x08158a7c,0x08158aac)
    expected=0 if target==99 else target+1 if target<99 else target
    self.assertEqual(p.u.mem_read(sp+0x31,1)[0],expected,(raw,target))
 def test_native_xml_cond_byte_write_and_read_preserves_all_choices(self):
  p=ConditionProbe();sp=0x2003c000;captured=[];selected=[0]
  def hook(u,a,s,d):
   if a in (0x08109cdc,0x08109c64):
    ptr=u.reg_read(UC_ARM_REG_R1);self.assertEqual(bytes(u.mem_read(ptr,5)),b'cond\0');u.reg_write(UC_ARM_REG_R0,0x20026000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   elif a==0x0810958e:
    captured.append(u.reg_read(UC_ARM_REG_R1));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   elif a==0x08109566:
    p.w(u.reg_read(UC_ARM_REG_R1),selected[0]);u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  h=p.u.hook_add(UC_HOOK_CODE,hook)
  try:
   for raw in range(135):
    p.u.mem_write(sp+9,bytes([raw]));p.fragment(0x0812f3c4,0x0812f3d4)
    self.assertEqual(captured[-1],raw);selected[0]=captured[-1];p.w(sp+0x20,0)
    p.fragment(0x0812fd02,0x0812fd18,{UC_ARM_REG_R4:0x20026000})
    self.assertEqual(p.u.mem_read(sp+0x25,1)[0],raw)
  finally:p.u.hook_del(h)
 def test_startup_clears_all_counter_slots_without_touching_ui(self):
  from test_input import Input
  p=Input();p.u.mem_write(STATE,bytes([0xa5])*512);p.u.reg_write(UC_ARM_REG_SP,0x2407e000)
  p.u.emu_start(0x080d0801,0x080404ba,count=20000)
  self.assertEqual(bytes(p.u.mem_read(STATE,512)),bytes(512))

if __name__=='__main__':unittest.main(verbosity=2)
