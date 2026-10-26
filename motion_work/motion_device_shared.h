#ifndef PLAYGROUND_MOTION_DEVICE_SHARED_H
#define PLAYGROUND_MOTION_DEVICE_SHARED_H
#include "motion_compact.h"
#define MOTION_DEVICE_MAGIC 0x31444d50u
#define MOTION_DEVICE_CLIPS 128u
#define MOTION_DEVICE_TRACKS 8u
#define MOTION_DEVICE_EU_POINTER_WORD 5u /* EuBank.reserved[1], M4 owned */
typedef struct {
 uint32_t serial,owner,row,epoch,reserved[4];
 MotionCompactLane lanes[MOTION_LANES];
} MotionDeviceClip;
/* First two cache lines are M7-written clock/status publication. M4 reads
 * only under serial. The remainder is an M7-private stable snapshot cache. */
typedef struct {
 uint32_t serial,sequence,owner,row;
 uint64_t native_tick,launch_tick;
 uint32_t valid,restart,epoch,clip_serial,clip_pointer,active_cache,reserved[2];
 MotionCompactLane lanes[2][MOTION_LANES];
} MotionDeviceRuntime;
typedef struct {
 uint32_t magic,bytes,epoch,count,serial,reserved[3];
 uint32_t clips[MOTION_DEVICE_CLIPS];
 MotionDeviceRuntime runtime[MOTION_DEVICE_TRACKS];
} MotionDevice;
#if defined(__cplusplus)
static_assert(sizeof(MotionDeviceClip)%32==0,"clip cache boundary");
static_assert(sizeof(MotionDeviceRuntime)%32==0,"runtime cache boundary");
static_assert(sizeof(MotionDevice)%32==0,"bank cache boundary");
#else
_Static_assert(sizeof(MotionDeviceClip)%32==0,"clip cache boundary");
_Static_assert(sizeof(MotionDeviceRuntime)%32==0,"runtime cache boundary");
_Static_assert(sizeof(MotionDevice)%32==0,"bank cache boundary");
#endif
#endif
