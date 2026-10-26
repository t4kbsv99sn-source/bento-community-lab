"""CH12 drum engines on M7: Clap and Tom / FM perc, and the bit-identical
optimisation of Kick/Snare/HiHat, on the built image."""
from pathlib import Path
import os,sys,unittest,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'k16_work'));sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import release
stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes()
# Compile K16 symbol maps needed by the inherited compiled-code fixtures.
base,_=release.candidate(stock)
out=Path(os.environ['BENTO_FX_CANDIDATE']);image=(out/'bento1.bin').read_bytes()
writes=json.loads((out/'FULL_MANIFEST.json').read_text())['writes']
release.native.candidate=lambda stock:(image,writes)
import importlib.util, kick_build
spec=importlib.util.spec_from_file_location('optimized_kick', ROOT/'eu4_work/drums/kick_build.py')
optimized=importlib.util.module_from_spec(spec);spec.loader.exec_module(optimized);optimized.compile_kick()
kick_build.SYMS.clear();kick_build.SYMS.update(optimized.SYMS)
import unicorn
native_map=unicorn.Uc.mem_map
def full_application_map(self,address,size,*args,**kwargs):
 # Legacy fixture's 1.5 MiB flash window ended five KiB before the new UI.
 # Model the declared application region, without changing any firmware limit.
 if address==0x08040000 and size==0x180000:size=0x1c0000
 return native_map(self,address,size,*args,**kwargs)
unicorn.Uc.mem_map=full_application_map
import struct,unittest
from unicorn.arm_const import *
from test_kick import Kick
SYMS=kick_build.SYMS
KNOBS=0x24043500;HANDLE=101
TUNE,DECAY,TONE,CLICK=0x1a0,0x1a1,0x1a2,0x1b0
def knobs(p,values=(55,65,45,65,55,25,25),reserved=1,click=40):
 p.u.mem_write(KNOBS,bytes(0x900));p.w(KNOBS,0x35424e4b);p.w(KNOBS+4,2)
 e=KNOBS+32;p.w(e,2);p.w(e+4,HANDLE);p.u.mem_write(e+8,bytes(values)+bytes([reserved]));p.u.mem_write(0x24043d80,bytes([click]))
def command(p,key,src,amount,slot=0,at=0x2002a000):
 p.u.mem_write(at,struct.pack('<BBHIIIIHh',0x3f,0,0,0,HANDLE,key,slot,src,amount));return at
def routes(p):
 n=p.r(p.root+0x5fc);return [(round(p.f(p.root+0x590+12*i),4),)+struct.unpack('<HHB',p.u.mem_read(p.root+0x594+12*i,5)) for i in range(n)]
def tail(x):return sum(v*v for v in x[1600:2560])
class Synth(Kick):
 def __init__(self,**k):
  super().__init__();knobs(self,**k);self.w(self.root+0x5fc,0)
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def route(self,key,src,amount,slot=0):
  self.call(SYMS['kick_route'],self.root,command(self,key,src,amount,slot));return self.u.reg_read(UC_ARM_REG_R0)
 def audio(self,blocks=6):
  self.start();out=[]
  for _ in range(blocks):ok,s=self.render();assert ok==1;out.extend(s)
  return out
import hashlib
from unicorn import UC_HOOK_CODE
# CH11 output (30 blocks x 64 samples) of the unoptimised engines.
# P10: Kick knob 7 is Punch (was Dirt), so the CH11 Kick references use 0 there
# (the P9 engine at Dirt 0 = this engine at Punch 0, bit for bit).
GOLDEN=[(1,(55,65,45,65,55,25,0),'ea637e84796c7b7bf964a1aa2fe5bad61f34fc05f4a3c45e172e4403d834ae75'),
 (1,(120,90,80,100,90,60,0),'09cc17932d1ac18bdea293fd47dac980cdcf97b13c2bec491be33f51dfd78a3a'),
 (5,(10,70,65,65,30,0,0),'239c8bda8ced3f1a94d7eddc402b9b86792c35fe916048c1c5aaf012a3d73e2c'),
 (5,(80,95,20,100,90,0,0),'6650bf235f5674f135dcac3e8c0981f2c4e95f0ae1bf36855a442cec0d07aa3c')]
CLAP=(40,40,50,65,40,0,0);TOM=(86,50,40,65,40,30,10)
def engine(eng,values,lock=None):
 p=Synth(reserved=eng,values=values);p.w(p.desc+0x24,144019+eng-1)
 if lock:p.w(0x24046000,0x374c5042);p.w(0x24046008,p.root);p.w(0x2404600c,0x51000000|lock[0]<<16|lock[1])
 return p
