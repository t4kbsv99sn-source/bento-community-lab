/* BENTO_MOD K1: DaisySP live kick in native one-shot sample position.
 * Application only. DSP MIT; see vendor/daisysp/LICENSE. */
#include "vendor/daisysp/Source/Drums/synthbassdrum.h"
#include "vendor/daisysp/Source/Drums/synthsnaredrum.h"
#include "vendor/daisysp/Source/Drums/hihat.h"
#include "clap.h"
#include "snare909.h"
#include "subtractive.h"
#include "analog.h"
#include "step_lock_shared.h"
#define KICK_FRAMES 144019u
#define SIGNATURE 0xb1e70a5cu
#include "kick_assignment.h"
#include "kick_knobs.h"
#include "drum_models.h"
#include "mod_matrix.h"
struct Slot {u32 root,handle,descriptor,provider,file,voice,left,last;daisysp::SyntheticBassDrum kick;};
struct Armed {u32 root,handle,ticket;};
struct State {u32 magic,random,starts,blocks;Slot slots[16];u32 serial;Armed armed[128];u32 ui_serial;u32 a_voice,a_now,a_root,a_serial,a_mode,a_glide,a_last_root,a_last_note;u32 a_pub[2];};
#define K ((State*)0x24042000u)
#define MAGIC 0x474b5342u
/* K14 uses ONLY gaps in K7's already-reserved RAM. S ends at 45810;
 * A ends at 47420. Native send/lock layouts and capacities are unchanged. */
static_assert(sizeof(daisysp::SyntheticSnareDrum)==288,"Snare state size changed");
static_assert(0x24045820u+7u*288u<=0x24046000u,"Snare pool A overlaps lock table");
static_assert(0x24047420u+9u*288u<=0x24047e40u,"Snare pool B overlaps model IDs");
static_assert(sizeof(daisysp::HiHat<>)<=288,"HiHat must fit existing snare pool");
#define VOICE_LOCKS ((u32*)0x24047e80u)
static_assert(0x24047e80u+32*4u<=0x24048000u,"Synth locks overlap UI");
#define MODELS ((u32*)0x24047e40u)
static daisysp::SyntheticSnareDrum *snare(Slot *s){u32 i=s-K->slots;return (daisysp::SyntheticSnareDrum*)(i<7?0x24045820u+i*288u:0x24047420u+(i-7)*288u);}
static daisysp::HiHat<> *hat(Slot*s){return (daisysp::HiHat<>*)snare(s);}
/* CH12: Clap shares the snare/hat pool; Tom uses the Slot's own kick engine. */
static_assert(sizeof(bento::Clap)<=288,"Clap must fit existing snare pool");
static bento::Clap *clap(Slot*s){return (bento::Clap*)snare(s);}
/* P10: the Snare engine is the 909 model (owner); same pool cell. */
static_assert(sizeof(bento::Snare909)<=288,"909 Snare must fit existing snare pool");
static bento::Snare909 *s909(Slot*s){return (bento::Snare909*)snare(s);}
static_assert(sizeof(bento::Subtractive)<=288,"Subtractive exceeds existing per-voice pool");
static bento::Subtractive *subtractive(Slot*s){return (bento::Subtractive*)snare(s);}
static u32 model(Slot*s){return MODELS[s-K->slots]&255u;}
static u32 duration(Slot*s){if(model(s)==11)return 0x7fffffffu;return MODELS[s-K->slots]&0x100u?48000u*8u:KICK_FRAMES+model(s)-1;}
/* Wide pitched-synth notes are a cold path; retain the drum pitch fast path. */
static __attribute__((noinline)) float wide_pitch(Slot *s,float ratio){
 return ratio>0 && ratio<=64.f && model(s)==11?ratio:1.f;
}
static const u8 snare_defaults[7]={10,45,50,65,70,0,0};
/* P10 (owner: "punch for the kick, weight for the snare").
 * Kick: knob 7 is Punch (was Dirt; the engine's own dirt is off on the Kick):
 * a fast extra pitch dive (6 ms) on top of Sweep, then warm saturation.
 * Snare: the 909 model (snare909.h); knob 3 is Tone (was FM).
 * Punch 0 sounds exactly as before. The Kick's dive envelope lives in the
 * slot's snare-pool cell, unused by Kick voices. */
static float *punch_env(Slot *s){return (float*)snare(s);}
static inline float warm(float x,float g){
 float y=g*x;if(y>3.f)y=3.f;if(y<-3.f)y=-3.f;float y2=y*y; /* t(3)=1: a true saturator */float t=y*(27.f+y2)/(27.f+9.f*y2);float n=g*(27.f+g*g)/(27.f+9.f*g*g);return t/n;
}
struct Extra {float punch,sweep;};
static_assert(sizeof(State)<=0x1500,"Kick state overlaps L7 send state");
static_assert(__builtin_offsetof(State,a_pub)==0x14f8,"P4 Analog display word moved (ANALOG_PUB in kick_knobs.h)");
/* K4: two separate cache-line-aligned diagnostic areas. M7 owns E00..E7F;
 * UI owns F00..F7F. Neither overlaps State or the held-step UI state. */
