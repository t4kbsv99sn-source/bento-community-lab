/* Bento Playground motion input/timeline seam for 1.6P19.
 * This module does not claim native firmware event hooks are installed.
 * Only signed note/transport ticks and identified parameter mappings enter here.
 */
#ifndef BENTO_MOTION_P19_ADAPTER_H
#define BENTO_MOTION_P19_ADAPTER_H
#include "motion_controls.h"
#include <stdint.h>

/* P19 native note domain: 960 ticks/quarter = 240 ticks/16th.
 * Portable motion core: 960 ticks/16th. Multiply native ticks by four,
 * using checked conversion rather than misreading a four-beat bar as one beat.
 */
#define MOTION_P19_NATIVE_TICKS_PER_QUARTER 960u
#define MOTION_P19_CLOCK_SCALE 4u
/* Verified stock M7 button scanner: AF(index 14) at 0808D342 and
 * RECORD transport 91 at 0808D820; release is B0(index 14). */
#define MOTION_P19_RECORD_BUTTON 14u

/* Parameter route binding supplied by the actual A-D editor; no fake mapping
 * from arbitrary encoder to an automation lane. */
typedef struct {
  uint8_t track;                  /* 0..7 */
  uint8_t lane;                   /* 0..3 */
  uint8_t valid;                  /* native routing confirmed */
  uint8_t reserved;
} MotionP19Route;
typedef struct {
  MotionControls *controls;       /* storage owned by P19 platform */
  uint8_t record_button;         /* MUST be established from controller trace */
  uint8_t button_valid;          /* refuse unknown button index */
  uint8_t shift_latched;         /* physical PROJ depressed */
  uint8_t transport_valid;
  uint64_t last_position;
  uint8_t active_track;           /* selected native track 0..7 */
  uint8_t selected_lane;          /* 0..3, or 4=all mapped A-D */
  uint8_t record_latched;         /* consume through release across rewinds */
  uint8_t reserved;
} MotionP19Adapter;

/* Refuse negative transport positions and conversion overflow. */
int motion_p19_tick(int64_t native_tick,uint64_t *motion_tick);
void motion_p19_init(MotionP19Adapter *adapter, MotionControls *controls);
int motion_p19_bind_record_button(MotionP19Adapter *adapter,uint8_t index);
int motion_p19_select(MotionP19Adapter *adapter,uint8_t track,uint8_t lane);
/* Return 1 only when native button event was consumed. Other events pass. */
int motion_p19_button(MotionP19Adapter *adapter,uint16_t event_type,
                      uint8_t button,int64_t native_tick);
/* Physical PROJ key-down/up from existing verified modifier handler. */
void motion_p19_shift(MotionP19Adapter *adapter,int down);
/* Encoder taps only when native routing resolves A-D; movement remains native. */
int motion_p19_movement(MotionP19Adapter *adapter, MotionP19Route route,
                        int64_t native_tick,uint16_t value);
/* Helpers for the native Automation pane to use the core's existing Length
 * behaviour without changing the musical clip length or rescaling events. */
int motion_p19_length(MotionP19Adapter *adapter,uint8_t lane,int direction);
/* Called on global song-clock observations; native clip wraps are NOT
 * discontinuities, so the platform must pass a global transport position.
 * A rewind safely terminates recording and starts fresh playback phase. */
int motion_p19_transport(MotionP19Adapter *adapter,int64_t native_tick);
int motion_p19_recording(const MotionP19Adapter *adapter);

#endif
