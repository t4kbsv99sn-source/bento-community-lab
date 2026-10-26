"""Render the persistent header with and without the P5 chord symbol.
Native header widgets and paint; the chord mail flag is set in the EuBank."""
import argparse,json,struct
from pathlib import Path
import emu,render
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
e=emu.Emu(str(a.build/'bento1.bin'));render.boot_gfx(e);e.call(0x08180198,render.ROOT)
BANK=0xc0300000;EC=0x24041fc0;BYTES=46080
e.u.mem_write(BANK,bytes(BYTES));e.w(BANK+4,2)
for off,v in [(0,0x324c5545),(4,BANK),(8,BYTES),(12,1)]:e.w(EC+off,v)
a.out.mkdir(parents=True,exist_ok=True)
for name,active in [('header_chord_on',1),('header_chord_off',0)]:
 e.w(BANK+44576,2);e.w(BANK+44576+4,active)
 render.page_reset(e);render.header(e,render.tpl(e,36));render.clear(e);render.paint(e,render.ROOT)
 render.save(e,str(a.out/f'{name}.png'),crop=(0,424,1280,480))
print('root rect',struct.unpack('<4i',e.u.mem_read(render.ROOT+4,16)))
