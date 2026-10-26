/* BENTO_MOD K7: reuse the exact native sample-editor rows. */
#include "step_lock_shared.h"
#include "kick_knobs.h"
#include "drum_models.h"
#include "../drums/mod_matrix.h"
#define MODEL ((void*)0x30024b00u)
#define PAD_KEY 0x1aau
#define LOAD_KEY 0x1adu
#define U ((volatile ViewState*)0x24043d20u)
typedef struct {u32 magic,view,active,third,wave;} ViewState;
static const char *const model_names[6]={"Kick","Snare","HiHat","Clap","Tom","Subtractive"};
static u32 model_slot(u32 m){return m==11?5:m==3?1:m==5?2:m==7?3:m==9?4:0;}
static const char load_name[]="Engine",click_name[]="Click",sync_name[]="Sync";
static const char *const names[7]={"Tune","Decay","Tone","Impact","Sweep","Sweep Dec","Punch"}; /* P10: Kick Dirt -> Punch */
static const char *label(u32 m,u32 i){return m==11?sub_labels[i]:m==3?snare_labels[i]:m==5?hat_labels[i]:m==7?clap_labels[i]:m==9?tom_labels[i]:names[i];}
static const unsigned short top[8]={2,0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9};
static const unsigned short bottom[8]={PAD_KEY,LOAD_KEY,4,0xe5,0x36,0x37,0x32,0x33};
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
int drum_assign(u32 pad,u32 *cell,u32 engine);
int drum_menu_event(void *event);
/* P11 (owner: drum synths loaded from the card show the sample page; the
 * synth page only via the burger menu). The file name/folder test (drum_path)
 * misses the path form the device stores, so a pad's file is also recognised
 * by its content: our carrier (48 kHz mono 16-bit, 144019 + id - 1 frames,
 * signature in the first 32 samples), exactly what the audio core checks.
 * Results are cached per file node handle (UI heap block). */
