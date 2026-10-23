"""Hash-guarded TF2 Track FX extension on the exact K16 build. No bootloader."""
from pathlib import Path
import struct,sys,subprocess,hashlib,json
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
R=Path(__file__).resolve().parent
BASE=0x08040000;AUDIO=0x080dc800;UI=0x081c0800
K16_SHA='5e72971b31388201454a71b0be7cc61ad40915bda3a75e635d104dd89346a03d'
def elf(path):
 b=path.read_bytes();off=struct.unpack_from('<I',b,32)[0];step,n=struct.unpack_from('<HH',b,46);ss=[struct.unpack_from('<10I',b,off+i*step) for i in range(n)];chunks=[];syms={}
 for s in ss:
  if s[2]&2:chunks.append((s[3],b[s[4]:s[4]+s[5]]))
  if s[1]!=2:continue
  st=ss[s[6]];tab=b[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   name,value,size,info,_,idx=struct.unpack_from('<IIIBBH',b,s[4]+i)
   if info&15==2:syms[tab[name:].split(b'\0')[0].decode()]=value&~1
 return chunks,syms
def compile():
 t=R.parent/'track_fx';v=t/'vendor/DaisySP-LGPL'
 common=[sys.executable,'-m','ziglang','c++','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp','-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-std=c++17','-Oz','-g','-ffreestanding','-fno-builtin','-fno-exceptions','-fno-rtti','-fno-stack-protector','-nostdlib','-nostdlib++','-I'+str(t/'arm_support'),'-I'+str(v),'-I'+str(v/'Utility')]
 sources=[R/'fx_audio.cpp',t/'track_fx.cpp',v/'Source/Dynamics/compressor.cpp',v/'Source/Filters/biquad.cpp',t/'arm_support/math_runtime.cpp']
 subprocess.run([*common,'-Wl,--entry=fx_audio','-Wl,--script='+str(R/'audio.ld'),*map(str,sources),'-o',str(R/'audio.elf')],check=True)
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=fx_dispatch','-Wl,--script='+str(R/'ui.ld'),str(R/'fx_ui.c'),'-o',str(R/'ui.elf')],check=True)
 ac,aa=elf(R/'audio.elf');uc,uu=elf(R/'ui.elf')
 assert len(ac)==len(uc)==1 and ac[0][0]==AUDIO and uc[0][0]==UI
 assert AUDIO+len(ac[0][1])<=0x080e0000 and UI+len(uc[0][1])<=0x081c4000
 return ac[0][1],aa,uc[0][1],uu
def build(base):
 if hashlib.sha256(base).hexdigest()!=K16_SHA:raise ValueError('Expected exact K16 base')
 ac,aa,uc,uu=compile();k=Ks(KS_ARCH_ARM,KS_MODE_THUMB);writes=[];image=bytearray(base)
 def asm(s,a):return bytes(k.asm(s,a)[0])
 def put(a,b,why):
  off=a-BASE;assert a>=BASE and a+len(b)<=0x08200000
  if any(a<x['address']+x['size'] and x['address']<a+len(b) for x in writes):raise ValueError('Patch overlap')
  old=bytes(image[off:off+len(b)]);assert off<=len(image)
  image[off:off+len(b)]=b;writes.append(dict(address=a,size=len(b),original_hex=old.hex(),replacement_hex=b.hex(),reason=why))
 integer_prefix='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; '
 integer_restore='pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 prefix=integer_prefix+'vpush {d0-d7}; '
 restore='vpop {d0-d7}; pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 aw=bytearray()
 def ab(s):
  while len(aw)%4:aw.append(0)
  a=0x080dc000+len(aw);aw.extend(asm(s,a));return a
 a=ab(prefix+'mov r0,r9; mov r1,r4; mov r2,r10; mov r3,r5; bl '+hex(aa['fx_audio'])+'; '+restore+'vldr s15,[r5]; b.w 0x080a0514')
 assert base[0x080a0510-BASE:0x080a0514-BASE]==bytes.fromhex('d5ed007a')
 put(0x080a0510,asm('b.w '+hex(a),0x080a0510),'TF2 per-track scratch after native Level, before pan and sends')
 # Startup initialization remains separate for both core owners.
 a=ab(integer_prefix+'ldr r0,=0x24040000; movs r1,#0; movw r2,#1296; zero: str r1,[r0],#4; subs r2,#1; bne zero; ldr r0,=0x240416c0; movw r2,#208; meta: str r1,[r0],#4; subs r2,#1; bne meta; dsb; '+integer_restore+'b.w 0x080d0800')
 put(0x080404b6,asm('b.w '+hex(a),0x080404b6),'Initialize new M7-owned FX memory, then original K16 startup')
 assert len(aw)<=0x800
 payload=bytes(aw)+bytes(0x800-len(aw))+ac
 assert base[0x080dc000-BASE:0x080dc000-BASE+len(payload)]==bytes(len(payload))
 put(0x080dc000,payload,'TF2 M7 code and exact-version adapters in zero application cave')
 uw=bytearray()
 def ub(s):
  while len(uw)%4:uw.append(0)
  a=0x081c0000+len(uw);uw.extend(asm(s,a));return a
 def site(a,s,reason,n=4):put(a,asm(s,a)+asm('nop',a+4)*(n==6),reason)
 a=ub(integer_prefix+'mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(uu['fx_dispatch'])+'; cmp r0,#0; beq old; '+integer_restore+'b.w 0x0813f2fc; old: '+integer_restore+'b.w 0x081b3f40')
 site(0x0813f98c,'b.w '+hex(a),'TF2 Double-tap TRACKS shortcut before unchanged K16 consumer')
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['fx_nav'])+'; '+integer_restore+'push.w {r4-r8,lr}; b.w 0x081420f0')
 site(0x081420ec,'b.w '+hex(a),'Leave custom mode on ordinary navigation')
 a=ub(integer_prefix+'sub sp,#8; ldr r12,[sp,#68]; str r12,[sp]; ldr r0,[sp,#16]; ldr r1,[sp,#20]; ldr r2,[sp,#24]; ldr r3,[sp,#28]; bl '+hex(uu['fx_header'])+'; add sp,#8; cmp r0,#0; beq old; '+integer_restore+'movs r0,#1; bx lr; old: '+integer_restore+'push {r4,r5,r6,lr}; sub sp,#8; b.w 0x08134b5c')
 site(0x08134b58,'b.w '+hex(a),'Use native parameter-row menu for Track FX only')
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; ldr r2,[sp,#16]; ldr r3,[sp,#20]; bl '+hex(uu['fx_get'])+'; cmp r0,#0; beq old; '+integer_restore+'movs r0,#1; bx lr; old: '+integer_restore+'push {r4,r5,r6,r7,lr}; sub sp,#12; b.w 0x08133618')
 site(0x08133614,'b.w '+hex(a),'Read private Track FX values without changing native properties')
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['fx_event'])+'; cmp r0,#0; beq old; '+integer_restore+'movs r0,#0; bx lr; old: '+integer_restore+'push {r4,r5,lr}; sub sp,#0x2c; b.w 0x08145d94')
 site(0x08145d90,'b.w '+hex(a),'Handle native encoder/touch events only on custom FX rows')
 for address,name,oldtarget,arg0,arg1 in [(0x0812f5ea,'fx_save',0x081bb200,'mov r0,r6','ldr r1,[sp,#8]'),(0x0812faac,'fx_load',0x081bb300,'ldr r0,[sp,#8]','ldr r1,[sp,#12]'),(0x081512a4,'fx_finish',0x081ba000,'ldr r0,[sp,#8]','ldr r1,[sp,#12]')]:
  a=ub(integer_prefix+arg0+'; '+arg1+'; bl '+hex(uu[name])+'; '+integer_restore+'b.w '+hex(oldtarget));site(address,'b.w '+hex(a),'Versioned Track FX project settings; chain original K16 hook')
 a=ub(integer_prefix+'ldr r0,=0x24041440; movs r1,#0; movw r2,#160; zero: str r1,[r0],#4; subs r2,#1; bne zero; ldr r0,=0x24041a00; movw r2,#384; state: str r1,[r0],#4; subs r2,#1; bne state; dsb; '+integer_restore+'b.w 0x081b5200')
 site(0x081004b6,'b.w '+hex(a),'Initialize new UI-owned FX memory, then original K16 startup')
 assert len(uw)<=0x800
 append=BASE+len(base);body=bytes(0x081c0000-append)+bytes(uw)+bytes(0x800-len(uw))+uc
 body+=b'BENTO_MOD:TrackFX:TF2:1.0\0';body+=b'\xff'*(-len(body)%4)
 put(append,body,'TF2 native settings UI implementation, application flash only')
 for a in [0x08040588,0x080a3bdc,0x080a3e94]:
  assert struct.unpack_from('<I',base,a-BASE)[0]==0x24042000;put(a,struct.pack('<I',0x24040000),'Reserve 8KB for Track FX inside native MPU permissions; stack unchanged')
 put(0x0818bad4,b'1.6T2\0','Visible TF2 test identifier')
 for a,n in [(BASE,0x400),(0x080e0000,0x20000),(0x08100000,0x400)]:assert image[a-BASE:a-BASE+n]==base[a-BASE:a-BASE+n]
 restored=bytearray(image)
 for w in reversed(writes):
  off=w['address']-BASE;restored[off:off+w['size']]=bytes.fromhex(w['original_hex'])
 restored=restored[:len(base)];assert bytes(restored)==base
 return bytes(image),writes,aa,uu
if __name__=='__main__':
 b=Path(sys.argv[1]).read_bytes();image,writes,aa,uu=build(b);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
 (out/'bento1.bin').write_bytes(image);(out/'manifest.json').write_text(json.dumps(dict(label='1.6T2',base_sha256=K16_SHA,sha256=hashlib.sha256(image).hexdigest(),writes=writes,audio_symbols=aa,ui_symbols=uu),indent=2)+'\n')
 print('TF2 built:',len(image),'bytes; exact K16 restore verified')