#define D ((volatile u32*)0x24043e00u)
static void diagnostic_init(){if(D[0]!=0x3444474bu){for(u32 i=0;i<32;i++)D[i]=0;D[0]=0x3444474bu;}}
static void publish(){
 __asm__ volatile("dsb" ::: "memory");
 if(*(volatile u32*)0xe000ed14u & (1u<<16))
  for(u32 a=0x24043e00u;a<0x24043e80u;a+=32)*(volatile u32*)0xe000ef68u=a;
 __asm__ volatile("dsb" ::: "memory");
}
extern "C" __attribute__((used)) void kick_command_probe(void *root,const u32 *record){
 diagnostic_init();D[1]++;D[2]=(u32)root;D[3]=root?W(root,0):0;
 D[4]=root?W(root,12):0;D[5]=record[2];D[6]=record[4];publish();
}
extern "C" void *memset(void *p,int value,unsigned n){for(unsigned i=0;i<n;i++)((u8*)p)[i]=(u8)value;return p;}
extern "C" void *memcpy(void *p,const void *s,unsigned n){for(unsigned i=0;i<n;i++)((u8*)p)[i]=((const u8*)s)[i];return p;}
extern "C" float sqrtf(float x){float out;__asm__("vsqrt.f32 %0,%1":"=t"(out):"t"(x));return out;}
extern "C" float fabsf(float x){return x<0?-x:x;}
extern "C" int rand(void){u32 v=K->random;v^=v<<13;v^=v>>17;v^=v<<5;K->random=v;return (int)(v&0x7fffffffu);}
/* Bounded deterministic embedded math. No libc, double helpers or OS calls. */
extern "C" float sinf(float x){
 const float pi=3.14159265358979323846f,twopi=6.2831853071795864769f;
 int n=(int)(x/twopi);x-=n*twopi;if(x>pi)x-=twopi;if(x<-pi)x+=twopi;
 if(x>pi*.5f)x=pi-x;else if(x<-pi*.5f)x=-pi-x;
 float q=x*x;return x*(1+q*(-.1666666666667f+q*(.0083333333333f+q*(-.0001984126984f+q*(.0000027557319f+q*(-.0000000250521f))))));
}
static float exp2f_small(float x){
 if(x<-24)return 0;if(x>16)x=16;
 int n=(int)x;if((float)n>x)n--;float f=(x-(float)n)*.6931471805599453f;
 float y=1+f*(1+f*(.5f+f*(.1666666666667f+f*(.0416666666667f+f*(.0083333333333f+f*(.0013888888889f+f*.0001984126984f))))));
 union {u32 bits;float value;} scale={(u32)(n+127)<<23};return y*scale.value;
}
extern "C" float powf(float a,float b){
 if(a==2)return exp2f_small(b);if(a==1)return 1;if(a<=0)return 0;
 union {float value;u32 bits;} v={a};int e=(int)((v.bits>>23)&255)-127;v.bits=(v.bits&0x7fffff)|0x3f800000;
 float z=(v.value-1)/(v.value+1),q=z*z;
 float l=2*z*(1+q*(1.f/3+q*(1.f/5+q*(1.f/7+q*(1.f/9+q*(1.f/11+q/13))))));
 return exp2f_small(b*((float)e+l*1.4426950408889634f));
}
static void init(){if(K->magic!=MAGIC){memset((void*)K,0,sizeof(State));memset((void*)0x24045820u,0,7*288);memset((void*)0x24047420u,0,9*288+16*4);memset(VOICE_LOCKS,0,32*4);K->random=0x51b37a29;K->magic=MAGIC;}}
/* K3 explicit assignment from the native loader. No PCM/cache probe needed.
 * 128 current pads fit; oldest assignments from prior projects are reclaimed
 * only when capacity is reached. Never dereference remembered/freed roots. */
extern "C" __attribute__((used)) void kick_enable(void *root,u32 enabled){
 diagnostic_init();if(!root || W(root,0)!=0x080ac66cu)return;init();
 Armed *chosen=0;u32 age=0;
 for(u32 i=0;i<128;i++){
  Armed *a=&K->armed[i];
  if(a->root==(u32)root)a->root=0;
  if(!a->root)chosen=a;
 }
 for(u32 i=0;i<16;i++)if(K->slots[i].root==(u32)root){K->slots[i].left=0;K->slots[i].root=0;K->slots[i].voice=0;}
 if(!enabled)return;
 if(!chosen)for(u32 i=0;i<128;i++){
  u32 d=K->serial-K->armed[i].ticket;
  if(!chosen || d>age){age=d;chosen=&K->armed[i];}
 }
 chosen->root=(u32)root;chosen->handle=W(root,12);chosen->ticket=++K->serial;D[7]++;publish();
}
/* This path is independent of the native queued-property route. The K4 device
 * report proves the UI sees the reserved name but M7 receives no private key.
 * UI MPU marks this reserved SRAM as non-cacheable. M7 invalidates reader-only
 * mailbox lines; it never cleans or writes them while the UI owns them. */