void **drum_cache_slot(void);
typedef struct {u32 magic,next,handle[8],model[8];} DrumCache;
static DrumCache *drum_cache(void){
 void **slot=drum_cache_slot();if(!slot)return 0;DrumCache *c=*slot;if(c)return c->magic==0x48434d44u?c:0;
 u32 cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(DrumCache)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 c=FN(0x08104c08,void*(*)(u32))(bytes);if((u32)c!=cursor)return 0;for(u32 i=0;i<sizeof(*c)/4;i++)((u32*)c)[i]=0;c->magic=0x48434d44u;*slot=c;return c;
}
static u32 carrier_open(const char *path){
 u32 file[22];for(u32 i=0;i<22;i++)file[i]=0;u8 b[108];char alt[260];
 if(FN(0x08120148,u32(*)(void*,const char*,u32))(file,path,1)){
  u32 n=0;alt[n++]='\\';for(u32 i=0;path[i]&&n<259;i++)alt[n++]=path[i];alt[n]=0;
  for(u32 i=0;i<22;i++)file[i]=0;if(FN(0x08120148,u32(*)(void*,const char*,u32))(file,alt,1))return 0;
 }
 u32 size=file[4],high=file[5],got=0;u32 r=FN(0x08120464,u32(*)(void*,void*,u32,u32*))(file,b,108,&got);FN(0x08120974,u32(*)(void*))(file);
 if(r||got!=108||high||size<44u||(size-44u)&1u)return 0;u32 frames=(size-44u)/2u;
 if(frames<144019u||frames>144029u)return 0;u32 id=frames-144018u;if(!(id&1u))return 0;
 if(W(b,0)!=0x46464952u||W(b,8)!=0x45564157u||W(b,24)!=48000u||H(b,22)!=1||H(b,34)!=16||W(b,40)!=frames*2u)return 0;
 for(u32 i=0;i<32;i++){u32 v=H(b,44+2*i),want=(0xb1e70a5cu>>i)&1u?1u:0xffffu;if(v!=want)return 0;}
 return id;
}
static u32 drum_file_model(u32 file,const char *path){
 u32 m=drum_path(path);if(m)return m;if(!file)return 0;
 DrumCache *c=drum_cache();
 if(c)for(u32 i=0;i<8;i++)if(c->handle[i]==file)return c->model[i];
 m=carrier_open(path);if(m==13)m=0;
 if(c){u32 i=c->next++&7u;c->handle[i]=file;c->model[i]=m;}
 return m;
}
__attribute__((used,retain)) int kick_ui_supported(void *v){
 if(!v || !W(v,0x87bc) || !W(v,0x87c4) || B(v,0x87cc)!=14)return 0;
 u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,(u8*)v+0x87bc);
 if(type!=1 && type!=2)return 0;
 char path[256];path[0]=0;FN(0x0813390e,int(*)(void*,void*,u32,char*))(MODEL,(u8*)v+0x87c4,0x81,path);
 return (int)drum_file_model(W(v,0x87c4),path);
}
static int registry(u32 model){
 u32 r=*(volatile u32*)0x30031484u;if(!r)return 0;
 for(u32 i=0;i<10;i++){
  u32 key=i<7?kick_keys[i]:i==7?PAD_KEY:i==8?LOAD_KEY:CLICK_KEY;void *d=(void*)(r+key*32);
  const char *name=i<7?label(model,i):i==7?model_names[model_slot(model)]:i==8?load_name:model==11?sync_name:click_name;
  if(H(d,0)){
   u32 old=W(d,4);int owned=old==(u32)name || old==(u32)load_name || old==(u32)click_name || old==(u32)sync_name;for(u32 j=0;j<6;j++)if(old==(u32)model_names[j])owned=1;
   for(u32 j=0;j<7;j++)if(old==(u32)names[j] || old==(u32)snare_labels[j] || old==(u32)hat_labels[j] || old==(u32)clap_labels[j] || old==(u32)tom_labels[j] || old==(u32)sub_labels[j])owned=1;
   if(!owned)return 0;
  }
 }
 for(u32 i=0;i<10;i++){
  u32 key=i<7?kick_keys[i]:i==7?PAD_KEY:i==8?LOAD_KEY:CLICK_KEY;void *d=(void*)(r+key*32);
  zero(d,32);H(d,0)=key;B(d,2)=i==8?7:2;if(i==8){W(d,8)=(u32)model_names;W(d,12)=6;}W(d,4)=(u32)(i<7?label(model,i):i==7?model_names[model_slot(model)]:i==8?load_name:model==11?sync_name:click_name);
  W(d,16)=i==0&&drum_family(model)==1?25:i==7?1:0;W(d,20)=i==0&&drum_family(model)==1?180:i==7?16:i==8?4:100;
 }return 1;
}
static void init(void){
 if(KNOBS->magic!=KNOBS_MAGIC){zero(KNOBS,sizeof(*KNOBS));zero((void*)CLICKS,128);KNOBS->magic=KNOBS_MAGIC;}
 if(U->magic!=0x3756494bu){zero((void*)U,sizeof(*U));U->magic=0x3756494bu;}
}
static KickKnob *entry(u32 handle,u32 model){
 KickKnob *chosen=0;u32 age=0;
 for(u32 i=0;i<128;i++){KickKnob *e=&KNOBS->entries[i];if(e->sequence && e->handle==handle){if(MOD_ENGINE(e->reserved)==model)return e;chosen=e;break;}if(!e->sequence && !chosen)chosen=e;}
 if(!chosen)for(u32 i=0;i<128;i++){KickKnob *e=&KNOBS->entries[i];u32 a=KNOBS->serial-e->sequence;if(!chosen || a>age){age=a;chosen=e;}}
 /* CH11: a pad whose sound changed engine keeps its routes for the old engine
  * (tag), silent until a synth route is edited on the new engine. */
 u32 keep=0;if(chosen->sequence && chosen->handle==handle){u32 r=chosen->reserved;keep=MOD_TAG(r)?MOD_TAG(r):MOD_ENGINE(r);}
 u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 chosen->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");chosen->handle=handle;chosen->reserved=(u8)(model|keep<<4);
 for(u32 j=0;j<7;j++)chosen->values[j]=drum_defaults(model)[j];
 CLICKS[chosen-KNOBS->entries]=model==11?0:kick_defaults[2];
 __asm__ volatile("dsb" ::: "memory");chosen->sequence=serial;KNOBS->serial=serial;return chosen;
}
static void update(KickKnob *e,u32 index,u32 value){
 u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 e->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");if(index==7)CLICKS[e-KNOBS->entries]=(u8)value;else e->values[index]=(u8)value;
 __asm__ volatile("dsb" ::: "memory");e->sequence=serial;KNOBS->serial=serial;__asm__ volatile("dsb" ::: "memory");
}
static void set_tag(KickKnob *e,u32 tag){
 if(MOD_TAG(e->reserved)==tag)return;u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 e->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");e->reserved=(u8)((e->reserved&15u)|tag<<4);
 __asm__ volatile("dsb" ::: "memory");e->sequence=serial;KNOBS->serial=serial;__asm__ volatile("dsb" ::: "memory");
}
static u32 pad(void *v){u32 n=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(u8*)v+0x87bc,0x73,&n);return n<16?n:0;}
static void rows(void *v,int custom){
 u32 handle=W(v,0x87bc);u32 model=custom?kick_ui_supported(v):0;
 for(u32 row=0;row<3;row++)for(u32 i=0;i<8;i++){
  W(v,0x701c+row*0x50+i*4)=handle;
  H(v,0x703c+row*0x50+i*2)=custom?(row==0?(drum_count(model)<7&&i>=6?0:top[i]):row==1?bottom[i]:model==11?(i==0?CLICK_KEY:i==1?0x1e:i==2?0x1f:i==3?0x20:i==4?0x21:0):model==1&&i==0?CLICK_KEY:0):H(v,0x6fdc+row*16+i*2);
 }
}
__attribute__((used,retain)) void kick_ui_before(void *v){
 init();u32 model=kick_ui_supported(v);int active=model && registry(model);
 if(active){
  if(!U->active || U->view!=(u32)v){U->view=(u32)v;U->active=1;U->third=B(v,0x4828+0x30);U->wave=B(v,0x71c0+0x30);}
  entry(W(v,0x87bc),model);rows(v,1);
  /* Key zero does not clear native text overrides left by the previous model. */
  for(u32 row=0;row<3;row++)for(u32 i=0;i<8;i++)if(!H(v,0x703c+row*0x50+i*2)){
   void *bar=(u8*)v+0x38+row*0x23f8,*slot=(u8*)bar+0x38+i*0x468;
   FN(0x08170656,void(*)(void*,u32,const char*))(bar,i,0);
   FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,0,0,1);
   FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,"");
  }
  B(v,0x4828+0x30)=model==1||model==11?0:1;B(v,0x71c0+0x30)=1;
 }else if(U->active && U->view==(u32)v){rows(v,0);
 for(u32 row=0;row<3;row++)for(u32 i=0;i<8;i++){
  void *bar=(u8*)v+0x38+row*0x23f8;u32 key=H(v,0x703c+row*0x50+i*2),value=0;
  FN(0x08170656,void(*)(void*,u32,const char*))(bar,i,0);
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(u8*)v+0x87bc,key,&value);
  FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)bar+0x38+i*0x468,key,(int)value,1);
 }
 B(v,0x4828+0x30)=(u8)U->third;B(v,0x71c0+0x30)=(u8)U->wave;U->active=0;}
}
static void text_value(void *bar,u32 index,u32 value,int percent){
 char text[16];u32 at=0;if(value>=1000)text[at++]='0'+value/1000%10;if(value>=100)text[at++]='0'+value/100%10;if(value>=10)text[at++]='0'+value/10%10;text[at++]='0'+value%10;
 if(percent)text[at++]='%';else{text[at++]=' ';text[at++]='H';text[at++]='z';}text[at]=0;
 FN(0x08170656,void(*)(void*,u32,const char*))(bar,index,text);
}
static void sub_text(void *bar,u32 index,u32 parameter,u32 value){
 if(parameter==3){text_value(bar,index,drum_exp2(35,value*85,1000),0);return;}
 if(parameter==1){
  int semi=(int)((value*48+50)/100)-24;char t[12];u32 n=0;
  if(semi<0){t[n++]='-';semi=-semi;}else t[n++]='+';
  if(semi>=10)t[n++]='0'+semi/10;t[n++]='0'+semi%10;t[n++]=' ';t[n++]='s';t[n++]='t';t[n]=0;
  FN(0x08170656,void(*)(void*,u32,const char*))(bar,index,t);return;
 }
 if(parameter==6){
  u32 ms=drum_exp2(12,value,10);char t[16];u32 n=0,div=10000;
  while(div>1&&ms<div)div/=10;do{t[n++]='0'+ms/div%10;div/=10;}while(div);
  t[n++]=' ';t[n++]='m';t[n++]='s';t[n]=0;
  FN(0x08170656,void(*)(void*,u32,const char*))(bar,index,t);return;
 }
 text_value(bar,index,value,1);
}
__attribute__((used,retain)) void kick_ui_after(void *v){
 if(!U->active || U->view!=(u32)v || !kick_ui_supported(v))return;
 u32 model=kick_ui_supported(v);KickKnob *e=entry(W(v,0x87bc),model);void *bar=(u8*)v+0x38;
 for(u32 i=0;i<drum_count(model);i++){
  void *slot=(u8*)bar+0x38+(i+1)*0x468;
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,kick_keys[i],e->values[i],1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,label(model,i));if(model==11)sub_text(bar,i+1,i,e->values[i]);else text_value(bar,i+1,i==0?drum_tune_hz(model,e->values[i]):e->values[i],i!=0);
 }
 if(model==1||model==11){
  void *third=(u8*)v+0x4828;
  FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)third+0x38,CLICK_KEY,CLICKS[e-KNOBS->entries],1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)third+0x38+0x3c8,model==11?sync_name:click_name);if(model==11 && !CLICKS[e-KNOBS->entries])FN(0x08170656,void(*)(void*,u32,const char*))(third,0,"Off");
  else text_value(third,0,CLICKS[e-KNOBS->entries],1);
 }
 void *mix=(u8*)v+0x2430;
 FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)mix+0x38,PAD_KEY,pad(v)+1,1);
 FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)mix+0x38+0x468,LOAD_KEY,(int)model_slot(model),1);
 char title[32];const char *prefix=model_names[model_slot(model)];u32 at=0;while(prefix[at]){title[at]=prefix[at];at++;}const char *pad_text=" / Pad ";for(u32 c=0;pad_text[c];c++)title[at++]=pad_text[c];u32 n=pad(v)+1;if(n>=10)title[at++]='1';title[at++]='0'+n%10;title[at]=0;
 FN(0x0817e85e,void(*)(void*,const char*))((u8*)v+0x80b4,title);
 /* Illustrative envelope in the existing native envelope widget. Audio's own
  * amplitude envelope is untouched; pitch-sweep drawing is deferred. */
 if(model!=11)FN(0x081689f8,void(*)(void*,u32,u32,u32,u32))((u8*)v+0x710c,0,e->values[1]*10,0,0);
}
__attribute__((used,retain)) int kick_ui_event(void *v,const void *event){
 if(H(event,0)!=0xcf || !kick_ui_supported(v))return 0;
 u32 key=W(event,8);int value=(int)W(event,12);init();u32 model=kick_ui_supported(v);
 for(u32 i=0;i<8;i++)if(key==(i==7?CLICK_KEY:kick_keys[i])){
  if(i==7&&model!=1&&model!=11)return 1;
  int lo=i==0&&drum_family(model)==1?25:0,hi=i==0&&drum_family(model)==1?180:100;if(value<lo)value=lo;if(value>hi)value=hi;
  update(entry(W(v,0x87bc),model),i,(u32)value);FN(0x0813130c,void(*)(void*))(MODEL);FN(0x08152144,void(*)(void*))(v);return 1;
 }
 if(key==PAD_KEY){if(value<1)value=1;if(value>16)value=16;FN(0x08152acc,void(*)(void*,u32))(v,(u32)value-1);return 1;}
 /* D1: Engine (was Browse) swaps the pad's synth; the pad keeps its place. */
 if(key==LOAD_KEY){if(value<0)value=0;if(value>4)value=4;if((u32)value!=model_slot(model)){u32 cell=W(v,0x87bc);drum_assign(pad(v),&cell,(u32)value);FN(0x08152144,void(*)(void*))(v);}return 1;}
 return 0;
}
/* Versioned attributes on the pad's existing params element. They do not
 * consume native automation lanes or change any original property value. */
