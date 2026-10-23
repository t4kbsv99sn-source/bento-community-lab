import unittest,json,struct,hashlib
from pathlib import Path
from unicorn import *
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parent.parent;BASE=0x08040000;V=0x30000000;WAVE=V+0x71c0;CTX=V+0x10000
IMAGE=(ROOT/'build/k16_candidate/bento1.bin').read_bytes();M=json.loads((ROOT/'build/k16_candidate/manifest.json').read_text())
class Fixture:
 def __init__(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
  for a,n in [(BASE,0x1c0000),(V,0x40000),(0x24040000,0x40000)]:self.u.mem_map(a,n)
  self.u.mem_write(BASE,IMAGE);self.kick=True;self.path=b'bento_kick.wav';self.original=False;self.continuation=0;self.fills=[];self.title='';self.widget=WAVE;self.entry=0x08183854;self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.w(V,0x0819e624);self.w(V+0x87bc,1);self.w(V+0x87c4,2);self.u.mem_write(V+0x87cc,b'\x0e');self.w(WAVE+0x2c,V)
  for i,x in enumerate([10,220,600,140]):self.w(WAVE+4+i*4,x)
  self.u.mem_write(CTX,b'\x01\x01');self.w(CTX+4,V+0x11000)
 def w(self,a,n):self.u.mem_write(a,struct.pack('<I',n))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def ret(self,n=0):self.u.reg_write(UC_ARM_REG_R0,n);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def hook(self,u,a,n,d):
  r=[u.reg_read(UC_ARM_REG_R0+i) for i in range(4)]
  if a==0x08133f7c:self.ret(1)
  elif a==0x0813390e:u.mem_write(r[3],self.path+b'\0' if self.kick else b'normal.wav\0');self.ret()
  elif a==0x081bb040:self.ret()
  elif a==0x0817e85e:self.title=bytes(u.mem_read(r[1],24)).split(b'\0')[0].decode();self.ret()
  elif a==0x08167fa0:
   sp=u.reg_read(UC_ARM_REG_SP);self.fills.append((*r,self.r(sp),self.r(sp+4)));self.ret()
  elif a in [0x08183858,0x0816876e,0x0817de02,0x0816a980,0x0817e784,0x08179124]:self.original=True;self.continuation=a;u.emu_stop()
 def call(self,refresh=False):
  self.u.reg_write(UC_ARM_REG_R0,V if refresh else self.widget);self.u.reg_write(UC_ARM_REG_R1,CTX);self.u.reg_write(UC_ARM_REG_SP,V+0x3f000);self.u.reg_write(UC_ARM_REG_LR,0x081ff001)
  for i in range(8):self.u.reg_write(UC_ARM_REG_R4+i,0x123400+i)
  self.u.emu_start((0x08152144 if refresh else self.entry)|1,0x081ff000,count=40000)
  assert [self.u.reg_read(UC_ARM_REG_R4+i) for i in range(8)]==[0x123400+i for i in range(8)]
  frames={0x08183858:36,0x0816876e:0,0x0817de02:0,0x0816a980:56,0x0817e784:24,0x08179124:40}
  assert self.u.reg_read(UC_ARM_REG_SP)==V+0x3f000-frames.get(self.continuation,0)

class Tests(unittest.TestCase):
 def widget(self,p,offset,entry,parent=V):
  p.widget=V+offset;p.entry=entry;p.w(p.widget+0x2c,parent)
  for i,x in enumerate([10,220,600,140]):p.w(p.widget+4+i*4,x)
 def test_wave_envelope_lfo_each_suppressed_at_actual_entry(self):
  for off,entry,letter in [(0x71c0,0x08183854,'W'),(0x710c,0x08168768,'E'),(0x715c,0x0817ddfc,'L')]:
   p=Fixture();self.widget(p,off,entry);p.call();self.assertFalse(p.original);self.assertEqual(p.fills,[(V+0x11000,10,220,600,140,0xf1)])
 def test_wave_envelope_lfo_markers_accumulate(self):
  p=Fixture()
  for off,entry in [(0x71c0,0x08183854),(0x710c,0x08168768),(0x715c,0x0817ddfc)]:self.widget(p,off,entry);p.call()
  self.assertEqual(p.r(0x24043d48)&7,7)
 def test_lower_buttons_labels_and_grey_rectangles_suppressed(self):
  for off,entry in [(0x7e60,0x0816a97c),(0x7f30,0x0816a97c),(0x8124,0x0817e780),(0x8204,0x08179120)]:
   p=Fixture();self.widget(p,off,entry);p.call();self.assertFalse(p.original);self.assertEqual(len(p.fills),1)
 def test_normal_sample_all_six_original_paths_preserve_arguments(self):
  for off,entry in [(0x71c0,0x08183854),(0x710c,0x08168768),(0x715c,0x0817ddfc),(0x7e60,0x0816a97c),(0x8124,0x0817e780),(0x8204,0x08179120)]:
   p=Fixture();p.kick=False;self.widget(p,off,entry);p.call();self.assertTrue(p.original);self.assertEqual(p.fills,[]);self.assertEqual(p.u.reg_read(UC_ARM_REG_R0),p.widget);self.assertEqual(p.u.reg_read(UC_ARM_REG_R1),CTX)
 def test_visible_title_and_upper_row_labels_not_suppressed(self):
  for off in [0x80b4,0x440,0x2838]:
   p=Fixture();self.widget(p,off,0x0817e780);p.call();self.assertTrue(p.original)
 def test_nested_third_row_click_label_visible(self):
  p=Fixture();p.w(V+0x4828+0x2c,V+0x6c20);p.w(V+0x6c20+0x2c,V);self.widget(p,0x4c30,0x0817e780,V+0x4828);p.call();self.assertTrue(p.original)
 def test_nested_second_row_label_visible(self):
  p=Fixture();p.w(V+0x2430+0x2c,V+0x6c20);p.w(V+0x6c20+0x2c,V);self.widget(p,0x2838,0x0817e780,V+0x2430);p.call();self.assertTrue(p.original)
 def test_detached_and_unrelated_page_untouched(self):
  for parent in [0,V]:
   p=Fixture();p.w(V,0x08190000);p.w(WAVE+0x2c,parent);p.call();self.assertTrue(p.original)
 def test_parent_cycle_is_bounded_and_falls_through(self):
  p=Fixture();p.w(WAVE+0x2c,WAVE);p.call();self.assertTrue(p.original)
 def test_no_other_widget_flags_or_params_written(self):
  p=Fixture();before=bytes(p.u.mem_read(V,0x8800));p.call();self.assertEqual(bytes(p.u.mem_read(V,0x8800)),before)
 def test_incremental_only_request_clears(self):
  p=Fixture();p.u.mem_write(CTX,b'\x00\x01');p.call();self.assertEqual(len(p.fills),1)
 def test_zero_context_paint_flags_dont_fill(self):
  p=Fixture();p.u.mem_write(CTX,b'\x00\x00');p.call();self.assertEqual(p.fills,[])
 def test_native_envelope_and_lfo_early_return_when_no_full_draw(self):
  for off,entry in [(0x710c,0x08168768),(0x715c,0x0817ddfc)]:
   p=Fixture();p.kick=False;p.u.mem_write(CTX,b'\x00\x01');self.widget(p,off,entry);p.call();self.assertFalse(p.original)
 def test_word_alignment_and_exact_K7_reversal(self):
  self.assertEqual(len(IMAGE)%4,0);b=bytearray(IMAGE)
  for r in reversed(M['patches']):
   a=int(r['address'],16)-BASE;n=bytes.fromhex(r['new']);self.assertEqual(b[a:a+len(n)],n);b[a:a+len(n)]=bytes.fromhex(r['old'])
  self.assertEqual(hashlib.sha256(b).hexdigest(),M['base_sha256']);self.assertEqual(b[:0xc0000],IMAGE[:0xc0000]);self.assertEqual(b[0xc0000:0xc0400],IMAGE[0xc0000:0xc0400]);self.assertEqual(len(M['patches']),9)
 def test_third_row_still_suppressed_for_snare_and_hat(self):
  for path in [b'BENTO_Synth_Snare.wav',b'BENTO_Synth_HiHat.wav']:
   p=Fixture();p.path=path;self.widget(p,0x4c30,0x0817e780);p.call();self.assertFalse(p.original)
 def test_lower_sampler_suppressed_for_all_three_engines(self):
  for path in [b'BENTO_Kick_K2.wav',b'BENTO_Synth_Snare.wav',b'BENTO_Synth_HiHat.wav']:
   for off,entry in [(0x71c0,0x08183854),(0x710c,0x08168768),(0x715c,0x0817ddfc),(0x8124,0x0817e780),(0x8204,0x08179120)]:
    p=Fixture();p.path=path;self.widget(p,off,entry);p.call();self.assertFalse(p.original)
if __name__=='__main__':unittest.main(verbosity=2)
