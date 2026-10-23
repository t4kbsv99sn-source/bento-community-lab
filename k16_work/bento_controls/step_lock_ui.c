/* BENTO_MOD L7: two native spare Event encoders, lossless note-owned locks. */
#include "step_lock_shared.h"
#define MODEL ((void*)0x30024b00u)
#define PICKER 0x1dau
#define PICKER2 0x1e4u
static u32 picker(u32 i){return i?PICKER2:PICKER;}
#define MAGIC 0x47555042u
typedef struct {u32 seq,drum,kind,kind2;} Target;
typedef struct {u32 magic,view,seq,drum,kind,shift,pick,changed,error,next,selection,kind2,pick2,changed2;Target targets[64];} UI;
#define U ((volatile UI*)0x24048000u)
static const char *const native_choices[]={"Remove lock","Level","Pitch","Pan","Filter","Resonance","Attack","Decay","Sustain","Release","Delay Send","Reverb Send"};
static const char *const titles[]={"Lock target","Lock Level","Lock Pitch","Lock Pan","Lock Filter","Lock Resonance","Lock Attack","Lock Decay","Lock Sustain","Lock Release","Lock Delay Send","Lock Reverb Send"};
static const char *const titles2[]={"Lock 2 target","Lock 2 Level","Lock 2 Pitch","Lock 2 Pan","Lock 2 Filter","Lock 2 Resonance","Lock 2 Attack","Lock 2 Decay","Lock 2 Sustain","Lock 2 Release","Lock 2 Delay Send","Lock 2 Reverb Send"};
#define CHOICES ((const char**)0x24048480u)
static const char *const synth_names[]={"Kick Tune","Kick Decay","Kick Tone","Kick Impact","Kick Sweep","Kick Sweep Dec","Kick Dirt","Kick Click","Snare Tune","Snare Decay","Snare FM","Snare Impact","Snare Snappy","HiHat Tune","HiHat Decay","HiHat Tone","HiHat Impact","HiHat Noise"};
static u32 engine(void *v,u32 *values){return FN(0x081bb080,u32(*)(u32,u32,u32*))(W(v,0x113e8),W(v,0x11400),values);}
static u32 first(u32 m){return m==1?12:m==3?20:m==5?25:0;}
static u32 total(u32 m){return m==1?20:(m==3||m==5)?17:12;}
static u32 to_kind(u32 v,u32 m){return v<12?v:first(m)+v-12;}
static u32 to_pick(u32 k,u32 m){return k<12?k:synth_model(k)==m?k-first(m)+12:0;}
static u32 kind(u32 i){return i?U->kind2:U->kind;}
static void setkind(u32 i,u32 k){if(i)U->kind2=k;else U->kind=k;}
static u32 pick(u32 i){return i?U->pick2:U->pick;}
static void setpick(u32 i,u32 k){if(i)U->pick2=k;else U->pick=k;}
static void init(void){if(U->magic!=MAGIC){for(u32 i=0;i<sizeof(UI)/4;i++)((volatile u32*)U)[i]=0;U->magic=MAGIC;}}
static int supported(void *v){return v && !B(v,0x113e0) && W(v,0x113e4) && W(v,0x113dc) && W(v,0x11400)<16 && FN(0x08133f7c,u32(*)(void*,void*))(MODEL,(u8*)v+0x113e8)==14;}
static int snapshot(void *v,u32 *e){return FN(0x0815ba04,int(*)(void*,void*))(v,e);}
static void remember(void){
 u32 slot=64;for(u32 i=0;i<64;i++)if(U->targets[i].seq==U->seq && U->targets[i].drum==U->drum){slot=i;break;}
 if(slot==64)slot=U->next++&63;
 U->targets[slot].seq=U->seq;U->targets[slot].drum=U->drum;U->targets[slot].kind=U->kind;U->targets[slot].kind2=U->kind2;
}
static void context(void *v){
 init();u32 seq=W(v,0x113e4),drum=W(v,0x11400);
 if(U->view==(u32)v && U->seq==seq && U->drum==drum)return;
 U->view=(u32)v;U->seq=seq;U->drum=drum;U->error=0;U->changed=0;U->changed2=0;U->selection=0;U->kind=1;U->kind2=4;
 for(u32 i=0;i<64;i++)if(U->targets[i].seq==seq && U->targets[i].drum==drum){U->kind=U->targets[i].kind;U->kind2=U->targets[i].kind2;break;}
 u32 e[6];for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;
  if(B(e,0)!=1 || H(e,2)!=drum || !has_locks(e[5]))continue;
  for(u32 j=0;j<2;j++){u32 k=lock_kind(lock_slot(e[5],j));if(k)setkind(j,k);}break;
 }
 if(U->kind==U->kind2)U->kind2=U->kind==4?1:4;
 U->pick=U->kind;U->pick2=U->kind2;
}
static int registry(u32 m){
 for(u32 i=0;i<total(m);i++)CHOICES[i]=i<12?native_choices[i]:synth_names[to_kind(i,m)-12];
 u32 r=*(volatile u32*)0x30031484u;if(!r)return 0;
 for(u32 j=0;j<2;j++){
  void *d=(void*)(r+picker(j)*32);const char *title=j?titles2[0]:titles[0];
  if(H(d,0) && W(d,4)!=(u32)title)return 0;
  for(u32 i=0;i<8;i++)W(d,i*4)=0;
  H(d,0)=picker(j);B(d,2)=7;W(d,4)=(u32)title;W(d,8)=(u32)CHOICES;W(d,12)=total(m);
 }return 1;
}
static int background(void *v,u32 k){
 if(k>11){u32 values[8];u32 m=engine(v,values);return synth_model(k)==m?(int)values[synth_index(k)]:0;}
 u32 parent=W(v,0x113e8),cell=0,idx=0,value=0;
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i,&cell))break;
  if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell)!=1)continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,0x73,&idx);if(idx!=W(v,0x11400))continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,native_key(k),&value);return (int)value;
 }return 0;
}
__attribute__((used)) void locks_header_before(void *v){
 H((void*)0x300000bcu,8)=0;H((void*)0x300000bcu,10)=0;if(!supported(v))return;context(v);
 if(!U->shift){u32 e[6]={0};int has=snapshot(v,e);u32 id=has?e[3]:0;
  if(id!=U->selection){for(u32 i=0;i<2;i++){u32 k=has?lock_kind(lock_slot(e[5],i)):0;if(k)setkind(i,k);}U->selection=id;
   if(U->kind==U->kind2)U->kind2=U->kind==4?1:4;
  }
 }
 u32 m=engine(v,0);
 for(u32 i=0;i<2;i++)if(kind(i)>11 && synth_model(kind(i))!=m)setkind(i,i?4:1);
 if(U->kind==U->kind2)U->kind2=U->kind==4?1:4;
 if(!registry(m))return;
 for(u32 i=0;i<2;i++)H((void*)0x300000bcu,8+i*2)=U->shift?picker(i):native_key(kind(i));
}
__attribute__((used)) void locks_grid(void *v){
 if(!supported(v))return;
 u32 marked=0,e[6],base=W(v,0x113f4),length=W(v,0x113f8);
 for(u32 j=0;j<511;j++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),j,e))break;
  if(B(e,0)!=1 || H(e,2)!=W(v,0x11400) || !has_locks(e[5]))continue;
  int time=(int)e[1],q=time%960;if(q>480)q-=960;int step=(time-q)/960;
  if(step>=(int)base && step-(int)base<32 && step<(int)length)marked|=1u<<(step-base);
 }
 for(u32 i=0;i<32;i++){
  u32 n=base+i+1;char text[12];u32 at=0;
  int selected=FN(0x0815b9c0,int(*)(void*,u32))(v,base+i) && base+i<length;
  if(selected)text[at++]='[';
  if(n>=1000)text[at++]='0'+n/1000%10;
  if(n>=100)text[at++]='0'+n/100%10;
  if(n>=10)text[at++]='0'+n/10%10;
  text[at++]='0'+n%10;if(marked&(1u<<i))text[at++]='*';if(selected)text[at++]=']';text[at]=0;
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)v+0x34+i*0x704+0x13c,text);
 }
 /* Never invoke the playback updater with an invented position. */
}

