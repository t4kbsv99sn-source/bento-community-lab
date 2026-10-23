"""CH6 chord pad audition on M7. Runs the real native pad module press 08084760
and release 08083FE0 (keyboard pad mode 3, chromatic mapping 0809DB40) with the
patched post sites. Only the router post 0809ECA0 is a fixture that records the
note records it would queue for the instrument."""
import struct,unittest,gc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,AA
MOD=0x20030000;KBD_SCALE=0x20031000;REC=0x20032000;ROUTER=0x20033000
BANK=0xc0000000;BANK_BYTES=46080;MAIL=BANK+44576;PUB=MAIL+128;OWN=PUB+32
TRACK=0x55;LAYER=0x66
KEEP=[]
class Pads(Fixture):
 def __init__(self,layer=False):
  super().__init__();KEEP.append(self);self.posts=[]
  self.u.mem_write(BANK,bytes(BANK_BYTES))
  for off,v in [(0,0x324c5545),(4,BANK),(8,BANK_BYTES),(12,1)]:self.w(0x24041fc0+off,v)
  self.w(BANK+4,2)
  self.u.mem_write(MOD,bytes(0x600));self.u.mem_write(MOD+0x490,b'\x03')
  self.w(MOD+0x2c8,0);self.w(MOD+0x2cc,TRACK);self.w(MOD+0x2ec,LAYER if layer else TRACK);self.w(MOD+0xc4,1000)
  self.w(MOD+0x424,KBD_SCALE);self.w(KBD_SCALE+0x10,12);self.u.mem_write(MOD+0x428,struct.pack('<hh',3,4)) # C, octave 4 -> pad idx 0 = MIDI 48
  self.u.hook_add(UC_HOOK_CODE,self.post,begin=0x0809eca0,end=0x0809eca0)
 def post(self,u,a,n,d):
  r=u.reg_read(UC_ARM_REG_R1);t,_,h,p,v,_=struct.unpack('<6I',u.mem_read(r,24))
  self.posts.append((t&255,h,p,v));self.ret()
 def mail(self,offsets,active=1,serial=2,velocity=0):
  self.w(MAIL,serial);self.w(MAIL+4,active);self.w(MAIL+8,velocity)
  for pc in range(12):
   o=offsets(pc) if callable(offsets) else offsets
   self.u.mem_write(MAIL+16+pc,bytes([len(o)]));self.u.mem_write(MAIL+32+pc*6,struct.pack('<6b',*(list(o)+[0]*(6-len(o)))))
 def press(self,pad,pressure=0x8000):
  self.u.mem_write(REC,struct.pack('<6I',0xac,0,0xfffffffe,pad,pressure,0));self.posts=[]
  self.call(0x08084760,MOD,REC,ROUTER);return self.posts
 def release(self,pad):
  self.w(MOD+0xc4,self.r(MOD+0xc4)+100);self.posts=[];self.call(0x08083fe0,MOD,pad,ROUTER);return self.posts
 def pub(self,pad):return self.u.mem_read(PUB+4+pad,1)[0]
def pitches(posts,kind,handle=TRACK):return [p for t,h,p,v in posts if t==kind and h==handle]
class Tests(unittest.TestCase):
 def test_without_chord_mode_a_pad_plays_its_single_native_note(self):
  p=Pads();on=p.press(8);self.assertEqual(pitches(on,2),[48]);self.assertEqual(p.pub(8),0)
  self.assertEqual(pitches(p.release(8),3),[48])
 def test_chord_mode_pad_plays_whole_chord_on_its_pitch_and_releases_it(self):
  p=Pads();p.mail([0,4,7]);on=p.press(10) # pad 10 -> idx 2 -> D3 (50)
  self.assertEqual(pitches(on,2),[50,54,57]);self.assertEqual({v for t,h,pp,v in on},{on[0][3]})
  self.assertEqual(p.pub(10),0x80|50) # M4 reads this to set the chord root
  self.assertEqual(pitches(p.release(10),3),[50,54,57])
 def test_release_uses_the_notes_actually_started_even_if_the_chord_changed(self):
  p=Pads();p.mail([0,4,7]);p.press(8);p.mail([0,3,7,10],serial=4)
  self.assertEqual(pitches(p.release(8),3),[48,52,55])
 def test_shared_tones_stay_until_every_pad_is_released(self):
  p=Pads();p.mail([0,4,7]);p.press(8);on=p.press(12) # C3 major 48 52 55, then E3 major 52 56 59
  self.assertEqual(pitches(on,2),[56,59]) # 52 already sounding: not restarted
  self.assertEqual(pitches(p.release(8),3),[48,55]) # 52 still held by the E chord
  self.assertEqual(pitches(p.release(12),3),[52,56,59])
 def test_diatonic_shape_per_pitch_class_and_range_clamp(self):
  p=Pads();p.mail(lambda pc:[0,3,7] if pc==2 else [0,4,7]);self.assertEqual(pitches(p.press(10),2),[50,53,57]);p.release(10)
  p.mail([0,4,7,24,31]);p.u.mem_write(MOD+0x428,struct.pack('<hh',3,9)) # octave 9: C8=108
  on=p.press(15);self.assertEqual(pitches(on,2),[115,119,122]) # +24/+31 above 127 dropped
  self.assertEqual(pitches(p.release(15),3),[115,119,122])
 def test_layer_handle_gets_the_same_chord(self):
  p=Pads(layer=True);p.mail([0,4,7]);on=p.press(8)
  self.assertEqual(pitches(on,2),[48,52,55]);self.assertEqual(pitches(on,2,LAYER),[48,52,55])
  off=p.release(8);self.assertEqual(pitches(off,3),[48,52,55]);self.assertEqual(pitches(off,3,LAYER),[48,52,55])
 def test_torn_or_inactive_mail_and_missing_bank_fall_back_to_native(self):
  p=Pads();p.mail([0,4,7],serial=3);self.assertEqual(pitches(p.press(8),2),[48]);p.release(8)
  p.mail([0,4,7],active=0);self.assertEqual(pitches(p.press(8),2),[48]);p.release(8)
  p.mail([0,4,7]);p.w(0x24041fc0,0);self.assertEqual(pitches(p.press(8),2),[48]);self.assertEqual(pitches(p.release(8),3),[48])
 def test_leaving_chord_mode_while_held_still_releases_the_chord(self):
  p=Pads();p.mail([0,4,7]);p.press(8);p.mail([0,4,7],active=0,serial=4)
  self.assertEqual(pitches(p.release(8),3),[48,52,55])
 def test_chord_velocity_scales_the_pad_velocity(self):
  # CH8: the chord's Velocity (published in ChordMail) scales what the pads play.
  p=Pads();full=p.press(8)[0][3];p.release(8)
  p.mail([0,4,7],velocity=64);on=p.press(8);self.assertEqual({v for t,h,pp,v in on},{full*64//127})
 def test_held_chord_pads_are_published(self):
  # CH9: M4 waits for all chord pads to be up before reshaping recordings.
  p=Pads();p.mail([0,4,7]);held=lambda:p.r(PUB+20)
  p.press(8);p.press(10);self.assertEqual(held(),2);p.release(8);self.assertEqual(held(),1);p.release(10);self.assertEqual(held(),0)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
