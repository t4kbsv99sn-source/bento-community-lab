"""CH6 Euclidean lanes in the native piano roll (Option B), rendered by the real
grid paint/tick code with only DMA2D emulated. Fonts are fixtures, so the text
primitive is skipped; everything drawn here is native fills/lines plus ours."""
import struct,unittest,gc,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/display_emulator'))
import dma2d
from test_native_piano import Piano
from test_euclidean import note
from test_integration import UU
from unicorn import UC_HOOK_CODE
BANK=0xc0000000;BANK_BYTES=46080;FB=0xc1000000;SURF=0x24078000;CTX=0x24078100
BG,BOX,GREY=0xf1,0xf2,0xf3
KEEP=[]
def pack(length,hits,on=1):return struct.pack('<II',(length-1)|(hits<<8)|(on<<25),100)
class Lanes(Piano):
 def __init__(self,lanes=None,step=None,drum=True,notes=None):
  super().__init__();KEEP.append(self);v=self.view;self.g=v+0x38
  self.u.mem_map(FB,0x100000);self.dma=dma2d.DMA2D(self.u);self.w(0x30000e68,0x52001000)
  self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:self.ret(0),begin=0x08166df4,end=0x08166df4) # text: fixture fonts
  if drum:self.u.mem_write(v+0x125dae,b'\x01');self.type=14
  self.setnotes(notes if notes is not None else [])
  self.call(0x0815abb8,v,0,0)
  if lanes is not None:self.bank(lanes,step)
 def bank(self,lanes,step=None,melodic=None):
  self.u.mem_write(BANK,bytes(BANK_BYTES))
  for off,val in [(0,0x324c5545),(4,BANK),(8,BANK_BYTES),(12,1)]:self.w(0x24041fc0+off,val)
  self.w(BANK,1);self.w(BANK+4,2);self.w(BANK+8,1)
  rec=BANK+32;self.w(rec,2);self.w(rec+4,self.owner);self.w(rec+8,0)
  if melodic:
   self.w(rec+12,1)
   for i,pitch in enumerate(melodic):self.u.mem_write(rec+16+i,bytes([pitch]))
  for pad,(length,hits) in lanes.items():self.u.mem_write(rec+32+pad*8,pack(length,hits))
  self.phase(step)
 def phase(self,step):
  rt=BANK+32+2*128*160;self.w(rt+4,0);self.w(rt+8,1);self.w(rt+36,self.owner) # EuRuntime row/epoch/owner
  self.w(rt+44,step or 0);self.w(rt+48,1 if step is not None else 0);self.w(rt+52,self.r(rt+52)+2) # reserved[1..3]
 def paint(self,full=1,partial=0):
  self.u.mem_write(CTX,struct.pack('<BBHI',full,partial,0,SURF));self.call(self.r(self.r(self.g)+4),self.g,CTX)
 def surface(self):
  self.u.mem_write(FB,bytes([0x55])*(480*1280));self.call(0x08167a1e,SURF,FB,480,1280,5,4)
 def tick(self):
  flags=0x2001f000;self.u.mem_write(flags,bytes(8));self.call(self.r(self.r(self.g)),self.g,flags);return tuple(self.u.mem_read(flags,2))
 def settle(self):
  # Let the native grid finish its own pending repaint requests first.
  for _ in range(4):
   f=self.tick()
   if f==(0,0):return
   self.paint(full=f[0],partial=f[1])
  raise AssertionError('native grid keeps requesting repaints')
 def px(self,x,y):return self.u.mem_read(FB+(1279-x)*480+(479-y),1)[0]
 def colx(self,i):return self.r(self.g+0x564+4*i)
 def rowy(self,k):return self.r(self.g+0x4fc+4*k)
 def stepx(self,s):tpc=self.r(self.g+0xa20);c=s*960//tpc;x0=self.colx(c);return x0+(s*960-c*tpc)*(self.colx(c+1)-x0)//tpc
 def mid(self,k,s):return (self.stepx(s)+self.stepx(s+1))//2,(self.rowy(k)+self.rowy(k+1))//2
 def edge(self,k,s): # left side of the box: native layout insets column starts by 1
  tpc=self.r(self.g+0xa20);x=self.stepx(s);return (x+1 if s*960%tpc==0 else x),(self.rowy(k)+self.rowy(k+1))//2
