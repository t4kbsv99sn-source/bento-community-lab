"""L3 native spare-encoder, note XML and per-voice lock integration."""
from pathlib import Path
import struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
AUDIO=0x080d3400;UI=0x081b7400;WRAP=0x081b7000

def compile_one(name,cpu,hard):
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabihf' if hard else 'thumb-freestanding-eabi','-mcpu='+cpu,'-mfloat-abi='+('hard' if hard else 'soft'),'-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry='+('edited_evaluate' if hard else 'locks_header_before'),'-Wl,--script='+str(ROOT/(name+'.ld')),str(ROOT/(name+'.c')),'-o',str(ROOT/(name+'.elf'))],check=True)
 e=(ROOT/(name+'.elf')).read_bytes();o=struct.unpack_from('<I',e,32)[0];size,n=struct.unpack_from('<HH',e,46)
 ss=[struct.unpack_from('<10I',e,o+i*size) for i in range(n)];alloc=[s for s in ss if s[2]&2]
 pieces=[(s[3],e[s[4]:s[4]+s[5]]) for s in alloc];syms={}
 for s in ss:
  if s[1]!=2:continue
  names=ss[s[6]];tab=e[names[4]:names[4]+names[5]]
  for i in range(0,s[5],s[9]):
   off,value,_,info,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   if info&15==2:syms[tab[off:].split(b'\0')[0].decode()]=value&~1
 return pieces,syms

