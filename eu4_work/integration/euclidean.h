#pragma once
#include "fx_shared.h"
/* preview: drum views keep the legacy EU1 preview count (1..8). CH3 melodic rows
   set EU_MEL|gate<<8|pitch (gate in quarter steps 1..64). Size is unchanged
   because Ui fills its reservation exactly. */
typedef struct {u32 seq,owner,pad,steps,hits,rotate,velocity,preview,scratch,valid,context[4],status;} Euclid;
#define EU_MEL 0x10000u
static inline int eu_mel(const Euclid *e){return (e->preview&EU_MEL)!=0;}
static inline u32 eu_mel_pitch(const Euclid *e){return e->preview&127u;}
static inline u32 eu_mel_gate(const Euclid *e){u32 g=(e->preview>>8)&127u;return g<1?4:g>64?64:g;}
enum {EU_OK,EU_STALE,EU_FULL,EU_MEMORY,EU_INVALID,EU_SAME,EU_USED};
int eu_hit(u32 step,u32 steps,u32 hits,u32 rotate);
void eu_capture(Euclid*,void*);
int eu_begin(Euclid*,void*);
int eu_apply(Euclid*,void*);
void eu_return(Euclid*,void*);

int eu_velocity(Euclid*,void*);
int eu_repitch(Euclid*,void*,u32);
int eu_gate_notes(Euclid*,void*);
int eu_pitched_type(u32);