static void invalidate(u32 first,u32 last){
 __asm__ volatile("dsb" ::: "memory");
 if(*(volatile u32*)0xe000ed14u & (1u<<16))
  for(u32 a=first;a<last;a+=32)*(volatile u32*)0xe000ef5cu=a;
 __asm__ volatile("dsb" ::: "memory");
}
extern "C" __attribute__((used)) u32 kick_assignment(void *root){
 init();invalidate(0x24043500u,0x24043520u);
 if(ASSIGN->magic!=ASSIGN_MAGIC)return 0;
 u32 serial=ASSIGN->serial;
 if(!K->ui_serial || K->ui_serial!=serial){invalidate(0x24043520u,0x24043d20u);K->ui_serial=serial;}
 u32 handle=W(root,12);
 for(u32 i=0;i<128;i++){
  KickAssignment *e=&ASSIGN->entries[i];u32 before=e->sequence,h=e->handle,value=e->enabled;
  __asm__ volatile("dmb" ::: "memory");
  if(before && !(before&1) && before==e->sequence && h==handle)return value?1:2;
 }return 0;
}
/* Snapshot UI-owned knobs. Only these cache lines are invalidated; M7 owns
 * no writes to this table. In-flight commits use defaults until next block. */
/* Returns 1 when this pad's synth routes apply: the UI entry matches the engine
 * and its routes were made for this engine (CH11 tag in reserved bits 4..7). */
static int parameters(void *root,u8 *values,u32 engine){
 for(u32 j=0;j<7;j++)values[j]=drum_defaults(engine)[j];
 init();invalidate(0x24043500u,0x24043520u);
 if(KNOBS->magic!=KNOBS_MAGIC)return 0;
 u32 serial=KNOBS->serial;
 if(!K->ui_serial || K->ui_serial!=serial){invalidate(0x24043520u,0x24043d20u);K->ui_serial=serial;}
 for(u32 i=0;i<128;i++){
  KickKnob *e=&KNOBS->entries[i];u32 before=e->sequence;
  u32 reserved=e->reserved;
  if(!before || (before&1) || e->handle!=W(root,12) || MOD_ENGINE(reserved)!=engine)continue;
  u8 next[7];for(u32 j=0;j<7;j++)next[j]=e->values[j];
  __asm__ volatile("dmb" ::: "memory");
  if(before!=e->sequence || (KNOBS->serial&1))return 0;
  int routes=!MOD_TAG(reserved) || MOD_TAG(reserved)==engine;
  if(drum_family(engine)==1?(next[0]<25 || next[0]>180):next[0]>100)return routes;
  for(u32 j=1;j<7;j++)if(next[j]>100)return routes;
  for(u32 j=0;j<7;j++)values[j]=next[j];return routes;
 }
 return 0;
}
extern "C" __attribute__((used)) void kick_parameters(void *root,u8 *values){parameters(root,values,1);}
/* Click shares the existing entry transaction/serial but has separate cache
 * lines. Snapshot sequence is checked after reading both sources. */
static u32 click(void *root,u32 fallback,u32 engine=1){
 invalidate(0x24043d80u,0x24043e00u);
 if(KNOBS->magic!=KNOBS_MAGIC)return fallback;
 for(u32 i=0;i<128;i++){
  KickKnob *e=&KNOBS->entries[i];u32 seq=e->sequence;
  if(!seq || (seq&1) || e->handle!=W(root,12) || (e->reserved&15u)!=engine)continue;
  u32 value=CLICKS[i];__asm__ volatile("dmb" ::: "memory");
  if(seq==e->sequence && value<=100)return value;
 }return fallback;
}
/* CH11: native modulation sources. Source objects keep their value at +4;
 * the ids and offsets are the ones the native sampler binds (080925E0/08092F20):
 * per voice LFO1 +610, velocity +B4, key +BC, pressure +C4; per pad Auto A-D
 * +650+8n, pitch bend +120, mod wheel +108, MIDI volume +110, MIDI pan +118. */
static float source(void *root,void *voice,u32 src){
 u32 p=src==4?(u32)voice+0x610u:src==13?(u32)voice+0xb4u:src==14?(u32)voice+0xbcu:src==32||src==33?(u32)voice+0xc4u:
  src>=9&&src<=12?(u32)root+0x650u+(src-9)*8u:src==25?(u32)root+0x120u:src==26?(u32)root+0x108u:src==28?(u32)root+0x110u:src==29?(u32)root+0x118u:0;
 if(!p)return 0;float v=*(volatile float*)(p+4);if(!(v==v))return 0;return v>4?4:v<-4?-4:v;
}
/* Add each route's amount x source x the parameter's range, then clamp. The
 * base (knob or accepted lock) is never written back. */
