from pathlib import Path
import hashlib,struct,subprocess,sys,json
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
BASE=0x08040000; CODE=0x081bd000
SHA='b067a4889d3c0bce4b9f95705b3d7d8df7eea9a5128c4940b46c29d539fd6294'
def branch(a,b):
 d=b-(a+4);assert d%2==0 and -(1<<24)<=d<(1<<24)
 s=d>>24&1;i1=d>>23&1;i2=d>>22&1
 return struct.pack('<HH',0xf000|(s<<10)|((d>>12)&0x3ff),0x9000|(((~i1^s)&1)<<13)|(((~i2^s)&1)<<11)|((d>>1)&0x7ff))
def build(src,out,expected_sha=SHA):
 original=Path(src).read_bytes();assert hashlib.sha256(original).hexdigest()==expected_sha
 (ROOT/'clean.ld').write_text('SECTIONS { . = 0x081bd000; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-sanitize=all','-fno-stack-protector','-fno-stack-check','-nostdlib','-Wl,--entry=wave_paint','-Wl,--script='+str(ROOT/'clean.ld'),str(ROOT/'clean.c'),'-o',str(ROOT/'clean.elf')],check=True)
 e=(ROOT/'clean.elf').read_bytes();off=struct.unpack_from('<I',e,32)[0];sz,n=struct.unpack_from('<HH',e,46);ss=[struct.unpack_from('<10I',e,off+i*sz) for i in range(n)];alloc=[s for s in ss if s[2]&2];assert len(alloc)==1 and alloc[0][3]==CODE
 symbols={}
 for s in ss:
  if s[1]!=2:continue
  t=ss[s[6]];names=e[t[4]:t[4]+t[5]]
  for i in range(0,s[5],s[9]):
   name,a,_,info,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   if info&15==2:symbols[names[name:].split(b'\0')[0].decode()]=a&~1
 specs=[('wave_paint',0x08183854,bytes.fromhex('2de9f04f')),('envelope_paint',0x08168768,bytes.fromhex('0b7803b9')),('lfo_paint',0x0817ddfc,bytes.fromhex('0b7803b9')),('button_paint',0x0816a97c,bytes.fromhex('f0b589b0')),('label_paint',0x0817e780,bytes.fromhex('00b585b0')),('rect_paint',0x08179120,bytes.fromhex('f0b585b0'))]
 s=alloc[0];payload=e[s[4]:s[4]+s[5]];assert len(payload)<=0x800
 payload+=bytes(0x800-len(payload));ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 for i,(name,address,old) in enumerate(specs):
  assert original[address-BASE:address-BASE+4]==old,(name,original[address-BASE:address-BASE+4].hex())
  at=0x081bd800+i*32
  if i in [1,2]:
   stub=bytes(ks.asm('ldrb r3,[r1]; cbz r3,exit; b.w '+hex(address+6)+'; exit: bx lr',at)[0])
  else:stub=old+branch(at+4,address+4)
  assert len(stub)<=32;payload+=stub+bytes(32-len(stub))
 assert len(original)+BASE<=CODE and CODE+len(payload)<0x081c0000
 b=bytearray(original);records=[]
 def put(a,new,old):
  o=a-BASE;assert bytes(b[o:o+len(old)])==old
  records.append(dict(address=hex(a),old=old.hex(),new=new.hex()));b[o:o+len(old)]=new
 put(BASE+len(b),bytes(CODE-BASE-len(b))+payload,b'')
 for name,address,old in specs:put(address,branch(address,symbols[name]),old)
 put(0x08152144,branch(0x08152144,symbols['clean_refresh']),branch(0x08152144,0x081bb040))
 put(0x0818bad4,b'1.6KG',b'1.6K7')
 assert len(b)%4==0
 assert b[:0xc0000]==original[:0xc0000] # entire audio/disk processor region unchanged
 assert b[0xc0000:0xc0400]==original[0xc0000:0xc0400]
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'bento1.bin').write_bytes(b)
 report=dict(name='K16 synth locks and sample display restore with confirmed direct drawing filters',display='1.6KG',base_sha256=expected_sha,sha256=hashlib.sha256(b).hexdigest(),symbols=symbols,patches=records)
 (out/'manifest.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2)[:700])
