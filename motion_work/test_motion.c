#include "motion_core.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BAR MOTION_DEFAULT_TICKS_PER_BAR
#define CHECK(x) do {assert((x));tests++;} while(0)
static unsigned tests;
static MotionBank bank;
static MotionLane *lane(void){return &bank.lanes[0][0];}
static void start(uint64_t t){CHECK(motion_press_record(&bank,1,0,0,t)==MOTION_OK);}
static void stop(uint64_t t){CHECK(motion_release_record(&bank,t)==MOTION_OK);}
static void sample(uint64_t t,uint16_t v){CHECK(motion_capture(&bank,0,0,t,v)==MOTION_OK);}
static uint16_t value(uint64_t tick){uint16_t v=1234;CHECK(motion_evaluate(lane(),tick,&v)==1);return v;}
static void fresh(void){motion_bank_init(&bank,BAR);}
static void test_hold_release_and_sparse_length(void){
 fresh();CHECK(lane()->length_bars==16);
 start(0);sample(0,100);sample(BAR,400);sample(3*BAR,900);stop(3*BAR);
 CHECK(lane()->length_bars==16);CHECK(value(3*BAR)==900);
 CHECK(value(12*BAR)==900); /* no automatic 3-bar repeated wiggle */
 CHECK(value(16*BAR)==100);CHECK(value(17*BAR)==400);
 CHECK(lane()->recording==0 && bank.record_held==0);
}
static void test_no_automatic_stop_at_selected_length(void){
 fresh();CHECK(motion_set_length(lane(),MOTION_4)==MOTION_OK);
 start(2*BAR);sample(2*BAR,100);sample(5*BAR,250);
 CHECK(lane()->recording==1);sample(7*BAR,900);CHECK(lane()->recording==1);
 stop(7*BAR);CHECK(lane()->length_bars==4);
 CHECK(value(7*BAR)==900); /* overwrite phase inside same 4 bar loop */
}
static void test_phase_separate_from_underlying_clip(void){
 fresh();start(101*BAR);sample(101*BAR,10);sample(104*BAR,500);stop(104*BAR);
 CHECK(value(105*BAR)==500);
 CHECK(value(106*BAR)==500); /* imagine 2-bar clip restarted here */
 CHECK(value(117*BAR)==10); /* independent 16-bar motion wrap */
}
static void test_resize_is_non_destructive(void){
 fresh();start(0);sample(0,200);sample(10*BAR,700);stop(10*BAR);
 CHECK(motion_resize_encoder(lane(),-1)==MOTION_OK);
 CHECK(lane()->length_bars==8);CHECK(lane()->count==2);
 CHECK(value(11*BAR)==200); /* future event stays hidden */
 CHECK(motion_resize_encoder(lane(),1)==MOTION_OK);
 CHECK(lane()->length_bars==16);CHECK(value(10*BAR)==700);
}
static void test_overdub_and_replace(void){
 fresh();start(0);sample(0,100);sample(2*BAR,500);stop(2*BAR);
 start(16*BAR);sample(16*BAR,250);stop(16*BAR);CHECK(value(0)==250);
 CHECK(value(2*BAR)==500);CHECK(lane()->count==2);
 CHECK(motion_set_mode(lane(),MOTION_REPLACE)==MOTION_OK);
 start(32*BAR);CHECK(lane()->count==2); /* don't erase until actual movement */
 stop(32*BAR);CHECK(lane()->count==2);
 start(48*BAR);sample(49*BAR,900);stop(49*BAR);
 CHECK(lane()->count==1);CHECK(value(48*BAR)==900);
}
static void test_auto_length(void){
 fresh();CHECK(motion_set_length(lane(),MOTION_AUTO)==MOTION_OK);
 start(0);sample(0,1);sample(3*BAR,250);stop(3*BAR);
 CHECK(lane()->length_bars==4);
 fresh();CHECK(motion_set_length(lane(),MOTION_AUTO)==MOTION_OK);
 start(0);sample(0,1);sample(10*BAR,250);stop(10*BAR);
 CHECK(lane()->length_bars==16);CHECK(value(10*BAR)==250);
 fresh();CHECK(motion_set_length(lane(),MOTION_AUTO)==MOTION_OK);
 start(0);sample(0,1);sample(60*BAR,900);stop(60*BAR);
 CHECK(lane()->length_bars==64);CHECK(value(60*BAR)==900);
 fresh();CHECK(motion_set_length(lane(),MOTION_AUTO)==MOTION_OK);
 start(0);sample(0,100);stop(0);CHECK(lane()->length_bars==4);
}
static void test_interpolation_and_hold(void){
 fresh();start(0);sample(0,100);sample(BAR,900);stop(BAR);
 CHECK(value(BAR/2)==500);CHECK(value(4*BAR)==900);
 CHECK(motion_set_interpolation(lane(),MOTION_STEP)==MOTION_OK);
 CHECK(value(BAR/2)==100);
}
static void test_inputs_and_held_record(void){
 fresh();CHECK(motion_press_record(&bank,0,0,0,0)==MOTION_ERR_STATE);
 CHECK(motion_press_record(&bank,1,9,0,0)==MOTION_ERR_RANGE);
 CHECK(motion_press_record(&bank,1,0,5,0)==MOTION_ERR_RANGE);
 CHECK(motion_capture(&bank,0,0,0,200)==MOTION_ERR_STATE);
 start(0);CHECK(motion_press_record(&bank,1,0,0,0)==MOTION_ERR_STATE);
 CHECK(motion_set_length(lane(),MOTION_8)==MOTION_ERR_STATE);
 CHECK(motion_capture(&bank,0,1,0,100)==MOTION_ERR_STATE);
 CHECK(motion_capture(&bank,0,0,0,1001)==MOTION_ERR_RANGE);
 sample(0,100);stop(0);
 CHECK(motion_release_record(&bank,0)==MOTION_ERR_STATE);
 CHECK(motion_set_length(lane(),(MotionBars)3)==MOTION_ERR_STATE);
 CHECK(motion_set_mode(lane(),(MotionWriteMode)3)==MOTION_ERR_RANGE);
}
static void test_quantization_duplicates_and_step_wrap(void){
 fresh();start(0);sample(0,250);sample(3,300);sample(4,350);
 CHECK(lane()->count==1);CHECK(value(0)==350);
 sample(8,500);CHECK(lane()->count==2);stop(8);
 CHECK(lane()->points[1].tick==10);
}
static void test_serialization_roundtrip_and_corruption(void){
 fresh();start(0);sample(0,100);sample(BAR,900);stop(BAR);
 uint8_t payload[28+MOTION_EVENTS*8];int n=motion_encode(lane(),payload,sizeof(payload));
 CHECK(n==44);CHECK(motion_encoded_size(lane())==(size_t)n);
 MotionLane out;CHECK(motion_decode(&out,payload,n)==MOTION_OK);
 CHECK(out.count==2&&out.length_bars==16&&out.points[1].value==900);
 CHECK(motion_evaluate(&out,2*BAR,&out.previous_value)==1&&out.previous_value==900);
 CHECK(motion_encode(lane(),payload,40)==MOTION_ERR_RANGE);
 payload[4]=66;CHECK(motion_decode(&out,payload,n)==MOTION_ERR_FORMAT);payload[4]=1;
 payload[28+4]=0xff;payload[28+5]=0xff;
 CHECK(motion_decode(&out,payload,n)==MOTION_ERR_FORMAT);
}
static void test_clear_and_boundaries(void){
 fresh();CHECK(motion_resize_encoder(lane(),-1)==MOTION_OK);CHECK(lane()->length_bars==8);
 CHECK(motion_resize_encoder(lane(),-1)==MOTION_OK);CHECK(lane()->length_bars==4);
 CHECK(motion_resize_encoder(lane(),-1)==MOTION_OK);CHECK(lane()->length_bars==4);
 CHECK(motion_resize_encoder(lane(),1)==MOTION_OK);CHECK(lane()->length_bars==8);
 start(0);sample(0,200);CHECK(motion_clear_lane(lane())==MOTION_ERR_STATE);stop(0);
 CHECK(motion_clear_lane(lane())==MOTION_OK);CHECK(motion_evaluate(lane(),0,&lane()->previous_value)==0);
}
static void test_capture_multiple_lanes_on_one_hold(void){
 fresh();CHECK(motion_press_record(&bank,1,0,MOTION_LANES,100*BAR)==MOTION_OK);
 CHECK(motion_capture(&bank,0,0,100*BAR,100)==MOTION_OK);
 CHECK(motion_capture(&bank,0,2,101*BAR,800)==MOTION_OK);
 CHECK(motion_capture(&bank,0,3,101*BAR,900)==MOTION_OK);
 CHECK(motion_capture(&bank,1,0,101*BAR,300)==MOTION_ERR_STATE);
 CHECK(motion_release_record(&bank,101*BAR)==MOTION_OK);
 CHECK(bank.lanes[0][0].count==1&&bank.lanes[0][1].count==0);
 CHECK(bank.lanes[0][2].count==1&&bank.lanes[0][3].count==1);
 CHECK(bank.lanes[0][2].recording==0);
 CHECK(bank.lanes[0][0].origin_tick==100*BAR);
}
static void test_capacity_and_no_motion_auto(void){
 fresh();CHECK(motion_set_length(lane(),MOTION_AUTO)==MOTION_OK);
 start(0);stop(30*BAR);CHECK(lane()->length_bars==16);
 CHECK(motion_set_length(lane(),MOTION_64)==MOTION_OK);
 start(0);
 for(unsigned i=0;i<MOTION_EVENTS;i++){
  CHECK(motion_capture(&bank,0,0,10u*i,(uint16_t)(i%1001u))==MOTION_OK);
 }
 CHECK(lane()->count==MOTION_EVENTS);
 CHECK(motion_capture(&bank,0,0,10u*MOTION_EVENTS,100)==MOTION_ERR_FULL);
 stop(10u*MOTION_EVENTS);
 uint8_t blob[28+MOTION_EVENTS*8];
 CHECK(motion_encode(lane(),blob,sizeof(blob))==(int)sizeof(blob));
 MotionLane decoded;
 CHECK(motion_decode(&decoded,blob,sizeof(blob))==MOTION_OK);
 CHECK(decoded.count==MOTION_EVENTS && decoded.points[MOTION_EVENTS-1].tick==(MOTION_EVENTS-1)*10u);
}
int main(void){
 test_hold_release_and_sparse_length();test_no_automatic_stop_at_selected_length();
 test_phase_separate_from_underlying_clip();test_resize_is_non_destructive();
 test_overdub_and_replace();test_auto_length();test_interpolation_and_hold();
 test_inputs_and_held_record();test_quantization_duplicates_and_step_wrap();
 test_serialization_roundtrip_and_corruption();test_clear_and_boundaries();
 test_capture_multiple_lanes_on_one_hold();
 test_capacity_and_no_motion_auto();
 printf("Motion core: %u assertions passed across 13 scenarios\n",tests);return 0;
}
