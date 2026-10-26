#define _Static_assert static_assert
#include "live_shared.h"
#define LOCK_M7
#include "step_lock_shared.h"
static void invalidate(u32 a,u32 n){__asm__ volatile("dsb" ::: "memory");if(W((void*)0xe000ed14u,0)&(1u<<16))for(u32 end=a+n;a<end;a+=32)W((void*)0xe000ef5cu,0)=a;__asm__ volatile("dsb" ::: "memory");}
static EuBank *bank(){invalidate(EU_CONTROL_ADDR,32);if(EC->magic!=EU_MAGIC||EC->bytes!=sizeof(EuBank)||!eu_memory(EC->pointer,sizeof(EuBank)))return 0;EuBank *b=(EuBank*)EC->pointer;invalidate((u32)b,32);return b;}

#include "melodic_lock_shared.h"
static float gain_db(int db){
 if(db<=-96000)return 0;float x=(float)db/6020.599913f;int n=(int)x;if((float)n>x)n--;
 float f=(x-(float)n)*.6931471805599453f;
 float y=1+f*(1+f*(.5f+f*(.1666666667f+f*(.0416666667f+f*(.0083333333f+f*.0013888889f)))));
 union{u32 u;float f;}scale={(u32)(n+127)<<23};return y*scale.f;
}
static MelAudio *mel_state(int coherent){
 EuBank *b=coherent?bank():(EC->magic==EU_MAGIC?(EuBank*)EC->pointer:0);
 if(!b)return 0;u32 p=b->reserved[0];if(!eu_memory(p,sizeof(MelAudio)))return 0;
 return (MelAudio*)p;
}
extern "C" __attribute__((used,retain)) void mel_pending(void *seq,void *router,u32 pad,u32 word){
 MelAudio *s=mel_state(1);if(!s)return;s->queue=s->word=0;
 if(!word||!has_locks(word)||!seq||!router)return;
 invalidate((u32)s,64);u32 serial=s->serial;int enabled=0;
 if(!serial||(serial&1))return;
 for(u32 i=0;i<8;i++)if(s->owners[i]==W(seq,12))enabled=1;
 __asm__ volatile("dmb" ::: "memory");if(!enabled||serial!=s->serial)return;
 u32 h=H(seq,0x10);if(pad<16&&W(seq,0x86dc+4*pad)!=0xffffff00u)h=W(seq,0x86dc+4*pad);
 u32 n=W(router,0x508);if(n>160)return;
 for(u32 i=0;i<n;i++)if(W(router,8+i*8)==h){s->queue=W(router,4)+W(router,12+i*8)*0x604;s->word=word;break;}
}
extern "C" __attribute__((used,retain)) void mel_pending_clear(){MelAudio *s=mel_state(0);if(s)s->queue=s->word=0;}
extern "C" __attribute__((used,retain)) void mel_queue(void *queue,void *record){
 MelAudio *s=mel_state(0);if(!s||!s->word||s->queue!=(u32)queue||B(record,0)!=0x12)return;
 B(record,1)=ML_MARK;H(record,2)=ML_SIGNATURE;W(record,20)=s->word;
}
static int generic_root(void *r){u32 vt=W(r,0);return vt>=0x08040000u&&vt<0x080d0000u&&W((void*)vt,8)==0x0807eb21u;}
extern "C" __attribute__((used,retain)) void mel_note(void *root,void *record){
 MelAudio *s=mel_state(1);if(!s)return;s->note_root=generic_root(root)?(u32)root:0;s->note_word=0;
 if(s->note_root&&B(record,0)==0x12&&B(record,1)==ML_MARK&&H(record,2)==ML_SIGNATURE&&has_locks(W(record,20)))s->note_word=W(record,20);
}
static MelVoice *mel_entry(MelAudio *s,void *root,void *voice,int create){
 u32 start=(((u32)voice>>5)^((u32)voice>>13))&(ML_ENTRIES-1);
 for(u32 i=0;i<ML_ENTRIES;i++){MelVoice *e=s->entries+((start+i)&(ML_ENTRIES-1));
  if(e->voice==(u32)voice)return e->root==(u32)root||create?e:0;
  if(!e->voice)return create?e:0;
 }return 0;
}
extern "C" __attribute__((used,retain)) void mel_attach(void *root,void *voice){
 MelAudio *s=mel_state(0);if(!s||!generic_root(root))return;
 MelVoice *e=mel_entry(s,root,voice,1);if(!e)return;
 e->voice=(u32)voice;e->root=(u32)root;e->word=s->note_root==(u32)root?s->note_word:0;e->gain=1;e->filter=e->resonance=e->decay=e->release=e->delay=e->reverb=0;
 for(u32 j=0;j<2;j++){u32 w=lock_slot(e->word,j),k=lock_kind(w);int v=decode_value(w);
  if(k==1)e->gain=v<=-96000?0:gain_db(v);
  if(k==4)e->filter=w;if(k==5)e->resonance=w;
  if(k==7)e->decay=w;if(k==9)e->release=w;if(k==10)e->delay=w;if(k==11)e->reverb=w;
  if(k==3)*(float*)((u8*)voice+0x18)=(float)(v+1000)/2000.0f;
 }
}
extern "C" __attribute__((used,retain)) void mel_context(void *root,void *voice){
 MelAudio *s=mel_state(0);if(!s)return;s->voice=s->active_word=s->active_filter=s->active_resonance=0;s->gain=1;
 MelVoice *e=mel_entry(s,root,voice,0);if(!e||!e->word)return;
 s->voice=(u32)voice;s->active_word=e->word;s->gain=e->gain;s->active_filter=e->filter;s->active_resonance=e->resonance;
}
extern "C" __attribute__((used,retain)) void mel_context_clear(){MelAudio *s=mel_state(0);if(s)s->voice=s->active_word=0;}
static int mel_apply(void *parameter,u32 w){
 u32 copy[16];for(u32 j=0;j<16;j++)copy[j]=W(parameter,j*4);
 struct {u32 opaque;float value;} source={0,(float)decode_value(w)/1000.0f};
 copy[0]=(u32)&source;copy[1]=0x3f800000u;copy[8]=copy[9]=0;
 u32 count=0;for(u32 j=0;j<5;j++)if(copy[2*j])((u8*)copy)[0x28+count++]=(u8)j;copy[12]=count;
 FN(0x080d1f00,void(*)(void*))(copy);W(parameter,0x3c)=copy[15];return 1;
}
extern "C" __attribute__((used,retain)) int mel_envelope(void *parameter,u32 kind){
 MelAudio *s=mel_state(0);if(!s)return 0;
 u32 voice=(u32)parameter-(kind==7?0x200u:0x240u),start=((voice>>5)^(voice>>13))&(ML_ENTRIES-1);
 for(u32 i=0;i<ML_ENTRIES;i++){MelVoice *e=s->entries+((start+i)&(ML_ENTRIES-1));if(!e->voice)return 0;if(e->voice!=voice)continue;
  u32 w=kind==7?e->decay:e->release;return w?mel_apply(parameter,w):0;
 }return 0;
}
extern "C" __attribute__((used,retain)) int mel_evaluate(void *parameter){
 MelAudio *s=mel_state(0);if(!s||!s->voice||!s->active_word)return 0;
 u32 kind=(u32)parameter==s->voice+0x5c4?4u:(u32)parameter==s->voice+0x60c?5u:0;if(!kind)return 0;
 u32 w=kind==4?s->active_filter:s->active_resonance;if(!w)return 0;
 return mel_apply(parameter,w);
}

extern "C" __attribute__((used,retain)) void mel_level(void *voice,void *buffer){
 MelAudio *s=mel_state(0);if(!s||s->voice!=(u32)voice||s->gain==1)return;
 u32 n=FN(0x080a1d60,u32(*)(void*))(buffer);if(n>1024)return;
 float *left=0,*right=0;
 if(B(buffer,0x11))FN(0x08052ea0,void(*)(void*,void*,void*))(buffer,&left,&right);
 else left=FN(0x08052e20,float*(*)(void*))(buffer);
 if(left)for(u32 i=0;i<n;i++)left[i]*=s->gain;
 if(right&&right!=left)for(u32 i=0;i<n;i++)right[i]*=s->gain;
}
