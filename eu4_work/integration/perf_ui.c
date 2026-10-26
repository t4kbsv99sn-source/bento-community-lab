/* P1 performance page (M4).
 *
 * PROJ+PLAY opens a performance page on the native GenericProperties page
 * (0x1A, the Track FX host) and never starts playback; PROJ+PLAY again goes
 * back. The native settings pages (previously PROJ+PLAY) move to PROJ+Left.
 *
 * Row 1 "Tempo & Key": the project's own BPM, Swing, Root Note and Scale
 * (native keys 8C/8F/8E/8D, the same values the settings pages edit, so there
 * is nothing to keep in sync) plus Tap tempo.
 * Row 2 "Pads": Fixed velocity On/Off and Velocity, per track (the track's own
 * setting follows track selection and is saved with the track).
 *
 * Fixed velocity reaches M7 through EuControl.reserved[1] (see live_shared.h);
 * the M7 pad-press hook rewrites the press pressure.
 * Row 3 "Chord" (P3): per track On/Off, Type (incl. Diatonic / Diatonic 7,
 * which follow the project Root/Scale), Voicing, Inversion. While on, the
 * selected pitched track's keyboard pads play the chord on their own pitch
 * through the CH6 chord audition (ChordMail). Live chord mode (SEQ double-tap
 * in the piano roll) keeps priority on its own track. */
#include "live_shared.h"
#include "../../chord_work/chords.h"
/* P7 (owner report on 1.6P6):
 * - BPM/Swing/Root/Scale live on the project settings node (08133E54), not on
 *   30030164 (the selection context); reads showed 0 and writes went nowhere.
 * - Voicing "Smooth": each chord takes the inversion/octave closest to the
 *   last chord played on the pads.
 * - The played chord's name is shown in the row title ("Chord / Dm7").
 * - Chord edits here bump a per-track version, so SEQ chord mode adopts them.
 * - The header chord symbol is gone (owner: overlaps the counter). */
