/* A1: "Analog" oscillators for the native Wavetable instrument.
 * Project code, GPL-3.0-or-later. Oscillator ideas from S1 (subtractive.h):
 * saw -> pulse blend, pulse-width narrowing, fractional two-sample BLEP
 * corrections and fractional hard-sync resets. One sample per output sample
 * (the native filters, envelopes and voice mixer follow).
 *
 * State lives in the oscillator's own native wavetable-kernel area
 * (WT object +10C), which analog tracks never use: no new fixed RAM.
 */
#pragma once
namespace bento {
struct AnalogOsc {
  unsigned magic;
  float phase,delayed;
  unsigned char events[128]; /* master resets: 0..254 = fraction of the sample, 255 = none */
  /* Glide, kept in WT1's state for the voice: the note being played, the
   * remaining pitch offset (octaves) and what was last added to the sub. */
  unsigned note;float glide,sub_applied;
};
static_assert(sizeof(AnalogOsc)<=0xc0,"Analog state must stay below the native kernel's own fields");
#define ANALOG_OSC_MAGIC 0x4f4c4e41u
#define ANALOG_NO_EVENT 255u
class AnalogKernel {
 public:
  /* inc: cycles per sample. shape 0..1: saw .. square .. 8% pulse.
   * master: record wrap events into events (may be 0).
   * sync: reset the phase at these events (may be 0). */
  static void Render(AnalogOsc &o,float inc,float shape,float *out,unsigned n,unsigned char *master,const unsigned char *sync){
    if(o.magic!=ANALOG_OSC_MAGIC){o.magic=ANALOG_OSC_MAGIC;o.phase=0;o.delayed=0;}
    if(!(inc>0))inc=0;if(inc>.45f)inc=.45f;
    if(!(shape>=0))shape=0;if(shape>1)shape=1;
    const float blend=shape*2.f>1.f?1.f:shape*2.f;
    const float width=.5f-(shape>.5f?shape-.5f:0.f)*.84f;
    const float pulse_dc=2.f*width-1.f;
    float p=o.phase,delayed=o.delayed;
    for(unsigned i=0;i<n;i++){
      float previous=0,current=0;
      unsigned e=sync && i<128?sync[i]:ANALOG_NO_EVENT;
      if(e!=ANALOG_NO_EVENT && inc>0){
        float edge=(float)e*(1.f/254.f);
        advance(p,inc,blend,width,0,edge,previous,current,0,i);
        float jump=wave(0,blend,width,pulse_dc)-wave(p,blend,width,pulse_dc);
        event(edge,jump,previous,current);p=0;
        advance(p,inc,blend,width,edge,1.f-edge,previous,current,0,i);
      }else advance(p,inc,blend,width,0,1,previous,current,master,i);
      out[i]=delayed+previous;
      delayed=wave(p,blend,width,pulse_dc)+current;
    }
    o.phase=p;o.delayed=delayed;
  }
 private:
  static float wave(float p,float blend,float width,float pulse_dc){
    return (2.f*p-1.f)*(1.f-blend)+((p<width?1.f:-1.f)-pulse_dc)*blend;
  }
  static void event(float fraction,float jump,float &previous,float &current){
    float t=1.f-fraction;previous+=jump*.5f*t*t;current-=jump*.5f*fraction*fraction;
  }
  static void advance(float &p,float inc,float blend,float width,float begin,float length,float &previous,float &current,unsigned char *master,unsigned i){
    if(master && i<128)master[i]=ANALOG_NO_EVENT;
    if(length<=0)return;
    float end=p+inc*length;
    if(p<width && end>=width)event(begin+(width-p)/inc,-2.f*blend,previous,current);
    if(end>=1.f){
      float wrap=begin+(1.f-p)/inc;
      event(wrap,-2.f+4.f*blend,previous,current);
      if(master && i<128){int f=(int)(wrap*254.f+.5f);master[i]=(unsigned char)(f<0?0:f>254?254:f);}
      end-=1.f;
      if(end>=width)event(wrap+width/inc,-2.f*blend,previous,current);
    }
    p=end;
  }
};
}
