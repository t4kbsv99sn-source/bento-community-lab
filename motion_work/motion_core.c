#include "motion_core.h"
#include <stddef.h>
/* No libc dependency: suitable for isolated M4/M7 builds. */
static void zero_mem(void *p,size_t n){unsigned char *b=(unsigned char*)p;while(n--)*b++=0;}

static const uint16_t lengths[5]={4,8,16,32,64};
static int valid_bars(uint16_t b){return b==0||b==4||b==8||b==16||b==32||b==64;}
static uint32_t quant(uint64_t tick){return (uint32_t)((tick+MOTION_QUANTUM/2)/MOTION_QUANTUM*MOTION_QUANTUM);}
static uint32_t loop_ticks(const MotionLane *l){return l->ticks_per_bar*l->length_bars;}
static uint64_t elapsed(uint64_t song,uint64_t origin){return song>=origin?song-origin:0;}
static uint16_t clamp(uint16_t value){return value>1000?1000:value;}
void motion_lane_init(MotionLane *l,uint32_t bar){
 if(!l)return;
 zero_mem(l,sizeof(*l));
 l->ticks_per_bar=bar?bar:MOTION_DEFAULT_TICKS_PER_BAR;
 l->length_bars=16; l->pending_bars=16;
 l->max_tick=l->ticks_per_bar*64u; l->interpolation=MOTION_LINEAR;
}
void motion_bank_init(MotionBank *b,uint32_t bar){
 if(!b)return;
 zero_mem(b,sizeof(*b)); b->selected_track=b->selected_lane=-1;
 for(unsigned t=0;t<MOTION_TRACKS;t++)for(unsigned i=0;i<MOTION_LANES;i++)motion_lane_init(&b->lanes[t][i],bar);
}
int motion_set_length(MotionLane *l,MotionBars bars){
 if(!l||!valid_bars((uint16_t)bars)||l->recording)return MOTION_ERR_STATE;
 /* Auto is a pre-recording mode, not an accidental shortening of the loop. */
 if(bars==MOTION_AUTO){l->pending_bars=0;return MOTION_OK;}
 l->pending_bars=l->length_bars=(uint16_t)bars;
 return MOTION_OK;
}
int motion_set_mode(MotionLane *l,MotionWriteMode mode){if(!l||mode>MOTION_REPLACE)return MOTION_ERR_RANGE;l->write_mode=(uint8_t)mode;return MOTION_OK;}
int motion_set_interpolation(MotionLane *l,MotionInterpolation mode){if(!l||mode>MOTION_LINEAR)return MOTION_ERR_RANGE;l->interpolation=(uint8_t)mode;return MOTION_OK;}
static int insert(MotionLane *l,uint32_t tick,uint16_t value){
 uint16_t i=0;while(i<l->count&&l->points[i].tick<tick)i++;
 if(i<l->count&&l->points[i].tick==tick){l->points[i].value=value;return MOTION_OK;}
 if(l->count==MOTION_EVENTS)return MOTION_ERR_FULL;
 for(uint16_t j=l->count;j>i;j--)l->points[j]=l->points[j-1];
 l->points[i]=(MotionPoint){tick,value,0};l->count++;
 return MOTION_OK;
}
int motion_press_record(MotionBank *b,uint8_t shift,uint8_t track,uint8_t index,uint64_t song){
 if(!b||track>=MOTION_TRACKS||index>MOTION_LANES)return MOTION_ERR_RANGE;
 if(!shift||b->record_held)return MOTION_ERR_STATE;
 if(index<MOTION_LANES && b->lanes[track][index].recording)return MOTION_ERR_STATE;
 b->record_held=1;b->record_tick=song;
 b->selected_track=(int8_t)track;
 b->selected_lane=index==MOTION_LANES?-1:(int8_t)index;
 if(index==MOTION_LANES)return MOTION_OK;
 MotionLane *l=&b->lanes[track][index];
 l->recording=1;l->record_tick=song;l->have_previous=0;
 l->replace_pending=l->write_mode==MOTION_REPLACE;
 if(!l->active)l->origin_tick=song; /* first take anchors phase */
 return MOTION_OK;
}
int motion_capture(MotionBank *b,uint8_t track,uint8_t index,uint64_t song,uint16_t value){
 if(!b||track>=MOTION_TRACKS||index>=MOTION_LANES||value>1000)return MOTION_ERR_RANGE;
 if(!b->record_held||b->selected_track!=(int8_t)track||
    (b->selected_lane>=0&&b->selected_lane!=(int8_t)index))return MOTION_ERR_STATE;
 MotionLane *l=&b->lanes[track][index];
 if(!l->recording&&b->selected_lane==-1){
  l->recording=1;l->record_tick=b->record_tick;l->have_previous=0;
  l->replace_pending=l->write_mode==MOTION_REPLACE;
  if(!l->active)l->origin_tick=b->record_tick;
 }
 if(!l->recording)return MOTION_ERR_STATE;
 uint32_t period=l->pending_bars==0 ? l->max_tick : loop_ticks(l);if(!period)return MOTION_ERR_STATE;
 uint32_t t=quant(elapsed(song,l->origin_tick)%period);
 if(t>=period)t=0; /* sample exactly at loop boundary goes to the first step */
 if(l->have_previous&&l->previous_value==value&&l->captured==t)return MOTION_OK;
 if(l->replace_pending){l->count=0;l->replace_pending=0;}
 int result=insert(l,t,clamp(value));if(result!=MOTION_OK)return result;
 l->active=1;l->have_previous=1;l->previous_value=value;l->captured=t;
 return MOTION_OK;
}
static void finish_lane(MotionLane *l,uint64_t song){
 if(l->pending_bars==0&&l->have_previous){
  uint64_t e=elapsed(song,l->record_tick);
  uint64_t actual=(e+l->ticks_per_bar-1u)/l->ticks_per_bar;
  uint32_t bars=(uint32_t)(actual>64u?64u:actual);
  if(bars<4)bars=4;
  unsigned i=0;while(i<4&&lengths[i]<bars)i++;
  l->length_bars=lengths[i];
 }
 l->recording=0;l->have_previous=0;l->replace_pending=0;
}
int motion_release_record(MotionBank *b,uint64_t song){
 if(!b||!b->record_held)return MOTION_ERR_STATE;
 unsigned track=(unsigned)b->selected_track;
 if(b->selected_lane==-1){
  for(unsigned i=0;i<MOTION_LANES;i++){
   MotionLane *l=&b->lanes[track][i];
   if(l->recording)finish_lane(l,song);
  }
 }else finish_lane(&b->lanes[track][(unsigned)b->selected_lane],song);
 b->record_held=0;b->selected_track=b->selected_lane=-1;
 return MOTION_OK;
}
int motion_evaluate(const MotionLane *l,uint64_t song,uint16_t *value){
 if(!l||!value||!l->active||!l->count)return 0;
 uint32_t period=loop_ticks(l);if(!period)return 0;
 uint32_t pos=(uint32_t)(elapsed(song,l->origin_tick)%period);
 /* Events outside a shortened lane remain stored for Undo/extend, but do not
  * wrap into the shortened cycle or get silently shifted in time. */
 uint16_t first=l->count;
 for(uint16_t i=0;i<l->count;i++)if(l->points[i].tick<period){first=i;break;}
 if(first==l->count)return 0;
 const MotionPoint *prev=&l->points[first],*next=0;
 if(pos<prev->tick){*value=prev->value;return 1;}
 for(uint16_t i=first+1;i<l->count;i++){
  if(l->points[i].tick>=period)break;
  if(l->points[i].tick>pos){next=&l->points[i];break;}
  prev=&l->points[i];
 }
 if(!next||l->interpolation==MOTION_STEP){*value=prev->value;return 1;}
 uint32_t span=next->tick-prev->tick;
 int32_t delta=(int32_t)next->value-(int32_t)prev->value;
 int32_t interp=(int32_t)prev->value+(int32_t)((int64_t)delta*(pos-prev->tick)/span);
 *value=(uint16_t)interp;return 1;
}
int motion_resize_encoder(MotionLane *l,int direction){
 if(!l||l->recording)return MOTION_ERR_STATE;
 unsigned i=0;while(i<5&&lengths[i]!=l->length_bars)i++;
 if(i==5)return MOTION_ERR_STATE;
 if(direction<0&&i>0)i--;else if(direction>0&&i<4)i++;
 return motion_set_length(l,(MotionBars)lengths[i]);
}
int motion_transport_restart(MotionBank *b,uint64_t song){
 if(!b||b->record_held)return MOTION_ERR_STATE;
 for(unsigned track=0;track<MOTION_TRACKS;track++)
  for(unsigned lane=0;lane<MOTION_LANES;lane++){
   MotionLane *l=&b->lanes[track][lane];
   if(l->active)l->origin_tick=song;
  }
 return MOTION_OK;
}
int motion_clear_lane(MotionLane *l){
 if(!l||l->recording)return MOTION_ERR_STATE;
 l->count=0;l->active=0;l->have_previous=0;return MOTION_OK;
}
/* LE wire format: MOTA, v1, interpolation, write mode, active, bar ticks,
 * chosen length, pending Auto/fixed length, origin, count, then 8-byte events.
 * Future project adapter writes this blob into a versioned native XML field. */