#define PROJECT ((void*)0x30030164u)
#define LOCK_HELD W((void*)0x24048d60u,8)
#define LOCK_USED W((void*)0x24048d60u,12)
#define CONSUMED W((void*)0x24048d70u,0)
#define TICK W((void*)0x3001fe2cu,0)
#define PERF_MAGIC 0x31465250u
#define KEY_BPM 0x8cu
#define KEY_SCALE 0x8du
#define KEY_ROOT 0x8eu
#define KEY_SWING 0x8fu
#define KEY_TAP 0x101u
#define KEY_OCTAVE 0x178u
#define KEY_FIXED 0x102u
#define KEY_VELOCITY 0x11cu
#define KEY_CHORD 0x104u
#define KEY_CTYPE 0x132u
#define KEY_VOICING 0x14au
#define KEY_INVERSION 0x144u
#define CHORD_TYPES 17u /* 15 shapes + Diatonic + Diatonic 7 */
#define CHORD_DEFAULT_TYPE 15u
#define PERF_TRACKS 16u
typedef struct {u32 handle,on,velocity,chord,type,voicing,inversion,ver;} PerfTrack;
#define SMOOTH 3u
typedef struct {
 u32 magic,active,view,nav,previous,left_down,arrow_down,published,tap_last,tap_count,taps[4];
 PerfTrack tracks[PERF_TRACKS];char titles[3][32];
 u32 chord_sig,chord_serial,chord_pub;const char *type_names[CHORD_TYPES];
 u32 in_get,pad,pad_serial,pad_since,ref_n;int ref[CH_MAX_VOICES];u8 count[12];signed char off[12][CH_MAX_VOICES];char name[12];u32 name_track;
 u32 trk_held,trk_used,trk_page;u8 trk_saved[256]; /* P20: pad colours while TRACKS is held */
} Perf;
void **perf_state_slot(void);
static const char tap_name[]="Tap Tempo",fixed_name[]="Fixed Vel",velocity_name[]="Velocity",chord_name[]="Chord",ctype_name[]="Type",voicing_name[]="Voicing",inversion_name[]="Inversion";
static const char *const voicing_names[4]={"Close","Open","Drop 2","Smooth"};
int chord_audition_publish(int active,const u8 *count,const signed char *off,u32 velocity);
u32 chord_mail_serial(void);int chord_diatonic(int root,int seventh);unsigned chord_live_owner(void);int chord_pad_pitch(unsigned pad);u32 chord_pub_serial(void);
/* The project settings node that owns BPM 8C, Scale 8D, Root 8E, Swing 8F. */
static u32 settings(void){u32 h=0;return FN(0x08133e54,int(*)(void*,u32*))(MODEL,&h)?h:0;}
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static Perf *perf(int create){
 void **slot=perf_state_slot();if(!slot)return 0;Perf *s=*slot;
 if(s)return s->magic==PERF_MAGIC?s:0;if(!create)return 0;
 u32 cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(Perf)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 s=FN(0x08104c08,void*(*)(u32))(bytes);if((u32)s!=cursor)return 0;zero(s,sizeof(*s));s->magic=PERF_MAGIC;*slot=s;return s;
}
static void descriptor(u32 key,const char *name,u32 type,int lo,int hi){
 u32 r=W((void*)0x30031484u,0);void *d=(void*)(r+key*32);
 zero(d,32);H(d,0)=(u16)key;B(d,2)=(u8)type;W(d,4)=(u32)name;W(d,16)=(u32)lo;W(d,20)=(u32)hi;
}
/* Never take a descriptor someone else owns. */
static int registry(void){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;
 static const u16 keys[7]={KEY_TAP,KEY_FIXED,KEY_VELOCITY,KEY_CHORD,KEY_CTYPE,KEY_VOICING,KEY_INVERSION};const char *names[7]={tap_name,fixed_name,velocity_name,chord_name,ctype_name,voicing_name,inversion_name};
 for(u32 i=0;i<7;i++){void *d=(void*)(r+keys[i]*32);if(H(d,0)&&W(d,4)!=(u32)names[i])return 0;}
 for(u32 i=0;i<4;i++)if(H((void*)(r+(KEY_BPM+i)*32),0)!=KEY_BPM+i)return 0; /* native project keys must exist */
 Perf *s=perf(1);if(!s)return 0;
 for(u32 i=0;i<CHORD_TYPES;i++)s->type_names[i]=i<CH_TYPES?chord_type_name(i):i==CH_TYPES?"Diatonic":"Diatonic 7";
 descriptor(KEY_TAP,tap_name,6,0,1);descriptor(KEY_FIXED,fixed_name,6,0,1);descriptor(KEY_VELOCITY,velocity_name,2,1,127);
 descriptor(KEY_CHORD,chord_name,6,0,1);descriptor(KEY_CTYPE,ctype_name,7,0,CHORD_TYPES-1);descriptor(KEY_VOICING,voicing_name,7,0,3);descriptor(KEY_INVERSION,inversion_name,2,0,3);
 void *d=(void*)(r+KEY_CTYPE*32);W(d,8)=(u32)s->type_names;W(d,12)=CHORD_TYPES;d=(void*)(r+KEY_VOICING*32);W(d,8)=(u32)voicing_names;W(d,12)=4;return 1;
}
static u32 current_track(void){u32 t=0;return FN(0x08133cfc,int(*)(void*,void*))(MODEL,&t)?t:0;}
static u32 track_index(void){u32 i=0;FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,PROJECT,0x131,&i);return i;}
static PerfTrack *entry(Perf *s,u32 handle,int create){
 if(!s||!handle)return 0;PerfTrack *free=0;
 for(u32 i=0;i<PERF_TRACKS;i++){if(s->tracks[i].handle==handle)return &s->tracks[i];if(!s->tracks[i].handle&&!free)free=&s->tracks[i];}
 if(!create)return 0;if(!free){for(u32 i=1;i<PERF_TRACKS;i++)s->tracks[i-1]=s->tracks[i];free=&s->tracks[PERF_TRACKS-1];}
 free->handle=handle;free->on=0;free->velocity=100;free->chord=0;free->type=CHORD_DEFAULT_TYPE;free->voicing=0;free->inversion=0;free->ver=0;return free;
}
static int pitched(u32 track){u32 t=track?FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&track):0;return t==15||t==18||t==19||t==22;}
/* Chord shape for every pitch class (as CH6 live chord mode publishes it). */
static int distance(const int *a,u32 an,const int *b,u32 bn){
 int d=0;
 for(u32 i=0;i<an;i++){int m=1000;for(u32 j=0;j<bn;j++){int x=a[i]-b[j];if(x<0)x=-x;if(x<m)m=x;}d+=m;}
 for(u32 j=0;j<bn;j++){int m=1000;for(u32 i=0;i<an;i++){int x=a[i]-b[j];if(x<0)x=-x;if(x<m)m=x;}d+=m;}
 return d;
}
/* Smooth: from the close root-position chord (offsets t, n tones) pick the
   inversion and octave nearest to the last chord played. The pad is assumed
   in the octave nearest that chord (offsets are relative to the pad). */
