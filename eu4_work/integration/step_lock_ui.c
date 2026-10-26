/* BENTO_MOD L7: two native spare Event encoders, lossless note-owned locks. */
#include "step_lock_shared.h"
#include "seq_bank.h"
#include "../../chord_work/device.h"
#include "header_actions.h"
#include "kick_knobs.h"
#include "drum_models.h"
int piano_eu_toolbar(void*,void*);int mod_toolbar(void*,void*);
#define MODEL ((void*)0x30024b00u)
#define PICKER 0x1dau
#define PICKER2 0x1e4u
static u32 picker(u32 i){return i?PICKER2:PICKER;}
#define MAGIC 0x47555042u
typedef struct {u32 seq,drum,kind,kind2;} Target;
typedef struct {u32 magic,view,seq,drum,kind,shift,pick,changed,error,next,selection,kind2,pick2,changed2;Target targets[64];u32 pool,pool_count,select_mode,selected[8],swallowed;void *chord_state,*melodic_state;u32 auto_eu;void *lane_state,*perf_state,*mod_state;} UI;
#define U ((volatile UI*)0x24048000u)
_Static_assert(sizeof(UI)<=0x480,"Lock UI overlaps choice table");
#define LOCK_COND_KEY 0x198u
#define LOCK_READ_KEY 0x199u
const char select_label[] __attribute__((used,retain))="Select";
static const char select_on[]="Select ON";
static const char cond_title[]="Lock condition",read_title[]="Locks when";
static u32 conditional(u32,u32);
int seq_selection_active(void*);
static const char *const native_choices[]={"Remove lock","Level","Pitch","Pan","Filter","Resonance","Attack","Decay","Sustain","Release","Delay Send","Reverb Send"};
static const char *const titles[]={"Lock target","Lock Level","Lock Pitch","Lock Pan","Lock Filter","Lock Resonance","Lock Attack","Lock Decay","Lock Sustain","Lock Release","Lock Delay Send","Lock Reverb Send"};
static const char *const titles2[]={"Lock 2 target","Lock 2 Level","Lock 2 Pitch","Lock 2 Pan","Lock 2 Filter","Lock 2 Resonance","Lock 2 Attack","Lock 2 Decay","Lock 2 Sustain","Lock 2 Release","Lock 2 Delay Send","Lock 2 Reverb Send"};
#define CHOICES ((const char**)0x24048480u)
/* CH12: Tom locks use the Kick kinds 12..18, Clap the Snare kinds 20..24. */
static const char *const tom_names[]={"Tom Tune","Tom Decay","Tom Tone","Tom Impact","Tom Sweep","Tom Sweep Dec","Tom Dirt"};
static const char *const clap_names[]={"Clap Tune","Clap Decay","Clap Tone","Clap Impact","Clap Spread"};
static u32 family(u32 m){return m==9?1:m==7?3:m;}
static const char *const synth_names[]={"Kick Tune","Kick Decay","Kick Tone","Kick Impact","Kick Sweep","Kick Sweep Dec","Kick Punch","Kick Click","Snare Tune","Snare Decay","Snare Tone","Snare Impact","Snare Snappy","HiHat Tune","HiHat Decay","HiHat Tone","HiHat Impact","HiHat Noise"};
static u32 engine(void *v,u32 *values){u32 m=FN(0x081bb080,u32(*)(u32,u32,u32*))(W(v,0x113e8),W(v,0x11400),values);return m==11?0:m;}
static u32 first(u32 m){m=family(m);return m==1?12:m==3?20:m==5?25:0;}
static u32 total(u32 m){return m==1?16:m==9?15:(m==3||m==5||m==7)?13:12;}
static u32 to_kind(u32 v,u32 m){if(!m)return v;return v<6?v:v<8?v+4:first(m)+v-8;}
static int synth_ok(u32 k,u32 m){return m && synth_model(k)==family(m) && k-first(m)+8<total(m);}
static u32 to_pick(u32 k,u32 m){if(!m)return k<12?k:0;return k<6?k:k==10||k==11?k-4:synth_ok(k,m)?k-first(m)+8:0;}
static u32 kind(u32 i){return i?U->kind2:U->kind;}
static void setkind(u32 i,u32 k){if(i)U->kind2=k;else U->kind=k;}
static u32 pick(u32 i){return i?U->pick2:U->pick;}
static void setpick(u32 i,u32 k){if(i)U->pick2=k;else U->pick=k;}
static void init(void){if(U->magic!=MAGIC){for(u32 i=0;i<sizeof(UI)/4;i++)((volatile u32*)U)[i]=0;U->magic=MAGIC;}}
void **chord_state_slot(void){init();return (void**)&U->chord_state;}
void **piano_eu_slot(void){init();return (void**)&U->melodic_state;}
void **lane_state_slot(void){init();return (void**)&U->lane_state;}
void **perf_state_slot(void){init();return (void**)&U->perf_state;}
void **mod_state_slot(void){init();return (void**)&U->mod_state;}
/* CH5: arm the default Euclidean view on every navigation into page 27. */
void seq_auto_arm(u32 page){init();U->auto_eu=page==0x27;}
int seq_auto_take(void *v){init();if(!U->auto_eu||!v)return 0;U->auto_eu=0;return 1;}
int seq_eu_tab(void*);void seq_eu_leave(void*);int seq_eu_mode(void*);
static int supported(void *v){return v && (!B(v,0x113e0)||seq_eu_active(v)) && W(v,0x113e4) && W(v,0x113dc) && W(v,0x11400)<16 && FN(0x08133f7c,u32(*)(void*,void*))(MODEL,(u8*)v+0x113e8)==14;}
static int snapshot(void *v,u32 *e){return FN(0x0815ba04,int(*)(void*,void*))(v,e);}
static void remember(void){
 u32 slot=64;for(u32 i=0;i<64;i++)if(U->targets[i].seq==U->seq && U->targets[i].drum==U->drum){slot=i;break;}
 if(slot==64)slot=U->next++&63;
 U->targets[slot].seq=U->seq;U->targets[slot].drum=U->drum;U->targets[slot].kind=U->kind;U->targets[slot].kind2=U->kind2;
}
static void context(void *v){
 init();u32 seq=W(v,0x113e4),drum=W(v,0x11400);
 if(U->view==(u32)v && U->seq==seq && U->drum==drum)return;
 for(u32 m=0;m<20;m++){void *menu=(void*)(0x30030168u+m*0xe0);for(u32 i=0;i<B(menu,0xcc)&&i<9;i++){void *cell=(u8*)menu+4+i*20;if(W(cell,0)==0x1051)W(cell,4)=(u32)select_label;}}U->select_mode=U->swallowed=0;for(u32 i=0;i<8;i++)U->selected[i]=0;U->view=(u32)v;U->seq=seq;U->drum=drum;U->error=0;U->changed=0;U->changed2=0;U->selection=0;U->kind=1;U->kind2=4;
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
 u32 reg=*(volatile u32*)0x30031484u;if(!reg)return 0;
 void *cd=(void*)(reg+LOCK_COND_KEY*32);
 if(H(cd,0) && W(cd,4)!=(u32)cond_title)return 0;
 for(u32 i=0;i<8;i++)W(cd,i*4)=0;
 H(cd,0)=LOCK_COND_KEY;B(cd,2)=7;W(cd,4)=(u32)cond_title;W(cd,8)=0x081b6000u;W(cd,12)=135;
 void *rd=(void*)(reg+LOCK_READ_KEY*32);if(H(rd,0) && W(rd,4)!=(u32)read_title)return 0;for(u32 i=0;i<8;i++)W(rd,i*4)=W(cd,i*4);H(rd,0)=LOCK_READ_KEY;W(rd,4)=(u32)read_title;

 for(u32 i=0;i<total(m);i++){u32 k=to_kind(i,m);CHOICES[i]=k<12?native_choices[k]:m==9?tom_names[k-12]:m==7?clap_names[k-20]:synth_names[k-12];}
 u32 r=*(volatile u32*)0x30031484u;if(!r)return 0;
 for(u32 j=0;j<2;j++){
  void *d=(void*)(r+picker(j)*32);const char *title=j?titles2[0]:titles[0];
  if(H(d,0) && W(d,4)!=(u32)title)return 0;
  for(u32 i=0;i<8;i++)W(d,i*4)=0;
  H(d,0)=picker(j);B(d,2)=7;W(d,4)=(u32)title;W(d,8)=(u32)CHOICES;W(d,12)=total(m);
 }return 1;
}
static int background(void *v,u32 k){
 if(k>11){u32 values[8];u32 m=engine(v,values);return synth_ok(k,m)?(int)values[synth_index(k)]:0;}
 u32 parent=W(v,0x113e8),cell=0,idx=0,value=0;
 for(u32 i=0;i<128;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&parent,i,&cell))break;
  if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&cell)!=1)continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,0x73,&idx);if(idx!=W(v,0x11400))continue;
  FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&cell,native_key(k),&value);return (int)value;
 }return 0;
}
__attribute__((used,retain)) void locks_header_before(void *v){
 H((void*)0x300000bcu,4)=0x184;for(u32 j=4;j<8;j++)H((void*)0x300000bcu,j*2)=0;if(!supported(v))return;context(v);
 if(!U->shift){u32 e[6]={0};int has=snapshot(v,e);u32 id=has?e[3]:0;
  if(id!=U->selection){for(u32 i=0;i<2;i++){u32 k=has?lock_kind(lock_slot(e[5],i)):0;if(k)setkind(i,k);}U->selection=id;
   if(U->kind==U->kind2)U->kind2=U->kind==4?1:4;
  }
 }
 u32 m=engine(v,0);
 for(u32 i=0;i<2;i++)if((kind(i)>11 && !synth_ok(kind(i),m)) || (m && kind(i)>=6 && kind(i)<=9))setkind(i,i?4:1);
 if(U->kind==U->kind2)U->kind2=U->kind==4?1:4;
 if(!registry(m))return;
 if(U->shift)H((void*)0x300000bcu,4)=LOCK_COND_KEY;
 u32 selected_event[6];if(snapshot(v,selected_event))H((void*)0x300000bcu,10)=LOCK_READ_KEY;
 for(u32 i=0;i<2;i++)H((void*)0x300000bcu,12+i*2)=U->shift?picker(i):native_key(kind(i));
}
__attribute__((used,retain)) void locks_grid(void *v){
 if(seq_eu_grid(v,1))return;
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

__attribute__((used,retain)) void locks_header_after(void *v){
 seq_eu_header(v);if(!supported(v) || U->view!=(u32)v || !H((void*)0x300000bcu,12))return;
 locks_grid(v);void *bar=(u8*)v+0xebf0;u32 e[6]={0};int has=snapshot(v,e);
 if(U->shift){
  u32 c=has?lc_condition(e[5]):0,display=c?c<100?c-1:c:99;
  void *slot=(u8*)bar+0x38+2*0x468;H(v,0x113ac+4)=LOCK_COND_KEY;W(v,0x113bc+8)=display;B(slot,0x2c8)=0;
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,LOCK_COND_KEY,(int)display,1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,"Lock condition");
 }
 /* Spare encoder6 is a persistent condition readout; preserve native A-D. */
 if(has){
  u32 c=lc_condition(e[5]),ix=c?c<100?c-1:c:99;const char *label=((const char**)0x081b6000u)[ix];
  void *slot=(u8*)bar+0x38+5*0x468;H(v,0x113ac+10)=LOCK_READ_KEY;W(v,0x113bc+20)=ix;B(slot,0x2c8)=0;FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,LOCK_READ_KEY,(int)ix,1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)bar+0x38+5*0x468+0x3c8,"Locks when");
  FN(0x08170656,void(*)(void*,u32,const char*))(bar,5,label);
 }

 u32 model=engine(v,0);
 for(u32 i=0;i<2;i++){
  void *slot=(u8*)bar+0x38+(6+i)*0x468;u32 k=kind(i),w=has?lock_slot(e[5],i):0;
  int value=U->shift?(int)to_pick(pick(i),engine(v,0)):lock_kind(w)==k?decode_value(w):background(v,k);
  H(v,0x113ac+(6+i)*2)=(unsigned short)(U->shift?picker(i):native_key(k));W(v,0x113bc+(6+i)*4)=(u32)value;
  B(slot,0x2c8)=0; /* Clear an old --/error override before native formatting. */
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,U->shift?picker(i):native_key(k),value,1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,(!U->shift&&k>11)?(model==9?tom_names[k-12]:model==7?clap_names[k-20]:synth_names[k-12]):i?titles2[U->shift?0:k]:titles[U->shift?0:k]);
  if(U->error)FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+i,U->error==2?"Lock memory full":"Target already used");
  else if(!U->shift && k>11){char text[20];u32 n=k==12||k==20||k==25?drum_tune_hz(model,(u32)value):(u32)value,at=0;if(n>=1000)text[at++]='0'+n/1000%10;if(n>=100)text[at++]='0'+n/100%10;if(n>=10)text[at++]='0'+n/10%10;text[at++]='0'+n%10;if(k==12||k==20||k==25){text[at++]=' ';text[at++]='H';text[at++]='z';}else text[at++]='%';text[at]=0;FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+i,text);}
  else if(!U->shift && lock_kind(w)!=k)FN(0x08170656,void(*)(void*,u32,const char*))(bar,6+i,"--");
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
 /* Reserve all immutable results before touching notes: full pool is atomic. */
 for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;if(!matches(v,e))continue;
  u32 a=which==0?word:lock_slot(e[5],0),b=which==1?word:lock_slot(e[5],1),p=which==2?0:pack_locks(a,b);
  if(p!=0xffffffffu && conditional(p,lc_condition(e[5]))==0xffffffffu){U->error=2;return;}
 }
 for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;if(!matches(v,e))continue;
  u32 a=which==0?word:lock_slot(e[5],0),b=which==1?word:lock_slot(e[5],1),packed=which==2?0:pack_locks(a,b);
  if(packed==0xffffffffu)continue;packed=conditional(packed,lc_condition(e[5]));if(packed==0xffffffffu){U->error=2;return;}if(packed==e[5])continue;e[5]=packed;
  FN(0x0810d1aa,void(*)(void*,void*))((void*)W(v,0x113dc),e);changed=1;
 }
 if(changed){FN(0x08136544,void(*)(void*,void*,void*))(MODEL,(u8*)v+0x113e4,(void*)W(v,0x113dc));FN(0x0815c4b8,void(*)(void*))(v);}
}
__attribute__((used,retain)) int locks_encoder(void *v,u32 key,int value){
 if(!supported(v))return seq_eu_encoder(v,key,value);context(v);
 if(key==LOCK_READ_KEY)return 1;
 if(U->shift && key==LOCK_COND_KEY){
  if(value<0)value=0;if(value>134)value=134;u32 c=value==99?0:value<99?(u32)value+1:(u32)value;
  protect_release(v);*(volatile u32*)0x24048d6cu=1;u32 e[6],changed=0;U->error=0;
  /* Preflight every immutable payload before changing any selected note. */
  for(u32 i=0;i<511;i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;if(matches(v,e)&&conditional(lc_word(e[5]),c)==0xffffffffu){U->error=2;refresh(v);return 1;}}
  for(u32 i=0;i<511;i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,e))break;if(!matches(v,e))continue;u32 w=conditional(lc_word(e[5]),c);if(w==e[5])continue;e[5]=w;FN(0x0810d1aa,void(*)(void*,void*))((void*)W(v,0x113dc),e);changed=1;}
  if(changed){FN(0x08136544,void(*)(void*,void*,void*))(MODEL,(u8*)v+0x113e4,(void*)W(v,0x113dc));FN(0x0815c4b8,void(*)(void*))(v);}refresh(v);return 1;
 }
 if(seq_eu_encoder(v,key,value))return 1;
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
__attribute__((used,retain)) void locks_proj(void *model,u32 down){
 extern void melodic_locks_proj(void*,u32);melodic_locks_proj(model,down);
 init();void *v=(void*)U->view;u32 was=U->shift;if(!down)U->shift=0;
 if(B(model,0x12c)!=0x27 || !supported(v))return;context(v);
 if(down){u32 e[6]={0};U->selection=snapshot(v,e)?e[3]:0;U->shift=1;U->pick=U->kind;U->pick2=U->kind2;U->changed=U->changed2=U->error=0;}
 else{if(was && U->changed && !U->pick)edit(v,0,0);if(was && U->changed2 && !U->pick2)edit(v,0,1);U->changed=U->changed2=U->error=0;}refresh(v);
}
__attribute__((used,retain)) void locks_save(void *node,const void *e){
 if(B(e,0)!=1)return;
 void *c=FN(0x08109cdc,void*(*)(void*,const char*))(node,"bento_lock_condition_v1");if(c)FN(0x0810958e,void(*)(void*,u32))(c,lc_condition(W(e,20)));
 for(u32 i=0;i<2;i++){u32 w=lock_slot(W(e,20),i);
  void *a=FN(0x08109cdc,void*(*)(void*,const char*))(node,i?"bento_lock2_v1":"bento_lock1_v1");if(a)FN(0x0810958e,void(*)(void*,u32))(a,w);
 }
}
__attribute__((used,retain)) void locks_load(void *node,void *e){
 if(B(e,0)!=1)return;u32 w[2]={0,0};
 for(u32 i=0;i<2;i++){void *a=FN(0x08109c64,void*(*)(void*,const char*))(node,i?"bento_lock2_v1":"bento_lock1_v1");u32 x=0;
  if(a && !FN(0x08109566,int(*)(void*,void*))(a,&x) && lock_kind(x))w[i]=x;
 }if(w[0] && lock_kind(w[0])==lock_kind(w[1]))w[1]=0;u32 cond=0;void *a=FN(0x08109c64,void*(*)(void*,const char*))(node,"bento_lock_condition_v1");if(a && FN(0x08109566,int(*)(void*,void*))(a,&cond))cond=0;if(cond>=135)cond=0;
 init();u32 packed=conditional(pack_locks(w[0],w[1]),cond);W(e,20)=packed==0xffffffffu?0:packed;
}
__attribute__((used,retain)) void locks_clear(void *model){init();void *v=(void*)U->view;if(B(model,0x12c)!=0x27 || !supported(v))return;context(v);U->error=0;edit(v,0,2);refresh(v);}
__attribute__((used,retain)) void locks_pad_clear(void *v,u32 local){
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
__attribute__((used,retain)) void seq_lights_clean(void *model){
 if(B(model,0x12c)!=0x27)return;
 seq_eu_tick(model);
 void *led=(u8*)model+0x19c4;u32 changed=0;
 for(u32 i=0;i<16;i++)if(B(led,i*16+12)){B(led,i*16+12)=0;changed=1;}
 if(changed)FN(0x081257f0,void(*)(void*))(led);
}

/* Codec exports for exact native-code migration/round-trip regression checks. */
__attribute__((used,retain)) u32 locks_pack(u32 a,u32 b){return pack_locks(a,b);}
__attribute__((used,retain)) u32 locks_slot(u32 w,u32 i){return lock_slot(w,i);}

/* Bounded immutable records: 64KiB at first conditional edit, deduplicated.
 * No fixed SRAM/MPU/voice-layout change and no M7 allocation. */
static u32 conditional(u32 w,u32 c){
 w=lc_word(w);if(!c)return w;init();
 if(!U->pool){u32 end=W((void*)0x30000048u,0),next=W((void*)0x3000004cu,0);if(next<0xc0000000u||end>0xc8000000u||next>end||end-next<65568)return 0xffffffffu;
  u32 p=FN(0x08104c08,u32(*)(u32))(65568);p=(p+31)&~31u;if(p<0xc0000000u||p>0xc7ff0000u)return 0xffffffffu;U->pool=p;U->pool_count=0;}
 for(u32 i=0;i<U->pool_count;i++){u32 a=U->pool+i*32;if(W((void*)a,4)==w&&W((void*)a,8)==c)return 0x60000000u|(a&0x0fffffffu);}
 if(U->pool_count>=2048)return 0xffffffffu;u32 a=U->pool+U->pool_count*32;void *p=(void*)a;
 for(u32 i=0;i<8;i++)W(p,i*4)=0;W(p,4)=w;W(p,8)=c;W(p,12)=LC_MAGIC^a^w^c;__asm__ volatile("dmb" ::: "memory");W(p,0)=LC_MAGIC;__asm__ volatile("dsb" ::: "memory");U->pool_count++;
 return 0x60000000u|(a&0x0fffffffu);
}
__attribute__((used,retain)) u32 locks_condition_word(u32 w,u32 c){return c<135?conditional(w,c):0xffffffffu;}
__attribute__((used,retain)) u32 locks_condition_get(u32 w){return lc_condition(w);}
__attribute__((used,retain)) int seq_selection_active(void *v){if(U->magic!=MAGIC || U->view!=(u32)v)return 0;if(!supported(v))return 0;context(v);for(u32 i=0;i<8;i++)if(U->selected[i])return 1;return 0;}
__attribute__((used,retain)) int seq_selection_match(void *v,u32 step){return seq_selection_active(v) && step<256 && (U->selected[step/32]>>(step%32)&1);}
__attribute__((used,retain)) int seq_select_event(void *v,void *event){
 u32 code=H(event,0);
 if(code==0x1055)return seq_eu_tab(v);
 if(code==0x49||code==0x4a){seq_eu_leave(v);return 0;}
 if(code==0x102c&&supported(v)){ /* P20: Clear with selected steps clears only those (owner plan) */
  context(v);int any=0;for(u32 i=0;i<8;i++)if(U->selected[i])any=1;if(!any)return 0;
  extern int eu_clear_steps(u32,u32,const u32*,void*);eu_clear_steps(U->seq,U->drum,U->selected,MODEL);
  for(u32 i=0;i<8;i++)U->selected[i]=0;refresh(v);return 1;
 }
 if(!supported(v)||code!=0x1051)return 0;context(v);U->select_mode^=1;
 if(U->select_mode){W((void*)0x24048d80u,20)=0;for(u32 i=0;i<32;i++)W(v,0x11420+i*4)=0;}
 /* FA native menu descriptor #1, beside Undo. Native renderer owns the hitbox. */
 for(u32 m=0;m<20;m++){void *menu=(void*)(0x30030168u+m*0xe0);for(u32 i=0;i<B(menu,0xcc)&&i<9;i++){void *cell=(u8*)menu+4+i*20;if(W(cell,0)==0x1051)W(cell,4)=(u32)(U->select_mode?select_on:select_label);}}
 refresh(v);return 1;
}
static int select_step(void *v,u32 local){
 if(!supported(v))return 0;context(v);if(!U->select_mode)return 0;
 u32 n=W(v,0x113f4)+local;if(local<32 && n<W(v,0x113f8)&&n<256 && FN(0x0815bcb4,int(*)(void*,u32))(v,local))U->selected[n/32]^=1u<<(n%32);
 W((void*)0x24048d80u,20)=0;refresh(v);return 1;
}
__attribute__((used,retain)) int seq_select_press(void *v,u32 pad){
 if(U->magic!=MAGIC || U->view!=(u32)v)return 0;
 if(pad>=16)return 0;int n=(int)(W(v,0x11404)+pad)-(int)W(v,0x113f4);
 if(supported(v) && *(volatile u32*)0x24048d68u){context(v);locks_pad_clear(v,(u32)n);U->swallowed|=1u<<pad;refresh(v);return 1;}
 if(select_step(v,(u32)n)){U->swallowed|=1u<<pad;return 1;}
 if(supported(v)){context(v);for(u32 i=0;i<8;i++)U->selected[i]=0;}return 0;
}
__attribute__((used,retain)) int seq_select_release(void *v,u32 pad){if(U->magic!=MAGIC || U->view!=(u32)v)return 0;if(!supported(v)||pad>=16)return 0;context(v);u32 bit=1u<<pad;if(!(U->swallowed&bit))return 0;U->swallowed&=~bit;return 1;}
__attribute__((used,retain)) int seq_select_touch(void *v,void *point){if(U->magic!=MAGIC || U->view!=(u32)v)return 0;if(!supported(v))return 0;context(v);if(!U->select_mode)return 0;return select_step(v,(u32)FN(0x0815bd50,int(*)(void*,void*))(v,point));}
__attribute__((used,retain)) int seq_select_touch_end(void *v){if(U->magic!=MAGIC || U->view!=(u32)v)return 0;if(!supported(v))return 0;context(v);return U->select_mode;}

__attribute__((used,retain)) void seq_selection_reset(void *v){if(!supported(v))return;context(v);for(u32 i=0;i<8;i++)U->selected[i]=0;}

/* EU9: persistent header actions are separate from the popup definitions.
 * CH2: Undo is the last native slot on SEQ page 27, so Select takes the
 * rightmost free normal slot; header_sync makes late insertions visible. */
/* P17 (owner: the Euclidean tab overlaps the on-screen pad selector). Undo is
 * gone, so the row moves right: slot 0 stays free for the pad selector;
 * Euclidean, Step, Sequence as tabs in 1..3 and Select in slot 4, directly
 * next to them and Clear in slot 5, lined up with the melodic row. The
 * native tab records are found by group, also when this ran before. */
static int drum_seq_layout(void *out){
 u8 tabs[2][48];u32 n=0;
 for(u32 i=0;i<6&&n<2;i++){u8 *r=(u8*)out+0x74+i*48;u32 id=r[44]|r[45]<<8;if(r[0x22]&&id&&!(id>=0x1051u&&id<=0x1064u)){for(u32 j=0;j<48;j++)tabs[n][j]=r[j];n++;}}
 int eu=seq_eu_mode((void*)U->view),changed=0;
 u8 before[6*48];for(u32 j=0;j<6*48;j++)before[j]=((u8*)out)[0x74+j];
 for(u32 i=0;i<6;i++){u8 *r=(u8*)out+0x74+i*48;for(u32 j=0;j<48;j++)r[j]=0;r[0x20]=1;}
 header_fixed_tab(out,1,0x1055,"Euclidean",eu);
 for(u32 k=0;k<n;k++){u8 *r=(u8*)out+0x74+(2+k)*48;for(u32 j=0;j<48;j++)r[j]=tabs[k][j];r[0x20]=0;r[0x22]=1;if(eu)r[0x21]=0;}
 header_fixed_action(out,4,0x1051,U->select_mode?select_on:select_label,U->select_mode!=0);
 header_fixed_action(out,5,0x102c,"Clear",0); /* owner: Clear next to Select, as in the melodic row (native Clear Seq) */
 for(u32 j=0;j<6*48;j++)if(before[j]!=((u8*)out)[0x74+j])changed=1;
 return changed;
}
__attribute__((used,retain)) int drum_seq_toolbar(void *model,void *out){return B(model,0x12c)==0x27&&U->magic==MAGIC&&supported((void*)U->view)?drum_seq_layout(out):0;}
__attribute__((used,retain)) int seq_toolbar(void *model,void *out,int native_changed){
 native_changed=chord_toolbar(model,out,native_changed);
 native_changed|=piano_eu_toolbar(model,out);
 native_changed|=mod_toolbar(model,out); /* P8 MOD / MATRIX on synth pages */
 if(B(model,0x12c)==0x27 && U->magic==MAGIC && supported((void*)U->view))native_changed|=drum_seq_layout(out);
 native_changed|=header_remove_undo(out);header_sync(out);
 return native_changed;
}

int melodic_lock_registry(int limited){
 if(!registry(0))return 0;
 static const char *const choices[]={"Remove lock","Level","Pan","Filter","Resonance","Env 1 Decay","Env 1 Release","Delay Send","Reverb Send"};
 if(limited)for(u32 i=0;i<2;i++){void *d=(void*)(W((void*)0x30031484u,0)+picker(i)*32);W(d,8)=(u32)choices;W(d,12)=9;}
 return 1;
}
u32 melodic_lock_pack(u32 previous,u32 a,u32 b){u32 p=pack_locks(a,b);return p==0xffffffffu?p:conditional(p,lc_condition(previous));}

void *step_current_view(void){return U->magic==MAGIC&&supported((void*)U->view)?(void*)U->view:0;}
