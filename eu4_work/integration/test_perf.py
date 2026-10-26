"""P1 performance page: PROJ+PLAY / PROJ+Left buttons (M4), the page rows and
values, tap tempo, per-track fixed velocity, and the M7 pad-press hook.

Runs the built image. Native model calls (getter 08133614, current track
08133CFC, navigation 081420EC, button event 08142AFC, model event 081403EC)
are fixtures; the M7 test runs the real native pad press from the patched call
site 080857D6."""
import struct,unittest,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,AA,IMAGE
M=0x30024b00;PROJECT=0x30030164;PROJ_HANDLE=0x77;SETTINGS=0x55;OUT=0x20034000;EV=0x20035000
LOCK=0x24048d60;MASK=0x24048d70;EC=0x24041fc0
KEEP=[]
class Page(Fixture):
 def __init__(self):
  super().__init__();KEEP.append(self);self.registry()
  self.w(0x3000004c,self.next);self.w(0x30000048,0xc0200000);self.w(PROJECT,PROJ_HANDLE)
  self.proj={0x8c:120,0x8d:0,0x8e:3,0x8f:50,0x131:0};self.track=0x91;self.octave=0;self.navs=[];self.buttons=[];self.model_events=[];self.page(0x17);self.ttype=18
  self.u.hook_add(UC_HOOK_CODE,self.native)
 def page(self,n):self.u.mem_write(M+0x12c,bytes([n]))
 def native(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0x08133614:
   # P7: 131 (track index) lives on the selection context 30030164; BPM, Scale,
   # Root and Swing on the project settings node (08133E54), handle SETTINGS.
   if r[2]==0x178 and self.r(r[1])==self.track:self.w(r[3],self.octave);self.ret(1)
   elif r[1]==PROJECT and r[2]==0x131:self.w(r[3],self.proj[0x131]);self.ret(1)
   elif self.r(r[1])==SETTINGS and r[2] in (0x8c,0x8d,0x8e,0x8f):self.w(r[3],self.proj[r[2]]);self.ret(1)
   else:self.ret(0)
  elif a==0x08133cfc:self.w(r[1],self.track);self.ret(1)
  elif a==0x081420ec:self.navs.append(r[1]);self.page(r[1]);self.ret()
  elif a==0x08142afc:self.buttons.append(struct.unpack('<3I',u.mem_read(r[1],12)));self.ret()
  elif a==0x081403ec:
   e=struct.unpack('<4I',u.mem_read(r[1],16));self.model_events.append(e)
   if e[0]==0xcf and e[1]==SETTINGS:self.proj[e[2]]=e[3]
   if e[0]==0xcf and e[1]==self.track and e[2]==0x178:self.octave=struct.unpack('<i',struct.pack('<I',e[3]))[0]
   self.ret(0)
  elif a in (0x08145cf4,0x08139138):self.ret()
  elif a==0x08133f7c:self.ret(self.ttype if self.r(r[1])==self.track else 0)
  elif a==0x08133e54:self.w(r[1],SETTINGS);self.ret(1)
 def button(self,code,index):return self.call(UU['fx_dispatch'],M,code,0,index)
 def open(self):
  self.w(LOCK+8,1);self.button(0xaf,15);self.w(LOCK+8,0)
 def header(self):
  self.u.mem_write(OUT,bytes(0x54));return self.call(UU['fx_header'],M,0,OUT,0,0x08145f22)
 def keys(self,rows=2):return [list(struct.unpack('<8H',self.u.mem_read(OUT+0x14+16*row,16))) for row in range(rows)]
 def mail(self):
  b=self.r(EC+4)
  if not b:return None
  m=b+44576;serial,active=self.r(m),self.r(m+4);count=list(self.u.mem_read(m+16,12))
  off=[list(struct.unpack('<6b',self.u.mem_read(m+32+pc*6,6)))[:count[pc]] for pc in range(12)]
  return active,off,self.r(m+8)
 def get(self,key,handle=0x20036000):self.w(0x20036100,0xdead);self.call(UU['fx_get'],M,handle,key,0x20036100);return self.r(0x20036100)
 def edit(self,key,value):self.u.mem_write(EV,struct.pack('<4I',0xcf,self.track,key,value));return self.call(UU['fx_event'],OUT-0x93c4,EV)
 def fixed(self):return self.r(EC+20)
class Tests(unittest.TestCase):
 def test_proj_play_opens_the_page_and_never_reaches_transport(self):
  p=Page();p.w(LOCK+8,1)
  self.assertEqual(p.button(0xaf,15),1);self.assertEqual(p.navs,[0x1a]);self.assertEqual(p.buttons,[])
  self.assertTrue(p.r(MASK)&1<<15);self.assertEqual(p.r(LOCK+12),1) # K16 consumes the release; PROJ counts as used
  self.assertEqual(p.button(0xb0,15),0) # release: K16's mask check consumes it
 def test_proj_play_again_goes_back(self):
  p=Page();p.open();p.w(LOCK+8,1);p.button(0xaf,15);self.assertEqual(p.navs,[0x1a,0x17])
 def test_proj_left_sends_undo_and_consumes_arrow_release(self):
  p=Page();p.w(LOCK+8,1);self.assertEqual(p.button(0xaf,0),1);self.assertEqual(p.buttons,[]);self.assertEqual(p.model_events[-1][0],0x1032)
  p.w(LOCK+8,0);self.assertEqual(p.button(0xb0,0),1) # the arrow release never reaches the view
  self.assertEqual(p.button(0xaf,0),0);self.assertEqual(p.button(0xb0,0),0) # plain Left stays native
 def burger(self,p):
  p.call(0x081412ec);t=IMAGE[0x8199008+20*0x1c4-0x8040000:][:0x1c4];p.page(0x1a);p.u.mem_write(OUT,t);p.call(UU['device_header_prepare'],OUT)
  for m in range(20):
   d=0x30030168+m*0xe0
   if p.r(d)==0xf9:return struct.unpack('<H',p.u.mem_read(OUT+0x194,2))[0],[(p.r(d+4+i*20),p.text(p.r(d+8+i*20))) for i in range(p.u.mem_read(d+0xcc,1)[0])]
 def test_proj_up_enters_sd_card_mode_through_the_native_action(self):
  # P26 (owner: SD card mode got lost): PROJ+Up posts native 101D (save, then disk mode).
  p=Page();p.w(LOCK+8,1);self.assertEqual(p.button(0xaf,1),1);self.assertEqual(p.model_events[-1][0],0x101d);self.assertEqual(p.buttons,[])
  self.assertEqual(p.button(0xb0,1),1);p.w(LOCK+8,0);n=len(p.model_events);p.button(0xaf,1);self.assertEqual(len(p.model_events),n) # plain Up stays native
 def test_performance_burger_holds_the_three_proj_pages(self):
  # P17 (owner plan): Projects / Settings / Date-Time only in the Performance page burger.
  p=Page();popup,menu=self.burger(p);self.assertEqual(popup,0)
  p=Page();p.open();popup,menu=self.burger(p);self.assertEqual(popup,0xf9)
  self.assertEqual(menu,[(0x1062,'Projects'),(0x1063,'Settings'),(0x1064,'Date / Time')])
  for code,page in [(0x1062,0x13),(0x1063,0x1a),(0x1064,0x19)]:
   q=Page();q.open();q.header();n=len(q.navs);q.u.mem_write(EV,struct.pack('<5I',code,0,0,0,0));self.assertEqual(q.call(UU['fx_event'],OUT-0x93c4,EV),1);self.assertEqual(q.navs[n:][-1],page)
 def test_holding_tracks_shows_track_colours_on_the_pads_and_restores_them(self):
  # P20 (owner): while TRACKS is held, each track's pads show its colour.
  p=Page();pads=M+0x19c4;objs={0:0x20010100,1:0x20010200,2:0x20010300}
  # The fixture answers 0812DC74 with .selected; answer property 73 (track number) for our tracks.
  base=p.selected
  def selected(self):
   r0,r1=self.u.reg_read(UC_ARM_REG_R0),self.u.reg_read(UC_ARM_REG_R1)
   return [k for k,v in objs.items() if v==r0][0] if r1==0x73 and r0 in objs.values() else base
  p.__class__=type('TrackPage',(Page,),{'selected':property(selected)});p.__dict__.pop('selected',None)
  flushes=[]
  p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:(flushes.append(1),p.ret()),begin=0x081257f0,end=0x081257f0)
  root=0x20010000;p.w(M,root);p.w(root+0x54,3) # native 0812D78A: count +54, tracks +34
  for k,v in objs.items():p.w(root+0x34+4*k,v)
  before=bytes(p.u.mem_read(pads,256));p.button(0xaf,2);p.page(2) # K16 opens the Tracks page
  col=lambda i:p.call(0x08140f50,i);off=p.call(0x08140fbc,0)
  got=[p.r(pads+i*16) for i in range(16)]
  self.assertEqual(got,[col(0),col(1),col(2)]+[off]*5+[col(0),col(1),col(2)]+[off]*5);self.assertEqual(len(flushes),1)
  p.button(0x8f,99);self.assertEqual(len(flushes),1) # unchanged: no extra flush
  p.button(0xb0,2);self.assertEqual(bytes(p.u.mem_read(pads,256)),before);self.assertEqual(len(flushes),2)
  # P22 (owner): pressing TRACKS on another page jumps to the Tracks page (2); colours still show.
  p.page(0x17);p.button(0xaf,2);p.page(2);p.u.mem_write(pads,bytes(256));p.button(0x8f,99)
  self.assertEqual([p.r(pads+i*16) for i in range(3)],[col(0),col(1),col(2)]);p.button(0xb0,2);p.page(2)
  # P21 (owner): picking a track during the hold leaves the new page's pads alone.
  p.button(0xaf,2);n=len(flushes);p.page(0x07);p.u.mem_write(pads,b'\x11'*256);p.button(0x8f,99)
  self.assertEqual(bytes(p.u.mem_read(pads,256)),b'\x11'*256)
  p.button(0xb0,2);self.assertEqual(bytes(p.u.mem_read(pads,256)),b'\x11'*256)
 def test_plain_play_stays_native(self):
  p=Page();self.assertEqual(p.button(0xaf,15),0);self.assertEqual(p.navs,[])
 def test_page_rows(self):
  p=Page();self.assertEqual(p.header(),0) # not open
  p.open();self.assertEqual(p.header(),1);self.assertEqual(p.u.mem_read(OUT,1)[0],3)
  self.assertEqual(p.keys(3),[[0x8c,0x101,0x8f,0x8e,0x8d,0,0,0],[0x102,0x11c,0x178,0,0,0,0,0],[0x104,0x132,0x14a,0x144,0,0,0,0]])
  self.assertEqual(p.text(p.r(OUT+4)),'Performance / Tempo & Key');self.assertEqual(p.text(p.r(OUT+8)),'Pads / Track 1')
  p.proj[0x131]=3;p.header();self.assertEqual(p.text(p.r(OUT+8)),'Pads / Track 4')
  r=p.r(0x30031484)
  for k,name in [(0x101,'Tap Tempo'),(0x102,'Fixed Vel'),(0x11c,'Velocity')]:self.assertEqual(p.text(p.r(r+k*32+4)),name)
  self.assertEqual(p.text(p.r(r+0x8c*32+4)),'BPM') # native descriptors untouched
 def test_tempo_and_key_are_the_project_values(self):
  p=Page();p.open();p.header()
  self.assertEqual([p.get(k) for k in (0x8c,0x8d,0x8e,0x8f)],[120,0,3,50])
  p.edit(0x8c,98);self.assertEqual(p.model_events[-1],(0xcf,SETTINGS,0x8c,98));self.assertEqual(p.get(0x8c),98)
  p.edit(0x8f,62);self.assertEqual(p.proj[0x8f],62);p.edit(0x8e,5);self.assertEqual(p.proj[0x8e],5)
 def test_closed_page_leaves_native_keys_alone(self):
  p=Page();self.assertEqual(p.get(0x8c),0xdead)
  p.open();p.header();p.call(UU['fx_nav'],M,0x27);self.assertEqual(p.get(0x8c),0xdead) # any other navigation closes it
 def test_tap_tempo(self):
  p=Page();p.open();p.header()
  for t in [1000,1500,2000,2500]:p.w(0x3001fe2c,t);p.edit(0x101,1)
  self.assertEqual(p.proj[0x8c],120)
  p.w(0x3001fe2c,2900);p.edit(0x101,1);self.assertEqual(p.proj[0x8c],126) # avg of 500,500,500,400
  p.w(0x3001fe2c,9000);n=len(p.model_events);p.edit(0x101,1);self.assertEqual(len(p.model_events),n) # long pause starts over
  p.w(0x3001fe2c,9250);p.edit(0x101,1);self.assertEqual(p.proj[0x8c],240)
  self.assertEqual(p.get(0x101),0)
 def test_fixed_velocity_is_per_track(self):
  p=Page();p.open();p.header()
  self.assertEqual((p.get(0x102),p.get(0x11c)),(0,100));self.assertEqual(p.fixed(),0)
  p.edit(0x11c,90);p.edit(0x102,1);self.assertEqual(p.fixed(),0x56454c00|90)
  p.track=0x92;p.button(0xfe,3);self.assertEqual(p.fixed(),0);self.assertEqual((p.get(0x102),p.get(0x11c)),(0,100))
  p.edit(0x11c,300);self.assertEqual(p.get(0x11c),127)
  p.track=0x91;p.button(0xfe,3);self.assertEqual(p.fixed(),0x56454c00|90)
  p.edit(0x102,0);self.assertEqual(p.fixed(),0)
 def test_fixed_velocity_saved_with_the_track(self):
  p=Page();p.open();p.header();p.edit(0x11c,64);p.edit(0x102,1);obj=0x20031200;p.w(obj+0x10,0x91);p.u.mem_write(obj+4,b'\x12')
  p.call(UU['fx_save'],obj,0x20017000);self.assertEqual(p.attrs['bento_perf_velocity'],0x100|64)
  p.edit(0x102,0);p.edit(0x11c,100);p.attrs.clear();p.call(UU['fx_save'],obj,0x20017000);self.assertNotIn('bento_perf_velocity',p.attrs)
  p.attrs['bento_perf_velocity']=0x100|33;p.call(UU['fx_load'],0x20017100,obj);self.assertEqual((p.get(0x102),p.get(0x11c)),(1,33))
  del p.attrs['bento_perf_velocity'];p.call(UU['fx_load'],0x20017100,obj);self.assertEqual((p.get(0x102),p.get(0x11c)),(0,100))
 def test_fixed_velocity_loads_before_the_page_was_ever_opened(self):
  p=Page();obj=0x20031200;p.w(obj+0x10,0x91);p.u.mem_write(obj+4,b'\x12');p.attrs['bento_perf_velocity']=0x100|20
  p.call(UU['fx_load'],0x20017100,obj);p.button(0xfe,3);self.assertEqual(p.fixed(),0x56454c00|20)