static void smooth(Perf *s,u32 pc,int *t,int n){
 if(!s->ref_n||n<1)return;int sum=0;for(u32 i=0;i<s->ref_n;i++)sum+=s->ref[i];int centre=sum/(int)s->ref_n;
 int r=(int)pc+12*((centre-(int)pc+6+120)/12-10),best[CH_MAX_VOICES],bd=1<<30;
 for(int inv=0;inv<n;inv++)for(int shift=-12;shift<=12;shift+=12){
  int c[CH_MAX_VOICES];for(int i=0;i<n;i++)c[i]=t[i]+(i<inv?12:0)+shift;
  int a[CH_MAX_VOICES];for(int i=0;i<n;i++)a[i]=r+c[i];int d=distance(a,(u32)n,s->ref,s->ref_n);
  if(d<bd){bd=d;for(int i=0;i<n;i++)best[i]=c[i];}
 }
 for(int i=0;i<n;i++)t[i]=best[i];
 for(int i=1;i<n;i++)for(int j=i;j>0&&t[j]<t[j-1];j--){int x=t[j];t[j]=t[j-1];t[j-1]=x;}
}
static void chord_publish(Perf *s,PerfTrack *e){
 u8 *count=s->count;signed char (*off)[CH_MAX_VOICES]=s->off;
 for(u32 pc=0;pc<12;pc++){
  Chord c;zero(&c,sizeof(c));c.root=(int16_t)(48+pc);c.voicing=(int16_t)(e->voicing==SMOOTH?CH_CLOSE:e->voicing);c.inversion=(int16_t)(e->voicing==SMOOTH?0:e->inversion);
  c.type=(int16_t)(e->type<CH_TYPES?e->type:chord_diatonic(c.root,e->type==CH_TYPES+1));
  c.velocity=100;c.end=1; /* chord_notes checks a playable chord */
  int p[CH_MAX_VOICES];int n=chord_notes(&c,p);
  /* Triads have no third inversion or Drop 2: use the nearest that exists. */
  while(n<0&&c.inversion>0){c.inversion--;n=chord_notes(&c,p);}
  if(n<0&&c.voicing==CH_DROP2){c.voicing=CH_OPEN;c.inversion=(int16_t)e->inversion;n=chord_notes(&c,p);while(n<0&&c.inversion>0){c.inversion--;n=chord_notes(&c,p);}}
  if(n<=0){n=1;p[0]=c.root;}
  int t[CH_MAX_VOICES];for(int i=0;i<n;i++)t[i]=p[i]-c.root;
  if(e->voicing==SMOOTH)smooth(s,pc,t,n);
  count[pc]=(u8)n;for(int i=0;i<CH_MAX_VOICES;i++)off[pc][i]=(signed char)(i<n?t[i]:0);
 }
 chord_audition_publish(1,count,&off[0][0],127);
}
static void chord_tick(Perf *s,u32 track,PerfTrack *e){
 u32 live=chord_live_owner();int want=e&&e->chord&&pitched(track)&&live!=track;
 if(!want){
  /* Turn our chord off, unless live chord mode now owns the pads. */
  if(s->chord_pub&&live!=track)chord_audition_publish(0,0,0,0);
  s->chord_pub=0;return;
 }
 u32 root=0,scale=0,h=e->type>=CH_TYPES?settings():0;
 if(h){FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&h,KEY_ROOT,&root);FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&h,KEY_SCALE,&scale);}
 u32 sig=track*31u^e->type<<1^e->voicing<<6^e->inversion<<9^root<<12^scale<<18;
 if(e->voicing==SMOOTH)for(u32 i=0;i<s->ref_n;i++)sig=sig*31u+(u32)s->ref[i];
 if(s->chord_pub&&s->chord_sig==sig&&chord_mail_serial()==s->chord_serial)return;
 chord_publish(s,e);s->chord_pub=1;s->chord_sig=sig;s->chord_serial=chord_mail_serial();
}
static void refresh(Perf *s);
static const char *const note_names[12]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
static const char *const suffixes[CH_TYPES]={"","m","dim","aug","sus2","sus4","maj7","m7","7","add9","m7b5","mMaj7","4ths","dim7","+maj7"};
static void put(char **d,const char *t){while(*t)*(*d)++=*t++;}
/* "Dm7", "C/E": root, quality, and the bass when it is not the root. */
static void played_name(Perf *s,PerfTrack *e,int pitch){
 u32 pc=(u32)pitch%12u;int type=e->type<CH_TYPES?(int)e->type:chord_diatonic(48+(int)pc,e->type==CH_TYPES+1);
 char *d=s->name;put(&d,note_names[pc]);if(type>=0&&type<CH_TYPES)put(&d,suffixes[type]);
 int low=127;for(u32 i=0;i<s->count[pc];i++)if(s->off[pc][i]<low)low=s->off[pc][i];
 u32 bass=(u32)((int)pc+low+120)%12u;if(s->count[pc]&&bass!=pc){*d++='/';put(&d,note_names[bass]);}*d=0;
}
/* P7: a pad press (fx_dispatch code AC) is matched with the pitch the audio
   core published for it (ChordPub, after the chord started). */
