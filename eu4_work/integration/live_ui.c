/* EU2 settings, native allocation and versioned per-track/clip-row XML. */
#include "live_ui.h"
static void clear(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static EuBank *bank(int create){
 if(EC->magic==EU_MAGIC&&EC->bytes==sizeof(EuBank)&&eu_memory(EC->pointer,sizeof(EuBank)))return (EuBank*)EC->pointer;
 if(!create)return 0;
 u32 p=W((void*)0x3000004c,0),end=W((void*)0x30000048,0),n=(sizeof(EuBank)+31)&~31u;
 if(!eu_memory(p,n)||end<p||end-p<n)return 0;
 u32 allocated=FN(0x08104c08,u32(*)(u32))(n);if(allocated!=p)return 0;
 clear((void*)p,n);EuBank *b=(EuBank*)p;b->epoch=1;b->serial=2;
 EC->magic=0;EC->pointer=p;EC->bytes=sizeof(EuBank);EC->epoch=1;__asm__ volatile("dmb" ::: "memory");EC->magic=EU_MAGIC;return b;
}
static EuRecord *record(EuRecord *r,u32 *count,u32 owner,u32 row,int create){
 for(u32 i=0;i<*count;i++)if(r[i].owner==owner&&r[i].row==row)return r+i;
 if(!create||*count>=EU_RECORDS||!owner||row>=16)return 0;
 EuRecord *out=r+(*count)++;clear(out,sizeof(*out));out->owner=owner;out->row=row;out->serial=2;return out;
}
static EuRecord *selected(Euclid *e,int create){
 EuBank *b=bank(create);u32 row=16;if(!b||e->pad>=16||!e->valid)return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&e->seq,0x73,&row)||row>=16)return 0;
 return record(b->records,&b->count,e->owner,row,create);
}
int live_begin(Euclid *e){return selected(e,1)!=0;}
EuPad live_value(Euclid *e){
 EuRecord *r=selected(e,0);EuPad p={0,0};if(r)p=r->pads[e->pad];
 if(!eu_pad_valid(p))p=eu_pack(e->steps,e->hits<=e->steps?e->hits:0,0,100,0);return p;
}
int live_edit(Euclid *e,u32 key,int value){
 if(key==0){e->pad=value<1?0:value>16?15:(u32)value-1;return 1;}
 if(key==6){e->preview=value<1?1:value>8?8:(u32)value;return 1;}
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);
 u32 n=eu_length(p),k=eu_pulses(p),rot=eu_rotation(p),vel=eu_base(p),on=eu_enabled(p);
 if(key==1){n=value<1?1:value>256?256:(u32)value;if(k>n)k=n;if(rot>=n)rot%=n;}
 if(key==2)k=value<0?0:(u32)value>n?n:(u32)value;
 if(key==3)rot=value<0?0:(u32)value>=n?n-1:(u32)value;
 if(key==4)vel=value<1?1:value>127?127:(u32)value;
 if(key==5)on=value>0;
 u32 serial=(r->serial+2)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->pads[e->pad]=eu_pack(n,k,rot,vel,on);r->pads[e->pad].velocity=eu_dynamics_gate(vel,eu_mode(p),eu_depth(p),eu_gate(p));r->pads[e->pad].pattern|=p.pattern&(1u<<26);__asm__ volatile("dmb" ::: "memory");r->serial=serial;
 FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
