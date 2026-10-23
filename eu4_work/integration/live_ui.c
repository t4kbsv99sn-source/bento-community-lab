/* EU2 settings, native allocation and versioned per-track/clip-row XML. */
#include "live_ui.h"
static void clear(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static EuBank *bank(int create){
 if(EC->magic==EU_MAGIC&&EC->bytes==sizeof(EuBank)&&eu_memory(EC->pointer,sizeof(EuBank)))return (EuBank*)EC->pointer;
 if(!create)return 0;
 u32 p=W((void*)0x3000004c,0),end=W((void*)0x30000048,0),n=(sizeof(EuBank)+31)&~31u;
 if(!eu_memory(p,n)||end<p||end-p<n)return 0;
 u32 allocated=FN(0x08104c08,u32(*)(u32))(n);if(allocated!=p)return 0;
 clear((void*)p,n);EuBank *b=(EuBank*)p;b->epoch=1;b->serial=2;
 EC->magic=0;EC->pointer=p;EC->bytes=sizeof(EuBank);EC->epoch=1;__asm__ volatile("dmb" ::: "memory");EC->magic=EU_MAGIC;return b;
}
static EuRecord *record(EuRecord *r,u32 *count,u32 owner,u32 row,int create){
 for(u32 i=0;i<*count;i++)if(r[i].owner==owner&&r[i].row==row)return r+i;
 if(!create||*count>=EU_RECORDS||!owner||row>=16)return 0;
 EuRecord *out=r+(*count)++;clear(out,sizeof(*out));out->owner=owner;out->row=row;out->serial=2;return out;
}
static EuRecord *selected(Euclid *e,int create){
 EuBank *b=bank(create);u32 row=16;if(!b||e->pad>=16||!e->valid)return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&e->seq,0x73,&row)||row>=16)return 0;
 return record(b->records,&b->count,e->owner,row,create);
}
int live_begin(Euclid *e){return selected(e,1)!=0;}
EuPad live_value(Euclid *e){
 EuRecord *r=selected(e,0);EuPad p={0,0};if(r)p=r->pads[e->pad];
 if(!eu_pad_valid(p))p=eu_pack(e->steps,e->hits<=e->steps?e->hits:0,0,100,0);return p;
}
int live_edit(Euclid *e,u32 key,int value){
 if(key==0){e->pad=value<1?0:value>16?15:(u32)value-1;return 1;}
 if(key==6){e->preview=value<1?1:value>8?8:(u32)value;return 1;}
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);
 u32 n=eu_length(p),k=eu_pulses(p),rot=eu_rotation(p),vel=eu_base(p),on=eu_enabled(p);
 if(key==1){n=value<1?1:value>256?256:(u32)value;if(k>n)k=n;if(rot>=n)rot%=n;}
 if(key==2)k=value<0?0:(u32)value>n?n:(u32)value;
 if(key==3)rot=value<0?0:(u32)value>=n?n-1:(u32)value;
 if(key==4)vel=value<1?1:value>127?127:(u32)value;
 if(key==5)on=value>0;
 u32 serial=(r->serial+2)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->pads[e->pad]=eu_pack(n,k,rot,vel,on);r->pads[e->pad].velocity=eu_dynamics(vel,eu_mode(p),eu_depth(p));r->pads[e->pad].pattern|=p.pattern&(1u<<26);__asm__ volatile("dmb" ::: "memory");r->serial=serial;
 FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
