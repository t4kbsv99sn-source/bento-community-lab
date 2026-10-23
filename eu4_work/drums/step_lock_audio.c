/* BENTO_MOD L7: two voice locks plus step-scoped shared one-shot sends. */
#include "step_lock_shared.h"
typedef struct {u32 parameter,voice,word;int pitch_base;u32 source;} Entry;
typedef struct {u32 magic,pending,root,word,count,queue,sequence,route;Entry entries[256];} Audio;
#define A ((volatile Audio*)0x24046000u)
#define MAGIC 0x374c5042u
typedef struct {u32 handle,root,sequence,owner,row,step,word,saved_delay,saved_reverb,saved_enabled,in_render,reserved;} Send;
typedef struct {u32 magic,reserved[3];Send entries[128];} Sends;
#define S ((volatile Sends*)0x24044000u)
_Static_assert(0x24044000u+sizeof(Sends)<=0x24045820u,"Send table overlaps snare pool");
_Static_assert(0x24046000u+sizeof(Audio)<=0x24047420u,"Lock table overlaps snare pool");
#define SEND_MAGIC 0x37535042u
static void init(void){
 if(A->magic!=MAGIC){for(u32 i=0;i<sizeof(Audio)/4;i++)((volatile u32*)A)[i]=0;A->magic=MAGIC;}
 if(S->magic!=SEND_MAGIC){for(u32 i=0;i<sizeof(Sends)/4;i++)((volatile u32*)S)[i]=0;S->magic=SEND_MAGIC;}
}
static u32 indexof(u32 p){return ((p>>6)^(p>>14))&255;}
__attribute__((used)) void lock_pending(u32 w){init();A->pending=has_locks(w)?w:0;A->queue=0;A->sequence=0;A->route=0;if(A->pending)*(volatile u32*)0x24048c64u=0;}
/* The native condition counter distinguishes a one-step loop from its previous pass. */
static u32 epoch(void *seq){
 for(u32 i=0;i<16;i++){void *c=(void*)(0x24048a60u+i*32);
  if(W(c,0)==(u32)seq && W(c,4)==W(seq,12) && W(c,8)==W(seq,0x86c0))return W(c,12)+1;
 }return 0;
}
/* Resolve the same primary sound destination as native 0805F8E0/0809F040.
 * Only that queue may receive +20 payload. MIDI forwarding keeps its own +20. */
__attribute__((used)) void lock_route(void *seq,void *router,u32 drum){
 if(!A->pending || drum>=16)return;
 u32 h=W(seq,0x86dc+drum*4),n=W(router,0x508);if(n>160)return;
 for(u32 i=0;i<n;i++)if(W(router,8+i*8)==h){A->queue=W(router,4)+W(router,12+i*8)*0x604;break;}
 if(!A->queue)return;
 u32 slot=128;for(u32 i=0;i<128;i++){
  if(S->entries[i].handle==h){slot=i;break;}
  if(!S->entries[i].handle && slot==128)slot=i;
 }
 if(slot==128)for(u32 i=0;i<128;i++){
  volatile Send *old=&S->entries[i];void *prior=(void*)old->sequence;
  u32 a=lock_kind(lock_slot(old->word,0)),b=lock_kind(lock_slot(old->word,1));
  if(!old->in_render && ((!old->word || ((a<10 || a>11) && (b<10 || b>11))) || !prior || !B(prior,0x20) || W(prior,12)!=old->owner || W(prior,0x86c0)!=old->row || W(prior,0x14)!=old->step)){
   for(u32 j=0;j<sizeof(Send)/4;j++)((volatile u32*)old)[j]=0;slot=i;break;
  }
 }
 if(slot==128)return;
 volatile Send *x=&S->entries[slot];x->handle=h;x->sequence=(u32)seq;x->owner=W(seq,12);x->row=W(seq,0x86c0);x->step=W(seq,0x14);x->reserved=epoch(seq);
 A->sequence=(u32)seq;A->route=slot+1;
}
__attribute__((used)) void lock_queue(void *queue,void *record){
 if(A->magic!=MAGIC || !A->pending || B(record,0)!=0x12)return;
 u32 w=A->pending;
 if((w&0x80000000u) || lock_kind(w)>=10){
  if(A->queue!=(u32)queue || !A->route)return;
  B(record,1)=0xb7;H(record,2)=(unsigned short)A->route;W(record,20)=w;
 }else{B(record,1)=(u8)(w>>16);B(record,2)=(u8)w;B(record,3)=(u8)(w>>8);}
}
__attribute__((used)) void lock_note(void *root,const void *record){
 init();A->root=(u32)root;A->word=0;
 if(B(record,0)!=0x12 || W(root,0)!=0x080ac66cu)return;
 u32 w=0,route=0;
 if(B(record,1)==0xb7){route=H(record,2);if(route && route<=128 && S->entries[route-1].handle==W(root,12))w=W(record,20);}
 else w=LOCK_TAG|((u32)B(record,1)<<16)|B(record,2)|((u32)B(record,3)<<8);
 if(has_locks(w))A->word=w;
 volatile Send *x=0;
 if(route && route<=128)x=&S->entries[route-1];
 else for(u32 i=0;i<128;i++)if(S->entries[i].handle==W(root,12)){x=&S->entries[i];break;}
 if(x){x->root=(u32)root;x->word=A->word;}
}
/* Back-shift deletion keeps unsuccessful parameter lookups short after long jams. */
static void erase(u32 hole){
 A->entries[hole].parameter=0;
 for(u32 n=0,j=(hole+1)&255;n<255;n++,j=(j+1)&255){
  u32 key=A->entries[j].parameter;if(!key)break;
  u32 origin=indexof(key);
  if(((j-origin)&255)>=((j-hole)&255)){
   A->entries[hole]=A->entries[j];hole=j;A->entries[hole].parameter=0;
  }
 }
}

