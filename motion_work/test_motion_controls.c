#include "motion_controls.h"
#include <assert.h>
#include <stdio.h>
#define CHECK(expr) do{assert((expr));tests++;}while(0)
static unsigned tests;
static MotionControls ui;
int main(void){
 motion_controls_init(&ui,MOTION_DEFAULT_TICKS_PER_BAR);
 CHECK(motion_controls_select(&ui,2,4)==MOTION_OK); /* record All mapped A-D */
 CHECK(motion_controls_menu_length(&ui,0,MOTION_32)==MOTION_OK);
 CHECK(motion_controls_menu_length(&ui,1,MOTION_8)==MOTION_OK);
 CHECK(motion_controls_menu_length(&ui,4,MOTION_8)==MOTION_ERR_RANGE);
 CHECK(motion_controls_record_button(&ui,1,0,0)==0); /* ordinary native REC */
 CHECK(ui.bank.record_held==0);
 CHECK(motion_controls_record_button(&ui,1,1,2000)==1);
 MotionCounter c;
 CHECK(motion_controls_counter(&ui,2000,&c)==1&&c.bar==1&&c.total==32);
 CHECK(motion_controls_parameter(&ui,2,0,2000,100)==1);
 CHECK(motion_controls_parameter(&ui,2,1,2000+MOTION_DEFAULT_TICKS_PER_BAR,700)==1);
 CHECK(motion_controls_parameter(&ui,1,0,2000,800)==0);
 CHECK(motion_controls_counter(&ui,2000+2*MOTION_DEFAULT_TICKS_PER_BAR,&c)==1&&c.bar==3);
 CHECK(motion_controls_record_button(&ui,0,0,2000+2*MOTION_DEFAULT_TICKS_PER_BAR)==1); /* released modifier */
 CHECK(ui.bank.record_held==0);
 CHECK(ui.bank.lanes[2][0].length_bars==32);
 CHECK(ui.bank.lanes[2][1].length_bars==8);
 CHECK(motion_controls_counter(&ui,2000,&c)==0);
 CHECK(motion_controls_select(&ui,2,0)==MOTION_OK);
 CHECK(motion_controls_editor_length(&ui,0,-1)==MOTION_OK);
 CHECK(ui.bank.lanes[2][0].length_bars==16);
 CHECK(motion_controls_editor_length(&ui,0,+1)==MOTION_OK);
 CHECK(ui.bank.lanes[2][0].length_bars==32);
 CHECK(motion_controls_record_button(&ui,0,0,0)==0);
 printf("Motion controls: %u assertions passed\n",tests);
}