static int read(void *p,const char *name,u32 *v){void *a=p?FN(0x08109c64,void*(*)(void*,const char*))(p,name):0;return a&&!FN(0x08109566,int(*)(void*,void*))(a,v);}
static void write(void *p,const char *name,u32 v){void *a=FN(0x08109cdc,void*(*)(void*,const char*))(p,name);if(a)FN(0x0810958e,void(*)(void*,u32))(a,v);}
static void name(char *s,u32 row,u32 pad,u32 word){const char *p="bento_eu2_00_00_0";u32 i=0;do{s[i]=p[i];}while(p[i++]);s[10]='0'+row/10;s[11]='0'+row%10;s[13]='0'+pad/10;s[14]='0'+pad%10;s[16]='0'+word;}
void live_save(void *object,void *params){
 EuBank *b=bank(0);if(!b||!object||!params)return;u32 owner=W(object,0x10);if(!owner||(B(object,4)!=14&&!eu_pitched_type(B(object,4))))return;
 write(params,"bento_eu2_version",1);
 for(u32 i=0;i<b->count;i++){EuRecord *r=b->records+i;if(r->owner!=owner)continue;
  for(u32 pad=0;pad<16;pad++){EuPad p=r->pads[pad];if(!eu_pad_valid(p))continue;char key[20];name(key,r->row,pad,0);write(params,key,p.pattern);name(key,r->row,pad,1);write(params,key,eu_base(p));name(key,r->row,pad,2);write(params,key,eu_mode(p));name(key,r->row,pad,3);write(params,key,eu_depth(p));
   if(eu_record_melodic(r)){name(key,r->row,pad,4);write(params,key,eu_record_pitch(r,pad));name(key,r->row,pad,5);write(params,key,eu_gate(p));}}
 }
}
void live_load(void *node,void *object){
 if(!node||!object||(B(object,4)!=14&&!eu_pitched_type(B(object,4)))||!W(object,0x10))return;
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");u32 ver=0;
 if(!read(params,"bento_eu2_version",&ver)||ver!=1)return;EuBank *b=bank(1);if(!b)return;
 u32 owner=W(object,0x10);
 for(u32 row=0;row<16;row++)for(u32 pad=0;pad<16;pad++){
  char key[20];EuPad p={0,0};name(key,row,pad,0);if(!read(params,key,&p.pattern))continue;name(key,row,pad,1);if(!read(params,key,&p.velocity)||!eu_pad_valid(p))continue;
  u32 mode=0,depth=0;name(key,row,pad,2);read(params,key,&mode);name(key,row,pad,3);read(params,key,&depth);if(mode>9)mode=0;if(depth>100)depth=0;u32 pitch=0,gate=0;name(key,row,pad,4);int mel=read(params,key,&pitch)&&pitch<=127;name(key,row,pad,5);if(mel)read(params,key,&gate);if(gate>64)gate=0;
  p.velocity=eu_dynamics_gate(eu_base(p),mode,depth,mel?gate:0);
  EuRecord *r=record(b->pending,&b->pending_count,owner,row,1);if(r){r->pads[pad]=p;if(mel){r->reserved[0]|=EU_MELODIC;eu_record_set_pitch(r,pad,pitch);}}
 }
}
void melodic_register_tracks(void);
void live_finish(void){
 EuBank *b=bank(0);if(!b)return;
 b->serial|=1;__asm__ volatile("dmb" ::: "memory");clear(b->records,sizeof(b->records));b->count=b->pending_count;
 for(u32 i=0;i<b->count;i++)b->records[i]=b->pending[i];clear(b->pending,sizeof(b->pending));b->pending_count=0;
 melodic_register_tracks();
 b->epoch++;if(!b->epoch)b->epoch=1;__asm__ volatile("dmb" ::: "memory");b->serial=(b->serial+1)&~1u;if(!b->serial)b->serial=2;
}

static int position(EuBank *b,u32 owner,u32 row,u32 *step);
int live_position(Euclid *e,u32 *step){
 EuBank *b=bank(0);u32 row=16;if(!b||!e->valid||!step)return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&e->seq,0x73,&row)||row>=16)return 0;
 return position(b,e->owner,row,step);
}
/* CH6 piano-roll lanes: the committed record and the published phase for one
   sequence. *step = ~0 while the generator is not playing. */
int live_lanes(u32 seq,u32 owner,EuPad *pads,u8 *pitch,u32 *mel,u32 *step){
 EuBank *b=bank(0);u32 row=16;if(!b||(b->serial&1))return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&seq,0x73,&row)||row>=16)return 0;
 u32 count=b->count;EuRecord *r=record(b->records,&count,owner,row,0);if(!r)return 0;
 for(u32 i=0;i<16;i++){pads[i]=r->pads[i];pitch[i]=(u8)eu_record_pitch(r,i);}*mel=(u32)eu_record_melodic(r);
 if(!position(b,owner,row,step))*step=~0u;return 1;
}
static int position(EuBank *b,u32 owner,u32 row,u32 *step){
 for(u32 i=0;i<16;i++){
  volatile EuRuntime *r=b->runtime+i;
  u32 serial=r->reserved[3],epoch=r->epoch,rr=r->row;
  if(!serial||(serial&1)||epoch!=b->epoch||r->owner!=owner||rr!=row)continue;
  u32 value=r->reserved[1],valid=r->reserved[2];__asm__ volatile("dmb" ::: "memory");
  if(serial==r->reserved[3]&&valid){*step=value;return 1;}
 }
 return 0;
}

/* UI generation commits native notes before publishing the playback mode.
   On failure, the existing pattern/settings remain active. */
