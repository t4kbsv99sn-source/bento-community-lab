/* BENTO_MOD EU1: independent integer Euclidean distribution into native notes.
   Original implementation; no imported third-party sequencing implementation. */
#include "euclidean.h"
#define MAX_STEPS 256u
#define MAX_NOTES 511u
#define BYTES 0x3004u
static int slot_u(u32 *e,u32 u){int t=(int)e[1],U=(int)u,q=t%U;if(q>U/2)q-=U;return (t-q)/U;}
#define slot(n) slot_u(n,960u)
static int read(void *c,u32 i,u32 *e){return FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,e);}
static void add(void *c,u32 *e){FN(0x0810d176,void(*)(void*,void*))(c,e);}
static void empty(void *c){FN(0x0810d16c,void(*)(void*))(c);}
__attribute__((used)) int eu_hit(u32 step,u32 steps,u32 hits,u32 rotate){
 if(!steps||steps>MAX_STEPS||hits>steps||step>=steps)return 0;
 return (((step+steps-rotate%steps)%steps)*hits)%steps<hits;
}
/* Drum rows match the pad address (H+2); melodic rows match pitch (H+16). */
static int match(Euclid *e,u32 *n){return B(n,0)==1&&(eu_mel(e)?H(n,16)==eu_mel_pitch(e):H(n,2)==e->pad);}
__attribute__((used)) int eu_pitched_type(u32 t){return t==15||t==18||t==19||t==22;} /* CH7: class ids (0812EFxx registration): 15 multisample, 18 wavetable, 19 granular, 22 external; 17 is a loop track */
static int current(Euclid *e,void *m){
 u32 owner=0,length=0;
 return e->valid && e->steps && e->steps<=MAX_STEPS && e->pad<16 &&
  FN(0x08133cfc,int(*)(void*,void*))(m,&owner) && owner==e->owner &&
  (eu_mel(e)?eu_pitched_type(FN(0x08133f7c,u32(*)(void*,void*))(m,&owner)):FN(0x08133f7c,u32(*)(void*,void*))(m,&owner)==14) &&
  FN(0x08133614,int(*)(void*,void*,u32,void*))(m,&e->seq,0x62,&length) && length>0 && length<=MAX_STEPS;
}
__attribute__((used)) void eu_capture(Euclid *e,void *v){
 if(B(MODEL,0x12c)!=0x27)return;
 u32 seq=W(v,0x113e4),owner=W(v,0x113e8),pad=W(v,0x11400),steps=W(v,0x113f8);
 if(!seq||!owner||!W(v,0x113dc)||pad>=16||!steps||steps>MAX_STEPS){e->valid=0;return;}
 if(FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&owner)!=14){e->valid=0;return;}
 if(!e->valid||seq!=e->seq||owner!=e->owner||pad!=e->pad||steps!=e->steps){
  e->status=EU_OK;e->seq=seq;e->owner=owner;e->pad=pad;e->steps=steps;e->hits=0;e->rotate=0;e->velocity=100;e->preview=1;
  u32 bits[8]={0},n[6];
  for(u32 i=0;i<MAX_NOTES&&read((void*)W(v,0x113dc),i,n);i++){
   int s=slot(n);if(B(n,0)!=1||H(n,2)!=pad||s<0||(u32)s>=steps)continue;
   u32 mask=1u<<((u32)s&31);if(!(bits[(u32)s/32]&mask)){bits[(u32)s/32]|=mask;e->hits++;}
  }
 }
 e->valid=1;
}
__attribute__((used)) int eu_begin(Euclid *e,void *m){
 if(W(m,0x144)!=e->seq||!current(e,m))return 0;
 for(u32 i=0;i<4;i++)e->context[i]=W(m,0x13c+i*4);
 e->status=EU_OK;return 1;
}
static int heap_span(u32 p,u32 end){
 return end>=p && ((p>=0xc0000000u&&end<=0xc8000000u)||(p>=0x30000000u&&end<=0x30040000u));
}
static int scratch(Euclid *e){
 if(e->scratch)return heap_span(e->scratch,e->scratch+BYTES);
 /* Native 08104C08 is a bump allocator, not malloc: allocate only once and
    preflight its actual cursor/end before calling its fatal-on-overflow path. */
 u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);
 if(!heap_span(p,end)||end-p<0x3020u)return 0;
 u32 allocated=FN(0x08104c08,u32(*)(u32))(BYTES);
 if(allocated!=p||!heap_span(allocated,allocated+BYTES))return 0;
 e->scratch=allocated;return 1;
}
/* P19 (owner video on P18: melodic Euclid silent while inserted chords play).
   Melodic rows are played by the native sequencer like any clip notes: the
   row's cycle (Length) repeats across the whole clip, so a 16-step row in a
   32-step clip writes two cycles. Drum rows keep their own M7 clock. */