static const char *const attrs[7]={"bento_kick_v1_tune","bento_kick_v1_decay","bento_kick_v1_tone","bento_kick_v1_impact","bento_kick_v1_sweep","bento_kick_v1_sweep_decay","bento_kick_v1_dirt"};
static KickKnob *existing(u32 handle){if(KNOBS->magic!=KNOBS_MAGIC)return 0;for(u32 i=0;i<128;i++)if(KNOBS->entries[i].sequence && KNOBS->entries[i].handle==handle)return &KNOBS->entries[i];return 0;}
static void analog_save(void *object,void *params);
static void analog_load(void *node,void *object);
extern void macro_save(void*,void*);extern void macro_load(void*,void*);extern int macro_increment(void*,int);
__attribute__((used,retain)) void kick_ui_save(void *object,void *params){
 macro_save(object,params); /* P27 */
 if(object && params && B(object,4)==18){analog_save(object,params);return;}
 if(!object || !params || (B(object,4)!=1 && B(object,4)!=2))return;
 KickKnob *e=existing(W(object,0x10));if(!e)return;
 void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_kick_version");if(!a)return;
 FN(0x0810958e,void(*)(void*,u32))(a,1);
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_drum_model");if(a)FN(0x0810958e,void(*)(void*,u32))(a,MOD_ENGINE(e->reserved));
 if(MOD_TAG(e->reserved)){a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_mod_engine");if(a)FN(0x0810958e,void(*)(void*,u32))(a,MOD_TAG(e->reserved));}
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_drum_v2_click");if(a)FN(0x0810958e,void(*)(void*,u32))(a,CLICKS[e-KNOBS->entries]);
 for(u32 i=0;i<7;i++){a=FN(0x08109cdc,void*(*)(void*,const char*))(params,attrs[i]);if(a)FN(0x0810958e,void(*)(void*,u32))(a,e->values[i]);}
}
__attribute__((used,retain)) void kick_ui_load(void *node,void *object){
 macro_load(node,object); /* P27 */
 if(node && object && B(object,4)==18){analog_load(node,object);return;}
 if(!node || !object || (B(object,4)!=1 && B(object,4)!=2) || !W(object,0x10))return;
 init();void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");
 u32 version=0;void *a=params?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_kick_version"):0;
 int valid=a && !FN(0x08109566,int(*)(void*,void*))(a,&version) && version==1;
 u32 model=1;void *m=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_drum_model"):0;if(m)FN(0x08109566,int(*)(void*,void*))(m,&model);if(model!=1&&model!=3&&model!=5&&model!=7&&model!=9&&model!=11)model=1;
 KickKnob *e=valid?entry(W(object,0x10),model):existing(W(object,0x10));if(!e)return;
 for(u32 i=0;i<7;i++){
  int value=drum_defaults(model)[i];u32 raw=0;
  a=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,attrs[i]):0;
  if(a && !FN(0x08109566,int(*)(void*,void*))(a,&raw))value=(int)raw;
  int lo=i==0&&drum_family(model)==1?25:0,hi=i==0&&drum_family(model)==1?180:100;if(value<lo)value=lo;if(value>hi)value=hi;update(e,i,(u32)value);
 }
 // Migrate old kicks with no Click attribute to their saved Tone amount.
 u32 cv=model==11?0:e->values[2];a=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_drum_v2_click"):0;
 if(a)FN(0x08109566,int(*)(void*,void*))(a,&cv);if(cv>100)cv=100;update(e,7,cv);
 u32 tag=0;a=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_mod_engine"):0;
 if(a && FN(0x08109566,int(*)(void*,void*))(a,&tag))tag=0;if(tag!=1&&tag!=3&&tag!=5&&tag!=7&&tag!=9&&tag!=11)tag=0;set_tag(e,tag);
}

