"""K7 exact native sample-editor hooks; K6 descriptor/audio integration retained."""
from pathlib import Path
import struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
WRAP=0x081bb000;CODE=0x081bb400;SYMS={}
def writes_for(stock,append):
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=kick_ui_before','-Wl,--script='+str(ROOT/'kick_ui.ld'),str(ROOT/'kick_ui.c'),'-o',str(ROOT/'kick_ui.elf')],check=True)
 e=(ROOT/'kick_ui.elf').read_bytes();o=struct.unpack_from('<I',e,32)[0];size,n=struct.unpack_from('<HH',e,46);ss=[struct.unpack_from('<10I',e,o+i*size) for i in range(n)];alloc=[s for s in ss if s[2]&2]
 if len(alloc)!=1 or alloc[0][3]!=CODE or alloc[0][5]>0x3000:raise ValueError('K7 UI layout')
 SYMS.clear()
 for s in ss:
  if s[1]!=2:continue
  t=ss[s[6]];names=e[t[4]:t[4]+t[5]]
  for i in range(0,s[5],s[9]):
   name,a,_,info,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   if info&15==2:SYMS[names[name:].split(b'\0')[0].decode()]=a&~1
 ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 def asm(src,a):return bytes(ks.asm(src,a)[0])
 original=asm('push.w {r4-r11,lr}; b.w 0x08152148',WRAP)
 header=asm('push {r4,lr}; mov r4,r0; bl '+hex(SYMS['kick_ui_before'])+'; mov r0,r4; bl '+hex(WRAP)+'; mov r0,r4; bl '+hex(SYMS['kick_ui_after'])+'; pop {r4,pc}',WRAP+0x40)
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; vpush {d0-d7}; '
 restore='vpop {d0-d7}; pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 event=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(SYMS['kick_ui_event'])+'; cmp r0,#0; beq stock; '+restore+'movs r0,#0; bx lr; stock: '+restore+'push {r4,r5,r6,lr}; sub sp,#0x1e0; b.w 0x08152c54',WRAP+0x100)
 payload=original+bytes(0x40-len(original))+header
 if len(payload)>0x100:raise ValueError('K7 wrapper overlap')
 payload+=bytes(0x80-len(payload))+asm("b.w "+hex(SYMS["drum_ui_step"]),WRAP+0x80)
 payload+=bytes(0x100-len(payload))+event
 if len(payload)>CODE-WRAP or append>WRAP:raise ValueError('K7 append overlap')
 save=asm(prefix+'mov r0,r6; ldr r1,[sp,#72]; bl '+hex(SYMS['kick_ui_save'])+'; '+restore+'mov r8,r0; movs r4,#0; b.w 0x0812f5ee',WRAP+0x200)
 load=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(SYMS['kick_ui_load'])+'; '+restore+'push {r4,r5,r6,r7,lr}; sub sp,#0x14; b.w 0x0812fab0',WRAP+0x300)
 if len(payload)>0x200 or len(save)>0x100 or len(load)>0x100:raise ValueError('K7 XML wrapper overlap')
 payload+=bytes(0x200-len(payload))+save
 payload+=bytes(0x300-len(payload))+load
 s=alloc[0];payload=bytes(WRAP-append)+payload+bytes(CODE-WRAP-len(payload))+e[s[4]:s[4]+s[5]]+b'BENTO_MOD:kick-ui:K7:0.14.0\0'
 payload+=b'\xff'*(-len(payload)%4)
 speed_at=append+len(payload)
 speed=asm(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(SYMS['kick_ui_increment'])+'; str r0,[sp,#76]; '+restore+'push {r4,r5,r6,r7,lr}; sub sp,#0x1c; b.w 0x08171e48',speed_at)
 payload+=speed;payload+=b'\xff'*(-len(payload)%4)
 a=0x08152144;old=stock[a-0x08040000:a-0x08040000+4]
 b=0x08152c50;oldb=stock[b-0x08040000:b-0x08040000+4]
 if old!=bytes.fromhex('2de9f04f') or oldb!=bytes.fromhex('70b5f8b0'):raise ValueError('K7 native header/event prologue changed')
 save_a=0x0812f5ea;save_old=stock[save_a-0x08040000:save_a-0x08040000+4]
 load_a=0x0812faac;load_old=stock[load_a-0x08040000:load_a-0x08040000+4]
 if save_old!=bytes.fromhex('80460024') or load_old!=bytes.fromhex('f0b585b0'):raise ValueError('K7 XML original instructions changed')
 writes=[(append,payload,b'','K7 native kick instrument editor'),(save_a,asm('b.w '+hex(WRAP+0x200),save_a),save_old,'K7 versioned kick attributes on native pad params save'),(load_a,asm('b.w '+hex(WRAP+0x300),load_a),load_old,'K7 restore kick attributes before native pad params load'),(a,asm('b.w '+hex(WRAP+0x40),a),old,'K7 custom kick rows around original sample-editor refresh'),(b,asm('b.w '+hex(WRAP+0x100),b),oldb,'K7 synth encoder/pad/load events with ordinary-sample fallback')]

 speed_old=stock[0x08171e44-0x08040000:0x08171e48-0x08040000]
 if speed_old!=bytes.fromhex('f0b587b0'):raise ValueError('Native encoder prologue changed')
 writes.append((0x08171e44,asm('b.w '+hex(speed_at),0x08171e44),speed_old,'K15 fivefold custom synth encoder response'))
 return writes