ROW=lambda pad:pad+8 if pad<8 else pad-8
class Tests(unittest.TestCase):
 def test_pixel_mapping_matches_native_note_rect(self):
  p=Lanes(notes=[note(0,pad=0,ident=100)]);p.surface();p.paint()
  n=p.r(p.g+0x34);x,y,w,h=[p.r(n+o) for o in (4,8,12,16)]
  self.assertEqual(p.px(x+w//2,y+h//2),0xf2);self.assertEqual(p.px(x+w+5,y+h//2),BG)
 def test_without_lanes_paint_is_exactly_native(self):
  p=Lanes(notes=[note(0,pad=0,ident=100),note(3,pad=2,ident=101)]);p.surface();p.paint();ours=bytes(p.u.mem_read(FB,480*1280))
  p.surface();p.u.mem_write(CTX,struct.pack('<BBHI',1,0,0,SURF));p.call(0x08176d74,p.g,CTX)
  self.assertEqual(ours,bytes(p.u.mem_read(FB,480*1280)));p.settle();self.assertEqual(p.tick(),(0,0))
 def test_each_lane_greyed_after_its_true_length(self):
  p=Lanes({0:(6,3),1:(16,4),2:(3,1)});p.surface();p.paint()
  k0,k1,k2=ROW(0),ROW(1),ROW(2)
  self.assertEqual(p.px(*p.mid(k0,5)),BG);self.assertEqual(p.px(*p.mid(k0,6)),GREY);self.assertEqual(p.px(*p.mid(k0,20)),GREY)
  self.assertEqual(p.px(*p.mid(k2,2)),BG);self.assertEqual(p.px(*p.mid(k2,3)),GREY)
  self.assertEqual(p.px(*p.mid(k1,15)),BG);self.assertEqual(p.px(*p.mid(k1,16)),GREY)
  self.assertEqual(p.px(*p.mid(ROW(3),20)),BG) # no lane on pad 3
 def test_greying_covers_hits_beyond_the_lane_but_not_inside_it(self):
  p=Lanes({0:(4,2)},notes=[note(0,pad=0,ident=100),note(6,pad=0,ident=101)]);p.surface();p.paint()
  self.assertEqual(p.px(*p.mid(ROW(0),0)),0xf2);self.assertEqual(p.px(*p.mid(ROW(0),6)),GREY)
 def test_per_row_playhead_box_at_each_lanes_own_step(self):
  p=Lanes({0:(6,3),1:(16,4),2:(3,1)},step=7);p.surface();p.paint()
  for pad,s in [(0,1),(1,7),(2,1)]:self.assertEqual(p.px(*p.edge(ROW(pad),s)),BOX,(pad,s))
  self.assertEqual(p.px(*p.edge(ROW(1),1)),BG) # pad 1 is at step 7, not 1
 def test_stopped_transport_shows_no_boxes(self):
  p=Lanes({0:(6,3)});p.surface();p.paint();self.assertEqual(p.px(*p.edge(ROW(0),0)),BG)
 def test_tick_requests_partial_repaint_and_partial_moves_the_boxes(self):
  p=Lanes({0:(6,3),2:(3,1)},step=7,notes=[note(1,pad=0,ident=100)]);p.surface();p.paint();p.settle()
  self.assertEqual(p.tick(),(0,0)) # nothing changed
  p.phase(8);self.assertEqual(p.tick(),(0,1)) # lanes moved: partial repaint
  p.paint(full=0,partial=1)
  self.assertEqual(p.px(*p.edge(ROW(0),2)),BOX);self.assertEqual(p.px(*p.edge(ROW(2),2)),BOX)
  self.assertEqual(p.px(*p.mid(ROW(0),1)),0xf2) # old box cell restored with its note
  self.assertEqual(p.px(*p.edge(ROW(2),1)),BG) # old empty box cell restored
 def test_length_change_requests_full_repaint_and_stop_removes_boxes(self):
  p=Lanes({0:(6,3)},step=2);p.surface();p.paint();p.settle()
  p.bank({0:(5,3)},step=2);self.assertEqual(p.tick(),(1,0))
  p.surface();p.paint();p.settle();self.assertEqual(p.px(*p.mid(ROW(0),5)),GREY)
  p.phase(None);self.assertEqual(p.tick(),(0,1));p.paint(full=0,partial=1);self.assertEqual(p.px(*p.edge(ROW(0),2)),BG)
 def test_lanes_removed_requests_one_full_repaint(self):
  p=Lanes({0:(6,3)},step=1);p.surface();p.paint();p.settle()
  p.w(0x24041fc0,0);self.assertEqual(p.tick(),(1,0));p.surface();p.paint();p.settle();self.assertEqual(p.tick(),(0,0))
  self.assertEqual(p.px(*p.mid(ROW(0),8)),BG)
 def test_melodic_lane_uses_its_pitch_row(self):
  p=Lanes(drum=False);p.u.mem_write(p.g+0xa10,b'\0');p.w(p.g+0x4f4,40) # pitched rows: first visible pitch 40
  p.bank({0:(5,2)},step=3,melodic=[48]);p.surface();p.paint()
  self.assertEqual(p.px(*p.mid(8,5)),GREY);self.assertEqual(p.px(*p.edge(8,3)),BOX);self.assertEqual(p.px(*p.mid(9,5)),BG)
 def test_folded_rows_follow_the_native_layout(self):
  # Device: the one-shot piano roll lists only used pads (+5276 fold, rows at
  # +5278, count +5478, scroll +547C). Pads 1 and 2 (rows 9, 10) become rows 0, 1.
  p=Lanes({1:(6,3),2:(3,1)},step=4);g=p.g
  p.u.mem_write(g+0x5276,b'\x01');p.w(g+0x5278,9);p.w(g+0x527c,10);p.w(g+0x5478,2);p.w(g+0x547c,0)
  # Folded row labels need the full track model; skip only the native background paint.
  p.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:p.ret(0),begin=0x08176d74,end=0x08176d74)
  p.surface();p.u.mem_write(FB,bytes([BG])*(480*1280));p.paint()
  self.assertEqual(p.px(*p.edge(0,4)),BOX);self.assertEqual(p.px(*p.edge(1,1)),BOX) # 4%6, 4%3
  self.assertEqual(p.px(*p.mid(0,6)),GREY);self.assertEqual(p.px(*p.mid(1,3)),GREY)
  self.assertEqual(p.px(*p.mid(ROW(1),8)),BG) # nothing drawn at the unfolded row
 def test_snap_mode_uses_the_step_length_unit(self):
  # Owner: a 3-step lane drew as 3 grid units. With Snap Mode on (+11CD10) one
  # step is round(table[Step Len] x 960) grid ticks; 1/16 = 240.
  p=Lanes({0:(3,1)},step=1);v=p.view;p.w(v+0x11cd10,1);p.w(v+0x11cd14,10);p.surface();p.paint()
  tpc=p.r(p.g+0xa20);x=lambda t:p.colx(t//tpc)+(t-(t//tpc)*tpc)*(p.colx(t//tpc+1)-p.colx(t//tpc))//tpc
  y=(p.rowy(ROW(0))+p.rowy(ROW(0)+1))//2
  self.assertEqual(p.px(x(3*240)+3,y),GREY);self.assertEqual(p.px(x(240)+(0 if 240%tpc else 1),y),BOX) # grey from step 3, box at step 1
if __name__=='__main__':gc.disable();unittest.main(verbosity=2)