/* Scale only custom synth controls: a reported ~20% turn becomes ~100%. */
__attribute__((used,retain)) int kick_ui_increment(void *slot,int delta){
 if(macro_increment(slot,delta))return 0; /* P27: macro strip owns the encoders */
 u32 key=H(slot,0x9c);int ours=key==CLICK_KEY || key==0x195;for(u32 i=0;i<7;i++)if(key==kick_keys[i])ours=1;
 if(!ours)return delta;if(delta>0x10000000)delta=0x10000000;if(delta<-0x10000000)delta=-0x10000000;return delta*5;
}

__attribute__((used,retain)) u32 drum_ui_step(u32 parent,u32 row,u32 *values){
 u32 cell=0,index=0,file=0;char path[256];
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i,&cell))break;
  u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell);if(type!=1 && type!=2)continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,0x73,&index);if(index!=row)continue;
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i+1,&file))return 0;
  if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&file)!=5)return 0;
  path[0]=0;FN(0x0813390e,int(*)(void*,void*,u32,char*))(MODEL,&file,0x81,path);u32 model=drum_file_model(file,path);if(!model || !registry(model))return 0;
  init();KickKnob *e=entry(cell,model);if(values){for(u32 j=0;j<7;j++)values[j]=e->values[j];values[7]=CLICKS[e-KNOBS->entries];}return model;
 }return 0;
}

/* CH11: drum-synth destinations in the native Mod Matrix (see mod_matrix.h).
 * Engine of a one-shot cell: same walk as drum_ui_step (cell, then its file). */
static u32 cell_model(u32 parent,u32 handle){
 u32 cell=0,file=0;char path[256];
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i,&cell))return 0;
  if(cell!=handle)continue;
  u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell);if(type!=1 && type!=2)return 0;
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i+1,&file))return 0;
  if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&file)!=5)return 0;
  path[0]=0;FN(0x0813390e,int(*)(void*,void*,u32,char*))(MODEL,&file,0x81,path);return drum_file_model(file,path);
 }return 0;
}
static const char *mod_label(u32 model,u32 j){return j==7?(model==11?sync_name:click_name):label(model,j);}
static void row_name(char *out,u32 model,u32 j){
 const char *a=model_names[model_slot(model)],*b=mod_label(model,j);u32 n=0;
 while(*a&&n<15)out[n++]=*a++;if(n<15)out[n++]=' ';while(*b&&n<15)out[n++]=*b++;while(n<16)out[n++]=0;
}
/* Called at 0814CE80, after the native one-shot rows (types 1/2) are built.
 * Matrix view +8AC44 cell, +8AC4D rows, +8AC50 keys (u16), +8ACCC row handles,
 * +8ADBC row byte, +8AE04 names (16 bytes). frame = the builder's stack, whose
 * +338 holds the current track. A synth pad lists its engine's parameters
 * first, then the native rows minus the sample envelope (Attack/Decay/Release),
 * which the synth instrument page does not offer. */
__attribute__((used,retain)) void mod_rows(void *view,void *frame){
 u8 *m=(u8*)view+0x8a000;u32 cell=W(m,0xc44),n=B(m,0xc4d);
 u32 model=cell&&n<=16?cell_model(W(frame,0x338),cell):0;if(!model)return;
 init();KickKnob *e=entry(cell,model);registry(model);
 u32 tag=MOD_TAG(e->reserved),shown=tag?tag:model,count=mod_count(shown);
 /* In place, no large stack buffers: drop the envelope rows, move the rest
  * down by count, then write the synth rows on top. */
 u32 k=0;
 for(u32 i=0;i<n;i++){
  u32 key=H(m,0xc50+2*i);if(model!=11&&(key==0x1e||key==0x1f||key==0x21))continue;
  if(k!=i){H(m,0xc50+2*k)=(unsigned short)key;W(m,0xccc+4*k)=W(m,0xccc+4*i);B(m,0xdbc+k)=B(m,0xdbc+i);for(u32 c=0;c<16;c++)B(m,0xe04+16*k+c)=B(m,0xe04+16*i+c);}
  k++;
 }
 for(u32 i=k;i-->0;){u32 r=count+i;H(m,0xc50+2*r)=H(m,0xc50+2*i);W(m,0xccc+4*r)=W(m,0xccc+4*i);B(m,0xdbc+r)=B(m,0xdbc+i);for(u32 c=0;c<16;c++)B(m,0xe04+16*r+c)=B(m,0xe04+16*i+c);}
 for(u32 j=0;j<count;j++){H(m,0xc50+2*j)=mod_keys[j];W(m,0xccc+4*j)=cell;B(m,0xdbc+j)=0;row_name((char*)m+0xe04+16*j,shown,j);}
 B(m,0xc4d)=(u8)(count+k);
}
/* Saved destination names: 0812F6A2 (write) and 0812FE52 (read) call these
 * instead of the registry token lookups. Synth descriptors exist only lazily. */
