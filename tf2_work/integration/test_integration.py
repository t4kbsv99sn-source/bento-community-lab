"""TF2 native UI/mixer integration. Controlled allocators, track lookup and XML I/O.
Actual stock buffer, gain/pan/mixer and widget code execute in the ARM emulator.
"""
import ctypes,gc,json,math,struct,unittest,os
from pathlib import Path
import numpy as np
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parent
WORK=R.parents[1]
CANDIDATE=Path(os.environ.get('BENTO_FX_CANDIDATE',WORK/'tf2_candidate'))
K16_IMAGE=Path(os.environ.get('BENTO_K16_IMAGE',WORK/'k16_release_verified/bento1.bin'))
IMAGE=(CANDIDATE/'bento1.bin').read_bytes()
MANIFEST=json.loads((CANDIDATE/'manifest.json').read_text())
AA=MANIFEST['audio_symbols'];UU=MANIFEST['ui_symbols']
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
KEYS=[0x1b1,0x1b2,0x1b3,0x1b4,0x1b5,0x1b6,0x1b7,0x1b9,0x1bc,0x1bf,0x1c0,0x1c1,0x1c2,0x1c3,0x1c4,0x1c5,0x1c6,0x1ca,0x1d0]
DEFAULT=[0,120,0,1000,0,1,6000,0,0,-18,3,10,120,1,0,100,0,-1]
class Fixture:
 def __init__(self,image=IMAGE):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
  for a,n in [(0x08040000,0x1c0000),(0x20000000,0x40000),(0x24000000,0x80000),(0x30000000,0x40000),(0xc0000000,0x200000),(0xe000e000,0x2000)]:self.u.mem_map(a,n)
  self.u.mem_write(0x08040000,image);self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  self.stop=0x081ff000;self.next=0xc0100000;self.tracks=[100+i for i in range(8)];self.selected=0;self.attrs={};self.handles={};self.nextattr=0x20018000;self.navlog=[];self.ui_mode=False;self.force_registry=False;self.mailserial=0
  # Font service owns these descriptors on hardware; initialize fixture metrics.
  for i in range(7):
   self.w(0x300000cc+i*4,0x2001c000+i*32);self.u.mem_write(0x2001c000+i*32+9,b"\x10")
  self.u.mem_write(0x081ff100,bytes.fromhex("08207047"))
  for i in range(7):self.w(0x2001c000+i*32+0x14,0x081ff101);self.u.mem_write(0x2001c000+i*32+0xf,b"\x01")
  self.h=[self.u.hook_add(UC_HOOK_CODE,self.hook,begin=a,end=a) for a in [0x0809f940,0x0809f960,0x08104c08,0x08133960,0x0812dc74,0x0813bc3c,0x0813130c,0x08109cdc,0x0810958e,0x08109268,0x08109c64,0x08109566,0x08082100]]
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def f(self,a,v):self.u.mem_write(a,struct.pack('<f',v))
 def text(self,a):return bytes(self.u.mem_read(a,100)).split(b'\0')[0].decode()
 def ret(self,v=0):self.u.reg_write(UC_ARM_REG_R0,v&0xffffffff);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def call(self,a,*args,fp=None):
  for reg,v in zip(REGS,args):self.u.reg_write(reg,v)
  sp=0x2003e000
  for i,v in enumerate(args[4:]):self.w(sp+i*4,v)
  if fp is not None:self.u.reg_write(UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',fp))[0])
  self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,self.stop|1)
  try:self.u.emu_start(a|1,self.stop,count=3000000)
  except Exception as e:raise RuntimeError(f'{e} at {self.u.reg_read(UC_ARM_REG_PC):08x}') from e
  assert self.u.reg_read(UC_ARM_REG_PC)==self.stop,hex(self.u.reg_read(UC_ARM_REG_PC))
  return self.u.reg_read(UC_ARM_REG_R0)
 def hook(self,u,a,n,d):
  r=[u.reg_read(x) for x in REGS]
  if a in [0x0809f940,0x0809f960,0x08104c08]:
   if self.force_registry:out=0x20020000
   else:out=self.next;self.next+=(r[0]+31)&~31
   self.ret(out)
  elif a==0x08133960:self.w(r[2],self.tracks[r[1]] if r[1]<8 else 0);self.ret(int(r[1]<8))
  elif a==0x0812dc74:self.ret(self.selected)
  elif a==0x0813bc3c:self.selected=r[1];self.ret()
  elif a==0x0813130c:self.ret()
  elif a==0x08109cdc:
   key=self.text(r[1]);h=self.nextattr;self.nextattr+=4;self.handles[h]=key;self.ret(h)
  elif a==0x0810958e:self.attrs[self.handles[r[0]]]=r[1];self.ret()
  elif a==0x08109268:self.ret(0x20017000)
  elif a==0x08109c64:
   key=self.text(r[1])
   if key not in self.attrs:self.ret(0)
   else:h=self.nextattr;self.nextattr+=4;self.handles[h]=key;self.ret(h)
  elif a==0x08109566:self.w(r[1],self.attrs[self.handles[r[0]]]);self.ret(0)
  elif a==0x08082100:self.ret()
 def registry(self):
  self.force_registry=True;self.call(0x081639a8,0);self.force_registry=False
 def open(self):
  self.registry();self.w(0x3001fe2c,1000);self.call(UU['fx_dispatch'],0x30024b00,0xaf,0,2)
  self.u.mem_write(0x30024b00+0x12c,b'\x02');self.w(0x3001fe2c,1060);self.call(UU['fx_dispatch'],0x30024b00,0xb0,0,2)
  self.w(0x3001fe2c,1200);self.call(UU['fx_dispatch'],0x30024b00,0xaf,0,2)
 def direct_open(self):
  # Exercise compiled dispatch up to the real native navigation call, then
  # construct the actual native GenericProperties view and enter its header.
  def nav(u,a,n,d):self.navlog.append(u.reg_read(UC_ARM_REG_R1));self.ret()
  h=self.u.hook_add(UC_HOOK_CODE,nav,begin=0x081420ec,end=0x081420ec)
  self.open();self.u.hook_del(h)
  self.view=0xc0000000
  self.call(0x08145b7c,self.view)
  arg=0x20016000;self.w(arg,42)
  self.call(0x08145efc,self.view,arg)
  return self.view
 def event(self,key,value):
  e=0x20015000;self.u.mem_write(e,struct.pack('<5I',0xcf,42,key,value&0xffffffff,0));return self.call(0x08145d90,self.view,e)
 def value(self,key):
  arg=0x20016000;out=0x20016010;self.w(arg,42);self.w(out,0xabcdef01)
  assert self.call(0x08133614,0x30024b00,arg,key,out)==1
  return struct.unpack('<i',self.u.mem_read(out,4))[0]
 def mailbox(self,tracks):
  self.mailserial+=2;self.w(0x24041444,self.mailserial|1);self.w(0x24041440,0x324d5846)
  for i in range(8):
   self.w(0x24041448+i*4,100+i)
   self.u.mem_write(0x24041468+i*72,struct.pack('<18i',*tracks.get(i,DEFAULT)))
  self.w(0x24041444,self.mailserial)
 def mixer(self):
  self.root=0x20000000;self.call(0x080a0f20,self.root)
  self.ctx=0xc0040000;self.buffers=[]
  for i in range(32):
   desc=self.ctx+0x5ac+i*20;self.call(0x08052f20,desc,128,0);self.buffers.append(desc)
  self.out=self.buffers[15]
  for i in range(8):
   strip=self.root+0x18+i*0x108
   # Stable unity track Level, preserve native initialized gain/filter objects.
   g=strip+0x20;self.call(0x0805bf80,g,1);self.call(0x0805bf00,g,fp=1);self.f(g+0x10,1)
  return self.root
 def audio(self,track,values,settings):
  tracks={track:settings}
  if settings is not None:self.mailbox(tracks)
  src=self.buffers[0];left=self.r(src+8);self.u.mem_write(left,np.array(values,dtype='float32').tobytes());self.w(src+4,len(values));self.u.mem_write(src+0x10,b'\x00\x00')
  strip=self.root+0x18+track*0x108
  self.call(0x08052c00,self.out)
  self.call(0x080a04c0,self.root,src,track,strip,self.out,self.ctx)
  return np.frombuffer(self.u.mem_read(self.r(self.out+8),len(values)*4),dtype='float32').copy()