static void attach(void *voice,void *root,u32 w){
 u32 k=lock_kind(w);if(!k || k>=10)return;
 if(k==8){*(volatile float*)((u8*)voice+0x428)=(float)decode_value(w)/1000.0f;return;}
 static const u32 offsets[]={0,0x180,0x300,0x1c0,0x388,0x3d0,0x430,0x470,0x428,0x4b0};
 u32 p=(u32)voice+offsets[k],at=indexof(p);
 for(u32 i=0;i<256;i++){
  u32 j=(at+i)&255;if(A->entries[j].parameter && A->entries[j].parameter!=p)continue;
  A->entries[j].voice=(u32)voice;A->entries[j].word=w;A->entries[j].source=W((void*)p,0);
  A->entries[j].pitch_base=(int)W(root,0x104);A->entries[j].parameter=p;A->count++;return;
 }
}
__attribute__((used)) void lock_voice(void *voice,void *root){
 init();W(voice,0x428)=W(root,0x3e0);
 for(u32 i=0;i<256;){if(A->entries[i].parameter && A->entries[i].voice==(u32)voice){erase(i);if(A->count)A->count--;}else i++;}
 if(A->root!=(u32)root || W(root,0)!=0x080ac66cu)return;
 u32 first=lock_slot(A->word,0),second=lock_slot(A->word,1),needed=0;
 for(u32 i=0;i<2;i++){u32 k=lock_kind(i?second:first);if(k && k!=8 && k<10)needed++;}
 if(A->count+needed>256)return;
 attach(voice,root,first);attach(voice,root,second);
}
/* Native send gain adapter is fixed at 080D33C0 and takes integer thousandths,
 * returning S0 bits in R0. No incorrect soft-float call into a hard-VFP routine. */
__attribute__((used)) void sends_begin(void *root){
 init();for(u32 i=0;i<128;i++){
  volatile Send *x=&S->entries[i];if(x->root!=(u32)root || x->handle!=W(root,12) || !x->word)continue;
  void *seq=(void*)x->sequence;
  if(!seq || !B(seq,0x20) || W(seq,12)!=x->owner || W(seq,0x86c0)!=x->row || W(seq,0x14)!=x->step || (x->reserved && epoch(seq)!=x->reserved)){x->word=0;return;}
  u32 a=lock_slot(x->word,0),b=lock_slot(x->word,1);if((lock_kind(a)<10 || lock_kind(a)>11) && (lock_kind(b)<10 || lock_kind(b)>11))return;
  if(x->in_render)return;
  x->saved_delay=W(root,0x608);x->saved_reverb=W(root,0x60c);x->saved_enabled=B(root,0x624);x->in_render=1;
  for(u32 j=0;j<2;j++){u32 w=j?b:a,k=lock_kind(w);if(k<10 || k>11)continue;
   u32 gain=FN(0x080d33c0,u32(*)(int))(decode_value(w));W(root,k==10?0x608:0x60c)=gain;
  }
  if(W(root,0x608) || W(root,0x60c))B(root,0x624)=1;
  return;
 }
}
__attribute__((used)) void sends_end(void *root){
 if(S->magic!=SEND_MAGIC)return;
 for(u32 i=0;i<128;i++){volatile Send *x=&S->entries[i];if(x->root!=(u32)root || !x->in_render)continue;
  W(root,0x608)=x->saved_delay;W(root,0x60c)=x->saved_reverb;B(root,0x624)=(u8)x->saved_enabled;x->in_render=0;return;
 }
}
__attribute__((used,section(".entry"))) int edited_evaluate(void *parameter){
 if(A->magic!=MAGIC || !A->count)return 0;
 u32 at=indexof((u32)parameter);volatile Entry *e=0;
 for(u32 i=0;i<256;i++){
  volatile Entry *x=&A->entries[(at+i)&255];
  if(!x->parameter)return 0;
  if(x->parameter==(u32)parameter){e=x;break;}
 }
 if(!e || W(parameter,0)!=e->source || !lock_kind(e->word))return 0;
 u32 k=lock_kind(e->word);float value;
 int raw=decode_value(e->word);
 if(k==1)value=raw<=-60000?0.0f:raw>12000?1.1875f:1.0f+(float)raw/60000.0f;
 else if(k==2){
  value=(float)(raw-e->pitch_base)/12000.0f;
  /* Native base source here is pitch bend, separate from the fixed note pitch. */
  if(W(parameter,0))value+=*(volatile float*)(W(parameter,0)+4u)*(*(volatile float*)((u8*)parameter+4));
 }
 else value=(float)raw/1000.0f;
 /* A voice-owned lock replaces base + native A-D, retains the three user mods. */
 u32 copy[16];for(u32 i=0;i<16;i++)copy[i]=W(parameter,i*4);
 struct {u32 opaque;float value;} source={0,value};
 copy[0]=(u32)&source;copy[1]=0x3f800000u;copy[8]=0;copy[9]=0;
 if(k==2){ /* Pitch is a delta from the separate native base pitch. */
  copy[13]=0xc0800000u;copy[14]=0x40800000u;
 }
 u32 count=0;for(u32 i=0;i<5;i++)if(copy[i*2])((u8*)copy)[0x28+count++]=(u8)i;
 copy[12]=count;FN(0x080d1f00,void(*)(void*))(copy);W(parameter,0x3c)=copy[15];return 1;
}