static void modulate(void *root,void *voice,float *values,u32 engine){
 u32 n=W(root,MOD_COUNT);if(!n || n>MOD_RECORDS)return;
 for(u32 i=0;i<n;i++){
  u8 *r=(u8*)root+MOD_LIST+i*12;int j=mod_index(H(r,4));if(j<0 || (u32)j>=mod_count(engine))continue;
  float amount=*(volatile float*)r;if(!(amount==amount))continue;
  values[j]+=amount*source(root,voice,H(r,6))*(float)mod_span(engine,(u32)j);
 }
 for(u32 j=0;j<mod_count(engine);j++){float lo=(float)mod_low(engine,j),hi=lo+(float)mod_span(engine,j);if(values[j]<lo)values[j]=lo;if(values[j]>hi)values[j]=hi;}
}
static void values_for(Slot *s,const u8 *background,float *values,void *voice,int routes){
 u8 merged[8];for(u32 j=0;j<7;j++)merged[j]=background[j];merged[7]=(u8)click((void*)s->root,model(s)==11?0:merged[2],model(s));
 for(u32 j=0;j<2;j++){u32 w=VOICE_LOCKS[(s-K->slots)*2+j],k=lock_kind(w);if(synth_model(k)==drum_family(model(s)) && (model(s)==1 || synth_index(k)<drum_count(model(s))))merged[synth_index(k)]=(u8)decode_value(w);}
 for(u32 j=0;j<8;j++)values[j]=(float)merged[j];
 if(routes && voice)modulate((void*)s->root,voice,values,model(s));
 }
static void apply(Slot *s,const u8 *background,float ratio,void *voice,int routes,Extra *x=0){
 float values[8];values_for(s,background,values,voice,routes);
 if(model(s)==11)return;
 if(model(s)==5){auto *h=hat(s);h->SetFreq((100+values[0]*10.7f)*ratio);h->SetDecay(values[1]*.01f);h->SetTone(values[2]*.01f);h->SetAccent(values[3]*.01f);h->SetNoisiness(values[4]*.01f);return;}
 if(model(s)==7){auto *c=clap(s);c->SetTune(values[0]*.01f);c->SetDecay(values[1]*.01f);c->SetTone(values[2]*.01f);c->SetAccent(values[3]*.01f);c->SetSpread(values[4]*.01f);return;}
 if(model(s)==3){auto *n=s909(s);n->SetFreq(140.f*powf(2.f,values[0]*.02f)*ratio);n->SetDecay(values[1]*.01f);n->SetTone(values[2]*.01f);n->SetAccent(values[3]*.01f);n->SetSnappy(values[4]*.01f);return;}
 /* Tom / FM perc: the kick's FM engine an octave-scaled range up, no Click
  * (its transient follows Tone): Tune 25..180 = 40 Hz x 2^((v-25)/28), 40 Hz..1.85 kHz. */
 if(model(s)==9)s->kick.SetFreq(40.f*powf(2.f,(values[0]-25.f)*(1.f/28.f))*ratio);else
 s->kick.SetFreq(values[0]*ratio);s->kick.SetDecay(values[1]*.01f);
 s->kick.SetTone(values[2]*.01f);s->kick.SetAccent(values[3]*.01f);
 s->kick.SetFmEnvelopeAmount(values[4]*.01f);s->kick.SetFmEnvelopeDecay(values[5]*.01f);
 s->kick.SetDirtiness(model(s)==1?0.f:values[6]*.01f);if(model(s)==1){s->kick.SetClick(values[7]*.01f);if(x){x->punch=values[6]*.01f;x->sweep=values[4]*.01f;}}s->kick.UpdateCoefficients();
}
/* CH11: 0x3F route commands for synth destinations, from the sampler's own
 * command switch (0808F38E). Upsert by (key, slot); source 0 removes. Native
 * destinations return 0 and take the original path. */
extern "C" __attribute__((used)) int kick_route(void *root,const u8 *record){
 if(mod_index(H(record,12))<0)return 0;
 if(!root || W(root,0)!=0x080ac66cu)return 1;
 u32 key=H(record,12),slot=H(record,16)&255u,src=H(record,20);int amount=(short)H(record,22);
 u32 n=W(root,MOD_COUNT);if(n>MOD_RECORDS)return 1;
 u8 *list=(u8*)root+MOD_LIST;u32 i=0;
 for(;i<n;i++)if(H(list+i*12,4)==key && B(list+i*12,8)==slot)break;
 if(!src){if(i<n){for(u32 k=i*12;k+12<n*12;k++)list[k]=list[k+12];W(root,MOD_COUNT)=n-1;}return 1;}
 if(i==n){if(n==MOD_RECORDS)return 1;W(root,MOD_COUNT)=n+1;}
 u8 *r=list+i*12;*(volatile float*)r=(float)amount/1000.f;H(r,4)=(unsigned short)key;H(r,6)=(unsigned short)src;B(r,8)=(u8)slot;
 return 1;
}
extern "C" __attribute__((used)) int kick_selected(void *root){
 init();for(u32 i=0;i<128;i++)if(K->armed[i].root==(u32)root && K->armed[i].handle==W(root,12))return 1;return 0;
}
/* K6: hardware report provider 100455E0 lies inside native MPU region 5,
 * 10040000..1004FFFF (RASR 1307001F). K1-K5 incorrectly rejected it.
 * Native M7 MPU regions include C0000000..C3FFFFFF AND C4000000..C5FFFFFF.
 * K1/K2 omitted the second region, rejecting valid native sample/audio buffers. */
