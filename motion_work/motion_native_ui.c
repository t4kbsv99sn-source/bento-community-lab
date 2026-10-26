/* M4 producer. Native type-5 nodes own editable data and Undo copies. Only
 * immutable-under-serial compact snapshots cross to the M7 audio core. */
#include "motion_native_ui.h"
#include "../eu4_work/integration/live_shared.h"
#define UI_MAGIC 0x31554d50u
static void clear(void *p,uint32_t n){uint8_t *b=p;while(n--)*b++=0;}
static void barrier(void){__asm__ volatile("dmb" ::: "memory");}
static void *allocate(uint32_t bytes){
 uint32_t n=(bytes+31u)&~31u,p=W((void*)0x3000004c,0),end=W((void*)0x30000048,0);
 if((p&31u)||p<0xc0000000u||end>0xc8000000u||p>end||end-p<n)return 0;
 void *v=FN(0x08104c08,void*(*)(uint32_t))(n);if((uint32_t)v!=p)return 0;
 clear(v,n);return v;
}
static EuBank *root_bank(int create){
 if(EC->magic==EU_MAGIC&&EC->bytes==sizeof(EuBank)&&eu_memory(EC->pointer,sizeof(EuBank)))return (EuBank*)EC->pointer;
 if(!create)return 0;EuBank *b=allocate(sizeof(EuBank));if(!b)return 0;
 b->epoch=1;b->serial=2;EC->magic=0;EC->pointer=(uint32_t)b;EC->bytes=sizeof(*b);EC->epoch=1;barrier();EC->magic=EU_MAGIC;return b;
}
MotionUi *motion_ui_state(int create){
 EuBank *b=root_bank(create);if(!b)return 0;
 MotionUi *u=(MotionUi*)b->reserved[2];if(u)return u->magic==UI_MAGIC?u:0;
 if(!create)return 0;u=allocate(sizeof(*u));if(!u)return 0;
 MotionDevice *d=allocate(sizeof(*d));if(!d)return 0;
 d->magic=MOTION_DEVICE_MAGIC;d->bytes=sizeof(*d);d->epoch=1;d->serial=2;
 motion_bank_init(&u->take,MOTION_DEFAULT_TICKS_PER_BAR);u->length=16;
 u->device=(uint32_t)d;u->magic=UI_MAGIC;b->reserved[2]=(uint32_t)u;barrier();b->reserved[1]=(uint32_t)d;return u;
}
/* Side store: one MotionNodeExtension per clip (sequence handle), allocated from
 * the bump heap and reused. Native clones (Undo snapshot/restore, clip copy and
 * paste) copy the entry to the clone's new handle; entries whose clip no longer
 * exists in its native tree (old Undo snapshots, deleted clips) are reclaimed. */
