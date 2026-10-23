"""Compiled K2 installer with a controlled filesystem backend.
Actual SD media and Load/browser behaviour still require a device check.
"""
import unittest,struct,wave,io
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_controls import Fixture,REGS
from kick_install_build import SYMS,WRAP
REPORT='\\Projects\\BENTO_K7_DIAGNOSTICS.txt'
PATH='\\Projects\\BENTO_Kick_K2.wav'
class Install(Fixture):
 def __init__(self):
  super().__init__();self.files={};self.open_files={};self.io=[];self.fail_open=None;self.fail_write=False;self.short_write=False;self.fail_close=False
  self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  self.u.hook_add(UC_HOOK_CODE,self.filesystem)
 def cstr(self,p):
  out=bytearray()
  while len(out)<256:
   x=self.u.mem_read(p+len(out),1)[0]
   if not x:return out.decode()
   out.append(x)
  raise AssertionError('unterminated filesystem path')
 def filesystem(self,u,a,size,data):
  r=[u.reg_read(x) for x in REGS[:4]]
  if a==0x08120148:
   f,path,mode=r[0],self.cstr(r[1]),r[2];self.io.append(('open',path,mode))
   if self.fail_open is not None:self.ret(self.fail_open);return
   if mode==1 and path not in self.files:self.ret(4);return
   if mode==6 and path in self.files:self.ret(8);return
   if mode in [6,10]:self.files[path]=bytearray()
   self.open_files[f]=[path,0];self.w(f+0x10,len(self.files[path]));self.w(f+0x14,0);self.ret(0)
  elif a==0x08120464:
   f,buf,n,got=r;path,pos=self.open_files[f];part=self.files[path][pos:pos+n]
   u.mem_write(buf,bytes(part));self.open_files[f][1]+=len(part);self.w(got,len(part));self.ret(0)
  elif a==0x08120604:
   f,buf,n,got=r;path,pos=self.open_files[f];self.io.append(('write',path,n))
   if self.fail_write:self.w(got,0);self.ret(1);return
   done=n-1 if self.short_write else n
   self.files[path][pos:pos+done]=u.mem_read(buf,done);self.open_files[f][1]+=done;self.w(got,done);self.ret(0)
  elif a==0x08120974:
   self.io.append(('close',self.open_files[r[0]][0]));del self.open_files[r[0]];self.ret(int(self.fail_close))
 def call(self,name,*args):
  for reg,v in zip(REGS,args):self.u.reg_write(reg,v)
  self.u.reg_write(UC_ARM_REG_SP,0x20030000);self.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  self.u.emu_start(SYMS[name]|1,0x081ff200,count=5000000)
  self.assert_stopped();return self.u.reg_read(UC_ARM_REG_R0)
 def assert_stopped(self):assert self.u.reg_read(UC_ARM_REG_PC)==0x081ff200

class Tests(unittest.TestCase):
 def test_firmware_generates_the_complete_exact_marker_without_external_file(self):
  p=Install();self.assertEqual(p.call('kick_install'),1);data=bytes(p.files[PATH])
  with wave.open(io.BytesIO(data),'rb') as w:
   self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()),(1,2,48000,144019))
   pcm=w.readframes(144019)
  self.assertEqual(pcm[:64],struct.pack('<32h',*[1 if 0xb1e70a5c&(1<<i) else -1 for i in range(32)]))
  self.assertEqual(pcm[64:],bytes((144019-32)*2));self.assertEqual(len(data),288082)
  self.assertEqual(p.open_files,{})
 def test_existing_valid_entry_is_only_read_and_not_rewritten(self):
  p=Install();p.call('kick_install');before=bytes(p.files[PATH]);p.io=[]
  self.assertEqual(p.call('kick_install'),1);self.assertEqual(bytes(p.files[PATH]),before)
  self.assertFalse(any(x[0]=='write' for x in p.io));self.assertEqual(p.open_files,{})
 def test_existing_unrelated_or_damaged_file_is_never_overwritten(self):
  for data in [b'my own file',bytes(288082)]:
   p=Install();p.files[PATH]=bytearray(data);self.assertEqual(p.call('kick_install'),0)
   self.assertEqual(bytes(p.files[PATH]),data);self.assertFalse(any(x[0]=='write' and x[1]==PATH for x in p.io))
   self.assertEqual(p.open_files,{})
 def test_missing_card_read_only_disk_and_other_open_errors_do_not_create(self):
  for error in [1,3,5,7,10,12]:
   p=Install();p.fail_open=error;self.assertEqual(p.call('kick_install'),0);self.assertEqual(p.files,{})
 def test_failed_or_short_write_stops_and_closes_the_file(self):
  for attr in ['fail_write','short_write']:
   p=Install();setattr(p,attr,True);self.assertEqual(p.call('kick_install'),0)
   self.assertEqual(len([x for x in p.io if x[0]=='write' and x[1]==PATH]),1);self.assertEqual(p.open_files,{})
 def test_close_error_is_reported_without_retry_or_other_file_changes(self):
  p=Install();p.fail_close=True;self.assertEqual(p.call('kick_install'),0);self.assertEqual(set(p.files),{PATH,'\\Projects\\BENTO_Synth_Snare.wav','\\Projects\\BENTO_Synth_HiHat.wav'})
 def test_only_the_native_oneshot_load_event_runs_the_installer(self):
  for event in [0x3f,0xcf,0x40,0x110,0x111]:
   p=Install();p.w(0x2001c000,event);p.call('kick_load_entry',0x2001b000,0x2001c000)
   self.assertEqual(bool(p.files),event==0x3f)
 def test_native_load_wrapper_preserves_registers_floats_and_replays_prologue(self):
  p=Install();event=0x2001c000;p.w(event,0x3f);sp=0x20030000
  before=[0x10100+i for i in range(13)];before[0:2]=[0x2001b000,event]
  for reg,v in zip(REGS,before):p.u.reg_write(reg,v)
  for i in range(32):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*7)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x081ff201)
  p.u.emu_start(0x081512a5,0x081512a8,count=5000000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x081512a8);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-56)
  self.assertEqual([p.u.reg_read(x) for x in REGS],before)
  for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*7)
  self.assertEqual(set(p.files),{PATH,REPORT,'\\Projects\\BENTO_Synth_Snare.wav','\\Projects\\BENTO_Synth_HiHat.wav'})

if __name__=='__main__':unittest.main(verbosity=2)
