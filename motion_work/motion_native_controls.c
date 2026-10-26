#include "motion_native_ui.h"
#include "../eu4_work/integration/live_shared.h"
#define API __attribute__((used,retain))
static const uint16_t bars[6]={0,4,8,16,32,64};
static const char *const bar_names[6]={"Auto","4 bars","8 bars","16 bars","32 bars","64 bars"};
static const char *const mode_names[2]={"Overdub","Replace"};
static const char *const page_names[4]={"1-16","17-32","33-48","49-64"};
static const char *const titles[4]={"Length","Rec Length","Write","Bars"};
static int index_of(uint16_t b){for(int i=0;i<6;i++)if(bars[i]==b)return i;return 3;}
static int automation(void *v){return v&&B(MODEL,0x12c)==0x17&&B(v,0x125dac)==2&&H(v,0x11bcc0)!=0x190&&H(v,0x11bcc0)!=0x196;}
static MotionLane *lane(void *v,int create){
 unsigned i=W(v,0x125d34);if(i>=4)return 0;
 if(create)motion_ui_node(W(v,0x11cd00),1);MotionNodeExtension *x=motion_store(W(v,0x11cd00),create);return x?x->lanes+i:0;
}
static void changed(void *v){
 uint32_t row=16,seq=W(v,0x11cd00),owner=W(v,0x11cd08);
 FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&seq,0x73,&row);
 motion_ui_publish(seq,owner,row);FN(0x0813130c,void(*)(void*))(MODEL);
}
API void motion_controls_restore(void){
 MotionUi *u=motion_ui_state(0);if(!u||!u->descriptors_saved)return;
 uint32_t r=W((void*)0x30031484,0);if(r)for(unsigned i=0;i<32;i++)W((void*)r,0x190*32+i*4)=u->descriptors[i];
 u->descriptors_saved=0;
}
API void motion_controls_before_header(void *v){motion_controls_restore();MotionUi *u=motion_ui_state(0);if(u)u->view=(uint32_t)v;}
API void motion_controls_after_header(void *v){
 if(!automation(v))return;MotionUi *u=motion_ui_state(1);if(!u)return;
 MotionLane *l=lane(v,0);uint32_t length=l?l->length_bars:16,pages=(length+15)/16;if(u->page>=pages)u->page=0;
 uint32_t r=W((void*)0x30031484,0);if(!r)return;
 for(unsigned i=0;i<32;i++)u->descriptors[i]=W((void*)r,0x190*32+i*4);u->descriptors_saved=1;
 uint32_t values[4]={(uint32_t)index_of(length)-1,(uint32_t)index_of(u->length),u->mode,u->page};
 const char *const *names[4]={bar_names+1,bar_names,mode_names,page_names};uint32_t counts[4]={5,6,2,pages};
 for(unsigned i=0;i<4;i++){
  unsigned key=0x190+i,slot=2+i; /* P24: native slots 0,1,6,7 (1DD 1DE . . . . 1DB 1DC) stay */void *d=(void*)(r+key*32);
  for(unsigned j=0;j<32;j++)B(d,j)=0;H(d,0)=key;B(d,2)=7;W(d,4)=(uint32_t)titles[i];W(d,8)=(uint32_t)names[i];W(d,12)=counts[i];W(d,20)=counts[i]-1;
  void *bar=(uint8_t*)v+0x55f0,*widget=(uint8_t*)bar+0x38+slot*0x468;
  H(v,0x11bcc0+slot*2)=key;W(v,0x11bcd0+slot*4)=values[i];W(v,0x11bca0+slot*4)=W(v,0x11cd00);
  FN(0x08170656,void(*)(void*,uint32_t,const char*))(bar,slot,0);
  FN(0x08171c1c,void(*)(void*,uint32_t,int,uint32_t))(widget,key,values[i],1);
  FN(0x0817e85e,void(*)(void*,const char*))((uint8_t*)widget+0x3c8,titles[i]);
 }
}
API int motion_controls_event(void *v,void *event){
 if(!automation(v)||H(event,0)!=0xcf)return 0;
 uint32_t key=W(event,8),value=W(event,12);if(key<0x190||key>0x193)return 0;
 MotionUi *u=motion_ui_state(1);if(!u)return 1;if(u->take.record_held)return 1;
 if(key==0x190){
  if(value>4)return 1;uint32_t seq=W(v,0x11cd00);FN(0x081338dc,void(*)(void*,uint32_t*))(MODEL,&seq);
  MotionLane *l=lane(v,1);if(l){motion_ui_import(seq,motion_ui_node(seq,0),W(v,0x125d34),l);motion_set_length(l,(MotionBars)bars[value+1]);}changed(v);
 }else if(key==0x191){if(value<=5)u->length=bars[value];}
 else if(key==0x192){if(value<=1)u->mode=(uint16_t)value;}
 else {MotionLane *l=lane(v,0);unsigned pages=((l?l->length_bars:16)+15)/16;if(value<pages)u->page=value;}
 FN(0x081579b0,void(*)(void*))(v);FN(0x081599bc,void(*)(void*))(v);return 1;
}
API int motion_controls_get(void *model,uint32_t *handle,uint32_t key,void *out,uint32_t caller){
 MotionUi *u=motion_ui_state(0);if(!u||model!=MODEL||!handle||!out)return 0;
 void *v=(void*)u->view;caller&=~1u;
 if(automation(v)&&*handle==W(v,0x11cd00)){
  MotionLane *shown=lane(v,0); /* P24: without motion the editor keeps the native clip length */
  if(shown&&shown->active){
   if(key==0x62&&caller==0x08159a1a){unsigned n=shown->length_bars*16;W(out,0)=n>256?256:n;return 1;}
   if(key==0x60&&caller==0x08159a0c){W(out,0)=10;return 1;}
  }
 }
 if(u->settings&&B(MODEL,0x12c)==0x1a&&(key==0x190||key==0x191)){W(out,0)=key==0x190?(uint32_t)index_of(u->length):u->mode;return 1;}
 if(u->take.record_held&&!u->read_base)for(unsigned i=0;i<u->target_count;i++){
  MotionTarget *t=u->targets+i;if(t->handle==*handle&&t->key==key){W(out,0)=(uint32_t)t->current;return 1;}
 }
 return 0;
}
API int motion_controls_graph(void *v){
 if(!automation(v))return 0;MotionLane *l=lane(v,0);if(!l||!l->active)return 0;
 MotionUi *u=motion_ui_state(0);uint64_t start=l->origin_tick+(uint64_t)(u?u->page:0)*16*MOTION_DEFAULT_TICKS_PER_BAR;
 for(unsigned i=0;i<256;i++){
  uint16_t value=500;if((u?u->page:0)*256+i<l->length_bars*16)motion_evaluate(l,start+i*MOTION_TICKS_PER_STEP,&value);
  FN(0x08174ffc,void(*)(void*,uint32_t,int))((uint8_t*)v+0x38,i,(int)value*2-1000);
 }
 return 1;
}
API int motion_controls_set(void *model,uint32_t *seq,uint32_t which,uint32_t step,int value,uint32_t snapshot){
 MotionUi *u=motion_ui_state(0);if(!u||model!=MODEL||!seq||which>=4||step>=256)return 0;
 void *v=(void*)u->view;if(!automation(v)||W(v,0x11cd00)!=*seq)return 0;
 MotionNodeExtension *x=motion_store(*seq,0);if(!x||!x->lanes[which].active)return 0;
 if(u->take.record_held)return 1;
 if(snapshot)FN(0x081338dc,void(*)(void*,uint32_t*))(MODEL,seq);
 x=motion_store(*seq,0);if(!x)return 1;
 MotionLane *l=x->lanes+which;uint32_t tick=(u->page*256+step)*MOTION_TICKS_PER_STEP;
 if(tick>=l->max_tick)return 1;
 if(value<-1000)value=-1000;if(value>1000)value=1000;
 unsigned i=0;while(i<l->count&&l->points[i].tick<tick)i++;
 if(i==l->count||l->points[i].tick!=tick){
  if(l->count==MOTION_EVENTS){u->error=3;return 1;}
  for(unsigned j=l->count;j>i;j--)l->points[j]=l->points[j-1];l->count++;
 }
 l->points[i]=(MotionPoint){tick,(uint16_t)((value+1000)/2),0};changed(v);return 1;
}
static int selected_clip(MotionUi *u,uint32_t *seq,uint32_t *owner,uint32_t *row){
 if(!FN(0x08133cfc,int(*)(void*,uint32_t*))(MODEL,owner))return 0;
 MotionDevice *d=(MotionDevice*)u->device;*row=16;
 for(unsigned i=0;i<8;i++){
  volatile MotionDeviceRuntime *r=d->runtime+i;uint32_t s=r->serial;
  if(!s||(s&1)||r->epoch!=d->epoch||r->owner!=*owner||!r->valid)continue;
  uint32_t rr=r->row;__asm__ volatile("dmb" ::: "memory");if(s==r->serial){*row=rr;break;}
 }
 if(*row>=16)return 0;
 for(unsigned i=0;i<512;i++){
  uint32_t rr=16;if(!FN(0x0813391a,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,owner,i,seq))break;
  if(FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,seq,0x73,&rr)&&rr==*row)return 1;
 }
 return 0;
}
static void try_begin(MotionUi *u){
 if(u&&u->record_latched==1&&!u->take.record_held){uint32_t seq,owner,row;if(selected_clip(u,&seq,&owner,&row))motion_ui_begin(seq,owner,row);}
}
API int motion_controls_dispatch(void *model,uint32_t code,uint32_t context,uint32_t index){
 (void)context;if(model!=MODEL)return 0;
 MotionUi *u=motion_ui_state((code==0xaf&&(index==7||index==14)));if(!u)return 0;
 if(index==7){if(code==0xaf)u->project_hold=1;if(code==0xb0)u->project_hold=0;}
 if(index==14&&code==0xaf){
  if(!u->record_latched&&(u->project_hold||W((void*)0x24048d60,8))){u->record_latched=1;u->error=0;}
  else if(!u->record_latched)return 0;
 }else if(index==14&&code==0xb0&&u->record_latched){motion_ui_end();u->record_latched=0;u->virtual_handle=0;return 1;}
 try_begin(u);
 if(u->take.record_held){uint32_t owner=0;uint64_t tick;if(!FN(0x08133cfc,int(*)(void*,uint32_t*))(MODEL,&owner)||owner!=u->owner||!motion_ui_clock(u,u->owner,u->row,&tick)||tick<u->take.record_tick){motion_ui_end();u->record_latched=2;}}
 return index==14&&code==0xaf&&u->record_latched;
}
/* Enumerate all existing native routes on this track before allocating a
 * source. A lane used by another destination is never considered free. */