static uint32_t model_tree(void){return W(MODEL,0);}
static int alive(uint32_t tree,uint32_t key){
 if(!tree)return 0;
 for(uint32_t i=0;i<64;i++){
  void *c=0;if(!FN(0x0812d78a,int(*)(void*,uint32_t,void**))((void*)tree,i,&c)||!c)return 0;
  void *o=0;if(FN(W(W(c,0),0x14),int(*)(void*,uint32_t,void**))(c,key,&o))return 1;
 }
 return 0;
}
static void reclaim(MotionUi *u,uint32_t keep){for(unsigned i=0;i<u->store_count;i++)if(u->store_key[i]&&u->store_key[i]!=keep&&!alive(u->store_tree[i],u->store_key[i]))u->store_key[i]=0;}
static unsigned free_slot(MotionUi *u){for(unsigned i=0;i<u->store_count;i++)if(!u->store_key[i])return i;return MOTION_STORE_SLOTS;}
static MotionNodeExtension *store_new(MotionUi *u,uint32_t seq,uint32_t tree,uint32_t keep){
 unsigned fresh=free_slot(u);
 if(fresh==MOTION_STORE_SLOTS){reclaim(u,keep);fresh=free_slot(u);}
 if(fresh==MOTION_STORE_SLOTS){
  if(u->store_count>=MOTION_STORE_SLOTS){u->error=6;return 0;}
  void *p=allocate(sizeof(MotionNodeExtension));if(!p)return 0;
  fresh=u->store_count;u->store_ptr[fresh]=(uint32_t)p;u->store_count++;
 }
 u->store_key[fresh]=seq;u->store_tag[fresh]=u->store_gen;u->store_tree[fresh]=tree;
 return (MotionNodeExtension*)u->store_ptr[fresh];
}
MotionNodeExtension *motion_store(uint32_t seq,int create){
 if(!seq)return 0;MotionUi *u=motion_ui_state(create);if(!u)return 0;
 for(unsigned i=0;i<u->store_count;i++)if(u->store_key[i]==seq)return (MotionNodeExtension*)u->store_ptr[i];
 if(!create)return 0;
 MotionNodeExtension *x=store_new(u,seq,model_tree(),0);if(!x)return 0;clear(x,sizeof(*x));
 for(unsigned i=0;i<MOTION_LANES;i++){motion_lane_init(x->lanes+i,MOTION_DEFAULT_TICKS_PER_BAR);x->gain[i]=1;}
 x->version=1;x->magic=MOTION_NODE_MAGIC;return x;
}
/* After native clone 0812EA2A(tree,type,parent,source,&out) succeeded. */
__attribute__((used,retain)) void motion_store_clone(uint32_t tree,void *source,void **out,int ok){
 if(!ok||!source||!out||!*out)return;MotionUi *u=motion_ui_state(0);if(!u)return;
 uint32_t from=W(source,0x10),to=W(*out,0x10);if(!from||!to||from==to)return;
 MotionNodeExtension *x=motion_store(from,0);if(!x||motion_store(to,0))return;
 MotionNodeExtension *y=store_new(u,to,tree,from);if(!y)return;
 const uint8_t *a=(const uint8_t*)x;uint8_t *b=(uint8_t*)y;for(uint32_t n=sizeof(*x);n--;)*b++=*a++;
}
void motion_store_loaded(uint32_t seq){MotionUi *u=motion_ui_state(0);if(!u)return;for(unsigned i=0;i<u->store_count;i++)if(u->store_key[i]==seq)u->store_tag[i]=u->store_gen|0x80000000u;}
/* After a project load: drop every clip the load did not fill (another project's handles). */
void motion_store_sweep(void){MotionUi *u=motion_ui_state(0);if(!u)return;for(unsigned i=0;i<u->store_count;i++)if(u->store_tag[i]!=(u->store_gen|0x80000000u))u->store_key[i]=0;u->store_gen=(u->store_gen+1)&0x7fffffffu;}
void *motion_ui_node(uint32_t seq,int create){
 void *p=0;if(!seq)return 0;
 if(!FN(0x0812ea72,int(*)(void*,uint32_t,void**,int))((void*)W(MODEL,0),seq,&p,create))return 0;
 return p;
}
static uint32_t next_serial(uint32_t s){s=(s+2)&~1u;return s?s:2;}
void motion_ui_publish(uint32_t seq,uint32_t owner,uint32_t row){
 if(!owner||row>=16)return;
 MotionNodeExtension *x=motion_store(seq,0);
 MotionUi *u=motion_ui_state(x!=0);if(!u)return;MotionDevice *d=(MotionDevice*)u->device;
 MotionDeviceClip *c=0;unsigned index,free_index=MOTION_DEVICE_CLIPS;
 for(index=0;index<d->count;index++){
  c=(MotionDeviceClip*)d->clips[index];if(!c->owner&&free_index==MOTION_DEVICE_CLIPS)free_index=index;if(c->owner==owner&&c->row==row)break;
 }
 if(index==d->count){
  if(!x)return;
  if(free_index<MOTION_DEVICE_CLIPS){index=free_index;c=(MotionDeviceClip*)d->clips[index];}
  else {if(index>=MOTION_DEVICE_CLIPS)return;c=allocate(sizeof(*c));if(!c){u->error=1;return;}}
  uint32_t serial=next_serial(d->serial);d->serial=serial|1;barrier();
  c->owner=owner;c->row=row;c->epoch=d->epoch;d->clips[index]=(uint32_t)c;if(index==d->count)d->count=index+1;u->directory_seq[index]=seq;barrier();d->serial=serial;
 }
 uint32_t serial=next_serial(c->serial);c->serial=serial|1;barrier();
 for(unsigned i=0;i<4;i++){
  if(x){if(motion_compact_pack(c->lanes+i,x->lanes+i)!=MOTION_OK){c->lanes[i].active=0;u->error=2;}uint16_t gain=x->gain[i]?x->gain[i]:1;c->lanes[i].reserved[0]=(uint8_t)gain;c->lanes[i].reserved[1]=(uint8_t)(gain>>8);}
  else {clear(c->lanes+i,sizeof(c->lanes[i]));c->lanes[i].ticks_per_bar=MOTION_DEFAULT_TICKS_PER_BAR;c->lanes[i].length_bars=16;}
 }
 u->directory_seq[index]=seq;c->epoch=d->epoch;barrier();c->serial=serial;
}
int motion_ui_clock(MotionUi *u,uint32_t owner,uint32_t row,uint64_t *tick){
 MotionDevice *d=(MotionDevice*)u->device;
 for(unsigned i=0;i<MOTION_DEVICE_TRACKS;i++){
  volatile MotionDeviceRuntime *r=d->runtime+i;
  uint32_t serial=r->serial;if(!serial||(serial&1)||r->epoch!=d->epoch||r->owner!=owner||r->row!=row||!r->valid)continue;
  uint64_t n=r->native_tick,launch=r->launch_tick;barrier();if(serial==r->serial&&n<=UINT64_MAX/4&&launch<=n){*tick=n*4;u->last_tick=*tick;u->launch_tick=launch*4;return 1;}
 }
 return 0;
}
int motion_ui_begin(uint32_t seq,uint32_t owner,uint32_t row){
 MotionUi *u=motion_ui_state(1);uint64_t tick;if(!u||u->take.record_held||!motion_ui_clock(u,owner,row,&tick))return 0;
 /* One native Undo snapshot for the entire gesture, before creating/mutating. */
 FN(0x081338dc,void(*)(void*,uint32_t*))(MODEL,&seq);
 void *n=motion_ui_node(seq,1);MotionNodeExtension *x=motion_store(seq,1);if(!x)return 0;
 for(unsigned i=0;i<4;i++){
  u->take.lanes[0][i]=x->lanes[i];u->gain[i]=x->gain[i]?x->gain[i]:1;
  if(u->take.lanes[0][i].active&&u->take.lanes[0][i].origin_tick<u->launch_tick)u->take.lanes[0][i].origin_tick=u->launch_tick;

 }
 if(motion_press_record(&u->take,1,0,4,tick)!=MOTION_OK)return 0;
 u->target_count=0;u->virtual_handle=0;u->seq=seq;u->owner=owner;u->row=row;u->record_node=(uint32_t)n;return 1;
}
static void commit(MotionUi *u){
 /* Never keep writing through a node pointer replaced by native Undo/load. */
 void *n=motion_ui_node(u->seq,0);if((uint32_t)n!=u->record_node)return;
 MotionNodeExtension *x=motion_store(u->seq,0);if(!x)return;
 for(unsigned i=0;i<4;i++){x->lanes[i]=u->take.lanes[0][i];x->gain[i]=u->gain[i];if(x->lanes[i].active)B(n,0x80e + i)=x->lanes[i].interpolation==MOTION_LINEAR;}
 motion_ui_publish(u->seq,u->owner,u->row);FN(0x0813130c,void(*)(void*))(MODEL);
}
static int thin(MotionLane *);
int motion_ui_capture(uint32_t lane,uint16_t value){
 MotionUi *u=motion_ui_state(0);uint64_t tick;
 if(!u||!u->take.record_held||lane>=4||!motion_ui_clock(u,u->owner,u->row,&tick))return 0;
 if((uint32_t)motion_ui_node(u->seq,0)!=u->record_node){motion_ui_end();return 0;}
 if(!u->take.lanes[0][lane].recording){
  if(u->mode==MOTION_OVERDUB&&!u->take.lanes[0][lane].active){motion_ui_import(u->seq,(void*)u->record_node,lane,u->take.lanes[0]+lane);if(u->take.lanes[0][lane].active)u->take.lanes[0][lane].origin_tick=u->launch_tick;}
  motion_set_length(u->take.lanes[0]+lane,(MotionBars)u->length);
  motion_set_mode(u->take.lanes[0]+lane,(MotionWriteMode)u->mode);
 }
 int result=motion_capture(&u->take,0,(uint8_t)lane,tick,value);
 if(result==MOTION_ERR_FULL&&thin(u->take.lanes[0]+lane)){result=motion_capture(&u->take,0,(uint8_t)lane,tick,value);u->error=5;}
 if(result!=MOTION_OK){u->error=result==MOTION_ERR_FULL?3:4;return 0;}
 commit(u);return 1;
}
void motion_ui_end(void){
 MotionUi *u=motion_ui_state(0);if(!u||!u->take.record_held)return;
 uint64_t tick=u->last_tick;motion_ui_clock(u,u->owner,u->row,&tick);
 motion_release_record(&u->take,tick);commit(u);u->record_node=0;
}
static void *find_node(void *object){
 if(!object)return 0;void *p=(void*)W(object,20);
 for(unsigned i=0;p&&i<64;i++,p=(void*)W(p,4))if(B(p,8)==5)return p;
 return 0;
}
static const char *const keys[4]={"playground_motion_v1_a","playground_motion_v1_b","playground_motion_v1_c","playground_motion_v1_d"};
static const char digits[]="0123456789ABCDEF";
void motion_ui_save(void *object,void *params){
 if(!params)return;MotionUi *u=motion_ui_state(0);if(!u)return;
 void *settings=FN(0x08109cdc,void*(*)(void*,const char*))(params,"playground_motion_settings_v1");if(settings)FN(0x0810958e,void(*)(void*,uint32_t))(settings,(uint32_t)u->length|((uint32_t)u->mode<<16));
 MotionNodeExtension *x=motion_store(W(object,0x10),0);if(!x)return;
 for(unsigned i=0;i<4;i++){
  int n=motion_encode(x->lanes+i,u->wire,sizeof(u->wire));if(n<0)continue;uint16_t gain=x->gain[i]?x->gain[i]:1;u->wire[26]=(uint8_t)gain;u->wire[27]=(uint8_t)(gain>>8);
  /* Saved phases start from the next launch, not a prior session's song tick. */
  for(unsigned j=16;j<24;j++)u->wire[j]=0;
  for(int j=0;j<n;j++){u->hex[j*2]=digits[u->wire[j]>>4];u->hex[j*2+1]=digits[u->wire[j]&15];}u->hex[n*2]=0;
  void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,keys[i]);
  if(a)FN(0x08109582,void(*)(void*,const char*))(a,u->hex);
 }
}
static int nibble(unsigned char c){if(c>='0'&&c<='9')return c-'0';if(c>='A'&&c<='F')return c-'A'+10;if(c>='a'&&c<='f')return c-'a'+10;return -1;}
void motion_ui_load(void *xml,void *root,void *object){
 if(!xml||!root||!object)return;
 void *params=FN(0x08109268,void*(*)(void*,const char*))(xml,"params");if(!params)return;
 MotionUi *u=0;MotionNodeExtension *x=0;
 void *settings=FN(0x08109c64,void*(*)(void*,const char*))(params,"playground_motion_settings_v1");uint32_t config=0;
 if(settings&&!FN(0x08109566,int(*)(void*,uint32_t*))(settings,&config)){uint32_t length=config&65535u,mode=config>>16;if(mode<=1&&(length==0||length==4||length==8||length==16||length==32||length==64)){u=motion_ui_state(1);if(u){u->length=(uint16_t)length;u->mode=(uint16_t)mode;}}}
 for(unsigned i=0;i<4;i++){
  void *a=FN(0x08109c64,void*(*)(void*,const char*))(params,keys[i]);if(!a)continue;
  const char *p=FN(0x081094c2,const char*(*)(void*))(a);if(!p)continue;
  if(!u)u=motion_ui_state(1);if(!u)return;
  unsigned n=0;int valid=1;
  while(*p){if(n>=sizeof(u->wire)||!p[1]){valid=0;break;}int hi=nibble(p[0]),lo=nibble(p[1]);if(hi<0||lo<0){valid=0;break;}u->wire[n++]=(uint8_t)(hi*16+lo);p+=2;}
  if(!valid||motion_decode(&u->decoded,u->wire,n)!=MOTION_OK||u->decoded.ticks_per_bar!=MOTION_DEFAULT_TICKS_PER_BAR)continue;
  /* Compact representation requires quantized positions and 2-bit flags. */
  for(unsigned j=0;j<u->decoded.count;j++)if(u->decoded.points[j].tick%MOTION_QUANTUM||u->decoded.points[j].flags>3)valid=0;
  if(!valid)continue;
  if(!x){x=motion_store(W(object,0x10),1);if(!x)return;for(unsigned k=0;k<4;k++){motion_lane_init(x->lanes+k,MOTION_DEFAULT_TICKS_PER_BAR);x->gain[k]=1;}motion_store_loaded(W(object,0x10));}
  u->decoded.origin_tick=0;x->lanes[i]=u->decoded;uint16_t gain=(uint16_t)(u->wire[26]|u->wire[27]<<8);x->gain[i]=gain?gain:1;
 }
}
void motion_ui_project_end(void){
 MotionUi *u=motion_ui_state(0);if(!u)return;u->take.record_held=0;u->record_node=0;u->record_latched=0;
 MotionDevice *d=(MotionDevice*)u->device;uint32_t serial=next_serial(d->serial);d->serial=serial|1;barrier();
 d->epoch++;if(!d->epoch)d->epoch=1;
 /* Keep allocated slots for reuse; invalidate their owners on project change.
  * Audio exclusively owns every runtime and cache line; never memset them. */
 for(unsigned i=0;i<d->count;i++){MotionDeviceClip *c=(MotionDeviceClip*)d->clips[i];c->owner=0;c->epoch=0;u->directory_seq[i]=0;}
 barrier();d->serial=serial;
}
/* Called after native project-load completion, before any recording gesture. */
__attribute__((used,retain)) void motion_ui_refresh_project(void){
 if(!motion_ui_state(0))return;motion_store_sweep();motion_ui_project_end();
 for(unsigned t=0;t<8;t++){
  uint32_t owner=0;if(!FN(0x08133960,int(*)(void*,uint32_t,uint32_t*))(MODEL,t,&owner)||!owner)continue;
  for(unsigned j=0;j<512;j++){
   uint32_t seq=0,row=16;if(!FN(0x0813391a,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&owner,j,&seq))break;
   if(FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&seq,0x73,&row)&&row<16)motion_ui_publish(seq,owner,row);
  }
 }
}
__attribute__((used,retain)) void motion_ui_rebuild(void *model,uint32_t *seq,uint32_t *owner){
 uint32_t row=16;if(model!=MODEL||!seq||!owner)return;
 if(FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,seq,0x73,&row)&&row<16)motion_ui_publish(*seq,*owner,row);
}
void motion_ui_import(uint32_t seq,void *node,unsigned which,MotionLane *l){
 if(!node||which>=4||!l||l->active||!B(node,0x80a+which))return;
 uint32_t count=256;FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&seq,0x62,&count);
 if(count>256)count=256;if(!count)return;
 l->count=0;l->interpolation=B(node,0x80e + which)?MOTION_LINEAR:MOTION_STEP;
 for(unsigned i=0;i<count;i++){
  int value=*(volatile int16_t*)((uint8_t*)node+10+which*512+i*2);if(value<-1000)value=-1000;if(value>1000)value=1000;
  uint16_t v=(uint16_t)((value+1000)/2);
  if(l->interpolation==MOTION_STEP&&l->count&&l->points[l->count-1].value==v)continue;
  l->points[l->count++]=(MotionPoint){i*MOTION_TICKS_PER_STEP,v,0};
 }
 l->active=l->count!=0;l->origin_tick=0;
}
static int thin(MotionLane *l){
 unsigned at=MOTION_EVENTS;uint64_t best=UINT64_MAX;uint32_t period=l->length_bars*l->ticks_per_bar;
 for(unsigned i=1;i+1<l->count;i++){
  MotionPoint *a=l->points+i-1,*b=a+1,*c=b+1;
  if(c->tick>=period)break; /* shortening never sacrifices hidden tail points */
  int64_t estimate=l->interpolation==MOTION_STEP?a->value:(int64_t)a->value+((int64_t)c->value-a->value)*(b->tick-a->tick)/(c->tick-a->tick);
  int64_t error=estimate-b->value;uint64_t score=(uint64_t)(error<0?-error:error);
  if(score<best){best=score;at=i;}
 }
 if(at==MOTION_EVENTS)return 0;
 for(unsigned i=at;i+1<l->count;i++)l->points[i]=l->points[i+1];l->count--;return 1;
}

