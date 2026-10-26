/* P14 note-owned p-locks in melodic Event encoders 7 and 8. */
#include "fx_shared.h"
#include "step_lock_shared.h"
#define PK1 0x1dau
#define PK2 0x1e4u
#define AUTO_ACTION 0x1059u
void **melodic_lock_state_slot(void);void mel_audio_prepare(u32);
int melodic_lock_registry(int);u32 melodic_lock_pack(u32,u32,u32);
typedef struct {u32 view,seq,owner,kind[2],pick[2],shift,changed,selection,scratch,error;} MelUI;
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static MelUI *state(int create){void **slot=melodic_lock_state_slot();if(!slot)return 0;if(*slot)return *slot;if(!create)return 0;
 u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),n=(sizeof(MelUI)+31)&~31u;
 if(p<0xc0000000u||end>0xc8000000u||end<p||end-p<n+32)return 0;
 if(FN(0x08104c08,u32(*)(u32))(n)!=p)return 0;zero((void*)p,n);*slot=(void*)p;return *slot;}
static u32 type(u32 owner){return FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&owner);}
static int limited(MelUI *s){return type(s->owner)!=15;}
static int allowed(MelUI *s,u32 k){return k&&k<=11&&(!limited(s)||k==1||k==3||k==4||k==5||k==7||k>=9);}
static u32 to_kind(MelUI *s,u32 pick){static const u8 ks[9]={0,1,3,4,5,7,9,10,11};return limited(s)?ks[pick<9?pick:0]:pick<12?pick:0;}
static u32 to_pick(MelUI *s,u32 k){if(!limited(s))return k;for(u32 i=0;i<9;i++)if(to_kind(s,i)==k)return i;return 0;}
static int context(MelUI *s,void *v){
 u32 owner=W(v,0x11cd08),current=0,t=type(owner);
 if(B(MODEL,0x12c)!=0x17||B(v,0x125dae)||B(v,0x125dac)!=0||!(t==15||t==18||t==19)||!W(v,0x11cd00)||W(MODEL,0x144)!=W(v,0x11cd00)||!FN(0x08133cfc,int(*)(void*,void*))(MODEL,&current)||current!=owner)return 0;
 if(s->seq!=W(v,0x11cd00)||s->owner!=owner){s->seq=W(v,0x11cd00);s->owner=owner;s->kind[0]=4;s->kind[1]=5;s->selection=0;s->shift=s->changed=s->error=0;}
 s->view=(u32)v;if(t==18||t==19)mel_audio_prepare(owner);return 1;
}
static void *container(MelUI *s){void *node=0;if(!FN(0x0812dfe8,int(*)(void*,u32,void*))((void*)W(MODEL,0),s->seq,&node)||!node)return 0;void *c=(u8*)node+12;return W(c,0x3000)<=511?c:0;}
static int selected(void *v,u32 id){void *g=(u8*)v+0x38;u32 n=W(g,0x1254);if(n>511)return 0;for(u32 i=0;i<n;i++){u32 x=0;if(FN(0x08174d70,int(*)(void*,u32,void*))(g,i,&x)&&id==x)return 1;}return 0;}
static int first(MelUI *s,void *v,u32 *out){void *c=container(s);if(!c)return 0;for(u32 i=0;i<W(c,0x3000);i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,out))break;if(B(out,0)==1&&selected(v,out[3]))return 1;}return 0;}
static void refresh(void *v){FN(0x081599bc,void(*)(void*))(v);}
static int scratch(MelUI *s){if(s->scratch)return 1;u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);if(p<0xc0000000u||end>0xc8000000u||end<p||end-p<0x3020)return 0;if(FN(0x08104c08,u32(*)(u32))(0x3004)!=p)return 0;s->scratch=p;return 1;}
static void edit(MelUI *s,void *v,u32 which,u32 word){
 void *c=container(s);if(!c||!scratch(s)){s->error=2;return;}void *temp=(void*)s->scratch;FN(0x0810d16c,void(*)(void*))(temp);u32 n=W(c,0x3000),e[6],count=0;
 for(u32 i=0;i<n;i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,e))return;if(B(e,0)!=1||!selected(v,e[3]))continue;
  u32 a=which==0?word:lock_slot(e[5],0),b=which==1?word:lock_slot(e[5],1);
  if(lock_kind(a)&&lock_kind(a)==lock_kind(b)){s->error=1;return;}
  u32 packed=melodic_lock_pack(e[5],a,b);if(packed==0xffffffffu){s->error=2;return;}if(packed==e[5])continue;e[5]=packed;FN(0x0810d176,void(*)(void*,void*))(temp,e);count++;
 }
 if(!count)return;
 FN(0x081338dc,void(*)(void*,void*))(MODEL,&s->seq);FN(0x08136544,void(*)(void*,void*,void*))(MODEL,&s->seq,temp);
 W(MODEL,0x36c4)=1;u32 ev[5]={0xc7,s->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((u8*)MODEL+0x160,ev);
}
static const char *const titles[12]={"Target","Level","Pitch","Pan","Filter","Resonance","Attack","Env 1 Decay","Sustain","Env 1 Release","Delay Send","Reverb Send"};
void melodic_locks_header(void *v){
 MelUI *s=state(1);if(!s||!context(s,v)||!melodic_lock_registry(limited(s)))return;
 u32 e[6]={0};int has=first(s,v,e);if(!s->shift&&s->selection!=(has?e[3]:0)){for(u32 j=0;j<2;j++){u32 k=lock_kind(lock_slot(e[5],j));if(allowed(s,k))s->kind[j]=k;}if(s->kind[0]==s->kind[1])s->kind[1]=s->kind[0]==5?4:5;s->selection=has?e[3]:0;}
 for(u32 j=0;j<2;j++){
  u32 k=s->kind[j],key=s->shift?(j?PK2:PK1):native_key(k),w=has?lock_slot(e[5],j):0;
  int value=s->shift?(int)to_pick(s,s->pick[j]):lock_kind(w)==k?decode_value(w):k==4?1000:0;
  void *bar=(u8*)v+0x55f0,*slot=(u8*)bar+0x38+(6+j)*0x468;
  H(v,0x11bcc0+2*(6+j))=key;W(v,0x11bcd0+4*(6+j))=(u32)value;W(v,0x11bca0+4*(6+j))=s->seq;
  FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+j,0);FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,key,value,1);
  char label[32];u32 at=0;const char *p=j?"Lock 2 ":"Lock 1 ";while(*p)label[at++]=*p++;p=titles[s->shift?0:k];while(*p&&at<30)label[at++]=*p++;if(has&&lock_kind(w)==k&&at<30)label[at++]='*';label[at]=0;
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,label);
  if(s->error)FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+j,s->error==1?"Target already used":"No lock memory");
  else if(!s->shift&&(!has||lock_kind(w)!=k))FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+j,has?"--":"Select note");
 }
}
int melodic_locks_event(void *v,void *event){
 if(H(event,0)==AUTO_ACTION){u32 seq=W(v,0x11cd00),value=!W(v,0x125da8),e[5]={0xcf,seq,0x1df,value,0};return FN(0x0815a598,int(*)(void*,void*))(v,e),1;}
 MelUI *s=state(0);if(!s||!context(s,v)||H(event,0)!=0xcf)return 0;u32 key=W(event,8);int value=(int)W(event,12);
 if(s->shift&&(key==PK1||key==PK2)){u32 j=key==PK2,k=to_kind(s,(u32)value);s->error=0;
  if(k&&k==s->kind[1-j]){u32 e[6]={0};first(s,v,e);if(lock_kind(lock_slot(e[5],1-j))==k){s->error=1;refresh(v);return 1;}s->kind[1-j]=s->kind[j];s->pick[1-j]=s->kind[1-j];}
  s->pick[j]=k;s->changed|=1u<<j;if(k){s->kind[j]=k;}W((void*)0x24048d6cu,0)=1;refresh(v);return 1;}
 if(!s->shift)for(u32 j=0;j<2;j++)if(key==native_key(s->kind[j])){s->error=0;edit(s,v,j,encode_value(s->kind[j],value));refresh(v);return 1;}
 return 0;
}
void melodic_locks_proj(void *model,u32 down){
 MelUI *s=state(0);if(!s||B(model,0x12c)!=0x17||!s->view||!context(s,(void*)s->view))return;void *v=(void*)s->view;
 if(down){s->shift=1;s->changed=s->error=0;for(u32 j=0;j<2;j++)s->pick[j]=s->kind[j];}
 else{for(u32 j=0;j<2;j++)if(s->shift&&(s->changed>>j&1)&&!s->pick[j])edit(s,v,j,0);s->shift=s->changed=0;}
 refresh(v);
}
void melodic_locks_menu(int pitched){
 MelUI *s=state(0);int event_page=pitched&&s&&s->view&&!B((void*)s->view,0x125dac);
 for(u32 m=0;m<20;m++){u8 *menu=(u8*)0x30030168u+m*0xe0;if(W(menu,0)!=0xf9)continue;u32 n=B(menu,0xcc);if(n>9)continue;
  for(u32 i=0;i<n;i++){void *cell=menu+4+i*20;u32 code=W(cell,0);
   if(code==0x102d||code==AUTO_ACTION){W(cell,0)=event_page?AUTO_ACTION:0x102d;W(cell,4)=(u32)(event_page?"Show/Hide Automation":"Clear Auto");}
  }
 }
}
/* Register loaded synth tracks before PLAY, including projects whose SEQ page
   has not been visited. Only UI-side lookups/allocation, never on the M7. */
void melodic_register_tracks(void){
 if(!W(MODEL,0))return; /* no project tree during startup/empty-session navigation */
 for(u32 i=0;i<8;i++){u32 owner=0;if(FN(0x08133960,u32(*)(void*,u32,void*))(MODEL,i,&owner)&&owner){u32 t=type(owner);if(t==18||t==19)mel_audio_prepare(owner);}}
}
