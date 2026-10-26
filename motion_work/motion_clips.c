#include "motion_clips.h"
void motion_clip_init(MotionClip *c,uint32_t owner,uint8_t row,uint32_t bar){
 if(!c)return;
 c->owner=owner;c->row=row;c->initialized=(uint8_t)(owner!=0&&row<MOTION_CLIP_ROWS);
 c->reserved[0]=c->reserved[1]=0;
 for(unsigned i=0;i<MOTION_LANES;i++)motion_lane_init(c->lanes+i,bar);
}
void motion_clip_recorder_init(MotionClipRecorder *r,uint32_t bar){
 if(!r)return;
 motion_bank_init(&r->take,bar);r->recording_clip=0;r->owner=0;
 r->row=0;r->selected=0;r->reserved[0]=r->reserved[1]=0;
}
int motion_clip_matches(const MotionClip *c,uint32_t owner,uint8_t row){
 return c&&c->initialized&&owner&&row<MOTION_CLIP_ROWS&&c->owner==owner&&c->row==row;
}
int motion_clip_begin(MotionClipRecorder *r,MotionClip *c,uint64_t tick){
 if(!r||!c||!c->initialized||!c->owner||c->row>=MOTION_CLIP_ROWS)return MOTION_ERR_RANGE;
 if(r->recording_clip||r->take.record_held)return MOTION_ERR_STATE;
 for(unsigned i=0;i<MOTION_LANES;i++)r->take.lanes[0][i]=c->lanes[i];
 int result=motion_press_record(&r->take,1,0,MOTION_LANES,tick);
 if(result!=MOTION_OK)return result;
 r->recording_clip=c;r->owner=c->owner;r->row=c->row;return MOTION_OK;
}
int motion_clip_capture(MotionClipRecorder *r,uint8_t lane,uint64_t tick,uint16_t value){
 if(!r||!motion_clip_matches(r->recording_clip,r->owner,r->row))return MOTION_ERR_STATE;
 int result=motion_capture(&r->take,0,lane,tick,value);
 if(result==MOTION_OK)r->recording_clip->lanes[lane]=r->take.lanes[0][lane];
 return result;
}
int motion_clip_end(MotionClipRecorder *r,uint64_t tick){
 if(!r||!r->recording_clip)return MOTION_ERR_STATE;
 if(!motion_clip_matches(r->recording_clip,r->owner,r->row)){
  /* Never write a take into a recycled/new-project handle. */
  (void)motion_release_record(&r->take,tick);r->recording_clip=0;return MOTION_ERR_STATE;
 }
 int result=motion_release_record(&r->take,tick);
 if(result!=MOTION_OK)return result;
 for(unsigned i=0;i<MOTION_LANES;i++)r->recording_clip->lanes[i]=r->take.lanes[0][i];
 r->recording_clip=0;return MOTION_OK;
}
int motion_clip_launch(MotionClip *c,uint64_t tick){
 if(!c||!c->initialized)return MOTION_ERR_RANGE;
 for(unsigned i=0;i<MOTION_LANES;i++)if(c->lanes[i].recording)return MOTION_ERR_STATE;
 for(unsigned i=0;i<MOTION_LANES;i++)if(c->lanes[i].active)c->lanes[i].origin_tick=tick;
 return MOTION_OK;
}