void perf_pad(u32 code,u32 index){
 Perf *s=perf(0);if(!s||code!=0xac||index>=16)return;s->pad=index|0x100u;s->pad_serial=chord_pub_serial();s->pad_since=TICK;
}
static void played(Perf *s,u32 track,PerfTrack *e){
 if(!(s->pad&0x100u))return;
 if(TICK-s->pad_since>300u){s->pad=0;return;}
 if(chord_pub_serial()==s->pad_serial)return;
 int pitch=chord_pad_pitch(s->pad&15u);s->pad=0;if(pitch<0||!e||!s->chord_pub)return;
 u32 pc=(u32)pitch%12u;s->ref_n=s->count[pc];for(u32 i=0;i<s->ref_n;i++)s->ref[i]=pitch+s->off[pc][i];
 played_name(s,e,pitch);s->name_track=track;
 if(s->active)refresh(s); /* the header shows it (perf_header) */
}
/* Called for every UI message: the selected track's fixed velocity and chord. */
/* P20 (owner: holding TRACKS and picking a pad needs looking at the screen).
 * While TRACKS (button 2) is held, each track's two pads (n and n+8, as in the
 * native scene builder 081355D8) show that track's colours (08140F50 / 08140EF0
 * / 08140FB4); pads without a track are off (08140FBC(0)). The native pad
 * colours are saved on press and given back on release. Written only when they
 * differ, so the native page cannot make them flicker by itself. */
