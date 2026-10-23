"""Native UI-thread held-step adapters; exact 1.6.1 only."""
from pathlib import Path
import struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
START=0x081b6600;CODE=0x081b6800

def build():
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=step_match','-Wl,--script='+str(ROOT/'holdstep.ld'),str(ROOT/'holdstep.c'),'-o',str(ROOT/'holdstep.elf')],check=True)
 e=(ROOT/'holdstep.elf').read_bytes();off=struct.unpack_from('<I',e,32)[0];size,n=struct.unpack_from('<HH',e,46)
 ss=[struct.unpack_from('<10I',e,off+i*size) for i in range(n)];alloc=[s for s in ss if s[2]&2]
 if len(alloc)!=1 or alloc[0][3]!=CODE or alloc[0][5]>0x800:raise ValueError('Unexpected hold code layout')
 s=alloc[0];code=e[s[4]:s[4]+s[5]];nameset={'step_press','step_touch','step_match','step_selected','step_edit'};symbols={}
 for s in ss:
  if s[1]!=2:continue
  st=ss[s[6]];tab=e[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   name,v,_,_,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i);name=tab[name:].split(b'\0')[0].decode()
   if name in nameset:symbols[name]=v&~1
 if len(symbols)!=5:raise ValueError('Missing hold functions')
 return code,symbols

def writes_for(stock,append):
 code,syms=build();k=Ks(KS_ARCH_ARM,KS_MODE_THUMB);payload=bytearray();sites=[]
 def asm(src,a):return bytes(k.asm(src,a)[0])
 def block(src):
  while len(payload)%4:payload.append(0)
  a=START+len(payload);payload.extend(asm(src,a));return a
 block('push {r4,lr}; add.w lr,r0,#0x11400; b.w 0x0815b9c6')
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; ldr r0,[sp,#8]; '
 restore='pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 for a,name,extra in [(0x0815d22e,'step_press','ldr r1,[sp,#12]; '),(0x0815d2ea,'step_touch','')]:
  target=block(prefix+extra+'bl '+hex(syms[name])+'; '+restore+'b.w 0x0815c27c')
  sites.append((a,asm('bl '+hex(target),a),stock[a-0x08040000:a-0x08040000+4],'T2 remember inspected native physical/touch step'))
 for a in [0x0815c7c4,0x0815c8ac,0x0815c990]:
  target=block(prefix+'bl '+hex(syms['step_edit'])+'; '+restore+'push.w {r4-r11,lr}; b.w '+hex(a+4))
  sites.append((a,asm('b.w '+hex(target),a),bytes.fromhex('2de9f04f'),'T2 encoder edit suppresses native release toggle'))
 if START+len(payload)>CODE:raise ValueError('Hold wrappers overlap C code')
 payload+=bytes(CODE-START-len(payload))+code+b'BENTO_MOD:step-inspect:0.8.1\0'
 payload+=b'\xff'*(-len(payload)%4)
 sites.append((0x0815b9c0,asm('b.w '+hex(syms['step_match'])+'; nop',0x0815b9c0),bytes.fromhex('10b500f58a3e'),'T2 selected-step matching with native held steps taking priority'))
 sites.append((0x0815bab0,asm('b.w '+hex(syms['step_selected']),0x0815bab0),bytes.fromhex('00f58a30'),'T2 edits use selected inspected hit when no pad is held'))
 return [(append,bytes(START-append)+payload,b'','T2 appended UI-thread step inspection implementation')]+sites
