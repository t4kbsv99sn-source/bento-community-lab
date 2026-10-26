#ifndef PLAYGROUND_MOTION_NATIVE_NODE_H
#define PLAYGROUND_MOTION_NATIVE_NODE_H
#include "motion_core.h"
/* P22b (owner: the R8 build, which enlarged every native type-5 node to hold
 * this data, restarted in a loop on the device). Motion data now lives in a
 * side store keyed by the clip's sequence handle; native nodes, their
 * allocation and copies are untouched. Native Undo/copy do not carry motion. */
#define MOTION_NATIVE_PREFIX 0x820u
#define MOTION_NODE_MAGIC 0x314e4d50u
typedef struct {
 uint32_t magic,version;
 MotionLane lanes[MOTION_LANES];
 uint16_t gain[MOTION_LANES];
} MotionNodeExtension;
#define MOTION_NATIVE_NODE_BYTES (MOTION_NATIVE_PREFIX+sizeof(MotionNodeExtension))
_Static_assert(sizeof(MotionLane)==2096,"native clone-size ABI");
MotionNodeExtension *motion_store(uint32_t seq,int create);
void motion_store_loaded(uint32_t seq);
void motion_store_sweep(void);
#endif
