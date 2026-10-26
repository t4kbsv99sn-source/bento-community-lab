"""Motion recording layer on top of a Bento Playground image (P22+: applied after
build_fx). Every site is guarded by the exact bytes it expects; no flash operation."""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess,sys
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from native_node_patches import patches
from build_native_audio import build as build_audio,P19,START as AUDIO_START,END as AUDIO_END
AUDIO_WRAPPERS=0x080d15f0;AUDIO_WRAPPERS_END=0x080d1f00 # stock zero gap
ROOT=Path(__file__).resolve().parent;BASE=0x08040000
# P22 (owner: installing the 081E0000-based image failed, "couldn't verify the
# firmware" / error 19). Every image that installed ended below 081E0000; the
# application must not reach the last 128 KB flash sector 081E0000..081FFFFF.
# M4 motion code sits right below it, above the standalone chord test origin.
UI_ORIGIN=0x081da000;WRAPPERS=0x081dd800;APP_END=0x081e0000

def elf(path):
 b=path.read_bytes();off=struct.unpack_from('<I',b,32)[0];step,n=struct.unpack_from('<HH',b,46)
 ss=[struct.unpack_from('<10I',b,off+i*step) for i in range(n)];chunks=[];syms={}
 for s in ss:
  if s[2]&2:chunks.append((s[3],b[s[4]:s[4]+s[5]]))
  if s[1]!=2:continue
  st=ss[s[6]];names=b[st[4]:st[4]+st[5]]
  for i in range(0,s[5],s[9]):
   name,value,size,info,_,idx=struct.unpack_from('<IIIBBH',b,s[4]+i)
   if info&15==2:syms[names[name:].split(b'\0')[0].decode()]=value&~1
 return chunks,syms

def build_ui(path):
 sources=['motion_native_ui.c','motion_native_controls.c','motion_native_node.c','motion_core.c','motion_compact.c']
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-flto','-g','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--entry=motion_ui_save','-Wl,--script='+str(ROOT/'motion_ui.ld'),*[str(ROOT/s) for s in sources],'-o',str(path)],check=True)
 chunks,syms=elf(path);assert len(chunks)==1 and chunks[0][0]==UI_ORIGIN
 assert chunks[0][0]+len(chunks[0][1])<=WRAPPERS
 return chunks[0][1],syms

