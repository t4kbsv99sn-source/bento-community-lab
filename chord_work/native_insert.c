#include "native_insert.h"
#define W(p,o) (*(volatile uint32_t*)((uint8_t*)(p)+(o)))
#define B(p,o) (*(volatile uint8_t*)((uint8_t*)(p)+(o)))
#define H(p,o) (*(volatile uint16_t*)((uint8_t*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define MAX_NATIVE 511u
#define SCRATCH 0x3004u
static int read_note(void *c,unsigned i,uint32_t *n){return FN(0x0810d2c0,int(*)(void*,unsigned,void*))(c,i,n);}
static int is_pitched(unsigned type){return type==15||type==18||type==19||type==22;} /* 15 multisample (CH7) */
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
 if(!s->no_snapshot)FN(0x081338dc,void(*)(void*,void*))(m,&s->seq);
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

/* CH4: remove the previous live draft (exactly the IDs this adapter inserted)
   in one native bulk delete; notes the user added or edited keep their IDs. */
int chord_native_remove(ChordNative *s,void *m){
 if(!s||!m||!s->note_count)return CH_OK;
 void *node=0,*root=(void*)W(m,0);
 if(!root||!FN(0x0812dfe8,int(*)(void*,unsigned,void*))(root,s->seq,&node)||!node){s->note_count=0;return CH_STALE;}
 if(!s->scratch||s->scratch<0xc0000000u||s->scratch>0xc8000000u-SCRATCH)return CH_MEMORY;
 void *container=(uint8_t*)node+12,*temp=(void*)s->scratch;unsigned count=W(container,0x3000),found=0;if(count>MAX_NATIVE)return CH_INVALID;
 uint32_t raw[6];FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<count;i++){if(!read_note(container,i,raw))return CH_INVALID;
  for(unsigned j=0;j<s->note_count&&j<CH_MAX_NOTES;j++)if(raw[3]==s->note_ids[j]){FN(0x0810d176,void(*)(void*,void*))(temp,raw);found++;break;}}
 if(found)FN(0x08136fb4,void(*)(void*,void*,void*))(m,&s->seq,temp);
 s->note_count=0;return CH_OK;
}

static void *container_of(ChordNative *s,void *m){
 void *node=0,*root=(void*)W(m,0);if(!root||!FN(0x0812dfe8,int(*)(void*,unsigned,void*))(root,s->seq,&node)||!node)return 0;
 void *c=(uint8_t*)node+12;return W(c,0x3000)<=MAX_NATIVE?c:0;
}
/* CH5: chords already in the clip = 2+ pitched notes starting together. Writes
   up to max sorted, distinct start ticks; returns the count. */
int chord_native_starts(ChordNative *s,void *m,uint32_t *starts,unsigned max){
 void *c=container_of(s,m);if(!c)return 0;unsigned count=W(c,0x3000),n=0;uint32_t a[6],b[6];
 for(unsigned i=0;i<count;i++){
  if(!read_note(c,i,a)||B(a,0)!=1||H(a,2)!=0)continue;unsigned same=0;
  for(unsigned j=0;j<count;j++)if(j!=i&&read_note(c,j,b)&&B(b,0)==1&&H(b,2)==0&&b[1]==a[1])same=1;
  if(!same)continue;unsigned k=0;while(k<n&&starts[k]<a[1])k++;if(k<n&&starts[k]==a[1])continue;
  if(n<max){for(unsigned j=n;j>k;j--)starts[j]=starts[j-1];starts[k]=a[1];n++;}
 }
 return (int)n;
}
/* Adopt the chord starting at `start` as the live draft: its notes become the
   notes the next edit replaces. Fills lowest pitch, pitch-class mask, length
   (longest note) and velocity of the first note. Returns the note count. */
int chord_native_adopt(ChordNative *s,void *m,uint32_t start,int *low,unsigned *mask,uint32_t *length,unsigned *velocity){
 void *c=container_of(s,m);if(!c)return 0;unsigned count=W(c,0x3000),n=0;uint32_t a[6];*low=128;*mask=0;*length=0;*velocity=100;
 for(unsigned i=0;i<count;i++){if(!read_note(c,i,a)||B(a,0)!=1||H(a,2)!=0||a[1]!=start)continue;
  int pitch=H(a,16);if(pitch<*low)*low=pitch;if(a[2]>*length)*length=a[2];if(!n)*velocity=H(a,18);if(n<CH_MAX_NOTES)s->note_ids[n++]=a[3];}
 for(unsigned i=0;i<count;i++){if(read_note(c,i,a)&&B(a,0)==1&&H(a,2)==0&&a[1]==start)*mask|=1u<<((H(a,16)-*low)%24);}
 s->note_count=n;return (int)n;
}
/* CH5 replace-on-overlap (owner): one bulk delete removes the previous draft
   (its IDs) and any same-pitch notes overlapping the new chord, so the insert
   never refuses with "Overlapping note". */
