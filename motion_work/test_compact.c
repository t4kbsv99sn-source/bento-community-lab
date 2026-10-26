#include "motion_compact.h"
#include <assert.h>
#include <stdio.h>
static MotionBank bank;static MotionCompactLane compact;
int main(void){
 unsigned n=0;
 assert(sizeof(MotionCompactLane)<=1060);
 motion_bank_init(&bank,MOTION_DEFAULT_TICKS_PER_BAR);
 assert(motion_press_record(&bank,1,2,0,0)==MOTION_OK);
 for(unsigned i=0;i<128;i++){
  assert(motion_capture(&bank,2,0,i*570u,(uint16_t)((i*31u)%1000))==MOTION_OK);
 }
 assert(motion_release_record(&bank,600000)==MOTION_OK);
 MotionLane *lane=&bank.lanes[2][0];
 assert(motion_compact_pack(&compact,lane)==MOTION_OK);
 assert(compact.count==lane->count);
 /* Check interpolation, last-value hold and wraps over 64-bar time span. */
 for(uint64_t t=0;t<1500000;t+=1831){
  uint16_t a=0,b=0;
  assert(motion_evaluate(lane,t,&a)==motion_compact_evaluate(&compact,t,&b));
  assert(a==b);n++;
 }
 assert(motion_set_length(lane,MOTION_4)==MOTION_OK);
 assert(motion_compact_pack(&compact,lane)==MOTION_OK);
 for(uint64_t t=0;t<1500000;t+=2129){
  uint16_t a=0,b=0;
  assert(motion_evaluate(lane,t,&a)==motion_compact_evaluate(&compact,t,&b));
  assert(a==b);n++;
 }
 assert(lane->count);
 uint32_t old=compact.ticks[0];lane->points[0].flags=4;
 assert(motion_compact_pack(&compact,lane)==MOTION_ERR_RANGE);
 assert(compact.ticks[0]==old); /* never partly publish invalid points */
 printf("Compact M7 snapshot: %u full-core equivalence comparisons passed (%zu bytes/lane)\n",n,sizeof(compact));
 return 0;
}
