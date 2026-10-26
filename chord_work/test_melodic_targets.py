"""P15 envelope phase hooks and native mixer tests for overlapping note sends."""
import unittest,struct,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_melodic_locks import Audio,Page,KEEP
from test_integration import AA,UU,DEFAULT,Fixture
class Sends(Audio):
 def __init__(self):
  super().__init__();self.synth=self.root;self.mixer();self.mixroot=self.root;self.root=self.synth;self.w(self.synth+0x284,0)
  self.src=self.buffers[0];self.strip=self.mixroot+0x18;self.n=16
  self.w(self.src+4,self.n);self.u.mem_write(self.src+16,b'\0\x01');self.call(0x08052ea0,self.src,0x2002b000,0x2002b004)
  for b in [self.src,self.out,self.buffers[17],self.buffers[18]]:self.w(b+4,self.n);self.call(0x08052c00,b)
  self.f(self.strip+0x30,1);self.f(self.strip+0x34,1);self.base_send(.25,.5)
 def base_send(self,delay,reverb):
  for off,value in [(0x50,delay),(0x80,reverb)]:
   self.call(0x0805bf80,self.strip+off,1);self.call(0x0805bf00,self.strip+off,fp=value);self.f(self.strip+off+0x10,value);self.f(self.strip+off+0x14,value)
 def begin(self,words):
  for v,w in zip([self.voice,self.other],words):self.note(w,v);self.u.mem_write(v,b'\x01')
  self.call(AA['mel_send_begin'],self.synth,self.ctx)
 def contribution(self,voice,left,right=None):
  dst=self.call(AA['mel_send_voice'],self.synth,voice,self.src)
  self.assert_isolated=dst!=self.src
  self.u.mem_write(self.r(dst+8),struct.pack('<%df'%self.n,*([left]*self.n)))
  self.u.mem_write(self.r(dst+12),struct.pack('<%df'%self.n,*([(right if right is not None else left)]*self.n)))
  self.u.mem_write(dst+16,b'\0\x01');self.call(AA['mel_send_voice_end'])
 def finish(self):
  self.call(AA['mel_send_end'],self.synth)
  self.call(0x080a04c0,self.mixroot,self.src,0,self.strip,self.out,self.ctx)
 def samples(self,b,side=0):return struct.unpack('<%df'%self.n,self.u.mem_read(self.r(b+8+side*4),self.n*4))
 def native_gain(self,v):return struct.unpack('<f',struct.pack('<I',self.call(0x080d33c0,v)))[0]