__attribute__((used,retain)) const char *mod_token(u32 key){
 int j=mod_index(key);return j>=0?mod_tokens[j]:FN(0x081666f8,const char*(*)(u32))(key);
}
__attribute__((used,retain)) u32 mod_key(const char *s){
 for(u32 j=0;s&&j<MOD_PARAMS;j++){const char *t=mod_tokens[j];u32 i=0;while(t[i]&&s[i]==t[i])i++;if(!t[i]&&!s[i])return mod_keys[j];}
 return FN(0x08166720,u32(*)(const char*))(s);
}
/* 08140924: a matrix edit (event: +4 cell, +8 key). Editing a synth route
 * adopts the pad's routes for its current engine. */
__attribute__((used,retain)) u32 mod_edit(void *model,void *event){
 if(mod_index(H(event,8))>=0){KickKnob *e=existing(W(event,4));if(e)set_tag(e,MOD_ENGINE(e->reserved));}
 return FN(0x08133388,u32(*)(void*,void*))(model,event);
}

/* A1 "Analog": a native Wavetable track (type 18) whose WT1/WT2 play analog
 * oscillators on M7. The track's handle gets a KickKnob entry with engine 13;
 * values[0] is Sync (0 off). It is created from the native instrument menu
 * (action 1052 in the free ninth cell) and saved on the track's params as
 * bento_analog / bento_analog_sync / bento_analog_glide (values[1], 0..100).
 * Stock firmware sees a Wavetable track. */
#define ANALOG 13u
#define ANALOG_ACTION 0x1052u
void analog_registry(void);
const char analog_label[] __attribute__((used,retain))="Analog";
static KickKnob *analog_entry(u32 handle){KickKnob *e=existing(handle);return e && MOD_ENGINE(e->reserved)==ANALOG?e:0;}
static void analog_clear(u32 handle){
 KickKnob *e=analog_entry(handle);if(!e)return;u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 e->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");e->handle=0;e->reserved=0;
 __asm__ volatile("dsb" ::: "memory");e->sequence=0;KNOBS->serial=serial;__asm__ volatile("dsb" ::: "memory");
}
static void analog_mark(u32 handle,u32 sync){if(!handle)return;init();KickKnob *e=entry(handle,ANALOG);if(e->values[0]!=(sync?1:0))update(e,0,sync?1:0);}
__attribute__((used,retain)) int analog_track(u32 handle){return analog_entry(handle)!=0;}
static void analog_save(void *object,void *params){
 KickKnob *e=analog_entry(W(object,0x10));if(!e)return;
 void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_analog");if(a)FN(0x0810958e,void(*)(void*,u32))(a,1);
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_analog_sync");if(a)FN(0x0810958e,void(*)(void*,u32))(a,e->values[0]);
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_analog_glide");if(a)FN(0x0810958e,void(*)(void*,u32))(a,e->values[1]);
}
static void analog_load(void *node,void *object){
 u32 handle=W(object,0x10);if(!handle)return;init();
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");u32 on=0,sync=0;
 void *a=params?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_analog"):0;
 if(a && FN(0x08109566,int(*)(void*,void*))(a,&on))on=0;
 if(!on){analog_clear(handle);return;}
 a=FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_analog_sync");if(a && FN(0x08109566,int(*)(void*,void*))(a,&sync))sync=0;
 analog_mark(handle,sync);
 u32 glide=0;a=FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_analog_glide");if(a && FN(0x08109566,int(*)(void*,void*))(a,&glide))glide=0;
 if(glide>100)glide=100;KickKnob *e=analog_entry(handle);if(e && e->values[1]!=glide)update(e,1,glide);
}
static u32 current_track(void){u32 t=0;return FN(0x08133cfc,int(*)(void*,void*))(MODEL,&t)?t:0;}
/* Instrument menu handler (view vtable 0819E52C, native 0814ECD4). */
__attribute__((used,retain)) u32 analog_menu_event(void *view,void *event){
 u32 code=H(event,0);
 if(code==ANALOG_ACTION){
  /* Same as the native Wavetable action (0814EF4E), then mark the track. */
  u32 index=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(void*)0x30030164u,0x131,&index);
  u32 ev[5]={0x42,0,6,index,0};FN(0x0816fc34,void(*)(void*,void*))(view,ev);
  u32 t=current_track();if(t && FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&t)==18){analog_registry();analog_mark(t,0);}
  u32 nav[5]={0x16,0,0,0,0};FN(0x0816fc34,void(*)(void*,void*))(view,nav);
  FN(0x0813130c,void(*)(void*))(MODEL);return 0;
 }
 u32 r=FN(0x0814ecd4,u32(*)(void*,void*))(view,event);
 if(code==0x102a){u32 t=current_track();if(t)analog_clear(t);}
 return r;
}

/* D1: drum synths without files to copy (owner, 2026-10-24).
 * The firmware writes the five synth marker WAVs itself (only when missing)
 * and loads one onto the pad through the native "file onto pad" function the
 * recorder uses (08139DE0: model, track index, &cell or &0, pad, path, 0).
 * One-shot pad menus get a "Drum Synth" entry (Kick); the synth page's second
 * bottom knob, Engine, switches Kick/Snare/HiHat/Clap/Tom. */
#define DRUM_ACTION 0x1056u
#define MENUS ((u8*)0x30030168u)
static const char drum_label[]="Drum Synth";
/* P7: files live in the firmware's own SD folder "Drum Synths" (drum_path
   recognises them there), so Load on an empty cell finds them in the browser. */