static bool memory(u32 p){return p>=0x10040000u && p<0x10050000u || p>=0x20000000u && p<0x30040000u || p>=0xc0000000u && p<0xc6000000u;}
/* Native descriptor's virtual sample reader: immutable position-zero probe.
 * Exact frame count + 32 signed one-LSB samples identify our browser carrier. */
extern "C" __attribute__((used)) int kick_marker(void *descriptor){
 diagnostic_init();D[30]=1;if(!memory((u32)descriptor) || !memory(W(descriptor,0)))return 0;
 D[26]=FN(0x08054ec0,u32(*)(void*))(descriptor);D[30]=2;u32 engine=D[26]==KICK_FRAMES?1:D[26]==KICK_FRAMES+2?3:D[26]==KICK_FRAMES+4?5:D[26]==KICK_FRAMES+6?7:D[26]==KICK_FRAMES+8?9:D[26]==KICK_FRAMES+10?11:0;if(!engine)return 0;
 D[28]=FN(0x08054f80,u32(*)(void*))(descriptor);D[30]=3;if(D[28])return 0;
 D[27]=FN(0x08054e00,u32(*)(void*))(descriptor);D[30]=4;if(D[27]!=48000)return 0;
 float probe[32];for(u32 i=0;i<32;i++)probe[i]=0;
 FN(0x08054da0,void(*)(void*,float*,u32,int,u32))(descriptor,probe,32,0,0);
 float mag=fabsf(probe[0]);union {float f;u32 u;} m={mag};D[29]=m.u;D[30]=5;if(mag<0.00000001f || mag>1.000001f)return 0;
 D[30]=6;for(u32 i=0;i<32;i++)if(probe[i]!=(SIGNATURE&(1u<<i)?mag:-mag))return 0;
 D[30]=7;return (int)engine;
}
static u32 now(){return *(volatile u32*)0x30035f40u;}
static Slot *find(void *root,void *descriptor,void *voice){
 for(u32 i=0;i<16;i++){Slot *s=&K->slots[i];if(s->root==(u32)root && s->handle==W(root,12) && s->descriptor==(u32)descriptor && s->provider==W(descriptor,0) && s->file==W(descriptor,4) && (model(s)!=11 || s->voice==(u32)voice))return s;}return 0;
}
extern "C" __attribute__((used)) void kick_voice(void *voice,void *root){
 diagnostic_init();D[8]++;D[9]=(u32)root;D[10]=root?W(root,0):0;D[11]=voice?W(voice,12):0;D[12]=1;publish();
 if(!root || W(root,0)!=0x080ac66cu || !voice || !memory(W(voice,12)))return;
 init();void *d=(void*)W(voice,12);Slot *s=find(root,d,voice);
 u32 engine=kick_selected(root)?1:(u32)kick_marker(d);
 if(!engine){
  for(u32 i=0;i<16;i++)if(K->slots[i].root==(u32)root){K->slots[i].left=0;K->slots[i].root=0;K->slots[i].voice=0;}
  D[12]=2;publish();return;
 }
 if(!s)for(u32 i=0;i<16;i++)if(!K->slots[i].left || (u32)(now()-K->slots[i].last)>5000u){s=&K->slots[i];break;}
 if(!s){D[12]=3;publish();return;}
 /* Monophonic per sound. Only touch old voice if still in this native root. */
 if(engine!=11 && s->root==(u32)root && s->voice!=(u32)voice && W(root,0x60)<=16)
  for(u32 i=0;i<W(root,0x60);i++)if(W(root,0x20+i*4)==s->voice && s->voice)B((void*)s->voice,0)=0;
 memset((void*)s,0,sizeof(Slot));s->root=(u32)root;s->handle=W(root,12);s->descriptor=(u32)d;s->provider=W(d,0);s->file=W(d,4);s->voice=(u32)voice;s->left=engine==11?0x7fffffffu:KICK_FRAMES+engine-1;s->last=now();MODELS[s-K->slots]=engine;
 // Accepted-note payload is snapshotted per voice; no pad/background mutation.
 u32 packed=W((void*)0x24046000u,0)==0x374c5042u && W((void*)0x24046000u,8)==(u32)root?W((void*)0x24046000u,12):0;
 for(u32 j=0;j<2;j++)VOICE_LOCKS[(s-K->slots)*2+j]=lock_slot(packed,j);
 if(engine==1)punch_env(s)[0]=1.f;
 if(engine==11)subtractive(s)->Init(48000);else if(engine==3)s909(s)->Init(48000);else if(engine==5)hat(s)->Init(48000);else if(engine==7)clap(s)->Init(48000);else s->kick.Init(48000);u8 values[7];parameters(root,values,engine);
 // Only long-decay hats reserve the longer voice lifetime; closed hats keep
 // the previous CPU cost. Include the accepted per-voice Decay lock.
 if(engine==5){u32 decay=values[1];for(u32 j=0;j<2;j++){u32 w=VOICE_LOCKS[(s-K->slots)*2+j];if(lock_kind(w)==26)decay=(u32)decode_value(w);}if(decay>70)MODELS[s-K->slots]|=0x100u;s->left=duration(s);}
 apply(s,values,1,voice,0);if(engine==3)s909(s)->Trig();else if(engine==5)hat(s)->Trig();else if(engine==7)clap(s)->Trig();else if(engine!=11)s->kick.Trig();K->starts++;D[18]++;D[12]=0;publish();
}
/* Keep the new voice's larger coefficient stack out of the drum hot path. */
static __attribute__((noinline)) u32 render_subtractive(Slot *s,const u8 *background,void *voice,int routes,float ratio,u32 n,float *samples,float velocity,u32 block_peak){
 float values[8];values_for(s,background,values,voice,routes);
 bento::Subtractive::Block sc=subtractive(s)->Prepare(values,ratio,n);
 for(u32 i=0;i<n;i++){
  float x=s->left?subtractive(s)->Process(sc)*.6f:0;
  if(!(x==x))x=0;if(x>1)x=1;if(x<-1)x=-1;
  if(s->left<256)x*=s->left*(1.f/256);
  samples[i]=x*velocity;union {float f;u32 u;} peak={fabsf(x)};
  if(peak.u>block_peak)block_peak=peak.u;if(s->left)s->left--;
 }
 return block_peak;
}
/* P10 Kick Punch, out of the plain engines' hot loop. */
static __attribute__((noinline)) u32 render_weight(Slot *s,const Extra &ex,u32 n,float *samples,float velocity,u32 block_peak){
 float *pe=punch_env(s);float g=1.f+3.f*ex.punch;
 for(u32 i=0;i<n;i++){
  float x=0;
  if(s->left){s->kick.SetFmEnvelopeAmountRaw(ex.sweep+ex.punch*2.f*pe[0]);pe[0]*=.99653f;x=warm(s->kick.Process(),g)*.6f;}
  if(!(x==x))x=0;if(x>1)x=1;if(x<-1)x=-1;
  if(s->left<256)x*=s->left*(1.f/256);
  samples[i]=x*velocity;union {float f;u32 u;} peak={fabsf(x)};if(peak.u>block_peak)block_peak=peak.u;if(s->left)s->left--;
 }
 return block_peak;
}
/* Integer/pointer ABI only. Native processing after this handles level, pan,
 * amplitude/filter envelopes, mute and bus mixing, retaining all L8 locks. */
