/* S1 subtractive voice. Project code GPL-3.0-or-later.
 * The two nonlinear, double-sampled SVFs are DaisySP (MIT); see vendor license.
 * Oscillators use fractional two-sample BLEP events, including slave resets.
 * Two internal samples per output sample. Native Bento owns the amp ADSR/gate.
 */
#pragma once
#include "vendor/daisysp/Source/Filters/svf.h"
#include <math.h>
namespace bento {
class Subtractive {
 public:
  struct Block {
    float inc, slave, blend, width, fat, cutoff, amount, decay, sync, res;
    float damping_a,damping_b;
    float slave_gain,sub_gain,mix_gain,drive,res_gain,slave_base;
  };
  void Init(float sample_rate) {
    rate_=sample_rate*2.f; p_=0; q_=.173f; sub_=.31f; env_=1.f;
    delayed_=dc_in_=dc_out_=0; clock_=0;
    for(unsigned i=0;i<7;i++)history_[i]=0;
    for(unsigned i=0;i<8;i++)smooth_[i]=-1;
    a_.Init(rate_); b_.Init(rate_); a_.SetDrive(.6f); b_.SetDrive(.25f);
  }
  /* Values: Shape, Osc2 interval, Fat, Cutoff, Resonance, Env amount,
   * Env decay, Sync (0 off; 1..100 adds 0..48 semitones of envelope sweep).
   * Incoming native pitch is relative to the carrier's root note.
   */
  Block Prepare(const float *v,float ratio,unsigned frames) {
    float alpha=1.f-powf(.5f,(float)frames/(rate_*.0025f));
    for(unsigned i=0;i<8;i++) {
      float x=bound(v[i],0,100);
      if(smooth_[i]<0)smooth_[i]=x;
      else smooth_[i]+=(x-smooth_[i])*alpha;
    }
    float shape=smooth_[0]*.01f, fat=smooth_[2]*.01f;
    float hz=130.81278265f*bound(ratio,.015625f,64.f);
    Block c;
    c.inc=bound(hz/rate_,.000001f,.20f);
    c.blend=bound(shape*2.f,0,1); c.width=.5f-bound(shape-.5f,0,.5f)*.84f;
    float interval=(float)((int)(smooth_[1]*.48f+.5f)-24);
    c.slave=powf(2.f,(interval+fat*.18f)/12.f);
    c.fat=fat; c.cutoff=35.f*powf(2.f,smooth_[3]*.085f);
    c.amount=smooth_[5]*.08f;
    float seconds=.012f*powf(2.f,smooth_[6]*.10f);
    c.decay=powf(.001f,1.f/(seconds*rate_));
    /* Keep OFF exact; smoothing a switch otherwise leaves it stuck on. */
    c.sync=v[7]<=0?0:1.f+bound(smooth_[7]-1,0,99)*(4.f/99.f);
    c.res=smooth_[4]*.01f;
    a_.SetRes(.12f+.78f*c.res); b_.SetRes(.08f);
    c.damping_a=2.f*(1.f-powf(.12f+.78f*c.res,.25f));
    c.damping_b=2.f*(1.f-powf(.08f,.25f));
    c.slave_gain=.58f+c.fat*.12f; c.sub_gain=c.fat*.32f;
    c.mix_gain=.65f/(1.f+c.slave_gain+c.sub_gain);
    c.drive=1.3f+c.fat*.8f; c.res_gain=1.f+c.res*.45f;
    c.slave_base=c.inc*c.slave;
    return c;
  }
  float Process(const Block &c) {
    for(unsigned k=0;k<2;k++) {
      env_*=c.decay;
      if((clock_++&15u)==0) {
        float cutoff=bound(c.cutoff*powf(2.f,c.amount*env_),25.f,16000.f);
        a_.SetFreqPrepared(cutoff,c.damping_a); b_.SetFreqPrepared(cutoff,c.damping_b);
      }
      float old=p_, master_next=p_+c.inc;
      bool reset=master_next>=1.f;
      float edge=reset?(1.f-old)/c.inc:1.f;
      float previous=0,current=0;
      advance(p_,c.inc,c,0,1,1,previous,current);
      float slave_inc=bound(c.slave_base*(c.sync?powf(2.f,(c.sync-1.f)*env_):1.f),.000001f,.45f);
      float slave_gain=c.slave_gain;
      if(c.sync && reset) {
        advance(q_,slave_inc,c,0,edge,slave_gain,previous,current);
        float jump=(wave(0,c)-wave(q_,c))*slave_gain;
        event(edge,jump,previous,current); q_=0;
        advance(q_,slave_inc,c,edge,1-edge,slave_gain,previous,current);
      } else advance(q_,slave_inc,c,0,1,slave_gain,previous,current);
      sub_+=c.inc*.5f; if(sub_>=1)sub_-=1;
      float triangle=4.f*abs(sub_-.5f)-1.f;
      float raw=wave(p_,c)+slave_gain*wave(q_,c)+triangle*c.fat*.32f;
      float x=(delayed_+previous)*c.mix_gain;
      delayed_=raw+current;
      /* Drive before the nonlinear filter; Fat also adds a little drive. */
      x=soft(x*c.drive);
      x=b_.ProcessLow(a_.ProcessLow(x))*c.res_gain;
      /* Remove asymmetric pulse/filter DC without touching the native envelope. */
      float y=x-dc_in_+.9987f*dc_out_; dc_in_=x; dc_out_=y;
      history_[0]=history_[1]; history_[1]=history_[2]; history_[2]=history_[3];
      history_[3]=history_[4]; history_[4]=history_[5]; history_[5]=history_[6];
      history_[6]=y;
    }
    /* Seven-tap halfband lowpass before 2:1 decimation (unity DC gain). */
    float y=-.04563588f*(history_[0]+history_[6])
       +.28382934f*(history_[2]+history_[4])
       +.52361308f*history_[3];
    /* Soft output levelling keeps high resonance from hard-clipping downstream.
     * Leave numerical failures visible to host tests/the render finite guard. */
    if(!(y==y) || abs(y)>1000.f)return y;
    return soft(y)*.85f;
  }
 private:
  daisysp::Svf a_,b_;
  float rate_,p_,q_,sub_,env_,delayed_,dc_in_,dc_out_;
  float smooth_[8],history_[7];
  unsigned clock_;
  static float abs(float x){return x<0?-x:x;}
  static float bound(float x,float lo,float hi){return !(x==x)?lo:x<lo?lo:x>hi?hi:x;}
  static float soft(float x){x=bound(x,-3,3);float q=x*x;return x*(27.f+q)/(27.f+9.f*q);}
  static float wave(float p,const Block &c){
    return (2.f*p-1.f)*(1.f-c.blend)+((p<c.width?1.f:-1.f)-(2.f*c.width-1.f))*c.blend;
  }
  static void event(float fraction,float jump,float &previous,float &current){
    float t=1.f-fraction;
    previous+=jump*.5f*t*t; current-=jump*.5f*fraction*fraction;
  }
  static void advance(float &phase,float inc,const Block &c,float begin,float length,float gain,float &previous,float &current){
    if(length<=0)return;
    float end=phase+inc*length;
    if(phase<c.width && end>=c.width)
      event(begin+(c.width-phase)/inc,-2.f*c.blend*gain,previous,current);
    if(end>=1.f) {
      float wrap=begin+(1.f-phase)/inc;
      event(wrap,(-2.f+4.f*c.blend)*gain,previous,current);
      end-=1.f;
      if(end>=c.width)event(wrap+c.width/inc,-2.f*c.blend*gain,previous,current);
    }
    phase=end;
  }
};
} // namespace bento
