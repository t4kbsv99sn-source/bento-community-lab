/* EU2: native-clock drum generation. No allocation or UI calls on M7. */
#define _Static_assert static_assert
#include "live_shared.h"
#define LOCK_M7
#include "step_lock_shared.h"
#include "lock_api.h"
#include "velocity.h"
static void invalidate(u32 a,u32 n){__asm__ volatile("dsb" ::: "memory");if(W((void*)0xe000ed14u,0)&(1u<<16))for(u32 end=a+n;a<end;a+=32)W((void*)0xe000ef5cu,0)=a;__asm__ volatile("dsb" ::: "memory");}
static EuBank *bank(){
 invalidate(EU_CONTROL_ADDR,32);if(EC->magic!=EU_MAGIC||EC->bytes!=sizeof(EuBank)||!eu_memory(EC->pointer,sizeof(EuBank)))return 0;
 EuBank *b=(EuBank*)EC->pointer;invalidate((u32)b,32);if(!b->serial||(b->serial&1)||b->count>EU_RECORDS)return 0;return b;
}
/* M7-owned display snapshot, in the existing runtime's reserved first 64 bytes.
   M4 only reads. Publish on grid boundaries or transport stop, never per sample. */
static void phase(EuRuntime *r,u32 step,u32 valid){
 if(!r || (r->reserved[1]==step&&r->reserved[2]==valid))return;
 u32 serial=(r->reserved[3]+2)&~1u;if(!serial)serial=2;
 r->reserved[3]=serial|1;__asm__ volatile("dmb" ::: "memory");
 r->reserved[1]=step;r->reserved[2]=valid;
 __asm__ volatile("dmb" ::: "memory");r->reserved[3]=serial;
 __asm__ volatile("dsb" ::: "memory");
 if(W((void*)0xe000ed14u,0)&(1u<<16))for(u32 a=(u32)r;a<(u32)r+64;a+=32)W((void*)0xe000ef68u,0)=a;
 __asm__ volatile("dsb" ::: "memory");
}
static int rowof(void *s){u32 p=W(s,0x86c0),start=(u32)s+0x240;if(p<start||p>=start+16*0x848||(p-start)%0x848)return -1;return (p-start)/0x848;}
static EuRuntime *runtime(EuBank *b,void *s,int create){
 EuRuntime *free=0;for(u32 i=0;i<16;i++){EuRuntime *r=b->runtime+i;if(r->sequence==(u32)s)return r;if(!r->sequence&&!free)free=r;}
 if(!create||!free)return 0;for(u32 i=0;i<sizeof(*free)/4;i++)((u32*)free)[i]=0;free->sequence=(u32)s;return free;
}
static int snapshot(EuBank *b,void *s,u32 row,EuPad *out,u32 *mel,u8 *pitch){
 u32 serial=b->serial,epoch=b->epoch,count=b->count;EuRecord *found=0;
 for(u32 i=0;i<count;i++){EuRecord *r=b->records+i;invalidate((u32)r,32);if(r->owner==W(s,12)&&r->row==row){found=r;break;}}
 if(!found)return 0;invalidate((u32)found,sizeof(*found));u32 rs=found->serial;if(!rs||(rs&1))return 0;
 *mel=eu_record_melodic(found);for(u32 i=0;i<16;i++){EuPad p=found->pads[i];if(!eu_pad_valid(p)){p.pattern=0;p.velocity=0;}out[i]=p;pitch[i]=(u8)eu_record_pitch(found,i);}
 __asm__ volatile("dmb" ::: "memory");invalidate((u32)found,32);invalidate((u32)b,32);
 return rs==found->serial&&serial==b->serial&&epoch==b->epoch;
}
extern "C" __attribute__((used,retain)) void live_restart(void *s){
 if((int)W(s,0x14)>=0)return;EuBank *b=bank();if(!b)return;EuRuntime *r=runtime(b,s,0);if(r){phase(r,0,0);r->ready=0;r->epoch=0;}
}
extern "C" __attribute__((used,retain)) int live_skip(void *s,u32 pad,u32 pitch){
 EuBank *b=bank();if(!b)return 0;EuRuntime *r=runtime(b,s,0);
 if(!r||!r->ready||r->epoch!=b->epoch||r->owner!=W(s,12)||(int)r->row!=rowof(s))return 0;
 if(r->melodic){(void)pitch;return 0;} /* CH4: melodic rows are a layer on top of the clip */
 if(pad>=16)return 0;return eu_enabled(r->pads[pad])&&eu_pad_valid(r->pads[pad]);
}
/* Native active-note table (sequence+238 count; entry i at sequence+i*16): byte
   +38 active, H+3A pad, W+3C note, i64 +40 end time. The stock renderer sends
   the note-off when the end time passes, exactly as for its own notes. */