static const char drum_dir[]="Drum Synths";
static const char *const drum_files[5]={"Kick.wav","Snare.wav","HiHat.wav","Clap.wav","Tom.wav"};
static void fs_zero(u32 *f){for(u32 i=0;i<22;i++)f[i]=0;}
static int fs_write(void *f,const void *data,u32 n){u32 done=0;return !FN(0x08120604,u32(*)(void*,const void*,u32,u32*))(f,data,n,&done)&&done==n;}
static void drum_header(u32 *h,u32 frames){
 u32 bytes=frames*2u;h[0]=0x46464952u;h[1]=36u+bytes;h[2]=0x45564157u;h[3]=0x20746d66u;h[4]=16;h[5]=0x00010001u;h[6]=48000;h[7]=96000;h[8]=0x00100002u;h[9]=0x61746164u;h[10]=bytes;
}
static void drum_signature(u8 *p){for(u32 i=0;i<32;i++){u32 v=(0xb1e70a5cu&(1u<<i))?1u:0xffffu;p[i*2]=(u8)v;p[i*2+1]=(u8)(v>>8);}}
/* An existing file must be exactly our marker; a missing one is written. */
__attribute__((used,retain)) int drum_ensure(const char *path,u32 frames){
 u32 file[22],h[11];u8 buffer[512];drum_header(h,frames);fs_zero(file);
 if(!FN(0x08120148,u32(*)(void*,const char*,u32))(file,path,1)){
  u32 size=file[4],high=file[5],got=0;zero(buffer,108);
  u32 r=FN(0x08120464,u32(*)(void*,void*,u32,u32*))(file,buffer,108,&got);u32 c=FN(0x08120974,u32(*)(void*))(file);
  u8 sig[64];drum_signature(sig);int ok=!r&&!c&&got==108&&size==44u+frames*2u&&!high;
  for(u32 i=0;ok&&i<44;i++)if(buffer[i]!=((u8*)h)[i])ok=0;for(u32 i=0;ok&&i<64;i++)if(buffer[44+i]!=sig[i])ok=0;return ok;
 }
 fs_zero(file);if(FN(0x08120148,u32(*)(void*,const char*,u32))(file,path,10))return 0; /* create always, write (as the K7 report) */
 int ok=fs_write(file,h,44);zero(buffer,sizeof(buffer));drum_signature(buffer);if(ok)ok=fs_write(file,buffer,64);zero(buffer,64);
 for(u32 left=frames*2u-64u;ok&&left;){u32 n=left>sizeof(buffer)?sizeof(buffer):left;ok=fs_write(file,buffer,n);left-=n;}
 u32 c=FN(0x08120974,u32(*)(void*))(file);return ok&&!c;
}
/* Pad cell of the track (types 1/2, property 73 = pad), or 0. */
static u32 drum_cell(u32 track,u32 pad){
 u32 cell=0,index=0;
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&track,i,&cell))return 0;
  u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell);if(type!=1&&type!=2)continue;
  index=99;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,0x73,&index);if(index==pad)return cell;
 }return 0;
}
__attribute__((used,retain)) int drum_assign(u32 pad,u32 *cell,u32 engine){
 if(engine>4||pad>15)return 0;
 char path[256],fs[260];path[0]=0;
 /* Native project path join (08127D7C uses it for "Projects" + name). */
 FN(0x08104648,void(*)(char*,void*,const char*,const char*))(path,(void*)0x300010f4u,drum_dir,drum_files[engine]);
 u32 n=0;if(path[0]!='\\'&&path[0]!='/')fs[n++]='\\';for(u32 i=0;path[i]&&n<259;i++)fs[n++]=path[i];fs[n]=0;
 u32 index=0,track=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(void*)0x30030164u,0x131,&index);
 if(!FN(0x08133960,int(*)(void*,u32,u32*))(MODEL,index,&track)||!track)return 0;
 if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&track)!=14)return 0; /* one-shot tracks only */
 if(!drum_ensure(fs,144019u+2u*engine))return 0;
 u32 target=cell&&*cell?*cell:drum_cell(track,pad);
 FN(0x08139de0,void(*)(void*,u32,u32*,u32,const char*,u32))(MODEL,index,&target,pad,path,0);
 FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
/* Every one-shot pad menu (a native menu that offers Load WAV) gets the
 * entry; other track types never show it. Menus: 20 x 0xE0 at 30030168,
 * id +0, cells +4 (20 bytes: code, label, 0, 0, enabled), count +CC. */
__attribute__((used,retain)) void drum_menus(int show){
 for(u32 m=0;m<20;m++){
  u8 *menu=MENUS+m*0xe0;u32 n=B(menu,0xcc);if(n>10)continue;int load=-1,ours=-1;
  for(u32 i=0;i<n;i++){u32 c=H(menu,4+i*20);if(c==0x1046)load=(int)i;if(c==DRUM_ACTION)ours=(int)i;}
  if(load<0)continue;
  if(show&&ours<0&&n<9){ /* native menu apply shows at most nine entries (EU8) */u8 *c=menu+4+n*20;zero(c,20);W(c,0)=DRUM_ACTION;W(c,4)=(u32)drum_label;B(c,16)=1;B(menu,0xcc)=(u8)(n+1);}
  if(!show&&ours>=0){for(u32 i=(u32)ours;i+1<n;i++)for(u32 j=0;j<20;j++)B(menu,4+i*20+j)=B(menu,4+(i+1)*20+j);zero(menu+4+(n-1)*20,20);B(menu,0xcc)=(u8)(n-1);}
 }
}
static u32 track_type(void){u32 t=current_track();return t?FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&t):0;}
/* Model events (081403EC hook): menu opens (F0..100, 100C..100E) refresh the
 * entry; the entry itself turns the selected pad (track property 74) into a
 * Kick. The event goes on to the native handler, which closes the menu. */
/* One action per press even if both the model and the view see the code. */
static void drum_action(void){
 static volatile u32 *const when=(volatile u32*)0x24043d78u;u32 now=W((void*)0x3001fe2cu,0);
 if(*when&&now+1u-*when<300u)return;*when=now+1u; /* stored +1 so 0 means never */
 u32 t=current_track(),pad=0;if(t)FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&t,0x74,&pad);
 if(pad<16)drum_assign(pad,0,0);
}
__attribute__((used,retain)) int drum_menu_event(void *event){
 u32 code=H(event,0);
 if((code>=0xf0&&code<=0x100)||(code>=0x100c&&code<=0x100e)){drum_menus(track_type()==14);return 0;}
 if(code==DRUM_ACTION){drum_action();return 0;}
 return 0;
}
/* P6: 1.6P5 showed no entry on hardware: the menu-open requests evidently do
 * not all pass the model event entry. The entry is now kept in the menus from
 * every UI message (fx_dispatch), following the current track type, and the
 * action is also taken from the pad page view's event handler (0814888C,
 * vtable slot 0819DC50) in case the menu code goes to the view only. */