def build(image,out,verify=False,expect=None):
 if expect:assert hashlib.sha256(image).hexdigest()==expect,'unexpected baseline image'
 out.mkdir(parents=True,exist_ok=True)
 audio=build_audio(out/'motion_audio.elf');ui,us=build_ui(out/'motion_ui.elf');_,aus=elf(out/'motion_audio.elf')
 if verify:
  assert audio==build_audio(out/'motion_audio_repeat.elf')
  repeat,_=build_ui(out/'motion_ui_repeat.elf');assert ui==repeat
 k=Ks(KS_ARCH_ARM,KS_MODE_THUMB);cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
 result=bytearray(image);writes=[]
 def asm(s,a):return bytes(k.asm(s,a)[0])
 def put(a,data,reason):
  o=a-BASE;assert a>=BASE and a+len(data)<=0x08200000
  assert not any(a<w['address']+w['size'] and w['address']<a+len(data) for w in writes)
  old=bytes(result[o:o+len(data)])
  if o>len(result):result.extend(bytes(o-len(result)))
  result[o:o+len(data)]=data
  writes.append(dict(address=a,size=len(data),original_hex=old.hex(),replacement_hex=data.hex(),reason=reason))
 def target(a):
  i=next(cs.disasm(image[a-BASE:a-BASE+4],a));assert i.mnemonic=='b.w',(hex(a),i.mnemonic)
  return int(i.op_str.lstrip('#'),16)
 def site(a,dest,reason):put(a,asm('b.w '+hex(dest),a),reason)
 wrappers=bytearray();aw=bytearray()
 def wrap(s,audio=False):
  data=aw if audio else wrappers;base=AUDIO_WRAPPERS if audio else WRAPPERS
  while len(data)%4:data.append(0)
  a=base+len(data);data.extend(asm(s,a));return a
 pre='push.w {r0-r12,lr}; mrs r0,APSR; push {r0,r1}; '
 post='pop {r0,r1}; msr APSR_nzcvq,r0; pop.w {r0-r12,lr}; '
 # P22b: no native node-size patches (side store).
 assert AUDIO_START+len(audio)<=AUDIO_END and image[AUDIO_START-BASE:AUDIO_END-BASE]==bytes(AUDIO_END-AUDIO_START)
 put(AUDIO_START,audio,'M7 motion playback and RECORD transport gate')
 assert BASE+len(image)<=0x081d8000 and image[UI_ORIGIN-BASE:APP_END-BASE] in (b'',bytes(min(APP_END-BASE,len(image))-min(UI_ORIGIN-BASE,len(image))))
 put(UI_ORIGIN,ui,'M4 motion native storage, recording, editor and persistence')
 put(0x08062216,asm('bl '+hex(aus['motion_native_automation']),0x08062216),'native A-D update followed by independent motion evaluation')
 a=wrap(pre+'ldr r0,[sp,#8]; bl '+hex(aus['motion_native_restart'])+'; '+post+'b.w '+hex(target(0x08061740)),True)
 site(0x08061740,a,'chain P19 launch/condition hooks')
 a=wrap(pre+'ldr r0,[sp,#12]; bl '+hex(aus['motion_native_record_gate'])+'; cmp r0,#0; beq old; '+post+'bx lr; old: '+post+'b.w '+hex(target(0x08058600)),True)
 site(0x08058600,a,'consume shifted RECORD; preserve P19 PLAY gating')
 a=wrap(pre+'mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(us['motion_controls_dispatch'])+'; cmp r0,#0; beq old; '+post+'b.w 0x0813f2fc; old: '+post+'b.w '+hex(target(0x0813f98c)))
 site(0x0813f98c,a,'motion hold input before P19 shortcuts')
 a=wrap(pre+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(us['motion_controls_model_event'])+'; cmp r0,#0; beq old; '+post+'movs r0,#0; bx lr; old: '+post+'b.w '+hex(target(0x081403ec)))
 site(0x081403ec,a,'capture assigned parameter movement before native base mutation')
 a=wrap('push {r4,r5,r6,lr}; mov r4,r0; bl '+hex(us['motion_controls_before_header'])+'; mov r0,r4; bl '+hex(target(0x081599bc))+'; mov r0,r4; bl '+hex(us['motion_controls_after_header'])+'; pop {r4,r5,r6,pc}')
 site(0x081599bc,a,'native automation header with per-lane Length and recording controls')
 a=wrap(pre+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(us['motion_controls_event'])+'; cmp r0,#0; beq old; '+post+'movs r0,#0; bx lr; old: '+post+'b.w '+hex(target(0x0815a598)))
 site(0x0815a598,a,'automation settings encoders; preserve P19 piano events')
 a=wrap(pre+'sub sp,#8; ldr r12,[sp,#68]; str r12,[sp]; ldr r0,[sp,#16]; ldr r1,[sp,#20]; ldr r2,[sp,#24]; ldr r3,[sp,#28]; bl '+hex(us['motion_controls_get'])+'; add sp,#8; cmp r0,#0; beq old; '+post+'movs r0,#1; bx lr; old: '+post+'b.w '+hex(target(0x08133614)))
 site(0x08133614,a,'automation-only view length and held-knob readout')
 a=wrap(pre+'ldr r0,[sp,#8]; bl '+hex(us['motion_controls_graph'])+'; cmp r0,#0; beq old; '+post+'bx lr; old: '+post+'push.w {r4-r8,lr}; b.w 0x081579b4')
 assert image[0x081579b0-BASE:0x081579b4-BASE]==asm('push.w {r4-r8,lr}',0x081579b0)
 site(0x081579b0,a,'project motion onto the existing bounded native graph')
 a=wrap(pre+'sub sp,#8; ldr r12,[sp,#72]; str r12,[sp]; ldr r12,[sp,#76]; str r12,[sp,#4]; ldr r0,[sp,#16]; ldr r1,[sp,#20]; ldr r2,[sp,#24]; ldr r3,[sp,#28]; bl '+hex(us['motion_controls_set'])+'; add sp,#8; cmp r0,#0; beq old; '+post+'bx lr; old: '+post+'push {r4-r7,lr}; sub sp,#0x5c; b.w 0x08137070')
 assert image[0x0813706c-BASE:0x08137070-BASE]==asm('push {r4-r7,lr}; sub sp,#0x5c',0x0813706c)
 site(0x0813706c,a,'native graph edits preserve independent motion timing')
 a=wrap(pre+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; ldr r2,[sp,#16]; bl '+hex(us['motion_ui_rebuild'])+'; '+post+'push.w {r4-r11,lr}; b.w 0x081367ec')
 assert image[0x081367e8-BASE:0x081367ec-BASE]==asm('push.w {r4-r11,lr}',0x081367e8)
 site(0x081367e8,a,'publish clip automation when native playback rebuilds')
 replay_clear=wrap('push {r4-r7,lr}; sub sp,#0x24; b.w 0x081366c0')
 assert image[0x081366bc-BASE:0x081366c0-BASE]==asm('push {r4-r7,lr}; sub sp,#0x24',0x081366bc)
 a=wrap('push {r4-r7,lr}; sub sp,#4; mov r4,r0; mov r5,r1; mov r6,r2; bl '+hex(replay_clear)+'; mov r7,r0; mov r0,r4; mov r1,r5; mov r2,r6; bl '+hex(us['motion_ui_after_clear'])+'; mov r0,r7; add sp,#4; pop {r4-r7,pc}')
 site(0x081366bc,a,'native Clear Auto also clears extended playback after its Undo snapshot')
 replay_slide=wrap('push.w {r4-r8,lr}; b.w 0x08136752')
 assert image[0x0813674e-BASE:0x08136752-BASE]==asm('push.w {r4-r8,lr}',0x0813674e)
 a=wrap('push.w {r4-r8,lr}; mov r4,r0; mov r5,r1; mov r6,r2; mov r7,r3; bl '+hex(us['motion_ui_before_slide'])+'; mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(replay_slide)+'; mov r8,r0; mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(us['motion_ui_after_slide'])+'; mov r0,r8; pop.w {r4-r8,pc}')
 site(0x0813674e,a,'native Slide changes extended interpolation with Undo')
 a=wrap(pre+'sub sp,#8; ldr r12,[sp,#72]; str r12,[sp]; ldr r12,[sp,#76]; str r12,[sp,#4]; ldr r0,[sp,#16]; ldr r1,[sp,#20]; ldr r2,[sp,#24]; ldr r3,[sp,#28]; bl '+hex(us['motion_controls_bulk'])+'; add sp,#8; cmp r0,#0; beq old; '+post+'bx lr; old: '+post+'push.w {r4-r11,lr}; b.w 0x08137130')
 assert image[0x0813712c-BASE:0x08137130-BASE]==asm('push.w {r4-r11,lr}',0x0813712c)
 site(0x0813712c,a,'native bulk Value offset updates visible extended points')
 a=wrap(pre+'sub sp,#8; ldr r12,[sp,#68]; str r12,[sp]; ldr r0,[sp,#16]; ldr r1,[sp,#20]; ldr r2,[sp,#24]; ldr r3,[sp,#28]; bl '+hex(us['motion_settings_header'])+'; add sp,#8; cmp r0,#0; beq old; '+post+'movs r0,#1; bx lr; old: '+post+'b.w '+hex(target(0x08134b58)))
 site(0x08134b58,a,'native GenericProperties recording-settings menu')
 a=wrap(pre+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(us['motion_settings_event'])+'; cmp r0,#0; beq old; '+post+'movs r0,#0; bx lr; old: '+post+'b.w '+hex(target(0x08145d90)))
 site(0x08145d90,a,'recording settings events before existing property handlers')
 finish_entry=target(0x081512a4)
 finish_call=next(i for i in cs.disasm(image[finish_entry-BASE:finish_entry-BASE+64],finish_entry) if i.mnemonic=='bl')
 finish_target=int(finish_call.op_str.lstrip('#'),16)
 a=wrap('push {r4-r6,lr}; mov r4,r0; mov r5,r1; bl '+hex(finish_target)+'; mov r6,r0; ldrh r0,[r5]; cmp r0,#0x3f; bne done; bl '+hex(us['motion_ui_refresh_project'])+'; done: mov r0,r6; pop {r4-r6,pc}')
 put(finish_call.address,asm('bl '+hex(a),finish_call.address),'refresh motion snapshots after native project-load completion')
 a=wrap(pre+'mov r0,r6; ldr r1,[sp,#8]; bl '+hex(us['motion_ui_save'])+'; '+post+'b.w '+hex(target(0x0812f5ea)))
 site(0x0812f5ea,a,'versioned clip motion attributes beside native project parameters')
 replay=wrap('push.w {r4-r11,lr}; sub sp,#0x24; b.w 0x0812ffb0')
 # Native loader prologue pushes r4-r11 AND lr (36 bytes), followed by sub 36.
 # Preserve exact original instruction bytes rather than relying on a guessed register set.
 # The exact prologue below is checked before wrapping.
 assert image[0x0812ffa8-BASE:0x0812ffae-BASE]==asm('push.w {r4-r11,lr}; sub sp,#0x24',0x0812ffa8)
 # Resume at the first original move, 0812FFAE.
 replay=wrap('push.w {r4-r11,lr}; sub sp,#0x24; b.w 0x0812ffae')
 a=wrap('push {r4-r7,lr}; sub sp,#4; mov r4,r0; mov r5,r1; mov r6,r2; bl '+hex(replay)+'; mov r7,r0; mov r0,r4; mov r1,r5; mov r2,r6; bl '+hex(us['motion_ui_load'])+'; mov r0,r7; add sp,#4; pop {r4-r7,pc}')
 put(0x0812ffa8,asm('b.w '+hex(a),0x0812ffa8)+asm('nop',0x0812ffac),'load motion after the native automation XML parser')
 # P23: 08134800(model,out,flag_ptr,r3) uses all four argument registers (r2 is
 # written through); keep r2/r3 across the menu helper (P22 boot loop).
 a=wrap('push {r4-r8,lr}; sub sp,#8; mov r4,r0; mov r5,r1; mov r6,r2; mov r7,r3; bl '+hex(us['motion_settings_menu_remove'])+'; mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(target(0x08134800))+'; mov r8,r0; mov r0,r5; bl '+hex(us['motion_controls_counter'])+'; mov r0,r8; add sp,#8; pop {r4-r8,pc}')
 site(0x08134800,a,'recording bar count in native transport readout')
 a=wrap(pre+'ldr r0,[sp,#8]; ldr r1,[sp,#12]; bl '+hex(us['motion_controls_nav'])+'; '+post+'b.w '+hex(target(0x081420ec)))
 site(0x081420ec,a,'restore shared encoder descriptors on navigation')
 # Native clone (Undo snapshot/restore, clip copy/paste) carries the clip's motion.
 assert image[0x0812ea2a-BASE:0x0812ea2e-BASE]==asm('push {r4,r5,r6,lr}; sub sp,#8',0x0812ea2a)
 replay_clone=wrap('push {r4,r5,r6,lr}; sub sp,#8; b.w 0x0812ea2e')
 a=wrap('push {r4-r7,lr}; sub sp,#12; mov r4,r0; mov r5,r3; ldr r6,[sp,#32]; str r6,[sp]; bl '+hex(replay_clone)+'; mov r7,r0; mov r0,r4; mov r1,r5; mov r2,r6; mov r3,r7; bl '+hex(us['motion_store_clone'])+'; mov r0,r7; add sp,#12; pop {r4-r7,pc}')
 site(0x0812ea2a,a,'native clone copies side-store motion to the new clip handle')
 # P26: record indicator after the root header's own paint (vtable 081B3680 slot 1).
 assert struct.unpack_from('<I',image,0x081b3684-BASE)[0]==0x0817f8f1
 put(0x081b3684,struct.pack('<I',us['motion_header_draw']|1),'motion record button in the header')
 assert AUDIO_WRAPPERS+len(aw)<=AUDIO_WRAPPERS_END and image[AUDIO_WRAPPERS-BASE:AUDIO_WRAPPERS_END-BASE]==bytes(AUDIO_WRAPPERS_END-AUDIO_WRAPPERS)
 put(AUDIO_WRAPPERS,bytes(aw),'bounded M7 wrappers in verified zero cave')
 assert not any(0x080e0000<=w['address']<0x08100000 for w in writes),'080E0000 sector is another program'
 assert WRAPPERS+len(wrappers)<=APP_END,'M4 wrappers past the application end'
 put(WRAPPERS,bytes(wrappers),'M4 native adapter wrappers')
 # P22b: the native type-5 node allocation, zeroing and deep copy stay stock.
 for a in (0x0812e8c6,0x0812e3b6,0x0812e8e6):assert not any(w['address']<a+4 and a<w['address']+w['size'] for w in writes),hex(a)
 while len(result)%4:result.append(0)
 assert BASE+len(result)<=APP_END,'image reaches the last flash sector'
 restored=bytearray(result)
 for w in reversed(writes):
  o=w['address']-BASE;old=bytes.fromhex(w['original_hex']);restored[o:o+len(old)]=old
 assert bytes(restored[:len(image)])==image
 (out/'bento1.bin').write_bytes(result)
 report={'status':'motion layer','baseline_sha256':hashlib.sha256(image).hexdigest(),'sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'p19_reversal':True,'ui_symbols':us,'audio_symbols':aus,'writes':writes}
 (out/'MOTION_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('writes','ui_symbols','audio_symbols')},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--verify-repeat',action='store_true');p.add_argument('--expect');a=p.parse_args();build(a.baseline.read_bytes(),a.out,a.verify_repeat,a.expect)
