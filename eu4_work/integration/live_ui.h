#pragma once
#include "euclidean.h"
#include "live_shared.h"
int live_begin(Euclid*);
EuPad live_value(Euclid*);
int live_edit(Euclid*,u32,int);
void live_save(void*,void*);
void live_load(void*,void*);
void live_finish(void);

int live_position(Euclid*,u32*);

int live_generate(Euclid*,u32,int);

int live_dynamic(Euclid*,u32,int);
