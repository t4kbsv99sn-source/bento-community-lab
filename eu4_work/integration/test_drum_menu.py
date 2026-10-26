"""D1 drum synths without files to copy (M4): the "Drum Synth" pad-menu entry,
the Engine knob on the synth page, the marker files the firmware writes, and
the native file-onto-pad call.

Runs the built image. The native menus are built by the real builder 081412EC.
FatFS (open 08120148, read 08120464, write 08120604, close 08120974), the
native path join 08104648, the model getters and the file-onto-pad function
08139DE0 are fixtures; the files are compared byte for byte with the package
generator tools/make_drum_carriers.py."""
import struct,unittest,gc,sys,tempfile
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from test_integration import Fixture,UU,IMAGE
M=0x30024b00;PROJECT=0x30030164;MENUS=0x30030168;EV=0x20035000
TRACK=0x91;CELL=0x95;FILE=0x96;VIEW=0xc0180000
NAMES=['BENTO_Kick_K2.wav','BENTO_Synth_Snare.wav','BENTO_Synth_HiHat.wav','BENTO_Synth_Clap.wav','BENTO_Synth_Tom.wav']
KEEP=[]
class Drum(Fixture):
 def __init__(self):
  super().__init__();KEEP.append(self);self.registry();self.call(0x081412ec)
  self.files={};self.open={};self.assigned=[];self.track_type=14;self.pad=5;self.cells={CELL:3};self.index=2;self.fail_open=set()
  self.path='..\\BENTO_Kick_K2.wav'
  self.u.hook_add(UC_HOOK_CODE,self.native)
 def native(self,u,a,n,d):
  r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0x08120148:
   path=self.text(r[1]);mode=r[2]
   if mode==1:
    if path not in self.files or path in self.fail_open:self.ret(4);return
    self.open[r[0]]=[path,0];self.w(r[0]+16,len(self.files[path]));self.w(r[0]+20,0);self.ret(0)
   else:self.files[path]=bytearray();self.open[r[0]]=[path,0];self.modes=getattr(self,'modes',[])+[mode];self.ret(0)
  elif a==0x08120464:
   path,pos=self.open[r[0]];data=self.files[path][pos:pos+r[2]];u.mem_write(r[1],bytes(data));self.w(r[3],len(data));self.open[r[0]][1]+=len(data);self.ret(0)
  elif a==0x08120604:
   path,pos=self.open[r[0]];self.files[path]+=bytes(u.mem_read(r[1],r[2]));self.w(r[3],r[2]);self.ret(0)
  elif a==0x08120974:self.open.pop(r[0],None);self.ret(0)
  elif a==0x08121152:self.dirs=getattr(self,'dirs',[])+[self.text(r[0])];self.ret(0)
  elif a==0x08104648:
   out='%s\\%s'%(self.text(r[2]),self.text(r[3]));u.mem_write(r[0],out.encode()+b'\0');self.ret(r[0])
  elif a==0x08133614:
   if r[1]==PROJECT and r[2]==0x131:self.w(r[3],self.index);self.ret(1)
   elif self.r(r[1])==TRACK and r[2]==0x74:self.w(r[3],self.pad);self.ret(1)
   elif r[2]==0x73 and self.r(r[1]) in self.cells:self.w(r[3],self.cells[self.r(r[1])]);self.ret(1)
   else:self.ret(0)
  elif a==0x08133960:self.w(r[2],TRACK if r[1]==self.index else 0);self.ret(1)
  elif a==0x08133cfc:self.w(r[1],TRACK);self.ret(1)
  elif a==0x08133f7c:
   h=self.r(r[1]);self.ret(self.track_type if h==TRACK else 1 if h in self.cells else 5 if h==FILE else 0)
  elif a==0x0813391a:
   kids=[CELL,FILE] if self.r(r[1])==TRACK else []
   if r[2]<len(kids):self.w(r[3],kids[r[2]]);self.ret(1)
   else:self.ret(0)
  elif a==0x0813390e:u.mem_write(r[3],self.path.encode()+b'\0');self.ret(1)
  elif a==0x08139de0:
   sp=u.reg_read(UC_ARM_REG_SP);self.assigned.append((r[1],self.r(r[2]),r[3],self.text(self.r(sp)),self.r(sp+4)));self.ret()
  elif a in (0x08145cf4,0x08152144,0x08171c1c,0x0817e85e,0x08170656,0x081689f8):self.ret()
 def menu(self,mid):
  for m in range(20):
   b=MENUS+m*0xe0
   if struct.unpack('<H',self.u.mem_read(b,2))[0]==mid:
    n=self.u.mem_read(b+0xcc,1)[0];return [(struct.unpack('<H',self.u.mem_read(b+4+k*20,2))[0],self.text(self.r(b+8+k*20)) if self.r(b+8+k*20) else '',self.u.mem_read(b+20+k*20,1)[0]) for k in range(n)]
 def model_event(self,code,*words):
  self.u.mem_write(EV,struct.pack('<5I',code,*(list(words)+[0]*(4-len(words)))));return self.call(UU['analog_model_event'],M,EV)
