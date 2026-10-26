/* P10 (owner: "a 909 type snare"). The TR-909 snare structure: two shell
 * oscillators (about 1 : 1.62, near-sine) with a short downward pitch bend at
 * the hit and their own decays, plus white noise through a high-pass and a
 * tone low-pass with its own envelope ("snappy"). Own code, GPL like the
 * project. Cheap on purpose: two phase accumulators with a polynomial sine,
 * one xorshift, one one-pole high-pass, one Chamberlin low-pass, and one-pole
 * envelopes; every coefficient is computed once per block. */
#pragma once
#include <math.h>
namespace bento {
class Snare909 {
 public:
  struct BlockCoefficients {float d1,d2,k1,k2,kp,kn,hp,f,q,gs,gn;};
  void Init(float sample_rate){sr_=sample_rate;rng_=0x9e3779b9u;ph1_=ph2_=.25f;a1_=a2_=pe_=na_=0;hp_=hx_=low_=band_=0;freq_=180;decay_=.45f;tone_=.5f;accent_=.65f;snappy_=.7f;}
  void SetFreq(float f){freq_=f;}      /* shell 1 in Hz (shell 2 = 1.62 x) */
  void SetDecay(float d){decay_=d;}    /* 0..1: shells 60..170 ms, noise 50..420 ms */
  void SetTone(float t){tone_=t;}      /* 0..1: noise low-pass 2.2..12 kHz */
  void SetAccent(float a){accent_=a;}  /* 0..1: level and attack */
  void SetSnappy(float s){snappy_=s;}  /* 0..1: noise against shells */
  void Trig(){ph1_=ph2_=.25f;a1_=1.f;a2_=1.f;pe_=1.f;na_=1.f;}
  BlockCoefficients PrepareBlock() const{
   BlockCoefficients c;float inv=1.f/sr_;
   c.d1=freq_*inv;c.d2=freq_*1.62f*inv;
   float t1=.06f+.11f*decay_,t2=t1*.55f,tn=.05f+.37f*decay_*decay_;
   c.k1=powf(2.f,-1.4427f/(t1*sr_));c.k2=powf(2.f,-1.4427f/(t2*sr_));
   c.kp=powf(2.f,-1.4427f/(.004f*sr_));c.kn=powf(2.f,-1.4427f/(tn*sr_));
   c.hp=powf(2.f,-6.2832f*900.f*inv); /* one-pole high-pass at ~900 Hz */
   float fc=2200.f*powf(2.f,tone_*2.45f);if(fc>.4f*sr_)fc=.4f*sr_;
   c.f=2.f*sinf(3.14159265f*fc*inv);c.q=1.1f;
   float acc=.55f+.45f*accent_;c.gs=acc*(1.f-.35f*snappy_);c.gn=acc*snappy_*.8f;
   return c;}
  float ProcessPrepared(const BlockCoefficients &c){
   pe_*=c.kp;float bend=1.f+.45f*pe_;
   ph1_+=c.d1*bend;if(ph1_>=1.f)ph1_-=1.f;ph2_+=c.d2*bend;if(ph2_>=1.f)ph2_-=1.f;
   float shell=sine(ph1_)*a1_*.8f+sine(ph2_)*a2_*.45f;a1_*=c.k1;a2_*=c.k2;
   unsigned x=rng_;x^=x<<13;x^=x>>17;x^=x<<5;rng_=x;
   float n=(float)(int)x*(1.f/2147483648.f);
   hp_=c.hp*(hp_+n-hx_);hx_=n;
   low_+=c.f*band_;float high=hp_-low_-c.q*band_;band_+=c.f*high;
   float noise=low_*na_;na_*=c.kn;
   float y=shell*c.gs+noise*c.gn;if(y>3.f)y=3.f;if(y<-3.f)y=-3.f;
   return y*(27.f+y*y)/(27.f+9.f*y*y); /* soft limit: loud settings round off instead of clipping */
  }
 private:
  static float sine(float ph){float x=ph*2.f-1.f;float ax=x<0?-x:x;float y=4.f*x*(1.f-ax);float ay=y<0?-y:y;return .225f*(y*ay-y)+y;}
  float sr_,ph1_,ph2_,a1_,a2_,pe_,na_,hp_,hx_,low_,band_,freq_,decay_,tone_,accent_,snappy_;
  unsigned rng_;
};
}
