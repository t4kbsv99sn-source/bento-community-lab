#ifndef BENTO_CHORD_AUDITION_H
#define BENTO_CHORD_AUDITION_H
#include "chords.h"
typedef void (*ChordMidi)(void *context,unsigned pitch,unsigned velocity);
typedef struct {
 uint8_t references[128],held[16],count[16],pitch[16][CH_MAX_VOICES];
} ChordAudition;
/* Root pads audition only; there is no sequence-write call in this module.
   The caller supplies Bento's verified note-on/note-off routing later. */
__attribute__((used,retain)) int chord_pad_on(ChordAudition*,unsigned pad,const Chord*,ChordMidi on,ChordMidi off,void*);
__attribute__((used,retain)) void chord_pad_off(ChordAudition*,unsigned pad,ChordMidi off,void*);
__attribute__((used,retain)) void chord_audition_stop(ChordAudition*,ChordMidi off,void*);
#endif
