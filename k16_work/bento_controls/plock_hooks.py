"""Build M7 hooks from exact stock bytes. Only application code/state changes."""
from pathlib import Path
import struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
COMMAND=0x080d1000;SEQUENCE=0x080d1080;EVALUATE=0x080d1100;ORIGINAL=0x080d1f00
LOCK_STATE=0x24048c60

def payloads():
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7','-mfloat-abi=hard','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=lock_command','-Wl,--script='+str(ROOT/'plock.ld'),str(ROOT/'plock.c'),'-o',str(ROOT/'plock.elf')],check=True)
 elf=(ROOT/'plock.elf').read_bytes();off=struct.unpack_from('<I',elf,32)[0];size,count=struct.unpack_from('<HH',elf,46)
 sections=[struct.unpack_from('<10I',elf,off+i*size) for i in range(count)]
 names=sections[struct.unpack_from('<H',elf,50)[0]];strings=elf[names[4]:names[4]+names[5]]
 def sname(s):return strings[s[0]:].split(b'\0')[0]
 allocated=[s for s in sections if s[2]&2]
 if len(allocated)!=1 or allocated[0][3]!=0x080d1400:raise ValueError('Unexpected M7 section layout')
 text=allocated[0];code=elf[text[4]:text[4]+text[5]]
 if len(code)>0xb00:raise ValueError('M7 code exceeds reserved cave')
 symbols={}
 for s in sections:
  if s[1]!=2:continue
  st=sections[s[6]];tab=elf[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   n,v,sz,info,other,sh=struct.unpack_from('<IIIBBH',elf,s[4]+i)
   name=tab[n:].split(b'\0')[0].decode()
   if name in ['lock_command','lock_sequence','lock_evaluate']:symbols[name]=v
 if len(symbols)!=3:raise ValueError('Missing M7 functions')
 k=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 def asm(s,a):return bytes(k.asm(s,a)[0])
 # Preserve original-loop registers/flags; record lives at old SP+0x28.
 command=asm('''push.w {r0-r12, lr}
 mrs r0, APSR
 push {r0,r1}
 mov r0,r4
 add r1,sp,#104
 bl %s
 cmp r0,#0
 bne used
 pop {r0,r1}
 msr APSR_nzcvq,r0
 pop.w {r0-r12,lr}
 ldr r2,[sp,#0x34]
 uxth r3,r2
 b.w 0x0808f3a0
 used:
 pop {r0,r1}
 msr APSR_nzcvq,r0
 pop.w {r0-r12,lr}
 b.w 0x0808e9e0'''%hex(symbols['lock_command']&~1),COMMAND)
 sequence=asm('''push.w {r0-r12,lr}
 mrs r1,APSR
 push {r1,r2}
 bl %s
 pop {r1,r2}
 msr APSR_nzcvq,r1
 pop.w {r0-r12,lr}
 ldrb.w r3,[r0,#0x20]
 b.w 0x08061044'''%hex(symbols['lock_sequence']&~1),SEQUENCE)
 # Other parameters go straight back to native code, avoiding a C stack frame.
 # Native evaluator preserves R12 and S1-S12 despite the public ABI allowing
 # a C callee to destroy them. Preserve its private contract around added C.
 save='push.w {r0-r3,r12,lr}; vpush {d0-d7}; '
 done='vpop {d0-d7}; pop.w {r0-r3,r12,lr}; '
 evaluate=asm('ldr r1,=0x24046000; ldr r2,[r1,#16]; cbz r2,legacy; '+save+'bl 0x080d3400; cmp r0,#0; '+done+'beq legacy; vldr s0,[r0,#0x3c]; bx lr; legacy: ldr r1,=0x24048c60; ldr r2,[r1,#4]; cbz r2,native; ldr r2,[r1,#12]; cbz r2,native; ldr r2,[r2]; cbz r2,native; ldr r3,[r0]; cmp r3,r2; bne native; '+save+'bl '+hex(symbols['lock_evaluate']&~1)+'; cmp r0,#0; '+done+'beq native; vldr s0,[r0,#0x3c]; bx lr; native: b.w 0x080d1f00',EVALUATE)
 original=bytes.fromhex('036b002b')+asm('b.w 0x0809fd84',ORIGINAL+4)
 if len(command)>0x80 or len(sequence)>0x80:raise ValueError('M7 wrapper overlap')
 return [(COMMAND,command),(SEQUENCE,sequence),(EVALUATE,evaluate),(0x080d1400,code),(ORIGINAL,original)],symbols