class Chord(unittest.TestCase):
 def page(self):p=Page();p.open();p.header();p.w(0x3000004c,p.next);return p
 def test_row_and_names(self):
  p=self.page();self.assertEqual(p.text(p.r(OUT+12)),'Chord / Track 1');r=p.r(0x30031484)
  for k,name in [(0x104,'Chord'),(0x132,'Type'),(0x14a,'Voicing'),(0x144,'Inversion')]:self.assertEqual(p.text(p.r(r+k*32+4)),name)
  t=r+0x132*32;self.assertEqual([p.text(p.r(p.r(t+8)+4*i)) for i in (0,1,15,16)],['Major','Minor','Diatonic','Diatonic 7']);self.assertEqual(p.r(t+12),17)
  self.assertEqual([p.get(k) for k in (0x104,0x132,0x14a,0x144)],[0,15,0,0]) # off, Diatonic
 def test_chord_on_plays_the_shape_on_every_pad_pitch_and_off_stops(self):
  p=self.page();p.edit(0x132,0);p.edit(0x104,1)
  active,off,vel=p.mail();self.assertEqual(active,1);self.assertEqual(off,[[0,4,7]]*12);self.assertEqual(vel,127)
  p.edit(0x132,7);self.assertEqual(p.mail()[1],[[0,3,7,10]]*12) # Min7
  p.edit(0x144,1);self.assertEqual(p.mail()[1][0],[3,7,10,12]) # first inversion
  p.edit(0x132,0);p.edit(0x144,3);self.assertEqual(p.mail()[1][0],[7,12,16]) # triad: second inversion is the highest
  p.edit(0x144,0);p.edit(0x14a,2);self.assertEqual(p.mail()[1][0],[0,7,16]) # triad Drop 2 -> Open
  p.edit(0x104,0);self.assertEqual(p.mail()[0],0)
 def test_diatonic_follows_the_key(self):
  p=self.page();p.edit(0x104,1);off=p.mail()[1] # C major (fixture default)
  self.assertEqual([off[pc] for pc in (0,2,4,5,7,9,11)],[[0,4,7],[0,3,7],[0,3,7],[0,4,7],[0,4,7],[0,3,7],[0,3,6]])
 def test_only_pitched_tracks_and_per_track(self):
  p=self.page();p.ttype=14;p.edit(0x104,1);self.assertIn(p.mail(),[None]) if p.mail() is None else self.assertEqual(p.mail()[0],0)
  p.ttype=18;p.button(0xfe,3);self.assertEqual(p.mail()[0],1)
  p.track=0x92;p.button(0xfe,3);self.assertEqual(p.mail()[0],0);self.assertEqual(p.get(0x104),0) # other track: its own setting (off)
  p.track=0x91;p.button(0xfe,3);self.assertEqual(p.mail()[0],1)
 def test_republishes_when_someone_else_changed_the_mail(self):
  p=self.page();p.edit(0x104,1);p.call(UU['chord_audition_publish'],0,0,0,0);self.assertEqual(p.mail()[0],0)
  p.button(0xfe,3);self.assertEqual(p.mail()[0],1)
 def test_saved_with_the_track(self):
  p=self.page();p.edit(0x104,1);p.edit(0x132,8);p.edit(0x14a,2);p.edit(0x144,3);obj=0x20031200;p.w(obj+0x10,0x91);p.u.mem_write(obj+4,b'\x12')
  p.call(UU['fx_save'],obj,0x20017000);self.assertEqual(p.attrs['bento_perf_chord'],1<<24|3<<16|2<<12|8<<4|1)
  p.edit(0x104,0);p.call(UU['fx_load'],0x20017100,obj);self.assertEqual([p.get(k) for k in (0x104,0x132,0x14a,0x144)],[1,8,2,3])
  del p.attrs['bento_perf_chord'];p.call(UU['fx_load'],0x20017100,obj);self.assertEqual([p.get(k) for k in (0x104,0x132,0x14a,0x144)],[0,15,0,0])
