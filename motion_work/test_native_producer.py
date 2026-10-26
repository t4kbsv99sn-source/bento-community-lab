"""M4 producer ARM execution; model lookup, Undo dispatch and XML DOM are fixtures.
Native type-5 allocator and clone are exercised separately by test_native_node.
"""
import json,struct,unittest,os
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_native_node import Probe as Base,OUT,PREFIX,IMAGE
from native_node_patches import patches
from build_motion_candidate import elf
C=Path(os.environ.get('MOTION_CANDIDATE','motion_checks/candidate_r3'));CHUNKS,S=elf(C/'motion_ui.elf')
class Probe(Base):
 def __init__(self):
  super().__init__()
  for a,old,new,_ in patches(IMAGE):self.u.mem_write(a,old) # P22b ships stock node sizes
  self.node=self.create();self.attrs={};self.handles={};self.nextattr=0x30038000;self.string=0xc01d0000;self.undo=0;self.routes={};self.base_values={}
  for a,b in CHUNKS:self.u.mem_write(a,b)
  self.w(0x3000004c,0xc0100000);self.w(0x30000048,0xc01c0000)
  self.keep=[self.u.hook_add(UC_HOOK_CODE,self.hook,begin=a,end=a) for a in [0x0812ea72,0x081338dc,0x0813130c,0x08133d84,0x08109cdc,0x08109c64,0x08109582,0x08109268,0x081094c2,0x0810958e,0x08109566,0x08131244,0x08131238,0x081403ec,0x0813391a,0x08133f7c,0x08133614]]
 def text(self,p):
  b=bytearray()
  while self.u.mem_read(p,1)!=b'\0':b.extend(self.u.mem_read(p,1));p+=1
  return b.decode()
 def ret(self,n=0):self.u.reg_write(UC_ARM_REG_R0,n);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def hook(self,u,a,n,d):
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x0812ea72:self.w(r[2],self.node);self.ret(1)
  elif a==0x081338dc:self.undo+=1;self.ret()
  elif a==0x0813130c:self.ret()
  elif a==0x08133d84:self.w(r[2],100);self.w(r[3],0);self.ret(1)
  elif a==0x0810958e:self.attrs[self.handles[r[0]]]=r[1];self.ret()
  elif a==0x08109566:
   value=self.attrs[self.handles[r[0]]]
   if isinstance(value,int):self.w(r[1],value);self.ret(0)
   else:self.ret(2)
  elif a==0x08131244:
   route=self.routes.get((self.r(r[1]),r[2],r[3]));out=self.r(u.reg_read(UC_ARM_REG_SP))
   if route:self.u.mem_write(out,struct.pack('<3I',route[1],route[0],r[3]));self.ret(1)
   else:self.ret(0)
  elif a==0x08131238:
   routes=[(k,v) for k,v in self.routes.items() if k[0]==self.r(r[1])]
   if r[2]<len(routes):
    k,v=routes[r[2]];self.u.mem_write(r[3],struct.pack('<3I',v[1],v[0]|k[1]<<16,k[2]));self.ret(1)
   else:self.ret(0)
  elif a==0x081403ec:
   e=struct.unpack('<5I',u.mem_read(r[1],20))
   if e[0]==0xd1:self.routes[(e[1],e[2]&65535,e[3]>>16)]=(e[3]&65535,e[4])
   self.ret()
  elif a==0x0813391a:
   children=[66,67] if self.r(r[1])==100 else []
   if r[2]<len(children):self.w(r[3],children[r[2]]);self.ret(1)
   else:self.ret(0)
  elif a==0x08133f7c:self.ret(1)
  elif a==0x08133614:
   key=(self.r(r[1]),r[2])
   if key in self.base_values:self.w(r[3],self.base_values[key]);self.ret(1)
   else:self.w(r[3],16 if r[2]==0x62 else 0);self.ret(1)
  elif a==0x08109cdc or a==0x08109c64:
   key=self.text(r[1]);h=self.nextattr;self.nextattr+=4;self.handles[h]=key;self.ret(h if a==0x08109cdc or key in self.attrs else 0)
  elif a==0x08109582:self.attrs[self.handles[r[0]]]=self.text(r[1]);self.ret()
  elif a==0x08109268:self.ret(0x30037000)
  elif a==0x081094c2:
   b=str(self.attrs[self.handles[r[0]]]).encode()+b'\0';p=self.string;self.string+=len(b);self.u.mem_write(p,b);self.ret(p)
 def api(self,n,*args):return self.call(S[n],*args)
 def state(self):return self.api('motion_ui_state',1)
 def device(self):return self.r(self.state()+4)
 def clock(self,t):
  d=self.device();p=d+544;self.u.mem_write(p,struct.pack('<4I2Q8I',2,0xc0080000,100,0,t,0,1,0,1,0,0,0,0,0))
 def begin(self):self.clock(0);return self.api('motion_ui_begin',55,100,0)
