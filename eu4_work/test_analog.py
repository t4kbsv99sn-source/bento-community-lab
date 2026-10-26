"""A1 Analog Wavetable oscillators on M7: the real native WT oscillator objects
(constructed by 08081520) rendered through kick_analog_enter/kick_analog_osc."""
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
import math
ROOT_OBJ=0x2002c000;VOICE=0x20030000;HANDLE=0x77
class Analog(Synth):
 def __init__(self,analog=True,sync=0,glide=0):
  super().__init__()
  self.u.mem_write(KNOBS,bytes(0x900));self.w(KNOBS,0x35424e4b);self.w(KNOBS+4,2)
  if analog:e=KNOBS+32;self.w(e,2);self.w(e+4,HANDLE);self.u.mem_write(e+8,bytes([sync,glide,0,0,0,0,0,13]))
  self.u.mem_write(ROOT_OBJ,bytes(0x100));self.w(ROOT_OBJ+12,HANDLE)
  self.u.mem_write(VOICE,bytes(0xb88))
  for o in (0x7a4,0x994):self.call(0x08081520,VOICE+o)
  self.out=0x20025000;self.w(self.out,64);self.w(self.out+4,64);self.w(self.out+8,0x20028000);self.w(self.out+12,0x20029000)
 def osc(self,i):return VOICE+(0x7a4 if i==0 else 0x994)
 def tune(self,i,hz,cents=0):
  # Native pitch (0804F5E0): 32.7032 Hz x 2^octaves; note 60 adds 3 octaves = middle C.
  # Table steps per sample = Hz x 2048 / 48000 (rate / 23.4375).
  self.f(self.osc(i)+4,math.log2(hz/32.7032)-3-self.evaluate(self.osc(i)+0x70));self.w(self.osc(i)+0xc,cents)
 def shape(self,i,v):self.f(self.osc(i)+0x2c,v)
 def level(self,i,v):self.f(self.osc(i)+0xf4,v)
 def block(self,which=(0,1)):
  self.u.mem_write(0x20028000,bytes(256))
  self.call(SYMS['kick_analog_enter'],ROOT_OBJ,VOICE);handled=[]
  for i in which:self.call(SYMS['kick_analog_osc'],self.osc(i),self.temp,self.out);handled.append(self.u.reg_read(UC_ARM_REG_R0))
  return handled,list(struct.unpack('<64f',self.u.mem_read(0x20028000,256)))
 def run(self,blocks,which=(0,1)):
  o=[]
  for _ in range(blocks):o+=self.block(which)[1]
  return o
def crossings(o):return sum(1 for a,b in zip(o,o[1:]) if a<0<=b)
class Tests(unittest.TestCase):
 def test_ordinary_wavetable_tracks_stay_native(self):
  p=Analog(analog=False);self.assertEqual(p.block()[0],[0,0])
  p=Analog();p.call(SYMS['kick_analog_enter'],ROOT_OBJ,VOICE+0x1000);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0)&0,0)
  p.call(SYMS['kick_analog_osc'],p.osc(0),p.temp,p.out);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0) # not this voice's oscillator
 def test_note_60_is_middle_c(self):
  p=Analog();p.block((0,));self.assertAlmostEqual(p.f(p.osc(0)+0x1e8)*48000/2048,261.63,delta=.05)
 def test_wt1_plays_a_saw_at_the_native_wavetable_pitch(self):
  p=Analog();p.tune(0,375);p.level(1,0);o=p.run(40,(0,))
  self.assertEqual(p.block((0,))[0],[1])
  n=crossings(o[640:]);self.assertAlmostEqual(n,(len(o)-640)/128,delta=1.5) # 375 Hz = 128 samples
  tail=o[1280:];self.assertLess(max(abs(x) for x in tail),1.3);self.assertGreater(max(tail)-min(tail),.5) # native Level curve scales it
  self.assertAlmostEqual(sum(tail)/len(tail),0,delta=.05)
 def test_position_morphs_saw_into_narrow_pulse(self):
  saw=Analog();saw.tune(0,375);saw.level(1,0);a=saw.run(30,(0,))[1280:]
  pul=Analog();pul.tune(0,375);pul.level(1,0);pul.shape(0,1.0);b=pul.run(30,(0,))[1280:]
  self.assertNotEqual(a,b)
  def high(o):m=max(o);return sum(1 for x in o if x>m*.5)/len(o)
  self.assertLess(high(b),.15) # 8% pulse: high only briefly
  self.assertGreater(high(a),.2) # saw: a quarter of the cycle above half
 def test_hard_sync_locks_wt2_to_wt1_period(self):
  def wt2(sync):
   p=Analog(sync=sync);p.tune(0,375);p.tune(1,375,7400);p.level(0,0);return p.run(40)[1280:]
  s,f=wt2(1),wt2(0)
  err=lambda o:sum(abs(o[i]-o[i+128]) for i in range(len(o)-128))/(len(o)-128)
  self.assertLess(err(s),.05);self.assertGreater(err(f),.2)
 def test_silent_master_still_drives_sync(self):
  p=Analog(sync=1);p.tune(0,375);p.tune(1,375,7400);p.level(0,0);o=p.run(40)[1280:]
  self.assertGreater(max(o)-min(o),1.0)
 def test_output_is_finite_across_pitch_and_shape(self):
  for hz in (20,375,4000,15000):
   for sh in (0,.3,.5,.8,1):
    p=Analog(sync=1);p.tune(0,hz);p.tune(1,hz,12000);p.shape(0,sh);p.shape(1,sh);o=p.run(6)
    self.assertTrue(all(math.isfinite(x) and abs(x)<4 for x in o),(hz,sh))
 def test_publishes_the_played_shape_for_the_display(self):
  # P4: {track handle, shape1 | shape2<<8 | counter<<16} at kick State +14F8.
  p=Analog();p.shape(0,.25);p.shape(1,1.0);p.block()
  h,v=p.r(0x240434f8),p.r(0x240434fc);self.assertEqual(h,HANDLE)
  self.assertAlmostEqual(v&255,round(p.evaluate(p.osc(0)+0x30)*255),delta=1);self.assertEqual((v>>8)&255,255)
  c=v>>16;p.block();self.assertEqual(p.r(0x240434fc)>>16,(c+2)&0xffff) # one step per oscillator block
 def test_glide_slides_from_the_previous_note(self):
  def rates(glide):
   p=Analog(glide=glide);out=[]
   p.w(p.osc(0)+0x10,48);p.block((0,));p.block((0,))  # C3 first
   p.w(p.osc(0)+0x10,60)                              # then C4 on the same voice
   for _ in range(40):p.block((0,));out.append(p.f(p.osc(0)+0x1e8))
   return out,p
  plain,_=rates(0);self.assertAlmostEqual(plain[0],plain[-1],delta=.001) # no glide: C4 at once
  slide,p=rates(20)
  self.assertLess(slide[0],plain[0]*.8);self.assertGreater(slide[0],plain[0]*.45) # starts near C3 (half the rate)
  self.assertTrue(all(b>=a for a,b in zip(slide,slide[1:])))                    # rises
  sub=p.f(VOICE+0x4c+4);self.assertLess(sub,0)                                # sub follows (negative offset)
  for _ in range(400):p.block((0,))
  self.assertAlmostEqual(p.f(p.osc(0)+0x1e8),plain[0],delta=.01);self.assertAlmostEqual(p.f(VOICE+0x4c+4),0,delta=.001)
if __name__=='__main__':unittest.main(verbosity=2)
