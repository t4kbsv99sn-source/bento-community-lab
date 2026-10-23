"""Ownership of overlapping audition notes; independent of native MIDI routing."""
import ctypes as C,unittest
from test_chords import lib,generate
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint)
class Audition(C.Structure):
 _fields_=[('references',C.c_uint8*128),('held',C.c_uint8*16),('count',C.c_uint8*16),('pitch',(C.c_uint8*6)*16)]
class Tests(unittest.TestCase):
 def setUp(self):
  self.a=Audition();self.log=[];self.on=CALLBACK(lambda _,p,v:self.log.append(('on',p,v)));self.off=CALLBACK(lambda _,p,v:self.log.append(('off',p,v)))
 def press(self,pad,c):return lib.chord_pad_on(C.byref(self.a),pad,C.byref(c),self.on,self.off,None)
 def release(self,pad):lib.chord_pad_off(C.byref(self.a),pad,self.off,None)
 def stop(self):lib.chord_audition_stop(C.byref(self.a),self.off,None)
 def test_root_pad_plays_the_entire_chord_and_release_uses_played_snapshot(self):
  c=generate().chords[0];self.assertEqual(self.press(0,c),0);self.assertEqual(self.log,[('on',48,100),('on',52,100),('on',55,100)])
  c.root=60;c.type=1;self.release(0);self.assertEqual(self.log[-3:],[('off',48,0),('off',52,0),('off',55,0)])
 def test_shared_notes_remain_until_every_owning_pad_is_released(self):
  c=generate().chords[0];self.press(0,c);self.press(1,c);self.assertEqual(len(self.log),3);self.release(0);self.assertEqual(len(self.log),3);self.release(1);self.assertEqual(len(self.log),6)
 def test_stop_and_repeated_release_are_idempotent(self):
  c=generate().chords[0];self.press(0,c);self.stop();before=list(self.log);self.stop();self.release(0);self.assertEqual(self.log,before);self.assertEqual(bytes(self.a.references),bytes(128))
 def test_invalid_new_chord_does_not_kill_current_audition(self):
  c=generate().chords[0];self.press(0,c);before=list(self.log);c.root=127;self.assertNotEqual(self.press(0,c),0);self.assertEqual(self.log,before);self.stop();self.assertEqual(len(self.log),6)
 def test_retrigger_releases_previous_pad_and_plays_new_chord(self):
  c=generate().chords[0];self.press(0,c);c.root=50;self.press(0,c);self.assertEqual([p for k,p,v in self.log if k=='on'],[48,52,55,50,54,57]);self.stop();self.assertFalse(any(self.a.references))
if __name__=='__main__':unittest.main(verbosity=2)
