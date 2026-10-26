"""P27 performance macros. The synth page is built by its native constructor,
so the encoder strip (vtable 081B2838), its eight slots, the native slot turn
08171E44 (through K15's increment hook), label setter 0817E85E and value text
override 08170656 are the real firmware code. Model getters/events, track
lookup and XML attributes are fixtures (test_mod.Page)."""
import struct,unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import IMAGE,UU
from test_mod import Page,V,TRACK,FILT1
BAR=V+0x38;PT=0x20031800;OUT=0x20032400;BASE=0x08040000
def slot(i):return BAR+0x38+i*0x468
class Macros(Page):
 def __init__(self):
  super().__init__();self.tracks[0]=TRACK;self.strings={}
  for a in [0x08133e54,0x08109582,0x081094c2,0x08104c08]:self.u.hook_add(UC_HOOK_CODE,self.xml,begin=a,end=a)
  self.shift(0)
 def xml(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1)]
  if a==0x08104c08:self.w(0x3000004c,self.next) # the native bump allocator moves its cursor
  elif a==0x08133e54:self.ret(0)
  elif a==0x08109582:self.strings[self.handles[r[0]]]=bytes(self.u.mem_read(r[1],4000)).split(b'\0')[0].decode();self.ret()
  elif a==0x081094c2:
   s=self.strings[self.handles[r[0]]].encode()+b'\0';self.u.mem_write(0x20033000,s);self.ret(0x20033000)
 def shift(self,on):self.w(0x24048d68,1 if on else 0)
 def touch(self,fn,x,y):self.w(0x3000004c,self.next);self.w(PT,x);self.w(PT+4,y);self.call(UU[fn],BAR,PT,0)
 def swipe(self,dx):
  x=600;y=440;self.touch('macro_bar_down',x,y)
  for k in range(1,6):self.touch('macro_bar_move',x+dx*k//5,y)
  self.touch('macro_bar_up',x+dx,y)
 def tap(self,i):
  x=self.r(slot(i)+4)+20;y=440;self.touch('macro_bar_down',x,y);self.touch('macro_bar_up',x,y)
 def name(self,i):return self.text(slot(i)+0x3f9)
 def value_text(self,i):return self.text(slot(i)+0x2c8)
 def turn(self,i,delta,raw=False):
  if not raw:delta*=160000//127+1 if self.overlay() else 1
  self.call_turn(i,delta)
 def overlay(self):
  return self.call(UU['macro_overlay'])!=0
 def call_turn(self,i,delta):self.w(0x3000004c,self.next);self.events=[];self.posted=[];self.call(0x08171e44,slot(i),delta)
 def change(self,key,value,h=FILT1):
  # what the page sends the model for a turned encoder: CF {CF, node, key, value}
  ev=0x20031c00;self.u.mem_write(ev,struct.pack('<HH4I',0xcf,0,h,key,value,0));self.call(UU['analog_model_event'],0x30024b00,ev);self.values[(h,key)]=value
 def cf(self):return [e for e in self.events if e[0]==0xcf]

class MacroTest(unittest.TestCase):
 def test_strip_vtable_takes_touches_only_through_macro_handlers(self):
  for k,fn in [(4,'macro_bar_down'),(5,'macro_bar_move'),(6,'macro_bar_up'),(7,'macro_bar_takes')]:
   self.assertEqual(struct.unpack_from('<I',IMAGE,0x081b2838+4*k-BASE)[0],UU[fn]|1)
  p=Macros();self.assertEqual(p.r(BAR),0x081b2838);self.assertEqual(p.r(slot(3)+0x2c),BAR)
  self.assertEqual(p.call(UU['macro_bar_takes'],BAR),1)
 def test_native_hit_test_delivers_strip_touches_to_the_strip(self):
  # 0816FA10 is the firmware's own hit test: children first, then the
  # container itself when it contains the point and takes touches.
  p=Macros();out=0x20031900
  p.w(PT,344);p.w(PT+4,426);self.assertEqual(p.call(0x0816fa10,V,PT,out),1);self.assertEqual(p.r(out),BAR)
  p.w(PT,344);p.w(PT+4,300);p.call(0x0816fa10,V,PT,out);self.assertNotEqual(p.r(out),BAR) # tiles stay native
 def test_swipe_left_shows_macros_and_swipe_right_restores_native_strip(self):
  p=Macros();native=[p.name(i) for i in range(8)]
  p.swipe(-200);self.assertEqual([p.name(i) for i in range(8)],['MACRO %d'%(i+1) for i in range(8)])
  self.assertEqual(p.value_text(0),'0')
  p.swipe(200);self.assertEqual([p.name(i) for i in range(8)],native);self.assertEqual(p.value_text(0),'')
 def test_short_or_vertical_moves_are_not_swipes(self):
  p=Macros();native=p.name(0);p.swipe(-40);self.assertEqual(p.name(0),native)
  p.touch('macro_bar_down',600,440);p.touch('macro_bar_move',520,300);p.touch('macro_bar_up',520,300);self.assertEqual(p.name(0),native)
 def test_overlay_owns_encoders_and_native_parameter_is_untouched(self):
  p=Macros();p.swipe(-200);p.turn(2,5)
  self.assertEqual(p.posted,[]);self.assertEqual(p.cf(),[]);self.assertEqual(p.value_text(2),'5')
  p.turn(2,-9);self.assertEqual(p.value_text(2),'0')
 def test_assign_by_turning_and_macro_drives_target_between_start_and_end(self):
  p=Macros();p.values[(FILT1,0x33)]=200;p.swipe(-200);p.tap(0);self.assertEqual(p.value_text(0),'ARM')
  out=0x20032000;p.u.mem_write(out,bytes(0x1c4));p.call(UU['macro_periodic'],out);self.assertEqual(p.text(out+0x196),'MACRO 1')
  p.swipe(200);p.turn(1,4000) # native turn of the Resonance slot (key 0x33) while armed
  self.assertIn(0xcf,p.posted) # the native parameter still moves while mapping
  p.change(0x33,450);p.change(0x33,700)
  p.swipe(-200);p.tap(0) # settle + disarm
  self.assertEqual(p.name(0),'Resonance') # named after its first target
  p.turn(0,127);ev=p.cf();self.assertEqual(len(ev),1);self.assertEqual(ev[0][1:4],(FILT1,0x33,700))
  p.turn(0,-127);self.assertEqual(p.cf()[0][3],200)
  for _ in range(64):p.turn(0,1)
  v=struct.unpack('<i',struct.pack('<I',p.cf()[0][3]))[0];self.assertTrue(440<=v<=460,v)
 def test_turning_back_to_the_start_unmaps(self):
  p=Macros();p.values[(FILT1,0x33)]=300;p.swipe(-200);p.tap(0);p.swipe(200);p.turn(1,4000);p.change(0x33,500);p.change(0x33,300);p.swipe(-200);p.tap(0)
  p.turn(0,10);self.assertEqual(p.cf(),[])
 def test_proj_tap_clears_a_macro(self):
  p=Macros();p.values[(FILT1,0x33)]=100;p.swipe(-200);p.tap(4);p.swipe(200);p.turn(1,4000);p.change(0x33,900)
  p.swipe(-200);p.tap(4);p.shift(1);p.tap(4);p.shift(0);p.turn(4,50);self.assertEqual(p.cf(),[]);self.assertEqual(p.name(4),'MACRO 5')
 def test_save_and_load_round_trip_by_track_path(self):
  p=Macros();p.values[(FILT1,0x33)]=250;p.swipe(-200);p.tap(2);p.swipe(200);p.turn(1,4000);p.change(0x33,650)
  p.swipe(-200);p.tap(2);p.turn(2,64)
  obj=0x20010000;p.w(obj+16,TRACK);p.call(UU['macro_save'],obj,0x20017000)
  saved=p.strings['playground_macros_v1'];self.assertTrue(saved.startswith('01'))
  q=Macros();q.attrs['playground_macros_v1']=1;q.strings['playground_macros_v1']=saved
  q.u.mem_write(0x20010000,bytes(32));q.w(0x20010010,TRACK)
  q.call(UU['macro_load'],0x20011000,0x20010000)
  q.swipe(-200);self.assertEqual(q.value_text(2),'64');q.turn(2,63);self.assertEqual(q.cf()[0][1:4],(FILT1,0x33,650))
 def test_save_writes_nothing_without_macros_or_on_other_objects(self):
  p=Macros();obj=0x20010000;p.w(obj+16,TRACK);p.call(UU['macro_save'],obj,0x20017000);self.assertNotIn('playground_macros_v1',p.strings)
 def test_tap_outside_overlay_reaches_native_hit_test_without_error(self):
  p=Macros();native=p.name(0);p.touch('macro_bar_down',300,440);p.touch('macro_bar_up',300,440);self.assertEqual(p.name(0),native)
if __name__=='__main__':unittest.main(verbosity=2)
