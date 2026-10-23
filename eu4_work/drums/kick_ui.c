/* BENTO_MOD K7: reuse the exact native sample-editor rows. */
#include "step_lock_shared.h"
#include "kick_knobs.h"
#include "drum_models.h"
#define MODEL ((void*)0x30024b00u)
#define PAD_KEY 0x1aau
#define LOAD_KEY 0x1adu
#define U ((volatile ViewState*)0x24043d20u)
typedef struct {u32 magic,view,active,third,wave;} ViewState;
static const char *const model_names[3]={"Kick","Snare","HiHat"};
static const char load_name[]="Load",click_name[]="Click";
static const char *const names[7]={"Tune","Decay","Tone","Impact","Sweep","Sweep Dec","Dirt"};
static const unsigned short top[8]={2,0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9};
static const unsigned short bottom[8]={PAD_KEY,LOAD_KEY,4,0xe5,0x36,0x37,0x32,0x33};
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
__attribute__((used)) int kick_ui_supported(void *v){
 if(!v || !W(v,0x87bc) || !W(v,0x87c4) || B(v,0x87cc)!=14)return 0;
 u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,(u8*)v+0x87bc);
 if(type!=1 && type!=2)return 0;
 char path[256];path[0]=0;FN(0x0813390e,int(*)(void*,void*,u32,char*))(MODEL,(u8*)v+0x87c4,0x81,path);
 return (int)drum_path(path);
}
static int registry(u32 model){
 u32 r=*(volatile u32*)0x30031484u;if(!r)return 0;
 for(u32 i=0;i<10;i++){
  u32 key=i<7?kick_keys[i]:i==7?PAD_KEY:i==8?LOAD_KEY:CLICK_KEY;void *d=(void*)(r+key*32);
  const char *name=i<7?(model==3?snare_labels[i]:model==5?hat_labels[i]:names[i]):i==7?model_names[model==3?1:model==5?2:0]:i==8?load_name:click_name;
  if(H(d,0)){
   u32 old=W(d,4);int owned=old==(u32)name || old==(u32)model_names[0] || old==(u32)model_names[1] || old==(u32)model_names[2] || old==(u32)load_name || old==(u32)click_name;
   for(u32 j=0;j<7;j++)if(old==(u32)names[j] || old==(u32)snare_labels[j] || old==(u32)hat_labels[j])owned=1;
   if(!owned)return 0;
  }
 }
 for(u32 i=0;i<10;i++){
  u32 key=i<7?kick_keys[i]:i==7?PAD_KEY:i==8?LOAD_KEY:CLICK_KEY;void *d=(void*)(r+key*32);
  zero(d,32);H(d,0)=key;B(d,2)=i==8?6:2;W(d,4)=(u32)(i<7?(model==3?snare_labels[i]:model==5?hat_labels[i]:names[i]):i==7?model_names[model==3?1:model==5?2:0]:i==8?load_name:click_name);
  W(d,16)=i==0&&model==1?25:i==7?1:0;W(d,20)=i==0&&model==1?180:i==7?16:i==8?1000:100;
 }return 1;
}
static void init(void){
 if(KNOBS->magic!=KNOBS_MAGIC){zero(KNOBS,sizeof(*KNOBS));zero((void*)CLICKS,128);KNOBS->magic=KNOBS_MAGIC;}
 if(U->magic!=0x3756494bu){zero((void*)U,sizeof(*U));U->magic=0x3756494bu;}
}
static KickKnob *entry(u32 handle,u32 model){
 KickKnob *chosen=0;u32 age=0;
 for(u32 i=0;i<128;i++){KickKnob *e=&KNOBS->entries[i];if(e->sequence && e->handle==handle){if((e->reserved?e->reserved:1)==model)return e;chosen=e;break;}if(!e->sequence && !chosen)chosen=e;}
 if(!chosen)for(u32 i=0;i<128;i++){KickKnob *e=&KNOBS->entries[i];u32 a=KNOBS->serial-e->sequence;if(!chosen || a>age){age=a;chosen=e;}}
 u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 chosen->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");chosen->handle=handle;chosen->reserved=(u8)model;
 for(u32 j=0;j<7;j++)chosen->values[j]=drum_defaults(model)[j];
 CLICKS[chosen-KNOBS->entries]=kick_defaults[2];
 __asm__ volatile("dsb" ::: "memory");chosen->sequence=serial;KNOBS->serial=serial;return chosen;
}
static void update(KickKnob *e,u32 index,u32 value){
 u32 serial=(KNOBS->serial+2u)&~1u;if(!serial)serial=2;
 e->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");if(index==7)CLICKS[e-KNOBS->entries]=(u8)value;else e->values[index]=(u8)value;
 __asm__ volatile("dsb" ::: "memory");e->sequence=serial;KNOBS->serial=serial;__asm__ volatile("dsb" ::: "memory");
}
static u32 pad(void *v){u32 n=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(u8*)v+0x87bc,0x73,&n);return n<16?n:0;}
static void rows(void *v,int custom){
 u32 handle=W(v,0x87bc);u32 model=custom?kick_ui_supported(v):0;
 for(u32 row=0;row<3;row++)for(u32 i=0;i<8;i++){
  W(v,0x701c+row*0x50+i*4)=handle;
  H(v,0x703c+row*0x50+i*2)=custom?(row==0?(model!=1&&i>=6?0:top[i]):row==1?bottom[i]:model==1&&i==0?CLICK_KEY:0):H(v,0x6fdc+row*16+i*2);
 }
}
__attribute__((used)) void kick_ui_before(void *v){
 init();u32 model=kick_ui_supported(v);int active=model && registry(model);
 if(active){
  if(!U->active || U->view!=(u32)v){U->view=(u32)v;U->active=1;U->third=B(v,0x4828+0x30);U->wave=B(v,0x71c0+0x30);}
  entry(W(v,0x87bc),model);rows(v,1);B(v,0x4828+0x30)=model==1?0:1;B(v,0x71c0+0x30)=1;
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
__attribute__((used)) void kick_ui_after(void *v){
 if(!U->active || U->view!=(u32)v || !kick_ui_supported(v))return;
 u32 model=kick_ui_supported(v);KickKnob *e=entry(W(v,0x87bc),model);void *bar=(u8*)v+0x38;
 for(u32 i=0;i<(model!=1?5u:7u);i++){
  void *slot=(u8*)bar+0x38+(i+1)*0x468;
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,kick_keys[i],e->values[i],1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,model==3?snare_labels[i]:model==5?hat_labels[i]:names[i]);text_value(bar,i+1,i==0&&model==3?80+e->values[i]*12:i==0&&model==5?100+e->values[i]*107/10:e->values[i],i!=0);
 }
 if(model==1){
  void *third=(u8*)v+0x4828;
  FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)third+0x38,CLICK_KEY,CLICKS[e-KNOBS->entries],1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)third+0x38+0x3c8,"Click");text_value(third,0,CLICKS[e-KNOBS->entries],1);
 }
 void *mix=(u8*)v+0x2430;
 FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)mix+0x38,PAD_KEY,pad(v)+1,1);
 FN(0x08171c1c,void(*)(void*,u32,int,u32))((u8*)mix+0x38+0x468,LOAD_KEY,0,1);
 FN(0x08170656,void(*)(void*,u32,const char*))(mix,1,"Browse");
 char title[32];const char *prefix=model==3?"Snare / Pad ":model==5?"HiHat / Pad ":"Kick / Pad ";u32 at=0;while(prefix[at]){title[at]=prefix[at];at++;}u32 n=pad(v)+1;if(n>=10)title[at++]='1';title[at++]='0'+n%10;title[at]=0;
 FN(0x0817e85e,void(*)(void*,const char*))((u8*)v+0x80b4,title);
 /* Illustrative envelope in the existing native envelope widget. Audio's own
  * amplitude envelope is untouched; pitch-sweep drawing is deferred. */
 FN(0x081689f8,void(*)(void*,u32,u32,u32,u32))((u8*)v+0x710c,0,e->values[1]*10,0,0);
}
__attribute__((used)) int kick_ui_event(void *v,const void *event){
 if(H(event,0)!=0xcf || !kick_ui_supported(v))return 0;
 u32 key=W(event,8);int value=(int)W(event,12);init();u32 model=kick_ui_supported(v);
 for(u32 i=0;i<8;i++)if(key==(i==7?CLICK_KEY:kick_keys[i])){
  if(i==7&&model!=1)return 1;
  int lo=i==0&&model==1?25:0,hi=i==0&&model==1?180:100;if(value<lo)value=lo;if(value>hi)value=hi;
  update(entry(W(v,0x87bc),model),i,(u32)value);FN(0x0813130c,void(*)(void*))(MODEL);FN(0x08152144,void(*)(void*))(v);return 1;
 }
 if(key==PAD_KEY){if(value<1)value=1;if(value>16)value=16;FN(0x08152acc,void(*)(void*,u32))(v,(u32)value-1);return 1;}
 if(key==LOAD_KEY){FN(0x081ba1c0,int(*)(void))();FN(0x08152bb0,void(*)(void*))(v);return 1;}
 return 0;
}
/* Versioned attributes on the pad's existing params element. They do not
 * consume native automation lanes or change any original property value. */