class Tests(unittest.TestCase):
 def test_native_parameter_view_builds_three_rows_and_private_values(self):
  p=Fixture();v=p.direct_open();self.assertEqual(p.navlog,[0x1a]);self.assertEqual(bytes(p.u.mem_read(v+0x93c4,1)),b'\x03')
  self.assertEqual(p.value(KEYS[13]),1);self.assertEqual(p.value(KEYS[9]),-18)
  for i in range(3):self.assertIn('Track 1',p.text(p.r(v+0x93c8+i*4)))
 def test_native_event_changes_comp_eq_clip_and_track_independently(self):
  p=Fixture();p.direct_open();self.assertEqual(p.event(KEYS[2],6),0);self.assertEqual(p.value(KEYS[2]),6)
  p.event(KEYS[8],1);p.event(KEYS[13],0);p.event(KEYS[16],1);p.event(KEYS[17],-6)
  p.event(KEYS[18],2);self.assertEqual(p.selected,1);self.assertEqual(p.value(KEYS[2]),0);self.assertEqual(p.value(KEYS[8]),0)
  p.event(KEYS[18],1);self.assertEqual(p.value(KEYS[2]),6);self.assertEqual(p.value(KEYS[16]),1);self.assertEqual(p.value(KEYS[17]),-6)
 def test_native_mixer_bypassed_matches_original_audio(self):
  p=Fixture();p.mixer();x=np.sin(np.arange(128)*.1).astype('float32')*.2;y=p.audio(0,x,DEFAULT)
  base=Fixture(K16_IMAGE.read_bytes());base.mixer();expected=base.audio(0,x,DEFAULT)
  self.assertGreater(float(np.max(np.abs(y))),.01);self.assertLess(float(np.max(np.abs(y-expected))),1e-6)
 def test_native_track_eq_changes_summed_audio_and_leaves_source_untouched(self):
  p=Fixture();p.mixer();s=DEFAULT.copy();s[0]=1;s[4]=12
  x=(np.sin(np.arange(128)*2*np.pi*1000/48000)*.05).astype('float32')
  y=None
  for _ in range(120):y=p.audio(0,x,s)
  self.assertGreater(float(np.max(np.abs(y))),.15)
  self.assertEqual(bytes(p.u.mem_read(p.r(p.buffers[0]+8),512)),x.tobytes())
 def test_native_track_compression_and_softclip(self):
  p=Fixture();p.mixer();s=DEFAULT.copy();s[8]=1;s[9]=-24;s[10]=8;s[11]=1;s[13]=0
  x=np.full(128,.8,dtype='float32')
  for _ in range(120):y=p.audio(0,x,s)
  self.assertLess(float(np.max(np.abs(y))),.2)
  s[13]=1;s[16]=1;s[17]=-6
  for _ in range(120):y=p.audio(0,x,s)
  self.assertLessEqual(float(np.max(np.abs(y))),10**(-6/20)+1e-6)
 def test_xml_roundtrip_and_missing_data_defaults(self):
  p=Fixture();p.direct_open();p.event(KEYS[8],1);p.event(KEYS[9],-30);p.event(KEYS[16],1)
  obj=0x20010000;params=0x20017000;p.w(obj+16,100);p.u.mem_write(obj+4,b'\x0e')
  p.call(UU['fx_save'],obj,params);self.assertEqual(p.attrs['bento_fx_version'],1)
  saved=dict(p.attrs);p.event(KEYS[9],-10);p.call(UU['fx_load'],0x20011000,obj)
  ev=0x20012000;p.w(ev,0x3f);p.call(UU['fx_finish'],0,ev);self.assertEqual(p.value(KEYS[9]),-30)
  p.attrs={};p.call(UU['fx_load'],0x20011000,obj);p.call(UU['fx_finish'],0,ev);self.assertEqual(p.value(KEYS[8]),0);self.assertEqual(p.value(KEYS[13]),1)
 def test_native_encoder_bubbles_into_fx_event_and_audio_mailbox(self):
  p=Fixture();p.direct_open();slot=p.view+0x940
  self.assertEqual(p.call(0x08171e44,slot,12800),1)
  self.assertEqual(p.value(KEYS[2]),1)
  self.assertEqual(p.r(0x24041468+2*4),1)
 def test_ui_to_native_audio_without_test_republishing(self):
  p=Fixture();p.direct_open();p.event(KEYS[8],1);p.event(KEYS[9],-30);p.event(KEYS[10],10);p.event(KEYS[11],1);p.event(KEYS[13],0)
  p.mixer();x=np.full(128,.8,dtype='float32')
  for _ in range(120):y=p.audio(0,x,None)
  self.assertLess(float(np.max(np.abs(y))),.1)
 def test_all_eight_tracks_are_independent(self):
  p=Fixture();p.mixer();s=DEFAULT.copy();s[16]=1;s[17]=-12;p.mailbox({3:s})
  x=np.full(128,.8,dtype='float32')
  for _ in range(120):wet=p.audio(3,x,None)
  self.assertLessEqual(float(np.max(np.abs(wet))),10**(-12/20)+1e-6)
  for t in range(8):
   if t==3:continue
   dry=p.audio(t,x,None);self.assertGreater(float(np.max(np.abs(dry))),.7)
 def test_odd_and_invalid_mailbox_updates_are_rejected(self):
  p=Fixture();p.mixer();x=np.full(128,.2,dtype='float32');p.audio(0,x,DEFAULT);serial=p.r(0x240416c4)
  p.w(0x24041444,serial+1);p.audio(0,x,None);self.assertEqual(p.r(0x240416c4),serial)
  p.mailbox({});p.w(0x24041468+9*4,100000);p.audio(0,x,None);self.assertEqual(p.r(0x240416c4),serial)
 def test_navigation_returns_native_project_rows_to_normal(self):
  p=Fixture();p.direct_open();p.call(UU['fx_nav'],0,0x17)
  out=0x20016010;p.w(out,0xabcdef01)
  self.assertEqual(p.call(UU['fx_get'],0,0,KEYS[9],out),0);self.assertEqual(p.r(out),0xabcdef01)
 def test_project_restore_in_fresh_ui_state(self):
  p=Fixture();p.direct_open();p.event(KEYS[8],1);p.event(KEYS[13],0);p.event(KEYS[9],-33)
  obj=0x20010000;p.w(obj+16,100);p.u.mem_write(obj+4,b'\x0e');p.call(UU['fx_save'],obj,0x20017000)
  q=Fixture();q.registry();q.attrs=dict(p.attrs);q.w(obj+16,100);q.u.mem_write(obj+4,b'\x0e');q.call(UU['fx_load'],0x20011000,obj)
  ev=0x20012000;q.w(ev,0x3f);q.call(UU['fx_finish'],0,ev);q.direct_open()
  self.assertEqual(q.value(KEYS[8]),1);self.assertEqual(q.value(KEYS[13]),0);self.assertEqual(q.value(KEYS[9]),-33)
if __name__=='__main__':
 gc.disable();unittest.main(verbosity=2)
