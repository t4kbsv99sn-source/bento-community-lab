"""K1 carrier recognition, real DaisySP samples and native entry ABI.
Native sample virtual I/O and final mixer are controlled fixtures, not hardware.
"""
import unittest,struct,math
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_editable_locks import VoiceProbe
from test_controls import REGS
from kick_build import SYMS

FRAMES=144019;SIGNATURE=0xb1e70a5c
class Kick(VoiceProbe):
 def __init__(self,marker=True):
  super().__init__();self.marker=marker;self.real_post=False;self.post=[];self.reads=0;self.ready=True;self.reader_gain=1.0
  self.desc=0x2001a000;self.provider=0x2001b000;vt=0x2001b100
  self.w(self.voice+12,self.desc);self.w(self.desc,self.provider);self.w(self.desc+4,7);self.w(self.desc+0x24,FRAMES)
  self.w(self.provider,vt);self.w(vt+0x1c,0x081be011);self.w(vt+8,0x081be021)
  self.w(self.root+0x60,1);self.w(self.root+0x20,self.voice);self.u.mem_write(self.voice,b'\1')
  self.f(self.voice+0x48,1);self.f(self.voice+0xb8,1)
  self.temp=0x20024000;self.output=0x20025000;self.samples=0x20026000
  self.w(self.temp,128);self.w(self.temp+8,self.samples);self.w(self.temp+12,self.samples+0x1000);self.w(self.output,64);self.w(self.output+4,64)
  self.u.hook_add(UC_HOOK_CODE,self.extra)
 def ret(self,n=0):self.u.reg_write(UC_ARM_REG_R0,n);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def extra(self,u,a,s,d):
  r=[u.reg_read(x) for x in REGS[:4]];sp=u.reg_read(UC_ARM_REG_SP)
  if a==0x081be010:self.ret(48000)
  elif a==0x081be020:
   dest=struct.unpack('<I',u.mem_read(sp+4,4))[0];n=struct.unpack('<I',u.mem_read(sp+12,4))[0];self.reads+=1
   values=[(1 if SIGNATURE&(1<<i) else -1)/32768*self.reader_gain if self.marker and self.ready else 0 for i in range(n)]
   u.mem_write(dest,struct.pack('<%df'%n,*values));self.ret(n)
  elif a==0x08092d00:
   self.post.append(tuple(r))
   if not self.real_post:self.ret()
 def native_postprocess(self):
  def clock(u,a,s,d):
   if a==0x08064ac0:u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  self.u.hook_add(UC_HOOK_CODE,clock)
  self.call(0x080638c0,self.root+0x3c8);self.call(0x08072a00,self.voice);self.call(0x08092f20,self.root,self.voice)
  self.w(self.voice+12,self.desc);self.f(self.voice+0x48,1);self.f(self.voice+0xb8,1);self.u.mem_write(self.voice,b'\1')
  self.w(self.output+8,0x20028000);self.w(self.output+12,0x20029000)
  self.call(0x080639a0,self.voice+0x58);self.real_post=True
 def outputs(self):
  left=struct.unpack('<64f',self.u.mem_read(0x20028000,256))
  right=struct.unpack('<64f',self.u.mem_read(0x20029000,256)) if self.u.mem_read(self.output+0x11,1)!=b'\0' else left
  return [left,right]
 def start(self):self.call(SYMS['kick_voice'],self.voice,self.root)
 def render(self):
  if self.real_post:
   for a in [0x20028000,0x20029000]:self.u.mem_write(a,bytes(256))
  self.call(SYMS['kick_render'],self.root,self.voice,self.temp,self.output)
  result=self.u.reg_read(UC_ARM_REG_R0)
  return result,struct.unpack('<64f',self.u.mem_read(self.samples,256))

