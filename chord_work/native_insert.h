#ifndef BENTO_CHORD_NATIVE_INSERT_H
#define BENTO_CHORD_NATIVE_INSERT_H
#include "chords.h"
typedef struct {
 uint32_t seq,owner,clip_end,scratch;
 uint32_t note_ids[CH_MAX_NOTES],note_count;
 uint32_t no_snapshot; /* P24: caller already took the gesture's single Undo snapshot */
} ChordNative;
/* Offline native adapter proof. Not hooked into the delivered firmware yet.
   Only new inserts; existing-chord update/group selection needs the UI owner. */
__attribute__((used,retain)) int chord_native_insert(ChordNative *state,void *model,const Progression *p);
__attribute__((used,retain)) int chord_native_remove(ChordNative *state,void *model);
__attribute__((used,retain)) int chord_native_starts(ChordNative*,void*,uint32_t*,unsigned);
__attribute__((used,retain)) int chord_native_adopt(ChordNative*,void*,uint32_t,int*,unsigned*,uint32_t*,unsigned*);
typedef unsigned (*ChordHits)(unsigned rhythm,uint32_t len,uint32_t *at,uint32_t *dur);
__attribute__((used,retain)) int chord_native_rhythmize(ChordNative*,void*,uint32_t,unsigned,ChordHits);
__attribute__((used,retain)) int chord_native_find(ChordNative*,void*,uint32_t,uint32_t*);
__attribute__((used,retain)) int chord_native_clear_for(ChordNative*,void*,const Progression*);
/* P24 (owner 5a): move every pitched note starting at/after `from` that is not
   part of the current chord by `delta` ticks, keeping IDs and locks. */
__attribute__((used,retain)) int chord_native_shift(ChordNative*,void*,uint32_t from,int32_t delta);
/* P24 (owner 7): delete exactly the current chord's notes. */
__attribute__((used,retain)) int chord_native_delete(ChordNative*,void*);
#endif
