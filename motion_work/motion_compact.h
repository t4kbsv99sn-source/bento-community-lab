/* Half-size, bounded playback snapshot for the second Bento core.
 * Not an M4/M7 mailbox by itself: the caller must separately provide verified
 * MPU permissions, cache ownership, barriers and versioned publication.
 */
#ifndef BENTO_MOTION_COMPACT_H
#define BENTO_MOTION_COMPACT_H
#include "motion_core.h"
/* tick/10 occupies 20 bits (even a 64-bar / 65535 ticks-per-bar timeline
 * fits), value 0..1000 occupies 10 bits, and point flags 0..3 occupy 2 bits. */
#define MOTION_COMPACT_TICK_BITS 20u
#define MOTION_COMPACT_TICK_MAX ((1u<<MOTION_COMPACT_TICK_BITS)-1u)
typedef struct {
 uint32_t ticks[MOTION_EVENTS];
 uint32_t ticks_per_bar;
 uint64_t origin_tick;
 uint16_t count,length_bars;
 uint8_t active,interpolation;
 uint8_t reserved[2];
} MotionCompactLane;
int motion_compact_pack(MotionCompactLane *dst,const MotionLane *src);
int motion_compact_evaluate(const MotionCompactLane *lane,uint64_t song_tick,uint16_t *out);
#endif