static void mel_play(void *s,u32 pitch,u32 vel,u32 frame,void *clock,void *router,u32 len_ticks,u32 period){
 u8 *base=(u8*)s;u32 count=W(s,0x238);if(count>32)return;int found=-1;
 for(u32 i=0;i<count;i++){u8 *e=base+i*16;if(e[0x38]&&W(e,0x3c)==pitch&&H(e,0x3a)==0){found=(int)i;break;}}
 if(found>=0)FN(0x0805fe00,void(*)(void*,u32,u32,u32,void*))(s,pitch,frame,0,router);
 FN(0x0805f8e0,void(*)(void*,u32,u32,u32,u32,void*))(s,pitch,vel,frame,0,router);
 i64 now=0;FN(0x080a21c0,void(*)(void*,void*,int))(&now,clock,(int)frame);
 i64 end=now+(i64)(((u64)period*(u64)(len_ticks?len_ticks:960u))/960u);
 if(found<0){if(count>=32)return;found=(int)count;W(s,0x238)=count+1;}
 u8 *e=base+(u32)found*16;W(e,0x3c)=pitch;H(e,0x3a)=0;e[0x38]=1;*(i64*)(e+0x40)=end;
}
extern "C" __attribute__((used,retain)) u32 locks_filter(void *s,u32 w,u32 loop){
 u32 c=lc_condition(w);if(!c)return lc_word(w);
 int pass=1;if(c<100)pass=(u32)FN(0x080a40b8,int(*)())()%100u<=c;
 else{u32 i=c-100,b=2;while(i>=b){i-=b;b++;}pass=loop%b==i;}
 return pass?lc_word(w):0;
}
extern "C" __attribute__((used,retain)) u32 locks_native_filter(void *s,u32 w){
 if(!lc_address(w))return w;u32 loop=0;for(u32 i=0;i<16;i++){void *c=(void*)(0x24048a60u+i*32);if(W(c,0)==(u32)s && W(c,4)==W(s,12)&&W(c,8)==W(s,0x86c0)){loop=W(c,12);break;}}
 return locks_filter(s,w,loop);
}
extern "C" __attribute__((used,retain)) void live_render(void *s,void *clock,u32 offset,u32 frames,void *router){
 EuBank *b=bank();if(!b)return;EuRuntime *r=runtime(b,s,0);if(r)r->ready=0;
 if(!B(s,0x20)||!clock||!router||frames>1024||offset>1024||offset+frames>1024){phase(r,0,0);return;}
 int row=rowof(s);if(row<0){phase(r,0,0);return;}EuPad pads[16];u32 mel=0;u8 pitch[16];if(!snapshot(b,s,(u32)row,pads,&mel,pitch))return;
 int any=0;for(u32 i=0;i<16;i++)if(eu_enabled(pads[i]))any=1;if(!any){phase(r,0,0);return;}
 if(!r)r=runtime(b,s,1);if(!r)return;
 void *clip=(void*)W(s,0x86c0);u32 grid=W(clip,0);if(grid>=15)return;
 float scale=((const float*)0x080bdbecu)[grid];u32 period=(u32)(scale*960.0f+0.5f);if(!period||period>30720)return;
 if(r->epoch!=b->epoch||r->owner!=W(s,12)||r->row!=(u32)row||r->reserved[0]!=period){
  r->origin=*(i64*)((u8*)clip+0x20);r->next=r->origin;r->step=0;
  i64 start=0;FN(0x080a21c0,void(*)(void*,void*,int))(&start,clock,(int)offset);
  if(start>r->origin){i64 steps=FN(0x080a34f4,i64(*)(i64,i64))(start-r->origin,(i64)period);r->step=(u32)steps;r->next=r->origin+steps*period;}
  r->row=(u32)row;r->owner=W(s,12);r->epoch=b->epoch;r->reserved[0]=period;
 }
 for(u32 i=0;i<16;i++){r->pads[i]=pads[i];r->pitch[i]=pitch[i];}r->melodic=mel;r->ready=1;
 /* Work is bounded even if a transport discontinuity is not signalled. */
 for(u32 work=0;work<32;work++){
  int frame=FN(0x080a2200,int(*)(void*,void*))(clock,&r->next);if(frame>=(int)(offset+frames))return;
  if(frame>=(int)offset){
   u32 mask=0,native=0,locks[16]={0},vel[16]={0},cond[16]={0},ranks[16]={0},totals[16]={0},bits[16][8]={0},glen[16]={0};
   for(u32 pad=0;pad<16;pad++){
    EuPad p=pads[pad];if(!eu_pad_valid(p)||!eu_enabled(p))continue;vel[pad]=eu_base(p);
    if(eu_native(p)&&!mel){native|=1u<<pad;continue;}
    u32 n=eu_length(p),k=eu_pulses(p),rot=eu_rotation(p);if((((r->step%n+n-rot)%n)*k)%n<k)mask|=1u<<pad;
   }
   if(mask||native){
    u32 cursor[6],event[6];for(u32 j=0;j<6;j++)cursor[j]=W(clip,8+j*4);
    /* Native notes are authoritative for editable pads, including empty steps.
       Read once for all pads; never change the native scheduling cursor. */
    u32 seen=0;
    if(!mel&&cursor[1]<=511)for(u32 j=0;j<cursor[1];j++){
     cursor[2]=j;if(!FN(0x08095da0,int(*)(void*,void*))(cursor,event))break;u32 pad=H(event,2);
     if(mel){pad=16;for(u32 q=0;q<16;q++)if(((mask|native)&(1u<<q))&&pitch[q]==H(event,16)){pad=q;break;}}
     if(B(event,0)!=1||pad>=16||!((mask|native)&(1u<<pad)))continue;
     int tick=(int)event[1],q=tick%960;if(q>480)q-=960;
     int at=(tick-q)/960;u32 n=eu_length(pads[pad]);
     if(eu_mode(pads[pad])&&eu_depth(pads[pad])&&(native&(1u<<pad)) && at>=0 && (u32)at<n){u32 bit=1u<<((u32)at%32);if(!(bits[pad][(u32)at/32]&bit)){bits[pad][(u32)at/32]|=bit;totals[pad]++;if((u32)at<r->step%n)ranks[pad]++;}}
     if(at!=(int)(r->step%n))continue;
     if(native&(1u<<pad)){
      if(seen&(1u<<pad))continue;seen|=1u<<pad;mask|=1u<<pad;
      vel[pad]=H(event,18)?H(event,18):100;cond[pad]=B(event,1);locks[pad]=event[5];glen[pad]=event[2];
     }else if(event[5]&&!locks[pad])locks[pad]=event[5];
    }
    for(u32 pad=0;pad<16;pad++)if(mask&(1u<<pad)){
     u32 c=cond[pad];int play=1;
     if(c>=100&&c<135){u32 i=c-100,b=2;while(i>=b){i-=b;b++;}play=(r->step/eu_length(pads[pad]))%b==i;}
     else if(c>0&&c<100)play=(u32)FN(0x080a40b8,int(*)())()%100u<=c;
     if(!play)continue;
     EuPad dyn=pads[pad];if(eu_mode(dyn)&&eu_depth(dyn)){
      u32 n=eu_length(dyn);if(!eu_native(dyn)){for(u32 at=0;at<n;at++)if(((((at+n-eu_rotation(dyn))%n)*eu_pulses(dyn))%n)<eu_pulses(dyn)){totals[pad]++;if(at<r->step%n)ranks[pad]++;}}
      u32 seed=vel_hash(W(s,12)^((mel?pitch[pad]:pad)*0x9e3779b9u)^((r->step/n)*0x85ebca6bu));vel[pad]=velocity_value(vel[pad],eu_mode(dyn),eu_depth(dyn),(r->step/n)*totals[pad]+ranks[pad],totals[pad],r->step%n,seed);
     }
     locks[pad]=locks_filter(s,locks[pad],r->step/eu_length(pads[pad]));
     if(mel){FN(LIVE_LOCK_PENDING,void(*)(u32))(locks[pad]);if(locks[pad])FN(LIVE_LOCK_ROUTE,void(*)(void*,void*,u32))(s,router,0);
      mel_play(s,pitch[pad],vel[pad],(u32)frame,clock,router,glen[pad]?glen[pad]:(eu_gate(pads[pad])?eu_gate(pads[pad]):4u)*240u,period);}
     else{FN(LIVE_LOCK_PENDING,void(*)(u32))(locks[pad]);if(locks[pad])FN(LIVE_LOCK_ROUTE,void(*)(void*,void*,u32))(s,router,pad);
     FN(0x0805f8e0,void(*)(void*,u32,u32,u32,u32,void*))(s,0,vel[pad],(u32)frame,pad,router);}
     FN(LIVE_LOCK_PENDING,void(*)(u32))(0);
    }
   }
  }
  if(frame>=(int)offset)phase(r,r->step,1);
  r->next+=period;r->step++;
 }
 phase(r,0,0);r->ready=0;r->epoch=0; /* fail back to native events; never an unbounded catch-up burst */
}