extern "C" __attribute__((used)) int kick_render(void *root,void *voice,void *temp,void *output){
 diagnostic_init();D[13]++;D[14]=(u32)root;D[15]=root?W(root,0):0;D[16]=voice?W(voice,12):0;D[31]=root?W(root,12):0;D[25]=voice && memory(W(voice,12))?W((void*)W(voice,12),0):0;D[17]=1;publish();
 if(!root || W(root,0)!=0x080ac66cu || !voice || !memory(W(voice,12)))return 0;
 init();void *d=(void*)W(voice,12);Slot *s=find(root,d,voice);
 if(!s){if(!kick_selected(root) && !kick_marker(d)){D[17]=2;publish();return 0;}kick_voice(voice,root);s=find(root,d,voice);if(!s){D[17]=3;publish();return 0;}}
 if(s->voice!=(u32)voice){D[17]=4;publish();return 0;}
 u32 n=FN(0x080a1d60,u32(*)(void*))(output);
 D[20]=n;D[21]=(u32)temp;D[22]=W(temp,0);D[23]=W(temp,8);
 if(!n || n>1024 || W(temp,0)<n || !memory(W(temp,8))){D[17]=5;publish();return 0;}
 /* Mark mono and obtain native writable scratch. Never replace its allocation. */
 float *samples=FN(0x08052340,float*(*)(void*))(temp);
 FN(0x08052f00,void(*)(void*,u32))(temp,n);
 /* CH11: the native render entry ticks the voice LFO1 first; synth voices skip
  * that entry, so tick it here (LFO1 routes to Pitch/Level and to synth params). */
 if(memory(W(voice,0x5dc)))FN(0x08064a80,void(*)(void*,u32))((u8*)voice+0x5d8,n);
 /* Same pitch multiplier as the original sample renderer, evaluated per block. */
 u32 pitch_bits=FN(0x080d5880,u32(*)(void*,void*))(root,voice);
 union {u32 bits;float value;} pitch={pitch_bits};
 float ratio=pitch.value;if(__builtin_expect(!(ratio>0) || ratio>8,0))ratio=wide_pitch(s,ratio);
 u8 values[7];int routes=parameters(root,values,model(s));Extra ex={0,0};apply(s,values,ratio,voice,routes,&ex);
 float velocity=*(volatile float*)((u8*)voice+0xb8);if(!(velocity>=0))velocity=0;if(velocity>1)velocity=1;
 // Coefficients are constant for this block, after pitch and locks apply.
 // Keep them on the stack: no fixed-RAM layout or voice capacity changes.
 bento::Snare909::BlockCoefficients snc={};
 daisysp::HiHat<>::BlockCoefficients hc={};
 bento::Clap::BlockCoefficients cc={};
 u32 engine=model(s);
 if(engine==3)snc=s909(s)->PrepareBlock();
 else if(engine==5)hc=hat(s)->PrepareBlock();
 else if(engine==7)cc=clap(s)->PrepareBlock();
 u32 block_peak=D[24];
 if(engine==11)block_peak=render_subtractive(s,values,voice,routes,ratio,n,samples,velocity,block_peak);
 else if(engine==1&&ex.punch>0)block_peak=render_weight(s,ex,n,samples,velocity,block_peak);
 else {
 for(u32 i=0;i<n;i++){
  float x=s->left?(engine==3?s909(s)->ProcessPrepared(snc):engine==5?hat(s)->ProcessPrepared(hc):engine==7?clap(s)->ProcessPrepared(cc):s->kick.Process())*.6f:0;
  if(!(x==x))x=0;if(x>1)x=1;if(x<-1)x=-1;
  if(s->left<256)x*=s->left*(1.f/256);
  samples[i]=x*velocity;union {float f;u32 u;} peak={fabsf(x)};if(peak.u>block_peak)block_peak=peak.u;if(s->left)s->left--;
 }
 }
 D[24]=block_peak;
 u32 elapsed=duration(s)-s->left;
 // Keep the native carrier cursor alive while the longer synthesized hat rings.
 if(engine==11)elapsed%=KICK_FRAMES+10;
 if(engine==5&&s->left&&elapsed>=KICK_FRAMES+4)elapsed=KICK_FRAMES+3;
 W(voice,0x40)=elapsed;W(voice,0x44)=0;
 FN(0x08092d00,void(*)(void*,void*,void*,void*))(root,voice,temp,output);
 if(engine==11 && !B(voice,0))s->left=0;
 if(!s->left)B(voice,0)=0;s->last=now();K->blocks++;D[19]++;D[17]=0;publish();return 1;
}

