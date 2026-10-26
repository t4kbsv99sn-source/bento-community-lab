"""Compile standalone host/ARM composition engine. Does NOT patch a firmware."""
from pathlib import Path
import subprocess,sys,argparse,json
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--origin',type=lambda x:int(x,0),default=0x081e0000);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-shared','-fPIC',str(R/'chords.c'),str(R/'audition.c'),'-o',str(out/'chords.so')],check=True)
ld=out/'chord.ld';ld.write_text('SECTIONS { . = '+hex(a.origin)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }\n')
subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=chord_generate','-Wl,--script='+str(ld),str(R/'chords.c'),str(R/'native_insert.c'),str(R/'audition.c'),'-o',str(out/'chords.elf')],check=True)
sys.path.insert(0,str(R.parent/'eu4_work/integration'));from build_fx import elf
chunks,syms=elf(out/'chords.elf');assert len(chunks)==1 and chunks[0][0]==a.origin
(out/'chords.bin').write_bytes(chunks[0][1]);(out/'symbols.json').write_text(json.dumps(syms,indent=2)+'\n')
print('Standalone ARM engine:',len(chunks[0][1]),'bytes. No firmware hooks installed.')