__attribute__((used)) void locks_header_after(void *v){
 if(!supported(v) || U->view!=(u32)v || !H((void*)0x300000bcu,8))return;
 locks_grid(v);void *bar=(u8*)v+0xebf0;u32 e[6]={0};int has=snapshot(v,e);
 for(u32 i=0;i<2;i++){
  void *slot=(u8*)bar+0x38+(4+i)*0x468;u32 k=kind(i),w=has?lock_slot(e[5],i):0;
  int value=U->shift?(int)to_pick(pick(i),engine(v,0)):lock_kind(w)==k?decode_value(w):background(v,k);
  B(slot,0x2c8)=0; /* Clear an old --/error override before native formatting. */
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,U->shift?picker(i):native_key(k),value,1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,(!U->shift&&k>11)?synth_names[k-12]:i?titles2[U->shift?0:k]:titles[U->shift?0:k]);
  if(U->error)FN(0x08170656,void(*)(void*,u32,const char*))(bar,4+i,"Target already used");
  else if(!U->shift && lock_kind(w)!=k)FN(0x08170656,void(*)(void*,u32,const char*))(bar,4+i,"--");
 }
}
static void refresh(void *v){FN(0x0815c27c,void(*)(void*))(v);}
static void protect_release(void *v){u32 now=*(volatile u32*)0x30035f40u,past=now-1001u;if(!past)past=0xffffffffu;for(u32 i=0;i<32;i++)if(W(v,0x11420+i*4))W(v,0x11420+i*4)=past;}
static int matches(void *v,u32 *e){
 if(B(e,0)!=1 || H(e,2)!=W(v,0x11400))return 0;int time=(int)e[1],q=time%960;if(q>480)q-=960;
 return FN(0x0815b9c0,int(*)(void*,u32))(v,(u32)((time-q)/960));
}
/* which=0/1 edits one lock; 2 clears both. Preflight avoids partial multi-edits. */
static void edit(void *v,u32 word,u32 which){
 if(!FN(0x0815bab0,int(*)(void*))(v))return;protect_release(v);u32 e[6],changed=0;
 if(word && which<2)for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;
  if(matches(v,e) && lock_kind(lock_slot(e[5],1-which))==lock_kind(word)){U->error=1;return;}
 }
 for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;if(!matches(v,e))continue;
  u32 a=which==0?word:lock_slot(e[5],0),b=which==1?word:lock_slot(e[5],1),packed=which==2?0:pack_locks(a,b);
  if(packed==e[5] || packed==0xffffffffu)continue;e[5]=packed;
  FN(0x0810d1aa,void(*)(void*,void*))((void*)W(v,0x113dc),e);changed=1;
 }
 if(changed){FN(0x08136544,void(*)(void*,void*,void*))(MODEL,(u8*)v+0x113e4,(void*)W(v,0x113dc));FN(0x0815c4b8,void(*)(void*))(v);}
}
__attribute__((used)) int locks_encoder(void *v,u32 key,int value){
 if(!supported(v))return 0;context(v);
 if(U->shift && (key==PICKER || key==PICKER2)){
  u32 i=key==PICKER2,m=engine(v,0);if(value<0)value=0;if(value>=(int)total(m))value=(int)total(m)-1;value=(int)to_kind((u32)value,m);U->error=0;protect_release(v);*(volatile u32*)0x24048d6cu=1;
  setpick(i,(u32)value);if(i)U->changed2=1;else U->changed=1;
  if(value){u32 e[6]={0};snapshot(v,e);
   if((u32)value==kind(1-i)){
    if(lock_kind(lock_slot(e[5],1-i))==(u32)value){U->error=1;setpick(i,kind(i));refresh(v);return 1;}
    setkind(1-i,kind(i));setpick(1-i,kind(1-i));
   }
   setkind(i,(u32)value);remember();
  }refresh(v);return 1;
 }
 if(!U->shift)for(u32 i=0;i<2;i++)if(key==native_key(kind(i))){U->error=0;edit(v,encode_value(kind(i),value),i);refresh(v);return 1;}
 return 0;
}
__attribute__((used,section(".proj"))) void locks_proj(void *model,u32 down){
 init();void *v=(void*)U->view;u32 was=U->shift;if(!down)U->shift=0;
 if(B(model,0x12c)!=0x27 || !supported(v))return;context(v);
 if(down){u32 e[6]={0};U->selection=snapshot(v,e)?e[3]:0;U->shift=1;U->pick=U->kind;U->pick2=U->kind2;U->changed=U->changed2=U->error=0;}
 else{if(was && U->changed && !U->pick)edit(v,0,0);if(was && U->changed2 && !U->pick2)edit(v,0,1);U->changed=U->changed2=U->error=0;}refresh(v);
}
__attribute__((used)) void locks_save(void *node,const void *e){
 if(B(e,0)!=1)return;
 for(u32 i=0;i<2;i++){u32 w=lock_slot(W(e,20),i);
  void *a=FN(0x08109cdc,void*(*)(void*,const char*))(node,i?"bento_lock2_v1":"bento_lock1_v1");if(a)FN(0x0810958e,void(*)(void*,u32))(a,w);
 }
}
__attribute__((used)) void locks_load(void *node,void *e){
 if(B(e,0)!=1)return;u32 w[2]={0,0};
 for(u32 i=0;i<2;i++){void *a=FN(0x08109c64,void*(*)(void*,const char*))(node,i?"bento_lock2_v1":"bento_lock1_v1");u32 x=0;
  if(a && !FN(0x08109566,int(*)(void*,void*))(a,&x) && lock_kind(x))w[i]=x;
 }if(w[0] && lock_kind(w[0])==lock_kind(w[1]))w[1]=0;W(e,20)=pack_locks(w[0],w[1]);
}
__attribute__((used,section(".clear"))) void locks_clear(void *model){init();void *v=(void*)U->view;if(B(model,0x12c)!=0x27 || !supported(v))return;context(v);U->error=0;edit(v,0,2);refresh(v);}
__attribute__((used,section(".padclear"))) void locks_pad_clear(void *v,u32 local){
 if(!supported(v) || local>=32 || !*(volatile u32*)0x24048d68u)return;context(v);U->error=0;protect_release(v);*(volatile u32*)0x24048d6cu=1;
 u32 absolute=W(v,0x113f4)+local,e[6],changed=0;
 for(u32 j=0;j<511;j++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),j,e))break;
  if(B(e,0)!=1 || H(e,2)!=W(v,0x11400) || !has_locks(e[5]))continue;
  int time=(int)e[1],q=time%960;if(q>480)q-=960;if((u32)((time-q)/960)!=absolute)continue;
  e[5]=0;FN(0x0810d1aa,void(*)(void*,void*))((void*)W(v,0x113dc),e);changed=1;
 }
 if(changed){FN(0x08136544,void(*)(void*,void*,void*))(MODEL,(u8*)v+0x113e4,(void*)W(v,0x113dc));FN(0x0815c4b8,void(*)(void*))(v);}
}
/* Sequencer owns +13 playhead overlay. +12 belongs to instrument playback
 * feedback, which native 0813C318 normally stops updating on page 27. Clear
 * only the stale instrument layer, including highlights arriving after return. */
__attribute__((used,section(".leds"))) void seq_lights_clean(void *model){
 if(B(model,0x12c)!=0x27)return;
 void *led=(u8*)model+0x19c4;u32 changed=0;
 for(u32 i=0;i<16;i++)if(B(led,i*16+12)){B(led,i*16+12)=0;changed=1;}
 if(changed)FN(0x081257f0,void(*)(void*))(led);
}

/* Codec exports for exact native-code migration/round-trip regression checks. */
__attribute__((used)) u32 locks_pack(u32 a,u32 b){return pack_locks(a,b);}
__attribute__((used)) u32 locks_slot(u32 w,u32 i){return lock_slot(w,i);}
