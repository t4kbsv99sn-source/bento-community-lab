"""A1 Analog instrument, UI core (M4): native instrument menu entry, track
marking and persistence. Model reads/writes and event posting are fixtures."""
import struct,unittest,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE
KNOBS=0x24043500;TRACK=0x91;VIEW=0x20030000;EV=0x20031000
KEEP=[]
class UI(Fixture):
 def __init__(self):
  super().__init__();KEEP.append(self);self.posted=[];self.native_calls=[];self.type=18
  self.u.hook_add(UC_HOOK_CODE,self.model)
 def model(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0x0816fc34:self.posted.append(struct.unpack('<5I',u.mem_read(r[1],20)));self.ret()
  elif a==0x08133614:self.w(r[3],3);self.ret(1)
  elif a==0x08133cfc:self.w(r[1],TRACK);self.ret(1)
  elif a==0x08133f7c:self.ret(self.type)
  elif a==0x0814ecd4:self.native_calls.append(struct.unpack('<H',u.mem_read(r[1],2))[0]);self.ret(0)
 def menu(self,code):self.u.mem_write(EV,struct.pack('<5I',code,0,0,0,0));return self.call(UU['analog_menu_event'],VIEW,EV)
 def analog(self,handle=TRACK):return self.call(UU['analog_track'],handle)
 def sync(self):
  for i in range(128):
   e=KNOBS+32+i*16
   if self.r(e) and self.r(e+4)==TRACK:return self.u.mem_read(e+8,1)[0]
class Tests(unittest.TestCase):
 def test_menu_has_analog_in_the_ninth_cell(self):
  cell=0x081981f8+8*20;code,label,_,_,_=struct.unpack('<5I',IMAGE[cell-0x08040000:cell-0x08040000+20])
  p=UI();self.assertEqual(code,0x1052);self.assertEqual(p.text(label),'Analog')
  self.assertEqual(IMAGE[0x08141370-0x08040000:0x08141372-0x08040000],bytes.fromhex('0923')) # movs r3,#9
 def test_analog_action_makes_a_wavetable_track_and_marks_it(self):
  p=UI();self.assertEqual(p.analog(),0);p.menu(0x1052)
  self.assertEqual(p.posted[0][:4],(0x42,0,6,3)) # native "Wavetable" for the selected track
  self.assertEqual(p.posted[1][0],0x16);self.assertEqual(p.analog(),1);self.assertEqual(p.native_calls,[])
 def test_choosing_plain_wavetable_clears_analog(self):
  p=UI();p.menu(0x1052);p.menu(0x102a);self.assertEqual(p.native_calls,[0x102a]);self.assertEqual(p.analog(),0)
 def test_other_menu_actions_stay_native(self):
  p=UI();p.menu(0x1052);p.menu(0x1024);self.assertEqual(p.native_calls,[0x1024]);self.assertEqual(p.analog(),1)
 def test_not_a_wavetable_track_is_not_marked(self):
  p=UI();p.type=14;p.menu(0x1052);self.assertEqual(p.analog(),0)
 def test_saved_and_loaded_with_the_track(self):
  p=UI();p.menu(0x1052);obj=0x20031200;p.u.mem_write(obj+4,b'\x12');p.w(obj+0x10,TRACK)
  p.call(UU['kick_ui_save'],obj,0x20017000);self.assertEqual(p.attrs['bento_analog'],1);self.assertEqual(p.attrs['bento_analog_sync'],0)
  p.menu(0x102a);self.assertEqual(p.analog(),0)
  p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.analog(),1);self.assertEqual(p.sync(),0)
  p.attrs['bento_analog_sync']=1;p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.sync(),1)
  p.attrs['bento_analog']=0;p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.analog(),0)
 def test_plain_wavetable_saves_nothing(self):
  p=UI();obj=0x20031200;p.u.mem_write(obj+4,b'\x12');p.w(obj+0x10,TRACK)
  p.call(UU['kick_ui_save'],obj,0x20017000);self.assertNotIn('bento_analog',p.attrs)
 def test_sync_is_private(self):
  p=UI();p.registry();p.menu(0x1052);out=0x20031300
  p.call(UU['analog_get'],0x1d1,out);self.assertEqual(p.r(out),0)
  d=p.r(0x30031484)+0x1d1*32;self.assertEqual(struct.unpack('<H',p.u.mem_read(d,2))[0],0x1d1);self.assertEqual(p.text(p.r(d+4)),'Sync');self.assertEqual((p.r(d+16),p.r(d+20)),(0,1))
  p.u.mem_write(EV,struct.pack('<4I',0xcf,TRACK,0x1d1,1));self.assertEqual(p.call(UU['analog_model_event'],0x30024b00,EV),1)
  self.assertEqual(p.sync(),1);p.call(UU['analog_get'],0x1d1,out);self.assertEqual(p.r(out),1)
  p.u.mem_write(EV,struct.pack('<4I',0xcf,TRACK,0x1d1,0));p.call(UU['analog_model_event'],0x30024b00,EV);self.assertEqual(p.sync(),0)
  p.u.mem_write(EV,struct.pack('<4I',0xcf,TRACK,2,5));self.assertEqual(p.call(UU['analog_model_event'],0x30024b00,EV),0) # other keys stay native
 def test_sync_on_a_plain_wavetable_does_nothing(self):
  p=UI();p.u.mem_write(EV,struct.pack('<4I',0xcf,TRACK,0x1d1,1));p.call(UU['analog_model_event'],0x30024b00,EV);self.assertEqual(p.analog(),0)
 def keys(self,p,wavetable=1):
  src=0x0819e918;dst=0x20032000;p.call(UU['analog_page_keys'],dst,src,0xb0,wavetable)
  return list(struct.unpack('<88H',p.u.mem_read(dst,0xb0)))
 def test_analog_page_gets_glide_sync_shape_and_pane_text(self):
  p=UI();p.registry();native=list(struct.unpack_from('<88H',IMAGE,0x0819e918-0x08040000))
  self.assertEqual(native[:16],[0xc4,3,0xc9,0,0,0,0,0,0xc4,3,0xc9,0,0,0,0,0])
  self.assertEqual(self.keys(p),native);self.assertEqual(p.text(0x24043d4c),'No WAV');self.assertEqual(p.text(0x24043d58),'Double-tap to load WAV')
  pos=p.r(0x30031484)+0xc9*32;self.assertEqual(p.text(p.r(pos+4)),'Position')
  p.menu(0x1052);k=self.keys(p)
  self.assertEqual(k[:4],[0xc4,3,0xc9,0x142]);self.assertEqual(k[8:12],[0xc4,3,0xc9,0x1d1]);self.assertEqual(k[16:],native[16:])
  self.assertEqual(p.text(p.r(pos+4)),'Shape');self.assertEqual(p.text(0x24043d4c),'Analog')
  p.menu(0x102a);self.assertEqual(self.keys(p),native);self.assertEqual(p.text(p.r(pos+4)),'Position') # plain Wavetable again
  p.menu(0x1052);self.keys(p);self.assertEqual(self.keys(p,0),native);self.assertEqual(p.text(p.r(pos+4)),'Position') # Granular page
 def test_glide_is_private_and_scaled(self):
  p=UI();p.registry();p.menu(0x1052);out=0x20031300
  p.u.mem_write(EV,struct.pack('<4I',0xcf,TRACK,0x142,455));self.assertEqual(p.call(UU['analog_model_event'],0x30024b00,EV),1)
  p.call(UU['analog_get'],0x142,out);self.assertEqual(p.r(out),460)
  e=[KNOBS+32+i*16 for i in range(128) if p.r(KNOBS+32+i*16+4)==TRACK][0];self.assertEqual(p.u.mem_read(e+9,1)[0],46)
  d=p.r(0x30031484)+0x142*32;self.assertEqual(p.text(p.r(d+4)),'Glide')
  obj=0x20031200;p.u.mem_write(obj+4,b'\x12');p.w(obj+0x10,TRACK);p.call(UU['kick_ui_save'],obj,0x20017000);self.assertEqual(p.attrs['bento_analog_glide'],46)
  p.menu(0x102a);p.call(UU['kick_ui_load'],0x20017100,obj);self.assertEqual(p.u.mem_read(e+9,1)[0],46)
 def test_wave_pane_hooks_and_shape(self):
  # P4: the wave pane class tick/paint go through our functions.
  for slot,fn in [(0x081b3a18,'analog_wave_tick'),(0x081b3a1c,'analog_wave_paint')]:
   self.assertEqual(struct.unpack_from('<I',IMAGE,slot-0x08040000)[0],UU[fn]|1)
  p=UI();v=lambda s,q:struct.unpack('<i',struct.pack('<I',p.call(UU['analog_wave_value'],s,q)))[0]
  self.assertEqual([v(0,q) for q in (0,512,1023)],[-1024,0,1022]) # saw
  self.assertEqual([v(128,q) for q in (0,511,512,1023)],[1024,1024,-1024,-1024]) # square
  self.assertEqual([v(255,q) for q in (0,80,90,512)],[1024,1024,-1024,-1024]) # 8% pulse
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
