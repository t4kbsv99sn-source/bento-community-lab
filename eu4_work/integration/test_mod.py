"""P8 mod mode, UI core (M4). The synth page view is built by its native
constructor (0815E228) and its native event handler, encoder slots (08171C1C,
08170656) and registry run. The model tree, getters, the route lookup
(08131244) and the model event entry (081403EC, D1 routes) are fixtures that
keep routes like the native setter 08133388: one route per (node, key, slot),
source 0 removes."""
import struct,unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE
V=0xc0400000;EV=0x20031000;OUT=0x20031400;TRACK=0x91
# Track children: (handle, node type). WT 6 x2, Osc 8, Env 9 x2, Filter 10 x2, LFO 11 x2.
KIDS=[(0x200,6),(0x201,6),(0x202,8),(0x203,9),(0x204,9),(0x205,10),(0x206,10),(0x207,11),(0x208,11)]
FILT1,FILT2,ENV1,LFO1=0x205,0x206,0x203,0x207
KEEP=[]
class Page(Fixture):
 def __init__(self,track_type=18):
  super().__init__();KEEP.append(self);self.u.mem_map(0xc0400000,0x40000)
  self.registry();self.w(0x3000004c,self.next);self.w(0x30000048,0xc0200000)
  self.track=TRACK;self.track_type=track_type;self.routes={};self.events=[];self.posted=[];self.values={}
  for a in [0x08133cfc,0x08133f7c,0x0813391a,0x08131244,0x081403ec,0x08133614,0x0816fc34,0x0815d7d0]:
   self.u.hook_add(UC_HOOK_CODE,self.model,begin=a,end=a)
  self.call(0x0815e228,V);self.w(0x3000004c,self.next);self.w(V+0x2430,TRACK);self.w(V+0x2434,0)
  self.select(5) # Filter 1 section
  self.bind([0xce,0x33,0x7f,0,0,0,0,0])
 def model(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0x08133cfc:self.w(r[1],self.track);self.ret(1)
  elif a==0x08133f7c:
   h=self.r(r[1]);self.ret(self.track_type if h==self.track else dict(KIDS).get(h,0))
  elif a==0x0813391a:
   if self.r(r[1])==self.track and r[2]<len(KIDS):self.w(r[3],KIDS[r[2]][0]);self.ret(1)
   else:self.ret(0)
  elif a==0x08131244:
   h=self.r(r[1]);sp=u.reg_read(UC_ARM_REG_SP);out=self.r(sp)
   e=self.routes.get((h,r[2]&0xffff,r[3]))
   if e:self.w(out,e[1]);self.w(out+4,e[0]|(r[2]&0xffff)<<16);self.w(out+8,r[3]);self.ret(0x20030000)
   else:self.ret(0)
  elif a==0x081403ec:
   ev=struct.unpack('<5I',u.mem_read(r[1],20));self.events.append(ev)
   if ev[0]==0xd1:
    key=ev[2]&0xffff;src=ev[3]&0xffff;slot=ev[3]>>16;amount=struct.unpack('<i',struct.pack('<I',ev[4]))[0]
    if src:self.routes[(ev[1],key,slot)]=(src,amount)
    else:self.routes.pop((ev[1],key,slot),None)
   self.ret(0)
  elif a==0x08133614:self.w(r[3],self.values.get((self.r(r[1]),r[2]),500));self.ret(1)
  elif a==0x0816fc34:self.posted.append(struct.unpack('<H',u.mem_read(r[1],2))[0]);self.ret()
  elif a==0x0815d7d0:self.ret()
 def select(self,tile):self.u.mem_write(V+0x10238,bytes([tile]))
 def bind(self,keys):
  for i,k in enumerate(keys):
   s=V+0x70+i*0x468
   if k:self.call(0x08171c1c,s,k,self.values.get((FILT1,k),500),1)
   else:self.u.mem_write(s+0x9c,b'\0\0')
 def tick(self,t=1000):self.w(0x3001fe2c,t);self.call(UU['mod_view_tick'],V,0)
 def event(self,code,a=0,b=0,c=0):
  self.u.mem_write(EV,struct.pack('<HH4I',code,0,a,b,c&0xffffffff,0));return self.call(UU['mod_view_event'],V,EV)
 def tap(self,tile):return self.event(0x79,0,tile)
 def turn(self,slot,delta,handle=FILT1):
  s=V+0x70+slot*0x468;key=struct.unpack('<H',self.u.mem_read(s+0x9c,2))[0]
  return self.event(0xcf,handle,key,self.shown(slot)+delta)
 def shown(self,slot):return struct.unpack('<i',self.u.mem_read(self.state()+0x70+4*slot,4))[0]
 def state(self):
  return self.r(self.slot())
 def slot(self):
  # UI struct: last pointer is mod_state; find by magic of the allocated block.
  for a in range(0x24048000,0x24048480,4):
   v=self.r(a)
   if 0xc0000000<=v<0xc0200000 and self.r(v)==0x444f4d50:return a
  raise AssertionError('no mod state')
 def text(self,a):return bytes(self.u.mem_read(a,40)).split(b'\0')[0].decode('latin1')
 def label(self,slot):return self.text(V+0x70+slot*0x468+0x2c8)
 def frame(self,tile):return self.r(V+0x2734+tile*0x40),self.r(V+0x2738+tile*0x40)
 def header(self):
  out=0x20032000;self.u.mem_write(out,IMAGE[0x08199008+10*0x1c4-0x08040000:][:0x1c4])
  self.call(UU['mod_toolbar'],0x30024b00,out)
  recs=[]
  for i in range(6):
   r=bytes(self.u.mem_read(out+0x74+48*i,48));recs.append((r[:32].split(b'\0')[0].decode(),struct.unpack_from('<H',r,44)[0],r[0x22],r[0x21]))
  return recs
class Tests(unittest.TestCase):
 def test_hooks_are_the_synth_view_vtable(self):
  for slot,fn in [(0x0819e894,'mod_view_tick'),(0x0819e8c4,'mod_view_event')]:
   self.assertEqual(struct.unpack_from('<I',IMAGE,slot-0x08040000)[0],UU[fn]|1)
 def test_header_moves_tabs_left_and_adds_mod_and_matrix_next_to_the_counter(self):
  p=Page();p.tick();h=p.header()
  self.assertEqual([x[0] for x in h],['','Dashboard','Grain 1','Grain 2','MOD','MATRIX'])
  self.assertEqual([x[2] for x in h],[0,1,1,1,0,0]);self.assertEqual((h[4][1],h[5][1]),(0x1057,0x1058))
  self.assertEqual(p.header(),p.header()) # stable from tick to tick
  p.event(0x1057);h=p.header();self.assertEqual(h[4][0],'MOD: SELECT');self.assertEqual(h[4][3],1)
 def test_other_page_headers_are_left_alone(self):
  p=Page();p.tick();out=0x20032000
  for k in (8,36,12):
   t=IMAGE[0x08199008+k*0x1c4-0x08040000:][:0x1c4];p.u.mem_write(out,t);p.call(UU['mod_toolbar'],0x30024b00,out)
   self.assertEqual(bytes(p.u.mem_read(out,0x1c4)),t)
 def test_buttons_appear_without_any_view_tick(self):
  # P11 (owner: MOD/MATRIX never showed on 1.6P10): the header no longer waits for
  # the view's vtable [0]; the synth template and a synth track are enough.
  p=Page();h=p.header();self.assertEqual([x[0] for x in h][4:],['MOD','MATRIX'])
  p.event(0x1057);p.tap(8);h=p.header();self.assertEqual(h[4][0],'MOD LFO1');self.assertEqual(p.frame(8),(0xf6,3))
 def test_header_drives_the_track_switch_off(self):
  p=Page();p.event(0x1057);p.tap(8);p.header();self.assertEqual(p.label(0),'0%')
  p.track=0x92;p.w(V+0x2430,0x92);p.header() # another synth track selected
  self.assertEqual(p.label(0),'');self.assertEqual(p.frame(8),(0xf3,1));self.assertEqual(p.header()[4][0],'MOD')
 def test_matrix_opens_the_native_mod_matrix_like_the_burger_menu(self):
  # P11: the synth page burger (native menu F3) has one entry, 0B "Modulation";
  # the view posts A8 (this track) then 0B, which opens the matrix (0A is the pad menus').
  p=Page();p.tick();self.assertEqual(p.event(0x1058),0)
  self.assertEqual(p.posted[-2:],[0xa8,0x0b])
  cell=struct.unpack_from('<5I',IMAGE,0x8198454-4-0x08040000);self.assertEqual(cell[0],0x0b)
  self.assertEqual(p.text(cell[1]),'Modulation')
 def test_tile_taps_toggle_sources_with_an_orange_outline_and_do_not_select(self):
  p=Page();p.tick();p.event(0x1057)
  self.assertEqual(p.tap(8),0);self.assertEqual(p.frame(8),(0xf6,3)) # LFO 1
  self.assertEqual(p.u.mem_read(V+0x10238,1)[0],5) # Filter 1 stays selected
  p.tap(3);self.assertEqual(p.frame(3),(0xf6,3));p.tap(8);self.assertEqual(p.frame(8),(0xf3,1))
  self.assertEqual(p.event(0x7b,0,7),0) # Mod Seq double tap does not open its page
 def test_tiles_are_native_when_mod_mode_is_off(self):
  p=Page();p.tick();p.u.mem_write(V+0xfc88,b'\x01');p.tap(8)
  self.assertEqual(p.u.mem_read(V+0x10238,1)[0],8);self.assertEqual(p.frame(8),(0xf2,2))
 def test_encoder_sets_depth_for_every_selected_source_and_leaves_the_value(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.tap(3);p.tick()
  self.assertEqual(p.label(0),'0%');self.assertEqual(p.label(2),'') # key 7F is no destination
  self.assertEqual(p.turn(0,250),0) # quarter of the knob range = +50%
  self.assertEqual(p.routes,{(FILT1,0xce,0):(1,500),(FILT1,0xce,1):(4,500)})
  self.assertFalse(any(e[0]==0xcf for e in p.events)) # cutoff itself unchanged
  self.assertEqual(p.label(0),'+50%')
  p.turn(0,-750);self.assertEqual(p.routes[(FILT1,0xce,1)],(4,-1000));self.assertEqual(p.label(0),'-100%')
  p.turn(0,-5);self.assertEqual(p.routes[(FILT1,0xce,0)][1],-1000) # clamped
 def test_native_widget_refresh_does_not_reset_depth_on_next_turn(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.turn(0,100)
  for _ in range(6):
   # Native synth header rebinds the original parameter value every refresh.
   p.call(0x08171c1c,V+0x70,0xce,500,0)
   p.header()
   self.assertEqual(p.r(V+0x70+0xa0),p.shown(0))
   p.turn(0,25)
  self.assertEqual(p.routes[(FILT1,0xce,0)],(4,500))
 def test_selected_sources_are_named_in_the_header_and_restore_on_deselect(self):
  p=Page();p.event(0x1057);self.assertEqual(p.header()[4][0],'MOD: SELECT')
  p.tap(8);self.assertEqual(p.header()[4][0],'MOD LFO1')
  p.tap(3);self.assertEqual(p.header()[4][0],'MOD ENV1+LFO1')
  p.tap(8);self.assertEqual(p.header()[4][0],'MOD ENV1')
 def test_back_to_zero_removes_the_routes(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.tick();p.turn(0,10);self.assertEqual(p.routes,{(FILT1,0xce,0):(4,20)})
  p.turn(0,-10);self.assertEqual(p.routes,{})
 def test_existing_routes_keep_their_slot_and_full_destinations_are_skipped(self):
  p=Page();p.routes={(FILT1,0xce,0):(13,300),(FILT1,0xce,1):(4,-200)};p.tick();p.event(0x1057);p.tap(8);p.tick()
  self.assertEqual(p.label(0),'-20%');p.turn(0,50)
  self.assertEqual(p.routes[(FILT1,0xce,1)],(4,-100));self.assertEqual(p.routes[(FILT1,0xce,0)],(13,300)) # velocity untouched
  p.routes[(FILT1,0xce,2)]=(9,100);p.tap(9);p.turn(0,50) # LFO 2: no free slot left
  self.assertNotIn(5,[v[0] for v in p.routes.values()])
 def test_slight_turn_still_moves_depth(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.tick();p.turn(1,1) # resonance, range 0..1000? any range
  self.assertEqual(list(p.routes.values())[0][1] in (10,20),True)
 def test_without_sources_encoders_stay_native(self):
  p=Page();p.tick();p.event(0x1057);p.tick();self.assertEqual(p.label(0),'')
  self.assertEqual(p.turn(0,10),1) # handled natively
 def test_other_section_uses_its_own_node(self):
  p=Page();p.select(6);p.tick();p.event(0x1057);p.tap(8);p.tick();p.turn(0,50,FILT2)
  self.assertEqual(list(p.routes),[(FILT2,0xce,0)])
 def test_non_destination_node_stays_native(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.tick();self.assertEqual(p.turn(0,50,ENV1),1);self.assertEqual(p.routes,{})
 def test_off_restores_values_and_outlines(self):
  p=Page();p.values[(FILT1,0xce)]=700;p.tick();p.event(0x1057);p.tap(8);p.tick();p.turn(0,100)
  p.event(0x1057);self.assertEqual(p.label(0),'2.5kHz L1');self.assertEqual(p.frame(8),(0xf3,1)) # P26 (owner): native value + source tag (was '*')
  self.assertEqual(p.routes[(FILT1,0xce,0)][0],4) # routes stay
 def test_tags_name_every_routed_source(self):
  # P26: Env1 (tile 3) and LFO1 (tile 8) on one target -> both tags, in route-slot order.
  p=Page();p.values[(FILT1,0xce)]=700;p.tick();p.event(0x1057);p.tap(3);p.tap(8);p.tick();p.turn(0,100)
  p.event(0x1057);self.assertIn(p.label(0),('2.5kHz E1 L1','2.5kHz L1 E1'))
 def test_switching_tracks_turns_mod_mode_off(self):
  p=Page();p.tick();p.event(0x1057);p.tap(8);p.tick();self.assertEqual(p.label(0),'0%')
  p.w(V+0x2430,0x92);p.tick();self.assertEqual(p.label(0),'');self.assertEqual(p.frame(8),(0xf3,1))
  p.w(V+0x2430,TRACK);p.tick();p.turn(0,50);self.assertEqual(p.routes,{})
 def test_granular_page_works_too(self):
  p=Page(19);p.tick();p.event(0x1057);p.tap(9);p.tick();p.turn(0,50);self.assertEqual(p.routes[(FILT1,0xce,0)][0],5)
 def test_not_a_synth_track_never_turns_on(self):
  p=Page(15);p.tick();p.event(0x1057);p.tap(8);self.assertEqual(p.frame(8)[0]!=0xf6,True);self.assertNotEqual(p.header()[4][1],0x1057)
if __name__=='__main__':unittest.main()
