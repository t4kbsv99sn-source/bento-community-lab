"""Compiled K7 editor, persistence and DSP handoff; native widgets/XML are substitutes."""
import struct,unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_controls import Fixture,REGS
from kick_ui_build import SYMS,WRAP
from test_kick import Kick
from kick_build import SYMS as DSP
KEYS=[0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9]
DEFAULT=[55,65,45,65,55,25,25]
class UI(Fixture):
 def __init__(self):
  super().__init__();self.v=0x20000000;self.o=0x2001b000;self.e=0x2001c000;self.calls=[];self.path='\\Projects\\BENTO_Kick_K2.wav';self.type=1;self.pad_index=0;self.attrs={};self.ids={};self.nextattr=0x2001e000;self.params=0x2001d000
  self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  self.w(0x30031484,0x20020000);self.w(self.v+0x87bc,0x13e);self.w(self.v+0x87c4,0x13f);self.u.mem_write(self.v+0x87cc,b'\x0e')
  self.u.mem_write(self.o+4,b'\x01');self.w(self.o+0x10,0x13e)
  for i in range(24):self.u.mem_write(self.v+0x6fdc+i*2,struct.pack('<H',i+1))
  self.u.hook_add(UC_HOOK_CODE,self.native)
 def text(self,p):
  out=bytearray()
  for i in range(256):
   c=self.u.mem_read(p+i,1)[0]
   if not c:return out.decode()
   out.append(c)
  raise AssertionError('unterminated string')
 def native(self,u,a,size,data):
  r=[u.reg_read(x) for x in REGS[:4]]
  if a==0x081ba1c0 and not getattr(self,'real_install',False):self.ret()
  elif a==0x08133f7c:self.ret(self.type)
  elif a==0x0813390e:u.mem_write(r[3],self.path.encode()+b'\0');self.ret()
  elif a==0x08133614:self.w(r[3],self.pad_index);self.ret()
  elif a==0x08171c1c:self.calls.append(('widget',*r));self.ret()
  elif a==0x0817e85e:self.calls.append(('title',r[0],self.text(r[1])));self.ret()
  elif a==0x08170656:self.calls.append(('value',r[0],r[1],self.text(r[2]) if r[2] else ""));self.ret()
  elif a==0x081689f8:self.calls.append(('envelope',*r));self.ret()
  elif a in [0x08152144,0x08152acc,0x08152bb0,0x0813130c]:self.calls.append(('native',a,*r));self.ret()
  elif a==0x08109268:self.ret(self.params if self.text(r[1])=='params' else 0)
  elif a in [0x08109cdc,0x08109c64]:
   key=self.text(r[1])
   if a==0x08109cdc and key not in self.attrs:self.attrs[key]=0
   if key not in self.attrs:self.ret(0);return
   if key not in self.ids:self.ids[key]=self.nextattr;self.nextattr+=4
   self.ret(self.ids[key])
  elif a==0x0810958e:self.attrs[next(k for k,v in self.ids.items() if v==r[0])]=r[1];self.ret()
  elif a==0x08109566:self.w(r[1],self.attrs[next(k for k,v in self.ids.items() if v==r[0])]);self.ret(0)
 def call(self,name,*args):
  for reg,v in zip(REGS,args):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000);self.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  self.u.emu_start(SYMS[name]|1,0x081ff200,count=200000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x081ff200
  return self.u.reg_read(UC_ARM_REG_R0)
 def event(self,key,value):
  self.u.mem_write(self.e,struct.pack('<4I',0xcf,0x13e,key,value&0xffffffff))
  return self.call('kick_ui_event',self.v,self.e)
 def values(self):return list(self.u.mem_read(0x24043528,7))
 def prepare(self):self.call('kick_ui_before',self.v);self.call('kick_ui_after',self.v)
class Tests(unittest.TestCase):
 def test_requested_rows_and_click_only_third_row(self):
  p=UI();p.prepare()
  self.assertEqual(list(struct.unpack('<8H',p.u.mem_read(p.v+0x703c,16))),[2]+KEYS)
  self.assertEqual(list(struct.unpack('<8H',p.u.mem_read(p.v+0x708c,16))),[0x1aa,0x1ad,4,0xe5,0x36,0x37,0x32,0x33])
  self.assertEqual(bytes(p.u.mem_read(p.v+0x70dc,16)),__import__("struct").pack("<8H",0x1b0,0,0,0,0,0,0,0))
  self.assertEqual(bytes(p.u.mem_read(p.v+0x4858,1)),b'\0');self.assertEqual(bytes(p.u.mem_read(p.v+0x71f0,1)),b'\1')
  self.assertIn(('title',p.v+0x80b4,'Kick / Pad 1'),p.calls)
 def test_all_seven_knobs_edit_actual_sound_not_file_and_mark_project_dirty(self):
  p=UI();p.prepare()
  for key,value in zip(KEYS,[70,90,80,50,40,30,20]):self.assertEqual(p.event(key,value),1)
  self.assertEqual(p.values(),[70,90,80,50,40,30,20]);self.assertEqual(p.r(0x24043524),0x13e)
  self.assertEqual(len([c for c in p.calls if c[:2]==('native',0x0813130c)]),7)
 def test_bounds_and_native_mix_fallthrough(self):
  p=UI();p.prepare();p.event(KEYS[0],-100);self.assertEqual(p.values()[0],25)
  p.event(KEYS[0],1000);self.assertEqual(p.values()[0],180)
  p.event(KEYS[1],-1);self.assertEqual(p.values()[1],0)
  p.event(KEYS[1],101);self.assertEqual(p.values()[1],100)
  for key in [2,4,0xe5,0x36,0x37,0x32,0x33]:self.assertEqual(p.event(key,50),0)
 def test_pad_and_load_reuse_native_navigation(self):
  p=UI();p.prepare();p.event(0x1aa,2);p.event(0x1ad,1)
  self.assertTrue(any(c[:4]==('native',0x08152acc,p.v,1) for c in p.calls))
  self.assertTrue(any(c[:3]==('native',0x08152bb0,p.v) for c in p.calls))
 def test_ordinary_sample_restores_original_three_rows_and_wave(self):
  p=UI();p.prepare();p.path='\\Drums\\normal.wav';p.call('kick_ui_before',p.v)
  for row in range(3):self.assertEqual(list(struct.unpack('<8H',p.u.mem_read(p.v+0x703c+row*0x50,16))),list(range(row*8+1,row*8+9)))
  self.assertEqual(bytes(p.u.mem_read(p.v+0x4858,1)),b'\0');self.assertEqual(bytes(p.u.mem_read(p.v+0x71f0,1)),b'\0')
  self.assertEqual(p.event(KEYS[0],80),0)
 def test_unrelated_names_parent_and_collision_are_not_modified(self):
  for cause in ['name','parent','registry']:
   p=UI()
   if cause=='name':p.path='BENTO_Kick_K2_other.wav'
   if cause=='parent':p.u.mem_write(p.v+0x87cc,b'\x11')
   if cause=='registry':p.w(0x20020000+KEYS[0]*32,KEYS[0]);p.w(0x20020000+KEYS[0]*32+4,0x1234)
   p.call('kick_ui_before',p.v);self.assertEqual(p.r(0x24043d28),0)
 def test_each_sound_has_its_own_values(self):
  p=UI();p.prepare();p.event(KEYS[0],80);p.w(p.v+0x87bc,0x140);p.prepare()
  self.assertEqual(list(p.u.mem_read(0x24043538,7)),DEFAULT)
  p.event(KEYS[0],110);self.assertEqual(p.values()[0],80)
 def test_versioned_params_roundtrip_and_unknown_attributes_are_not_used(self):
  p=UI();p.prepare();p.event(KEYS[0],87);p.event(KEYS[5],73);p.call('kick_ui_save',p.o,p.params)
  self.assertEqual(len(p.attrs),10);self.assertEqual(p.attrs['bento_kick_version'],1)
  p.u.mem_write(0x24043500,bytes(0x820));p.call('kick_ui_load',p.params,p.o)
  self.assertEqual(p.values(),[87,65,45,65,55,73,25])
 def test_missing_unknown_version_and_out_of_range_values_are_safe(self):
  p=UI();p.prepare();p.event(KEYS[0],87);p.call('kick_ui_load',p.params,p.o);self.assertEqual(p.values(),DEFAULT)
  p.attrs={'bento_kick_version':1,'bento_kick_v1_tune':999,'bento_kick_v1_decay':0xffffffff};p.call('kick_ui_load',p.params,p.o)
  self.assertEqual(p.values()[:2],[180,0]);p.attrs={'bento_kick_version':2};p.call('kick_ui_load',p.params,p.o);self.assertEqual(p.values(),DEFAULT)
 def test_non_sampler_objects_do_not_save_or_load_kick_state(self):
  p=UI();p.prepare();p.u.mem_write(p.o+4,b'\x0e');p.call('kick_ui_save',p.o,p.params);self.assertEqual(p.attrs,{})
 def test_xml_load_wrapper_replays_original_prologue_and_preserves_registers(self):
  p=UI();sp=0x20030000;before=[0x1010+i for i in range(13)];before[:2]=[p.params,p.o]
  for reg,v in zip(REGS,before):p.u.reg_write(reg,v)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x0812faad,0x0812fab0,count=200000)
  self.assertEqual([p.u.reg_read(r) for r in REGS],before);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-40)
 def test_ui_values_reach_real_dsp_using_sound_handle(self):
  p=UI();p.prepare();p.event(KEYS[0],93);p.event(KEYS[2],17)
  k=Kick();k.w(k.root+12,0x13e);k.u.mem_write(0x24043500,bytes(p.u.mem_read(0x24043500,0x820)))
  k.call(DSP['kick_parameters'],k.root,0x2001f000);self.assertEqual(list(k.u.mem_read(0x2001f000,7)),[93,65,17,65,55,25,25])
  k.start();ok,a=k.render();self.assertEqual(ok,1);self.assertGreater(max(abs(x) for x in a),.001)
 def test_xml_save_wrapper_preserves_registers_and_replays_original_instructions(self):
  p=UI();p.prepare();sp=0x20030000;before=[0x2010+i for i in range(13)];before[0]=p.params;before[6]=p.o
  for reg,v in zip(REGS,before):p.u.reg_write(reg,v)
  for i in range(32):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*7)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x0812f5eb,0x0812f5ee,count=200000)
  before[4]=0;before[8]=p.params
  self.assertEqual([p.u.reg_read(r) for r in REGS],before);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
  for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*7)
  self.assertEqual(p.attrs['bento_kick_version'],1)
 def test_event_fallback_preserves_native_registers_and_stack(self):
  p=UI();sp=0x20030000;p.u.mem_write(p.e,struct.pack('<4I',0xcf,0x13e,4,50));before=[0x3010+i for i in range(13)];before[:2]=[p.v,p.e]
  for reg,v in zip(REGS,before):p.u.reg_write(reg,v)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x08152c51,0x08152c54,count=200000)
  self.assertEqual([p.u.reg_read(r) for r in REGS],before);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-0x1f0)
 def test_two_tunes_produce_different_audio_and_torn_ui_commit_is_ignored(self):
  outputs=[]
  for tune in [35,140]:
   p=UI();p.prepare();p.event(KEYS[0],tune);k=Kick();k.w(k.root+12,0x13e);k.u.mem_write(0x24043500,bytes(p.u.mem_read(0x24043500,0x820)));k.start();outputs.append(k.render()[1])
  self.assertGreater(sum(abs(a-b) for a,b in zip(*outputs)),.01)
  k.w(0x24043520,3);k.call(DSP['kick_parameters'],k.root,0x2001f000);self.assertEqual(list(k.u.mem_read(0x2001f000,7)),DEFAULT)
if __name__=='__main__':unittest.main(verbosity=2)