static u32 span_of(Euclid *e,void *m){
 if(!eu_mel(e))return e->steps;u32 len=0,seq=e->seq;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(m,&seq,0x62,&len)||!len)return e->steps;return len>MAX_STEPS?MAX_STEPS:len;
}
static int hit_at(Euclid *e,u32 s,u32 span){return s<span&&e->steps&&eu_hit(s%e->steps,e->steps,e->hits,e->rotate);}
__attribute__((used)) int eu_apply(Euclid *e,void *m){
 if(!current(e,m))return EU_STALE;
 if(e->hits>e->steps||e->rotate>=e->steps||!e->velocity||e->velocity>127)return EU_INVALID;
 void *root=(void*)W(m,0),*node=0;
 if(!root||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,e->seq,&node)||!node)return EU_STALE;
 void *c=(u8*)node+12;u32 count=W(c,0x3000),span=span_of(e,m);if(count>MAX_NOTES)return EU_INVALID;
 u32 bits[8]={0},n[6],remove=0,create=0,maxid=0;
 for(u32 i=0;i<count;i++){
  if(!read(c,i,n))return EU_INVALID;if(n[3]>maxid)maxid=n[3];
  int s=slot_u(n,eu_unit(e));if(!match(e,n)||s<0||(u32)s>=MAX_STEPS)continue;
  if(!hit_at(e,(u32)s,span))remove++;
  else bits[(u32)s/32]|=1u<<((u32)s&31);
 }
 for(u32 s=0;s<span;s++)if(hit_at(e,s,span)&&!(bits[s/32]&(1u<<(s&31))))create++;
 if(count-remove+create>MAX_NOTES)return EU_FULL;
 if(!remove&&!create)return EU_SAME;
 u32 next=W(root,0x68);
 if(create&&(!next||next<=maxid||create>0xffffffffu-next))return EU_INVALID;
 if(!scratch(e))return EU_MEMORY;
 void *temp=(void*)e->scratch;empty(temp);
 for(u32 i=0;i<count;i++){
  if(!read(c,i,n))return EU_INVALID;int s=slot_u(n,eu_unit(e));
  if(match(e,n)&&s>=0&&(u32)s<MAX_STEPS&&!hit_at(e,(u32)s,span))add(temp,n);
 }
 /* Native bulk delete takes exactly one native undo snapshot before mutation,
    updates model and audio, and emits the standard sequence refresh event. */
 if(remove)FN(0x08136fb4,void(*)(void*,void*,void*))(m,&e->seq,temp);
 else FN(0x081338dc,void(*)(void*,void*))(m,&e->seq);
 empty(temp);
 for(u32 s=0;s<span;s++){
  if(!hit_at(e,s,span)||(bits[s/32]&(1u<<(s&31))))continue;
  u32 u=eu_unit(e),event[6]={1u|(e->pad<<16),s*u,u,0,e->velocity<<16,0};
  if(eu_mel(e)){event[0]=1u;event[2]=eu_mel_gate(e)*u/4u;event[4]=eu_mel_pitch(e)|(e->velocity<<16);}
  /* Byte 1 zero = native Always, not our A:B condition ID 100. Native ID
     allocator advances the project's counter; retained hit IDs never change. */
  event[3]=FN(0x0812e070,u32(*)(void*,u32,void*))(root,e->seq,event);add(temp,event);
 }
 if(create)FN(0x08136544,void(*)(void*,void*,void*))(m,&e->seq,temp);
 W(m,0x36c4)=1;
 u32 event[5]={0xc7,e->seq,0,0,0};
 FN(0x08173272,void(*)(void*,void*))((u8*)m+0x160,event);
 return EU_OK;
}
__attribute__((used)) void eu_return(Euclid *e,void *m){
 if(!current(e,m)){u32 event[5]={0x73,0,11,0,0};FN(0x08142afc,void(*)(void*,void*))(m,event);return;}
 for(u32 i=0;i<4;i++)W(m,0x13c+i*4)=e->context[i];
 FN(0x081420ec,void(*)(void*,u32,u32,u32,u32))(m,0x27,0,0,0);
}

/* Native per-pad velocity edit, one undo gesture; preserve IDs/conditions/locks. */
int eu_velocity(Euclid *e,void *m){
 if(!current(e,m)||!scratch(e))return EU_STALE;
 void *node=0,*root=(void*)W(m,0);if(!root||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,e->seq,&node)||!node)return EU_STALE;
 void *c=(u8*)node+12,*temp=(void*)e->scratch;u32 n[6],count=W(c,0x3000),changed=0;if(count>MAX_NOTES)return EU_INVALID;empty(temp);
 for(u32 i=0;i<count;i++){
  if(!read(c,i,n))return EU_INVALID;int s=slot_u(n,eu_unit(e));
  if(!match(e,n)||s<0||(u32)s>=span_of(e,m)||H(n,18)==e->velocity)continue;
  H(n,18)=(u16)e->velocity;add(temp,n);changed++;
 }
 if(!changed)return EU_SAME;
 FN(0x081338dc,void(*)(void*,void*))(m,&e->seq);
 FN(0x08136544,void(*)(void*,void*,void*))(m,&e->seq,temp);
 W(m,0x36c4)=1;u32 event[5]={0xc7,e->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((u8*)m+0x160,event);
 return EU_OK;
}

