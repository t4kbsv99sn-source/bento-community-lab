#pragma once
#include "fx_shared.h"
typedef struct {u32 seq,owner,pad,steps,hits,rotate,velocity,preview,scratch,valid,context[4],status;} Euclid;
enum {EU_OK,EU_STALE,EU_FULL,EU_MEMORY,EU_INVALID,EU_SAME};
int eu_hit(u32 step,u32 steps,u32 hits,u32 rotate);
void eu_capture(Euclid*,void*);
int eu_begin(Euclid*,void*);
int eu_apply(Euclid*,void*);
void eu_return(Euclid*,void*);

int eu_velocity(Euclid*,void*);
