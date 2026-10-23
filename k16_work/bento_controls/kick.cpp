/* BENTO_MOD K1: DaisySP live kick in native one-shot sample position.
 * Application only. DSP MIT; see vendor/daisysp/LICENSE. */
#include "vendor/daisysp/Source/Drums/synthbassdrum.h"
#include "vendor/daisysp/Source/Drums/synthsnaredrum.h"
#include "vendor/daisysp/Source/Drums/hihat.h"
#include "step_lock_shared.h"
#define KICK_FRAMES 144019u
#define SIGNATURE 0xb1e70a5cu
#include "kick_assignment.h"
#include "kick_knobs.h"
#include "drum_models.h"
struct Slot {u32 root,handle,descriptor,provider,file,voice,left,last;daisysp::SyntheticBassDrum kick;};
struct Armed {u32 root,handle,ticket;};
struct State {u32 magic,random,starts,blocks;Slot slots[16];u32 serial;Armed armed[128];u32 ui_serial;};
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
static u32 model(Slot*s){return MODELS[s-K->slots];}
static const u8 snare_defaults[7]={10,45,10,65,70,0,0};
static_assert(sizeof(State)<=0x1500,"Kick state overlaps L7 send state");
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
static void parameters(void *root,u8 *values,u32 engine){
 for(u32 j=0;j<7;j++)values[j]=drum_defaults(engine)[j];
 init();invalidate(0x24043500u,0x24043520u);
 if(KNOBS->magic!=KNOBS_MAGIC)return;
 u32 serial=KNOBS->serial;
 if(!K->ui_serial || K->ui_serial!=serial){invalidate(0x24043520u,0x24043d20u);K->ui_serial=serial;}
 for(u32 i=0;i<128;i++){
  KickKnob *e=&KNOBS->entries[i];u32 before=e->sequence;
  if(!before || (before&1) || e->handle!=W(root,12) || (e->reserved?e->reserved:1)!=engine)continue;
  u8 next[7];for(u32 j=0;j<7;j++)next[j]=e->values[j];
  __asm__ volatile("dmb" ::: "memory");
  if(before!=e->sequence || (KNOBS->serial&1))return;
  if(engine==1?(next[0]<25 || next[0]>180):next[0]>100)return;
  for(u32 j=1;j<7;j++)if(next[j]>100)return;
  for(u32 j=0;j<7;j++)values[j]=next[j];return;
 }
}
extern "C" __attribute__((used)) void kick_parameters(void *root,u8 *values){parameters(root,values,1);}
/* Click shares the existing entry transaction/serial but has separate cache
 * lines. Snapshot sequence is checked after reading both sources. */
