#include "native_insert.h"
#define W(p,o) (*(volatile uint32_t*)((uint8_t*)(p)+(o)))
#define B(p,o) (*(volatile uint8_t*)((uint8_t*)(p)+(o)))
#define H(p,o) (*(volatile uint16_t*)((uint8_t*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define MAX_NATIVE 511u
#define SCRATCH 0x3004u
static int read_note(void *c,unsigned i,uint32_t *n){return FN(0x0810d2c0,int(*)(void*,unsigned,void*))(c,i,n);}
static int is_pitched(unsigned type){return type==17||type==18||type==19||type==22;}
int chord_native_insert(ChordNative *s,void *m,const Progression *p){
 if(!s||!m||!s->seq||!s->owner)return CH_INVALID;
 uint32_t owner=0,length=0;void *node=0,*root=(void*)W(m,0);
 if(!root||W(m,0x144)!=s->seq||!FN(0x08133cfc,int(*)(void*,void*))(m,&owner)||owner!=s->owner||!is_pitched(FN(0x08133f7c,unsigned(*)(void*,void*))(m,&owner)))return CH_STALE;
 if(!FN(0x08133614,int(*)(void*,void*,unsigned,void*))(m,&s->seq,0x62,&length)||!length||length>256||length*960!=s->clip_end)return CH_STALE;
 if(!FN(0x0812dfe8,int(*)(void*,unsigned,void*))(root,s->seq,&node)||!node)return CH_STALE;
 void *container=(uint8_t*)node+12;unsigned count=W(container,0x3000);if(count>MAX_NATIVE)return CH_INVALID;
 ChordNote notes[CH_MAX_NOTES];int n=chord_render(p,notes,CH_MAX_NOTES,s->clip_end);if(n<0)return -n;
 if(count+(unsigned)n>MAX_NATIVE)return CH_CAPACITY;
 uint32_t raw[6],maxid=0;
 for(unsigned i=0;i<count;i++){
  if(!read_note(container,i,raw))return CH_INVALID;if(raw[3]>maxid)maxid=raw[3];
  if(B(raw,0)!=1||H(raw,2)!=0)continue;
  /* Half-open time ranges: adjacent notes are legal; overlapping same-pitch
     notes are refused rather than silently duplicated or replaced. */
  for(int j=0;j<n;j++)if(H(raw,16)==notes[j].pitch&&raw[1]<notes[j].end&&(raw[1]>0xffffffffu-raw[2]||notes[j].start<raw[1]+raw[2]))return CH_CONFLICT;
 }
 uint32_t next=W(root,0x68);if(!next||next<=maxid||(unsigned)n>0xffffffffu-next)return CH_INVALID;
 if(!s->scratch){
  uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);
  if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<SCRATCH+32)return CH_MEMORY;
  uint32_t allocated=FN(0x08104c08,uint32_t(*)(unsigned))(SCRATCH);if(allocated!=cursor)return CH_MEMORY;s->scratch=allocated;
 }
 if(s->scratch<0xc0000000u||s->scratch>0xc8000000u-SCRATCH||(s->scratch&3))return CH_MEMORY;
 void *temp=(void*)s->scratch;FN(0x0810d16c,void(*)(void*))(temp);
 /* Musical bounds, native capacity, ID headroom and allocation have all
     passed before the single snapshot/mutation boundary. */
 FN(0x081338dc,void(*)(void*,void*))(m,&s->seq);
 s->note_count=(unsigned)n;
 /* The ID allocator inserts into the model. Bulk publish sends those same
     IDs to the audio queue and must not allocate them a second time. */
 for(int i=0;i<n;i++){
  uint32_t event[6]={1,notes[i].start,notes[i].end-notes[i].start,0,(uint32_t)notes[i].pitch|((uint32_t)notes[i].velocity<<16),0};
  event[3]=FN(0x0812e070,uint32_t(*)(void*,unsigned,void*))(root,s->seq,event);s->note_ids[i]=event[3];FN(0x0810d176,void(*)(void*,void*))(temp,event);
 }
 FN(0x08136544,void(*)(void*,void*,void*))(m,&s->seq,temp);
 W(m,0x36c4)=1;uint32_t event[5]={0xc7,s->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((uint8_t*)m+0x160,event);
 return CH_OK;
}
