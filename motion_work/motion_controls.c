#include "motion_controls.h"
void motion_controls_init(MotionControls *ui,uint32_t bar){
 if(!ui)return;
 motion_bank_init(&ui->bank,bar);ui->track=0;ui->lane=0;
}
int motion_controls_select(MotionControls *ui,uint8_t track,uint8_t lane){
 if(!ui||track>=MOTION_TRACKS||lane>MOTION_LANES)return MOTION_ERR_RANGE;
 ui->track=track;ui->lane=lane;return MOTION_OK;
}
int motion_controls_record_button(MotionControls *ui,int down,int shift,uint64_t tick){
 if(!ui)return 0;
 if(down){
  if(shift&&motion_press_record(&ui->bank,1,ui->track,ui->lane,tick)==MOTION_OK)return 1;
  return 0; /* stock RECORD untouched unless modifier/gesture recognized */
 }
 if(ui->bank.record_held){(void)motion_release_record(&ui->bank,tick);return 1;}
 return 0;
}
int motion_controls_parameter(MotionControls *ui,uint8_t track,uint8_t lane,uint64_t tick,uint16_t value){
 if(!ui||!ui->bank.record_held)return 0;
 return motion_capture(&ui->bank,track,lane,tick,value)==MOTION_OK;
}
int motion_controls_menu_length(MotionControls *ui,uint8_t lane,MotionBars bars){
 if(!ui||lane>=MOTION_LANES)return MOTION_ERR_RANGE;
 return motion_set_length(&ui->bank.lanes[ui->track][lane],bars);
}
int motion_controls_editor_length(MotionControls *ui,uint8_t lane,int delta){
 if(!ui||lane>=MOTION_LANES)return MOTION_ERR_RANGE;
 MotionLane *l=&ui->bank.lanes[ui->track][lane];
 if(!delta)return MOTION_OK;
 /* Encode wheel acceleration conservatively: one standard length increment
  * per signed encoder event, preserving native knob feel as much as possible. */
 return motion_resize_encoder(l,delta);
}
int motion_controls_counter(MotionControls *ui,uint64_t tick,MotionCounter *counter){
 if(!ui||!counter||!ui->bank.record_held)return 0;
 uint8_t tr=(uint8_t)ui->bank.selected_track;
 uint8_t la=ui->bank.selected_lane<0?0:(uint8_t)ui->bank.selected_lane;
 MotionLane *l=&ui->bank.lanes[tr][la];
 uint64_t d=tick>=ui->bank.record_tick?tick-ui->bank.record_tick:0;
 uint64_t b=d/l->ticks_per_bar;
 uint16_t n=l->pending_bars?l->pending_bars:64;
 counter->bar=(uint16_t)(b%n+1);counter->total=n;
 counter->cycles=(uint32_t)(b/n);
 return 1;
}
