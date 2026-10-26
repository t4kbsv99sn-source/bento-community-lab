/* M7-only native automation adapter. No M4/UI calls and no allocation.
 * Hook target is the call to native 08061040 at 08062216, after native timed
 * note rendering. Its second argument is an i64 native song-position value,
 * not the larger clock object accepted by 080A21C0.
 *
 * Source objects at sequence+871C and +873C are constructed by 08062A80;
 * 08061040 computes raw A-D at +8720+8*n and native smoothed A-D at
 * +8740+8*n. The native automation provider consumes these source objects.
 * Only enabled, validated motion lanes overwrite them. Ordinary A-D remains
 * native. An unbound/unpublished bank is a complete pass-through.
 */
#include "motion_device_shared.h"
#include "motion_p19_adapter.h"
#define W(p,o) (*(volatile uint32_t*)((uint8_t*)(p)+(o)))
#define B(p,o) (*(volatile uint8_t*)((uint8_t*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define EU_CONTROL 0x24041fc0u
#define EU_MAGIC 0x324c5545u
#define EU_BYTES 45920u
#define TRANSPORT_STATE 0x24041980u
/* Meta at 240416C0 occupies 688 bytes in P19. Its pre-reserved 832-byte
 * M7 block leaves the aligned final four lines free. This owns exactly one
 * line at +2C0; existing startup zeros that line. M4 never writes it. */