class RealPage(unittest.TestCase):
 """1.6P5 reset on PROJ+PLAY (owner, 24 Oct): with the page open, every
 property read went through perf_get, which asked for the current track, whose
 own read (project property 131) came back to perf_get: endless recursion.
 This runs the real native GenericProperties page (constructor 08145B7C,
 handle/header 08145EFC) with the real getter path; only navigation is a
 fixture."""
 def test_open_page_builds_without_recursion(self):
  p=Fixture();KEEP.append(p);p.registry();p.w(0x3000004c,p.next);p.w(0x30000048,0xc0200000)
  navs=[];depth=[0,0]
  def nav(u,a,n,d):navs.append(u.reg_read(UC_ARM_REG_R1));p.ret()
  def get(u,a,n,d):depth[0]+=1;depth[1]=max(depth[1],0x2003e000-u.reg_read(UC_ARM_REG_SP))
  p.u.hook_add(UC_HOOK_CODE,nav,begin=0x081420ec,end=0x081420ec)
  p.u.hook_add(UC_HOOK_CODE,get,begin=0x08133614,end=0x08133614)
  # The fixture model has no property tree: the native getter body (after our
  # adapter at 08133614) answers 0. Our hook chain and 08133CFC stay real.
  def body(u,a,n,d):
   # Entered after the adapter replayed "push {r4-r7,lr}; sub sp,#12": undo it.
   sp=u.reg_read(UC_ARM_REG_SP);p.w(u.reg_read(UC_ARM_REG_R3),0);u.reg_write(UC_ARM_REG_SP,sp+32);u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,p.r(sp+28))
  p.u.hook_add(UC_HOOK_CODE,body,begin=0x08133618,end=0x08133618)
  def track(u,a,n,d):
   # 08133CFC after its own property-131 read (the recursion path): answer
   # track 0x91 instead of walking the absent project tree; pop its frame.
   sp=u.reg_read(UC_ARM_REG_SP);p.w(u.reg_read(UC_ARM_REG_R9),0x91)
   for i,r in enumerate((UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9)):u.reg_write(r,p.r(sp+12+4*i))
   u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_SP,sp+40);u.reg_write(UC_ARM_REG_PC,p.r(sp+36))
  p.u.hook_add(UC_HOOK_CODE,track,begin=0x08133d26,end=0x08133d26)
  def settings(u,a,n,d):p.w(u.reg_read(UC_ARM_REG_R1),0x55);p.ret(1)
  p.u.hook_add(UC_HOOK_CODE,settings,begin=0x08133e54,end=0x08133e54)
  p.w(LOCK+8,1);self.assertEqual(p.call(UU['fx_dispatch'],M,0xaf,0,15),1);p.w(LOCK+8,0);self.assertEqual(navs,[0x1a])
  v=0xc0000000;p.call(0x08145b7c,v);arg=0x20016000;p.w(arg,42)
  p.call(0x08145efc,v,arg) # raised (stack overflow) before the fix
  self.assertLess(depth[1],0x1000);self.assertGreater(depth[0],0)
  out=0x20016100;p.w(out,7);p.call(UU['fx_get'],M,arg,0,out);self.assertEqual(p.r(out),0) # empty slot
  p.call(UU['fx_dispatch'],M,0xfe,0,3) # per-message tick with the page open
