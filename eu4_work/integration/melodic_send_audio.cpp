#define _Static_assert static_assert
#include "live_shared.h"
#include "melodic_lock_shared.h"
#include "melodic_send_shared.h"
static MelAudio *audio(){if(EC->magic!=EU_MAGIC||EC->bytes!=sizeof(EuBank)||!eu_memory(EC->pointer,sizeof(EuBank)))return 0;u32 p=((EuBank*)EC->pointer)->reserved[0];return eu_memory(p,sizeof(MelAudio))?(MelAudio*)p:0;}
static MelSends *state(){MelAudio *a=audio();return a&&eu_memory(a->sends,sizeof(MelSends))?(MelSends*)a->sends:0;}
static MelVoice *entry(MelAudio *a,u32 voice){u32 start=((voice>>5)^(voice>>13))&(ML_ENTRIES-1);for(u32 i=0;i<ML_ENTRIES;i++){MelVoice *e=a->entries+((start+i)&(ML_ENTRIES-1));if(e->voice==voice)return e;if(!e->voice)return 0;}return 0;}
static void reset(MelBuffer *b,u32 n){b->native[0]=ML_FRAMES;b->native[1]=n;b->native[2]=(u32)b->left;b->native[3]=(u32)b->right;b->native[4]=0x100;for(u32 i=0;i<n;i++)b->left[i]=b->right[i]=0;}
static void add(void *out,void *in){FN(0x080526c0,void(*)(void*,void*))(out,in);}
static void gain(void *g,void *in,void *out){FN(0x0805bc40,void(*)(void*,void*,void*))(g,in,out);}
extern "C" __attribute__((used,retain)) void mel_send_begin(void *root,void *router){
 MelSends *s=state();if(!s)return;s->current=s->source=0;
 u32 bus=W(root,0x284);if(bus>=17)return;u32 input=(u32)router+0x5ac+bus*20;
 MelSendTrack *t=0;for(u32 i=0;i<8;i++)if(s->tracks[i].input==input){t=s->tracks+i;break;}
 if(!t)for(u32 i=0;i<8;i++)if(!s->tracks[i].active&&!s->tracks[i].ready){t=s->tracks+i;break;}
 if(!t)return;t->root=(u32)root;t->input=input;t->router=(u32)router;t->active=t->ready=0;
 MelAudio *a=audio();for(u32 i=0;i<ML_ENTRIES;i++){MelVoice *e=a->entries+i;if(e->root==(u32)root&&(e->delay||e->reverb)&&B((void*)e->voice,0)){t->active=1;break;}}
 if(!t->active)return;
 u32 n=FN(0x080a1d60,u32(*)(void*))((void*)input);if(!n||n>ML_FRAMES){t->active=0;return;}t->n=n;
 for(u32 j=0;j<2;j++){reset(t->unlocked+j,n);reset(t->locked+j,n);}s->current=(u32)(t-s->tracks)+1;
}
extern "C" __attribute__((used,retain)) void *mel_send_voice(void *root,void *voice,void *output){
 MelSends *s=state();if(!s||!s->current)return output;MelSendTrack *t=s->tracks+s->current-1;
 if(t->root!=(u32)root||t->input!=(u32)output)return output;
 s->source=(u32)output;s->voice=(u32)voice;reset(&s->isolated,t->n);return &s->isolated;
}
extern "C" __attribute__((used,retain)) void mel_send_voice_end(){
 MelSends *s=state();if(!s||!s->source||!s->current)return;MelSendTrack *t=s->tracks+s->current-1;
 add((void*)s->source,&s->isolated);MelVoice *e=entry(audio(),s->voice);
 if(!B(&s->isolated,16))for(u32 j=0;j<2;j++){
  u32 word=e&&e->root==t->root?(j?e->reverb:e->delay):0;
  if(!word){add(t->unlocked+j,&s->isolated);continue;}
  union{u32 u;float f;}g={FN(0x080d33c0,u32(*)(int))((int)(word&65535))};
  for(u32 i=0;i<t->n;i++){t->locked[j].left[i]+=s->isolated.left[i]*g.f;t->locked[j].right[i]+=s->isolated.right[i]*g.f;}
 }s->source=0;
}
extern "C" __attribute__((used,retain)) void mel_send_end(void *root){MelSends *s=state();if(!s||!s->current)return;MelSendTrack *t=s->tracks+s->current-1;if(t->root==(u32)root)t->ready=t->active;s->current=s->source=0;}
static MelSendTrack *find(MelSends *s,u32 key,int strip){for(u32 i=0;i<8;i++){MelSendTrack *t=s->tracks+i;if(t->ready&&(strip?t->strip:t->input)==key)return t;}return 0;}
extern "C" __attribute__((used,retain)) void mel_send_prepare(void *strip,void *input){MelSends *s=state();if(!s)return;MelSendTrack *t=find(s,(u32)input,0);if(!t)return;t->strip=(u32)strip;for(u32 i=0;i<6;i++)t->level[i]=W(strip,0x20+i*4);}
extern "C" __attribute__((used,retain)) void mel_send_duck(void *strip){MelSends *s=state();if(!s)return;MelSendTrack *t=find(s,(u32)strip,1);if(t)for(u32 i=0;i<28;i++)t->duck[i]=W(strip,0x98+i*4);}
extern "C" __attribute__((used,retain)) void mel_send_mix(void *control,void *input,void *bus,void *strip){
 MelSends *s=state();MelSendTrack *t=s?find(s,(u32)strip,1):0;
 if(!t){gain(control,input,bus);return;}
 u32 j=(u32)control==(u32)strip+0x50?0:1,n=t->n;
 reset(&s->weighted,n);gain(control,t->unlocked+j,&s->weighted);add(&s->weighted,t->locked+j);
 reset(&s->post,n);u32 level[6];for(u32 i=0;i<6;i++)level[i]=t->level[i];gain(level,&s->weighted,&s->post);
 float pan=*(float*)strip,l=pan>0?1-pan:1,r=pan<0?1+pan:1;
 for(u32 i=0;i<n;i++){s->post.left[i]*=l;s->post.right[i]*=r;}
 u32 duck[28];for(u32 i=0;i<28;i++)duck[i]=t->duck[i];FN(0x080635e0,void(*)(void*,void*,void*))(duck,(void*)t->router,&s->post);
 add(bus,&s->post);if(j)t->ready=0;
}