static int read(void *p,const char *name,u32 *v){void *a=p?FN(0x08109c64,void*(*)(void*,const char*))(p,name):0;return a&&!FN(0x08109566,int(*)(void*,void*))(a,v);}
static void write(void *p,const char *name,u32 v){void *a=FN(0x08109cdc,void*(*)(void*,const char*))(p,name);if(a)FN(0x0810958e,void(*)(void*,u32))(a,v);}
static void name(char *s,u32 row,u32 pad,u32 word){const char *p="bento_eu2_00_00_0";u32 i=0;do{s[i]=p[i];}while(p[i++]);s[10]='0'+row/10;s[11]='0'+row%10;s[13]='0'+pad/10;s[14]='0'+pad%10;s[16]='0'+word;}
void live_save(void *object,void *params){
 EuBank *b=bank(0);if(!b||!object||!params)return;u32 owner=W(object,0x10);if(!owner||B(object,4)!=14)return;
 write(params,"bento_eu2_version",1);
 for(u32 i=0;i<b->count;i++){EuRecord *r=b->records+i;if(r->owner!=owner)continue;
  for(u32 pad=0;pad<16;pad++){EuPad p=r->pads[pad];if(!eu_pad_valid(p))continue;char key[20];name(key,r->row,pad,0);write(params,key,p.pattern);name(key,r->row,pad,1);write(params,key,eu_base(p));name(key,r->row,pad,2);write(params,key,eu_mode(p));name(key,r->row,pad,3);write(params,key,eu_depth(p));}
 }
}
void live_load(void *node,void *object){
 if(!node||!object||B(object,4)!=14||!W(object,0x10))return;
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");u32 ver=0;
 if(!read(params,"bento_eu2_version",&ver)||ver!=1)return;EuBank *b=bank(1);if(!b)return;
 u32 owner=W(object,0x10);
 for(u32 row=0;row<16;row++)for(u32 pad=0;pad<16;pad++){
  char key[20];EuPad p={0,0};name(key,row,pad,0);if(!read(params,key,&p.pattern))continue;name(key,row,pad,1);if(!read(params,key,&p.velocity)||!eu_pad_valid(p))continue;
  u32 mode=0,depth=0;name(key,row,pad,2);read(params,key,&mode);name(key,row,pad,3);read(params,key,&depth);if(mode>9)mode=0;if(depth>100)depth=0;p.velocity=eu_dynamics(eu_base(p),mode,depth);
  EuRecord *r=record(b->pending,&b->pending_count,owner,row,1);if(r)r->pads[pad]=p;
 }
}
void live_finish(void){
 EuBank *b=bank(0);if(!b)return;
 b->serial|=1;__asm__ volatile("dmb" ::: "memory");clear(b->records,sizeof(b->records));b->count=b->pending_count;
 for(u32 i=0;i<b->count;i++)b->records[i]=b->pending[i];clear(b->pending,sizeof(b->pending));b->pending_count=0;
 b->epoch++;if(!b->epoch)b->epoch=1;__asm__ volatile("dmb" ::: "memory");b->serial=(b->serial+1)&~1u;if(!b->serial)b->serial=2;
}

int live_position(Euclid *e,u32 *step){
 EuBank *b=bank(0);u32 row=16;if(!b||!e->valid||!step)return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&e->seq,0x73,&row)||row>=16)return 0;
 for(u32 i=0;i<16;i++){
  volatile EuRuntime *r=b->runtime+i;
  u32 serial=r->reserved[3],epoch=r->epoch,owner=r->owner,rr=r->row;
  if(!serial||(serial&1)||epoch!=b->epoch||owner!=e->owner||rr!=row)continue;
  u32 value=r->reserved[1],valid=r->reserved[2];__asm__ volatile("dmb" ::: "memory");
  if(serial==r->reserved[3]&&valid){*step=value;return 1;}
 }
 return 0;
}

/* UI generation commits native notes before publishing the playback mode.
   On failure, the existing pattern/settings remain active. */
int live_generate(Euclid *e,u32 key,int value){
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);
 if(key==5&&value==0)return live_edit(e,5,0);
 if(key==5&&eu_native(p))return live_edit(e,5,1);
 Euclid next=*e;next.steps=eu_length(p);next.hits=eu_pulses(p);next.rotate=eu_rotation(p);next.velocity=100;
 if(key==1){next.steps=value<1?1:value>256?256:(u32)value;if(next.hits>next.steps)next.hits=next.steps;if(next.rotate>=next.steps)next.rotate%=next.steps;}
 if(key==2)next.hits=value<0?0:(u32)value>next.steps?next.steps:(u32)value;
 if(key==3)next.rotate=value<0?0:(u32)value>=next.steps?next.steps-1:(u32)value;
 if(key==4)next.velocity=value<1?1:value>127?127:(u32)value;
 int status=key==4&&eu_native(p)?eu_velocity(&next,MODEL):eu_apply(&next,MODEL);
 e->scratch=next.scratch;e->status=status;if(status!=EU_OK&&status!=EU_SAME)return 0;
 u32 serial=(r->serial+2)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->pads[e->pad]=eu_pack(next.steps,next.hits,next.rotate,next.velocity,1);r->pads[e->pad].pattern|=1u<<26;r->pads[e->pad].velocity=eu_dynamics(next.velocity,eu_mode(p),eu_depth(p));
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}

int live_dynamic(Euclid *e,u32 key,int value){
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);u32 mode=eu_mode(p),depth=eu_depth(p);
 if(key==4)mode=value<0?0:value>9?9:(u32)value;else if(key==6)depth=value<0?0:value>100?100:(u32)value;else return 0;
 u32 serial=(r->serial+2u)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");p.velocity=eu_dynamics(100,mode,depth);r->pads[e->pad]=p;__asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
