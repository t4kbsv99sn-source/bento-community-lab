#include "motion_p19_adapter.h"
#include <stdint.h>

/* 1.6P19 button dispatch uses 0xAF down / 0xB0 up. Native RECORD is 14;
 * binding remains explicit so portable/other-version callers fail closed. */
#define P19_KEY_DOWN 0xafu
#define P19_KEY_UP   0xb0u

int motion_p19_tick(int64_t native_tick,uint64_t *out){
 if(!out||native_tick<0)return MOTION_ERR_RANGE;
 uint64_t t=(uint64_t)native_tick;
 if(t>UINT64_MAX/MOTION_P19_CLOCK_SCALE)return MOTION_ERR_RANGE;
 *out=t*MOTION_P19_CLOCK_SCALE;
 return MOTION_OK;
}
void motion_p19_init(MotionP19Adapter *a,MotionControls *controls){
 if(!a)return;
 a->controls=controls;a->record_button=0;a->button_valid=0;
 a->shift_latched=0;a->transport_valid=0;a->last_position=0;
 a->active_track=0;a->selected_lane=MOTION_LANES;
 a->record_latched=0;a->reserved=0;
}
int motion_p19_bind_record_button(MotionP19Adapter *a,uint8_t index){
 if(!a||!a->controls||index>=16)return MOTION_ERR_RANGE;
 a->record_button=index;a->button_valid=1;return MOTION_OK;
}
int motion_p19_select(MotionP19Adapter *a,uint8_t track,uint8_t lane){
 if(!a||!a->controls||track>=MOTION_TRACKS||lane>MOTION_LANES)return MOTION_ERR_RANGE;
 if(a->controls->bank.record_held)return MOTION_ERR_STATE;
 a->active_track=track;a->selected_lane=lane;
 return motion_controls_select(a->controls,track,lane);
}
void motion_p19_shift(MotionP19Adapter *a,int down){if(a)a->shift_latched=down?1:0;}
int motion_p19_recording(const MotionP19Adapter *a){
 return a&&a->controls&&a->controls->bank.record_held;
}
int motion_p19_transport(MotionP19Adapter *a,int64_t native_tick){
 uint64_t tick;
 if(!a||!a->controls||motion_p19_tick(native_tick,&tick)!=MOTION_OK)return MOTION_ERR_RANGE;
 if(a->transport_valid&&tick<a->last_position){
  if(motion_p19_recording(a)){
   (void)motion_controls_record_button(a->controls,0,0,a->last_position);
  }
  (void)motion_transport_restart(&a->controls->bank,tick);
 }
 a->last_position=tick;a->transport_valid=1;
 return MOTION_OK;
}
int motion_p19_button(MotionP19Adapter *a,uint16_t type,uint8_t button,int64_t native_tick){
 uint64_t tick;
 if(!a||!a->controls||!a->button_valid||button!=a->record_button||
    (type!=P19_KEY_DOWN&&type!=P19_KEY_UP))return 0;
 if(motion_p19_tick(native_tick,&tick)!=MOTION_OK)return 0;
 /* A transport rewind may finish the core take, but must not leak a shifted
  * RECORD event/release into the normal native recorder. */
 if(a->transport_valid&&tick<a->last_position){
  (void)motion_p19_transport(a,native_tick);
 }
 a->last_position=tick;a->transport_valid=1;
 if(type==P19_KEY_DOWN&&a->record_latched)return 1;
 int consumed=motion_controls_record_button(a->controls,type==P19_KEY_DOWN,
                                          a->shift_latched,tick);
 if(type==P19_KEY_DOWN){if(consumed)a->record_latched=1;}
 else if(a->record_latched){a->record_latched=0;return 1;}
 return consumed;
}
int motion_p19_movement(MotionP19Adapter *a, MotionP19Route route,
                        int64_t native_tick,uint16_t value){
 uint64_t tick;
 if(!motion_p19_recording(a)||!route.valid||route.track!=a->active_track||
    route.track>=MOTION_TRACKS||route.lane>=MOTION_LANES||value>1000||
    motion_p19_tick(native_tick,&tick)!=MOTION_OK)return 0;
 if(!a->transport_valid||tick<a->last_position)return 0;
 a->last_position=tick;
 return motion_controls_parameter(a->controls,route.track,route.lane,tick,value);
}
int motion_p19_length(MotionP19Adapter *a,uint8_t lane,int direction){
 if(!a||!a->controls||lane>=MOTION_LANES||motion_p19_recording(a))return MOTION_ERR_STATE;
 return motion_controls_editor_length(a->controls,lane,direction);
}