class P7(unittest.TestCase):
 """P7 owner report on 1.6P6."""
 def page(self):p=Chord().page();return p
 def press(self,p,pad,pitch):
  # A pad press (UI message AC) and the pitch the audio core publishes for it.
  bank=p.r(EC+4);pub=bank+44576+128;p.button(0xac,pad)
  p.u.mem_write(pub+4+pad,bytes([0x80|pitch]));p.w(pub,p.r(pub)+2);p.w(0x3001fe2c,p.r(0x3001fe2c)+10);p.button(0xfe,3)
 def test_tap_field_flips_and_sets_the_project_bpm(self):
  p=self.page();vals=[]
  for t in [1000,1500,2000,2500]:p.w(0x3001fe2c,t);p.edit(0x101,1);vals.append(p.get(0x101))
  self.assertEqual(vals,[1,0,1,0]);self.assertEqual(p.proj[0x8c],120);self.assertEqual(p.get(0x8c),120)
 def test_played_chord_name_in_the_row_title(self):
  p=self.page();p.edit(0x132,7);p.edit(0x104,1) # Min7
  self.press(p,3,50);p.header();self.assertEqual(p.text(p.r(OUT+12)),'Chord / Dm7')
  p.edit(0x132,0);p.edit(0x144,1);self.press(p,4,52);p.header();self.assertEqual(p.text(p.r(OUT+12)),'Chord / E/G#')
  p.edit(0x132,15);p.edit(0x144,0);self.press(p,5,50);p.header();self.assertEqual(p.text(p.r(OUT+12)),'Chord / Dm') # Diatonic in C major
 def test_smooth_voicing_follows_the_last_chord(self):
  p=self.page();p.edit(0x132,0);p.edit(0x14a,3);p.edit(0x104,1) # Major, Smooth
  self.assertEqual(p.text(p.r(p.r(0x30031484)+0x14a*32+8+0) and p.r(p.r(p.r(0x30031484)+0x14a*32+8)+12)),'Smooth')
  self.assertEqual(p.mail()[1][0],[0,4,7]) # nothing played yet: close
  self.press(p,0,48) # C major 48 52 55
  off=p.mail()[1]
  self.assertEqual(off[5],[-5,0,4]) # F major after C-E-G: C-F-A (F pad near the chord)
  self.assertEqual(off[7],[-8,-5,0]) # G major after C-E-G: B-D-G, the textbook voice leading
 def test_version_tells_seq_chord_mode_about_changes(self):
  p=self.page();out=0x20036300
  self.assertEqual(p.call(UU['perf_chord_shared'],0x91,out,out+4,out+8),0) # never set
  p.edit(0x132,7);v1=p.call(UU['perf_chord_shared'],0x91,out,out+4,out+8);self.assertGreater(v1,0)
  p.edit(0x14a,3);v2=p.call(UU['perf_chord_shared'],0x91,out,out+4,out+8);self.assertGreater(v2,v1)
  self.assertEqual([p.r(out),p.r(out+4)],[7,0]) # Smooth reads as Close in SEQ
  p.call(UU['perf_chord_share'],0x91,8,0,1);self.assertEqual(p.call(UU['perf_chord_shared'],0x91,out,out+4,out+8),v2) # SEQ edits keep the version
  self.assertEqual([p.get(k) for k in (0x132,0x14a,0x144)],[8,3,1]) # and keep Smooth
