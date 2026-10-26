"""Host and Cortex-M4 parity, musical invariants, atomic render and metadata."""
import ctypes as C,json,os,struct,unittest,random
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB
from unicorn.arm_const import *
OUT=Path(os.environ['BENTO_CHORD_BUILD']);lib=C.CDLL(str(OUT/'chords.so'))
class Chord(C.Structure):
 _fields_=[('start',C.c_uint32),('end',C.c_uint32),('root',C.c_int16),('type',C.c_int16),('voicing',C.c_int16),('inversion',C.c_int16),('strum',C.c_int16),('velocity',C.c_uint8),('degree',C.c_uint8),('seventh',C.c_uint8),('quality_override',C.c_uint8),('manual_inversion',C.c_uint8),('pinned',C.c_uint8)]
class Progression(C.Structure):
 _fields_=[(n,C.c_uint32) for n in ['key','scale','tonic','grid','count','preset','auto_voice']]+[('chords',Chord*16)]
class Note(C.Structure):
 _fields_=[('start',C.c_uint32),('end',C.c_uint32),('pitch',C.c_uint16),('velocity',C.c_uint16),('chord',C.c_uint8),('voice',C.c_uint8),('reserved',C.c_uint16)]
lib.chord_preset_name.restype=C.c_char_p
class Arm:
 def __init__(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
  self.u.mem_map(int(os.environ.get('BENTO_CHORD_TEST_ORIGIN','0x081e0000'),0),0x20000);self.u.mem_write(int(os.environ.get('BENTO_CHORD_TEST_ORIGIN','0x081e0000'),0),(OUT/'chords.bin').read_bytes());self.u.mem_map(0x20000000,0x40000);self.syms=json.loads((OUT/'symbols.json').read_text())
 def call(self,name,*args):
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(r,v)
  for i,v in enumerate(args[4:]):self.u.mem_write(0x2003e000+i*4,struct.pack('<I',v))
  self.u.reg_write(UC_ARM_REG_SP,0x2003e000);self.u.reg_write(UC_ARM_REG_LR,0x2003f001)
  self.u.emu_start(self.syms[name]|1,0x2003f000,count=3000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x2003f000
  return C.c_int32(self.u.reg_read(UC_ARM_REG_R0)).value
 def progression(self,**kw):
  p=generate(**kw);self.u.mem_write(0x20000000,bytes(p));return p
 def read(self):return Progression.from_buffer_copy(bytes(self.u.mem_read(0x20000000,C.sizeof(Progression))))
def generate(preset=0,key=0,scale=0,tonic=48,start=0,duration=3840):
 p=Progression();assert lib.chord_generate(C.byref(p),preset,key,scale,tonic,start,duration)==0;return p
def pitches(c):
 out=(C.c_int*6)();n=lib.chord_notes(C.byref(c),out);return n,list(out)[:max(n,0)]
class Tests(unittest.TestCase):
 def test_progression_preset_has_degree_qualities_and_default_duration(self):
  p=generate();self.assertEqual([c.type for c in p.chords[:4]],[0,0,1,0]);self.assertEqual([c.degree for c in p.chords[:4]],[0,4,5,3]);self.assertEqual([c.start for c in p.chords[:4]],[0,3840,7680,11520]);self.assertEqual(lib.chord_preset_count(),12)
 def test_every_preset_renders_for_each_supported_scale_and_key_on_host_and_arm(self):
  arm=Arm()
  for preset in range(12):
   for scale in range(5):
    for key in range(12):
     host=generate(preset,key,scale,48+key)
     self.assertEqual(arm.call('chord_generate',0x20000000,preset,key,scale,48+key,0,3840),0)
     self.assertEqual(bytes(arm.read()),bytes(host))
     notes=(Note*96)();n=lib.chord_render(C.byref(host),notes,96,61440);self.assertGreater(n,0)
     self.assertEqual(arm.call('chord_render',0x20000000,0x20010000,96,61440),n)
     self.assertEqual(bytes(arm.u.mem_read(0x20010000,n*16)),bytes(notes)[:n*16])
 def test_all_diatonic_triads_and_sevenths_are_supported(self):
  for scale in range(5):
   for degree in range(7):
    for seventh in range(2):self.assertGreaterEqual(lib.chord_degree_type(scale,degree,seventh),0)
 def test_explicit_minor_dominant_is_preserved_when_scale_changes(self):
  p=generate(8,9,1,45);self.assertEqual(p.chords[2].type,0);self.assertEqual(p.chords[2].quality_override,1)
  self.assertEqual(lib.chord_reharmonize(C.byref(p),2,2),0);self.assertEqual(p.chords[2].type,0);self.assertEqual([c.degree for c in p.chords[:4]],[0,3,4,0])
 def test_scale_change_adapts_nonoverridden_qualities_and_preserves_tonic_register(self):
  p=generate();self.assertEqual(lib.chord_reharmonize(C.byref(p),2,1),0);self.assertEqual(p.tonic,50);self.assertEqual([c.type for c in p.chords[:4]],[1,1,0,1])
 def test_automatic_voiceleading_is_repeatable_and_manual_inversion_is_protected(self):
  p=generate();before=bytes(p)
  for _ in range(20):self.assertEqual(lib.chord_voicelead(C.byref(p)),0);self.assertEqual(bytes(p),before)
  p.chords[1].manual_inversion=1;p.chords[1].inversion=2;before=bytes(p.chords[1]);lib.chord_voicelead(C.byref(p));self.assertEqual(bytes(p.chords[1]),before)
 def test_single_chord_inversions_and_drop2_match_expected_notes(self):
  p=generate();c=p.chords[0];c.root=50;c.type=7;c.inversion=1
  self.assertEqual(pitches(c),(4,[53,57,60,62]));c.root=48;c.type=6;c.inversion=0;c.voicing=2
  self.assertEqual(pitches(c),(4,[43,48,52,59]))
 def test_strum_direction_delays_correct_voices_and_keeps_common_endpoint(self):
  for gap in [120,-120]:
   p=generate();p.count=1;p.chords[0].strum=gap;notes=(Note*96)();self.assertEqual(lib.chord_render(C.byref(p),notes,96,61440),3)
   self.assertEqual([n.start for n in notes[:3]],[0,120,240] if gap>0 else [240,120,0]);self.assertEqual([n.end for n in notes[:3]],[3840]*3)
 def test_render_failures_leave_output_unchanged(self):
  for cause in ['short','capacity','clip','pitch']:
   p=generate();out=(Note*96)();C.memset(C.byref(out),0xa5,C.sizeof(out));before=bytes(out)
   if cause=='short':p.chords[0].end=100;p.chords[0].strum=120
   if cause=='pitch':p.chords[0].root=126
   n=lib.chord_render(C.byref(p),out,1 if cause=='capacity' else 96,100 if cause=='clip' else 61440)
   self.assertLess(n,0);self.assertEqual(bytes(out),before)
 def test_invalid_generation_does_not_mutate_previous_phrase(self):
  p=generate();before=bytes(p)
  for args in [(12,0,0,48,0,3840),(0,12,0,48,0,3840),(0,0,5,48,0,3840),(0,0,0,49,0,3840),(0,0,0,48,0,0),(0,0,0,48,0x7ffffff0,3840)]:
   self.assertNotEqual(lib.chord_generate(C.byref(p),*args),0);self.assertEqual(bytes(p),before)
 def test_metadata_roundtrip_is_versioned_pointer_free_and_arm_identical(self):
  arm=Arm();p=generate(8,9,1,45);p.chords[0].pinned=1;p.chords[1].strum=-240;p.chords[1].manual_inversion=1
  data=(C.c_uint8*440)();self.assertEqual(lib.chord_encode(C.byref(p),data),0);out=Progression();self.assertEqual(lib.chord_decode(C.byref(out),data,440),0);self.assertEqual(bytes(out),bytes(p))
  arm.u.mem_write(0x20000000,bytes(p));self.assertEqual(arm.call('chord_encode',0x20000000,0x20010000),0);self.assertEqual(bytes(arm.u.mem_read(0x20010000,440)),bytes(data))
  self.assertEqual(arm.call('chord_decode',0x20001000,0x20010000,440),0);self.assertEqual(bytes(arm.u.mem_read(0x20001000,C.sizeof(p))),bytes(p))
 def test_damaged_or_unknown_metadata_never_partially_loads(self):
  p=generate();raw=(C.c_uint8*440)();lib.chord_encode(C.byref(p),raw);before=bytes(p)
  for offset in [0,4,16,26,100,439]:
   data=(C.c_uint8*440).from_buffer_copy(raw);data[offset]^=1;self.assertEqual(lib.chord_decode(C.byref(p),data,440),1);self.assertEqual(bytes(p),before)
 def test_reharmonizing_there_and_back_does_not_drift(self):
  p=generate();before=bytes(p)
  for _ in range(20):
   self.assertEqual(lib.chord_reharmonize(C.byref(p),11,1),0);self.assertEqual(lib.chord_reharmonize(C.byref(p),0,0),0);self.assertEqual(bytes(p),before)
if __name__=='__main__':unittest.main(verbosity=2)
