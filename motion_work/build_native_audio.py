"""Build/validate the native motion module; does NOT produce a tester image.

The M4 recording/editor/persistence producer must exist and be validated before
the module and its call sites may be included in an installation package.
"""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess,sys
ROOT=Path(__file__).resolve().parent
P19='5c657c73e447bf9efe66b5e95336c2f4bf03da5c6ec6a6704db1a10147f23c00'
BASE=0x08040000
# P22b: 080E0000..080FFFFF holds a separate program with its own vector table
# (SP 24029898, reset 080E03C3); our builds never write that sector. Motion M7
# code uses the stock zero gap 080CF4A0..080D0000 below it.
START=0x080cf4a0;END=0x080d0000
def allocated_sections(path):
 b=path.read_bytes();off=struct.unpack_from('<I',b,32)[0];step,count=struct.unpack_from('<HH',b,46)
 result=[]
 for i in range(count):
  s=struct.unpack_from('<10I',b,off+i*step)
  if s[2]&2:result.append((s[3],b[s[4]:s[4]+s[5]]))
 return result
def build(out):
 cmd=[sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabihf',
  '-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp',
  '-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-Oz','-flto','-g','-ffreestanding',
  '-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=motion_native_automation',
  '-Wl,--script='+str(ROOT/'motion_audio.ld'),str(ROOT/'motion_native_audio.c'),
  str(ROOT/'motion_compact.c'),'-o',str(out)]
 subprocess.run(cmd,check=True)
 chunks=allocated_sections(out)
 assert len(chunks)==1 and chunks[0][0]==START
 assert START+len(chunks[0][1])<=END
 return chunks[0][1]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();image=a.baseline.read_bytes()
 assert hashlib.sha256(image).hexdigest()==P19,'exact owner P19 required'
 a.out.mkdir(parents=True,exist_ok=True)
 code=build(a.out/'motion_audio.elf');other=build(a.out/'motion_audio_repeat.elf')
 assert code==other,'independent links must produce identical loaded code'
 assert image[START-BASE:START-BASE+len(code)]==bytes(len(code)),'native zero cave changed'
 callsite=image[0x08062216-BASE:0x0806221a-BASE]
 assert callsite.hex()=='fef713ff','native automation call site changed'
 report={'status':'linked module only; not a flashable tester','p19_sha256':P19,
  'module_address':START,'module_bytes':len(code),'module_sha256':hashlib.sha256(code).hexdigest(),
  'identical_repeat_link':True,'zero_cave_guard':True,'native_callsite_hex':callsite.hex(),
  'firmware_image_modified':False,'controller_modified':False,'bootloader_modified':False}
 (a.out/'NATIVE_MODULE_BUILD.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