/* Called after the native clear has taken its Undo snapshot and removed the
 * stock lane, so an extended lane cannot continue overriding the clear. */
__attribute__((used,retain)) void motion_ui_after_clear(void *model,uint32_t *seq,uint32_t which){
 if(model!=MODEL||!seq||which>=4)return;
 MotionUi *u=motion_ui_state(0);if(u&&u->take.record_held&&u->seq==*seq){motion_ui_end();u->record_latched=2;}
 MotionNodeExtension *x=motion_store(*seq,0);
 if(x){motion_clear_lane(x->lanes+which);x->gain[which]=1;}
 uint32_t owner=0,row=16;
 if(FN(0x08133d84,int(*)(void*,uint32_t*,uint32_t*,uint32_t*))(MODEL,seq,&owner,&row)&&row<16)motion_ui_publish(*seq,owner,row);
}

/* Source units match native A-D signed thousandths. Per-clip gain lets a
 * shallow existing route record a wider gesture without changing its depth
 * or affecting the same routing in other clips. */
int motion_ui_capture_source(uint32_t lane,int32_t source,int32_t initial){
 MotionUi *u=motion_ui_state(0);if(!u||lane>=4||!u->take.record_held)return 0;
 MotionLane *l=u->take.lanes[0]+lane;
 if(u->mode==MOTION_OVERDUB&&!l->active){motion_ui_import(u->seq,(void*)u->record_node,lane,l);if(l->active)l->origin_tick=u->launch_tick;}
 int64_t magnitude=source<0?-(int64_t)source:source,first=initial<0?-(int64_t)initial:initial;if(first>magnitude)magnitude=first;
 uint32_t needed=(uint32_t)((magnitude+999)/1000);if(!needed)needed=1;
 if(needed>65535){u->error=7;return 0;}
 uint32_t old=u->gain[lane]?u->gain[lane]:1;
 if(needed>old){
  for(unsigned j=0;j<l->count;j++)l->points[j].value=(uint16_t)(500+((int32_t)l->points[j].value-500)*(int64_t)old/needed);
  u->gain[lane]=(uint16_t)needed;
 }
 uint32_t gain=u->gain[lane];int seed=500+(int64_t)initial/(2*gain),v=500+(int64_t)source/(2*gain);
 if(seed<0)seed=0;if(seed>1000)seed=1000;if(v<0)v=0;if(v>1000)v=1000;
 if(!l->recording){
  uint64_t now=u->last_tick; /* motion_capture uses the original gesture clock for the seed */
  if(u->mode==MOTION_OVERDUB&&!l->active){motion_ui_import(u->seq,(void*)u->record_node,lane,l);if(l->active)l->origin_tick=u->launch_tick;}
  motion_set_length(l,(MotionBars)u->length);motion_set_mode(l,(MotionWriteMode)u->mode);
  motion_capture(&u->take,0,(uint8_t)lane,u->take.record_tick,(uint16_t)seed);u->last_tick=now;
 }
 return motion_ui_capture(lane,(uint16_t)v);
}