static u32 click(void *root,u32 fallback){
 invalidate(0x24043d80u,0x24043e00u);
 if(KNOBS->magic!=KNOBS_MAGIC)return fallback;
 for(u32 i=0;i<128;i++){
  KickKnob *e=&KNOBS->entries[i];u32 seq=e->sequence;
  if(!seq || (seq&1) || e->handle!=W(root,12) || e->reserved!=1)continue;
  u32 value=CLICKS[i];__asm__ volatile("dmb" ::: "memory");
  if(seq==e->sequence && value<=100)return value;
 }return fallback;
}
static void apply(Slot *s,const u8 *background,float ratio){
 u8 values[8];for(u32 j=0;j<7;j++)values[j]=background[j];values[7]=(u8)click((void*)s->root,values[2]);
 for(u32 j=0;j<2;j++){u32 w=VOICE_LOCKS[(s-K->slots)*2+j],k=lock_kind(w);if(synth_model(k)==model(s))values[synth_index(k)]=(u8)decode_value(w);}

 if(model(s)==5){auto *h=hat(s);h->SetFreq((100+values[0]*10.7f)*ratio);h->SetDecay(values[1]*.01f);h->SetTone(values[2]*.01f);h->SetAccent(values[3]*.01f);h->SetNoisiness(values[4]*.01f);return;}
 if(model(s)==3){auto *n=snare(s);n->SetFreq((80+values[0]*12)*ratio);n->SetDecay(values[1]*.01f);n->SetFmAmount(values[2]*.01f);n->SetAccent(values[3]*.01f);n->SetSnappy(values[4]*.01f);return;}
 s->kick.SetFreq(values[0]*ratio);s->kick.SetDecay(values[1]*.01f);
 s->kick.SetTone(values[2]*.01f);s->kick.SetAccent(values[3]*.01f);
 s->kick.SetFmEnvelopeAmount(values[4]*.01f);s->kick.SetFmEnvelopeDecay(values[5]*.01f);
 s->kick.SetDirtiness(values[6]*.01f);s->kick.SetClick(values[7]*.01f);s->kick.UpdateCoefficients();
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
 D[26]=FN(0x08054ec0,u32(*)(void*))(descriptor);D[30]=2;u32 engine=D[26]==KICK_FRAMES?1:D[26]==KICK_FRAMES+2?3:D[26]==KICK_FRAMES+4?5:0;if(!engine)return 0;
 D[28]=FN(0x08054f80,u32(*)(void*))(descriptor);D[30]=3;if(D[28])return 0;
 D[27]=FN(0x08054e00,u32(*)(void*))(descriptor);D[30]=4;if(D[27]!=48000)return 0;
 float probe[32];for(u32 i=0;i<32;i++)probe[i]=0;
 FN(0x08054da0,void(*)(void*,float*,u32,int,u32))(descriptor,probe,32,0,0);
 float mag=fabsf(probe[0]);union {float f;u32 u;} m={mag};D[29]=m.u;D[30]=5;if(mag<0.00000001f || mag>1.000001f)return 0;
 D[30]=6;for(u32 i=0;i<32;i++)if(probe[i]!=(SIGNATURE&(1u<<i)?mag:-mag))return 0;
 D[30]=7;return (int)engine;
}
static u32 now(){return *(volatile u32*)0x30035f40u;}
static Slot *find(void *root,void *descriptor){
 for(u32 i=0;i<16;i++){Slot *s=&K->slots[i];if(s->root==(u32)root && s->handle==W(root,12) && s->descriptor==(u32)descriptor && s->provider==W(descriptor,0) && s->file==W(descriptor,4))return s;}return 0;
}
extern "C" __attribute__((used)) void kick_voice(void *voice,void *root){
 diagnostic_init();D[8]++;D[9]=(u32)root;D[10]=root?W(root,0):0;D[11]=voice?W(voice,12):0;D[12]=1;publish();
 if(!root || W(root,0)!=0x080ac66cu || !voice || !memory(W(voice,12)))return;
 init();void *d=(void*)W(voice,12);Slot *s=find(root,d);
 u32 engine=kick_selected(root)?1:(u32)kick_marker(d);
 if(!engine){
  for(u32 i=0;i<16;i++)if(K->slots[i].root==(u32)root){K->slots[i].left=0;K->slots[i].root=0;K->slots[i].voice=0;}
  D[12]=2;publish();return;
 }
 if(!s)for(u32 i=0;i<16;i++)if(!K->slots[i].left || (u32)(now()-K->slots[i].last)>5000u){s=&K->slots[i];break;}
 if(!s){D[12]=3;publish();return;}
 /* Monophonic per sound. Only touch old voice if still in this native root. */
 if(s->root==(u32)root && s->voice!=(u32)voice && W(root,0x60)<=16)
  for(u32 i=0;i<W(root,0x60);i++)if(W(root,0x20+i*4)==s->voice && s->voice)B((void*)s->voice,0)=0;
 memset((void*)s,0,sizeof(Slot));s->root=(u32)root;s->handle=W(root,12);s->descriptor=(u32)d;s->provider=W(d,0);s->file=W(d,4);s->voice=(u32)voice;s->left=KICK_FRAMES+engine-1;s->last=now();MODELS[s-K->slots]=engine;
 // Accepted-note payload is snapshotted per voice; no pad/background mutation.
 u32 packed=W((void*)0x24046000u,0)==0x374c5042u && W((void*)0x24046000u,8)==(u32)root?W((void*)0x24046000u,12):0;
 for(u32 j=0;j<2;j++)VOICE_LOCKS[(s-K->slots)*2+j]=lock_slot(packed,j);
 if(engine==3)snare(s)->Init(48000);else if(engine==5)hat(s)->Init(48000);else s->kick.Init(48000);u8 values[7];parameters(root,values,engine);apply(s,values,1);if(engine==3)snare(s)->Trig();else if(engine==5)hat(s)->Trig();else s->kick.Trig();K->starts++;D[18]++;D[12]=0;publish();
}
/* Integer/pointer ABI only. Native processing after this handles level, pan,
 * amplitude/filter envelopes, mute and bus mixing, retaining all L8 locks. */