int chord_native_clear_for(ChordNative *s,void *m,const Progression *p){
 ChordNote notes[CH_MAX_NOTES];int n=chord_render(p,notes,CH_MAX_NOTES,s->clip_end);if(n<0)return -n;
 void *c=container_of(s,m);if(!c){s->note_count=0;return CH_STALE;}
 if(!s->scratch){uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);
  if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<SCRATCH+32)return CH_MEMORY;
  uint32_t allocated=FN(0x08104c08,uint32_t(*)(unsigned))(SCRATCH);if(allocated!=cursor)return CH_MEMORY;s->scratch=allocated;}
 void *temp=(void*)s->scratch;unsigned count=W(c,0x3000),found=0;uint32_t raw[6];FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<count;i++){if(!read_note(c,i,raw))return CH_INVALID;int hit=0;
  for(unsigned j=0;j<s->note_count&&j<CH_MAX_NOTES;j++)if(raw[3]==s->note_ids[j])hit=1;
  if(!hit&&B(raw,0)==1&&H(raw,2)==0)for(int j=0;j<n;j++)if(H(raw,16)==notes[j].pitch&&raw[1]<notes[j].end&&notes[j].start<raw[1]+raw[2])hit=1;
  if(hit){FN(0x0810d176,void(*)(void*,void*))(temp,raw);found++;}}
 if(found)FN(0x08136fb4,void(*)(void*,void*,void*))(m,&s->seq,temp);
 s->note_count=0;return CH_OK;
}
/* CH7: start tick of the pitched note with this native ID (touch selection). */
int chord_native_find(ChordNative *s,void *m,uint32_t id,uint32_t *start){
 void *c=container_of(s,m);if(!c||!start)return 0;unsigned count=W(c,0x3000);uint32_t a[6];
 for(unsigned i=0;i<count;i++)if(read_note(c,i,a)&&B(a,0)==1&&H(a,2)==0&&a[3]==id){*start=a[1];return 1;}
 return 0;
}
/* CH9 recorded chords + Rhythm (owner): the native recorder writes each played
   chord as notes held for as long as the pad was down. Pitched notes with an
   ID >= min_id in the current clip are grouped by start (2+ notes = a chord)
   and each chord is replaced, in one Undo step, by the rhythm's hits over its
   held length. Returns the number of chords reshaped. */
int chord_native_rhythmize(ChordNative *s,void *m,uint32_t min_id,unsigned rhythm,ChordHits hits){
 void *node=0,*root=(void*)W(m,0);uint32_t seq=W(m,0x144);if(!s||!root||!seq||!hits)return 0;
 if(!FN(0x0812dfe8,int(*)(void*,unsigned,void*))(root,seq,&node)||!node)return 0;
 void *c=(uint8_t*)node+12;unsigned count=W(c,0x3000);if(count>MAX_NATIVE)return 0;
 uint32_t raw[6],starts[16],lens[16];uint32_t notes[CH_MAX_NOTES][6];unsigned n=0,g=0,size[16]={0};
 for(unsigned i=0;i<count&&n<CH_MAX_NOTES;i++){
  if(!read_note(c,i,raw)||B(raw,0)!=1||H(raw,2)!=0||raw[3]<min_id)continue;
  unsigned k=0;while(k<g&&starts[k]!=raw[1])k++;if(k==g){if(g==16)continue;starts[g]=raw[1];lens[g]=0;g++;}
  size[k]++;if(raw[2]>lens[k])lens[k]=raw[2];for(unsigned j=0;j<6;j++)notes[n][j]=raw[j];n++;
 }
 unsigned chords=0;for(unsigned k=0;k<g;k++)if(size[k]>=2)chords++;if(!chords)return 0;
 if(!s->scratch){uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);
  if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<SCRATCH+32)return 0;
  uint32_t allocated=FN(0x08104c08,uint32_t(*)(unsigned))(SCRATCH);if(allocated!=cursor)return 0;s->scratch=allocated;}
 void *temp=(void*)s->scratch;
 /* Room check: every chord's hits fit the native clip. */
 unsigned add=0;for(unsigned i=0;i<n;i++){unsigned k=0;while(starts[k]!=notes[i][1])k++;if(size[k]<2)continue;uint32_t at[CH_MAX_CHORDS],dur[CH_MAX_CHORDS];add+=hits(rhythm,lens[k],at,dur)-1;}
 if(count+add>MAX_NATIVE)return 0;
 FN(0x081338dc,void(*)(void*,void*))(m,&seq);
 FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<n;i++){unsigned k=0;while(starts[k]!=notes[i][1])k++;if(size[k]>=2)FN(0x0810d176,void(*)(void*,void*))(temp,notes[i]);}
 FN(0x08136fb4,void(*)(void*,void*,void*))(m,&seq,temp);
 FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<n;i++){
  unsigned k=0;while(starts[k]!=notes[i][1])k++;if(size[k]<2)continue;
  uint32_t at[CH_MAX_CHORDS],dur[CH_MAX_CHORDS];unsigned h=hits(rhythm,lens[k],at,dur);
  for(unsigned j=0;j<h;j++){uint32_t e[6]={1,starts[k]+at[j],dur[j],0,notes[i][4],0};e[3]=FN(0x0812e070,uint32_t(*)(void*,unsigned,void*))(root,seq,e);FN(0x0810d176,void(*)(void*,void*))(temp,e);}
 }
 FN(0x08136544,void(*)(void*,void*,void*))(m,&seq,temp);
 W(m,0x36c4)=1;uint32_t ev[5]={0xc7,seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((uint8_t*)m+0x160,ev);
 return (int)chords;
}

