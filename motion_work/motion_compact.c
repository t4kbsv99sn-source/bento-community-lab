#include "motion_compact.h"
#define POINT_TICK_MASK 0xfffffu
#define POINT_VALUE_SHIFT 20u
#define POINT_FLAGS_SHIFT 30u
static uint32_t pt_tick(uint32_t word){return (word&POINT_TICK_MASK)*MOTION_QUANTUM;}
static uint32_t pt_value(uint32_t word){return (word>>POINT_VALUE_SHIFT)&0x3ffu;}
int motion_compact_pack(MotionCompactLane *dst,const MotionLane *src){
 if(!dst||!src||src->count>MOTION_EVENTS||src->ticks_per_bar==0||
    src->length_bars==0||src->length_bars>64||src->interpolation>MOTION_LINEAR)return MOTION_ERR_RANGE;
 /* Check before touching destination: rejected source cannot corrupt live M7
  * snapshot. The actual cross-core publication is a separate responsibility. */
 for(unsigned i=0;i<src->count;i++){
  const MotionPoint *p=&src->points[i];
  if(p->value>1000||p->flags>3||p->tick%MOTION_QUANTUM||
     p->tick/MOTION_QUANTUM>MOTION_COMPACT_TICK_MAX||
     (i&&p->tick<=src->points[i-1].tick))return MOTION_ERR_RANGE;
 }
 for(unsigned i=0;i<src->count;i++){
  const MotionPoint *p=&src->points[i];
  dst->ticks[i]=(p->tick/MOTION_QUANTUM)|
   ((uint32_t)p->value<<POINT_VALUE_SHIFT)|((uint32_t)p->flags<<POINT_FLAGS_SHIFT);
 }
 dst->count=src->count;dst->ticks_per_bar=src->ticks_per_bar;
 dst->origin_tick=src->origin_tick;dst->length_bars=src->length_bars;
 dst->interpolation=src->interpolation;dst->active=src->active;
 dst->reserved[0]=dst->reserved[1]=0;
 return MOTION_OK;
}
int motion_compact_evaluate(const MotionCompactLane *l,uint64_t song,uint16_t *out){
 if(!l||!out||!l->active||!l->count||l->count>MOTION_EVENTS||!l->ticks_per_bar||
    !l->length_bars||l->length_bars>64)return 0;
 uint32_t period=l->ticks_per_bar*l->length_bars;
 if(!period)return 0;
 uint32_t pos=(uint32_t)((song>=l->origin_tick?song-l->origin_tick:0)%period);
 /* Published points are strictly sorted. Bound both searches so audio work
  * is logarithmic even for a full 256-point lane. Hidden tail points stay in
  * storage and do not fold back into a shorter loop. */
 unsigned lo=0,hi=l->count;
 while(lo<hi){unsigned mid=lo+(hi-lo)/2;if(pt_tick(l->ticks[mid])<period)lo=mid+1;else hi=mid;}
 unsigned end=lo;if(!end)return 0;
 uint32_t prev=l->ticks[0],next=0;
 if(pos<pt_tick(prev)){*out=(uint16_t)pt_value(prev);return 1;}
 lo=1;hi=end;
 while(lo<hi){unsigned mid=lo+(hi-lo)/2;if(pt_tick(l->ticks[mid])<=pos)lo=mid+1;else hi=mid;}
 prev=l->ticks[lo-1];if(lo<end)next=l->ticks[lo];
 if(!next||l->interpolation==MOTION_STEP){*out=(uint16_t)pt_value(prev);return 1;}
 uint32_t span=pt_tick(next)-pt_tick(prev);
 int32_t delta=(int32_t)pt_value(next)-(int32_t)pt_value(prev);
 int32_t value=(int32_t)pt_value(prev)+(int32_t)((int64_t)delta*(pos-pt_tick(prev))/span);
 *out=(uint16_t)value;return 1;
}
