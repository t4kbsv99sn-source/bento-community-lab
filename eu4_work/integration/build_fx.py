"""Hash-guarded EU10 Euclidean + TF2 extension on the exact K16 build. No bootloader."""
from pathlib import Path
import struct,sys,subprocess,hashlib,json
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
R=Path(__file__).resolve().parent
BASE=0x08040000;AUDIO=0x080dc400;UI=0x081c0800
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
MEL_CODE=None;MEL_SYMS=None;SEND_CODE=None;SEND_SYMS=None;NATIVE_LOCK=None
def compile():
 global MEL_CODE,MEL_SYMS,SEND_CODE,SEND_SYMS,NATIVE_LOCK
 sys.path.insert(0,str(R.parents[1]/'k16_work/bento_controls'))
 import step_locks
 _,native_lock=step_locks.compile_one('step_lock_audio','cortex_m7',True)
 NATIVE_LOCK=native_lock
 (R/'lock_api.h').write_text('/* Generated from exact K16 APIs. */\n'+''.join('#define LIVE_'+name.upper()+' '+hex(native_lock[name])+'u\n' for name in ['lock_pending','lock_route','lock_queue']))
 t=R.parent/'track_fx';v=t/'vendor/DaisySP-LGPL'
 common=[sys.executable,'-m','ziglang','c++','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp','-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-std=c++17','-Os','-flto','-g','-ffreestanding','-fno-builtin','-fno-exceptions','-fno-rtti','-fno-stack-protector','-nostdlib','-nostdlib++','-I'+str(t/'arm_support'),'-I'+str(v),'-I'+str(v/'Utility')]
 mel_cmd=[*common];mel_cmd[mel_cmd.index('-Os')]='-Oz'
 subprocess.run([*mel_cmd,'-Wl,--entry=mel_pending','-Wl,--script='+str(R/'melodic_lock_audio.ld'),str(R/'melodic_lock_audio.cpp'),'-o',str(R/'melodic_lock_audio.elf')],check=True)
 mc,ms=elf(R/'melodic_lock_audio.elf');assert len(mc)==1 and mc[0][0]==0x080d4400 and len(mc[0][1])<=0x1400
 MEL_CODE,MEL_SYMS=mc[0][1],ms
 subprocess.run([*mel_cmd,'-Wl,--entry=mel_send_begin','-Wl,--script='+str(R/'melodic_send_audio.ld'),str(R/'melodic_send_audio.cpp'),'-o',str(R/'melodic_send_audio.elf')],check=True)
 sc,ss=elf(R/'melodic_send_audio.elf');assert len(sc)==1 and sc[0][0]==0x080dac00 and len(sc[0][1])<=0xe00,(len(sc[0][1]),'send helper bounds')
 SEND_CODE,SEND_SYMS=sc[0][1],ss
 (R/'melodic_lock_api.h').write_text('/* Generated exact melodic lock APIs. */\n'+''.join('#define '+n.upper()+' '+hex(ms[n])+'u\n' for n in ['mel_pending','mel_pending_clear']))
 sources=[R/'fx_audio.cpp',R/'live_audio.cpp',t/'track_fx.cpp',v/'Source/Dynamics/compressor.cpp',v/'Source/Filters/biquad.cpp',t/'arm_support/math_runtime.cpp']
 subprocess.run([*common,'-Wl,--entry=fx_audio','-Wl,--script='+str(R/'audio.ld'),*map(str,sources),'-o',str(R/'audio.elf')],check=True)
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=fx_dispatch','-Wl,--script='+str(R/'ui.ld'),str(R/'fx_ui.c'),str(R/'euclidean.c'),str(R/'live_ui.c'),str(R/'step_lock_ui.c'),str(R/'header_actions.c'),str(R/'melodic_eu.c'),str(R/'lanes_ui.c'),str(R/'bars_ui.c'),str(R/'kick_ui.c'),str(R/'perf_ui.c'),str(R/'synth_draw.c'),str(R/'mod_ui.c'),str(R/'macro_ui.c'),str(R/'melodic_lock_ui.c'),str(R/'seq_nav_ui.c'),*[str(R.parents[1]/'chord_work'/n) for n in ['chords.c','native_insert.c','device.c']],'-o',str(R/'ui.elf')],check=True)
 ac,aa=elf(R/'audio.elf');uc,uu=elf(R/'ui.elf')
 assert len(ac)==len(uc)==1 and ac[0][0]==AUDIO and uc[0][0]==UI
 # CH7: UI bound 081D0000 (was 081CC000, a margin). Stock M4 MPU region 1 makes
 # 08100000..081FFFFF executable; code stays in the 128 KB sector 081C0000 it already uses.
 assert AUDIO+len(ac[0][1])<=0x080e0000 and UI+len(uc[0][1])<=0x081e0000
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
 a=ab(prefix+'mov r0,r8; ldrh.w r1,[sp,#170]; ldrh.w r2,[sp,#184]; bl '+hex(aa['live_skip'])+'; cmp r0,#0; beq old; '+restore+'b.w 0x080609e2; old: '+restore+'b.w 0x080d2000')
 put(0x08060b64,asm('b.w '+hex(a),0x08060b64),'EU10 suppress only native hits for generator-controlled pads; chain conditions')
 a=ab(prefix+'ldr r0,[sp,#72]; bl '+hex(aa['live_restart'])+'; '+restore+'b.w 0x080d2100')
 put(0x08061740,asm('b.w '+hex(a),0x08061740),'EU10 restart on launches, preserve phase on normal loop; chain condition counter')
 # Resolve conditional payload only after the native note condition passed.
 # K16 adapter receives its accepted note word at original SP+60.
 old_native=0x080d3000
 a=ab(prefix+'mov r0,r8; ldr r1,[sp,#188]; bl '+hex(aa['locks_native_filter'])+'; str r0,[sp,#188]; mov r3,r0; mov r0,r8; ldr r1,[sp,#132]; ldrh.w r2,[sp,#170]; bl '+hex(MEL_SYMS['mel_pending'])+'; '+restore+'b.w '+hex(old_native))
 put(0x08060b9a,asm('b.w '+hex(a),0x08060b9a),'EU10 conditional lock payload on accepted native hits')
 # CH9 (owner): the per-track meter measured the raw track signal plus the fader
 # level (080A0566 reads r6, 080A055C/05C0/05E0 load the level offset), so Track
 # FX (clipper/compressor/EQ) never showed. Measure r4 instead: after Level and
 # Track FX (the TF2 hook at 080A0510), before pan/sends; no offset.
 for site_a,old,new,why in [(0x080a055c,'95ed1c8a0023','movs r3,#0; vmov s16,r3','meter offset 0 (post-level buffer)'),
                            (0x080a0566,'3046','mov r0,r4','meter the post-level, post-Track-FX buffer'),
                            (0x080a05c0,'95ed0a8a','b 0x080a055c; nop','other track type: same zero offset'),
                            (0x080a05e0,'95ed108a','b 0x080a055c; nop','other track type: same zero offset')]:
  assert base[site_a-BASE:site_a-BASE+len(old)//2].hex()==old,hex(site_a)
  mb=asm(new,site_a);assert len(mb)==len(old)//2,(hex(site_a),len(mb));put(site_a,mb,'CH9 meter after Track FX: '+why)
 # CH6 chord pad audition: the native keyboard-pad press/release posts in the
 # pad module (08084760 press, 08083FE0 release) call chord_press/chord_release,
 # which post the whole chord while M4 chord mode is active, else the original.
 for site_a,fn,args,why in [(0x08084918,'chord_press','mov r2,r4; movs r3,#0','track press'),(0x0808494e,'chord_press','mov r2,r4; movs r3,#1','layer press'),(0x0808414a,'chord_release','movs r2,#0','track release'),(0x08084180,'chord_release','movs r2,#1','layer release')]:
  assert base[site_a-BASE:site_a-BASE+4]==asm('bl 0x0809eca0',site_a),hex(site_a)
  a=ab(args+'; b.w '+hex(aa[fn]))
  put(site_a,asm('bl '+hex(a),site_a),'CH6 chord pad audition: '+why)
 # CH11 Mod Matrix: the sampler's 0x3F route command (0808F38E) offers synth
 # destinations to kick_route first, which keeps them in the root's own list.
 assert base[0x0808f38e-BASE:0x0808f392-BASE]==asm('bl 0x080925e0',0x0808f38e)
 a=ab('push {r0,r1,r2,lr}; bl '+hex(dk.SYMS['kick_route'])+'; cmp r0,#0; pop {r0,r1,r2,lr}; beq native; bx lr; native: b.w 0x080925e0')
 put(0x0808f38e,asm('bl '+hex(a),0x0808f38e),'CH11 synth destinations in the native route command')
 # A1 Analog Wavetable: the Wavetable root's per-voice render (vtable 080AC798
 # slot 18) records voice and track mode; the WT oscillator class (080AC3E4
 # slot 0) renders analog WT1/WT2 and leaves every other oscillator native.
 for slot,old,fn,why in [(0x080ac7e0,0x0809be81,'kick_analog_enter','Wavetable voice: note analog mode'),(0x080ac3e4,0x08081361,'kick_analog_osc','WT oscillator: analog render')]:
  assert struct.unpack_from('<I',base,slot-BASE)[0]==old,hex(slot)
  if fn=='kick_analog_enter':a=ab('push {r0-r3,r12,lr}; bl '+hex(dk.SYMS[fn])+'; pop {r0-r3,r12,lr}; b.w '+hex(old&~1))
  else:a=ab('push {r0-r3,r4,lr}; bl '+hex(dk.SYMS[fn])+'; cmp r0,#0; pop {r0-r3,r4,lr}; beq native; bx lr; native: b.w '+hex(old&~1))
  put(slot,struct.pack('<I',a|1),'A1 '+why)
 # P1 fixed velocity: the pad module's press call (08085540 -> 08084760) lets
 # perf_press adjust the record's pressure first.
 assert base[0x080857d6-BASE:0x080857da-BASE]==asm('bl 0x08084760',0x080857d6)
 a=ab('push {r0-r3,r12,lr}; mov r0,r1; bl '+hex(aa['perf_press'])+'; pop {r0-r3,r12,lr}; b.w 0x08084760')
 put(0x080857d6,asm('bl '+hex(a),0x080857d6),'P1 fixed velocity before the native pad press')
 # P4/P6 Analog oscillator display: the Wavetable pane class (081B3A18) tick [0] and
 # paint [1] go through analog_wave_tick/paint, which call the native ones.
 for slot,old,fn in [(0x081b3a18,0x081822a5,'analog_wave_tick'),(0x081b3a1c,0x08182315,'analog_wave_paint')]:
  assert struct.unpack_from('<I',base,slot-BASE)[0]==old,hex(slot)
  put(slot,struct.pack('<I',uu[fn]|1),'P4 Analog wave pane: '+fn)
 # P8 mod mode: the synth page view class (0819E894, Wavetable/Granular) tick [0]
 # and event [12] go through mod_view_tick/mod_view_event, which call the native ones.
 for slot,old,fn in [(0x0819e894,0x0815d7d1,'mod_view_tick'),(0x0819e8c4,0x0815f149,'mod_view_event')]:
  assert struct.unpack_from('<I',base,slot-BASE)[0]==old,hex(slot)
  put(slot,struct.pack('<I',uu[fn]|1),'P8 mod mode: '+fn)
 # P7: the P5 header chord symbol is removed (owner: overlaps the counter).
 # P6 Drum Synth action from the pad page view too (handler 0814888C).
 assert struct.unpack_from('<I',base,0x0819dc50-BASE)[0]==0x0814888d
 put(0x0819dc50,struct.pack('<I',uu['drum_view_event']|1),'P6 Drum Synth action on the pad page view')
 # P7 PROJ+PLAY never starts playback: the audio core's button scan posts the
 # transport play request (0x8F) itself at 0808D800 (button 15). The scan holds
 # each button's new state byte at r8 (current index): PROJ (7) is [r8-8]. While
 # PROJ is down, skip the request and leave the scan as the native path does.
 # Keystone mis-encodes conditional T3 branches; encode beq.w by hand.
 def beq_w(src,dst):
  off=dst-(src+4);assert -(1<<20)<=off<(1<<20) and not off&1
  v=off&0x1fffff;h1=0xf000|((v>>20)&1)<<10|0<<6|((v>>12)&0x3f);h2=0x8000|((v>>18)&1)<<13|((v>>19)&1)<<11|((v>>1)&0x7ff)
  return struct.pack('<HH',h1,h2)
 assert base[0x0808d34e-BASE:0x0808d352-BASE]==beq_w(0x0808d34e,0x0808d800)
 a=ab('sub.w r1,r8,#8; ldrb r1,[r1]; cmp r1,#0; beq native; mov r4,fp; ldrd r5,r7,[sp]; b.w 0x0808d2e2; native: b.w 0x0808d800')
 put(0x0808d34e,beq_w(0x0808d34e,a),'P7 PLAY while PROJ is held does not start playback')
 # P12: guard the native transport enqueue too, not only one scan branch.
 # PROJ is bit 8 of the producer's raw button mask (same source as input.s).
 # M4 shift state is a second independent guard after the UI receives it.
 a=ab('push {r2,r3}; ldrb r2,[r1]; cmp r2,#0x8f; bne native; ldr r2,=0x2401bd3c; ldr r2,[r2]; cbz r2,ui; add.w r2,r2,#0x2000; ldrh.w r2,[r2,#0x338]; tst.w r2,#0x100; bne blocked; ui: ldr r2,=0xe000ed14; ldr r2,[r2]; tst.w r2,#0x10000; beq read; ldr r2,=0xe000ef5c; ldr r3,=0x24048d60; str r3,[r2]; dsb; read: ldr r2,=0x24048d68; ldr r2,[r2]; cmp r2,#0; bne blocked; native: pop {r2,r3}; b.w 0x08059980; blocked: pop {r2,r3}; bx lr')
 assert base[0x08058600-BASE:0x08058604-BASE]==asm('b.w 0x08059980',0x08058600)
 put(0x08058600,asm('b.w '+hex(a),0x08058600),'P12 suppress queued PLAY while physical PROJ or UI shift is held')
 # P26 (owner: "hold LAUNCH: the pads don't work"; wanted: the pads play/select the
 # clip, or the empty slot, inside the white rectangle on their track = the native
 # Launch page's own pad function). K16's input hook turned LAUNCH+pad into its
 # stop/start request; LAUNCH now passes the pad through to the native page.
 assert base[0x080d0058-BASE:0x080d005e-BASE]==bytes.fromhex('b0f5805f18d0') # cmp.w r0,#0x1000 (LAUNCH); beq launch
 put(0x080d005c,bytes.fromhex('5ad0'),'P26 LAUNCH hold: pads go to the native Launch page (K16 input passthrough)')
 # P14 melodic locks: separately guarded zero caves, retaining K16 code.
 mw=bytearray()
 def mab(code):
  while len(mw)%4:mw.append(0)
  address=0x080dba00+len(mw);mw.extend(asm(code,address));return address
 # Tag only the primary queue of an owner enabled by the melodic editor.
 a=mab(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(NATIVE_LOCK['lock_queue'])+'; ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(MEL_SYMS['mel_queue'])+'; '+integer_restore+'ldr.w r3,[r0,#0x600]; b.w 0x08065604')
 put(0x08065600,asm('b.w '+hex(a),0x08065600),'P14 queue p-lock payload; chain exact legacy drum queue adapter')
 # Clear after native accepted-note emitter returns.
 assert base[0x08060b9e-BASE:0x08060ba2-BASE]==asm('ldr.w r3,[r9,#0x6c0]',0x08060b9e)
 a=mab(prefix+'bl '+hex(MEL_SYMS['mel_pending_clear'])+'; '+restore+'ldr.w r3,[r9,#0x6c0]; b.w 0x08060ba2')
 put(0x08060b9e,asm('b.w '+hex(a),0x08060b9e),'P14 clear melodic pending word after accepted hit')
 a=mab(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(MEL_SYMS['mel_note'])+'; '+restore+'ldr r3,[r0]; push.w {r4-r10,lr}; b.w 0x0807ebe6')
 assert base[0x0807ebe0-BASE:0x0807ebe6-BASE]==asm('ldr r3,[r0]; push.w {r4-r10,lr}',0x0807ebe0)
 put(0x0807ebe0,asm('b.w '+hex(a)+'; nop',0x0807ebe0),'P14 generic melodic note capture')
 a=mab(prefix+'mov r0,r7; mov r1,r4; bl '+hex(MEL_SYMS['mel_attach'])+'; '+restore+'mov r0,r7; bl 0x0807e020; b.w 0x0807c0fc')
 assert base[0x0807c0f6-BASE:0x0807c0fc-BASE]==asm('mov r0,r7; bl 0x0807e020',0x0807c0f6)
 put(0x0807c0f6,asm('b.w '+hex(a)+'; nop',0x0807c0f6),'P14 capture locks on initialized native melodic voice')
 a=mab(prefix+'ldr r0,[sp,#72]; ldr r1,[sp,#76]; bl '+hex(MEL_SYMS['mel_context'])+'; ldr r0,[sp,#72]; ldr r1,[sp,#76]; ldr r2,[sp,#140]; bl '+hex(SEND_SYMS['mel_send_voice'])+'; str r0,[sp,#140]; '+restore+'b.w 0x0807b000')
 assert base[0x0807a80e-BASE:0x0807a812-BASE]==asm('bl 0x0807b000',0x0807a80e)
 put(0x0807a80e,asm('bl '+hex(a),0x0807a80e),'P14 bind per-voice filter evaluation context')
 a=mab(prefix+'bl '+hex(SEND_SYMS['mel_send_voice_end'])+'; bl '+hex(MEL_SYMS['mel_context_clear'])+'; '+restore+'b.w 0x0807a7e0')
 put(0x0807a812,asm('b.w '+hex(a)+'; nop',0x0807a812),'P14 leave per-voice evaluation context')
 a=mab(prefix+'mov r0,r4; mov r1,r7; bl '+hex(MEL_SYMS['mel_level'])+'; '+restore+'ldrb.w r3,[r5,#0x161]; b.w 0x0807b1a8')
 assert base[0x0807b1a4-BASE:0x0807b1a8-BASE]==asm('ldrb.w r3,[r5,#0x161]',0x0807b1a4)
 put(0x0807b1a4,asm('b.w '+hex(a),0x0807b1a4),'P14 voice gain before native pan/mix')
 evsave='push.w {r0-r3,r12,lr}; vpush {d0-d7}; '
 evrestore='vpop {d0-d7}; pop.w {r0-r3,r12,lr}; '
 a=mab('ldr r1,=0x24041fc0; ldr r2,[r1]; ldr r3,=0x324c5545; cmp r2,r3; bne legacy; ldr r1,[r1,#4]; cbz r1,legacy; ldr r1,[r1,#16]; cbz r1,legacy; ldr r2,[r1,#80]; cbz r2,legacy; subs r3,r0,r2; movw r2,#0x5c4; cmp r3,r2; beq check; adds r2,#0x48; cmp r3,r2; bne legacy; check: '+evsave+'bl '+hex(MEL_SYMS['mel_evaluate'])+'; cmp r0,#0; '+evrestore+'beq legacy; vldr s0,[r0,#0x3c]; bx lr; legacy: b.w 0x080d1100')
 put(0x0809fd80,asm('b.w '+hex(a),0x0809fd80),'P14 fast per-voice filter lock guard; chain unchanged drum evaluator')
 # P15: phase-local envelope evaluation also catches note-off outside render.
 for address,kind in [(0x0808773a,7),(0x08087aae,9)]:
  assert base[address-BASE:address-BASE+4]==asm('bl 0x0809fd80',address)
  a=mab(evsave+'movs r1,#'+str(kind)+'; bl '+hex(MEL_SYMS['mel_envelope'])+'; cmp r0,#0; '+evrestore+'beq native; vldr s0,[r0,#0x3c]; bx lr; native: b.w 0x0809fd80')
  put(address,asm('bl '+hex(a),address),'P15 Env 1 phase entry: note-owned decay/release')
 # Root rendering begins only after incoming note events have been applied.
 address=0x0807a7c8
 assert base[address-BASE:address-BASE+4]==asm('mov sl,r5; ldr r7,[sp,#0x20]',address)
 a=mab(prefix+'mov r0,r4; mov r1,r8; bl '+hex(SEND_SYMS['mel_send_begin'])+'; '+restore+'mov sl,r5; ldr r7,[sp,#0x20]; b.w 0x0807a7cc')
 put(address,asm('b.w '+hex(a),address),'P15 begin isolated note sends after note events')
 address=0x0807ab60
 assert base[address-BASE:address-BASE+4]==asm('ldr r3,[r4,#0x3c]; cbz r3,0x0807ab6c',address)
 a=mab(prefix+'mov r0,r4; bl '+hex(SEND_SYMS['mel_send_end'])+'; '+restore+'ldr r3,[r4,#0x3c]; cmp r3,#0; bne native; b.w 0x0807ab6c; native: b.w 0x0807ab64')
 put(address,asm('b.w '+hex(a),address),'P15 publish isolated send submixes after all voices')
 for address,fn,args,native in [(0x080a050c,'mel_send_prepare','mov r0,r5; mov r1,r6',0x0805bc40),(0x080a0526,'mel_send_duck','mov r0,r5',0x080635e0)]:
  assert base[address-BASE:address-BASE+4]==asm('bl '+hex(native),address)
  a=mab(prefix+args+'; bl '+hex(SEND_SYMS[fn])+'; '+restore+'b.w '+hex(native))
  put(address,asm('bl '+hex(a),address),'P15 snapshot native track gain/duck before state advances')
 for address in [0x080a0532,0x080a053e]:
  assert base[address-BASE:address-BASE+4]==asm('bl 0x0805bc40',address)
  a=mab('push {r3,lr}; mov r3,r5; bl '+hex(SEND_SYMS['mel_send_mix'])+'; pop {r3,pc}')
  put(address,asm('bl '+hex(a),address),'P15 per-note send bus mix; native fallback without send locks')
 assert len(mw)<=0x600 and base[0x080dba00-BASE:0x080dba00-BASE+len(mw)]==bytes(len(mw)),len(mw)
 assert base[0x080dac00-BASE:0x080dac00-BASE+len(SEND_CODE)]==bytes(len(SEND_CODE))
 put(0x080dac00,SEND_CODE,'P15 note send routing in checked application cave')
 aa.update(SEND_SYMS)

 assert base[0x080d4400-BASE:0x080d4400-BASE+len(MEL_CODE)]==bytes(len(MEL_CODE))
 put(0x080d4400,MEL_CODE,'P14 melodic locks in checked free application cave')
 put(0x080dba00,bytes(mw),'P14 preserving adapters in checked free application cave')
 aa.update(MEL_SYMS)
 assert len(aw)<=AUDIO-0x080dc000 # CH6: adapters use <0x200; M7 code starts at 080DC400
 payload=bytes(aw)+bytes(AUDIO-0x080dc000-len(aw))+ac
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
 # S1: the inherited clean filter hid every third row except Kick. Reveal
 # Subtractive's Sync/amp ADSR row while preserving all other cleanup rules.
 for address,name in [(0x08183854,'wave_paint'),(0x08168768,'envelope_paint'),(0x0817ddfc,'lfo_paint'),(0x0816a97c,'button_paint'),(0x0817e780,'label_paint'),(0x08179120,'rect_paint')]:
  site(address,'b.w '+hex(uu['synth_'+name]),'S1 direct drawing filter: Subtractive third row visible')
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
 # CH1 captures only the real pitched piano roll after its native header.
 replay=ub('push.w {r4-r11,lr}; b.w 0x081599c0')
 a=ub('push {r4,lr}; mov r4,r0; bl '+hex(replay)+'; mov r0,r4; bl '+hex(uu['piano_after_header'])+'; pop {r4,pc}')
 assert base[0x081599bc-BASE:0x081599c0-BASE]==bytes.fromhex('2de9f04f')
 site(0x081599bc,'b.w '+hex(a),'CH1 capture native pitched piano-roll context')
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['piano_event'])+'; cmp r0,#0; beq old; '+integer_restore+'movs r0,#0; bx lr; old: '+integer_restore+'push {r4-r7,lr}; sub sp,#0x174; b.w 0x0815a59c')
 assert base[0x0815a598-BASE:0x0815a59c-BASE]==bytes.fromhex('f0b5ddb0')
 site(0x0815a598,'b.w '+hex(a),'CH1 native Chord toolbar action; ordinary piano events fall through')
 # CH5: piano hardware events (vtable slot 13): arrows walk chords in live chord mode.
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['piano_hw'])+'; cmp r0,#0; beq old; '+integer_restore+'bx lr; old: '+integer_restore+'push {r4-r7,lr}; sub sp,#0x44; b.w 0x0815b54c')
 assert base[0x0815b548-BASE:0x0815b54c-BASE]==bytes.fromhex('f0b591b0')
 site(0x0815b548,'b.w '+hex(a),'CH5 live chord Left/Right; other piano hardware events stay native')
 # Native persistent header output; popup records alone do not populate it.
 a=ub(integer_prefix+'ldr r0,[sp,#12]; bl '+hex(uu['device_header_prepare'])+'; '+integer_restore+'push.w {r4-r11,lr}; b.w 0x0817fafc')
 assert base[0x0817faf8-BASE:0x0817fafc-BASE]==bytes.fromhex('2de9f04f')
 site(0x0817faf8,'b.w '+hex(a),'P12 custom controls at final native header application')
 replay=ub('push.w {r4-r10,lr}; b.w 0x08134804')
 a=ub('push {r4,r5,r6,lr}; mov r4,r0; mov r5,r1; bl '+hex(replay)+'; mov r2,r0; mov r0,r4; mov r1,r5; bl '+hex(uu['seq_toolbar'])+'; pop {r4,r5,r6,pc}')
 assert base[0x08134800-BASE:0x08134804-BASE]==bytes.fromhex('2de9f047')
 site(0x08134800,'b.w '+hex(a),'Persistent header custom actions (Select/Chord) with visibility sync')
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
 # CH11 drum-synth destinations in the native Mod Matrix (one-shot types 1/2).
 assert base[0x0814ce80-BASE:0x0814ce84-BASE]==bytes.fromhex('039e0f2e')
 a=ub('push {r0-r3,r12,lr}; mov r0,r4; add r1,sp,#24; bl '+hex(uu['mod_rows'])+'; pop {r0-r3,r12,lr}; ldr r6,[sp,#0xc]; cmp r6,#0xf; bx lr')
 site(0x0814ce80,'bl '+hex(a),'CH11 synth pad rows in the native Mod Matrix')
 for site_a,old,fn,why in [(0x0812f6a2,0x081666f8,'mod_token','save synth destination names'),(0x0812fe52,0x08166720,'mod_key','load synth destination names'),(0x08140924,0x08133388,'mod_edit','editing a synth route adopts the pad engine')]:
  assert base[site_a-BASE:site_a-BASE+4]==asm('bl '+hex(old),site_a),hex(site_a)
  site(site_a,'bl '+hex(uu[fn]),'CH11 Mod Matrix: '+why)
 # A1: "Analog" in the ninth (blank) cell of the native instrument menu
 # (Multisample..External at 081981F8, ten 20-byte cells); its action 1052 is
 # handled before the native menu handler (view vtable 0819E52C, 0814ECD4).
 cell=0x081981f8+8*20
 assert base[cell-BASE:cell-BASE+20]==struct.pack('<5I',0,0x0818a3d8,0,0,1)
 put(cell,struct.pack('<5I',0x1052,uu['analog_label'],0,0,1),'A1 Analog entry in the instrument menu')
 assert base[0x08141370-BASE:0x08141372-BASE]==asm('movs r3,#8',0x08141370)
 put(0x08141370,asm('movs r3,#9',0x08141370),'A1 instrument menu F6 shows nine cells (native maximum)')
 assert struct.unpack_from('<I',base,0x0819e52c-BASE)[0]==0x0814ecd5
 put(0x0819e52c,struct.pack('<I',uu['analog_menu_event']|1),'A1 instrument menu: Analog action, Wavetable clears it')
 # A1 Sync on WT2's empty fourth control (Wavetable osc page key table).
 # A1b: Glide/Sync only on Analog pages, Shape label, "Analog" pane text.
 for site_a,flag in [(0x0815f5ae,0),(0x0815f68e,1)]:
  assert base[site_a-BASE:site_a-BASE+4]==asm('bl 0x08187252',site_a),hex(site_a)
  a=ub('movs r3,#'+str(flag)+'; b.w '+hex(uu['analog_page_keys']))
  put(site_a,asm('bl '+hex(a),site_a),'A1 synth page keys: '+('Wavetable/Analog' if flag else 'Granular stays native'))
 for lit,old in [(0x0815dcf8,0x0818cb94),(0x0815e218,0x0818cb94),(0x0815d9a8,0x0818cb74),(0x0815dcfc,0x0818cb74),(0x0815e21c,0x0818cb74)]:
  assert struct.unpack_from('<I',base,lit-BASE)[0]==old,hex(lit)
  put(lit,struct.pack('<I',0x24043d4c if old==0x0818cb94 else 0x24043d58),'A1 waveform pane text follows the track (No WAV / Analog)')
 assert base[0x081403ec-BASE:0x081403f0-BASE]==asm('push {r4,r5,r6,lr}; sub sp,#0x68',0x081403ec)
 a=ub(integer_prefix+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(uu['analog_model_event'])+'; cmp r0,#0; beq old; '+integer_restore+'movs r0,#0; bx lr; old: '+integer_restore+'push {r4,r5,r6,lr}; sub sp,#0x68; b.w 0x081403f0')
 site(0x081403ec,'b.w '+hex(a),'A1 model events: Analog Sync stays private')
 # P20: header root events (vtable 081B3680 slot 13) pass through header_root_event.
 a=0x081b3680+13*4;assert struct.unpack_from('<I',base,a-BASE)[0]==0x0817ffb9
 put(a,struct.pack('<I',uu['header_root_event']|1),'P20 keep native tab lights off while Chord/Euclid is shown')
 # CH6 Euclidean lanes in the piano roll: the piano grid class (vtable 081B2BCC)
 # paints and ticks through lane_paint/lane_tick, which call the originals.
 # P17 (owner: the touch selection rectangle always opens at the lower middle):
 # slot 4 touch-down records the first finger as the box anchor (+A48), which the
 # native drag (mode 5, 081762B0) uses but only box mode used to set.
 for slot,old_fn,fn in [(0,0x081773a5,'lane_tick'),(1,0x08176d75,'lane_paint'),(4,0x08174999,'grid_touch_down'),(5,0x08175f39,'grid_touch_move'),(6,0x08176a29,'grid_touch_up')]:
  a=0x081b2bcc+slot*4;assert struct.unpack_from('<I',base,a-BASE)[0]==old_fn
  put(a,struct.pack('<I',uu[fn]|1),'CH6 piano-grid lanes: '+fn)
 # P27 macros: the native encoder strip (vtable 081B2838) takes touches. Its
 # touch slots [4..6] are empty stubs and [7] ("takes touches") returns 0 in
 # stock; swipes and taps on it go to macro_ui.c.
 for slot,old_fn,fn in [(4,0x08143ac1,'macro_bar_down'),(5,0x08143ac3,'macro_bar_move'),(6,0x08143ac5,'macro_bar_up'),(7,0x08143ac7,'macro_bar_takes')]:
  a=0x081b2838+slot*4;assert struct.unpack_from('<I',base,a-BASE)[0]==old_fn
  put(a,struct.pack('<I',uu[fn]|1),'P27 macro strip touches: '+fn)
 assert len(uw)<=0x800
 append=BASE+len(base);body=bytes(0x081c0000-append)+bytes(uw)+bytes(0x800-len(uw))+uc
 body+=b'BENTO_MOD:Chord:CH1:1.0\0';body+=b'\xff'*(-len(body)%4)
 put(append,body,'TF2 native settings UI implementation, application flash only')
 for a in [0x08040588,0x080a3bdc,0x080a3e94]:
  assert struct.unpack_from('<I',base,a-BASE)[0]==0x24042000;put(a,struct.pack('<I',0x24040000),'Reserve 8KB for Track FX inside native MPU permissions; stack unchanged')
 # P17 (owner plan): no hold-INST shortcut on SEQ. K16 inst_hold compares the page
 # with 0x27 (drum Step SEQ); compare with 0xFF (never a page) so the press is stock.
 assert base[0x081b43b8-BASE:0x081b43bc-BASE]==bytes.fromhex('00262728')
 put(0x081b43b8,bytes.fromhex('0026ff28'),'P17 remove K16 hold-INST shortcut on SEQ (INST press is stock)')
 put(0x0818bad4,b'1.6P22\0','Visible P22 identifier')
 for a,n in [(BASE,0x400),(0x080e0000,0x20000),(0x08100000,0x400)]:assert image[a-BASE:a-BASE+n]==base[a-BASE:a-BASE+n]
 restored=bytearray(image)
 for w in reversed(writes):
  off=w['address']-BASE;restored[off:off+w['size']]=bytes.fromhex(w['original_hex'])
 restored=restored[:len(base)];assert bytes(restored)==base
 return bytes(image),writes,aa,uu
if __name__=='__main__':
 b=Path(sys.argv[1]).read_bytes();image,writes,aa,uu=build(b);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
 (out/'bento1.bin').write_bytes(image);(out/'manifest.json').write_text(json.dumps(dict(label='1.6P22',base_sha256=K16_SHA,sha256=hashlib.sha256(image).hexdigest(),writes=writes,audio_symbols=aa,ui_symbols=uu),indent=2)+'\n')
 print('EU10 built:',len(image),'bytes; exact K16 restore verified')