class Shared(unittest.TestCase):
 """P5/P7: the chord shared with SEQ chord mode (the header symbol is gone)."""
 def test_shared_chord_store(self):
  p=Chord().page();out=0x20036300
  self.assertEqual(p.call(UU['perf_chord_shared'],0x92,out,out+4,out+8),0)
  p.call(UU['perf_chord_share'],0x91,9,2,3);self.assertEqual([p.get(k) for k in (0x132,0x14a,0x144)],[9,2,3])
  p.call(UU['perf_chord_share'],0x91,40,0,0);self.assertEqual(p.get(0x132),9) # invalid ignored
class Pads(Fixture):
 """M7: the patched pad-module call site, then the real native press."""
 def __init__(self):
  super().__init__();KEEP.append(self);self.posts=[];self.mod=0x20030000;self.rec=0x20032000
  self.u.mem_write(self.mod,bytes(0x600));self.u.mem_write(self.mod+0x490,b'\x03')
  self.w(self.mod+0x2cc,0x55);self.w(self.mod+0x2ec,0x55);self.w(self.mod+0xc4,1000)
  self.w(self.mod+0x424,0x20031000);self.w(0x20031010,12);self.u.mem_write(self.mod+0x428,struct.pack('<hh',3,4))
  self.u.hook_add(UC_HOOK_CODE,self.post,begin=0x0809eca0,end=0x0809eca0)
 def post(self,u,a,n,d):
  t,_,h,pitch,v,_=struct.unpack('<6I',u.mem_read(u.reg_read(UC_ARM_REG_R1),24));self.posts.append((t&255,v));self.ret()
 def press(self,pressure):
  self.u.mem_write(self.rec,struct.pack('<6I',0xac,0,0xfffffffe,8,pressure,0));self.posts=[]
  self.u.reg_write(UC_ARM_REG_R0,self.mod);self.u.reg_write(UC_ARM_REG_R1,self.rec);self.u.reg_write(UC_ARM_REG_R2,0x20033000);self.u.reg_write(UC_ARM_REG_R5,self.mod)
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000);self.u.emu_start(0x080857d6|1,0x080857da,count=2000000)
  return [v for t,v in self.posts if t==2]