int motion_ui_native_source(MotionUi *u,unsigned lane,int32_t *value){
 if(!u||lane>=4||!value)return 0;MotionDevice *d=(MotionDevice*)u->device;
 for(unsigned i=0;i<8;i++){
  volatile MotionDeviceRuntime *r=d->runtime+i;uint32_t serial=r->serial;
  if(!serial||(serial&1)||r->owner!=u->owner||r->row!=u->row||r->epoch!=d->epoch)continue;
  int16_t source=((volatile int16_t*)r->reserved)[lane];barrier();if(serial==r->serial){*value=source;return 1;}
 }
 return 0;
}

__attribute__((used,retain)) void motion_ui_before_slide(void *model,uint32_t *seq,uint32_t which,uint32_t slide){
 if(model!=MODEL||!seq||which>=4)return;MotionNodeExtension *x=motion_store(*seq,0);
 if(x&&x->lanes[which].active&&x->lanes[which].interpolation!=(slide?MOTION_LINEAR:MOTION_STEP))FN(0x081338dc,void(*)(void*,uint32_t*))(MODEL,seq);
}
__attribute__((used,retain)) void motion_ui_after_slide(void *model,uint32_t *seq,uint32_t which,uint32_t slide){
 if(model!=MODEL||!seq||which>=4)return;MotionNodeExtension *x=motion_store(*seq,0);if(!x)return;
 x->lanes[which].interpolation=slide?MOTION_LINEAR:MOTION_STEP;uint32_t owner=0,row=16;
 if(FN(0x08133d84,int(*)(void*,uint32_t*,uint32_t*,uint32_t*))(MODEL,seq,&owner,&row)&&row<16)motion_ui_publish(*seq,owner,row);
}