int live_generate(Euclid *e,u32 key,int value){
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);
 if(key==5&&value==0)return live_edit(e,5,0);
 if(key==5&&eu_native(p))return live_edit(e,5,1);
 Euclid next=*e;next.steps=eu_length(p);next.hits=eu_pulses(p);next.rotate=eu_rotation(p);next.velocity=100;
 if(key==1){next.steps=value<1?1:value>256?256:(u32)value;if(next.hits>next.steps)next.hits=next.steps;if(next.rotate>=next.steps)next.rotate%=next.steps;}
 if(key==2)next.hits=value<0?0:(u32)value>next.steps?next.steps:(u32)value;
 if(key==3)next.rotate=value<0?0:(u32)value>=next.steps?next.steps-1:(u32)value;
 if(key==4)next.velocity=value<1?1:value>127?127:(u32)value;
 int status=key==4&&eu_native(p)?eu_velocity(&next,MODEL):eu_apply(&next,MODEL);
 e->scratch=next.scratch;e->status=status;if(status!=EU_OK&&status!=EU_SAME)return 0;
 u32 serial=(r->serial+2)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->pads[e->pad]=eu_pack(next.steps,next.hits,next.rotate,next.velocity,1);r->pads[e->pad].pattern|=1u<<26;r->pads[e->pad].velocity=eu_dynamics_gate(next.velocity,eu_mode(p),eu_depth(p),eu_mel(e)?eu_mel_gate(e):eu_gate(p));
 if(eu_mel(e)){r->reserved[0]=(r->reserved[0]&~0xf00u)|EU_MELODIC|(((e->preview>>20)&15u)<<8);eu_record_set_pitch(r,e->pad,eu_mel_pitch(e));}
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}

int live_dynamic(Euclid *e,u32 key,int value){
 EuRecord *r=selected(e,1);if(!r)return 0;EuPad p=live_value(e);u32 mode=eu_mode(p),depth=eu_depth(p);
 if(key==4)mode=value<0?0:value>9?9:(u32)value;else if(key==6)depth=value<0?0:value>100?100:(u32)value;else return 0;
 u32 serial=(r->serial+2u)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");p.velocity=eu_dynamics_gate(100,mode,depth,eu_gate(p));r->pads[e->pad]=p;__asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}

/* CH3 accessors for melodic rows (pitched piano roll). */
int live_row_pitch(Euclid *e,u32 row,u32 *pitch){
 EuRecord *r=selected(e,0);if(!r||!eu_record_melodic(r)||row>=16)return 0;EuPad p=r->pads[row];if(!eu_pad_valid(p))return 0;*pitch=eu_record_pitch(r,row);return 1;
}
int live_pitch_owner(Euclid *e,u32 pitch,u32 except){
 EuRecord *r=selected(e,0);if(!r||!eu_record_melodic(r))return -1;
 for(u32 i=0;i<16;i++){EuPad p=r->pads[i];if(i!=except&&eu_pad_valid(p)&&eu_enabled(p)&&eu_record_pitch(r,i)==pitch)return (int)i;}return -1;
}
int live_assign_pitch(Euclid *e,u32 pitch){
 EuRecord *r=selected(e,1);if(!r||pitch>127)return 0;EuPad p=live_value(e);
 u32 serial=(r->serial+2u)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->reserved[0]=(r->reserved[0]&~0xf00u)|EU_MELODIC|(((e->preview>>20)&15u)<<8);eu_record_set_pitch(r,e->pad,pitch);r->pads[e->pad]=p;
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
int live_set_gate(Euclid *e,u32 gate){
 EuRecord *r=selected(e,1);if(!r||gate<1||gate>64)return 0;EuPad p=live_value(e);
 u32 serial=(r->serial+2u)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 p.velocity=(p.velocity&~(63u<<24))|((gate&63u)<<24);r->pads[e->pad]=p;
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return 1;
}
/* CH6 chord pad audition mailbox (see live_shared.h). M4 writes ChordMail only. */
__attribute__((used,retain)) int chord_audition_publish(int active,const u8 *count,const signed char *off,u32 velocity){
 EuBank *b=bank(active);if(!b)return 0;volatile ChordMail *m=&b->chord_mail;
 if(!active&&!m->active)return 1;
 u32 s=m->serial|1u;m->serial=s;__asm__ volatile("dmb" ::: "memory");
 m->active=active?1u:0u;m->velocity=velocity>127?127:velocity; /* CH8: pads scaled by the chord's Velocity */
 if(active)for(u32 pc=0;pc<12;pc++){u32 n=count[pc];m->count[pc]=(u8)(n>CA_VOICES?CA_VOICES:n);for(u32 i=0;i<CA_VOICES;i++)m->off[pc][i]=i<n?off[pc*CA_VOICES+i]:0;}
 __asm__ volatile("dmb" ::: "memory");m->serial=s+1u;return 1;
}
u32 chord_mail_active(void){EuBank *b=bank(0);if(!b)return 0;volatile ChordMail *m=&b->chord_mail;return m->active&&!(m->serial&1u);}
u32 chord_pub_serial(void){EuBank *b=bank(0);return b?((volatile ChordPub*)&b->chord_pub)->serial:0;}
u32 chord_mail_serial(void){EuBank *b=bank(0);return b?((volatile ChordMail*)&b->chord_mail)->serial:0;}
__attribute__((used,retain)) int chord_pad_pitch(u32 pad){
 EuBank *b=bank(0);if(!b||pad>=16)return -1;u8 v=((volatile ChordPub*)&b->chord_pub)->pitch[pad];return v&0x80u?(int)(v&127u):-1;
}
/* CH7 (owner): recording takes over. Generated drum hits always sit exactly on
   their pattern steps. When notes are added (the project's next note ID at
   project+68 changes), a note on a generator pad of the current clip that is
   off the grid, past the lane length or not on a pattern step was recorded or
   drawn: that pad goes back to Manual (as Shift+Left). The generated notes stay
   in the clip as ordinary notes, so they and the recorded hits all play. The
   last seen ID is kept in EuControl.reserved[0] (UI-written, ignored by M7). */
__attribute__((used,retain)) u32 live_record_check(void){
 EuBank *b=bank(0);void *project=(void*)W(MODEL,0);if(!b||!project||(b->serial&1))return 0;
 u32 next=W(project,0x68);if(next==EC->reserved[0])return 0;EC->reserved[0]=next;
 u32 owner=0,seq=W(MODEL,0x144),row=16;void *node=0;
 if(!FN(0x08133cfc,int(*)(void*,void*))(MODEL,&owner)||FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&owner)!=14)return 0;
 if(!FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&seq,0x73,&row)||row>=16)return 0;
 u32 count=b->count;EuRecord *r=record(b->records,&count,owner,row,0);if(!r||eu_record_melodic(r))return 0;
 if(!FN(0x0812dfe8,int(*)(void*,u32,void*))(project,seq,&node)||!node)return 0;
 void *c=(u8*)node+12;u32 n=W(c,0x3000),foreign=0,raw[6];if(n>2000)return 0;
 for(u32 i=0;i<n;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,raw)||B(raw,0)!=1)continue;u32 pad=H(raw,2);if(pad>=16)continue;
  EuPad p=r->pads[pad];if(!eu_enabled(p))continue;
  u32 L=eu_length(p),k=eu_pulses(p),rot=eu_rotation(p),t=raw[1],at=t/960;
  if(!eu_native(p)||t%960||at>=L||((((at+L-rot)%L)*k)%L)>=k)foreign|=1u<<pad;
 }
 if(!foreign)return 0;
 u32 serial=(r->serial+2)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");
 for(u32 i=0;i<16;i++)if(foreign&(1u<<i))r->pads[i].pattern&=~(1u<<25);
 __asm__ volatile("dmb" ::: "memory");r->serial=serial;FN(0x0813130c,void(*)(void*))(MODEL);return foreign;
}
/* CH9: chord pads currently held (M7-published); recorded chords are only
   reshaped to the Rhythm once every chord pad is up. */
