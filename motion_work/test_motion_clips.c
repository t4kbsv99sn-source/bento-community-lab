#include "motion_clips.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static MotionClip a,b,other;
static MotionClipRecorder recorder;
static unsigned checks;
#define C(x) do {assert(x);checks++;} while(0)
int main(void){
 const uint32_t bar=MOTION_DEFAULT_TICKS_PER_BAR;
 motion_clip_init(&a,100,0,bar);motion_clip_init(&b,100,1,bar);
 motion_clip_init(&other,200,0,bar);motion_clip_recorder_init(&recorder,bar);
 C(motion_clip_matches(&a,100,0));C(!motion_clip_matches(&a,100,1));
 C(!motion_clip_matches(&a,200,0));C(!motion_clip_matches(&a,100,16));
 C(motion_set_length(a.lanes,MOTION_16)==MOTION_OK);
 C(motion_set_length(a.lanes+1,MOTION_32)==MOTION_OK);
 C(motion_clip_begin(&recorder,&a,0)==MOTION_OK);
 C(motion_clip_begin(&recorder,&b,1)==MOTION_ERR_STATE);
 C(motion_clip_capture(&recorder,0,0,100)==MOTION_OK);
 C(motion_clip_capture(&recorder,0,bar*3,900)==MOTION_OK);
 C(motion_clip_capture(&recorder,1,bar,500)==MOTION_OK);
 C(motion_clip_launch(&a,100)==MOTION_ERR_STATE);
 C(motion_clip_end(&recorder,bar*3)==MOTION_OK);
 C(a.lanes[0].length_bars==16&&a.lanes[1].length_bars==32);
 C(!b.lanes[0].active&&!other.lanes[0].active);
 uint16_t value;
 C(motion_evaluate(a.lanes,bar*10,&value)&&value==900);
 C(motion_set_length(b.lanes,MOTION_4)==MOTION_OK);
 C(motion_clip_begin(&recorder,&b,bar*10)==MOTION_OK);
 C(motion_clip_capture(&recorder,0,bar*10,700)==MOTION_OK);
 C(motion_clip_end(&recorder,bar*11)==MOTION_OK);
 C(b.lanes[0].length_bars==4&&a.lanes[0].length_bars==16);
 C(motion_evaluate(b.lanes,bar*12,&value)&&value==700);
 C(motion_evaluate(a.lanes,bar*12,&value)&&value==900);
 C(motion_clip_launch(&a,bar*20)==MOTION_OK);
 C(a.lanes[0].origin_tick==bar*20&&b.lanes[0].origin_tick==bar*10);
 C(motion_evaluate(a.lanes,bar*20,&value)&&value==100);
 C(motion_resize_encoder(a.lanes,-1)==MOTION_OK);
 C(a.lanes[0].count==2&&a.lanes[0].length_bars==8);
 unsigned char data[4096];MotionLane loaded;
 int n=motion_encode(a.lanes,data,sizeof(data));C(n>0);
 C(motion_decode(&loaded,data,(size_t)n)==MOTION_OK);
 C(loaded.count==2&&loaded.length_bars==8);
 C(motion_evaluate(&loaded,bar*24,&value)&&value==900);
 /* A reused track handle during project load must not receive the old take. */
 C(motion_clip_begin(&recorder,&other,0)==MOTION_OK);
 other.owner=300;C(motion_clip_capture(&recorder,0,1,500)==MOTION_ERR_STATE);
 C(motion_clip_end(&recorder,2)==MOTION_ERR_STATE);
 C(!recorder.take.record_held&&!recorder.recording_clip);
 printf("Per-clip motion: %u checks passed\n",checks);
 return 0;
}
