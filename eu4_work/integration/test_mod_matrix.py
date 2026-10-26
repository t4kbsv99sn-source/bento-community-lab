"""CH11 drum-synth destinations in the native Mod Matrix, UI core (M4).

Runs the built image. The model tree (child walk 0813391A, type 08133F7C, file
path 0813390E) and the native route setter 08133388 are fixtures; the row
arrays live in a matrix view buffer laid out like the native one."""
import struct,unittest,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE
KNOBS=0x24043500
VIEW=0xc0000000;M=VIEW+0x8a000;FRAME=0x20030000;TRACK=0x55;CELL=0x66;FILE=0x67
NATIVE=[2,3,4,0x1e,0x1f,0x21,0x4c,0x4b,0x32,0x33]
SYNTH=[0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9,0x1b0]
KEEP=[]
class Matrix(Fixture):
 def __init__(self,path='\\Projects\\bento_kick.wav'):
  super().__init__();KEEP.append(self);self.path=path;self.edits=[];self.registry()
  self.u.hook_add(UC_HOOK_CODE,self.tree);self.native()
 def native(self):
  # What the native builder leaves for a one-shot cell before our hook runs.
  self.u.mem_write(VIEW+0x8a000,bytes(0x2000))
  self.w(M+0xc44,CELL);self.u.mem_write(M+0xc4d,bytes([len(NATIVE)]))
  for i,k in enumerate(NATIVE):
   self.u.mem_write(M+0xc50+2*i,struct.pack('<H',k));self.w(M+0xccc+4*i,CELL);self.u.mem_write(M+0xdbc+i,bytes([i]))
   self.u.mem_write(M+0xe04+16*i,('N%x'%k).encode().ljust(16,b'\0'))
  self.w(FRAME+0x338,TRACK)
 def tree(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0x0813391a:
   kids=[CELL,FILE] if self.r(r[1])==TRACK else []
   if r[2]<len(kids):self.w(r[3],kids[r[2]]);self.ret(1)
   else:self.ret(0)
  elif a==0x08133f7c:h=self.r(r[1]);self.ret(1 if h==CELL else 5 if h==FILE else 14)
  elif a==0x0813390e:u.mem_write(r[3],self.path.encode()+b'\0');self.ret(1)
  elif a==0x08133388:self.edits.append(self.r(r[1]+8)&0xffff);self.ret(0)
 def rows(self):
  n=self.u.mem_read(M+0xc4d,1)[0]
  return [(struct.unpack('<H',self.u.mem_read(M+0xc50+2*i,2))[0],self.r(M+0xccc+4*i),self.u.mem_read(M+0xdbc+i,1)[0],self.text(M+0xe04+16*i)) for i in range(n)]
 def entry(self):
  for i in range(128):
   e=KNOBS+32+i*16
   if self.r(e) and self.r(e+4)==CELL:return e
 def reserved(self):return self.u.mem_read(self.entry()+15,1)[0]
 def build(self):self.native();self.call(UU['mod_rows'],VIEW,FRAME);return self.rows()
class Tests(unittest.TestCase):
 def test_kick_pad_lists_its_synth_parameters_first_without_sample_envelope(self):
  rows=Matrix().build()
  self.assertEqual([r[0] for r in rows],SYNTH+[2,3,4,0x4c,0x4b,0x32,0x33])
  self.assertEqual([r[3] for r in rows[:8]],['Kick Tune','Kick Decay','Kick Tone','Kick Impact','Kick Sweep','Kick Sweep Dec','Kick Punch','Kick Click'])
  self.assertTrue(all(r[1]==CELL for r in rows));self.assertEqual([r[2] for r in rows[:8]],[0]*8)
  self.assertEqual([r[3] for r in rows[8:]],['N2','N3','N4','N4c','N4b','N32','N33']) # native rows keep their names and row bytes
  self.assertEqual([r[2] for r in rows[8:]],[0,1,2,6,7,8,9])
 def test_snare_and_hat_list_five_parameters(self):
  for path,name in [('bento_synth_snare.wav','Snare'),('BENTO_SYNTH_HIHAT.WAV','HiHat')]:
   rows=Matrix('\\X\\'+path).build()
   self.assertEqual([r[0] for r in rows[:5]],SYNTH[:5]);self.assertEqual(rows[5][0],2);self.assertTrue(rows[0][3].startswith(name+' '))
 def test_clap_and_tom_list_their_own_parameters(self):
  # CH12 engines: Clap five, Tom seven (no Click).
  rows=Matrix('\\P\\bento_synth_clap.wav').build()
  self.assertEqual([r[3] for r in rows[:5]],['Clap Tune','Clap Decay','Clap Tone','Clap Impact','Clap Spread']);self.assertEqual(rows[5][0],2)
  rows=Matrix('\\P\\BENTO_Synth_Tom.wav').build()
  self.assertEqual([r[0] for r in rows[:7]],SYNTH[:7]);self.assertEqual(rows[6][3],'Tom Dirt');self.assertEqual(rows[7][0],2)
 def test_ordinary_sample_pad_keeps_the_native_rows(self):
  p=Matrix('\\Samples\\kick.wav');before=p.rows();self.assertEqual(p.build(),before)
 def test_saved_destination_names_round_trip(self):
  p=Matrix()
  for k,t in zip(SYNTH,['bento_synth_p1','bento_synth_p2','bento_synth_p3','bento_synth_p4','bento_synth_p5','bento_synth_p6','bento_synth_p7','bento_synth_click']):
   self.assertEqual(p.text(p.call(UU['mod_token'],k)),t)
   p.u.mem_write(0x20031000,t.encode()+b'\0');self.assertEqual(p.call(UU['mod_key'],0x20031000),k)
  level=p.call(UU['mod_token'],2);self.assertEqual(p.text(level),p.text(p.call(0x081666f8,2))) # native destinations unchanged
  p.u.mem_write(0x20031000,b'bento_synth_p\0');self.assertEqual(p.call(UU['mod_key'],0x20031000),p.call(0x08166720,0x20031000))
 def test_engine_change_keeps_old_routes_silent_and_labelled_until_an_edit(self):
  p=Matrix();p.build();self.assertEqual(p.reserved(),1)
  p.path='\\P\\bento_synth_snare.wav';rows=p.build()
  self.assertEqual(p.reserved(),3|1<<4) # snare pad, routes made for the kick
  self.assertEqual(rows[0][3],'Kick Tune');self.assertEqual(len(rows),8+7)
  ev=0x20031100;p.u.mem_write(ev,struct.pack('<5I',0xd1,CELL,0x1a1|1<<16,13,500))
  p.call(UU['mod_edit'],0x30024b00,ev);self.assertEqual(p.edits,[0x1a1]);self.assertEqual(p.reserved(),3|3<<4)
  rows=p.build();self.assertEqual(rows[0][3],'Snare Tune');self.assertEqual(rows[5][0],2)
 def test_native_edit_leaves_the_tag_alone(self):
  p=Matrix();p.build();p.path='\\P\\bento_synth_snare.wav';p.build()
  ev=0x20031100;p.u.mem_write(ev,struct.pack('<5I',0xd1,CELL,2|1<<16,13,500))
  p.call(UU['mod_edit'],0x30024b00,ev);self.assertEqual(p.edits,[2]);self.assertEqual(p.reserved(),3|1<<4)
 def test_tag_is_saved_and_loaded_with_the_pad(self):
  p=Matrix();p.build();p.path='\\P\\bento_synth_snare.wav';p.build()
  obj=0x20031200;p.u.mem_write(obj+4,b'\x01');p.w(obj+0x10,CELL)
  p.call(UU['kick_ui_save'],obj,0x20017000)
  self.assertEqual(p.attrs['bento_drum_model'],3);self.assertEqual(p.attrs['bento_mod_engine'],1)
  e=p.entry();p.u.mem_write(e+15,b'\x03') # tag lost
  p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.reserved(),3|1<<4)
  del p.attrs['bento_mod_engine'];p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.reserved(),3)
 def test_untagged_pad_saves_no_tag(self):
  p=Matrix();p.build();obj=0x20031200;p.u.mem_write(obj+4,b'\x01');p.w(obj+0x10,CELL)
  p.call(UU['kick_ui_save'],obj,0x20017000);self.assertNotIn('bento_mod_engine',p.attrs);self.assertEqual(p.attrs['bento_drum_model'],1)
 def test_builder_adapter_replays_the_replaced_instructions(self):
  p=Matrix();site=0x0814ce80
  h1,h2=struct.unpack('<HH',IMAGE[site-0x08040000:site-0x08040000+4])
  s=(h1>>10)&1;off=((s<<24)|((1-(((h2>>13)&1)^s))<<23)|((1-(((h2>>11)&1)^s))<<22)|((h1&0x3ff)<<12)|((h2&0x7ff)<<1))
  if s:off-=1<<25
  adapter=site+4+off
  sp=0x2003d000;p.w(sp+0xc,0xf);p.w(sp+0x338,TRACK)
  p.u.reg_write(UC_ARM_REG_R4,VIEW);p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,0x08100001)
  p.u.emu_start(adapter|1,0x08100000,count=200000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_R6),0xf);self.assertTrue(p.u.reg_read(UC_ARM_REG_CPSR)&(1<<30)) # Z from cmp r6,#0xf
  self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp);self.assertEqual(p.rows()[0][0],0x1a0)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
