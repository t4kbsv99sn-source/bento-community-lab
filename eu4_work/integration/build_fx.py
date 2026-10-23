"""Hash-guarded EU10 Euclidean + TF2 extension on the exact K16 build. No bootloader."""
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
   if info&15 in (1,2):syms[tab[name:].split(b'\0')[0].decode()]=value&~1 if info&15==2 else value
 return chunks,syms
def compile():
 sys.path.insert(0,str(R.parents[1]/'k16_work/bento_controls'))
 import step_locks
 _,native_lock=step_locks.compile_one('step_lock_audio','cortex_m7',True)
 (R/'lock_api.h').write_text('/* Generated from exact K16 APIs. */\n'+''.join('#define LIVE_'+name.upper()+' '+hex(native_lock[name])+'u\n' for name in ['lock_pending','lock_route']))
 t=R.parent/'track_fx';v=t/'vendor/DaisySP-LGPL'
 common=[sys.executable,'-m','ziglang','c++','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp','-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-std=c++17','-Os','-flto','-g','-ffreestanding','-fno-builtin','-fno-exceptions','-fno-rtti','-fno-stack-protector','-nostdlib','-nostdlib++','-I'+str(t/'arm_support'),'-I'+str(v),'-I'+str(v/'Utility')]
 sources=[R/'fx_audio.cpp',R/'live_audio.cpp',t/'track_fx.cpp',v/'Source/Dynamics/compressor.cpp',v/'Source/Filters/biquad.cpp',t/'arm_support/math_runtime.cpp']
 subprocess.run([*common,'-Wl,--entry=fx_audio','-Wl,--script='+str(R/'audio.ld'),*map(str,sources),'-o',str(R/'audio.elf')],check=True)
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=fx_dispatch','-Wl,--script='+str(R/'ui.ld'),str(R/'fx_ui.c'),str(R/'euclidean.c'),str(R/'live_ui.c'),str(R/'step_lock_ui.c'),str(R/'kick_ui.c'),'-o',str(R/'ui.elf')],check=True)
 ac,aa=elf(R/'audio.elf');uc,uu=elf(R/'ui.elf')
 assert len(ac)==len(uc)==1 and ac[0][0]==AUDIO and uc[0][0]==UI
 assert AUDIO+len(ac[0][1])<=0x080e0000 and UI+len(uc[0][1])<=0x081cc000
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
 # Replace only the existing K16 synth cave and its existing render adapter.
 import importlib.util
 spec=importlib.util.spec_from_file_location('eu4_kick',R.parent/'drums/kick_build.py')
 dk=importlib.util.module_from_spec(spec);spec.loader.exec_module(dk)
 for address,data,expected,why in dk.writes_for(base,0):
  put(address,data,'EU10 same synth formulas, block constants and LTO: '+why)
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
 a=ab(prefix+'sub sp,#8; ldr r0,[sp,#136]; str r0,[sp]; ldr r0,[sp,#80]; ldr r1,[sp,#84]; ldr r2,[sp,#88]; ldr r3,[sp,#92]; bl '+hex(aa['live_render'])+'; add sp,#8; '+restore+'push.w {r4-r11,lr}; b.w 0x08060824')
 put(0x08060820,asm('b.w '+hex(a),0x08060820),'EU10 native timed-note renderer entry')
 a=ab(prefix+'mov r0,r8; ldrh.w r1,[sp,#170]; bl '+hex(aa['live_skip'])+'; cmp r0,#0; beq old; '+restore+'b.w 0x080609e2; old: '+restore+'b.w 0x080d2000')
 put(0x08060b64,asm('b.w '+hex(a),0x08060b64),'EU10 suppress only native hits for generator-controlled pads; chain conditions')
 a=ab(prefix+'ldr r0,[sp,#72]; bl '+hex(aa['live_restart'])+'; '+restore+'b.w 0x080d2100')
 put(0x08061740,asm('b.w '+hex(a),0x08061740),'EU10 restart on launches, preserve phase on normal loop; chain condition counter')
 # Resolve conditional payload only after the native note condition passed.
 # K16 adapter receives its accepted note word at original SP+60.
 old_native=0x080d3000
 a=ab(prefix+'mov r0,r8; ldr r1,[sp,#188]; bl '+hex(aa['locks_native_filter'])+'; str r0,[sp,#188]; '+restore+'b.w '+hex(old_native))
 put(0x08060b9a,asm('b.w '+hex(a),0x08060b9a),'EU10 conditional lock payload on accepted native hits')
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
 a=ub(integer_prefix+'ldr r0,[sp,#8]; bl '+hex(uu['eu_view_capture'])+'; '+integer_restore+'b.w 0x081b7008')
 site(0x0815c27c,'b.w '+hex(a),'EU10 capture valid native one-shot sequence context before unchanged K16 header')
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
 # Recompile exact baseline API maps, guarded by the complete K16 input hash.
 sys.path.insert(0,str(R.parents[1]/'k16_work/bento_controls'))
 import step_locks,kick_ui_build
 _,oldlocks=step_locks.compile_one('step_lock_ui','cortex_m4',False)
 # compile kick API without rebuilding or mutating the baseline binary
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--entry=kick_ui_before','-Wl,--script='+str(R.parents[1]/'k16_work/bento_controls/kick_ui.ld'),str(R.parents[1]/'k16_work/bento_controls/kick_ui.c'),'-o',str(R/'baseline_kick_ui.elf')],check=True)
 _,oldkick=elf(R/'baseline_kick_ui.elf')
 for name in ['locks_header_before','locks_header_after','locks_encoder','locks_proj','locks_save','locks_load','locks_clear','locks_pad_clear','seq_lights_clean','locks_grid','locks_pack','locks_slot']:
  address=oldlocks[name];site(address,'b.w '+hex(uu[name]),'EU10 relocated step lock UI: '+name)
 for name in ['kick_ui_supported','kick_ui_before','kick_ui_after','kick_ui_event','kick_ui_save','kick_ui_load','kick_ui_increment','drum_ui_step']:
  address=oldkick[name];site(address,'b.w '+hex(uu[name]),'EU10 synth display cleanup: '+name)
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['seq_eu_arrows'])+'; cmp r0,#0; beq old; '+integer_restore+'b.w 0x0815d520; old: '+integer_restore+'ldr r3,[r1,#8]; cmp r3,#9; b.w 0x0815d582')
 site(0x0815d57e,'b.w '+hex(a),'EU10 native SEQ arrows swap encoder banks and reuse sequence navigation')
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['seq_eu_native_head'])+'; cmp r0,#0; beq old; '+integer_restore+'bx lr; old: '+integer_restore+'add.w r3,r0,#0x11000; b.w 0x0815bde6')
 site(0x0815bde2,'b.w '+hex(a),'EU10 generated playhead overrides native clip position only in Euclid bank')
 # Select mode uses native Undo menu's next cell, not a coordinate overlay.
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['seq_select_event'])+'; cmp r0,#0; beq old; '+integer_restore+'movs r0,#0; bx lr; old: '+integer_restore+'push {lr}; sub sp,#0x6c; b.w 0x0815d604')
 site(0x0815d600,'b.w '+hex(a),'EU10 native Select action dispatcher')
 import holdstep
 _,hs=holdstep.build()
 for address,name,check in [(0x0815b9c0,'step_match','seq_selection_match'),(0x0815bab0,'step_selected','seq_selection_active')]:
  # No selected mask: fall through to exact K16 held/single inspection.
  c=uu['seq_selection_active']
  body=integer_prefix+'ldr r0,[sp,#8]; bl '+hex(c)+'; cmp r0,#0; beq old; '
  if name=='step_match':body+='ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu[check])+'; '
  body+='str r0,[sp,#8]; '+integer_restore+'bx lr; old: '+integer_restore+'b.w '+hex(hs[name])
  a=ub(body);site(address,'b.w '+hex(a),'EU10 persistent multi-step selection with native fallback')
 for address,name,replay in [
  (0x0815d1ec,'seq_select_press','cmp r1,#15; bhi 0x0815d234; b.w 0x0815d1f0'),
  (0x0815d23c,'seq_select_release','cmp r1,#15; bhi 0x0815d296; b.w 0x0815d240'),
  (0x0815d29c,'seq_select_touch','push {r3,r4,r5,lr}; mov r4,r0; b.w 0x0815d2a0'),
  (0x0815d2f4,'seq_select_touch_end','add.w r3,r0,#0x11000; b.w 0x0815d2f8'),
  (0x0815d444,'seq_select_touch_end','push {r3,lr}; add.w r3,r0,#0x11000; b.w 0x0815d44a')]:
  a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu[name])+'; cmp r0,#0; beq old; '+integer_restore+'bx lr; old: '+integer_restore+replay)
  site(address,'b.w '+hex(a),'EU10 selection gesture consumes native toggle path',6 if address==0x0815d444 else 4)
 # Native persistent header output; popup records alone do not populate it.
 replay=ub('push.w {r4-r10,lr}; b.w 0x08134804')
 a=ub('push {r4,r5,r6,lr}; mov r4,r0; mov r5,r1; bl '+hex(replay)+'; mov r2,r0; mov r0,r4; mov r1,r5; bl '+hex(uu['seq_toolbar'])+'; pop {r4,r5,r6,pc}')
 assert base[0x08134800-BASE:0x08134804-BASE]==bytes.fromhex('2de9f047')
 site(0x08134800,'b.w '+hex(a),'EU10 native persistent Select action beside Undo')
 # FA has five equal native menu columns; fifth was unused. Insert Select
 # after Undo and shift Length+/Length-/Duplicate intact into cells3..5.
 menu=bytearray(base[0x08198db0-BASE:0x08198db0-BASE+100])
 assert struct.unpack_from('<I',menu)[0]==0x1032
 entry=struct.pack('<5I',0x1051,uu['select_label'],0,0,1)
 new=menu[:80]+entry
 put(0x08198db0,new,'EU10 native Undo Select Length+ Length- Duplicate menu')
 put(0x081415f8,asm('movs r3,#5',0x081415f8),'EU10 populate fifth FA menu cell')
 assert base[0x081415f0-BASE:0x081415f0-BASE+4]==bytes.fromhex('cdf804b0')
 put(0x081415f0,asm('movs r3,#4; str r3,[sp,#4]',0x081415f0),'EU10 four menu rows put fifth Select button directly right of Undo')
 # F9 has eight actions and a blank fourth cell. Reuse that blank: native
 # popup application accepts at most nine entries, despite ten stored slots.
 old_menu=base[0x08198770-BASE:0x08198770-BASE+180]
 assert struct.unpack_from('<I',old_menu)[0]==0x1032
 assert struct.unpack_from('<I',old_menu,60)[0]==0
 put(0x08198770,old_menu[:60]+old_menu[80:100]+entry+old_menu[100:],'EU10 Select beside Undo in existing blank F9 cell; preserve eight actions')
 a=ub('push {r4,r5,r6,lr}; mov r4,r0; mov r5,r1; bl 0x0816faec; mov r0,r4; mov r1,r5; bl '+hex(uu['eu_glyph_paint'])+'; pop {r4,r5,r6,pc}')
 assert base[0x0819e858-BASE:0x0819e858-BASE+4]==struct.pack('<I',0x0816faed)
 put(0x0819e858,struct.pack('<I',a|1),'EU10 sequencer-only velocity glyph after native child drawing')
 assert len(uw)<=0x800
 append=BASE+len(base);body=bytes(0x081c0000-append)+bytes(uw)+bytes(0x800-len(uw))+uc
 body+=b'BENTO_MOD:Euclidean:EU10:1.0\0';body+=b'\xff'*(-len(body)%4)
 put(append,body,'TF2 native settings UI implementation, application flash only')
 for a in [0x08040588,0x080a3bdc,0x080a3e94]:
  assert struct.unpack_from('<I',base,a-BASE)[0]==0x24042000;put(a,struct.pack('<I',0x24040000),'Reserve 8KB for Track FX inside native MPU permissions; stack unchanged')
 put(0x0818bad4,b'1.6EA\0','Visible EU10 test identifier')
 for a,n in [(BASE,0x400),(0x080e0000,0x20000),(0x08100000,0x400)]:assert image[a-BASE:a-BASE+n]==base[a-BASE:a-BASE+n]
 restored=bytearray(image)
 for w in reversed(writes):
  off=w['address']-BASE;restored[off:off+w['size']]=bytes.fromhex(w['original_hex'])
 restored=restored[:len(base)];assert bytes(restored)==base
 return bytes(image),writes,aa,uu
if __name__=='__main__':
 b=Path(sys.argv[1]).read_bytes();image,writes,aa,uu=build(b);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
 (out/'bento1.bin').write_bytes(image);(out/'manifest.json').write_text(json.dumps(dict(label='1.6EA',base_sha256=K16_SHA,sha256=hashlib.sha256(image).hexdigest(),writes=writes,audio_symbols=aa,ui_symbols=uu),indent=2)+'\n')
 print('EU10 built:',len(image),'bytes; exact K16 restore verified')