__attribute__((used,retain)) u32 chord_pads_held(void){EuBank *b=bank(0);return b?((volatile ChordPub*)&b->chord_pub)->held:0;}

#include "melodic_lock_shared.h"
#include "melodic_send_shared.h"
/* A separate checked allocation: no EuBank ABI or fixed RAM boundary changes. */
void mel_audio_prepare(u32 owner){
 EuBank *b=bank(1);if(!b||!owner)return;
 if(!b->reserved[0]){
  u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),n=sizeof(MelAudio)+sizeof(MelSends);
  if(!eu_memory(p,n)||end<p||end-p<n+32)return;
  if(FN(0x08104c08,u32(*)(u32))(n)!=p)return;clear((void*)p,n);
  ((MelAudio*)p)->sends=p+sizeof(MelAudio);
  __asm__ volatile("dmb" ::: "memory");b->reserved[0]=p;
 }
 MelAudio *s=(MelAudio*)b->reserved[0];for(u32 i=0;i<8;i++)if(s->owners[i]==owner)return;
 s->serial|=1;__asm__ volatile("dmb" ::: "memory");s->owners[s->next++&7]=owner;
 __asm__ volatile("dmb" ::: "memory");s->serial=(s->serial+1)&~1u;if(!s->serial)s->serial=2;
}

/* P18: keep the published Step Len current (project load, Step Len changes). */
int live_mel_unit(Euclid *e){
 EuRecord *r=selected(e,0);if(!r||!eu_record_melodic(r))return 0;u32 want=(r->reserved[0]&~0xf00u)|(((e->preview>>20)&15u)<<8);if(r->reserved[0]==want)return 0;
 u32 serial=(r->serial+2u)&~1u;if(!serial)serial=2;r->serial=serial|1;__asm__ volatile("dmb" ::: "memory");r->reserved[0]=want;__asm__ volatile("dmb" ::: "memory");r->serial=serial;return 1;
}
