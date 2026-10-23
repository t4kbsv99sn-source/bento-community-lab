/* Original Bento composition tool. No borrowed device firmware or preset assets. */
#ifndef BENTO_CHORDS_H
#define BENTO_CHORDS_H
#include <stdint.h>
enum {CH_MAX_VOICES=6, CH_MAX_CHORDS=16, CH_MAX_NOTES=96};
enum {CH_OK,CH_INVALID,CH_RANGE,CH_CAPACITY,CH_CONFLICT,CH_STALE,CH_MEMORY};
enum {CH_MAJOR,CH_MINOR,CH_DIM,CH_AUG,CH_SUS2,CH_SUS4,CH_MAJ7,CH_MIN7,CH_DOM7,CH_ADD9,CH_HALF_DIM,CH_MIN_MAJ7,CH_QUARTAL,CH_DIM7,CH_AUG_MAJ7,CH_TYPES};
enum {CH_SCALE_MAJOR,CH_SCALE_MINOR,CH_SCALE_DORIAN,CH_SCALE_MIXOLYDIAN,CH_SCALE_HARMONIC_MINOR,CH_SCALES};
enum {CH_CLOSE,CH_OPEN,CH_DROP2,CH_VOICINGS};
typedef struct {
 uint32_t start,end; /* Native stored ticks: 960 per sixteenth. */
 int16_t root,type,voicing,inversion,strum; /* strum = signed ticks between voices */
 uint8_t velocity,degree,seventh,quality_override,manual_inversion,pinned;
} Chord;
typedef struct {
 uint32_t start,end;uint16_t pitch,velocity;uint8_t chord,voice;uint16_t reserved;
} ChordNote;
typedef struct {
 uint32_t key,scale,tonic,grid,count,preset,auto_voice;
 Chord chords[CH_MAX_CHORDS];
} Progression;
__attribute__((used,retain)) unsigned chord_preset_count(void);
__attribute__((used,retain)) const char *chord_preset_name(unsigned i);
__attribute__((used,retain)) const char *chord_type_name(unsigned i);
__attribute__((used,retain)) unsigned chord_preset_minor(unsigned i);
__attribute__((used,retain)) int chord_degree_type(unsigned scale,unsigned degree,unsigned seventh);
__attribute__((used,retain)) int chord_notes(const Chord *c,int pitches[CH_MAX_VOICES]);
__attribute__((used,retain)) int chord_generate(Progression *p,unsigned preset,unsigned key,unsigned scale,unsigned tonic,uint32_t start,uint32_t duration);
__attribute__((used,retain)) int chord_reharmonize(Progression *p,unsigned key,unsigned scale);
__attribute__((used,retain)) int chord_voicelead(Progression *p);
__attribute__((used,retain)) int chord_render(const Progression *p,ChordNote *out,unsigned capacity,uint32_t clip_end);
/* Fixed-size, versioned, checked little-endian metadata; no pointers. */
#define CH_SERIAL_BYTES 440
__attribute__((used,retain)) int chord_encode(const Progression *p,uint8_t out[CH_SERIAL_BYTES]);
__attribute__((used,retain)) int chord_decode(Progression *p,const uint8_t *in,unsigned size);
#endif