/* A1 "Analog" Wavetable tracks. The UI marks a Wavetable instrument as analog
 * with a KickKnob entry (engine 13) keyed by the instrument's handle; values[0]
 * is Sync (0 off). Two vtable hooks: the Wavetable root's per-voice render
 * (slot 18, 0809BE80) records the voice and the track's mode; the WT oscillator
 * render (class 080AC3E4 slot 0, 08081360) is replaced for WT1/WT2 of analog
 * voices. Pitch, level, smoothing and mixing use the native helpers in the
 * native order; only the wavetable read (080A1860) and its "table loaded" gate
 * are replaced. The third "Osc" (sub) stays native. */
#define ANALOG_ENGINE 13u
static u32 analog_mode(void *root){
 invalidate(0x24043500u,0x24043520u);
 if(KNOBS->magic!=KNOBS_MAGIC)return 0;
 u32 serial=KNOBS->serial,handle=W(root,12);
 if(serial && K->a_root==(u32)root && K->a_serial==serial)return K->a_mode;
 if(!K->ui_serial || K->ui_serial!=serial){invalidate(0x24043520u,0x24043d20u);K->ui_serial=serial;}
 u32 mode=0;
 for(u32 i=0;i<128;i++){
  KickKnob *e=&KNOBS->entries[i];u32 seq=e->sequence;
  if(!seq || (seq&1) || e->handle!=handle || MOD_ENGINE(e->reserved)!=ANALOG_ENGINE)continue;
  u32 sync=e->values[0],glide=e->values[1];__asm__ volatile("dmb" ::: "memory");
  if(seq!=e->sequence)continue;
  mode=1u|(sync?2u:0u);K->a_glide=glide>100?100:glide;break;
 }
 if(!mode)K->a_glide=0;
 K->a_root=(u32)root;K->a_serial=serial;K->a_mode=mode;return mode;
}
#define FLOAT(p,o) (*(volatile float*)((u8*)(p)+(o)))
/* Glide: a new note on a voice starts from the track's previous note and
 * slides to its own pitch. The offset (octaves) is added to WT1/WT2 in
 * kick_analog_osc and to the sub (Osc, voice+4C, whose native pitch reads its
 * +4 detune every block); it decays exponentially in WT1's render. */