extern "C" __attribute__((used,retain)) u32 eu_velocity_value(u32 base,u32 mode,u32 depth,u32 hit,u32 hits,u32 step,u32 seed){return velocity_value(base,mode,depth,hit,hits,step,seed);}
/* CH6 chord pad audition. Keyboard pads (pad mode 3 in the native pad module,
   0808_4760 press / 0808_3FE0 release) post one note record (type 2 on, 3 off;
   +0C pitch, +10 velocity) through router 0809ECA0. While the M4 chord mode is
   active the press posts every chord tone instead, and the release turns off
   exactly the tones that press started. slot 0 = track handle, 1 = layer handle. */
typedef void (*ChordPost)(void*,void*);
#define CHORD_POST ((ChordPost)(0x0809eca0u|1u))
static int chord_mail(EuBank *b,u32 pc,u8 *count,signed char *off,u32 *vel){
 ChordMail *m=&b->chord_mail;invalidate((u32)m,sizeof(*m));u32 s=m->serial;
 if(!s||(s&1)||!m->active)return 0;u32 n=m->count[pc];if(!n||n>CA_VOICES)return 0;
 for(u32 i=0;i<n;i++)off[i]=m->off[pc][i];*vel=m->velocity;__asm__ volatile("dmb" ::: "memory");
 invalidate((u32)m,32);*count=(u8)n;return s==m->serial;
}
static void chord_send(void *router,const u32 *rec,u32 pitch,u32 vel=0){u32 r[6];for(u32 i=0;i<6;i++)r[i]=rec[i];r[3]=pitch;if(vel&&(r[0]&255)==2){u32 v=r[4]*vel/127u;r[4]=v?v:1;}CHORD_POST(router,r);}
extern "C" __attribute__((used,retain)) void chord_press(void *router,u32 *rec,u32 pad,u32 slot){
 EuBank *b=bank();u32 root=rec[3];if(!b||root>127||slot>1){CHORD_POST(router,rec);return;}
 ChordOwn *o=&b->chord_own;u32 bit=1u<<(root&31),*held=&o->held[slot][root>>5];
 if(!(*held&bit)){
  if(!slot){
   u8 n;signed char off[CA_VOICES];u32 vel=0;if(!chord_mail(b,root%12,&n,off,&vel)){CHORD_POST(router,rec);return;}o->vel[root]=(u8)vel;
   u32 k=0;for(u32 i=0;i<n;i++){int p=(int)root+off[i];if(p<0||p>127)continue;u32 dup=0;for(u32 j=0;j<k;j++)dup|=o->notes[root][j]==(u8)p;if(!dup)o->notes[root][k++]=(u8)p;}
   o->count[root]=(u8)k;
   ChordPub *pub=&b->chord_pub;if(pad<16)pub->pitch[pad]=(u8)(0x80|root);pub->held++;pub->serial+=2;__asm__ volatile("dsb" ::: "memory");W((void*)0xe000ef68u,0)=(u32)pub;__asm__ volatile("dsb" ::: "memory");
  }else if(!(o->held[0][root>>5]&bit)){CHORD_POST(router,rec);return;}
  *held|=bit;for(u32 i=0;i<o->count[root];i++){u32 p=o->notes[root][i];if(!o->refs[slot][p]++)chord_send(router,rec,p,o->vel[root]);}
  return;
 }
 for(u32 i=0;i<o->count[root];i++)chord_send(router,rec,o->notes[root][i],o->vel[root]); /* retrigger without a release: no new ownership */
}
extern "C" __attribute__((used,retain)) void chord_release(void *router,u32 *rec,u32 slot){
 EuBank *b=bank();u32 root=rec[3];if(!b||root>127||slot>1){CHORD_POST(router,rec);return;}
 ChordOwn *o=&b->chord_own;u32 bit=1u<<(root&31),*held=&o->held[slot][root>>5];
 if(!(*held&bit)){CHORD_POST(router,rec);return;}
 *held&=~bit;if(!slot){ChordPub *pub=&b->chord_pub;if(pub->held)pub->held--;pub->serial+=2;__asm__ volatile("dsb" ::: "memory");W((void*)0xe000ef68u,0)=(u32)pub;__asm__ volatile("dsb" ::: "memory");}
 for(u32 i=0;i<o->count[root];i++){u32 p=o->notes[root][i];if(o->refs[slot][p]&&!--o->refs[slot][p])chord_send(router,rec,p);}
}