def run(p,blocks=30,cost=None):
 p.start();out=[]
 for i in range(blocks):
  if cost is not None and i==10:
   n=[0];h=p.u.hook_add(UC_HOOK_CODE,lambda u,a,s,d:n.__setitem__(0,n[0]+1))
  out+=p.render()[1]
  if cost is not None and i==10:p.u.hook_del(h);cost.append(n[0]/64)
 return out
def digest(o):return hashlib.sha256(struct.pack('<%df'%len(o),*o)).hexdigest()
def energy(o,a=0,b=None):return sum(x*x for x in o[a:b])
# The K16 lock-UI harness, adapted to this image exactly as test_k16_regressions does.
import types
_src=(ROOT/'k16_work/bento_controls/test_k16.py').read_text().replace("struct.unpack('<2H',p.u.mem_read(0x300000bc+8,4))","struct.unpack('<2H',p.u.mem_read(0x300000bc+12,4))")
_k16=types.ModuleType('k16_for_engines');_k16.__file__=str(ROOT/'k16_work/bento_controls/test_k16.py');exec(compile(_src,_k16.__file__,'exec'),_k16.__dict__)
class LockUI(_k16.SynthUI):
 def __init__(self,model):
  self.engine=model;self.path={7:'BENTO_Synth_Clap.wav',9:'BENTO_Synth_Tom.wav'}[model];_k16.UIProbe.__init__(self)
 def choice(self,i):return self.text(self.word(0x24048480+4*i))
