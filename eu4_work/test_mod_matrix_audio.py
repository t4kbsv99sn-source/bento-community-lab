"""CH11 Mod Matrix synth destinations on M7: real kick_route and kick_render on the built image."""
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
# P10: knob 7 is the Kick's Punch (was Dirt); these tests measure decay/pitch, so Punch stays 0.
def knobs(p,values=(55,65,45,65,55,25,0),reserved=1,click=40):
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
class Tests(unittest.TestCase):
 def test_route_commands_upsert_by_destination_and_slot_and_source_none_removes(self):
  p=Synth()
  self.assertEqual(p.route(DECAY,13,500),1);self.assertEqual(p.route(DECAY,4,-250,slot=1),1);self.assertEqual(p.route(TUNE,26,1000),1)
  self.assertEqual(routes(p),[(.5,DECAY,13,0),(-.25,DECAY,4,1),(1.,TUNE,26,0)])
  p.route(DECAY,14,100);self.assertEqual(routes(p)[0],(.1,DECAY,14,0)) # same slot: replaced
  p.route(DECAY,0,0,slot=1);self.assertEqual(routes(p),[(.1,DECAY,14,0),(1.,TUNE,26,0)])
  p.route(CLICK,0,0);self.assertEqual(len(routes(p)),2) # removing a missing route is harmless
 def test_list_never_exceeds_the_native_nine_records(self):
  p=Synth()
  for i in range(12):p.route(TUNE if i%2 else DECAY,13,100,slot=i)
  self.assertEqual(p.r(p.root+0x5fc),9)
 def test_native_destinations_are_not_taken(self):
  p=Synth();self.assertEqual(p.route(2,13,500),0);self.assertEqual(routes(p),[])
 def test_native_command_site_keeps_native_routes_native(self):
  p=Synth();site=0x0808f38e;img=bytes(p.u.mem_read(site,4));h1,h2=struct.unpack('<HH',img)
  s=(h1>>10)&1;off=((s<<24)|((1-(((h2>>13)&1)^s))<<23)|((1-(((h2>>11)&1)^s))<<22)|((h1&0x3ff)<<12)|((h2&0x7ff)<<1))
  if s:off-=1<<25
  adapter=site+4+off
  seen=[]
  from unicorn import UC_HOOK_CODE
  p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:(seen.append(1),p.ret()) if a==0x080925e0 else None)
  for key,native in [(DECAY,0),(2,1)]:
   seen.clear();p.call(adapter,p.root,command(p,key,13,500));self.assertEqual(len(seen),native)
  self.assertEqual(routes(p),[(.5,DECAY,13,0)])
 def test_no_route_audio_is_unchanged(self):
  a=Synth().audio();p=Synth();p.route(DECAY,13,0);self.assertEqual(p.audio(),a) # amount 0
  p=Synth();p.route(2,13,500);self.assertEqual(p.audio(),a)
 def test_velocity_on_decay_changes_the_sound_and_keeps_the_knob(self):
  a=Synth().audio(40);p=Synth();p.route(DECAY,13,600);b=p.audio(40)
  self.assertGreater(tail(b),tail(a)*1.5) # longer decay; base 65 + 1.0 x 0.6 x 100
  self.assertEqual(list(p.u.mem_read(KNOBS+40,7)),[55,65,45,65,55,25,0])
 def test_negative_amounts_and_global_sources(self):
  a=Synth().audio(40)
  p=Synth();p.f(p.root+0x654,1.0);p.route(DECAY,9,-600);self.assertLess(tail(p.audio(40)),tail(a)*.2) # Auto A pulls Decay down
  p=Synth();p.route(DECAY,9,-600);self.assertEqual(p.audio(40),a) # Auto A at zero: no change
  p=Synth();p.f(p.root+0x10c,1.0);p.route(TUNE,26,500);self.assertNotEqual(p.audio(),Synth().audio()) # mod wheel on Tune
 def test_routes_made_for_another_engine_stay_silent(self):
  a=Synth().audio();p=Synth(reserved=1|3<<4);p.route(DECAY,13,600);self.assertEqual(p.audio(),a)
  p=Synth(reserved=1|1<<4);p.route(DECAY,13,600);self.assertNotEqual(p.audio(),a)
 def test_pad_without_its_ui_entry_is_not_modulated(self):
  p=Synth();p.u.mem_write(KNOBS+32,bytes(16));a=p.audio()
  q=Synth();q.u.mem_write(KNOBS+32,bytes(16));q.route(DECAY,13,600);self.assertEqual(q.audio(),a)
 def test_modulation_is_clamped_to_the_parameter_range(self):
  p=Synth();p.route(DECAY,13,1000);p.route(DECAY,26,1000,slot=1);p.f(p.root+0x10c,1.0)
  q=Synth(values=(55,100,45,65,55,25,0))
  self.assertEqual(p.audio(),q.audio()) # 65+100+100 -> 100
if __name__=='__main__':unittest.main(verbosity=2)