/* CH3: move a melodic row's notes to another pitch in one native undo gesture.
   Every note of the old pitch belongs to the row once it is generator-owned. */
int eu_repitch(Euclid *e,void *m,u32 pitch){
 if(!eu_mel(e)||pitch>127||!current(e,m)||!scratch(e))return EU_STALE;
 void *node=0,*root=(void*)W(m,0);if(!root||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,e->seq,&node)||!node)return EU_STALE;
 void *c=(u8*)node+12,*temp=(void*)e->scratch;u32 n[6],count=W(c,0x3000),moved=0;if(count>MAX_NOTES)return EU_INVALID;
 for(u32 i=0;i<count;i++){if(!read(c,i,n))return EU_INVALID;if(B(n,0)==1&&H(n,16)==pitch&&pitch!=eu_mel_pitch(e))return EU_USED;}
 empty(temp);
 for(u32 i=0;i<count;i++){if(!read(c,i,n))return EU_INVALID;if(!match(e,n))continue;H(n,16)=(u16)pitch;add(temp,n);moved++;}
 if(!moved)return EU_SAME;
 FN(0x081338dc,void(*)(void*,void*))(m,&e->seq);FN(0x08136544,void(*)(void*,void*,void*))(m,&e->seq,temp);
 W(m,0x36c4)=1;u32 event[5]={0xc7,e->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((u8*)m+0x160,event);return EU_OK;
}

/* CH3: apply a melodic row's gate to its existing notes (one undo gesture). */
int eu_gate_notes(Euclid *e,void *m){
 if(!eu_mel(e)||!current(e,m)||!scratch(e))return EU_STALE;
 void *node=0,*root=(void*)W(m,0);if(!root||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,e->seq,&node)||!node)return EU_STALE;
 void *c=(u8*)node+12,*temp=(void*)e->scratch;u32 n[6],count=W(c,0x3000),changed=0,len=eu_mel_gate(e)*eu_unit(e)/4u;if(count>MAX_NOTES)return EU_INVALID;empty(temp);
 for(u32 i=0;i<count;i++){if(!read(c,i,n))return EU_INVALID;int s=slot_u(n,eu_unit(e));if(!match(e,n)||s<0||(u32)s>=span_of(e,m)||n[2]==len)continue;n[2]=len;add(temp,n);changed++;}
 if(!changed)return EU_SAME;
 FN(0x081338dc,void(*)(void*,void*))(m,&e->seq);FN(0x08136544,void(*)(void*,void*,void*))(m,&e->seq,temp);
 W(m,0x36c4)=1;u32 event[5]={0xc7,e->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((u8*)m+0x160,event);return EU_OK;
}

/* P20 (owner plan: Clear acts on the selection). Deletes one drum pad's notes at
 * the selected steps (bit n = step n, 960 per step in the one-shot view) in one
 * native bulk delete (one undo step). Returns the number of notes removed. */
u32 *eu_shared_scratch(void);
__attribute__((used,retain)) int eu_clear_steps(u32 seq,u32 pad,const u32 *bits,void *m){
 Euclid e;for(u32 i=0;i<sizeof(e)/4;i++)((u32*)&e)[i]=0;e.seq=seq;e.scratch=*eu_shared_scratch();
 if(!scratch(&e))return 0;*eu_shared_scratch()=e.scratch;
 void *root=(void*)W(m,0),*node=0;if(!root||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,seq,&node)||!node)return 0;
 void *c=(u8*)node+12,*temp=(void*)e.scratch;u32 count=W(c,0x3000),n[6],hit=0;if(count>MAX_NOTES)return 0;empty(temp);
 for(u32 i=0;i<count;i++){if(!read(c,i,n))return 0;int st=slot(n);
  if(B(n,0)!=1||H(n,2)!=pad||st<0||(u32)st>=MAX_STEPS||!(bits[(u32)st/32]&(1u<<((u32)st&31))))continue;add(temp,n);hit++;}
 if(!hit)return 0;
 FN(0x08136fb4,void(*)(void*,void*,void*))(m,&seq,temp);empty(temp);
 W(m,0x36c4)=1;u32 ev[5]={0xc7,seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((u8*)m+0x160,ev);
 return (int)hit;
}