class Tests(unittest.TestCase):
 def test_native_second_external_ram_region_accepts_descriptor_provider_and_audio(self):
  p=Kick();p.u.mem_map(0xc4000000,0x10000)
  desc,provider,samples=0xc4001000,0xc4002000,0xc4003000
  p.u.mem_write(desc,bytes(p.u.mem_read(p.desc,0x2c)));p.u.mem_write(provider,bytes(p.u.mem_read(p.provider,4)))
  p.w(desc,provider);p.desc=desc;p.provider=provider;p.samples=samples;p.w(p.voice+12,desc)
  p.w(p.temp+8,samples);p.w(p.temp+12,samples+0x1000)
  p.start();ok,audio=p.render();self.assertEqual(ok,1);self.assertGreater(max(abs(x) for x in audio),.001)
 def test_address_past_native_external_ram_regions_is_rejected(self):
  p=Kick();p.call(SYMS['kick_marker'],0xc6000000);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_marker_requires_exact_length_rate_mono_and_signature(self):
  p=Kick();p.call(SYMS['kick_marker'],p.desc);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),1)
  p=Kick();p.reader_gain=32768;p.call(SYMS['kick_marker'],p.desc);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),1)
  for mutate in ['length','stereo','signature']:
   p=Kick()
   if mutate=='length':p.w(p.desc+0x24,FRAMES-1)
   elif mutate=='stereo':p.u.mem_write(p.desc+0x28,b'\1')
   else:p.marker=False
   p.call(SYMS['kick_marker'],p.desc);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),0)
 def test_real_daisy_engine_generates_finite_nonzero_audio_and_uses_native_postprocess(self):
  p=Kick();p.start();samples=[]
  for _ in range(16):
   ok,out=p.render();self.assertEqual(ok,1);samples.extend(out)
  self.assertGreater(max(abs(x) for x in samples),.01);self.assertLess(max(abs(x) for x in samples),1)
  self.assertTrue(all(math.isfinite(x) for x in samples));self.assertEqual(p.post[-1],(p.root,p.voice,p.temp,p.output))
  self.assertEqual(struct.unpack('<I',p.u.mem_read(p.voice+0x40,4))[0],1024)
 def test_ordinary_sample_falls_back_without_changing_audio_or_voice(self):
  p=Kick(False);p.u.mem_write(p.samples,b'\x5a'*256);before=bytes(p.u.mem_read(p.voice,128));p.start();ok,_=p.render()
  self.assertEqual(ok,0);self.assertEqual(bytes(p.u.mem_read(p.samples,256)),b'\x5a'*256)
  self.assertEqual(bytes(p.u.mem_read(p.voice,128)),before);self.assertEqual(p.post,[])
 def test_delayed_native_sample_cache_is_recognized_on_later_render(self):
  p=Kick();p.ready=False;p.start();self.assertEqual(p.render()[0],0)
  p.ready=True;self.assertEqual(p.render()[0],1)
 def test_retrigger_is_monophonic_only_within_the_same_native_sound(self):
  p=Kick();p.start();p.render();old=p.voice;new=old+0x800
  p.w(new+12,p.desc);p.f(new+0x48,1);p.u.mem_write(new,b'\1');p.w(p.root+0x60,2);p.w(p.root+0x24,new)
  p.call(SYMS['kick_voice'],new,p.root)
  self.assertEqual(bytes(p.u.mem_read(old,1)),b'\0');self.assertEqual(bytes(p.u.mem_read(new,1)),b'\1')
 def test_native_entry_wrapper_preserves_registers_floats_and_stack(self):
  p=Kick();p.start();sp=0x2003d000;before=[0x1100+i for i in range(13)];before[0:4]=[p.root,p.voice,0,0]
  p.w(sp,p.temp);p.w(sp+4,p.output)
  for r,v in zip(REGS,before):p.u.reg_write(r,v)
  for i in range(32):p.u.reg_write(UC_ARM_REG_S0+i,0x3f800000+i*100)
  p.u.reg_write(UC_ARM_REG_SP,sp);p.u.reg_write(UC_ARM_REG_LR,p.stop|1)
  p.u.emu_start(0x08091821,p.stop,count=1000000)
  before[0]=1;self.assertEqual([p.u.reg_read(r) for r in REGS],before);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp)
  for i in range(32):self.assertEqual(p.u.reg_read(UC_ARM_REG_S0+i),0x3f800000+i*100)
 def test_original_entry_prologue_is_replayed_for_non_synth_sample(self):
  p=Kick(False);sp=0x2003d000;p.w(sp,p.temp);p.w(sp+4,p.output)
  p.u.reg_write(UC_ARM_REG_R0,p.root);p.u.reg_write(UC_ARM_REG_R1,p.voice);p.u.reg_write(UC_ARM_REG_SP,sp)
  p.u.emu_start(0x08091821,0x08091824,count=1000000)
  self.assertEqual(p.u.reg_read(UC_ARM_REG_PC),0x08091824);self.assertEqual(p.u.reg_read(UC_ARM_REG_SP),sp-36)
 def test_actual_native_postprocess_produces_audio_and_native_mute_silences_it(self):
  p=Kick();p.native_postprocess();p.start()
  for _ in range(8):p.render()
  self.assertGreater(max(abs(v) for channel in p.outputs() for v in channel),.001)
  p.u.mem_write(p.root+0x600,b'\1')
  for _ in range(8):p.render()
  self.assertLess(max(abs(v) for channel in p.outputs() for v in channel),.0000001)
 def test_actual_native_pan_processing_routes_synth_left_and_right(self):
  energies=[]
  for pan in [-1,0,1]:
   p=Kick();p.native_postprocess();p.f(p.root+0x12c,pan);p.base_source(p.voice+0x1c0,p.root+0x128);p.start()
   for _ in range(8):p.render()
   energies.append([sum(x*x for x in ch) for ch in p.outputs()])
  self.assertGreater(energies[0][0],.0001);self.assertLess(energies[0][1],.00000001)
  self.assertGreater(energies[2][1],.0001);self.assertLess(energies[2][0],.00000001)
  self.assertAlmostEqual(energies[1][0],energies[1][1],places=7)
 def test_native_pitch_lock_controls_live_generator_frequency_multiplier(self):
  from test_editable_locks import word
  from step_locks import A_SYMS
  p=Kick();p.start();p.call(0x080d5880,p.root,p.voice)
  self.assertAlmostEqual(struct.unpack('<f',struct.pack('<I',p.u.reg_read(UC_ARM_REG_R0)))[0],1)
  p.payload(word(2,12000));p.call(A_SYMS['lock_voice'],p.voice,p.root);p.call(0x080d5880,p.root,p.voice)
  self.assertAlmostEqual(struct.unpack('<f',struct.pack('<I',p.u.reg_read(UC_ARM_REG_R0)))[0],2,places=5)
 def test_normal_sample_replacing_marker_disables_prior_synth_slot(self):
  p=Kick();p.start();p.render();p.marker=False;p.start();self.assertEqual(p.render()[0],0)
 def test_generator_fades_to_silence_and_releases_native_voice_at_lifetime_end(self):
  p=Kick();p.start();p.render();p.w(0x24042000+16+24,8);ok,out=p.render()
  self.assertEqual(ok,1);self.assertEqual(out[8:],(0.,)*56);self.assertEqual(bytes(p.u.mem_read(p.voice,1)),b'\0')
 def test_old_project_slots_are_reclaimed_without_reading_freed_roots(self):
  p=Kick()
  for i in range(16):
   root=0x20000000+i*0x800;p.w(root,0x080ac66c);p.w(root+12,100+i)
   p.call(SYMS['kick_voice'],p.voice,root)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24042008,4))[0],16)
  p.w(0x30035f40,6001);p.call(SYMS['kick_voice'],p.voice,p.root)
  self.assertEqual(struct.unpack('<I',p.u.mem_read(0x24042008,4))[0],17)
 def test_compiled_engine_uses_hardware_float_without_software_float_helpers(self):
  for name in ['__aeabi_fadd','__aeabi_fmul','__addsf3','__mulsf3']:self.assertNotIn(name,SYMS)

 def test_embedded_math_matches_host_reference_over_used_ranges(self):
  p=Kick()
  for name,inputs in [('sinf',[i*.1 for i in range(-63,64)]),('powf',[(2,i*.1) for i in range(-100,101)]+[(.5,.25),(1,.25)])]:
   for value in inputs:
    args=value if isinstance(value,tuple) else (value,)
    for i,v in enumerate(args):p.u.reg_write(UC_ARM_REG_S0+i,struct.unpack('<I',struct.pack('<f',v))[0])
    p.call(SYMS[name]);actual=struct.unpack('<f',struct.pack('<I',p.u.reg_read(UC_ARM_REG_S0)))[0]
    expected=math.sin(value) if name=='sinf' else math.pow(*value)
    self.assertAlmostEqual(actual,expected,delta=max(1,abs(expected))*.00001)

if __name__=='__main__':unittest.main(verbosity=2)