def writes_for(stock,append):
 k=Ks(KS_ARCH_ARM,KS_MODE_THUMB);writes=[]
 def asm(s,a):return bytes(k.asm(s,a)[0])
 global A_SYMS,U_SYMS
 ap,asym=compile_one('step_lock_audio','cortex_m7',True)
 up,usym=compile_one('step_lock_ui','cortex_m4',False)
 A_SYMS,U_SYMS=asym,usym
 if len(ap)!=1 or ap[0][0]!=AUDIO or len(ap[0][1])>0x2000:raise ValueError('Audio lock layout')
 if len(up)!=5 or up[0][0]!=UI or up[0][0]+len(up[0][1])>up[1][0] or up[1][0]!=0x081b8c00:raise ValueError('UI lock layout')
 if up[-1][0]+len(up[-1][1])>0x081ba000:raise ValueError('UI constants overlap installer')
 for a,data in ap:writes.append((a,data,bytes(len(data)),'L3 M7 voice-owned lock implementation'))
 def original(a,n):return stock[a-0x08040000:a-0x08040000+n]
 def site(a,target,n=4,call=False):
  code=asm(('bl ' if call else 'b.w ')+hex(target),a)
  if n>4:code+=asm('nop',a+4)
  writes.append((a,code,original(a,n),'L3 exact-version native integration'))
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; '
 restore='pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 audio=bytearray()
 def ablock(s):
  while len(audio)%4:audio.append(0)
  a=0x080d3000+len(audio);audio.extend(asm(s,a));return a
 target=ablock(prefix+'ldr r0,[sp,#124]; bl '+hex(asym['lock_pending'])+'; ldr r0,[sp,#8]; ldr r1,[sp,#68]; ldr r2,[sp,#64]; bl '+hex(asym['lock_route'])+'; '+restore+'bl 0x0805f8e0; '+prefix+'movs r0,#0; bl '+hex(asym['lock_pending'])+'; '+restore+'b.w 0x08060b9e')
 site(0x08060b9a,target)
 target=ablock(prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(asym['lock_queue'])+'; '+restore+'ldr.w r3,[r0,#0x600]; b.w 0x08065604')
 site(0x08065600,target)
 target=ablock(prefix+'mov r0,r4; add r1,sp,#104; bl '+hex(asym['lock_note'])+'; '+restore+'ldrb.w r3,[sp,#0x28]; b.w 0x0808e9f4')
 site(0x0808e9f0,target)
 for a,displaced,nexta in [(0x08093cda,'ldrb.w r3,[r5,#0x625]',0x08093cde),(0x08094ade,'vldr s15,[r5,#0x104]',0x08094ae2)]:
  target=ablock(prefix+'vpush {d0-d7}; mov r0,r4; mov r1,r5; bl '+hex(asym['lock_voice'])+'; mov r0,r4; mov r1,r5; bl 0x080d5800; vpop {d0-d7}; '+restore+displaced+'; b.w '+hex(nexta))
  site(a,target)
 for a,name,replay,nexta in [(0x0808fc40,'sends_begin','addw r8,r5,#0xe1c',0x0808fc44),(0x0808ed22,'sends_end','movs r0,#1; add sp,#0x44',0x0808ed26),(0x0808fcc2,'sends_end','movs r0,#1; add sp,#0x44',0x0808fcc6)]:
  target=ablock(prefix+'vpush {d0-d7}; mov r0,r4; bl '+hex(asym[name])+'; vpop {d0-d7}; '+restore+replay+'; b.w '+hex(nexta));site(a,target)
 if len(audio)>0x3c0:raise ValueError('Audio wrappers overlap native send gain adapter')
 gain=asm('push {r4,lr}; vmov s0,r0; vcvt.f32.s32 s0,s0; vldr s1,divisor; vdiv.f32 s0,s0,s1; bl 0x080503e0; vmov r0,s0; pop {r4,pc}; .align 2; divisor: .word 0x447a0000',0x080d33c0)
 audio+=bytes(0x3c0-len(audio))+gain
 if len(audio)>0x400:raise ValueError('Audio lock wrappers overlap code')
 writes.append((0x080d3000,bytes(audio),bytes(len(audio)),'L3 M7 accepted-note queue and voice adapters'))
 ui=bytearray()
 def ublock(s):
  while len(ui)%4:ui.append(0)
  a=WRAP+len(ui);ui.extend(asm(s,a));return a
 orig=ublock('push.w {r4-r8,r9,lr}; b.w 0x0815c280')
 target=ublock('push {r4,lr}; mov r4,r0; bl '+hex(usym['locks_header_before'])+'; mov r0,r4; bl '+hex(orig)+'; mov r0,r4; bl '+hex(usym['locks_header_after'])+'; pop {r4,pc}')
 site(0x0815c27c,target)
 target=ublock(prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; ldr r2,[sp,#16]; bl '+hex(usym['locks_encoder'])+'; cmp r0,#0; beq fallback; '+restore+'movs r0,#0; bx lr; fallback: '+restore+'add.w r3,r0,#0x11000; b.w 0x0815caa4')
 site(0x0815caa0,target)
 for a,name,offset,displaced,nexta in [(0x0812f4f0,'locks_save',8,'ldrb.w r3,[sp,#8]',0x0812f4f4),(0x0812fbb4,'locks_load',0x24,'add r1,sp,#0x24; ldr r0,[sp,#0x3c]',0x0812fbb8)]:
  target=ublock(prefix+'mov r0,r4; add r1,sp,#'+str(64+offset)+'; bl '+hex(usym[name])+'; '+restore+displaced+'; b.w '+hex(nexta))
  site(a,target)
 target=ublock(prefix+'ldr r0,[sp,#8]; bl '+hex(usym['seq_lights_clean'])+'; '+restore+'bx lr')
 site(0x0813c3f0,target)
 if WRAP+len(ui)>UI:raise ValueError('UI wrapper overlap')
 ui+=bytes(UI-WRAP-len(ui))
 for a,data in up:
  ui+=bytes(a-WRAP-len(ui))+data
 ui+=b'BENTO_MOD:editable-step-locks:0.13.0\0';ui+=b'\xff'*(-len(ui)%4)
 if append>WRAP:raise ValueError('UI append overlap')
 writes.append((append,bytes(WRAP-append)+bytes(ui),b'','L3 appended native encoder and note XML adapters'))
 return writes