class Tests(unittest.TestCase):
 def test_optimised_engines_are_bit_identical_to_ch11(self):
  for eng,values,want in GOLDEN:self.assertEqual(digest(run(engine(eng,values))),want,(eng,values))
 def test_optimised_engines_cost_less(self):
  # Emulated instructions per sample in one block; CH11 was 331 / 352-362 / 388-391.
  # P10: Kick +~1 from the Punch branch (same samples at Punch 0); the 909 Snare is far cheaper.
  for eng,values,budget in [(1,(55,65,45,65,55,25,0),315),(1,(55,65,45,65,55,25,25),330),(3,(10,45,50,65,70,0,0),200),(5,(10,70,65,65,30,0,0),240),(7,CLAP,200),(9,TOM,335)]:
   c=[];run(engine(eng,values),12,c);self.assertLess(c[0],budget,(eng,c))
 def test_kick_punch_is_a_sharper_start_and_a_denser_body(self):
  # P10 (owner: missing punch). Punch adds a fast pitch dive and warm drive.
  def zc(o):return sum(1 for a,b in zip(o,o[1:]) if a<0<=b)
  plain=run(engine(1,(55,65,45,65,55,25,0)),40);punch=run(engine(1,(55,65,45,65,55,25,100)),40)
  self.assertGreater(zc(punch[:960]),zc(plain[:960])) # extra cycles from the dive in the first 20 ms
  self.assertGreater(energy(punch,480,4800),energy(plain,480,4800)*1.3) # fuller body
  self.assertLessEqual(max(abs(x) for x in punch),.61) # saturates, never clips
 def test_snare_is_a_909_two_shells_and_snappy_noise(self):
  # P10 (owner: "a 909 type snare"): shells at f and 1.62 f, noise set by Snappy and Tone.
  import math
  def power(o,f,a=0,b=4800):
   c=s_=0
   for i,x in enumerate(o[a:b]):c+=x*math.cos(2*math.pi*f*i/48000);s_+=x*math.sin(2*math.pi*f*i/48000)
   return c*c+s_*s_
  def hf(o):return sum((b-a)**2 for a,b in zip(o[:4800],o[1:4800])) # rough high-frequency energy
  f=140*2**(10/50);o=run(engine(3,(10,45,50,65,70,0,0)),80)
  self.assertGreater(power(o,f,960),power(o,f*1.3,960)*4);self.assertGreater(power(o,f*1.62,960),power(o,f*1.3,960)*2)
  self.assertGreater(hf(o),hf(run(engine(3,(10,45,50,65,0,0,0)),80))*5) # Snappy brings the noise
  self.assertGreater(hf(run(engine(3,(10,45,100,65,70,0,0)),80)),hf(run(engine(3,(10,45,0,65,70,0,0)),80))*1.5) # Tone brightens
  hi=run(engine(3,(60,45,50,65,0,0,0)),80);self.assertGreater(power(hi,140*2**(60/50),960),power(hi,f,960)) # Tune moves the shells
  long=run(engine(3,(10,95,50,65,70,0,0)),200);short=run(engine(3,(10,5,50,65,70,0,0)),200)
  self.assertGreater(energy(long,9600,14400),energy(short,9600,14400)*4) # Decay
  self.assertTrue(all(abs(x)<=1 for x in o))
 def test_new_carriers_are_recognised(self):
  for eng in (7,9):
   p=engine(eng,CLAP if eng==7 else TOM);p.call(SYMS['kick_marker'],p.desc);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),eng)
 def test_clap_is_three_bursts_and_a_tail(self):
  o=run(engine(7,CLAP),40);self.assertTrue(all(abs(x)<1 for x in o));self.assertGreater(max(abs(x) for x in o),.05)
  spacing=int(48000*(.004+.4*.018));quiet=[energy(o,k*spacing-40,k*spacing) for k in (1,2,3)]
  peaks=[energy(o,k*spacing,k*spacing+40) for k in (1,2,3)]
  for q,pk in zip(quiet,peaks):self.assertGreater(pk,q*3) # each burst restarts loud
  self.assertGreater(energy(o,3*spacing+400,3*spacing+800),0) # tail rings on
 def test_clap_controls_change_the_sound(self):
  base=run(engine(7,CLAP),40)
  for i,v in [(0,90),(1,90),(2,0),(3,100),(4,90)]:
   vals=list(CLAP);vals[i]=v;self.assertNotEqual(run(engine(7,tuple(vals)),40),base,i)
  self.assertGreater(energy(run(engine(7,(40,95,50,65,40,0,0)),60),3000),energy(run(engine(7,CLAP),60),3000)*4) # longer Decay: the tail rings on
 def test_tom_is_pitched_by_tune(self):
  def zero_crossings(o):return sum(1 for a,b in zip(o,o[1:]) if a<0<=b)
  low=run(engine(9,(60,)+TOM[1:]),40);high=run(engine(9,(150,)+TOM[1:]),40)
  self.assertGreater(max(abs(x) for x in low),.05);self.assertGreater(zero_crossings(high),zero_crossings(low)*3)
 def test_tom_takes_kick_locks_and_clap_takes_snare_locks(self):
  base=run(engine(9,TOM),20);self.assertNotEqual(run(engine(9,TOM,(12,150-25)),20),base) # Kick Tune kind
  self.assertEqual(run(engine(9,TOM,(19,90)),20),base) # Kick Click kind: not a Tom control
  self.assertEqual(run(engine(9,TOM,(20,90)),20),base) # Snare kind: other family
  base=run(engine(7,CLAP),40);self.assertNotEqual(run(engine(7,CLAP,(21,95)),40),base) # Snare Decay kind = Clap Decay (tail after the bursts)
  self.assertEqual(run(engine(7,CLAP,(12,90-25)),40),base)
 def test_mod_matrix_reaches_the_new_engines(self):
  for eng,values,key in [(7,CLAP,DECAY),(9,TOM,TUNE)]:
   base=run(engine(eng,values),40);p=engine(eng,values);p.route(key,13,700);self.assertNotEqual(run(p,40),base,eng)
   p=engine(eng,values);p.route(0x1a6,13,700) # sixth parameter (Sweep Dec) exists on Tom only
   (self.assertNotEqual if eng==9 else self.assertEqual)(run(p,40),base)
 def test_lock_picker_lists_tom_and_clap_controls_on_their_family_kinds(self):
  for model,first,total,names in [(9,12,15,['Tom Tune','Tom Decay','Tom Tone','Tom Impact','Tom Sweep','Tom Sweep Dec','Tom Dirt']),(7,20,13,['Clap Tune','Clap Decay','Clap Tone','Clap Impact','Clap Spread'])]:
   p=LockUI(model);p.press(0);p.shift();self.assertEqual(p.word(0x20029000+0x1da*32+12),total)
   self.assertEqual([p.choice(8+i) for i in range(len(names))],names)
   p.encoder(0x1da,8);p.shift(False);p.encoder(_k16.KEYS[0],80)
   self.assertEqual(p.stored(),_k16.word(first,80))
 def test_instrument_page_shows_the_new_engines(self):
  K=[0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9]
  for name,title,keys,labels,hz in [('BENTO_Synth_Clap.wav','Clap / Pad 1',K[:5]+[0,0],['Tune','Decay','Tone','Impact','Spread'],'914 Hz'),
                                    ('BENTO_Synth_Tom.wav','Tom / Pad 1',K,['Tune','Decay','Tone','Impact','Sweep','Sweep Dec','Dirt'],'180 Hz')]:
   p=_k16.UI();p.path='\\Projects\\'+name;p.prepare()
   self.assertEqual(list(struct.unpack('<8H',p.u.mem_read(p.v+0x703c,16))),[2]+keys)
   self.assertEqual(struct.unpack('<H',p.u.mem_read(p.v+0x703c+2*0x50,2))[0],0) # Click row is Kick only
   titles=[c[2] for c in p.calls if c[0]=='title'];self.assertIn(title,titles)
   for l in labels:self.assertIn(l,titles)
   self.assertIn(hz,[c[3] for c in p.calls if c[0]=='value'])
if __name__=='__main__':unittest.main(verbosity=2)