static void w16(uint8_t*p,uint16_t x){p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);}
static void w32(uint8_t*p,uint32_t x){w16(p,(uint16_t)x);w16(p+2,(uint16_t)(x>>16));}
static void w64(uint8_t*p,uint64_t x){w32(p,(uint32_t)x);w32(p+4,(uint32_t)(x>>32));}
static uint16_t r16(const uint8_t*p){return (uint16_t)(p[0]|p[1]<<8);}
static uint32_t r32(const uint8_t*p){return r16(p)|((uint32_t)r16(p+2)<<16);}
static uint64_t r64(const uint8_t*p){return r32(p)|((uint64_t)r32(p+4)<<32);}
#define HEADER 28u
size_t motion_encoded_size(const MotionLane*l){return l?HEADER+8u*l->count:0;}
int motion_encode(const MotionLane*l,uint8_t *dst,size_t cap){
 if(!l||!dst||l->count>MOTION_EVENTS||cap<motion_encoded_size(l))return MOTION_ERR_RANGE;
 zero_mem(dst,HEADER);dst[0]='M';dst[1]='O';dst[2]='T';dst[3]='A';dst[4]=MOTION_FORMAT_VERSION;
 dst[5]=l->interpolation;dst[6]=l->write_mode;dst[7]=l->active;
 w32(dst+8,l->ticks_per_bar);w16(dst+12,l->length_bars);
 w16(dst+14,l->pending_bars);w64(dst+16,l->origin_tick);w16(dst+24,l->count);
 for(unsigned i=0;i<l->count;i++){uint8_t*p=dst+HEADER+i*8;w32(p,l->points[i].tick);w16(p+4,l->points[i].value);w16(p+6,l->points[i].flags);}
 return (int)motion_encoded_size(l);
}
int motion_decode(MotionLane*l,const uint8_t *p,size_t len){
 if(!l||!p||len<HEADER||(p[0]!='M'||p[1]!='O'||p[2]!='T'||p[3]!='A')||p[4]!=MOTION_FORMAT_VERSION||p[5]>MOTION_LINEAR||p[6]>MOTION_REPLACE||p[7]>1)return MOTION_ERR_FORMAT;
 uint32_t bar=r32(p+8);uint16_t bars=r16(p+12),pending=r16(p+14),count=r16(p+24);
 if(!bar||bar>65535u||!bars||!valid_bars(bars)||!valid_bars(pending)||count>MOTION_EVENTS||len!=HEADER+8u*count)return MOTION_ERR_FORMAT;
 uint32_t max_tick=bar*64u;
 for(unsigned i=0;i<count;i++){
  const uint8_t *e=p+HEADER+i*8;
  uint32_t tick=r32(e);uint16_t value=r16(e+4);
  if(value>1000||tick>=max_tick||
     (i&&tick<=r32(p+HEADER+(i-1)*8)))return MOTION_ERR_FORMAT;
 }
 if(p[7]&&!count)return MOTION_ERR_FORMAT;
 motion_lane_init(l,bar);l->length_bars=bars;l->pending_bars=pending;
 l->interpolation=p[5];l->write_mode=p[6];l->active=p[7];l->origin_tick=r64(p+16);
 l->count=count;
 for(unsigned i=0;i<count;i++){
  const uint8_t *e=p+HEADER+i*8;
  l->points[i]=(MotionPoint){r32(e),r16(e+4),r16(e+6)};
 }
 return MOTION_OK;
}
