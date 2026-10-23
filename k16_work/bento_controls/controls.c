/* BENTO_MOD hold-controls 0.12.0. Native bindings are only for exact stock 1.6.1. */
#include "bindings.h"
typedef unsigned int u32;
typedef unsigned char u8;
typedef void *Ptr;
#define FN(a,t) ((t)((a)|1u))
#define W(p,o) (*(u32 *)((u8 *)(p)+(o)))
#define B(p,o) (*(u8 *)((u8 *)(p)+(o)))
typedef struct {u32 code,context,key,value,extra;} Event;
typedef struct {u32 magic,button,used,await_press,page,track,previous,ctx[4],generation;} State;
#define S ((volatile State *)0x24048cc0u)
/* Separate momentary drum selector. Selection is deliberately NOT restored. */
typedef struct {u32 active,track,sequence,scene,previous,picked;} InstHold;
#define INST ((volatile InstHold *)0x24048cf0u)
typedef struct {u32 magic,active,generation,old_mode;} MixerUI;
#define UI ((volatile MixerUI *)0x24048d20u)
typedef struct {u32 active,old_mode;} MixerLights;
#define LIGHTS ((volatile MixerLights *)0x24048d40u)
typedef struct {u32 target,owner,held,used;} LockUI;
#define LOCK_UI ((volatile LockUI *)0x24048d60u)
static void mixer_pad_mode(Ptr m,u32 enabled){
 Event e={0x10c,0,enabled,0,0};
 FN(NATIVE_MIXER_PAD_MODE,void(*)(Ptr,Event*))(m,&e);
}
static void flush_pad_lights(Ptr m){
 FN(NATIVE_FLUSH_PAD_LIGHTS,void(*)(Ptr))((u8*)m+0x19c4);
}
static u32 get(Ptr obj,u32 key){return FN(NATIVE_GET_PROPERTY,u32(*)(Ptr,u32))(obj,key);}
static void nav(Ptr m,u32 page){FN(NATIVE_NAVIGATE,void(*)(Ptr,u32,u32,u32,u32))(m,page,0,0,0);}
static void button(Ptr m,u32 id){Event e={0x73,0,id,0,0};FN(NATIVE_BUTTON_EVENT,void(*)(Ptr,Event*))(m,&e);}
static Ptr instrument(Ptr m,u32 track,u32 *h){
 if(!FN(NATIVE_FIND_TRACK,u32(*)(Ptr,u32,u32*))(m,track,h))return 0;
 Ptr obj=0;
 if(!FN(NATIVE_RESOLVE_OBJECT,u32(*)(Ptr,u32,Ptr*))((Ptr)W(m,0),*h,&obj))return 0;
 return obj;
}
static u32 type(Ptr obj){return ((u32(*)(Ptr))W((Ptr)W(obj,0),0))(obj);}
static int save(Ptr m,u32 id,u32 late){
 if(LIGHTS->active){mixer_pad_mode(m,LIGHTS->old_mode);LIGHTS->active=0;}
 if(id==5)LIGHTS->old_mode=B(m,0x3c7c);
 S->generation++;S->button=id;S->used=0;S->await_press=late;S->page=B(m,0x12c);
 S->track=get((u8*)m+4,0x131);S->previous=B(m,0x13a);
 for(u32 i=0;i<4;i++)S->ctx[i]=W(m,0x13c+i*4);
 button(m,id);
 if(B(m,0x12c)!=(id==2?2:id==3?0x1e:0x1f)){S->button=0;S->used=0;S->await_press=0;return 0;}
 if(id==5){LIGHTS->active=1;mixer_pad_mode(m,1);flush_pad_lights(m);}
 return 1;
}
static void restore(Ptr m){
 /* Do not reselect a track when the shortcut did not change it. */
 if(get((u8*)m+4,0x131)!=S->track)
  FN(NATIVE_SELECT_TRACK,void(*)(Ptr,u32))(m,S->track);
 for(u32 i=0;i<4;i++)W(m,0x13c+i*4)=S->ctx[i];
 nav(m,S->page);B(m,0x13a)=S->previous;
}
static int playing(Ptr m,u32 track,int *row,int *queued){return FN(NATIVE_PLAYING_STATUS,int(*)(Ptr,u32,int*,int*))(m,track,row,queued);}
static void choose_seq(Ptr m,u32 h,u32 row){FN(NATIVE_SELECT_SEQUENCE,void(*)(Ptr,u32*,u32,u32))(m,&h,row,0);}
static void tracks(Ptr m,u32 track,u32 seq){
 FN(NATIVE_SELECT_TRACK,void(*)(Ptr,u32))(m,track);
 u32 h=0;Ptr obj=instrument(m,track,&h);
 if(!obj)return;
 if(seq && type(obj)!=0x11){
  int row=-1,q=-1;
  if(playing(m,track,&row,&q)!=-1 && row>=0 && row<16)choose_seq(m,h,(u32)row);
  button(m,11);
 }else button(m,10);
}
static void mixer(Ptr m,u32 track,u32 mute){
 u32 h=0;Ptr obj=instrument(m,track,&h);if(!obj)return;
 u32 key=mute?0x13d:0x13e;
 Event e={0xd3,h,key,!get(obj,key),0};
 FN(NATIVE_TRACK_PROPERTY_EVENT,void(*)(Ptr,Event*))(m,&e);
 mixer_pad_mode(m,1);flush_pad_lights(m);
}
/* Same native child property and model/engine event as touchscreen mute. */
static void drum_mute(Ptr m,u32 pad,u32 selected){
 if(B(m,0x12c)!=7 || W(m,0x13c)!=selected || pad>=16)return;
 u32 h=0;Ptr obj=instrument(m,get((u8*)m+4,0x131),&h);
 if(!obj || type(obj)!=0x0e)return;
 for(u32 i=0;i<128;i++){
  Ptr child=0;
  if(!((u32(*)(Ptr,u32,Ptr*))W((Ptr)W(obj,0),0x18))(obj,i,&child))return;
  if(!child || (type(child)!=1 && type(child)!=2) || get(child,0x73)!=pad)continue;
  Event e={0xcf,W(child,0x10),0x1e0,!get(child,0x1e0),0};
  FN(NATIVE_PROPERTY_EVENT,void(*)(Ptr,Event*))(m,&e);
  flush_pad_lights(m);return;
 }
}
static Ptr clip(Ptr obj,u32 row){
 /* Typed native enumeration; does not create or select any clip. */
 u32 kind=type(obj)==0x11?0x2e:0x18;
 for(u32 i=0;i<256;i++){
  Ptr child=0;
  u32 ok=((u32(*)(Ptr,u32,u32,Ptr*))W((Ptr)W(obj,0),0x1c))(obj,kind,i,&child);
  if(!ok)return 0;
  if(child && get(child,kind==0x2e?0x6f:0x73)==row)return child;
 }return 0;
}
static void launch(Ptr m,u32 track,u32 start){
 u32 h=0;Ptr obj=instrument(m,track,&h);if(!obj)return;
 int row=-1,q=-1;int pos=playing(m,track,&row,&q);
 Ptr engine=*(Ptr*)0x3000f650u;
 if(!start){if(pos==-1 && q<0)return;
  FN(NATIVE_ENGINE_PROPERTY,void(*)(Ptr,u32,u32,u32))(engine,h,0x64,0);return;}
 u32 selected=get(obj,0x133);
 if(selected>=16 || !clip(obj,selected))return;
 if((pos!=-1 && row==(int)selected) || q==(int)selected)return;
 FN(NATIVE_ENGINE_PROPERTY,void(*)(Ptr,u32,u32,u32))(engine,h,0x64,1);
 FN(NATIVE_ENGINE_PROPERTY,void(*)(Ptr,u32,u32,u32))(engine,h,0x63,selected);
}
static void lock_off(void){
 if(LOCK_UI->target)FN(NATIVE_ENGINE_PROPERTY,void(*)(Ptr,u32,u32,u32))(*(Ptr*)0x3000f650u,LOCK_UI->target,0x7ffd,0);
 LOCK_UI->target=0;LOCK_UI->owner=0;
}
static void lock_arm(Ptr m){
 lock_off();
 u32 h=0;Ptr obj=instrument(m,get((u8*)m+4,0x131),&h);
 if(!obj)return;
 u32 target=type(obj)==0x0e?W(m,0x13c):h;
 if(!target)return;
 LOCK_UI->target=target;LOCK_UI->owner=h;
 FN(NATIVE_ENGINE_PROPERTY,void(*)(Ptr,u32,u32,u32))(*(Ptr*)0x3000f650u,target,0x7ffe,h);
}
static int inst_hold(Ptr m,u32 code,u32 index){
 if(code==0xaf && index!=10)INST->active=0;
 if(index!=10 || (code!=0xaf && code!=0xb0))return 0;
 if(code==0xaf){
  if(INST->active)return 1;
  if(B(m,0x12c)!=0x27)return 0;
  u32 track=get((u8*)m+4,0x131),h=0;
  Ptr obj=instrument(m,track,&h);
  if(!obj || type(obj)!=0x0e)return 0;
  INST->track=track;INST->sequence=W(m,0x144);INST->scene=W(m,0x148);
  INST->previous=B(m,0x13a);INST->picked=0;
  button(m,10);
  if(B(m,0x12c)==7)INST->active=1;
  return 1;
 }
 if(!INST->active)return 0;
 INST->active=0;
 if(!INST->picked)return 1;
 if(get((u8*)m+4,0x131)!=INST->track)return 1;
 u32 page=B(m,0x12c);
 if(page!=7 && page!=9 && page!=0x14)return 1;
 /* Keep newly selected cell context (13C/140) and native parent property 74. */
 W(m,0x144)=INST->sequence;W(m,0x148)=INST->scene;
 /* Native playback updater 0813C318 stops touching LED press flags on SEQ.
    Clear instrument overlays BEFORE navigation rebuilds SEQ/playhead colours. */
 FN(NATIVE_CLEAR_PAD_HIGHLIGHTS,void(*)(Ptr))((u8*)m+0x19c4);
 nav(m,0x27);B(m,0x13a)=(u8)INST->previous;
 if(B(m,0x12c)==0x27){FN(0x081b9000,void(*)(Ptr))(m);flush_pad_lights(m);}
 return 1;
}
__attribute__((used)) int controls_dispatch(Ptr m,u32 code,u32 context,u32 index,const u32 *record){
 if(S->magic!=0x354d5442u){for(u32 i=0;i<sizeof(State)/4;i++)((volatile u32*)S)[i]=0;S->magic=0x354d5442u;}
 if((code==0xaf || code==0xb0) && index==7){
  if(code==0xaf){LOCK_UI->held=1;LOCK_UI->used=0;FN(0x081b8c00,void(*)(Ptr,u32))(m,1);}
  else {FN(0x081b8c00,void(*)(Ptr,u32))(m,0);LOCK_UI->held=0;}
  return 1;
 }
 if((index==14 || index==15) && code==0xb0 && (*(volatile u32*)0x24048d70u&(1u<<index))){
  *(volatile u32*)0x24048d70u&=~(1u<<index);return 1;
 }
 /* PROJ is pure shift. A shifted transport press is consumed through release. */
 if((code==0xaf || code==0xb0) && LOCK_UI->held && index==15){
  LOCK_UI->used=1;if(code==0xaf){*(volatile u32*)0x24048d70u|=1u<<index;button(m,7);}return 1;
 }
 if((code==0xaf || code==0xb0) && LOCK_UI->held && index==14){
  LOCK_UI->used=1;if(code==0xaf){*(volatile u32*)0x24048d70u|=1u<<index;FN(0x081b8d00,void(*)(Ptr))(m);}return 1;
 }
 if(code==0xaf && index==14)lock_off();
 if(code==0xaf && index!=7 && LOCK_UI->held)LOCK_UI->used=1;
 if(inst_hold(m,code,index))return 1;
 if((code==0xaf || code==0xb0) && (index==2 || index==3 || index==5)){
  if(code==0xaf){
   if(S->button==index && S->await_press){S->await_press=0;return 1;}
   save(m,index,0);return 1;
  }
  if(S->button==index){
   u32 returning=S->used && index!=2;
   if(index==5 && LIGHTS->active){
    u32 mode=LIGHTS->old_mode;
    /* A plain tap stays on MIXER with the native screen's previous mode. */
    if(!returning && UI->magic==0x35554942u && UI->active && UI->generation==S->generation)mode=UI->old_mode;
    mixer_pad_mode(m,mode);LIGHTS->active=0;
   }
   if(returning)restore(m);
   if(index==5)flush_pad_lights(m);
   S->button=0;S->used=0;S->await_press=0;
  }
  return 1;
 }
 if(code==0xfe && record[1]==0x314d5442u && record[5]==0x31525442u && record[4]==9){
  LOCK_UI->used=1;drum_mute(m,index,context);return 1;
 }
 if(code!=0xfe || context!=0xfffffffeu || index>7 || record[1]!=0x314d5442u || record[5]!=0x31525442u)return 0;
 u32 action=record[4];if(action<1 || action>8)return 0;
 if(action>=7){
  LOCK_UI->used=1;
  if(index==0){if(action==7)lock_arm(m);else lock_off();}
  return 1;
 }
 INST->active=0;
 u32 id=action<=2?2:action<=4?3:5;
 if(S->button!=id && !save(m,id,1))return 1;S->used=1;
 if(action<=2)tracks(m,index,action==2);
 else if(action<=4)launch(m,index,action==4);
 else mixer(m,index,action==6);
 return 1;
}

/* UI-thread adapter: reveal the native Solo / Mute controls using the same
 * toolbar action as a touchscreen press. No cross-thread widget mutations. */
static void mixer_mode(Ptr pane,u32 wanted){
 if(B(pane,0x9a08)!=(u8)wanted){
  Event e={0x10c,0,0,0,0};
  FN(NATIVE_MIXER_EVENT,u32(*)(Ptr,Event*))(pane,&e);
 }
}
__attribute__((used,section(".mixer"))) u32 mixer_render(Ptr pane,Ptr canvas){
 if(UI->magic!=0x35554942u){UI->active=0;UI->magic=0x35554942u;}
 u32 held=S->magic==0x354d5442u && S->button==5;
 if(UI->active && (!held || UI->generation!=S->generation)){
  mixer_mode(pane,UI->old_mode);UI->active=0;
 }
 if(held && !UI->active){
  UI->old_mode=B(pane,0x9a08);UI->generation=S->generation;UI->active=1;
  mixer_mode(pane,1);
 }
 return FN(NATIVE_MIXER_RENDER,u32(*)(Ptr,Ptr))(pane,canvas);
}
