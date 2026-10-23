"""Compile the MIT DaisySP engine and exact-version native adapters."""
from pathlib import Path
import subprocess,sys,struct
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
CODE=0x080d6000;WRAP=0x080d5800
SYMS={}
def compile_kick():
 v=ROOT/'vendor/daisysp/Source'
 subprocess.run([sys.executable,'-m','ziglang','c++','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp','-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-Oz','-g','-fno-exceptions','-fno-rtti','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-nostdlib++','-I'+str(ROOT/'kick_support'),'-I'+str(v),'-I'+str(v/'Utility'),'-Wl,--entry=kick_render','-Wl,--script='+str(ROOT/'kick.ld'),str(ROOT/'kick.cpp'),str(v/'Drums/synthbassdrum.cpp'),str(v/'Drums/synthsnaredrum.cpp'),str(v/'Drums/hihat.cpp'),str(v/'Filters/svf.cpp'),'-o',str(ROOT/'kick.elf')],check=True)
 e=(ROOT/'kick.elf').read_bytes();o=struct.unpack_from('<I',e,32)[0];size,n=struct.unpack_from('<HH',e,46);ss=[struct.unpack_from('<10I',e,o+i*size) for i in range(n)]
 alloc=[s for s in ss if s[2]&2]
 if len(alloc)!=1 or alloc[0][3]!=CODE or alloc[0][5]>0x6000:raise ValueError('Kick code layout')
 global SYMS
 SYMS.clear()
 for s in ss:
  if s[1]!=2:continue
  tab=ss[s[6]];names=e[tab[4]:tab[4]+tab[5]]
  for i in range(0,s[5],s[9]):
   off,a,_,info,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   if info&15==2:SYMS[names[off:].split(b'\0')[0].decode()]=a&~1
 s=alloc[0];return e[s[4]:s[4]+s[5]]
def writes_for(stock,append):
 code=compile_kick();k=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 def asm(s,a):return bytes(k.asm(s,a)[0])
 # Fixed endpoint called from existing voice hook. Entry 9480 adapts native VFP pitch.
 voice=asm('b.w '+hex(SYMS['kick_voice']),WRAP)
 pitch=asm('push {r4,r5,r6,lr}; vpush {d8}; mov r4,r0; mov r5,r1; add.w r0,r5,#0x300; bl 0x0809fd80; vldr s16,[r4,#0x104]; vcvt.f32.s32 s16,s16; vldr s1,scale; vmul.f32 s16,s16,s1; vadd.f32 s0,s0,s16; bl 0x080518a0; vldr s1,[r5,#0x48]; vmul.f32 s0,s0,s1; vmov r0,s0; vpop {d8}; pop {r4,r5,r6,pc}; .align 2; scale: .word 0x38aec33e',0x080d5880)
 start=0x080d5900
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; vpush {d0-d7}; '
 restore='vpop {d0-d7}; pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 wrap=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; ldr r2,[sp,#128]; ldr r3,[sp,#132]; bl '+hex(SYMS['kick_render'])+'; cmp r0,#0; beq stock; '+restore+'movs r0,#1; bx lr; stock: '+restore+'push.w {r4-r11,lr}; b.w 0x08091824',start)
 payload=voice+bytes(0x80-len(voice))+pitch
 if len(payload)>0xf0:raise ValueError('Pitch adapter overlaps K7 assignment endpoint')
 payload+=bytes(0xf0-len(payload))+asm('b.w '+hex(SYMS['kick_enable']),WRAP+0xf0)
 payload+=asm('b.w '+hex(SYMS['kick_command_probe']),WRAP+0xf4)
 payload+=bytes(0x100-len(payload))+wrap
 if WRAP+len(payload)>CODE:raise ValueError('Kick append overlap')
 payload+=bytes(CODE-WRAP-len(payload))+code
 payload+=b"BENTO_MOD:daisy-kick:0.14.0:K7\0"
 payload+=b"\xff"*(-len(payload)%4)
 return [(WRAP,payload,bytes(len(payload)),'K7 live DaisySP kick in verified-zero M7 application cave'),(0x08091820,asm('b.w '+hex(start),0x08091820),stock[0x08091820-0x08040000:0x08091824-0x08040000],'K7 native per-voice render entry; original path on ordinary samples')]
