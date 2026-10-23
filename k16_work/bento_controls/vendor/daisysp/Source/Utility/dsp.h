/* Freestanding subset of DaisySP Utility/dsp.h.
 * Copyright (c) 2020 Electrosmith, Corp, Emilie Gillet. MIT: see ../../../LICENSE.
 * Bento adapter: omit desktop C++ library dependencies; keep used helpers. */
#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#define PI_F 3.1415927410125732421875f
#define TWOPI_F (2.0f * PI_F)
namespace daisysp {
static constexpr float kRandFrac=1.f/(float)RAND_MAX;
static constexpr float kOneTwelfth=1.f/12.f;
inline float fmax(float a,float b){return a>b?a:b;}
inline float fmin(float a,float b){return a<b?a:b;}
inline float fclamp(float a,float lo,float hi){return fmin(fmax(a,lo),hi);}
inline void fonepole(float &out,float in,float coeff){out+=coeff*(in-out);}
}