#define PADS ((u8*)MODEL+0x19c4)
static void track_pads(Perf *s){
 u32 want[16][3],off=FN(0x08140fbc,u32(*)(u32))(0);
 for(u32 i=0;i<16;i++){want[i][0]=want[i][1]=want[i][2]=off;}
 void *root=(void*)W(MODEL,0);
 for(u32 i=0;root&&i<16;i++){
  void *obj=0;if(!FN(0x0812d78a,int(*)(void*,u32,void*))(root,i,&obj)||!obj)break;
  u32 n=FN(0x0812dc74,u32(*)(void*,u32))(obj,0x73);if(n>7)continue;
  u32 a=FN(0x08140f50,u32(*)(u32))(n),b=FN(0x08140ef0,u32(*)(u32))(n),c=FN(0x08140fb4,u32(*)(u32))(n);
  for(u32 r=0;r<2;r++){want[n+r*8][0]=a;want[n+r*8][1]=b;want[n+r*8][2]=c;}
 }
 int changed=0;
 for(u32 i=0;i<16;i++){u8 *e=PADS+i*16;
  if(W(e,0)!=want[i][0]||W(e,4)!=want[i][1]||W(e,8)!=want[i][2]||B(e,12)||B(e,13)){W(e,0)=want[i][0];W(e,4)=want[i][1];W(e,8)=want[i][2];B(e,12)=0;B(e,13)=0;changed=1;}}
 if(changed)FN(0x081257f0,void(*)(void*))(PADS);
 (void)s;
}
/* P21 (owner on P20: after switching to INST or SEQ through the hold, the pads
 * went back to the old colours). Once a track is picked during the hold (a pad
 * press or record, or the page changes), painting stops and the new page keeps
 * its own pad colours; only a hold without a switch gives the old ones back. */