class Tests(unittest.TestCase):
 def test_recording_publishes_a_complete_clip_and_release_ends_all_lanes(self):
  p=Probe();self.assertEqual(p.begin(),1);self.assertEqual(p.undo,1)
  p.clock(240);self.assertEqual(p.api('motion_ui_capture',0,250),1)
  p.clock(3840*3);self.assertEqual(p.api('motion_ui_capture',1,750),1)
  p.api('motion_ui_end');d=p.device();self.assertEqual(p.r(d+12),1);c=p.r(d+32)
  self.assertEqual(p.r(c+4),100);self.assertEqual(p.r(c)&1,0)
  for i in (0,1):
   lane=c+32+i*1048;self.assertEqual(struct.unpack('<H',p.u.mem_read(lane+1042,2))[0],16)
   self.assertEqual(p.u.mem_read(lane+1044,1),b'\1')
  self.assertEqual(p.api('motion_ui_capture',0,500),0)
 def test_native_clear_companion_removes_published_motion(self):
  p=Probe();p.begin();p.api('motion_ui_capture',0,200);p.api('motion_ui_end')
  handle=0x30036000;p.w(handle,55);p.api('motion_ui_after_clear',0x30024b00,handle,0)
  c=p.r(p.device()+32);self.assertEqual(p.u.mem_read(c+32+1044,1),b'\0')
 def parameter(self,p,value,key=3):
  registry=0xc0190000;p.w(0x30031484,registry);p.w(registry+key*32+16,(-1000)&0xffffffff);p.w(registry+key*32+20,1000)
  e=0x30035000;p.u.mem_write(e,struct.pack('<5I',0xcf,66,key,value&0xffffffff,0));return p.api('motion_controls_model_event',0x30024b00,e)
 def test_unassigned_parameter_uses_next_free_lane_and_preserves_base(self):
  p=Probe();p.routes[(67,3,0)]=(9,1000);p.base_values[(66,3)]=0;p.begin();p.clock(240)
  self.assertEqual(self.parameter(p,500),1);self.assertEqual(p.routes[(66,3,0)],(10,1000));self.assertEqual(p.base_values[(66,3)],0)
  c=p.r(p.device()+32);self.assertEqual(p.u.mem_read(c+32+1048+1044,1),b'\1')
 def test_existing_shallow_route_is_retained_with_clip_owned_source_gain(self):
  p=Probe();p.routes[(66,3,0)]=(9,82);p.base_values[(66,3)]=0;p.begin();p.clock(240)
  self.assertEqual(self.parameter(p,500),1);self.assertEqual(p.routes[(66,3,0)],(9,82))
  c=p.r(p.device()+32);l=c+32;gain=struct.unpack('<H',p.u.mem_read(l+1046,2))[0];self.assertGreater(gain,1)
  count=struct.unpack('<H',p.u.mem_read(l+1040,2))[0];word=p.r(l+(count-1)*4);value=(word>>20)&1023
  replay=(value*2-1000)*gain*82/1000;self.assertLess(abs(replay-500),2)
 def test_full_lanes_do_not_overwrite_routes(self):
  p=Probe();p.routes={(67,3,i):(9+i,1000) for i in range(3)};p.routes[(67,4,0)]=(12,1000);p.base_values[(66,3)]=0;p.begin();before=dict(p.routes)
  self.assertEqual(self.parameter(p,500),0);self.assertEqual(p.routes,before)
 def test_real_module_xml_fields_round_trip_and_reject_corruption(self):
  p=Probe();p.begin();p.api('motion_ui_capture',2,311);p.api('motion_ui_end')
  # P22b: motion lives in the side store keyed by the clip handle (object +10).
  p.w(0xc0002000+0x10,55);p.api('motion_ui_save',0xc0002000,0x30037000);self.assertEqual(len(p.attrs),5)
  before=dict(p.attrs);x=p.api('motion_store',55,0);self.assertNotEqual(x,0);p.u.mem_write(x,bytes(8408))
  p.api('motion_ui_load',0x30037000,0xc0001000,0xc0002000)
  p.api('motion_ui_save',0xc0002000,0x30037000);self.assertEqual(p.attrs,before)
  p.u.mem_write(x,bytes(8408));p.attrs={k:'garbage' for k in p.attrs}
  p.api('motion_ui_load',0x30037000,0xc0001000,0xc0002000);self.assertEqual(p.r(x),0)
  self.assertEqual(p.r(p.node+PREFIX),0) # the native node is never written
 def test_project_transition_reuses_directory_slots_without_touching_audio_cache(self):
  p=Probe();p.begin();p.api('motion_ui_capture',0,200);p.api('motion_ui_end');d=p.device();c=p.r(d+32)
  p.u.mem_write(d+544+64,b'\xa5'*32);p.api('motion_ui_project_end')
  self.assertEqual(p.u.mem_read(d+544+64,32),b'\xa5'*32)
  p.api('motion_ui_publish',55,101,0);self.assertEqual(p.r(d+12),1);self.assertEqual(p.r(d+32),c);self.assertEqual(p.r(c+4),101) # P22b: a clip with motion
 def test_native_clone_carries_motion_and_dead_entries_are_reclaimed(self):
  p=Probe();p.begin();x=p.api('motion_store',55,1);self.assertNotEqual(x,0);pattern=bytes((i*7)&255 for i in range(8408));p.u.mem_write(x,pattern)
  p.w(0xc0002000+0x10,55);p.w(0xc0003000+0x10,77);p.w(0xc0004000,0xc0003000)
  p.api('motion_store_clone',0x30030000,0xc0002000,0xc0004000,1);y=p.api('motion_store',77,0)
  self.assertNotEqual(y,0);self.assertNotEqual(y,x);self.assertEqual(bytes(p.u.mem_read(y,8400)),pattern[:8400])
  p.w(0xc0003000+0x10,78);p.api('motion_store_clone',0x30030000,0xc0002000,0xc0004000,0);self.assertEqual(p.api('motion_store',78,0),0)
  # source without motion: nothing is created for the clone (Undo of a first recording)
  p.w(0xc0002000+0x10,56);p.w(0xc0003000+0x10,79);p.api('motion_store_clone',0x30030000,0xc0002000,0xc0004000,1);self.assertEqual(p.api('motion_store',79,0),0)
  # fill the store; when full, clips no longer present in their native tree are reused
  dead=p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:p.ret(0),begin=0x0812d78a,end=0x0812d78a)
  made=set()
  for k in range(1000,1100):
   v=p.api('motion_store',k,1)
   if not v:break
   made.add(v)
  self.assertEqual(k,1099);self.assertLessEqual(len(made),64)
 def test_clone_wrapper_passes_native_arguments_and_result(self):
  p=Probe();x=p.api('motion_store',55,1);p.u.mem_write(x,b'\x11'*8400)
  full=(C/'bento1.bin').read_bytes()  # shipped image: clone site and M4 wrapper area
  for a,n in ((0x0812ea2a,4),(0x081dd800,0x2800)):p.u.mem_write(a,full[a-0x08040000:a-0x08040000+n])
  p.w(0xc0002000+0x10,55);p.w(0xc0003000+0x10,91);seen={}
  def native(u,a,n,d):
   sp=u.reg_read(UC_ARM_REG_SP);seen['args']=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]+[p.r(sp+0x18)]
   p.w(p.r(sp+0x18),0xc0003000);u.reg_write(UC_ARM_REG_R4,1);u.reg_write(UC_ARM_REG_PC,0x0812ea3c|1)
  p.u.hook_add(UC_HOOK_CODE,native,begin=0x0812ea2e,end=0x0812ea2e)
  p.w(0x2003e000,0x2003f000);self.assertEqual(p.call(0x0812ea2a,0x30030000,0x18,0x30031000,0xc0002000),1)
  self.assertEqual(seen['args'],[0x30030000,0x18,0x30031000,0xc0002000,0x2003f000])
  y=p.api('motion_store',91,0);self.assertNotEqual(y,0);self.assertEqual(bytes(p.u.mem_read(y,8400)),b'\x11'*8400)
 def test_readout_wrapper_passes_all_four_native_arguments(self):
  # P23: P22 boot-looped because the 08134800 wrapper clobbered r2/r3 (r2 is an
  # output pointer the native readout writes through) with the menu helper.
  from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
  p=Probe();full=(C/'bento1.bin').read_bytes();fx=(C/'fx/bento1.bin').read_bytes() if (C/'fx/bento1.bin').exists() else IMAGE
  for a,n in ((0x08134800,4),(0x081dd800,0x2800)):p.u.mem_write(a,full[a-0x08040000:a-0x08040000+n])
  cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);native=int(next(cs.disasm(fx[0x08134800-0x08040000:0x08134804-0x08040000],0x08134800)).op_str.lstrip('#'),16)
  seen={}
  def stub(u,a,n,d):seen['args']=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];u.reg_write(UC_ARM_REG_R0,7);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  p.u.hook_add(UC_HOOK_CODE,stub,begin=native,end=native)
  self.assertEqual(p.call(0x08134800,0x30024b00,0x30031000,0x2003d01b,0x5a5a1234),7)
  self.assertEqual(seen['args'],[0x30024b00,0x30031000,0x2003d01b,0x5a5a1234])
 def automation_view(self,p):
  # P24 fixture: native automation editor view (mode 2), lane A of clip 55.
  V=0xc1000000;p.u.mem_map(V,0x130000);u=p.state();p.w(u+8,V)
  p.u.mem_write(0x30024b00+0x12c,b'\x17');p.u.mem_write(V+0x125dac,b'\x02');p.w(V+0x11cd00,55);p.w(V+0x125d34,0)
  for slot,key in enumerate((0x1dd,0x1de,0,0,0,0,0x1db,0x1dc)):p.u.mem_write(V+0x11bcc0+slot*2,struct.pack('<H',key))
  return V,u
 def test_automation_view_keeps_clip_length_until_the_lane_holds_motion(self):
  p=Probe();V,u=self.automation_view(p);h=0x30030000;out=0x30030010;p.w(h,55)
  def get(key,caller):p.w(0x2003e000,caller);return p.api('motion_controls_get',0x30024b00,h,key,out)  # 5th argument on the stack
  self.assertEqual(get(0x62,0x08159a1b),0)
  self.assertEqual(get(0x60,0x08159a0d),0)
  self.assertEqual(p.begin(),1);p.clock(240);p.api('motion_ui_capture',0,250);p.clock(480);p.api('motion_ui_capture',0,300);p.api('motion_ui_end')
  self.assertEqual(get(0x62,0x08159a1b),1);self.assertEqual(p.r(out),256)
 def test_motion_encoders_use_free_slots_and_keep_native_lane_selection(self):
  p=Probe();V,u=self.automation_view(p);registry=0x30020000;p.w(0x30031484,registry)
  stub=lambda u_,a,n,d:p.ret()
  for a in (0x08170656,0x08171c1c,0x0817e85e):p.u.hook_add(UC_HOOK_CODE,stub,begin=a,end=a)
  p.api('motion_controls_after_header',V)
  keys=[struct.unpack('<H',p.u.mem_read(V+0x11bcc0+i*2,2))[0] for i in range(8)]
  self.assertEqual(keys,[0x1dd,0x1de,0x190,0x191,0x192,0x193,0x1db,0x1dc])
 def test_header_record_button_states(self):
  # P26 (owner: "red little button in the upper left corner").
  p=Probe();u=p.state();fills=[]
  def native(u_,a,n,d):p.ret()
  def fill(u_,a,n,d):
   r=[u_.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1)];fills.append(('fill' if a==0x08166ef6 else 'line',struct.unpack('<4i',p.u.mem_read(r[0],16)),r[1]));p.ret()
  p.u.hook_add(UC_HOOK_CODE,native,begin=0x0817f8f0,end=0x0817f8f0)
  for a in (0x08166ef6,0x08166e9e):p.u.hook_add(UC_HOOK_CODE,fill,begin=a,end=a)
  ctx=0x30031000;p.w(ctx,1);p.w(ctx+4,0x24078000)
  p.api('motion_header_draw',0x30034d48,ctx);self.assertEqual(fills,[])
  p.w(u+28,1);p.api('motion_header_draw',0x30034d48,ctx);self.assertIn(('line',(164,15,26,26),0xf4),fills)
  fills.clear();self.assertEqual(p.begin(),1);p.api('motion_header_draw',0x30034d48,ctx);self.assertEqual(fills,[('fill',(164,15,26,26),0xf4)])
  fills.clear();p.api('motion_ui_end');p.w(u+28,0);p.api('motion_header_draw',0x30034d48,ctx);self.assertEqual(fills,[('fill',(164,15,26,26),0)])
  fills.clear();p.api('motion_header_draw',0x30020000,ctx);self.assertEqual(fills,[]) # other widgets of the class
if __name__=='__main__':unittest.main(argv=[__file__,'-v'])
