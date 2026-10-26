/* Bento Playground: version-independent motion automation engine.
 * Copyright (C) 2026 Bento Playground contributors.
 * GPL-3.0-or-later, consistent with the Bento Lab source.
 *
 * IMPORTANT: Portable core ONLY. No native Bento firmware hooks are installed.
 * Clock ticks must be monotonically increasing within a transport take.
 * The platform adapter must supply native transport ticks and map values to A-D.
 */
#ifndef BENTO_MOTION_CORE_H
#define BENTO_MOTION_CORE_H
#include <stdint.h>
#include <stddef.h>

#define MOTION_TRACKS 8u
#define MOTION_LANES 4u
#define MOTION_EVENTS 256u
/* Native note-position domain: 960 ticks per 1/16th; recorder quantizes
 * one ninety-sixth of that step. Actual clock conversion belongs to adapter. */
#define MOTION_TICKS_PER_STEP 960u
#define MOTION_QUANTUM (MOTION_TICKS_PER_STEP / 96u)
#define MOTION_DEFAULT_TICKS_PER_BAR (MOTION_TICKS_PER_STEP * 16u)
#define MOTION_FORMAT_VERSION 1u

typedef enum {
  MOTION_OK=0, MOTION_ERR_RANGE=-1, MOTION_ERR_STATE=-2,
  MOTION_ERR_FULL=-3, MOTION_ERR_FORMAT=-4
} MotionResult;
typedef enum {MOTION_OVERDUB=0, MOTION_REPLACE=1} MotionWriteMode;
typedef enum {MOTION_STEP=0, MOTION_LINEAR=1} MotionInterpolation;
typedef enum {MOTION_AUTO=0, MOTION_4=4, MOTION_8=8,
              MOTION_16=16, MOTION_32=32, MOTION_64=64} MotionBars;

typedef struct {uint32_t tick;uint16_t value;uint16_t flags;} MotionPoint;
typedef struct {
  MotionPoint points[MOTION_EVENTS];
  uint32_t ticks_per_bar;   /* preserve actual musical meter from native transport */
  uint32_t max_tick;        /* maximum selected length; points outside current remain recoverable */
  uint64_t origin_tick;
  uint64_t record_tick;
  uint32_t captured;       /* last capture phase; avoids redundant events */
  uint16_t count;
  uint16_t length_bars;
  uint16_t pending_bars;
  uint16_t previous_value;
  uint8_t active;
  uint8_t recording;
  uint8_t replace_pending;
  uint8_t write_mode;
  uint8_t interpolation;
  uint8_t have_previous;
  uint8_t reserved[2];
} MotionLane;
typedef struct {
  MotionLane lanes[MOTION_TRACKS][MOTION_LANES];
  uint64_t record_tick;
  int8_t selected_track, selected_lane;
  uint8_t record_held;
  uint8_t reserved;
} MotionBank;

void motion_lane_init(MotionLane *lane, uint32_t ticks_per_bar);
void motion_bank_init(MotionBank *bank, uint32_t ticks_per_bar);
int motion_set_length(MotionLane *lane, MotionBars bars);
int motion_set_mode(MotionLane *lane, MotionWriteMode mode);
int motion_set_interpolation(MotionLane *lane, MotionInterpolation interpolation);
/* Shift+REC key-down starts only after modifier held. Key-up always stops,
 * even if Shift was released earlier. lane=MOTION_LANES permits up to four
 * A-D lanes on the selected track in the same gesture. */
int motion_press_record(MotionBank *bank, uint8_t shift_held,
                        uint8_t track, uint8_t lane, uint64_t song_tick);
int motion_release_record(MotionBank *bank, uint64_t song_tick);
/* Call on movements only, after the native adapter has mapped the moved knob
 * to an A-D target. In all-lane mode, the first movement arms its lane. */
int motion_capture(MotionBank *bank, uint8_t track, uint8_t lane,
                   uint64_t song_tick, uint16_t value);
/* 0..1000 normalized target value, interpolate or step, sustain last value
 * until the independent loop wraps. 0 means no automation is present. */
int motion_evaluate(const MotionLane *lane, uint64_t song_tick, uint16_t *value);
int motion_resize_encoder(MotionLane *lane, int direction);
int motion_clear_lane(MotionLane *lane);
/* Transport start/seek/discontinuity. Rebase every active lane's phase to
 * the new global song origin; do not call at a musical clip-loop boundary.
 * The platform must distinguish global transport rewinds from clip wraps. */
int motion_transport_restart(MotionBank *bank, uint64_t song_tick);
/* No allocation, safe for host regression tests; project adapter must encode
 * these versioned lane records and retain old stock XML project fields. */
size_t motion_encoded_size(const MotionLane *lane);
int motion_encode(const MotionLane *lane, uint8_t *dst, size_t capacity);
int motion_decode(MotionLane *lane, const uint8_t *src, size_t length);
#endif