def expected():
 # Same as tools/make_drum_carriers.py (the package's SD files).
 out={}
 for i,name in enumerate(NAMES):
  frames=144019+2*i;pcm=struct.pack('<32h',*[1 if 0xb1e70a5c&(1<<k) else -1 for k in range(32)])+bytes((frames-32)*2)
  out[name]=b'RIFF'+struct.pack('<I',36+len(pcm))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,48000,96000,2,16)+b'data'+struct.pack('<I',len(pcm))+pcm
 return out
class Tests(unittest.TestCase):
 def test_one_shot_pad_menus_get_drum_synth(self):
  p=Drum();before=p.menu(0xf1)
  self.assertEqual(p.model_event(0xf1),0) # the native handler still opens the menu
  for mid in (0xf1,0x100c,0x100e):
   cells=p.menu(mid);self.assertEqual(cells[-1],(0x1056,'Drum Synth',1),hex(mid))
  self.assertEqual(len(p.menu(0xf7)),9);self.assertNotIn(0x1056,[c[0] for c in p.menu(0xf7)]) # already nine: the native menu shows at most nine
  self.assertEqual(p.menu(0xf1)[:-1],before)
  p.model_event(0xf7);self.assertEqual(len(p.menu(0xf1)),9) # added once
  self.assertNotIn(0x1056,[c[0] for c in p.menu(0xf6)]) # instrument menu untouched
 def test_other_track_types_never_show_it(self):
  p=Drum();p.model_event(0xf1);p.track_type=15;p.model_event(0x100c)
  for mid in (0xf1,0xf7,0x100c,0x100e):self.assertNotIn(0x1056,[c[0] for c in p.menu(mid)])
  self.assertEqual([c[0] for c in p.menu(0xf1)],[0x102b,0x1039,0x1045,0x1046,0xa,0x103f,0x103e,0x1040])
 def test_entry_writes_the_kick_marker_and_loads_it_onto_the_selected_pad(self):
  p=Drum();p.model_event(0xf1);self.assertEqual(p.model_event(0x1056),0)
  self.assertEqual(p.assigned,[(2,0,5,'Drum Synths\\Kick.wav',0)]) # pad 5 has no cell yet: native creates it
  self.assertEqual(bytes(p.files['\\Drum Synths\\Kick.wav']),expected()['BENTO_Kick_K2.wav']);self.assertEqual(p.modes,[10])
 def test_existing_pad_cell_is_reused(self):
  p=Drum();p.pad=3;p.model_event(0x1056);self.assertEqual(p.assigned[0][1],CELL)
 def test_existing_marker_is_not_rewritten_and_a_foreign_file_is_left_alone(self):
  p=Drum();e=expected()['BENTO_Kick_K2.wav'];p.files['\\Drum Synths\\Kick.wav']=bytearray(e)
  p.model_event(0x1056);self.assertFalse(hasattr(p,'modes'));self.assertEqual(len(p.assigned),1)
  p=Drum();p.files['\\Drum Synths\\Kick.wav']=bytearray(b'RIFF'+bytes(200))
  p.model_event(0x1056);self.assertEqual(p.assigned,[]);self.assertEqual(len(p.files['\\Drum Synths\\Kick.wav']),204)
 def test_not_on_other_track_types(self):
  p=Drum();p.track_type=18;p.model_event(0x1056);self.assertEqual(p.assigned,[]);self.assertEqual(p.files,{})
 def test_engine_knob_switches_the_synth_on_the_same_pad(self):
  p=Drum();p.registry();p.w(VIEW+0x87bc,CELL);p.w(VIEW+0x87c4,FILE);p.u.mem_write(VIEW+0x87cc,b'\x0e')
  r=p.r(0x30031484)
  p.call(UU['kick_ui_before'],VIEW)
  d=r+0x1ad*32;self.assertEqual(p.text(p.r(d+4)),'Engine');self.assertEqual(p.u.mem_read(d+2,1)[0],7)
  self.assertEqual([p.text(p.r(p.r(d+8)+4*i)) for i in range(5)],['Kick','Snare','HiHat','Clap','Tom'])
  p.u.mem_write(EV,struct.pack('<4I',0xcf,CELL,0x1ad,3));self.assertEqual(p.call(UU['kick_ui_event'],VIEW,EV),1)
  self.assertEqual(p.assigned,[(2,CELL,3,'Drum Synths\\Clap.wav',0)])
  self.assertEqual(bytes(p.files['\\Drum Synths\\Clap.wav']),expected()['BENTO_Synth_Clap.wav'])
  p.u.mem_write(EV,struct.pack('<4I',0xcf,CELL,0x1ad,0));p.call(UU['kick_ui_event'],VIEW,EV);self.assertEqual(len(p.assigned),1) # already a Kick
 def test_every_engine_file_matches_the_package_files(self):
  p=Drum();e=expected()
  for i,name in enumerate(NAMES):
   p.u.mem_write(0x20036000,('\\Projects\\'+name).encode()+b'\0');self.assertEqual(p.call(UU['drum_ensure'],0x20036000,144019+2*i),1)
   self.assertEqual(bytes(p.files['\\Projects\\'+name]),e[name],name)
 def test_menus_follow_the_track_on_every_ui_message(self):
  # P6: no menu-open event needed (1.6P5 showed nothing on hardware).
  p=Drum();p.call(UU['fx_dispatch'],M,0xfe,0,3)
  for mid in (0xf1,0x100c,0x100e):self.assertEqual(p.menu(mid)[-1][:2],(0x1056,'Drum Synth'),hex(mid))
  p.track_type=15;p.call(UU['fx_dispatch'],M,0xfe,0,3)
  for mid in (0xf1,0x100c,0x100e):self.assertNotIn(0x1056,[c[0] for c in p.menu(mid)])
 def test_pad_page_view_takes_the_action_once(self):
  p=Drum();p.w(0x3001fe2c,5000);p.u.mem_write(EV,struct.pack('<5I',0x1056,0,0,0,0))
  self.assertEqual(p.call(UU['drum_view_event'],VIEW,EV),0);self.assertEqual(len(p.assigned),1)
  p.model_event(0x1056);self.assertEqual(len(p.assigned),1) # the same press seen by the model too
  p.w(0x3001fe2c,6000);p.model_event(0x1056);self.assertEqual(len(p.assigned),2)
  self.assertEqual(struct.unpack_from('<I',IMAGE,0x0819dc50-0x08040000)[0],UU['drum_view_event']|1)
 def test_first_ui_message_makes_the_drum_synths_folder(self):
  # P7: Load on an empty cell opens the browser directly (owner photo), so the
  # synths are files in "\\Drum Synths", made once per boot when missing.
  p=Drum();p.call(UU['fx_dispatch'],M,0xfe,0,3);e=expected()
  self.assertEqual(p.dirs,['\\Drum Synths'])
  for name,want in zip(['Kick','Snare','HiHat','Clap','Tom'],NAMES):self.assertEqual(bytes(p.files['\\Drum Synths\\'+name+'.wav']),e[want],name)
  n=len(p.modes);p.call(UU['fx_dispatch'],M,0xfe,0,3);self.assertEqual(len(p.modes),n) # once per boot
 def test_folder_files_are_drum_synths(self):
  p=Drum();p.registry();p.w(VIEW+0x87bc,CELL);p.w(VIEW+0x87c4,FILE);p.u.mem_write(VIEW+0x87cc,b'\x0e')
  for path,model in [('..\\..\\Drum Synths\\Clap.wav',7),('Drum Synths\\TOM.wav',9),('..\\Samples\\Kick.wav',0),('\\Projects\\BENTO_Synth_Snare.wav',3)]:
   p.path=path;self.assertEqual(p.call(UU['kick_ui_supported'],VIEW),model,path)
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
class Recognition(unittest.TestCase):
 # P11 (owner: pads loaded from the Drum Synths folder showed the sample page).
 def view(self,p):
  v=VIEW;p.u.mem_write(v+0x87bc,struct.pack('<I',CELL));p.u.mem_write(v+0x87c4,struct.pack('<I',FILE));p.u.mem_write(v+0x87cc,b'\x0e');return v
 def test_carrier_is_recognised_by_content_whatever_the_stored_path(self):
  for i,(path,model) in enumerate([('0:/DRUMSY~1/SNARE.WAV',3),('Drum Synths/HiHat.wav',5),('\\Somewhere\\my clap.wav',7)]):
   p=Drum();data=expected()[NAMES[[3,5,7].index(model)+1]]
   p.files[path.lstrip('\\')]=bytearray(data);p.files[path]=bytearray(data);p.path=path
   self.assertEqual(p.call(UU['kick_ui_supported'],self.view(p)),model,path)
 def test_path_without_leading_separator_is_tried_with_one(self):
  p=Drum();p.files['\\Drum Synths\\Tom.wav']=bytearray(expected()[NAMES[4]]);p.path='Drum Synths\\Tom.wav'
  self.assertEqual(p.call(UU['kick_ui_supported'],self.view(p)),9)
 def test_plain_sample_is_not_a_drum_synth_and_is_read_once(self):
  p=Drum();wav=bytearray(expected()[NAMES[1]]);wav[44]^=0xff # wrong signature
  p.files['kick.wav']=wav;p.path='kick.wav';reads=[]
  p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:reads.append(1),begin=0x08120464,end=0x08120464)
  v=self.view(p);self.assertEqual(p.call(UU['kick_ui_supported'],v),0);self.assertEqual(p.call(UU['kick_ui_supported'],v),0)
  self.assertEqual(len(reads),1) # cached per file node
 def test_wrong_length_or_format_is_rejected(self):
  p=Drum();wav=bytearray(expected()[NAMES[1]]+b'\0\0');p.files['x.wav']=wav;p.path='x.wav'
  self.assertEqual(p.call(UU['kick_ui_supported'],self.view(p)),0)
