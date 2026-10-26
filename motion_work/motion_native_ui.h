#ifndef PLAYGROUND_MOTION_NATIVE_UI_H
#define PLAYGROUND_MOTION_NATIVE_UI_H
#define MOTION_STORE_SLOTS 64u
#include "motion_native_node.h"
#include "motion_device_shared.h"
typedef struct {uint32_t handle,key;int32_t base,current,source,amount;uint8_t lane;uint8_t spare[3];} MotionTarget;
typedef struct {
 uint32_t magic,device,view,seq,owner,row,record_node,record_latched;
 uint32_t directory_seq[MOTION_DEVICE_CLIPS];
 uint64_t launch_tick,last_tick;
 uint16_t length,mode;
 uint32_t page,error,project_hold,virtual_handle,virtual_key,virtual_value;
 uint32_t descriptors_saved,descriptors[32];
 uint32_t settings,settings_opening,bulk_seq;int16_t bulk_remainder[4];
 uint16_t gain[4];
 uint32_t target_count,read_base;MotionTarget targets[64];
 uint32_t store_count,store_gen,store_key[MOTION_STORE_SLOTS],store_ptr[MOTION_STORE_SLOTS],store_tag[MOTION_STORE_SLOTS],store_tree[MOTION_STORE_SLOTS]; /* side store; tree = native root holding the clip */
 MotionBank take;
 MotionLane decoded;
 uint32_t indicator; /* P26: record button drawn in the header (0 none, 1 armed, 2 recording) */
 uint8_t wire[28+8*MOTION_EVENTS];
 char hex[2*(28+8*MOTION_EVENTS)+1];
} MotionUi;
__attribute__((used,retain)) MotionUi *motion_ui_state(int create);
__attribute__((used,retain)) void motion_ui_save(void *object,void *params);
__attribute__((used,retain)) void motion_ui_load(void *xml,void *root,void *object);
__attribute__((used,retain)) void motion_ui_publish(uint32_t seq,uint32_t owner,uint32_t row);
__attribute__((used,retain)) int motion_ui_begin(uint32_t seq,uint32_t owner,uint32_t row);
__attribute__((used,retain)) int motion_ui_capture(uint32_t lane,uint16_t value);
__attribute__((used,retain)) void motion_ui_end(void);
__attribute__((used,retain)) void motion_ui_project_end(void);
void *motion_ui_node(uint32_t,int);
int motion_ui_clock(MotionUi *,uint32_t,uint32_t,uint64_t *);
void motion_ui_import(uint32_t,void *,unsigned,MotionLane *);
int motion_ui_capture_source(uint32_t,int32_t,int32_t);
int motion_ui_native_source(MotionUi *,unsigned,int32_t *);
#endif
