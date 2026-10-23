"""CH1 installed ARM UI through actual native widgets and note container.
Navigation, model lookup, fonts, Undo storage and engine queue remain fixtures.
"""
import struct,unittest,gc
from test_native_piano import Piano
from test_integration import UU,IMAGE
import test_eu9 as header_fixture
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
KEYS=[0x196,0x197,0x19a,0x19b,0x19d,0x19e,0x19f,0x177,0x1d2,0x1d3,0x128,0x129,0x12a,0x12b,0x12c,0x12d]
KEEP=[]
class Device(Piano):
 def __init__(self):
  super().__init__();KEEP.append(self);self.call(0x081599bc,self.view);self.piano=self.view
  self.u.hook_add(UC_HOOK_CODE,self.nav,begin=0x081420ec,end=0x081420ec)
  self.u.hook_add(UC_HOOK_CODE,self.bubble,begin=0x0816fc34,end=0x0816fc34)
  self.editor=0xc0500000;self.u.mem_map(self.editor,0x20000)
 def nav(self,u,a,n,d):self.navlog.append(u.reg_read(UC_ARM_REG_R1));self.ret()
 def bubble(self,u,a,n,d):
  e=u.reg_read(UC_ARM_REG_R1);code=self.r(e)&65535
  if code in [0xcf,0x1052,0x1053,0xe6]: # E6: grid selection changed (bubbles to the view)
   u.reg_write(UC_ARM_REG_R0,self.editor if self.navlog and self.navlog[-1]==0x1a else self.piano)
   u.reg_write(UC_ARM_REG_PC,0x08145d91 if self.navlog and self.navlog[-1]==0x1a else 0x0815a599)
  else:self.ret()
 def open_editor(self):
  self.action(0x1052,piano=True);self.call(0x08145b7c,self.editor);self.w(0x20016000,42);self.call(0x08145efc,self.editor,0x20016000)
 def action(self,code,piano=False):
  e=0x2002e000;self.w(e,code);return self.call(0x0815a598 if piano else 0x08145d90,self.piano if piano else self.editor,e)
 def edit(self,i,value):
  e=0x2002e000;self.u.mem_write(e,struct.pack('<5I',0xcf,42,KEYS[i],value&0xffffffff,0));return self.call(0x08145d90,self.editor,e)
 def value(self,i):
  arg=0x20016000;out=0x20016010;self.w(arg,42);assert self.call(0x08133614,self.model,arg,KEYS[i],out)==1
  return struct.unpack('<i',self.u.mem_read(out,4))[0]
 def status(self):return self.text(self.r(self.editor+0x93c8+8))
 def toolbar(self):
  out=header_fixture.Tests().header_data(self,page=0x17)
  header_fixture.Tests().native_header(self,out);return out