static void tracks_button(void *m,u32 code,u32 index){
 Perf *s=perf(0);
 if(s&&s->trk_held&&(code==0xac||code==0xfe||B(m,0x12c)!=s->trk_page))s->trk_used=1;
 if(index!=2||(code!=0xaf&&code!=0xb0))return;
 s=perf(code==0xaf);if(!s)return;
 if(code==0xaf&&!s->trk_held){for(u32 i=0;i<256;i++)s->trk_saved[i]=PADS[i];s->trk_held=1;s->trk_used=0;s->trk_page=2;track_pads(s);return;} /* P22 (owner): TRACKS opens the Tracks page (2); that jump is not a switch */
 if(code==0xb0&&s->trk_held){s->trk_held=0;if(!s->trk_used){for(u32 i=0;i<256;i++)PADS[i]=s->trk_saved[i];FN(0x081257f0,void(*)(void*))(PADS);}}
}
void perf_tick(void){
 Perf *s=perf(0);if(!s)return;if(s->trk_held&&!s->trk_used&&B(MODEL,0x12c)==s->trk_page)track_pads(s);u32 track=current_track();PerfTrack *e=entry(s,track,0);
 u32 v=e&&e->on&&e->velocity>=1&&e->velocity<=127?PERF_FIXED_TAG|e->velocity:0;
 if(EC->reserved[1]!=v||s->published!=v){EC->reserved[1]=v;s->published=v;__asm__ volatile("dsb" ::: "memory");}
 played(s,track,e);
 chord_tick(s,track,e);
}
static void project_set(u32 key,int value){
 u32 h=settings();if(!h)return;u32 ev[5]={0xcf,h,key,(u32)value,0};FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);FN(0x0813130c,void(*)(void*))(MODEL);
}
static void refresh(Perf *s){if(s->view)FN(0x08145cf4,void(*)(void*))((void*)s->view);}
static void nav(Perf *s,void *m,u32 page){s->nav=1;FN(0x081420ec,void(*)(void*,u32,u32,u32,u32))(m,page,0,0,0);s->nav=0;}
static void toggle(void *m){
 Perf *s=perf(1);if(!s)return;
 if(s->active&&B(m,0x12c)==0x1a){s->active=0;s->view=0;nav(s,m,s->previous?s->previous:0x1a);return;}
 if(!registry())return;s->previous=B(m,0x12c);s->active=1;s->view=0;s->tap_count=0;nav(s,m,0x1a);
}
/* Before every other custom button handling (fx_dispatch). */
int perf_dispatch(void *m,u32 code,u32 index){
 tracks_button(m,code,index); /* P20; the press goes on to K16 */
 /* P26 (owner: "we lost SD card mode along the way"). Native disk mode is model
    action 101D (save, then BKP0R=4 + reset into the disk-mode program; 101E skips
    the save). Its menu entry disappeared with the rebuilt burger menus, so PROJ+Up
    (button 1) posts it. */
 if(LOCK_HELD&&index==1&&(code==0xaf||code==0xb0)){if(code==0xaf){LOCK_USED=1;u32 ev[5]={0x101d,0,0,0,0};FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);}return 1;}
 Perf *s=perf(0);
 if(s&&(index==1||index==8)&&(code==0xaf||code==0xb0)){
  u32 bit=1u<<index;
  if(code==0xb0&&(s->arrow_down&bit)){s->arrow_down&=~bit;return 1;}
  if(code==0xaf&&s->active&&pitched(current_track())){
   s->arrow_down|=bit;u32 track=current_track();int offset=0;
   FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&track,KEY_OCTAVE,&offset);
   offset+=index==1?1:-1;if(offset<-5)offset=-5;if(offset>5)offset=5;
   u32 ev[5]={0xcf,track,KEY_OCTAVE,(u32)offset,0};FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);
   FN(0x08139138,void(*)(void*))(MODEL);FN(0x0813130c,void(*)(void*))(MODEL);refresh(s);return 1;
  }
 }
 if(code==0xb0&&index==0&&s&&s->left_down){s->left_down=0;return 1;}
 if((code!=0xaf&&code!=0xb0)||!LOCK_HELD)return 0;
 if(index==15){
  /* The release goes on to K16, which consumes it through the mask (and
     clears the bit); nothing reaches transport. */
  if(code==0xaf){CONSUMED|=1u<<15;LOCK_USED=1;toggle(m);return 1;}return 0;
 }
 if(index==0){
  if(code==0xaf){LOCK_USED=1;s=perf(1);if(s)s->left_down=1;extern void seq_nav_undo(void*);seq_nav_undo(m);}
  return 1;
 }
 return 0;
}
void perf_nav(u32 page){(void)page;Perf *s=perf(0);if(s&&!s->nav){s->active=0;s->view=0;}}
static void copy(char *d,const char *a,const char *b){while(*a)*d++=*a++;while(b&&*b)*d++=*b++;*d=0;}
int perf_header(void *out,u32 caller){
 Perf *s=perf(0);if(!s||!s->active||(caller&~1u)!=0x08145f22u||!registry())return 0;
 s->view=(u32)out-0x93c4;zero(out,0x54);B(out,0)=3;
 char n[3]={'1',0,0};u32 t=track_index();n[0]=(char)('1'+(t<8?t:0));
 copy(s->titles[0],"Performance / Tempo & Key",0);copy(s->titles[1],"Pads / Track ",n);copy(s->titles[2],"Chord / Track ",n);
 if(s->name[0]&&s->name_track==current_track())copy(s->titles[2],"Chord / ",s->name); /* P7: the chord just played */
 W(out,4)=(u32)s->titles[0];W(out,8)=(u32)s->titles[1];W(out,12)=(u32)s->titles[2];
 static const u16 row1[8]={KEY_BPM,KEY_TAP,KEY_SWING,KEY_ROOT,KEY_SCALE,0,0,0},row2[8]={KEY_FIXED,KEY_VELOCITY,KEY_OCTAVE,0,0,0,0,0},row3[8]={KEY_CHORD,KEY_CTYPE,KEY_VOICING,KEY_INVERSION,0,0,0,0};
 for(u32 i=0;i<8;i++){H(out,0x14+i*2)=row1[i];H(out,0x24+i*2)=row2[i];H(out,0x34+i*2)=row3[i];}
 return 1;
}
int perf_get(void *m,void *handle,u32 key,void *out){
 Perf *s=perf(0);if(!s||!s->active||!out)return 0;
 if(key==KEY_OCTAVE){if(s->in_get)return 0;u32 h=current_track();s->in_get=1;int ok=FN(0x08133614,int(*)(void*,void*,u32,void*))(m,&h,key,out);s->in_get=0;if(!ok)W(out,0)=0;return 1;}
 if(key>=KEY_BPM&&key<=KEY_SWING){
  if(s->in_get)return 0; /* our own read of the settings node (below) */
  u32 h=settings();if(!h)return 0;
  s->in_get=1;int ok=FN(0x08133614,int(*)(void*,void*,u32,void*))(m,&h,key,out);s->in_get=0;
  if(!ok)W(out,0)=0;return 1;
 }
 /* Only our own keys below: current_track() itself reads the project's
    property 131 through this very getter, so looking it up for every key
    recursed until the stack overflowed (1.6P5 reset on PROJ+PLAY). */
 if(!key){W(out,0)=0;return 1;} /* empty encoder slots */
 if(key!=KEY_TAP&&key!=KEY_FIXED&&key!=KEY_VELOCITY&&key!=KEY_CHORD&&key!=KEY_CTYPE&&key!=KEY_VOICING&&key!=KEY_INVERSION)return 0;
 PerfTrack *e=entry(s,current_track(),0);
 if(key==KEY_TAP){W(out,0)=s->tap_count&1u;return 1;} /* flips with every tap */
 if(key==KEY_FIXED){W(out,0)=e&&e->on;return 1;}
 if(key==KEY_VELOCITY){W(out,0)=e?e->velocity:100;return 1;}
 if(key==KEY_CHORD){W(out,0)=e&&e->chord;return 1;}
 if(key==KEY_CTYPE){W(out,0)=e?e->type:CHORD_DEFAULT_TYPE;return 1;}
 if(key==KEY_VOICING){W(out,0)=e?e->voicing:0;return 1;}
 if(key==KEY_INVERSION){W(out,0)=e?e->inversion:0;return 1;}
 return 0;
}
/* Tap tempo: a tap is any change of the Tap field (touch or a knob nudge).
   Taps 0.2..2 s apart; the average of the last four intervals sets BPM. */
