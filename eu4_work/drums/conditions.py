"""Exact-1.6.1 native condition hook and on-screen enum extension."""
from pathlib import Path
import struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
GATE=0x080d2000;LOOP=0x080d2100;CODE=0x080d2400
UI=0x081b5800;TABLE=0x081b6000
STATE=0x24048a60
LABELS=[f'{a}:{b}' for b in range(2,9) for a in range(1,b+1)]

def compile_conditions():
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m7','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=condition_decide','-Wl,--script='+str(ROOT/'conditions.ld'),str(ROOT/'conditions.c'),'-o',str(ROOT/'conditions.elf')],check=True)
 e=(ROOT/'conditions.elf').read_bytes();o=struct.unpack_from('<I',e,32)[0];size,n=struct.unpack_from('<HH',e,46)
 ss=[struct.unpack_from('<10I',e,o+i*size) for i in range(n)];alloc=[s for s in ss if s[2]&2]
 if len(alloc)!=1 or alloc[0][3]!=CODE or alloc[0][5]>0xb00:raise ValueError('Unexpected condition code layout')
 s=alloc[0];code=e[s[4]:s[4]+s[5]];symbols={}
 for s in ss:
  if s[1]!=2:continue
  st=ss[s[6]];names=e[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   off,value,_,_,_,_=struct.unpack_from('<IIIBBH',e,s[4]+i)
   name=names[off:].split(b'\0')[0].decode()
   if name in ['condition_loop','condition_decide']:symbols[name]=value&~1
 if len(symbols)!=2:raise ValueError('Missing condition functions')
 return code,symbols

def writes_for(stock,append):
 k=Ks(KS_ARCH_ARM,KS_MODE_THUMB);out=[]
 def asm(src,a):return bytes(k.asm(src,a)[0])
 def add(a,data,old=None,reason='T2 native conditions'):
  if old is None:old=stock[a-0x08040000:a-0x08040000+len(data)]
  out.append((a,data,old,reason))
 def restore():return 'pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 code,sym=compile_conditions()
 prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; '
 gate=asm(prefix+'mov r0,r8; ldrb.w r1,[sp,#105]; bl '+hex(sym['condition_decide'])+'''; cmp r0,#0; beq skip; cmp r0,#1; beq play;
 '''+restore()+'''ldrb.w r3,[sp,#0x29]; b.w 0x08060b68;
 play: '''+restore()+'''movs r3,#0; b.w 0x08060b68;
 skip: '''+restore()+'''b.w 0x080609e2''',GATE)
 if len(gate)>0x100:raise ValueError('Gate overlap')
 loop=asm(prefix+'ldr r0,[sp,#8]; bl '+hex(sym['condition_loop'])+'; '+restore()+'push.w {r4-r8,r9,lr}; b.w 0x08061744',LOOP)
 for a,data in [(GATE,gate),(LOOP,loop),(CODE,code)]:
  if any(stock[a-0x08040000:a-0x08040000+len(data)]):raise ValueError('Condition code cave is not zero')
  add(a,data,bytes(len(data)))
 for a,target,old in [(0x08060b64,GATE,'9df82930'),(0x08061740,LOOP,'2de9f043')]:add(a,asm('b.w '+hex(target),a),bytes.fromhex(old))
 helpers=bytearray();symbols={}
 def helper(name,src):
  while len(helpers)%4:helpers.append(0)
  a=UI+len(helpers);symbols[name]=a;helpers.extend(asm(src,a));return a
 def show(store,back):
  return f'cmp r3,#100; blo dec; cmp r3,#134; bls store; movs r3,#99; b store; dec: subs r3,#1; store: str r3,[{store}]; b.w {back}'
 helper('show_piano',show('r6','0x08159b84'))
 helper('show_drum',show('r1','0x0815c3d6'))
 helper('set_drum','''cmp r1,#134; bhi unknown; cmp r1,#100; bhs direct; cmp r1,#99; beq unknown; adds r6,r1,#1; b done; direct: mov r6,r1; b done; unknown: movs r6,#0; done: b.w 0x0815c8be''')
 helper('piano_reference','''ldrb.w r3,[sp,#0x25]; cbz r3,always; cmp r3,#135; bhs always; cmp r3,#100; blo done; adds r3,#1; b done; always: movs r3,#100; done: b.w 0x08158f26''')
 helper('piano_edit','''ldrb.w r3,[sp,#0x19]; cbz r3,always; cmp r3,#135; bhs always; cmp r3,#100; blo add; adds r3,#1; b add; always: movs r3,#100; add: ldr r2,[sp,#0x84]; adds r3,r3,r2; cmp r3,#1; bge minok; movs r3,#1; minok: cmp r3,#135; ble maxok; movs r3,#135; maxok: cmp r3,#100; beq zero; blo store; subs r3,#1; b store; zero: movs r3,#0; store: strb.w r3,[sp,#0x31]; b.w 0x08158aac''')
 if UI+len(helpers)>TABLE:raise ValueError('UI helper overlap')
 ptrs=bytearray(stock[0x0819f30c-0x08040000:0x0819f30c-0x08040000+400]);labels=bytearray()
 for name in LABELS:
  ptrs+=struct.pack('<I',TABLE+135*4+len(labels));labels+=name.encode()+b'\0'
 data=bytes(UI-append)+helpers+bytes(TABLE-UI-len(helpers))+ptrs+labels+b'BENTO_MOD:trigger-conditions:0.8.1\0'
 data+=b'\xff'*(-len(data)%4)
 add(append,bytes(data),b'','T2 appended native enum labels and editor adapters')
 for a,name,old in [(0x08159b80,'show_piano','013b3360'),(0x0815c3d2,'show_drum','013b0b60'),(0x0815c8b4,'set_drum','63291abf'),(0x08158f1c,'piano_reference','9df82530'),(0x08158a7c,'piano_edit','9df81930')]:add(a,asm('b.w '+hex(symbols[name]),a),bytes.fromhex(old),'T2 condition UI value conversion')
 add(0x08165d40,asm('movs r3,#135; str r3,[sp]',0x08165d40),bytes.fromhex('cdf80080'),'T2 extend native condition list count without changing other fields')
 add(0x08165f8c,struct.pack('<I',TABLE),struct.pack('<I',0x0819f30c),'T2 native on-screen probability/condition labels')
 return out
