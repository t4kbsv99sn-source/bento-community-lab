"""K2 UI-thread kick-entry installation, using the stock filesystem API."""
from pathlib import Path
import subprocess,sys,struct
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
WRAP=0x081ba000;CODE=0x081ba200;SYMS={}
def writes_for(stock,append):
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=kick_load_entry','-Wl,--script='+str(ROOT/'kick_install.ld'),str(ROOT/'kick_install.c'),'-o',str(ROOT/'kick_install.elf')],check=True)
 e=(ROOT/'kick_install.elf').read_bytes();off=struct.unpack_from('<I',e,32)[0];size,count=struct.unpack_from('<HH',e,46)
 ss=[struct.unpack_from('<10I',e,off+i*size) for i in range(count)];alloc=[s for s in ss if s[2]&2]
 if len(alloc)!=1 or alloc[0][3]!=CODE or alloc[0][5]>0xf00:raise ValueError('K2 installer layout')
 SYMS.clear()
 for s in ss:
  if s[1]!=2:continue
  tab=ss[s[6]];names=e[tab[4]:tab[4]+tab[5]]
  for i in range(0,s[5],s[9]):
   name,a,_,info,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   if info&15==2:SYMS[names[name:].split(b'\0')[0].decode()]=a&~1
 ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 def asm(s,a):return bytes(ks.asm(s,a)[0])
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; vpush {d0-d7}; '
 restore='vpop {d0-d7}; pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 wrap=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(SYMS['kick_load_entry'])+'; '+restore+'push {r4,r5,r6,lr}; sub sp,#0x28; b.w 0x081512a8',WRAP)
 if len(wrap)>0x80:raise ValueError('Load wrapper overlap')
 sample=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; ldr r2,[sp,#80]; ldr r3,[sp,#84]; bl '+hex(SYMS['kick_sample_loading'])+'; '+restore+'push.w {r4-r10,lr}; b.w 0x0810e0bc',WRAP+0x80)
 if len(sample)>0x80:raise ValueError('Sample wrapper overlap')
 wrap+=bytes(0x80-len(wrap))+sample
 eager=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; ldr r2,[sp,#80]; ldr r3,[sp,#84]; bl '+hex(SYMS['kick_sample_loading'])+'; '+restore+'push.w {r4-r11,lr}; b.w 0x0810dff8',WRAP+0x100)
 wrap+=bytes(0x100-len(wrap))+eager
 if len(wrap)>0x1c0:raise ValueError('Installer endpoint overlap')
 wrap+=bytes(0x1c0-len(wrap))+asm('b.w '+hex(SYMS['kick_install']),WRAP+0x1c0)
 if append>WRAP or WRAP+len(wrap)>CODE:raise ValueError('K2 installer overlap')
 s=alloc[0];code=e[s[4]:s[4]+s[5]]
 payload=bytes(WRAP-append)+wrap+bytes(CODE-WRAP-len(wrap))+code+b'BENTO_MOD:kick-entry:K7\0'
 payload+=b'\xff'*(-len(payload)%4)
 old=stock[0x081512a4-0x08040000:0x081512a8-0x08040000]
 if old!=bytes.fromhex('70b58ab0'):raise ValueError('K2 Load entry original changed')
 native=stock[0x0810e0b8-0x08040000:0x0810e0bc-0x08040000]
 if native!=bytes.fromhex('2de9f047'):raise ValueError('K7 sample-loader entry original changed')
 eager_old=stock[0x0810dff4-0x08040000:0x0810dff8-0x08040000]
 if eager_old!=bytes.fromhex('2de9f04f'):raise ValueError('K7 eager sample-loader original changed')
 return [(append,payload,b'','K7 automatic kick entry and native loader diagnostics'),(0x081512a4,asm('b.w '+hex(WRAP),0x081512a4),old,'Prepare built-in kick entry before native one-shot Load'),(0x0810e0b8,asm('b.w '+hex(WRAP+0x80),0x0810e0b8),native,'K7 record native file loading on sample load, including project reload'),(0x0810dff4,asm('b.w '+hex(WRAP+0x100),0x0810dff4),eager_old,'K7 record native file loading on eager sample load')]
