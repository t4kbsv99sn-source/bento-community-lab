#ifndef BENTO_CHORD_NATIVE_INSERT_H
#define BENTO_CHORD_NATIVE_INSERT_H
#include "chords.h"
typedef struct {
 uint32_t seq,owner,clip_end,scratch;
 uint32_t note_ids[CH_MAX_NOTES],note_count;
} ChordNative;
/* Offline native adapter proof. Not hooked into the delivered firmware yet.
   Only new inserts; existing-chord update/group selection needs the UI owner. */
__attribute__((used,retain)) int chord_native_insert(ChordNative *state,void *model,const Progression *p);
#endif