#define TRANSPORT_MAGIC 0x31524d50u
static void invalidate(uint32_t p,uint32_t bytes){
 __asm__ volatile("dsb" ::: "memory");
 if(W((void*)0xe000ed14u,0)&(1u<<16)){
  uint32_t end=(p+bytes+31u)&~31u;p&=~31u;
  for(;p<end;p+=32)W((void*)0xe000ef5cu,0)=p;
 }
 __asm__ volatile("dsb" ::: "memory");
}
static void clean(uint32_t p,uint32_t bytes){
 __asm__ volatile("dsb" ::: "memory");
 if(W((void*)0xe000ed14u,0)&(1u<<16)){
  uint32_t end=(p+bytes+31u)&~31u;p&=~31u;
  for(;p<end;p+=32)W((void*)0xe000ef68u,0)=p;
 }
 __asm__ volatile("dsb" ::: "memory");
}
static int memory(uint32_t p,uint32_t n){
 return !(p&31u)&&p>=0xc0000000u&&p<=0xc8000000u-n;
}
static MotionDevice *device(void){
 volatile uint32_t *ec=(volatile uint32_t*)EU_CONTROL;
 invalidate(EU_CONTROL,32);
 if(ec[0]!=EU_MAGIC||ec[2]!=EU_BYTES||!memory(ec[1],EU_BYTES))return 0;
 invalidate(ec[1],32);uint32_t p=W((void*)ec[1],MOTION_DEVICE_EU_POINTER_WORD*4);
 if(!memory(p,sizeof(MotionDevice)))return 0;
 invalidate(p,32);MotionDevice *d=(MotionDevice*)p;
 if(d->magic!=MOTION_DEVICE_MAGIC||d->bytes!=sizeof(*d)||d->count>MOTION_DEVICE_CLIPS||(d->serial&1u))return 0;
 return d;
}
static MotionDeviceRuntime *runtime(MotionDevice *d,void *s){
 MotionDeviceRuntime *free=0;
 for(unsigned i=0;i<MOTION_DEVICE_TRACKS;i++){
  MotionDeviceRuntime *r=d->runtime+i;
  if(r->sequence==(uint32_t)s)return r;
  if((!r->sequence||r->epoch!=d->epoch)&&!free)free=r;
 }
 return free;
}
static uint32_t rowof(void *s){
 uint32_t p=W(s,0x86c0),first=(uint32_t)s+0x240u;
 if(p<first||p>=first+16u*0x848u||(p-first)%0x848u)return 16;
 return (p-first)/0x848u;
}
static MotionDeviceClip *find(MotionDevice *d,uint32_t owner,uint32_t row){
 uint32_t serial=d->serial,count=d->count,epoch=d->epoch;
 invalidate((uint32_t)d->clips,sizeof(d->clips));
 for(unsigned i=0;i<count;i++){
  uint32_t p=d->clips[i];if(!memory(p,sizeof(MotionDeviceClip)))continue;
  invalidate(p,32);MotionDeviceClip *c=(MotionDeviceClip*)p;
  if(c->owner==owner&&c->row==row&&c->epoch==epoch){
   invalidate((uint32_t)d,32);
   if(d->serial==serial&&d->epoch==epoch&&!(serial&1u))return c;
   return 0;
  }
 }
 return 0;
}
static int snapshot(MotionDeviceRuntime *r,MotionDeviceClip *c){
 invalidate((uint32_t)c,sizeof(*c));uint32_t serial=c->serial;
 if(!serial||(serial&1u))return r->clip_pointer==(uint32_t)c&&r->clip_serial!=0;
 if(r->clip_pointer==(uint32_t)c&&r->clip_serial==serial)return 1;
 /* Validate every lane before changing the last accepted cache. No computed
  * float or unchecked count may reach the native modulation source objects. */
 for(unsigned i=0;i<MOTION_LANES;i++){
  const MotionCompactLane *l=c->lanes+i;
  uint16_t value;
  if(l->count>MOTION_EVENTS||l->interpolation>MOTION_LINEAR||l->ticks_per_bar!=MOTION_DEFAULT_TICKS_PER_BAR)return 0;
  for(unsigned j=0;j<l->count;j++){
   uint32_t word=l->ticks[j],t=word&0xfffffu;
   if(((word>>20)&1023u)>1000u||(j&&t<=(l->ticks[j-1]&0xfffffu)))return 0;
  }
  if(l->active&&(!l->count||!l->ticks_per_bar||
      !(l->length_bars==4||l->length_bars==8||l->length_bars==16||l->length_bars==32||l->length_bars==64)||
      !motion_compact_evaluate(l,l->origin_tick,&value)||value>1000))return 0;
 }
 /* Never overwrite the accepted cache while copying a potentially changing
  * M4 snapshot. A rejected copy keeps the previous complete audible state. */
 unsigned pending=(r->active_cache^1u)&1u;
 for(unsigned i=0;i<MOTION_LANES;i++)r->lanes[pending][i]=c->lanes[i];
 __asm__ volatile("dmb" ::: "memory");invalidate((uint32_t)c,32);
 if(c->serial!=serial)return r->clip_pointer==(uint32_t)c&&r->clip_serial!=0;
 r->active_cache=pending;r->clip_pointer=(uint32_t)c;r->clip_serial=serial;return 1;
}
__attribute__((used,retain)) void motion_native_automation(void *s,const int64_t *now){
 FN(0x08061040u,void(*)(void*,const int64_t*))(s,now);
 if(!s||!now||*now<0||(uint64_t)*now>UINT64_MAX/MOTION_P19_CLOCK_SCALE)return;
 MotionDevice *d=device();if(!d)return;
 uint32_t row=rowof(s),owner=W(s,12);if(row>=16||!owner)return;
 MotionDeviceRuntime *r=runtime(d,s);if(!r)return;
 uint32_t serial=(r->serial+2u)&~1u;if(!serial)serial=2;
 r->serial=serial|1u;__asm__ volatile("dmb" ::: "memory");
 uint64_t tick=(uint64_t)*now;
 if(r->sequence!=(uint32_t)s||r->owner!=owner||r->row!=row||r->epoch!=d->epoch||r->restart||tick<r->native_tick){
  int first=r->sequence!=(uint32_t)s;
  int64_t clip_origin=*(const int64_t*)((const uint8_t*)s+0x240u+row*0x848u+0x20u);
  r->sequence=(uint32_t)s;r->owner=owner;r->row=row;r->epoch=d->epoch;
  r->launch_tick=first&&clip_origin>=0&&(uint64_t)clip_origin<=tick?(uint64_t)clip_origin:tick;
  r->clip_pointer=0;r->clip_serial=0;r->restart=0;
 }
 r->native_tick=tick;r->valid=B(s,0x20)!=0;
 for(unsigned i=0;i<4;i++){float f=*(volatile float*)((uint8_t*)s+0x8720u+i*8)*1000.f;int v=f>32767.f?32767:f<-32768.f?-32768:(int)f;((uint16_t*)r->reserved)[i]=(uint16_t)v;}
 if(r->valid){
  MotionDeviceClip *c=find(d,owner,row);
  if(c&&snapshot(r,c))for(unsigned i=0;i<MOTION_LANES;i++){
   MotionCompactLane *l=r->lanes[r->active_cache&1u]+i;uint64_t position=tick*MOTION_P19_CLOCK_SCALE;
   uint64_t launch=r->launch_tick*MOTION_P19_CLOCK_SCALE;
   if(l->origin_tick<launch)position=position-launch+l->origin_tick;
   uint16_t value;if(!motion_compact_evaluate(l,position,&value))continue;
   uint32_t gain=(uint32_t)l->reserved[0]|((uint32_t)l->reserved[1]<<8);if(!gain)gain=1;
   float native=(float)((int)value*2-1000)*(float)gain/1000.f;
   *(volatile float*)((uint8_t*)s+0x8720u+i*8)=native;
   *(volatile float*)((uint8_t*)s+0x8740u+i*8)=native;
  }
 }
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;clean((uint32_t)r,64);
}
__attribute__((used,retain)) void motion_native_restart(void *s){
 if(!s||(int32_t)W(s,0x14)>=0)return;
 MotionDevice *d=device();if(!d)return;
 MotionDeviceRuntime *r=runtime(d,s);if(r&&r->sequence==(uint32_t)s)r->restart=1;
}
/* Call before the native transport enqueue, alongside P12's PLAY guard.
 * RECORD press has packet byte 91 and word +16=1; release has +16=0.
 * Latch the modifier on press, not on release. Otherwise releasing PROJ
 * first leaks RECORD-up, or holding PROJ after ordinary RECORD-down prevents
 * the ordinary recorder from stopping. No controller firmware is touched. */
__attribute__((used,retain)) int motion_native_record_gate(const void *packet){
 if(!packet||B(packet,0)!=0x91u)return 0;
 /* P24 (owner on P23: PROJ+RECORD also started the normal recorder): the
  * press/release word at +16 was a guess. Same rule as the P12 PLAY guard: every RECORD packet is dropped while PROJ (physical bit or UI
  * shift) is held. */
 int shift=0;uint32_t raw=W((void*)0x2401bd3cu,0);
 if(raw>=0x24000000u&&raw<=0x24080000u-0x233au)shift=(int)(*(volatile uint16_t*)(raw+0x2338u)&0x100u);
 invalidate(0x24048d60u,32);
 if(W((void*)0x24048d68u,0))shift=1;
 return shift!=0;
}
