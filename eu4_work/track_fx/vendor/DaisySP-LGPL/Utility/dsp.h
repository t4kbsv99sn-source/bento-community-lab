/* Freestanding subset of DaisySP Utility/dsp.h, MIT; see DaisySP-MIT-LICENSE.
 * The logarithm polynomial and pow10f are retained from pinned upstream.
 * Guard zero before its logarithm. */
#pragma once
#include <math.h>
#include <stddef.h>
#define TWOPI_F 6.2831853071795864769f
namespace daisysp {
inline float fmax(float a,float b){return a>b?a:b;}
inline float pow10f(float f){return expf(2.302585092994046f*f);}
inline float fastlog2f(float f){
    float frac;int exp;
    frac=frexpf(fabsf(f)>1e-20f?fabsf(f):1e-20f,&exp);
    f=1.23149591368684f;f*=frac;f+=-4.11852516267426f;
    f*=frac;f+=6.02197014179219f;f*=frac;f+=-3.13396450166353f;
    return f+exp;
}
inline float fastlog10f(float f){return fastlog2f(f)*0.3010299956639812f;}
// Verbatim DaisySP helpers, extracted from pichenettes/stmlib upstream.
inline float SoftLimit(float x){return x*(27.f+x*x)/(27.f+9.f*x*x);}
inline float SoftClip(float x){if(x < -3.0f)return -1.0f;else if(x > 3.0f)return 1.0f;else return SoftLimit(x);}
}
