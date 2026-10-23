"""Render the CH6 piano-roll lanes (one-shot track) with the real grid code.
Run from a CH6 build workspace's chord_work directory (needs the test fixtures):
  python ../research/display_emulator/render_lanes.py out.png"""
import sys,struct
from test_lanes import Lanes,ROW
from test_euclidean import note
import render
def euclid(n,k,rot=0):return [s for s in range(n) if ((((s+n-rot)%n)*k)%n)<k]
lanes={0:(6,3),1:(16,4),2:(3,1),3:(5,2)}
notes=[];i=100
for pad,(n,k) in lanes.items():
 for s in euclid(n,k):notes.append(note(s,pad=pad,ident=i));i+=1
p=Lanes(lanes,step=int(sys.argv[2]) if len(sys.argv)>2 else 7,notes=notes);p.surface();p.paint()
class E:pass
e=E();e.u=p.u;render.FB=0xc1000000;render.save(e,sys.argv[1],crop=(0,40,1280,430))