static void tap(Perf *s){
 u32 now=TICK,dt=now-s->tap_last;
 if(!s->tap_count||dt<200||dt>2000){s->tap_count=1;s->tap_last=now;return;}
 for(u32 i=3;i>0;i--)s->taps[i]=s->taps[i-1];s->taps[0]=dt;s->tap_last=now;if(s->tap_count<5)s->tap_count++;
 u32 n=s->tap_count-1,sum=0;for(u32 i=0;i<n;i++)sum+=s->taps[i];
 int bpm=(int)((60000u*n+sum/2)/sum);if(bpm<40)bpm=40;if(bpm>250)bpm=250;project_set(KEY_BPM,bpm);
}
int perf_page_active(void){Perf *s=perf(0);return s&&s->active;}
int perf_event(void *v,void *event){
 Perf *s=perf(0);if(!s||!s->active)return 0;
 {extern int seq_nav_global(void*,void*);u32 c=H(event,0);if(c>=0x1062u&&c<=0x1064u)return seq_nav_global(MODEL,event);} /* P17 burger */
 if(s->view!=(u32)v||H(event,0)!=0xcf)return 0;
 u32 key=W(event,8);int value=(int)W(event,12);
 if(key==KEY_OCTAVE){u32 t=current_track();if(value<-5)value=-5;if(value>5)value=5;u32 ev[5]={0xcf,t,key,(u32)value,0};FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);FN(0x08139138,void(*)(void*))(MODEL);FN(0x0813130c,void(*)(void*))(MODEL);}
 else if(key>=KEY_BPM&&key<=KEY_SWING)project_set(key,value);
 else if(key==KEY_TAP)tap(s);
 else if(key==KEY_FIXED||key==KEY_VELOCITY||key==KEY_CHORD||key==KEY_CTYPE||key==KEY_VOICING||key==KEY_INVERSION){
  PerfTrack *e=entry(s,current_track(),1);if(!e)return 1;
  if(value<0)value=0;
  if(key==KEY_FIXED)e->on=value?1:0;else if(key==KEY_VELOCITY)e->velocity=(u32)(value<1?1:value>127?127:value);
  else if(key==KEY_CHORD)e->chord=value?1:0;else if(key==KEY_CTYPE)e->type=(u32)value<CHORD_TYPES?(u32)value:CHORD_TYPES-1;
  else if(key==KEY_VOICING)e->voicing=value>3?3:(u32)value;else e->inversion=value>3?3:(u32)value;
  if(key>=KEY_CHORD&&key!=KEY_FIXED&&key!=KEY_VELOCITY){e->ver++;if(!e->ver)e->ver=1;} /* SEQ chord mode adopts it */
  perf_tick();FN(0x0813130c,void(*)(void*))(MODEL);
 }else return 0;
 refresh(s);return 1;
}
/* Saved with the track object (fx_save/fx_load). */
static void attr(void *params,const char *name,u32 value){void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,name);if(a)FN(0x0810958e,void(*)(void*,u32))(a,value);}
void perf_save(void *object,void *params){
 Perf *s=perf(0);if(!s||!object||!params)return;PerfTrack *e=entry(s,W(object,0x10),0);
 if(e&&(e->on||e->velocity!=100))attr(params,"bento_perf_velocity",e->on<<8|e->velocity);
 if(e&&(e->chord||e->type!=CHORD_DEFAULT_TYPE||e->voicing||e->inversion))attr(params,"bento_perf_chord",1u<<24|e->inversion<<16|e->voicing<<12|e->type<<4|e->chord);
}
static int read(void *params,const char *name,u32 *value){void *a=params?FN(0x08109c64,void*(*)(void*,const char*))(params,name):0;return a&&!FN(0x08109566,int(*)(void*,void*))(a,value);}
void perf_load(void *node,void *object){
 if(!node||!object||!W(object,0x10))return;Perf *s=perf(0);
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");
 u32 vel=0,chord=0;int has_vel=read(params,"bento_perf_velocity",&vel),has_chord=read(params,"bento_perf_chord",&chord);
 if(!has_vel&&!has_chord){PerfTrack *e=entry(s,W(object,0x10),0);if(e){u32 h=e->handle;zero(e,sizeof(*e));e->handle=h;e->velocity=100;e->type=CHORD_DEFAULT_TYPE;}return;}
 if(!s)s=perf(1);PerfTrack *e=entry(s,W(object,0x10),1);if(!e)return;
 u32 v=vel&255;e->on=has_vel?(vel>>8)&1:0;e->velocity=has_vel&&v>=1&&v<=127?v:100;
 if(has_chord&&(chord>>24)==1){e->ver=1;e->chord=chord&1;u32 t=(chord>>4)&255;e->type=t<CHORD_TYPES?t:CHORD_DEFAULT_TYPE;e->voicing=(chord>>12)&15;if(e->voicing>3)e->voicing=0;e->inversion=(chord>>16)&15;if(e->inversion>3)e->inversion=0;}
 else{e->chord=0;e->type=CHORD_DEFAULT_TYPE;e->voicing=0;e->inversion=0;}
}

/* P5: one chord per track. The performance page keeps it; SEQ chord mode
   (device.c) writes Type/Voicing/Inversion here when you edit them and starts
   an empty clip from it. */
/* Returns the chord's version (0: none). SEQ chord mode applies the chord when
   the version differs from the one it last saw. Smooth reads as Close there. */
int perf_chord_shared(u32 handle,u32 *type,u32 *voicing,u32 *inversion){
 PerfTrack *e=entry(perf(0),handle,0);if(!e||!e->ver)return 0;*type=e->type;*voicing=e->voicing==SMOOTH?0:e->voicing;*inversion=e->inversion;return (int)e->ver;
}
/* From SEQ chord mode. Keeps Smooth if SEQ only changed the type. */
void perf_chord_share(u32 handle,u32 type,u32 voicing,u32 inversion){
 PerfTrack *e=entry(perf(1),handle,1);if(!e||type>=CHORD_TYPES||voicing>2||inversion>3)return;
 if(!(e->voicing==SMOOTH&&voicing==0))e->voicing=voicing;
 e->type=type;e->inversion=inversion;if(!e->ver)e->ver=1;FN(0x0813130c,void(*)(void*))(MODEL);
}