/* P7: once per boot (first UI message), make "\Drum Synths" and its five
   marker files if they are missing (about 1.4 MB the very first time; later
   boots only read 108 bytes per file). f_mkdir 08121152; FR_EXIST is fine. */
__attribute__((used,retain)) void drum_install_folder(void){
 static volatile u32 *const done=(volatile u32*)0x24043d7cu;if(*done==0x44524d46u)return;*done=0x44524d46u;
 FN(0x08121152,u32(*)(const char*))("\\Drum Synths");
 for(u32 i=0;i<5;i++){char fs[40];u32 n=0;const char *a="\\Drum Synths\\";while(*a)fs[n++]=*a++;for(const char *b=drum_files[i];*b;)fs[n++]=*b++;fs[n]=0;drum_ensure(fs,144019u+2u*i);}
}
__attribute__((used,retain)) void drum_menu_tick(void){
 /* Only once the native menus exist (built at boot by 081412EC). */
 int any=0;for(u32 m=0;m<20&&!any;m++){u8 *menu=MENUS+m*0xe0;u32 n=B(menu,0xcc);for(u32 i=0;i<n&&i<10;i++)if(H(menu,4+i*20)==0x1046)any=1;}
 if(!any)return;
 drum_install_folder(); /* the UI is up (menus built) */
 u32 t=current_track(),show=t&&FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&t)==14;
 drum_menus((int)show);
}
__attribute__((used,retain)) u32 drum_view_event(void *view,void *event){
 if(H(event,0)==DRUM_ACTION){drum_action();return 0;}
 return FN(0x0814888c,u32(*)(void*,void*))(view,event);
}


/* P4: Analog oscillator display. The Wavetable page (view class 0819E894)
 * shows WT1/WT2 in two wave panes (class 081B3A18, view +3550 and +36C8 =
 * oscillator index 0 and 1; label child at pane +104). P6: P4 hooked class
 * 081B3A98 (+2E90/+31F0), which the Wavetable builder (0815F6DA) hides; those
 * are the Granular panes, so nothing was drawn on hardware. On an Analog track the
 * pane hides its "No WAV" label and draws two cycles of the shape the
 * oscillator plays: saw > square > narrow pulse. While notes play the shape
 * comes from M7 (ANALOG_PUB, includes modulation such as LFO -> Shape, so
 * pulse-width modulation is visible); otherwise from the page's own Position
 * value (view +10154 + 4 x index). Redraws are limited to about 30 per second.
 * Paint gets ctx {full, partial, -, -, surface}; fills use 08166EF6. */
#define WAVE_VIEW 0x0819e894u
#define WAVE_STATE ((volatile u8*)0x24043d34u) /* shape0, shape1, flags (dirty 1/2, hidden 4/8), - ; +4 two 16-bit redraw times; +8 counter */
#define WAVE_COUNT (*(volatile u32*)0x24043d3cu) /* last M7 counter (low 16) and when it changed (high 16, ms) */
#define WFILL(r,c,s) FN(0x08166ef6,void(*)(const int*,u32,u32))(r,c,s)
static int analog_pane(void *w,u32 *idx){
 u8 *p=(u8*)W(w,0x2c);if(!p||W(p,0)!=WAVE_VIEW)return 0;
 if((u8*)w==p+0x3550)*idx=0;else if((u8*)w==p+0x36c8)*idx=1;else return 0;
 u32 t=current_track();return t&&FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&t)==18&&analog_entry(t);
}
static u32 wave_shape(void *w,u32 idx,u32 now){
 u8 *p=(u8*)W(w,0x2c);u32 t=current_track(),pub=ANALOG_PUB[1],c=pub>>16;
 if(c!=(WAVE_COUNT&0xffffu))WAVE_COUNT=c|(now<<16);
 if(ANALOG_PUB[0]==t&&((now-(WAVE_COUNT>>16))&0xffffu)<150u)return (pub>>(idx*8))&255u; /* notes playing */
 u32 v=W(p,0x10154+idx*4);return v>255?255:v;
}
/* Integer only (UI core code stays free of floating point). */
__attribute__((used,retain)) int analog_wave_value(u32 shape,u32 q){
 int blend=shape*2>256?256:(int)shape*2,width=512-(shape>128?(int)((shape-128)*3373/1000):0);
 int saw=(int)(q&1023)*2-1024,pulse=(int)(q&1023)<width?1024:-1024;return (saw*(256-blend)+pulse*blend)/256;
}
static void wave_draw(void *w,u32 shape,u32 surface){
 int x=(int)W(w,4),y=(int)W(w,8),wd=(int)W(w,12),ht=(int)W(w,16);if(wd<40||ht<20)return;
 /* P7: the pane's own colours (+174 line, +175 background), as native waveforms. */
 u32 track_index=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(void*)0x30030164u,0x131,&track_index);
 u32 line=FN(0x08140ebc,u32(*)(u32))(track_index),bg=B(w,0x175)?B(w,0x175):0xf1u;
 int r[4]={x,y,wd,ht};WFILL(r,bg,surface);
 int cy=y+ht/2,amp=ht*3/8,left=x+12,span=wd-24,prev=0;
 int mid[4]={left,cy,span,1};WFILL(mid,0xf3,surface);
 for(int i=0;i<span;i++){
  int v=analog_wave_value(shape,(u32)(i*2048/span)),yy=cy+v*amp/1024; /* native y grows towards the top of the screen (emulator renders) */
  int top=i?(prev<yy?prev:yy):yy,bot=i?(prev>yy?prev:yy):yy;
  int col[4]={left+i,top,2,bot-top+2};WFILL(col,line,surface);prev=yy;
 }
}
__attribute__((used,retain)) void analog_wave_tick(void *w,void *flags){
 u32 idx=0;void *label=(u8*)w+0x104;
 if(!analog_pane(w,&idx)){
  /* Not Analog (any more): give the native label back once. */
  u8 *p=(u8*)W(w,0x2c);u32 i=p&&(u8*)w==p+0x36c8?1:0;
  if(p&&W(p,0)==WAVE_VIEW&&(WAVE_STATE[2]&(4u<<i))){B(label,0x30)=0;B(w,0x31)=1;WAVE_STATE[2]&=(u8)~(4u<<i);}
  FN(0x081822a4,void(*)(void*,void*))(w,flags);return;
 }
 if(!B(label,0x30)){B(label,0x30)=1;WAVE_STATE[2]|=(u8)((4u<<idx)|(1u<<idx));} /* hidden by us; redraw */
 u32 ti=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(void*)0x30030164u,0x131,&ti);
 u32 colour=FN(0x08140ebc,u32(*)(u32))(ti);if(B(w,0x174)!=colour){B(w,0x174)=(u8)colour;WAVE_STATE[2]|=(u8)(1u<<idx);}
 u32 now=W((void*)0x3001fe2cu,0),s=wave_shape(w,idx,now);
 volatile unsigned short *last=(volatile unsigned short*)0x24043d38u; /* per pane, ms (16 bit) */
 if(s!=WAVE_STATE[idx]&&(unsigned short)(now-last[idx])>=33){WAVE_STATE[idx]=(u8)s;WAVE_STATE[2]|=(u8)(1u<<idx);last[idx]=(unsigned short)now;}
 if(WAVE_STATE[2]&(1u<<idx))B(w,0x32)=1; /* the native tick turns this into a partial repaint */
 FN(0x081822a4,void(*)(void*,void*))(w,flags);
}
__attribute__((used,retain)) void analog_wave_paint(void *w,void *ctx){
 FN(0x08182314,void(*)(void*,void*))(w,ctx);
 u32 idx=0;if(!analog_pane(w,&idx))return;
 if(!B(ctx,0)&&!(WAVE_STATE[2]&(1u<<idx)))return;
 wave_draw(w,WAVE_STATE[idx],W(ctx,4));WAVE_STATE[2]&=(u8)~(1u<<idx);
}