static int scratch_of(ChordNative *s){
 if(!s->scratch){uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0);
  if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<SCRATCH+32)return 0;
  uint32_t allocated=FN(0x08104c08,uint32_t(*)(unsigned))(SCRATCH);if(allocated!=cursor)return 0;s->scratch=allocated;}
 return s->scratch>=0xc0000000u&&s->scratch<=0xc8000000u-SCRATCH&&!(s->scratch&3);
}
static int own(ChordNative *s,uint32_t id){for(unsigned j=0;j<s->note_count&&j<CH_MAX_NOTES;j++)if(s->note_ids[j]==id)return 1;return 0;}
static void changed(ChordNative *s,void *m){W(m,0x36c4)=1;uint32_t event[5]={0xc7,s->seq,0,0,0};FN(0x08173272,void(*)(void*,void*))((uint8_t*)m+0x160,event);}
int chord_native_shift(ChordNative *s,void *m,uint32_t from,int32_t delta){
 if(!delta)return CH_OK;void *c=container_of(s,m);if(!c)return CH_STALE;if(!scratch_of(s))return CH_MEMORY;
 void *temp=(void*)s->scratch;unsigned count=W(c,0x3000),moved=0;uint32_t raw[6];FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<count;i++){if(!read_note(c,i,raw))return CH_INVALID;if(B(raw,0)!=1||H(raw,2)!=0||raw[1]<from||own(s,raw[3]))continue;
  int64_t at=(int64_t)raw[1]+delta;if(at<0||at+raw[2]>s->clip_end)return CH_RANGE; /* refuse rather than lose notes past the clip end */
  raw[1]=(uint32_t)at;FN(0x0810d176,void(*)(void*,void*))(temp,raw);moved++;}
 if(!moved)return CH_OK;
 if(!s->no_snapshot)FN(0x081338dc,void(*)(void*,void*))(m,&s->seq);
 FN(0x08136544,void(*)(void*,void*,void*))(m,&s->seq,temp);changed(s,m);return CH_OK;
}
int chord_native_delete(ChordNative *s,void *m){
 if(!s->note_count)return CH_OK;void *c=container_of(s,m);if(!c)return CH_STALE;if(!scratch_of(s))return CH_MEMORY;
 void *temp=(void*)s->scratch;unsigned count=W(c,0x3000),found=0;uint32_t raw[6];FN(0x0810d16c,void(*)(void*))(temp);
 for(unsigned i=0;i<count;i++){if(!read_note(c,i,raw))return CH_INVALID;if(own(s,raw[3])){FN(0x0810d176,void(*)(void*,void*))(temp,raw);found++;}}
 if(found){if(!s->no_snapshot)FN(0x081338dc,void(*)(void*,void*))(m,&s->seq);FN(0x08136fb4,void(*)(void*,void*,void*))(m,&s->seq,temp);changed(s,m);}
 s->note_count=0;return CH_OK;
}