class Audio(unittest.TestCase):
 def test_off_keeps_pressure(self):
  p=Pads();self.assertEqual(p.press(0x8000),[78]);self.assertEqual(p.press(0x2000),[19])
  p.w(EC+20,0x12345600|90);self.assertEqual(p.press(0x8000),[78]) # wrong tag
 def test_every_fixed_velocity_is_exact(self):
  p=Pads()
  for v in [1,2,50,64,78,100,126,127]:
   p.w(EC+20,0x56454c00|v)
   for pr in [0x100,0x8000,0xffff,0x30000]:self.assertEqual(p.press(pr),[v],(v,pr))
 def play_scan(self,proj_down):
  # P7: the audio core's button scan (loop at 0808D2C0) for button 15 = PLAY,
  # pressed now (new 1, old 0). Button states: new at base+i, old at base+0x10+i.
  p=Fixture();KEEP.append(p);base=0x20034000;p.u.mem_write(base,bytes(0x40))
  p.u.mem_write(base+15,b'\x01');p.u.mem_write(base+7,bytes([proj_down]));p.u.mem_write(base+0x17,bytes([proj_down]))
  fp=0x20035000;p.u.mem_write(fp,bytes(0x900));sb=0x20036000;p.w(sb,0x20037000)
  posts=[]
  def ret(u,a,n,d):p.ret()
  def transport(u,a,n,d):posts.append(u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]);p.ret()
  for a in (0x080a04a0,0x08082220):p.u.hook_add(UC_HOOK_CODE,ret,begin=a,end=a)
  p.u.hook_add(UC_HOOK_CODE,transport,begin=0x08058600,end=0x08058600)
  for r,v in [(UC_ARM_REG_R6,15),(UC_ARM_REG_R8,base+14),(UC_ARM_REG_R9,sb),(UC_ARM_REG_R11,fp),(UC_ARM_REG_SP,0x2003d000)]:p.u.reg_write(r,v)
  p.u.emu_start(0x0808d2c0|1,0x0808d2e2,count=2000)
  return posts,p.u.reg_read(UC_ARM_REG_PC)
 def test_play_starts_transport_unless_proj_is_held(self):
  posts,pc=self.play_scan(0);self.assertEqual(posts,[0x8f]) # native: transport play
  posts,pc=self.play_scan(1);self.assertEqual(posts,[]);self.assertEqual(pc,0x0808d2e2) # PROJ held: no playback, scan ends as native
 def test_call_site_is_patched(self):
  self.assertIn('perf_press',AA)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