/* A1 Sync: key 1D1 (free in the stock registry) in WT2's empty fourth slot of
 * the native Wavetable osc page (table 0819E91C). Value reads go through the
 * fx_get property hook; changes (event CF) are taken at the model's event
 * entry (081403EC) so the native model never stores the private key. */
#define ANALOG_SYNC_KEY 0x1d1u
#define ANALOG_GLIDE_KEY 0x142u
static const char analog_sync_name[]="Sync",analog_glide_name[]="Glide",analog_shape_name[]="Shape";
static void analog_descriptor(u32 key,const char *name,u32 type,u32 hi){
 u32 r=*(volatile u32*)0x30031484u;if(!r)return;void *d=(void*)(r+key*32);
 if(H(d,0)==key && W(d,4)==(u32)name)return;
 if(H(d,0) && W(d,4)!=(u32)name)return; /* someone else owns it */
 zero(d,32);H(d,0)=(unsigned short)key;B(d,2)=(u8)type;W(d,4)=(u32)name;W(d,16)=0;W(d,20)=hi;
}
__attribute__((used,retain)) void analog_registry(void){
 analog_descriptor(ANALOG_SYNC_KEY,analog_sync_name,6,1);analog_descriptor(ANALOG_GLIDE_KEY,analog_glide_name,10,1000);
}
__attribute__((used,retain)) int analog_get(u32 key,void *out){
 if((key!=ANALOG_SYNC_KEY && key!=ANALOG_GLIDE_KEY) || !out)return 0;analog_registry();
 KickKnob *e=analog_entry(current_track());
 W(out,0)=!e?0:key==ANALOG_SYNC_KEY?(e->values[0]?1:0):(u32)e->values[1]*10;return 1;
}
__attribute__((used,retain)) int analog_model_event(void *model,void *event){
 extern int macro_model_event(void*);macro_model_event(event); /* P27: armed macro maps what is turned */
 extern int seq_nav_global(void*,void*);if(seq_nav_global(model,event))return 1;
 if(drum_menu_event(event))return 1;
 (void)model;u32 key=W(event,8);if(H(event,0)!=0xcf || (key!=ANALOG_SYNC_KEY && key!=ANALOG_GLIDE_KEY))return 0;
 u32 t=current_track();KickKnob *e=analog_entry(t);
 if(e){
  if(key==ANALOG_SYNC_KEY)analog_mark(t,W(event,12)?1:0);
  else{int v=(int)W(event,12);if(v<0)v=0;if(v>1000)v=1000;u32 g=((u32)v+5)/10;if(e->values[1]!=g)update(e,1,g);}
  FN(0x0813130c,void(*)(void*))(MODEL);
 }
 return 1;
}
/* A1 page details, applied when the native synth page builder (0815F52C)
 * copies its control-key table (memcpy at 0815F5AE granular, 0815F68E
 * wavetable). An Analog track gets Glide in WT1's empty fourth slot and Sync
 * in WT2's; Position reads "Shape"; the waveform pane says "Analog" instead of
 * "No WAV". Plain Wavetable/Granular pages keep everything native. The pane
 * texts are read from two UI-RAM buffers (24043D4C, 24043D58) that the native
 * code copies into its text widgets. */
#define PANE_TITLE ((char*)0x24043d4cu)
#define PANE_HINT ((char*)0x24043d58u)
#define POSITION_TITLE 0x0818d5b8u
static void copy_text(char *dst,const char *src,u32 max){u32 i=0;for(;src[i] && i+1<max;i++)dst[i]=src[i];dst[i]=0;}
__attribute__((used,retain)) void analog_page_keys(unsigned short *dst,const unsigned short *src,u32 bytes,u32 wavetable){
 for(u32 i=0;i<bytes/2;i++)dst[i]=src[i];
 u32 t=wavetable?current_track():0;int analog=t && analog_entry(t);
 u32 r=*(volatile u32*)0x30031484u;void *position=r?(void*)(r+0xc9*32):0;
 if(analog){
  analog_registry();dst[3]=ANALOG_GLIDE_KEY;dst[8+3]=ANALOG_SYNC_KEY;
  if(position && H(position,0)==0xc9)W(position,4)=(u32)analog_shape_name;
  copy_text(PANE_TITLE,"Analog",12);copy_text(PANE_HINT,"Saw > Square > Pulse",24);
 }else{
  if(position && H(position,0)==0xc9 && W(position,4)==(u32)analog_shape_name)W(position,4)=POSITION_TITLE;
  copy_text(PANE_TITLE,"No WAV",12);copy_text(PANE_HINT,"Double-tap to load WAV",24);
 }
}