class Tests(unittest.TestCase):
 def test_registry_fits_actual_native_allocation_and_preserves_every_other_descriptor(self):
  p=Device();r=p.r(0x30031484);before=bytes(p.u.mem_read(r,0x3e60));p.u.mem_write(r+0x3e60,b'CANARY32');p.open_editor()
  after=bytes(p.u.mem_read(r,0x3e60));self.assertEqual(p.u.mem_read(r+0x3e60,8),b'CANARY32')
  for i in range(499):
   if i in KEYS:self.assertEqual(struct.unpack_from('<H',after,i*32)[0],i)
   else:self.assertEqual(before[i*32:(i+1)*32],after[i*32:(i+1)*32],hex(i))
 def seq(self,p,code,ms):p.w(0x3001fe2c,ms);return p.call(UU['fx_dispatch'],p.model,code,0,11)
 def double(self,p):self.seq(p,0xaf,1000);self.seq(p,0xb0,1080);return self.seq(p,0xaf,1200)
 def pianokeys(self,p):return list(struct.unpack('<8H',p.u.mem_read(p.view+0x11bcc0,16)))
 def piano(self,p,code,key=0,value=0):
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',code,0,key,value&0xffffffff,0));return p.call(UU['piano_event'],p.view,e)
 def notes(self,p):return sorted((struct.unpack_from('<I',e,4)[0],struct.unpack_from('<H',e,16)[0]) for e in p.events())
 def arrow(self,p,index):
  # Real path: patched piano hardware-event entry 0815B548 with native code 0xAE.
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',0xae,0,index,0,0));p.call(0x0815b548,p.view,e);return 1
 def test_seq_double_tap_enters_live_chord_mode_on_the_piano_roll(self):
  # CH5: no page change; empty slot at the start, written only on the first turn.
  p=Device();before=p.events();self.assertEqual(self.double(p),1);self.assertEqual(p.navlog,[])
  self.assertEqual(self.pianokeys(p),KEYS[:8]);self.assertEqual(p.events(),before)
  self.assertEqual(self.piano(p,0xcf,KEYS[0],0),1);self.assertEqual(self.notes(p),[(0,48),(0,52),(0,55)]) # C3 major (Bento naming, MIDI 48)
 def test_live_edit_replaces_draft_immediately_and_exit_keeps_notes(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],1) # Minor
  self.assertEqual(self.notes(p),[(0,48),(0,51),(0,55)])
  self.assertEqual(self.piano(p,0x1052),1);self.assertEqual(self.pianokeys(p),KEYS[8:]) # bank 2
  self.assertEqual(self.double(p),1);self.assertEqual(len(p.events()),3);self.assertNotEqual(self.pianokeys(p),KEYS[8:])
 def test_right_opens_empty_chord_after_previous_and_left_returns_to_existing(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0) # C major at 0, length 4 sixteenths
  self.assertEqual(self.arrow(p,9),1);self.assertEqual(len(p.events()),3) # empty until turned
  self.piano(p,0xcf,KEYS[0],1);self.assertEqual(self.notes(p)[3:],[(3840,48),(3840,51),(3840,55)])
  self.assertEqual(self.arrow(p,0),1);self.piano(p,0xcf,KEYS[0],7) # back to first chord: Min7 replaces it
  self.assertEqual([n for n in self.notes(p) if n[0]==0],[(0,48),(0,51),(0,55),(0,58)]);self.assertEqual(len(p.events()),7)
 def test_reentering_adopts_the_last_existing_chord(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],1);self.double(p) # exit, notes stay
  self.double(p);self.assertEqual(p.events().__len__(),3);self.piano(p,0xcf,KEYS[6],90) # velocity edit rewrites same chord
  self.assertEqual(len(p.events()),3);self.assertEqual({struct.unpack_from('<H',e,18)[0] for e in p.events()},{90})
 def test_arrows_outside_live_chord_mode_stay_native(self):
  seen=[];p=Device();p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:seen.append(u.reg_read(UC_ARM_REG_R1)),begin=0x0815b3ec,end=0x0815b3ec)
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',0xae,0,9,0,0));p.call(0x0815b548,p.view,e);self.assertEqual(seen,[1])
 def project_scale(self,p,root,scale):
  # Fixture for model services: project handle lookup and properties 8E/8D.
  def handle(u,a,n,d):p.w(u.reg_read(UC_ARM_REG_R1),0x5c);p.ret(1)
  def prop(u,a,n,d):
   key=u.reg_read(UC_ARM_REG_R2)
   if key in (0x8d,0x8e) and p.r(u.reg_read(UC_ARM_REG_R1))==0x5c:p.w(u.reg_read(UC_ARM_REG_R3),root if key==0x8e else scale);p.ret(1)
  p.u.hook_add(UC_HOOK_CODE,handle,begin=0x08133e54,end=0x08133e54);p.u.hook_add(UC_HOOK_CODE,prop,begin=0x08133614,end=0x08133614)
 def test_diatonic_types_follow_project_key_and_scale(self):
  # Fixture project: C major (native 8E root index 3 = C, 8D scale 1 = Major).
  p=Device();self.project_scale(p,3,1);self.double(p);self.piano(p,0xcf,KEYS[0],15) # Diatonic
  self.assertEqual(self.notes(p),[(0,48),(0,52),(0,55)])
  self.piano(p,0xcf,KEYS[10],62);self.assertEqual(self.notes(p),[(0,62),(0,65),(0,69)]) # D -> minor
  self.piano(p,0xcf,KEYS[10],71);self.assertEqual(self.notes(p),[(0,71),(0,74),(0,77)]) # B -> dim
  self.piano(p,0xcf,KEYS[0],16);self.piano(p,0xcf,KEYS[10],67);self.assertEqual(self.notes(p),[(0,67),(0,71),(0,74),(0,77)]) # G7
  value=0x20016000;p.call(UU['chord_get'],p.model,0,KEYS[0],value);self.assertEqual(p.r(value),16)
 def test_diatonic_in_a_minor_project(self):
  p=Device();self.project_scale(p,0,3);self.double(p);self.piano(p,0xcf,KEYS[0],15) # A minor
  self.piano(p,0xcf,KEYS[10],69);self.assertEqual(self.notes(p),[(0,69),(0,72),(0,76)]) # A minor
  self.piano(p,0xcf,KEYS[10],64);self.assertEqual(self.notes(p),[(0,64),(0,67),(0,71)]) # E minor (natural minor v)
 # CH6 chord pad audition: M4 publishes the chord shape per pitch class; M7 plays it
 # (test_chord_audition.py) and publishes the pad's pitch, which becomes the root.
 def mail(self,p):
  bank=p.r(0x24041fc0+4);m=bank+44576;count=list(p.u.mem_read(m+16,12))
  return p.r(m),p.r(m+4),[list(struct.unpack('<6b',p.u.mem_read(m+32+pc*6,6)))[:count[pc]] for pc in range(12)]
 def pad(self,p,pad,pitch,code=0xb0):
  bank=p.r(0x24041fc0+4);p.u.mem_write(bank+44576+128+4+pad,bytes([0x80|pitch]))
  e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',code,0,pad,1,0));p.call(0x0815b548,p.view,e)
 def test_live_mode_publishes_chord_shape_and_exit_withdraws_it(self):
  p=Device();self.double(p);serial,active,shapes=self.mail(p)
  self.assertEqual((serial%2,active),(0,1));self.assertEqual(shapes,[[0,4,7]]*12)
  self.piano(p,0xcf,KEYS[0],7);self.assertEqual(self.mail(p)[2],[[0,3,7,10]]*12) # Min7 follows the encoder
  self.double(p);serial,active,_=self.mail(p);self.assertEqual((serial%2,active),(0,0))
 def test_diatonic_shape_differs_per_pitch_class(self):
  p=Device();self.project_scale(p,3,1);self.double(p);self.piano(p,0xcf,KEYS[0],15) # C major, Diatonic
  shapes=self.mail(p)[2];self.assertEqual(shapes[0],[0,4,7]);self.assertEqual(shapes[2],[0,3,7]);self.assertEqual(shapes[11],[0,3,6])
 def test_pad_press_sets_chord_root_and_redraws_chord(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0) # C3 major written at 0
  self.pad(p,3,62);self.assertEqual(self.notes(p),[(0,62),(0,66),(0,69)]) # D4 major replaces it
  value=0x20016000;p.call(UU['chord_get'],p.model,0,KEYS[10],value);self.assertEqual(p.r(value),62)
  self.pad(p,3,62,code=0xb1);self.assertEqual(self.notes(p),[(0,62),(0,66),(0,69)]) # release changes nothing
 def test_pad_on_empty_slot_creates_the_chord_and_pads_outside_chord_mode_do_nothing(self):
  p=Device();before=p.events();self.double(p);self.double(p) # enter + leave: bank exists, mode off
  self.pad(p,0,60);self.assertEqual(p.events(),before)
  self.double(p);self.pad(p,0,60);self.assertEqual(self.notes(p),[(0,60),(0,64),(0,67)])
 def test_pad_without_published_pitch_is_ignored(self):
  p=Device();self.double(p);before=p.events();e=0x2002e000;p.u.mem_write(e,struct.pack('<5I',0xb0,0,5,1,0));p.call(0x0815b548,p.view,e)
  self.assertEqual(p.events(),before)
 # CH7 Rhythm (encoder 4, replaces Strum): the chord repeats inside its length.
 def starts(self,p):return sorted({struct.unpack_from('<I',e,4)[0]//960 for e in p.events()})
 def lengths(self,p):return sorted({struct.unpack_from('<I',e,8)[0] for e in p.events()})
 def rhythm(self,p):value=0x20016000;p.call(UU['chord_get'],p.model,0,KEYS[3],value);return p.r(value)
 def test_rhythm_repeats_the_chord_inside_its_length(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0) # C3 major, 4 steps
  self.piano(p,0xcf,KEYS[3],1);self.assertEqual(self.starts(p),[0,2]);self.assertEqual(self.lengths(p),[960]);self.assertEqual(len(p.events()),6)
  self.piano(p,0xcf,KEYS[3],5);self.assertEqual(self.starts(p),[0,1,2,3]);self.assertEqual(self.lengths(p),[480]) # 16ths
  self.piano(p,0xcf,KEYS[3],0);self.assertEqual(self.starts(p),[0]);self.assertEqual(self.lengths(p),[3840]);self.assertEqual(len(p.events()),3) # Hold again
 def test_type_edit_rewrites_every_hit(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.piano(p,0xcf,KEYS[3],3) # 4 hits
  self.piano(p,0xcf,KEYS[0],1);self.assertEqual(sorted({struct.unpack_from('<H',e,16)[0] for e in p.events()}),[48,51,55]);self.assertEqual(len(p.events()),12)
 def test_navigation_treats_rhythm_hits_as_one_chord_and_recognises_it(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.piano(p,0xcf,KEYS[3],1) # C: 2 hits over 4 steps
  self.arrow(p,9);self.piano(p,0xcf,KEYS[0],1) # Right: empty slot at step 4 (not on the second hit), Minor
  self.assertEqual(self.starts(p),[0,2,4,6]);self.assertEqual(self.rhythm(p),1) # new chord keeps the rhythm
  self.arrow(p,0);self.assertEqual(self.rhythm(p),1);self.piano(p,0xcf,KEYS[0],7) # back on C, still 2 hits: Min7
  self.assertEqual(len([e for e in p.events() if struct.unpack_from('<I',e,4)[0]<3840]),8)
  self.double(p);self.double(p);self.assertEqual(self.rhythm(p),1) # re-enter on the last chord: rhythm recognised
 def test_identical_held_chords_stay_separate(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.arrow(p,9);self.piano(p,0xcf,KEYS[0],0) # C, C held
  self.arrow(p,0);self.assertEqual(self.rhythm(p),0);self.piano(p,0xcf,KEYS[6],90)
  self.assertEqual({struct.unpack_from('<I',e,4)[0]:struct.unpack_from('<H',e,18)[0] for e in p.events()},{0:90,3840:100})
 # CH7 chord selection: the chord's notes use the native grid selection.
 def project(self,p):p.call(0x0815abb8,p.view,0,0);p.call(0x081599bc,p.view)
 def selected(self,p):
  g=p.view+0x38;notes=p.r(g+0x34);out=[]
  for i in range(0x200):
   n=notes+i*0x48
   if p.u.mem_read(n+0x31,1)[0] and p.u.mem_read(n+0x32,1)[0]:out.append(p.r(n+0x40))
  return sorted(out)
 def ids(self,p,start):return sorted(struct.unpack_from('<I',e,12)[0] for e in p.events() if struct.unpack_from('<I',e,4)[0]==start)
 def test_current_chord_is_selected_white(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.arrow(p,9);self.piano(p,0xcf,KEYS[0],1);self.project(p)
  self.assertEqual(self.selected(p),self.ids(p,3840)) # only the second (current) chord
  self.arrow(p,0);self.project(p);self.assertEqual(self.selected(p),self.ids(p,0))
  self.double(p);self.project(p);self.assertLessEqual(len(self.selected(p)),1) # leaving clears the chord (native event cursor may stay)
 def test_touching_a_note_picks_its_chord(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.piano(p,0xcf,KEYS[3],1) # C, 2 hits
  self.arrow(p,9);self.piano(p,0xcf,KEYS[0],1);self.project(p) # current: second chord
  target=self.ids(p,1920)[0] # a note in the second hit of the first chord
  p.call(0x08174c4e,p.view+0x38,target,1) # native touch-style select, posts E6
  self.project(p);self.assertEqual(self.selected(p),sorted(self.ids(p,0)+self.ids(p,1920))) # whole first chord
  self.assertEqual(self.rhythm(p),1);self.piano(p,0xcf,KEYS[0],7) # encoders now edit the touched chord
  self.assertEqual(len([e for e in p.events() if struct.unpack_from('<I',e,4)[0]<3840]),8)
 # CH8 Bars encoder (key 177): clip length in bars through native Step Count (62).
 def steplen(self,p,index):
  # Fixture: the sequence's Step Len property (60) as the native header reads it.
  def prop(u,a,n,d):
   if u.reg_read(UC_ARM_REG_R2)==0x60:p.w(u.reg_read(UC_ARM_REG_R3),index);p.ret(1)
  p.u.hook_add(UC_HOOK_CODE,prop,begin=0x0812dca2,end=0x0812dca2)
 def sent(self,p):
  log=[];p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:log.append(tuple(p.r(u.reg_read(UC_ARM_REG_R1)+o) for o in (0,8,12))),begin=0x0815a598,end=0x0815a598);return log
 def test_bars_encoder_right_of_step_count_in_sequence_tab(self):
  p=Device();v=p.view;self.steplen(p,6);p.u.mem_write(v+0x125dac,b'\x01');p.call(0x081599bc,v) # Sequence tab, stored Step Len 6 = 1/16, 16 steps
  self.assertEqual(self.pianokeys(p)[4],0x177);self.assertEqual(p.r(v+0x11bcd0+16),0) # 1 bar
  log=self.sent(p);self.piano(p,0xcf,0x177,2);self.assertIn((0xcf,0x62,64),log) # 4 bars = 64 sixteenths
  p.u.mem_write(v+0x125dac,b'\x01');self.steplen(p,3);p.call(0x081599bc,v);log=self.sent(p);self.piano(p,0xcf,0x177,3);self.assertIn((0xcf,0x62,32),log) # stored 3 = 1/4 steps: 8 bars = 32
 def test_bars_shows_plus_or_minus_when_not_exact(self):
  p=Device();v=p.view;txt=lambda:p.text(p.call(UU['bars_text'],v))
  p.w(v+0x11cd14,6);p.w(v+0x11cd18,16);self.assertEqual(txt(),'1')
  p.w(v+0x11cd18,20);self.assertEqual(txt(),'1+');p.w(v+0x11cd18,64);self.assertEqual(txt(),'4');p.w(v+0x11cd18,8);self.assertEqual(txt(),'1-')
 def test_chord_encoder_8_is_bars(self):
  p=Device();v=p.view;self.steplen(p,6);self.double(p);self.assertEqual(self.pianokeys(p)[7],0x177)
  log=self.sent(p);self.piano(p,0xcf,0x177,1);self.assertIn((0xcf,0x62,32),log)
 # CH8 live overlay: the played chord's name while a pad is held.
 def dev(self,p):return p.r(0x24048000+1128)
 def test_held_pad_shows_chord_name_until_release(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],7) # Min7
  self.pad(p,3,62);d=self.dev(p);self.assertEqual(p.r(d+96),1);self.assertEqual(p.text(d+112),'Dm7') # name after held,aud,seen,quiet
  self.piano(p,0xcf,KEYS[2],1);self.assertEqual(p.text(d+112),'Dm7/F') # first inversion: bass F
  self.pad(p,3,62,code=0xb1);self.assertEqual(p.r(d+96),0)
 # CH8 MIXER hold: an encoder turn (AB) while K16 holds MIXER counts as use.
 def test_encoder_turn_while_holding_mixer_counts_as_use(self):
  p=Device();k=0x24048cc0;p.w(k,0x354d5442);p.w(k+4,5);p.w(k+8,0)
  p.call(UU['fx_dispatch'],p.model,0xab,0xfffffffe,3);self.assertEqual(p.r(k+8),1)
  p.w(k+4,0);p.w(k+8,0);p.call(UU['fx_dispatch'],p.model,0xab,0xfffffffe,3);self.assertEqual(p.r(k+8),0) # not holding: nothing
 # CH9 chord mode stays on for its track; recorded chords get the Rhythm.
 def record(self,p,start,length,pitches):
  # Native recorder fixture: new notes with fresh IDs through the native add path.
  temp=0xc01e0000;handle=0x2002c000;raw=0x2002c100;p.w(handle,p.seq);p.call(0x0810d16c,temp)
  for pitch in pitches:
   p.u.mem_write(raw,struct.pack('<6I',1,start,length,0,pitch|(100<<16),0));ident=p.call(0x0812e070,p.project,p.seq,raw);p.w(raw+12,ident);p.call(0x0810d176,temp,raw)
  p.call(0x08136544,p.model,handle,temp)
 def tick(self,p,ms):p.w(0x3001fe2c,ms);p.call(UU['chord_track_tick'])
 def test_chord_mode_survives_leaving_the_piano_roll(self):
  p=Device();self.double(p);mail=lambda:p.r(p.r(0x24041fc0+4)+44576+4)
  p.call(UU['fx_nav'],p.model,0x0c);self.tick(p,10);self.assertEqual(mail(),1) # FX view: pads still play chords
  owner=p.owner;p.owner=owner+1;self.tick(p,20);self.assertEqual(mail(),0) # other track selected: off
  p.owner=owner;self.tick(p,30);self.assertEqual(mail(),1) # back: on again
 def test_recorded_chords_get_the_rhythm(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0);self.piano(p,0xcf,KEYS[3],1) # 2 hits; draft at 0
  self.record(p,3840,3840,[50,54,57]);self.record(p,7680,960,[60]) # a recorded chord and a single note
  self.tick(p,1000);self.tick(p,1050);self.assertEqual(len([e for e in p.events() if struct.unpack_from('<I',e,4)[0]==3840]),3) # waits 100 ms
  self.tick(p,1200)
  rec=sorted((struct.unpack_from('<I',e,4)[0],struct.unpack_from('<I',e,8)[0],struct.unpack_from('<H',e,16)[0]) for e in p.events() if struct.unpack_from('<I',e,4)[0]>=3840)
  self.assertEqual(rec,[(3840,960,50),(3840,960,54),(3840,960,57),(5760,960,50),(5760,960,54),(5760,960,57),(7680,960,60)])
  before=p.events();self.tick(p,1400);self.assertEqual(p.events(),before) # our own notes are not reshaped again
 def test_no_rhythm_or_held_pad_leaves_recordings_alone(self):
  p=Device();self.double(p);self.piano(p,0xcf,KEYS[0],0) # Hold
  self.record(p,3840,3840,[50,54,57]);self.tick(p,1000);self.tick(p,1300);self.assertEqual(len([e for e in p.events() if struct.unpack_from('<I',e,4)[0]==3840]),3)
 def test_overlapping_notes_are_replaced_not_refused(self):
  e=struct.pack('<BBHIIIHHI',1,0,0,0,1920,300,52,100,0);p=Device();p.setnotes([e]);self.double(p)
  self.piano(p,0xcf,KEYS[0],0);self.assertEqual(self.notes(p),[(0,48),(0,52),(0,55)])
  self.assertNotIn(300,[struct.unpack_from('<I',x,12)[0] for x in p.events()])
 def test_live_header_shows_lit_chord_bank_in_free_slot(self):
  p=Device();self.double(p);out=p.toolbar()
  self.assertEqual(p.text(out+0x74),'Chord 1/2');self.assertEqual(p.u.mem_read(out+0x74+0x21,1)[0],1)
 def test_single_seq_and_slow_or_drum_double_tap_stay_native(self):
  p=Device();self.assertEqual(self.seq(p,0xaf,1000),0);self.seq(p,0xb0,1080);self.assertEqual(self.seq(p,0xaf,1800),0);self.assertFalse(p.navlog)
  p=Device();p.type=14;self.seq(p,0xaf,1000);self.seq(p,0xb0,1080);self.assertEqual(self.seq(p,0xaf,1200),0);self.assertFalse(p.navlog)
 def test_piano_header_no_longer_carries_chord(self):
  p=Device();out=p.toolbar();self.assertNotIn(0x1052,[p.r(out+0x74+i*48+44)&65535 for i in range(6)])
 def test_editor_header_places_back_and_insert_visibly_on_empty_native_page(self):
  p=Device();p.open_editor();root=header_fixture.ROOT;p.call(0x08180198,root)
  out=0x20028000;p.u.mem_write(out,bytes(p.u.mem_read(header_fixture.TEMPLATES+20*0x1c4,0x1c4)));self.assertEqual(p.u.mem_read(out+0x1c2,1)[0],0x1a)
  p.u.mem_write(p.model+0x12c,b'\x1a');p.call(UU['seq_toolbar'],p.model,out,0);p.call(0x0817faf8,root,out)
  back=root+0x54c+5*0xd0;insert=root+0x54c+4*0xd0
  self.assertEqual((p.text(insert+0x3c+0x31),p.text(back+0x3c+0x31)),('Insert','Back'))
  self.assertEqual((p.u.mem_read(insert+0x30,1)[0],p.u.mem_read(back+0x30,1)[0]),(0,0))
 def test_native_encoder_bubbles_to_new_chord_editor(self):
  p=Device();p.open_editor();before=p.value(0);self.assertEqual(p.call(0x08171e44,p.editor+0x70,12800),1);self.assertNotEqual(p.value(0),before)
 def test_insert_single_chord_then_native_piano_projection_and_duplicate_refusal(self):
  p=Device();p.open_editor();p.edit(6,83);p.action(0x1053);self.assertEqual(len(p.events()),3);self.assertEqual(len(p.undo),1)
  self.assertEqual(sorted(struct.unpack_from('<H',e,16)[0] for e in p.events()),[48,52,55]);self.assertEqual({struct.unpack_from('<H',e,18)[0] for e in p.events()},{83})
  before=p.events();p.action(0x1053);self.assertEqual(p.events(),before);self.assertIn('Overlapping',p.status());self.assertEqual(len(p.undo),1)
  p.action(0x1052);self.assertEqual(p.navlog[-1],0x17)
 def test_progression_preset_key_scale_voicing_and_insert(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(9,2);p.edit(11,2);p.edit(0,7);p.edit(1,2);p.edit(2,1);p.action(0x1053)
  self.assertEqual(len(p.events()),10);self.assertEqual(len(p.undo),1);self.assertIn('Inserted',p.status())
  self.assertEqual(sorted({struct.unpack_from('<I',e,4)[0] for e in p.events()}),[0,3840,7680])
 def test_minor_preset_adopts_minor_and_explicit_quality_survives_key_changes(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(9,6);self.assertEqual(p.value(12),1);self.assertEqual(p.value(0),1)
  p.edit(0,6);p.edit(11,2);self.assertEqual(p.value(0),6);p.edit(13,3);self.assertEqual(p.value(0),6)
 def test_outside_clip_edit_is_atomic_and_reports_error_without_silent_replacement(self):
  p=Device();p.open_editor();p.edit(8,1);p.edit(13,32);self.assertEqual(p.value(13),4);self.assertIn('Outside clip',p.status());self.assertFalse(p.events());self.assertFalse(p.undo)
  p.action(0x1053);self.assertEqual(len(p.events()),12)
 def test_stale_owner_and_occupied_registry_do_not_modify_music_or_other_owner(self):
  p=Device();r=p.r(0x30031484);p.w(r+KEYS[0]*32,KEYS[0]);p.w(r+KEYS[0]*32+4,0xdeadbeef);p.action(0x1052,piano=True);self.assertFalse(p.navlog);self.assertEqual(p.r(r+KEYS[0]*32+4),0xdeadbeef)
  p=Device();p.open_editor();p.owner+=1;p.action(0x1053);self.assertIn('Sequence changed',p.status());self.assertFalse(p.events());self.assertFalse(p.undo)
 def test_full_toolbar_is_preserved_and_navigation_disarms_custom_actions(self):
  p=Device();out=0x20028000
  for i in range(6):p.w(out+0x74+i*48+44,0x1032+i)
  before=bytes(p.u.mem_read(out,0x1c4));self.assertEqual(p.call(UU['chord_toolbar'],p.model,out,0),0);self.assertEqual(bytes(p.u.mem_read(out,0x1c4)),before)
  p.open_editor();p.call(UU['chord_nav'],p.model,2);self.assertEqual(p.call(UU['chord_event'],p.editor,0x2002e000),0)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