extern "C" __attribute__((used)) void kick_analog_enter(void *root,void *voice){
 init();K->a_voice=(u32)voice;K->a_now=root && voice?analog_mode(root):0;
 if(!(K->a_now&1))return;
 bento::AnalogOsc *g=(bento::AnalogOsc*)((u8*)voice+0x7a4+0x10c);
 if(g->magic!=ANALOG_OSC_MAGIC){g->magic=ANALOG_OSC_MAGIC;g->phase=0;g->delayed=0;g->note=0xffffffffu;g->glide=0;g->sub_applied=0;}
 u32 note=W((u8*)voice+0x7a4,0x10);
 if(note!=g->note){
  u32 last=K->a_last_root==(u32)root?K->a_last_note:note;
  g->glide=K->a_glide?((float)(int)last-(float)(int)note)*(1.f/12.f):0.f;
  g->note=note;K->a_last_root=(u32)root;K->a_last_note=note;
 }
 if(!K->a_glide)g->glide=0;
 if(!(g->glide==g->glide))g->glide=0;
 u8 *sub=(u8*)voice+0x4c;float delta=g->glide-g->sub_applied;
 if(delta!=0){FLOAT(sub,4)=FLOAT(sub,4)+delta;g->sub_applied=g->glide;}
}
extern "C" __attribute__((used)) int kick_analog_osc(void *osc,void *scratch,void *out){
 u8 *voice=(u8*)K->a_voice;u32 mode=K->a_now;
 if(K->magic!=MAGIC || !voice || !(mode&1))return 0;
 u32 which=(u8*)osc==voice+0x7a4?0:(u8*)osc==voice+0x994?1:2;if(which>1)return 0;
 u32 n=FN(0x080a1d60,u32(*)(void*))(out);
 float oct=(float)(int)W(osc,0xc)/1000.f/12.f+FLOAT(osc,4);
 oct+=FN(0x0809fd80,float(*)(void*))((u8*)osc+0x70);
 u32 note=W(osc,0x10);oct+=FN(0x0804f680,float(*)(void*))(&note);
 bento::AnalogOsc *glider=(bento::AnalogOsc*)(voice+0x7a4+0x10c);
 if(glider->magic==ANALOG_OSC_MAGIC)oct+=glider->glide;
 float ratio=FN(0x0804f5e0,float(*)(float))(oct);
 float rate=ratio/23.4375f/FLOAT(osc,0x108);
 float pos=FN(0x0809fd80,float(*)(void*))((u8*)osc+0x30)*255.f;
 int position=(int)pos;if(position<0)position=0;if(position>255)position=255;
 float level=FN(0x0804f360,float(*)(float))(FN(0x0809fd80,float(*)(void*))((u8*)osc+0xb0));
 FN(0x08071240,void(*)(void*,float))((u8*)osc+0xf8,level);
 FLOAT(osc,0x1e8)=rate;W(osc,0x20)=(u32)position;
 /* P4: the Analog page draws the shape the oscillator really plays (with
    modulation): {track handle, shape1 | shape2<<8 | counter<<16}, M7-owned
    cache line, cleaned for the UI core. */
 {u32 sh=which*8u,v=K->a_pub[1];v=(v&~(255u<<sh))|((u32)position<<sh);v=(v&0xffffu)|((v+0x10000u)&0xffff0000u);
  K->a_pub[0]=W((void*)K->a_root,12);K->a_pub[1]=v;__asm__ volatile("dsb" ::: "memory");W((void*)0xe000ef68u,0)=(u32)&K->a_pub[0];__asm__ volatile("dsb" ::: "memory");}
 bool silent=level==0 && !W(osc,0x104);
 bool master=which==0 && (mode&2);
 /* Glide time 0..100 = 0..about 2 s to 1/1000 of the interval; decay once per block in WT1. */
 if(which==0 && glider->glide!=0 && n<=1024){
  float seconds=(float)K->a_glide*.02f,coef=seconds>0?powf(.001f,(float)n/(seconds*48000.f)):0.f;
  glider->glide*=coef;if(glider->glide<.0005f && glider->glide>-.0005f)glider->glide=0;
 }
 if(silent && !master)return 1;
 if(n>1024)return 1;
 float *samples=FN(0x08052340,float*(*)(void*))(scratch);
 FN(0x08052f00,void(*)(void*,u32))(scratch,n);
 bento::AnalogOsc *self=(bento::AnalogOsc*)((u8*)osc+0x10c),*slave=(bento::AnalogOsc*)(voice+0x994+0x10c);
 /* A 2048-sample cycle at the native rate, as for a standard wavetable. */
 bento::AnalogKernel::Render(*self,rate*(1.f/2048.f),(float)position*(1.f/255.f),samples,n,which==0?slave->events:0,which==1 && (mode&2)?slave->events:0);
 if(silent)return 1;
 FN(0x08071040,void(*)(void*,float*,u32,u32))((u8*)osc+0xf8,samples,0,n);
 FN(0x080526c0,void(*)(void*,void*))(out,scratch);
 return 1;
}