static unsigned used_sources(MotionUi *u){
 uint32_t *queue=(uint32_t*)u->wire;unsigned count=1,at=0,mask=0;queue[0]=u->owner;
 while(at<count){
  uint32_t handle=queue[at++];
  for(unsigned j=0;j<512;j++){uint32_t route[3]={0};if(!FN(0x08131238,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&handle,j,route))break;unsigned src=route[1]&65535u;if(src>=9&&src<=12)mask|=1u<<(src-9);}
  for(unsigned j=0;j<512;j++){
   uint32_t child=0;if(!FN(0x0813391a,int(*)(void*,uint32_t*,uint32_t,uint32_t*))(MODEL,&handle,j,&child))break;
   if(!child)continue;unsigned k=0;while(k<count&&queue[k]!=child)k++;if(k<count)continue;
   if(count==256)return 15;queue[count++]=child;
  }
 }
 for(unsigned i=0;i<4;i++)if(u->take.lanes[0][i].active||B((void*)u->record_node,0x80a+i))mask|=1u<<i;
 return mask;
}
static int destination(uint32_t handle,uint32_t key){
 uint32_t type=FN(0x08133f7c,uint32_t(*)(void*,uint32_t*))(MODEL,&handle);
 for(unsigned i=0;i<60;i++){const uint32_t *d=(const uint32_t*)(0x0819de54u+i*24);if(d[0]==type&&d[2]==key)return 1;}
 if(type==1){const uint16_t keys[]={2,3,4,0x1e,0x1f,0x21,0x4c,0x4b,0x32,0x33,0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9,0x1b0};for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++)if(key==keys[i])return 1;}
 return 0;
}
API int motion_controls_model_event(void *model,void *event){
 if(model==MODEL&&H(event,0)==0x1070u&&B(MODEL,0x12c)==0x17){MotionUi *state=motion_ui_state(1);if(!state)return 1;state->settings=1;state->settings_opening=1;FN(0x081420ec,void(*)(void*,uint32_t,uint32_t,uint32_t,uint32_t))(MODEL,0x1a,0,0,1);state->settings_opening=0;return 1;}
 MotionUi *u=motion_ui_state(0);if(u&&model==MODEL&&H(event,0)==0xcf)try_begin(u);
 if(!u||!u->take.record_held||model!=MODEL||H(event,0)!=0xcf)return 0;
 uint32_t handle=W(event,4),key=W(event,8);if(!handle||key>=499)return 0;
 uint32_t registry=W((void*)0x30031484,0);if(!registry)return 0;
 int lo=(int)W((void*)registry,key*32+16),hi=(int)W((void*)registry,key*32+20),value=(int)W(event,12);
 if(hi<=lo)return 0;if(value<lo)value=lo;if(value>hi)value=hi;
 MotionTarget *target=0;for(unsigned i=0;i<u->target_count;i++)if(u->targets[i].handle==handle&&u->targets[i].key==key){target=u->targets+i;break;}
 if(!target){
  int amounts[4]={0},free_slot=-1;
  for(unsigned slot=0;slot<3;slot++){
   uint32_t route[3]={0};if(!FN(0x08131244,int(*)(void*,uint32_t*,uint32_t,uint32_t,uint32_t*))(MODEL,&handle,key,slot,route)){if(free_slot<0)free_slot=(int)slot;continue;}
   unsigned src=route[1]&65535u;if(src>=9&&src<=12)amounts[src-9]+=(int32_t)route[0];
  }
  unsigned lane=0;while(lane<4&&!amounts[lane])lane++;
  int base=0;u->read_base=1;int got=FN(0x08133614,int(*)(void*,uint32_t*,uint32_t,int*))(MODEL,&handle,key,&base);u->read_base=0;if(!got)return 0;
  if(lane==4){
   if(!destination(handle,key))return 0;
   unsigned mask=used_sources(u);lane=0;while(lane<4&&(mask&(1u<<lane)))lane++;
   if(lane==4||free_slot<0){u->error=6;return 0;}
   uint32_t route[5]={0xd1,handle,key|1u<<16,(lane+9)|((uint32_t)free_slot<<16),1000};
   FN(0x081403ec,int(*)(void*,void*))(MODEL,route);
   uint32_t check[3]={0};if(!FN(0x08131244,int(*)(void*,uint32_t*,uint32_t,uint32_t,uint32_t*))(MODEL,&handle,key,(uint32_t)free_slot,check)||(check[1]&65535u)!=lane+9){u->error=6;return 0;}
   amounts[lane]=(int32_t)check[0];if(!amounts[lane]){u->error=6;return 0;}
  }
  if(u->target_count==64){u->error=6;return 0;}
  MotionLane *l=u->take.lanes[0]+lane;int native_existing=!l->active&&B((void*)u->record_node,0x80a+lane);
  if(!l->active&&u->mode==MOTION_OVERDUB){motion_ui_import(u->seq,(void*)u->record_node,lane,l);if(l->active)l->origin_tick=u->launch_tick;}
  uint64_t tick;if(!motion_ui_clock(u,u->owner,u->row,&tick))return 0;uint16_t previous=500;motion_evaluate(l,tick,&previous);
  target=u->targets+u->target_count++;target->handle=handle;target->key=key;target->base=base;target->current=base;target->lane=(uint8_t)lane;target->amount=amounts[lane];target->source=((int32_t)previous*2-1000)*u->gain[lane];if(native_existing)motion_ui_native_source(u,lane,&target->source);
 }
 int64_t source=(int64_t)target->source+((int64_t)value-target->base)*1000/target->amount;
 if(source<INT32_MIN||source>INT32_MAX){u->error=7;return 1;}
 if(motion_ui_capture_source(target->lane,(int32_t)source,target->source))target->current=value;
 return 1;
}
static void settings_menu_add(void);
API void motion_controls_counter(void *out){
 settings_menu_add();MotionUi *u=motion_ui_state(0);if(!u||!out||!u->record_latched)return;
 try_begin(u);
 if(!u->take.record_held){if(u->record_latched==1){const char *w="REC WAIT";char *q=(char*)out+0x196;unsigned k=0;while(w[k]){q[k]=w[k];k++;}q[k]=0;}return;}
 uint64_t tick;if(!motion_ui_clock(u,u->owner,u->row,&tick))return;
 uint64_t elapsed=tick>=u->take.record_tick?tick-u->take.record_tick:0;unsigned bar=(unsigned)(elapsed/MOTION_DEFAULT_TICKS_PER_BAR)+1;
 char *p=(char*)out+0x196;const char *label=u->error==6?"NO LANE ":u->error==7?"RANGE ":u->error==3?"FULL ":"REC ";unsigned n=0;while(label[n]){p[n]=label[n];n++;}
 if(bar>999)bar=999;if(bar>=100)p[n++]='0'+bar/100;if(bar>=10)p[n++]='0'+bar/10%10;p[n++]='0'+bar%10;p[n]=0;
}
#define MOTION_SETTINGS_ACTION 0x1070u
API void motion_settings_menu_remove(void){
 for(unsigned m=0;m<20;m++){uint8_t *menu=(uint8_t*)0x30030168u+m*0xe0;if(W(menu,0)!=0xf9u)continue;unsigned n=B(menu,0xcc);if(n>9)continue;
  for(unsigned i=0;i<n;i++)if(W(menu,4+i*20)==MOTION_SETTINGS_ACTION){for(unsigned j=i;j+1<n;j++)for(unsigned k=0;k<5;k++)W(menu,4+j*20+k*4)=W(menu,4+(j+1)*20+k*4);B(menu,0xcc)=--n;break;}
 }
}
static void settings_menu_add(void){
 if(B(MODEL,0x12c)!=0x17)return;
 for(unsigned m=0;m<20;m++){uint8_t *menu=(uint8_t*)0x30030168u+m*0xe0;if(W(menu,0)!=0xf9u)continue;unsigned n=B(menu,0xcc);if(n>=9)continue;unsigned i=0;for(;i<n;i++)if(W(menu,4+i*20)==MOTION_SETTINGS_ACTION)break;if(i<n)continue;
  void *cell=menu+4+n*20;for(unsigned k=0;k<5;k++)W(cell,k*4)=0;W(cell,0)=MOTION_SETTINGS_ACTION;W(cell,4)=(uint32_t)"Motion Settings";W(cell,16)=1;B(menu,0xcc)=n+1;
 }
}
API void motion_controls_nav(void *model,uint32_t page){
 (void)model;motion_controls_restore();MotionUi *u=motion_ui_state(0);if(!u)return;
 if(!u->settings_opening)u->settings=0;
 (void)page;
}
API int motion_settings_header(void *model,void *handle,void *out,uint32_t mode,uint32_t caller){
 (void)handle;(void)mode;MotionUi *u=motion_ui_state(0);
 if(model!=MODEL||!u||!u->settings||!out||(caller&~1u)!=0x08145f22u)return 0;
 motion_controls_restore();uint32_t r=W((void*)0x30031484,0);if(!r)return 0;
 for(unsigned i=0;i<32;i++)u->descriptors[i]=W((void*)r,0x190*32+i*4);u->descriptors_saved=1;
 const char *const *names[2]={bar_names,mode_names};const char *labels[2]={"Length","Mode"};unsigned counts[2]={6,2};
 for(unsigned i=0;i<2;i++){void *d=(void*)(r+(0x190+i)*32);for(unsigned j=0;j<32;j++)B(d,j)=0;H(d,0)=0x190+i;B(d,2)=7;W(d,4)=(uint32_t)labels[i];W(d,8)=(uint32_t)names[i];W(d,12)=counts[i];W(d,20)=counts[i]-1;}
 for(unsigned j=0;j<0x54;j++)B(out,j)=0;B(out,0)=1;W(out,4)=(uint32_t)"Motion Recording";H(out,0x14)=0x190;H(out,0x16)=0x191;return 1;
}
API int motion_settings_event(void *view,void *event){
 MotionUi *u=motion_ui_state(0);if(!u||!u->settings||B(MODEL,0x12c)!=0x1a||H(event,0)!=0xcf)return 0;
 uint32_t key=W(event,8),value=W(event,12);if(key==0x190){if(value<6)u->length=bars[value];}else if(key==0x191){if(value<2)u->mode=(uint16_t)value;}else return 0;
 FN(0x08145cf4,void(*)(void*))(view);FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
API int motion_controls_bulk(void *model,uint32_t *seq,uint32_t lane_index,uint32_t count,int delta,uint32_t snapshot){
 MotionUi *u=motion_ui_state(0);if(!u||model!=MODEL||!seq||lane_index>=4||!automation((void*)u->view)||W((void*)u->view,0x11cd00)!=*seq)return 0;
 MotionNodeExtension *x=motion_store(*seq,0);if(!x||!x->lanes[lane_index].active)return 0;
 if(u->take.record_held||!count)return 1;if(count>256)count=256;
 if(snapshot)FN(0x081338dc,void(*)(void*,uint32_t*))(MODEL,seq);
 x=motion_store(*seq,0);if(!x)return 1;MotionLane *l=x->lanes+lane_index;
 if(u->bulk_seq!=*seq){u->bulk_seq=*seq;for(unsigned i=0;i<4;i++)u->bulk_remainder[i]=0;}
 int adjusted=delta+u->bulk_remainder[lane_index];u->bulk_remainder[lane_index]=(int16_t)(adjusted%2);adjusted/=2;
 uint32_t start=u->page*256*MOTION_TICKS_PER_STEP,end=start+count*MOTION_TICKS_PER_STEP;
 for(unsigned i=0;i<l->count;i++)if(l->points[i].tick>=start&&l->points[i].tick<end){int value=(int)l->points[i].value+adjusted;if(value<0)value=0;if(value>1000)value=1000;l->points[i].value=(uint16_t)value;}
 changed((void*)u->view);return 1;
}

/* P26 (owner: "red little button in the upper left corner"). Drawn after the
 * root header's own paint (30034D48, class vtable 081B3680 slot 1 = 0817F8F0;
 * the display calls it, then paints the children with 0816F9E8 directly),
 * in the free top-left area of the header: filled red while motion
 * records, red outline while armed and waiting for the playing clip. Header
 * coordinates are logical (0..1280 x 0..56); CLUT 4 = rec red (AL44 0xF4),
 * 0 = header background. Position checked in the display emulator. */
#define HEADER_ROOT 0x30034d48u
#define FILL(r,c,s) FN(0x08166ef6,void(*)(const int*,uint32_t,uint32_t))(r,c,s)
#define OUTLINE(r,c,s) FN(0x08166e9e,void(*)(const int*,uint32_t,uint32_t))(r,c,s)
API void motion_header_draw(void *w,void *ctx){
 FN(0x0817f8f0,void(*)(void*,void*))(w,ctx);
 if((uint32_t)w!=HEADER_ROOT||!ctx)return;uint32_t surface=W(ctx,4);if(!surface)return;
 MotionUi *u=motion_ui_state(0);uint32_t want=!u?0:u->take.record_held?2:u->record_latched==1?1:0;
 const int r[4]={164,15,26,26},in[4]={166,17,22,22};
 if(want==2)FILL(r,0xf4u,surface);
 else if(want==1){FILL(r,0x00u,surface);OUTLINE(r,0xf4u,surface);OUTLINE(in,0xf4u,surface);}
 else if(u&&u->indicator)FILL(r,0x00u,surface); /* header background is 0 (transparent over the black LTDC background) */
 if(u)u->indicator=want;
}
