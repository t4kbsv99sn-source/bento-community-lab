"""Render the native persistent header of a Bento main image to PNG.

Uses the firmware's own widget, text and fill code under Unicorn; only the
DMA2D peripheral is emulated (dma2d.py). No device access, no flashing.

  python research/display_emulator/render_headers.py --image bento1.bin --out shots/
writes stock_template_<page>.png for the SEQ templates and, for images that
contain seq_toolbar (EU9+/CH1+), drum_late.png / piano_late.png where the custom
view state becomes ready one tick after page navigation (the hardware case).
"""
import argparse,os,sys
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import emu,render
from scenario import World
p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--out',required=True);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
e=emu.Emu(a.image);render.boot_gfx(e);e.call(0x08180198,render.ROOT)
for index,page in [(36,0x27),(8,0x17),(20,0x1a)]:
    render.page_reset(e);render.header(e,render.tpl(e,index));render.clear(e);render.paint(e,render.ROOT)
    render.save(e,str(out/f'stock_template_{page:02x}.png'),crop=(0,424,1280,480))
image=open(a.image,'rb').read()
if len(image)>1523516:  # patched image with UI cave (CH1 or later layout)
    for kind in ['drum','piano']:
        w=World(a.image,kind);w.navigate(36,0x27);w.tick();w.ready();w.tick();w.tick()
        w.shot(str(out/f'{kind}_late.png'));print(kind,w.buttons())
print('wrote',out)