extern "C" __attribute__((used)) int kick_render(void *root,void *voice,void *temp,void *output){
 diagnostic_init();D[13]++;D[14]=(u32)root;D[15]=root?W(root,0):0;D[16]=voice?W(voice,12):0;D[31]=root?W(root,12):0;D[25]=voice && memory(W(voice,12))?W((void*)W(voice,12),0):0;D[17]=1;publish();
 if(!root || W(root,0)!=0x080ac66cu || !voice || !memory(W(voice,12)))return 0;
 init();void *d=(void*)W(voice,12);Slot *s=find(root,d);
 if(!s){if(!kick_selected(root) && !kick_marker(d)){D[17]=2;publish();return 0;}kick_voice(voice,root);s=find(root,d);if(!s){D[17]=3;publish();return 0;}}
 if(s->voice!=(u32)voice){D[17]=4;publish();return 0;}
 u32 n=FN(0x080a1d60,u32(*)(void*))(output);
 D[20]=n;D[21]=(u32)temp;D[22]=W(temp,0);D[23]=W(temp,8);
 if(!n || n>1024 || W(temp,0)<n || !memory(W(temp,8))){D[17]=5;publish();return 0;}
 /* Mark mono and obtain native writable scratch. Never replace its allocation. */
 float *samples=FN(0x08052340,float*(*)(void*))(temp);
 FN(0x08052f00,void(*)(void*,u32))(temp,n);
 /* Same pitch multiplier as the original sample renderer, evaluated per block. */
 u32 pitch_bits=FN(0x080d5880,u32(*)(void*,void*))(root,voice);
 union {u32 bits;float value;} pitch={pitch_bits};
 float ratio=pitch.value;if(!(ratio>0) || ratio>8)ratio=1;
 u8 values[7];parameters(root,values,model(s));apply(s,values,ratio);
 float velocity=*(volatile float*)((u8*)voice+0xb8);if(!(velocity>=0))velocity=0;if(velocity>1)velocity=1;
 for(u32 i=0;i<n;i++){
  float x=s->left?(model(s)==3?snare(s)->Process():model(s)==5?hat(s)->Process():s->kick.Process())*.6f:0;
  if(!(x==x))x=0;if(x>1)x=1;if(x<-1)x=-1;
  /* Last 256 samples fade to exact silence before native voice termination. */
  if(s->left<256)x*=s->left*(1.f/256);
  samples[i]=x*velocity;union {float f;u32 u;} peak={fabsf(x)};if(peak.u>D[24])D[24]=peak.u;if(s->left)s->left--;
 }
 W(voice,0x40)=KICK_FRAMES+model(s)-1-s->left;W(voice,0x44)=0;
 FN(0x08092d00,void(*)(void*,void*,void*,void*))(root,voice,temp,output);
 if(!s->left)B(voice,0)=0;s->last=now();K->blocks++;D[19]++;D[17]=0;publish();return 1;
}