static const char *const attrs[7]={"bento_kick_v1_tune","bento_kick_v1_decay","bento_kick_v1_tone","bento_kick_v1_impact","bento_kick_v1_sweep","bento_kick_v1_sweep_decay","bento_kick_v1_dirt"};
static KickKnob *existing(u32 handle){if(KNOBS->magic!=KNOBS_MAGIC)return 0;for(u32 i=0;i<128;i++)if(KNOBS->entries[i].sequence && KNOBS->entries[i].handle==handle)return &KNOBS->entries[i];return 0;}
__attribute__((used)) void kick_ui_save(void *object,void *params){
 if(!object || !params || (B(object,4)!=1 && B(object,4)!=2))return;
 KickKnob *e=existing(W(object,0x10));if(!e)return;
 void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_kick_version");if(!a)return;
 FN(0x0810958e,void(*)(void*,u32))(a,1);
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_drum_model");if(a)FN(0x0810958e,void(*)(void*,u32))(a,e->reserved?e->reserved:1);
 a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"bento_drum_v2_click");if(a)FN(0x0810958e,void(*)(void*,u32))(a,CLICKS[e-KNOBS->entries]);
 for(u32 i=0;i<7;i++){a=FN(0x08109cdc,void*(*)(void*,const char*))(params,attrs[i]);if(a)FN(0x0810958e,void(*)(void*,u32))(a,e->values[i]);}
}
__attribute__((used)) void kick_ui_load(void *node,void *object){
 if(!node || !object || (B(object,4)!=1 && B(object,4)!=2) || !W(object,0x10))return;
 init();void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");
 u32 version=0;void *a=params?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_kick_version"):0;
 int valid=a && !FN(0x08109566,int(*)(void*,void*))(a,&version) && version==1;
 u32 model=1;void *m=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_drum_model"):0;if(m)FN(0x08109566,int(*)(void*,void*))(m,&model);if(model!=1&&model!=3&&model!=5)model=1;
 KickKnob *e=valid?entry(W(object,0x10),model):existing(W(object,0x10));if(!e)return;
 for(u32 i=0;i<7;i++){
  int value=drum_defaults(model)[i];u32 raw=0;
  a=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,attrs[i]):0;
  if(a && !FN(0x08109566,int(*)(void*,void*))(a,&raw))value=(int)raw;
  int lo=i==0&&model==1?25:0,hi=i==0&&model==1?180:100;if(value<lo)value=lo;if(value>hi)value=hi;update(e,i,(u32)value);
 }
 // Migrate old kicks with no Click attribute to their saved Tone amount.
 u32 cv=e->values[2];a=valid?FN(0x08109c64,void*(*)(void*,const char*))(params,"bento_drum_v2_click"):0;
 if(a)FN(0x08109566,int(*)(void*,void*))(a,&cv);if(cv>100)cv=100;update(e,7,cv);
}

/* Scale only custom synth controls: a reported ~20% turn becomes ~100%. */
__attribute__((used)) int kick_ui_increment(void *slot,int delta){
 u32 key=H(slot,0x9c);int ours=key==CLICK_KEY;for(u32 i=0;i<7;i++)if(key==kick_keys[i])ours=1;
 if(!ours)return delta;if(delta>0x10000000)delta=0x10000000;if(delta<-0x10000000)delta=-0x10000000;return delta*5;
}

__attribute__((used)) u32 drum_ui_step(u32 parent,u32 row,u32 *values){
 u32 cell=0,index=0,file=0;char path[256];
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i,&cell))break;
  u32 type=FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell);if(type!=1 && type!=2)continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,0x73,&index);if(index!=row)continue;
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i+1,&file))return 0;
  if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&file)!=5)return 0;
  path[0]=0;FN(0x0813390e,int(*)(void*,void*,u32,char*))(MODEL,&file,0x81,path);u32 model=drum_path(path);if(!model || !registry(model))return 0;
  init();KickKnob *e=entry(cell,model);if(values){for(u32 j=0;j<7;j++)values[j]=e->values[j];values[7]=CLICKS[e-KNOBS->entries];}return model;
 }return 0;
}
