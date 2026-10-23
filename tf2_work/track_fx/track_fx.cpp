#include "track_fx.h"
#include "vendor/DaisySP-LGPL/Source/Dynamics/compressor.h"
#include "vendor/DaisySP-LGPL/Source/Filters/biquad.h"
#include <math.h>
#include <new>

namespace {
constexpr uint32_t MAGIC=0x31584654u;
constexpr unsigned FIELDS=14, RECORD_BYTES=16+TF_TRACKS*(16+FIELDS*4)+4;
constexpr float PI=3.14159265358979323846f;
struct Coeff {float b0,b1,b2,a1,a2;};
struct Track {
    TfSettings settings;
    daisysp::Biquad eq[2][3];
    daisysp::Compressor comp;
    Coeff now[3],target[3];
    float eq_wet,comp_wet,makeup,makeup_target;
    float clip_wet,ceiling,ceiling_target;
    unsigned phase;bool asleep;
    TfMeters meters;
};
struct Bank {uint32_t magic;float rate,smooth,coeff_smooth;Track tracks[TF_TRACKS];};
static_assert(sizeof(TfSettings)==16+FIELDS*4,"Settings layout changed");
static_assert(sizeof(float)==4,"Requires IEEE binary32");
bool finite(float x){return x==x && x<=3.402823466e38f && x>=-3.402823466e38f;}
bool range(float x,float a,float b){return finite(x)&&x>=a&&x<=b;}
bool valid(const TfSettings &s,float rate){
    return s.eq_enabled<=1&&s.comp_enabled<=1&&s.clip_enabled<=1&&s.auto_makeup<=1 &&
      range(s.low_hz,20,rate*.45f)&&range(s.low_db,-12,12)&&
      range(s.mid_hz,20,rate*.45f)&&range(s.mid_db,-12,12)&&range(s.mid_q,.3f,6)&&
      range(s.high_hz,20,rate*.45f)&&range(s.high_db,-12,12)&&
      range(s.threshold_db,-60,0)&&range(s.ratio,1,20)&&
      range(s.attack_ms,.1f,100)&&range(s.release_ms,10,2000)&&
      range(s.makeup_db,0,12)&&range(s.comp_mix,0,1)&&range(s.clip_ceiling_db,-12,0);
}
Bank *bank(void *p){return p&&!(uintptr_t(p)%alignof(Bank))&&((Bank*)p)->magic==MAGIC?(Bank*)p:nullptr;}
const Bank *bank(const void *p){return bank(const_cast<void*>(p));}
Coeff coefficients(float rate,unsigned kind,float hz,float db,float q){
    // RBJ audio EQ cookbook, low/high shelves S=1 and a peaking middle band.
    // DaisySP Biquad supplies the recursive sample processing, independently L/R.
    if(db==0)return {1,0,0,0,0};
    float a=powf(10,db*.025f),w=2*PI*hz/rate,c=cosf(w),sn=sinf(w);
    float alpha=sn/(2*q),b0,b1,b2,a0,a1,a2;
    if(kind==1){b0=1+alpha*a;b1=-2*c;b2=1-alpha*a;a0=1+alpha/a;a1=-2*c;a2=1-alpha/a;}
    else {
      float beta=sn*sqrtf(2*a);
      if(kind==0){b0=a*((a+1)-(a-1)*c+beta);b1=2*a*((a-1)-(a+1)*c);b2=a*((a+1)-(a-1)*c-beta);a0=(a+1)+(a-1)*c+beta;a1=-2*((a-1)+(a+1)*c);a2=(a+1)+(a-1)*c-beta;}
      else {b0=a*((a+1)+(a-1)*c+beta);b1=-2*a*((a-1)+(a+1)*c);b2=a*((a+1)+(a-1)*c-beta);a0=(a+1)-(a-1)*c+beta;a1=2*((a-1)-(a+1)*c);a2=(a+1)-(a-1)*c-beta;}
    }
    return {b0/a0,b1/a0,b2/a0,a1/a0,a2/a0};
}
void set_coeff(Track &t,unsigned band){
    const Coeff &x=t.now[band];
    for(unsigned ch=0;ch<2;ch++)t.eq[ch][band].SetCoefficients(x.b0,x.b1,x.b2,x.a1,x.a2);
}
void reset(Track &t,float rate){
    for(unsigned band=0;band<3;band++){
      for(unsigned ch=0;ch<2;ch++)t.eq[ch][band].Init(rate);
      t.now[band]=t.target[band];set_coeff(t,band);
    }
    t.comp.Init(rate);t.comp.AutoMakeup(false);
    t.comp.SetAttack(t.settings.attack_ms*.001f);t.comp.SetRelease(t.settings.release_ms*.001f);
    t.comp.SetRatio(t.settings.ratio);t.comp.SetThreshold(t.settings.threshold_db);
    // Total manual/automatic makeup is separately smoothed after compression.
    t.comp.SetMakeup(0);t.comp.ResetState();t.phase=0;
}
void configure(Track &t,float rate,const TfSettings &s){
    t.settings=s;
    t.target[0]=coefficients(rate,0,s.low_hz,s.low_db,1);
    t.target[1]=coefficients(rate,1,s.mid_hz,s.mid_db,s.mid_q);
    t.target[2]=coefficients(rate,2,s.high_hz,s.high_db,1);
    t.ceiling_target=powf(10,s.clip_ceiling_db*.05f);
    // Use DaisySP's own threshold/ratio compensation, then apply it in the
    // separately smoothed output gain. Keep GR metering independent of makeup.
    t.comp.AutoMakeup(s.auto_makeup!=0);
    t.comp.SetAttack(s.attack_ms*.001f);t.comp.SetRelease(s.release_ms*.001f);
    t.comp.SetRatio(s.ratio);t.comp.SetThreshold(s.threshold_db);
    float auto_db=s.auto_makeup?t.comp.GetMakeup():0;
    t.makeup_target=powf(10,(s.makeup_db+auto_db)*.05f);t.comp.SetMakeup(0);
}
float mix(float a,float b,float wet){return wet==0?a:wet==1?b:a+(b-a)*wet;}
float soft_clip(float x,float ceiling){
    float y=daisysp::SoftClip(x/ceiling);
    // Roundoff near the flat knee may exceed unity by one binary32 ULP.
    if(y>1)y=1;else if(y<-1)y=-1;
    return y*ceiling;
}
bool overlap(const float *l,const float *r,size_t n){
    uintptr_t a=(uintptr_t)l,b=(uintptr_t)r,len=n*sizeof(float);
    return r&&(a>b?a-b<len:b-a<len);
}
uint32_t crc(const unsigned char *p,size_t n){uint32_t v=~0u;while(n--){v^=*p++;for(unsigned j=0;j<8;j++)v=(v>>1)^(0xedb88320u&(0u-(v&1)));}return ~v;}
void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
uint32_t get(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
}
extern "C" size_t tf_bank_bytes(){return sizeof(Bank);}
extern "C" size_t tf_bank_alignment(){return alignof(Bank);}
extern "C" void tf_defaults(TfSettings *s){if(s)*s={0,0,0,1,120,0,1000,0,1,6000,0,-18,3,10,120,0,1,-1};}
extern "C" int tf_init(void *p,float rate){
    if(!p||uintptr_t(p)%alignof(Bank)||!range(rate,32000,96000))return 0;
    Bank &b=*new(p) Bank{};b.rate=rate;b.smooth=1-expf(-1/(rate*.02f));b.coeff_smooth=1-expf(-32/(rate*.02f));
    for(auto &t:b.tracks){TfSettings s;tf_defaults(&s);configure(t,rate,s);reset(t,rate);t.makeup=1;t.ceiling=t.ceiling_target;t.asleep=true;}
    b.magic=MAGIC;return 1;
}
extern "C" int tf_configure(void *p,unsigned track,const TfSettings *s){Bank *b=bank(p);if(!b||track>=TF_TRACKS||!s||!valid(*s,b->rate))return 0;configure(b->tracks[track],b->rate,*s);return 1;}
extern "C" int tf_get_settings(const void *p,unsigned track,TfSettings *s){const Bank *b=bank(p);if(!b||track>=TF_TRACKS||!s)return 0;*s=b->tracks[track].settings;return 1;}
extern "C" int tf_reset_track(void *p,unsigned track){Bank *b=bank(p);if(!b||track>=TF_TRACKS)return 0;Track &t=b->tracks[track];reset(t,b->rate);t.eq_wet=t.comp_wet=t.clip_wet=0;t.makeup=1;t.ceiling=t.ceiling_target;t.asleep=true;t.meters={};return 1;}
extern "C" int tf_process(void *p,unsigned track,float *left,float *right,size_t n){
    Bank *b=bank(p);if(!b||track>=TF_TRACKS||!left||n>4096||uintptr_t(left)%alignof(float)||(right&&uintptr_t(right)%alignof(float))||overlap(left,right,n))return 0;
    if(!n)return 1;
    Track &t=b->tracks[track];TfSettings &s=t.settings;
    t.meters.input_peak=t.meters.output_peak=t.meters.reduction_db=0;
    bool active=s.eq_enabled||s.comp_enabled||s.clip_enabled||t.eq_wet>0||t.comp_wet>0||t.clip_wet>0;
    if(active&&t.asleep){reset(t,b->rate);t.ceiling=t.ceiling_target;t.asleep=false;}
    float coeff_alpha=b->coeff_smooth;
    for(size_t i=0;i<n;i++){
      float l=left[i],r=right?right[i]:l;
      if(!finite(l)||!finite(r)){left[i]=0;if(right)right[i]=0;t.meters.faults++;reset(t,b->rate);continue;}
      float peak=fmaxf(fabsf(l),fabsf(r));t.meters.input_peak=fmaxf(t.meters.input_peak,peak);
      if(active){
        t.eq_wet+=(float(s.eq_enabled)-t.eq_wet)*b->smooth;
        t.comp_wet+=(float(s.comp_enabled)-t.comp_wet)*b->smooth;
        t.clip_wet+=(float(s.clip_enabled)-t.clip_wet)*b->smooth;
        t.ceiling+=(t.ceiling_target-t.ceiling)*b->smooth;
        t.makeup+=(t.makeup_target-t.makeup)*b->smooth;
        // Binary32 updates near unity stall before 1e-6 at this time constant.
        // Snap below 0.01% so no permanent dry leak defeats the clip ceiling.
        if(fabsf(t.eq_wet-float(s.eq_enabled))<1e-4f)t.eq_wet=float(s.eq_enabled);
        if(fabsf(t.comp_wet-float(s.comp_enabled))<1e-4f)t.comp_wet=float(s.comp_enabled);
        if(fabsf(t.clip_wet-float(s.clip_enabled))<1e-4f)t.clip_wet=float(s.clip_enabled);
        if(fabsf(t.ceiling-t.ceiling_target)<1e-4f*t.ceiling_target)t.ceiling=t.ceiling_target;
        if((t.phase++&31u)==0)for(unsigned j=0;j<3;j++){
          Coeff &x=t.now[j];const Coeff &y=t.target[j];
          x.b0+=(y.b0-x.b0)*coeff_alpha;x.b1+=(y.b1-x.b1)*coeff_alpha;x.b2+=(y.b2-x.b2)*coeff_alpha;
          x.a1+=(y.a1-x.a1)*coeff_alpha;x.a2+=(y.a2-x.a2)*coeff_alpha;set_coeff(t,j);
        }
        if(t.eq_wet>0){float a=l,z=r;for(unsigned j=0;j<3;j++){a=t.eq[0][j].Process(a);z=t.eq[1][j].Process(z);}l=mix(l,a,t.eq_wet);r=mix(r,z,t.eq_wet);}
        if(t.comp_wet>0){
          // One peak detector drives BOTH channels, preserving stereo balance.
          float key=fmaxf(fmaxf(fabsf(l),fabsf(r)),1e-20f);
          t.comp.Process(key);float wet=t.comp_wet*s.comp_mix;
          float a=t.comp.Apply(l)*t.makeup,z=t.comp.Apply(r)*t.makeup;
          l=mix(l,a,wet);r=mix(r,z,wet);
        }
        if(!finite(l)||!finite(r)){l=r=0;t.meters.faults++;reset(t,b->rate);}
        if(t.clip_wet>0){
          // Normalize to the requested ceiling; DaisySP's rounded curve is
          // odd-symmetric, unity slope near zero, and bounded at +/-1.
          // Bypass fade can intentionally exceed the ceiling while transitioning.
          l=mix(l,soft_clip(l,t.ceiling),t.clip_wet);
          r=mix(r,soft_clip(r,t.ceiling),t.clip_wet);
        }
      }
      left[i]=l;if(right)right[i]=r;
      t.meters.output_peak=fmaxf(t.meters.output_peak,fmaxf(fabsf(l),fabsf(r)));
    }
    if(t.comp_wet>0)t.meters.reduction_db=fmaxf(0,-t.comp.GetGain());
    if(!s.eq_enabled&&!s.comp_enabled&&!s.clip_enabled&&t.eq_wet==0&&t.comp_wet==0&&t.clip_wet==0)t.asleep=true;
    return 1;
}
extern "C" int tf_meters(const void *p,unsigned track,TfMeters *m){const Bank *b=bank(p);if(!b||track>=TF_TRACKS||!m)return 0;*m=b->tracks[track].meters;return 1;}
extern "C" size_t tf_record_bytes(){return RECORD_BYTES;}
extern "C" int tf_save(const void *p,void *out,size_t bytes){
    const Bank *b=bank(p);if(!b||!out||bytes!=RECORD_BYTES)return 0;
    auto d=(unsigned char*)out;put(d,MAGIC);put(d+4,TF_SCHEMA);put(d+8,TF_TRACKS);put(d+12,RECORD_BYTES);
    unsigned off=16;for(const auto &t:b->tracks){put(d+off,t.settings.eq_enabled);put(d+off+4,t.settings.comp_enabled);put(d+off+8,t.settings.clip_enabled);put(d+off+12,t.settings.auto_makeup);off+=16;uint32_t v[FIELDS];__builtin_memcpy(v,&t.settings.low_hz,sizeof(v));for(unsigned j=0;j<FIELDS;j++){put(d+off,v[j]);off+=4;}}
    put(d+off,crc(d,off));return 1;
}
extern "C" int tf_load(void *p,const void *in,size_t bytes){
    Bank *b=bank(p);if(!b||!in||(bytes!=RECORD_BYTES&&bytes!=500&&bytes!=564))return 0;auto d=(const unsigned char*)in;
    unsigned version=get(d+4);bool old1=bytes==500&&version==1,old2=bytes==564&&version==2;
    if(get(d)!=MAGIC||(!old1&&!old2&&(bytes!=RECORD_BYTES||version!=TF_SCHEMA))||get(d+8)!=TF_TRACKS||get(d+12)!=bytes||get(d+bytes-4)!=crc(d,bytes-4))return 0;
    TfSettings settings[TF_TRACKS];unsigned off=16;
    for(auto &s:settings){tf_defaults(&s);s.eq_enabled=get(d+off);s.comp_enabled=get(d+off+4);s.clip_enabled=old1?0:get(d+off+8);s.auto_makeup=(old1||old2)?0:get(d+off+12);off+=old1?8:old2?12:16;uint32_t v[FIELDS];unsigned n=old1?13:FIELDS;for(unsigned j=0;j<n;j++){v[j]=get(d+off);off+=4;}__builtin_memcpy(&s.low_hz,v,n*4);if(!valid(s,b->rate))return 0;}
    for(unsigned i=0;i<TF_TRACKS;i++){configure(b->tracks[i],b->rate,settings[i]);tf_reset_track(b,i);}return 1;
}
