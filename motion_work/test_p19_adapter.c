#include "motion_p19_adapter.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
static unsigned checks=0;
#define C(x) do{assert((x));++checks;}while(0)
static MotionControls controls;static MotionP19Adapter native;
int main(void){
 uint64_t tick;
 C(motion_p19_tick(240,&tick)==MOTION_OK&&tick==960); /* native 16th */
 C(motion_p19_tick(3840,&tick)==MOTION_OK&&tick==15360); /* 4/4 bar */
 C(motion_p19_tick(-1,&tick)==MOTION_ERR_RANGE);
 C(motion_p19_tick(INT64_MAX,&tick)==MOTION_ERR_RANGE);
 motion_controls_init(&controls,MOTION_DEFAULT_TICKS_PER_BAR);
 motion_p19_init(&native,&controls);
 C(!motion_p19_button(&native,0xaf,9,0)); /* unmapped: no native hijack */
 C(motion_p19_bind_record_button(&native,9)==MOTION_OK);
 C(motion_p19_select(&native,1,4)==MOTION_OK);
 C(motion_controls_menu_length(&controls,0,MOTION_16)==MOTION_OK);
 C(motion_controls_menu_length(&controls,1,MOTION_32)==MOTION_OK);
 C(!motion_p19_button(&native,0xaf,8,0)); /* non-REC passes through */
 C(!motion_p19_button(&native,0xaf,9,0)); /* plain REC passes through */
 motion_p19_shift(&native,1);
 C(motion_p19_button(&native,0xaf,9,0));
 C(motion_p19_recording(&native));
 C(motion_p19_select(&native,2,4)==MOTION_ERR_STATE); /* no editing during take */
 MotionP19Route a={1,0,1,0},b={1,1,1,0},unmapped={1,2,0,0},other={2,0,1,0};
 C(motion_p19_movement(&native,unmapped,240,850)==0);
 C(motion_p19_movement(&native,other,240,850)==0);
 C(motion_p19_movement(&native,a,0,100)==1);
 C(motion_p19_movement(&native,a,240,800)==1);
 C(motion_p19_movement(&native,b,3840,600)==1);
 motion_p19_shift(&native,0);
 C(motion_p19_button(&native,0xb0,9,11520)==1); /* release 3 bars */
 C(!motion_p19_recording(&native));
 C(controls.bank.lanes[1][0].length_bars==16);
 C(controls.bank.lanes[1][1].length_bars==32);
 C(motion_evaluate(&controls.bank.lanes[1][0],4*3840*8,&(uint16_t){0})==1);
 C(motion_p19_length(&native,0,-1)==MOTION_OK);
 C(controls.bank.lanes[1][0].length_bars==8);
 C(controls.bank.lanes[1][0].count==2);
 C(!motion_p19_button(&native,0xb0,9,11521)); /* unmatched release passes */
 C(!motion_p19_movement(&native,a,11522,200));
 /* Rewind while record is held: terminate recording without spilling values. */
 motion_p19_shift(&native,1);
 C(motion_p19_button(&native,0xaf,9,13000)==1);
 C(motion_p19_movement(&native,a,13500,500)==1);
 C(motion_p19_button(&native,0xb0,9,2000));
 C(!motion_p19_recording(&native));
 C(controls.bank.lanes[1][0].origin_tick==2000u*4u);
 C(motion_p19_transport(&native,25000)==MOTION_OK);
 C(motion_p19_transport(&native,0)==MOTION_OK); /* global song restart */
 C(controls.bank.lanes[1][0].origin_tick==0);
 uint16_t value=0;
 C(motion_evaluate(&controls.bank.lanes[1][0],4u*240u,&value)==1);
 C(value<=1000);
 /* Bind the physically traced P19 button, then test event/release ordering. */
 C(motion_p19_bind_record_button(&native,MOTION_P19_RECORD_BUTTON)==MOTION_OK);
 C(motion_p19_button(&native,0xaf,14,1000)==1);
 C(motion_p19_button(&native,0xaf,14,1001)==1); /* repeated press stays consumed */
 C(motion_p19_transport(&native,0)==MOTION_OK);
 C(!motion_p19_recording(&native));
 motion_p19_shift(&native,0);
 C(motion_p19_button(&native,0xb0,14,0)==1); /* even after async rewind */
 C(!motion_p19_button(&native,0xb0,14,1));
 C(!motion_p19_button(&native,0xaf,14,2)); /* ordinary record still passes */
 C(!motion_p19_button(&native,0xb0,14,3));
 printf("P19 motion interface: %u checks passed\n",checks);
 return 0;
}
