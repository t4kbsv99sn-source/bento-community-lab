/* Test-link freestanding single-precision math. No native Bento symbols assumed.
 * sin/pow polynomial follows our K8 freestanding adapter; input domains guarded
 * by track settings. This is not an installation address or firmware hook. */
#include <stdint.h>
#include "math.h"
extern "C" float fabsf(float x){return x<0?-x:x;}
extern "C" float fmaxf(float a,float b){return a>b?a:b;}
extern "C" float sqrtf(float x){float y;__asm__("vsqrt.f32 %0,%1":"=t"(y):"t"(x));return y;}
extern "C" float sinf(float x){
 const float pi=3.14159265358979323846f,twopi=6.2831853071795864769f;
 int n=(int)(x/twopi);x-=n*twopi;if(x>pi)x-=twopi;if(x<-pi)x+=twopi;
 if(x>pi*.5f)x=pi-x;else if(x<-pi*.5f)x=-pi-x;
 float q=x*x;return x*(1+q*(-.1666666666667f+q*(.0083333333333f+q*(-.0001984126984f+q*(.0000027557319f+q*(-.0000000250521f))))));
}
extern "C" float cosf(float x){return sinf(x+1.5707963267948966f);}
static float exp2(float x){
 if(x<-126)return 0;if(x>126)x=126;
 int n=(int)x;if(float(n)>x)n--;float f=(x-float(n))*.6931471805599453f;
 float y=1+f*(1+f*(.5f+f*(.1666666666667f+f*(.0416666666667f+f*(.0083333333333f+f*(.0013888888889f+f*.0001984126984f))))));
 union{uint32_t u;float f;}s={uint32_t(n+127)<<23};return y*s.f;
}
extern "C" float expf(float x){return exp2(x*1.4426950408889634f);}
extern "C" float powf(float a,float b){
 if(a==1)return 1;if(a<=0)return 0;
 union{float f;uint32_t u;}v={a};int e=int((v.u>>23)&255)-127;v.u=(v.u&0x7fffff)|0x3f800000;
 float z=(v.f-1)/(v.f+1),q=z*z;
 float l=2*z*(1+q*(1.f/3+q*(1.f/5+q*(1.f/7+q*(1.f/9+q*(1.f/11+q/13))))));
 return exp2(b*(float(e)+l*1.4426950408889634f));
}
extern "C" float frexpf(float f,int *e){
 union{float f;uint32_t u;}v={f};
 if((v.u&0x7fffffff)==0){*e=0;return f;}
 int adjust=0;if((v.u&0x7f800000)==0){v.f*=16777216.f;adjust=-24;}
 *e=int((v.u>>23)&255)-126+adjust;v.u=(v.u&0x807fffff)|0x3f000000;return v.f;
}
extern "C" void *memcpy(void *d,const void *s,unsigned n){auto a=(unsigned char*)d;auto b=(const unsigned char*)s;for(unsigned i=0;i<n;i++)a[i]=b[i];return d;}
extern "C" void *memset(void *d,int v,unsigned n){auto a=(unsigned char*)d;for(unsigned i=0;i<n;i++)a[i]=(unsigned char)v;return d;}
extern "C" void __aeabi_memcpy(void *d,const void *s,unsigned n){memcpy(d,s,n);}
extern "C" void __aeabi_memclr(void *d,unsigned n){memset(d,0,n);}
extern "C" void __aeabi_memclr4(void *d,unsigned n){memset(d,0,n);}
