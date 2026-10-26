/* CH12: hand clap. Noise through a resonant band-pass, three short bursts then
 * a tail (the classic analog clap shape). Own code, GPL like the project.
 * Cheap on purpose: one xorshift, one Chamberlin band-pass, two one-pole
 * envelopes per sample; every coefficient is computed once per block. */
#pragma once
#include <math.h> /* sinf/powf/sqrtf: the project's own, in kick.cpp */
namespace bento {
class Clap {
 public:
  struct BlockCoefficients {float f,q,burst_decay,tail_decay,bright,gain;unsigned spacing;};
  void Init(float sample_rate){sr_=sample_rate;rng_=0x2545f491u;low_=band_=0;burst_=3;left_=0;env_=0;tail_=0;tune_=.4f;decay_=.4f;tone_=.5f;accent_=.6f;spread_=.4f;}
  void SetTune(float t){tune_=t;}      /* 0..1: band centre 400 Hz..3.2 kHz */
  void SetDecay(float d){decay_=d;}    /* 0..1: tail 40 ms..1 s */
  void SetTone(float t){tone_=t;}      /* 0..1: dark/resonant .. bright/open */
  void SetAccent(float a){accent_=a;}  /* 0..1: level and snap */
  void SetSpread(float s){spread_=s;}  /* 0..1: burst spacing 4..22 ms */
  void Trig(){burst_=0;left_=0;env_=1;tail_=0;}
  BlockCoefficients PrepareBlock() const{
   BlockCoefficients c;float fc=400.f*powf(2.f,tune_*3.f);c.f=2.f*sinf(3.14159265f*fc/sr_);
   c.q=.3f+tone_*.9f;c.bright=tone_*.6f;
   c.spacing=(unsigned)(sr_*(.004f+spread_*.018f));if(c.spacing<16)c.spacing=16;
   c.burst_decay=powf(2.f,-5.f/(float)c.spacing);
   float n=sr_*.04f*powf(25.f,decay_);c.tail_decay=powf(2.f,-10.f/n);
   c.gain=(.35f+accent_*.65f)*1.1f*sqrtf(c.q/c.f)/((1.f+tone_)*(1.f+tone_));return c;}
  float ProcessPrepared(const BlockCoefficients &c){
   unsigned x=rng_;x^=x<<13;x^=x>>17;x^=x<<5;rng_=x;
   float noise=(float)(int)x*(1.f/2147483648.f);
   float high=noise-low_-c.q*band_;band_+=c.f*high;low_+=c.f*band_;
   float sig=band_+c.bright*high;
   float amp;
   if(burst_<3){
    env_*=c.burst_decay;amp=env_;
    if(++left_>=c.spacing){left_=0;burst_++;env_=1;if(burst_==3)tail_=1;}
   }else{tail_*=c.tail_decay;amp=tail_;}
   return sig*amp*c.gain;
  }
 private:
  float sr_,low_,band_,env_,tail_,tune_,decay_,tone_,accent_,spread_;
  unsigned rng_,burst_,left_;
};
}
