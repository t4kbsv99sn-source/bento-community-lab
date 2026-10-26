#ifndef PLAYGROUND_MOTION_CLIPS_H
#define PLAYGROUND_MOTION_CLIPS_H
#include "motion_core.h"
/* Native clips are identified by track node handle and row, never by the
 * currently selected track number. Storage belongs to the caller's checked
 * allocation; this layer neither reserves RAM nor touches firmware addresses. */
#define MOTION_CLIP_ROWS 16u
typedef struct {
 uint32_t owner;
 uint8_t row, initialized, reserved[2];
 MotionLane lanes[MOTION_LANES];
} MotionClip;
typedef struct {
 MotionBank take;
 MotionClip *recording_clip;
 uint32_t owner;
 uint8_t row, selected, reserved[2];
} MotionClipRecorder;
void motion_clip_init(MotionClip *,uint32_t owner,uint8_t row,uint32_t bar_ticks);
void motion_clip_recorder_init(MotionClipRecorder *,uint32_t bar_ticks);
int motion_clip_begin(MotionClipRecorder *,MotionClip *,uint64_t tick);
int motion_clip_capture(MotionClipRecorder *,uint8_t lane,uint64_t tick,uint16_t value);
int motion_clip_end(MotionClipRecorder *,uint64_t tick);
int motion_clip_matches(const MotionClip *,uint32_t owner,uint8_t row);
/* Clip launch reanchors this clip only. Musical loop wraps do not call it. */
int motion_clip_launch(MotionClip *,uint64_t tick);
#endif