class Tests(unittest.TestCase):
 def test_four_new_targets_are_selectable_and_roundtrip(self):
  for index,kind,title in [(5,7,'Env 1 Decay'),(6,9,'Env 1 Release'),(7,10,'Delay Send'),(8,11,'Reverb Send')]:
   p=Page();p.shift(1);p.event(0x1da,index);p.shift(0);p.event({7:0x1f,9:0x21,10:0x36,11:0x37}[kind],650)
   self.assertEqual(p.call(UU['locks_slot'],p.word(),0),0x51000000|(kind<<16)|650);self.assertIn(title,p.title(6))
 def test_native_release_phase_uses_own_note_after_context_has_changed(self):
  p=Audio();p.note(0x510902ee);p.note(0x510900fa,p.other);p.context(p.other)
  for v,expected in [(p.voice,.75),(p.other,.25)]:
   p.u.mem_write(v+0x188,b'\x03');p.f(v+0x1ac,.8);p.call(0x08087a80,v+0x184)
   self.assertAlmostEqual(struct.unpack('<f',p.u.mem_read(v+0x27c,4))[0],expected,places=6)
  self.assertNotEqual(p.r(p.voice+0x198),p.r(p.other+0x198))
 def test_native_decay_phase_hook_and_unlocked_reuse(self):
  p=Audio();p.note(0x510701f4)
  # Run the actual transition through both BL sites and native time conversion.
  p.u.reg_write(UC_ARM_REG_R4,p.voice+0x184);p.u.reg_write(UC_ARM_REG_SP,0x2003e000)
  p.u.emu_start(0x08087735,0x08087746,count=10000)
  self.assertAlmostEqual(struct.unpack('<f',p.u.mem_read(p.voice+0x23c,4))[0],.5,places=6);self.assertGreater(p.r(p.voice+0x194),0)
  p.note(0);self.assertEqual(p.call(AA['mel_envelope'],p.voice+0x200,7),0)
 def test_matrix_modulation_remains_and_direct_automation_is_overridden(self):
  p=Audio();p.note(p.pack(0x510701f4,0x510902ee))
  for off,kind,expected in [(0x200,7,.7),(0x240,9,.95)]:
   q=p.voice+off
   for i in range(10):p.w(q+i*4,0)
   for pair,addr,value in [(0,0x2002b100,.1),(1,0x2002b110,.2),(4,0x2002b120,.3)]:
    p.w(q+pair*8,addr);p.f(q+pair*8+4,1);p.f(addr+4,value)
   p.call(AA['mel_envelope'],q,kind)
   self.assertAlmostEqual(struct.unpack('<f',p.u.mem_read(q+0x3c,4))[0],expected,places=5)
   self.assertEqual(p.r(q+32),0x2002b120) # source configuration itself is preserved
 def test_two_overlapping_notes_keep_independent_delay_and_reverb(self):
  p=Sends();p.begin([p.pack(0x510a03e8,0x510b0000),p.pack(0x510a0000,0x510b03e8)])
  p.contribution(p.voice,.2,.1);p.contribution(p.other,.3,.4);p.finish()
  self.assertAlmostEqual(p.samples(p.out)[0],.5,places=5);self.assertAlmostEqual(p.samples(p.out,1)[0],.5,places=5)
  self.assertAlmostEqual(p.samples(p.buffers[17])[0],.2*p.native_gain(1000),places=5)
  self.assertAlmostEqual(p.samples(p.buffers[17],1)[0],.1*p.native_gain(1000),places=5)
  self.assertAlmostEqual(p.samples(p.buffers[18])[0],.3*p.native_gain(1000),places=5)
  self.assertAlmostEqual(p.samples(p.buffers[18],1)[0],.4*p.native_gain(1000),places=5)
 def test_unlocked_note_follows_automated_send_while_locked_note_keeps_value(self):
  p=Sends();p.begin([0x510a03e8,0]);p.contribution(p.voice,.2);p.contribution(p.other,.3);p.base_send(.7,.8);p.finish()
  self.assertAlmostEqual(p.samples(p.buffers[17])[0],.2*p.native_gain(1000)+.3*.7,places=5)
  self.assertAlmostEqual(p.samples(p.buffers[18])[0],.5*.8,places=5)
  self.assertAlmostEqual(struct.unpack('<f',p.u.mem_read(p.strip+0x64,4))[0],.7,places=6)
 def test_track_fader_pan_mute_and_existing_bus_tails(self):
  p=Sends();p.begin([0x510a03e8,0]);p.contribution(p.voice,.2);p.contribution(p.other,.3)
  p.f(p.strip+0x30,.5);p.f(p.strip+0x34,.5);p.f(p.strip,.5)
  bus=p.buffers[17];p.call(0x08052ea0,bus,0x2002b000,0x2002b004);p.u.mem_write(bus+16,b'\0\x01')
  for side in [0,1]:p.u.mem_write(p.r(bus+8+side*4),struct.pack('<16f',*([.9]*16)))
  p.finish();wet=(.2*p.native_gain(1000)+.3*.25)*.5
  self.assertAlmostEqual(p.samples(bus)[0],.9+wet*.5,places=5);self.assertAlmostEqual(p.samples(bus,1)[0],.9+wet,places=5)
  q=Sends();q.begin([0x510a03e8,0]);q.contribution(q.voice,.2);q.contribution(q.other,.3);q.call(0x0805bf80,q.strip+0x20,0);q.f(q.strip+0x30,0);q.u.mem_write(q.strip+0x2c,b"\x01");q.finish()
  self.assertAlmostEqual(q.samples(q.buffers[17])[0],0,places=5)
 def test_unlocked_reuse_returns_to_native_send_routing(self):
  p=Sends();p.begin([0x510a03e8,0]);p.contribution(p.voice,.2);p.contribution(p.other,.3);p.finish()
  for v in [p.voice,p.other]:p.note(0,v)
  p.call(AA['mel_send_begin'],p.synth,p.ctx);self.assertEqual(p.call(AA['mel_send_voice'],p.synth,p.voice,p.src),p.src)
 def test_send_locks_tap_before_shared_track_effects(self):
  p=Sends();p.n=128
  for b in [p.src,p.out,p.buffers[17],p.buffers[18]]:p.w(b+4,p.n)
  settings=DEFAULT.copy();settings[16]=1;settings[17]=-12;p.mailbox({0:settings})
  for _ in range(60):
   for b in [p.src,p.out,p.buffers[17],p.buffers[18]]:p.call(0x08052c00,b)
   p.begin([0x510a03e8,0]);p.contribution(p.voice,.8);p.contribution(p.other,0);p.finish()
  self.assertLess(max(p.samples(p.out)),.4)
  self.assertAlmostEqual(p.samples(p.buffers[17])[0],.8*p.native_gain(1000),places=5)
 def test_gain_ramps_match_native_gain_for_unlocked_contribution(self):
  p=Sends();p.begin([0x510a0000,0]);p.contribution(p.voice,.2);p.contribution(p.other,.3)
  p.f(p.strip+0x64,.8);p.finish();actual=p.samples(p.buffers[17])
  q=Fixture();KEEP.append(q);q.mixer();src=q.buffers[0];bus=q.buffers[17];q.w(src+4,16);q.w(bus+4,16);q.u.mem_write(src+16,b"\0\0");q.u.mem_write(q.r(src+8),struct.pack('<16f',*([.3]*16)))
  g=q.root+0x18+0x50;q.call(0x0805bf80,g,1);q.f(g+0x10,.25);q.f(g+0x14,.8);q.u.mem_write(g+0xc,b"\0");q.call(0x0805bc40,g,src,bus)
  expected=struct.unpack('<16f',q.u.mem_read(q.r(bus+8),64))
  for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=6)
 def test_multiple_blocks_do_not_accumulate_old_note_send_audio(self):
  p=Sends()
  for amount in [.2,.4,0.]:
   for b in [p.src,p.out,p.buffers[17],p.buffers[18]]:p.call(0x08052c00,b)
   p.begin([0x510a03e8,0]);p.contribution(p.voice,amount);p.contribution(p.other,0);p.finish()
   for sample in p.samples(p.buffers[17]):self.assertAlmostEqual(sample,amount*p.native_gain(1000),places=5)
 def test_installed_context_adapter_substitutes_output_and_restores_dry(self):
  p=Sends();p.begin([0x510a03e8,0]);p.call(AA['mel_context'],p.synth,p.voice)
  def render(u,a,n,d):
   sp=u.reg_read(UC_ARM_REG_SP);out=p.r(sp+12);self.assertNotEqual(out,p.src)
   p.u.mem_write(p.r(out+8),struct.pack('<16f',*([.2]*16)));p.u.mem_write(p.r(out+12),struct.pack('<16f',*([.3]*16)));p.u.mem_write(out+16,b'\0\x01');p.ret()
  h=p.u.hook_add(UC_HOOK_CODE,render,begin=0x0807b000,end=0x0807b000)
  p.u.reg_write(UC_ARM_REG_R0,p.synth);p.u.reg_write(UC_ARM_REG_R1,p.voice);p.u.reg_write(UC_ARM_REG_SP,0x2003e000);p.w(0x2003e00c,p.src)
  p.u.emu_start(0x0807a80f,0x0807a7e0,count=100000);p.u.hook_del(h)
  self.assertAlmostEqual(p.samples(p.src)[0],.2,places=6);self.assertAlmostEqual(p.samples(p.src,1)[0],.3,places=6)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
