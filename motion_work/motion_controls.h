/* UI-independent control adapter; no fabricated native firmware addresses. */
#ifndef BENTO_MOTION_CONTROLS_H
#define BENTO_MOTION_CONTROLS_H
#include "motion_core.h"
typedef struct {
 MotionBank bank;
 uint8_t track;                 /* currently selected track 0..7 */
 uint8_t lane;                  /* currently selected automation A..D, or 4=All */
 uint8_t reserved[2];
} MotionControls;
typedef struct {uint16_t bar;uint16_t total;uint32_t cycles;} MotionCounter;
void motion_controls_init(MotionControls *ui,uint32_t ticks_per_bar);
int motion_controls_select(MotionControls *ui,uint8_t track,uint8_t lane);
/* Return 1 if RECORD event consumed, 0 for normal native behaviour (pass through). */
int motion_controls_record_button(MotionControls *ui,int down,int shift_held,uint64_t song_tick);
/* Knob movements remain audible as normal; we only tap normalized 0..1000
 * changes when the lane's native A-D routing is already known. */
int motion_controls_parameter(MotionControls *ui,uint8_t track,uint8_t lane,
                              uint64_t song_tick,uint16_t normalized_value);
/* Menu and automation editor: the menu selects duration before recording;
 * the existing Automation pane uses its Length encoder after recording. */
int motion_controls_menu_length(MotionControls *ui,uint8_t lane,MotionBars bars);
int motion_controls_editor_length(MotionControls *ui,uint8_t lane,int encoder_delta);
int motion_controls_counter(MotionControls *ui,uint64_t song_tick,MotionCounter *counter);
#endif
