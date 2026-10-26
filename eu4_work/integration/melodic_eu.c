/* CH3: Euclidean rows on pitched tracks, edited from the native piano roll.
 *
 * Each of 16 rows owns one MIDI pitch. A row's pattern is ordinary native
 * notes at that pitch (EU6 model), so the piano roll shows and edits them and
 * projects save them. M7 plays enabled rows on their own cycle length and
 * sends note-offs through the native active-note table (live_audio.cpp).
 *
 * Entry: the "Euclid" header action (1054) on the pitched piano roll toggles
 * the 8 piano encoders (page 17) to Row/Note/Length/Hits/Rotate/Gate/Vel Mode/Vel Depth.
 * Piano encoder bindings: keys view+11BCC0 (u16), values +11BCD0, handle
 * +11BCA0; encoder bar view+55F0 (slots +38+i*468). See docs/DISPLAY.md and
 * docs/releases/ch3/DESIGN.md.
 */
#include "fx_shared.h"
#include "euclidean.h"
#include "live_ui.h"
#include "header_actions.h"
#include "../../chord_work/device.h"
void bars_header(void*);
int bars_event(void*,void*);
#define PE_MAGIC 0x4c454d50u
#define PE_ACTION 0x1054u
#define PIANO_PAGE 0x17u /* native SEQ handler 08142D58 */
#define BAR 0x55f0u
#define KEYS 0x11bcc0u
#define VALUES 0x11bcd0u
#define HANDLES 0x11bca0u
typedef struct {u32 magic,view,mode,row,assigned,select,select_drag;Euclid e;char note[8],gate[8];u32 held,snap_n,snap[128];} PianoEu;
void **piano_eu_slot(void);
u32 *eu_shared_scratch(void);
const char *eu_drum_title(u32);
const char *const *eu_vel_names(void);
static const u16 pe_keys[8]={0x190,0x18d,0x191,0x192,0x193,0x18f,0x194,0x195};
static const char *const pe_titles[8]={"Row","Note","Length","Hits","Rotate","Gate","Vel Mode","Vel Depth"};
static const char note_title[]="Note",gate_title[]="Gate";
static const char *const pitch_names[12]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};

static PianoEu *state(int create){
 void **slot=piano_eu_slot();if(!slot)return 0;PianoEu *s=(PianoEu*)*slot;
 if(s)return s->magic==PE_MAGIC?s:0;if(!create)return 0;
 u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),n=(sizeof(PianoEu)+31u)&~31u;
 if(p<0xc0000000u||end>0xc8000000u||p>end||end-p<n+32u)return 0;
 u32 a=FN(0x08104c08,u32(*)(u32))(n);if(a!=p)return 0;
 for(u32 i=0;i<n;i++)((u8*)a)[i]=0;s=(PianoEu*)a;s->magic=PE_MAGIC;*slot=s;return s;
}
static u32 owner_type(u32 owner){return FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&owner);}
static u32 current_owner(void){u32 o=0;return FN(0x08133cfc,int(*)(void*,void*))(MODEL,&o)?o:0;}
static int piano_ok(PianoEu *s){
 void *v=(void*)s->view;if(!v||B(MODEL,0x12c)!=PIANO_PAGE||B(v,0x125dae))return 0;
 u32 seq=W(v,0x11cd00),owner=W(v,0x11cd08),len=W(v,0x11cd18);
 return seq&&owner&&len&&len<=256&&owner==current_owner()&&eu_pitched_type(owner_type(owner));
}
static void note_name(char *d,u32 pitch){const char *n=pitch_names[pitch%12];while(*n)*d++=*n++;int o=(int)pitch/12-1; /* Bento naming: C3 = MIDI 48 (owner) */if(o<0){*d++='-';o=-o;}*d++=(char)('0'+o);*d=0;}
static void gate_name(char *d,u32 q){u32 w=q/4,f=q%4;if(w>=10)*d++=(char)('0'+w/10);*d++=(char)('0'+w%10);if(f){*d++='.';*d++=f==2?'5':f==1?'2':'7';*d++=f==2?0:'5';}*d=0;}
/* Rebuild the Euclid view of the current row from the record. */
static void capture(PianoEu *s){
 void *v=(void*)s->view;Euclid *e=&s->e;u32 seq=W(v,0x11cd00),owner=W(v,0x11cd08),len=W(v,0x11cd18);
 if(!e->valid||e->seq!=seq||e->owner!=owner){for(u32 i=0;i<sizeof(*e)/4;i++)((u32*)e)[i]=0;s->row=0;}
 e->seq=seq;e->owner=owner;e->steps=len;e->pad=s->row;e->valid=1;e->velocity=100;e->scratch=*eu_shared_scratch();
 u32 pitch=0;s->assigned=live_row_pitch(e,s->row,&pitch);
 EuPad p=live_value(e);u32 gate=eu_gate(p)?eu_gate(p):4;
 e->preview=EU_MEL|(gate<<8)|(s->assigned?pitch:48u); /* owner: default C3 (Bento naming) = MIDI 48 */
 u32 grid=W(v,0x11cd14);if(!W(v,0x11cd10)&&grid<15)e->preview|=(grid+1u)<<20; /* P17: absolute-tick clip, see eu_unit */
 {extern int live_mel_unit(Euclid*);if(s->assigned)live_mel_unit(e);}
}
static void done(PianoEu *s){*eu_shared_scratch()=s->e.scratch;}
static int registry(PianoEu *s){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;
 for(u32 i=0;i<8;i++){void *d=(void*)(r+pe_keys[i]*32);u32 t=W(d,4);
  if(!H(d,0))continue;if(i==1?t==(u32)note_title:i==5?t==(u32)gate_title:t==(u32)eu_drum_title(i==0?0:i<5?i-1:i-2))continue;return 0;}
 EuPad p=live_value(&s->e);u32 len=eu_length(p);
 int lo[8]={1,0,1,0,0,1,0,0},hi[8]={4,128,256,(int)len,(int)len-1,64,9,100};
 for(u32 i=0;i<8;i++){void *d=(void*)(r+pe_keys[i]*32);for(u32 j=0;j<32;j++)B(d,j)=0;H(d,0)=pe_keys[i];B(d,2)=i==6?7:2;
  if(i==6){W(d,8)=(u32)eu_vel_names();W(d,12)=10;}
  W(d,4)=i==1?(u32)note_title:i==5?(u32)gate_title:(u32)eu_drum_title(i==0?0:i<5?i-1:i-2);W(d,16)=(u32)lo[i];W(d,20)=(u32)hi[i];}
 return 1;
}
static const char *status_text(u32 st){return st==EU_FULL?"Clip note limit":st==EU_MEMORY?"No edit memory":st==EU_USED?"Note in use":st==EU_STALE?"Sequence changed":0;}
/* After the native piano header: replace the eight encoder bindings. */
void piano_eu_header(void *v){
 PianoEu *s=state(0);if(!s||!s->mode||s->view!=(u32)v||!piano_ok(s))return;
 capture(s);if(!registry(s))return;
 EuPad p=live_value(&s->e);u32 gate=(s->e.preview>>8)&127u,pitch=eu_mel_pitch(&s->e),on=!s->assigned||eu_enabled(p)||!eu_pulses(p); /* unassigned rows show C3; P22 (owner): a row without hits shows its note, Off only when switched off */
 note_name(s->note,pitch);gate_name(s->gate,gate);
 u32 values[8]={s->row+1,on?pitch+1:0,eu_length(p),eu_pulses(p),eu_rotation(p),gate,eu_mode(p),eu_depth(p)};
 void *bar=(u8*)v+BAR;
 for(u32 i=0;i<8;i++){
  H(v,KEYS+i*2)=pe_keys[i];W(v,VALUES+i*4)=values[i];W(v,HANDLES+i*4)=W(v,0x11cd00);
  void *slot=(u8*)bar+0x38+i*0x468;FN(0x08170656,void(*)(void*,u32,const char*))(bar,i,0);
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,pe_keys[i],(int)values[i],1);
  FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,pe_titles[i]);
 }
 FN(0x08170656,void(*)(void*,u32,const char*))(bar,1,on?s->note:"Off");
 FN(0x08170656,void(*)(void*,u32,const char*))(bar,5,s->gate);
 const char *st=status_text(s->e.status);if(st)FN(0x08170656,void(*)(void*,u32,const char*))(bar,0,st);
}
static void rebuild(void *v){FN(0x081599bc,void(*)(void*))(v);}
/* P9 (owner): rows are real clip notes from the start, as on one-shots (EU6
   model, CH3): each row writes native notes at its pitch, the piano roll can
   select and edit them, and Length/Hits/Rotate regenerate the row. A new row
   starts on C3 (MIDI 48, Bento naming) until a Note is chosen. */
static int ensure(PianoEu *s){if(!s->assigned){live_assign_pitch(&s->e,eu_mel_pitch(&s->e));s->assigned=1;}return 1;}
static void edit(PianoEu *s,u32 i,int value){
 Euclid *e=&s->e;EuPad p=live_value(e);e->status=EU_OK;
 if(i==0){s->row=value<1?0:value>4?3:(u32)value-1;e->pad=s->row;return;}
 if(i==1){
  if(value<=0){if(s->assigned&&eu_enabled(p))live_generate(e,5,0);return;}
  u32 pitch=(u32)(value>128?128:value)-1;
  if(live_pitch_owner(e,pitch,s->row)>=0){e->status=EU_USED;return;}
  u32 old=eu_mel_pitch(e);int had=s->assigned&&eu_native(p);
  if(had&&old!=pitch){int st=eu_repitch(e,MODEL,pitch);if(st!=EU_OK&&st!=EU_SAME){e->status=(u32)st;return;}}
  live_assign_pitch(e,pitch);e->preview=(e->preview&~127u)|pitch;s->assigned=1;
  if(!eu_enabled(p)&&eu_pulses(p))live_generate(e,2,(int)eu_pulses(p));
  return;
 }
 if(i>=2&&i<=4){ensure(s);live_generate(e,i-1,value);return;}
 if(i==5){ensure(s);u32 g=value<1?1:value>64?64:(u32)value;live_set_gate(e,g);e->preview=(e->preview&~(127u<<8))|(g<<8);if(eu_native(p))eu_gate_notes(e,MODEL);return;}
 if(i==6||i==7){ensure(s);live_dynamic(e,i==6?4:6,value);}
}
int piano_eu_event(void *v,void *event){
 PianoEu *s=state(0);u32 code=H(event,0);
 if(code==PE_ACTION){
  s=state(1);if(!s)return 0;s->view=(u32)v;if(!piano_ok(s))return 0;
  s->mode=!s->mode;if(s->mode){capture(s);live_begin(&s->e);done(s);}rebuild(v);return 1;
 }
 if(s&&s->mode&&s->view==(u32)v&&(code==0x49||code==0x4a||code==0x4b)){s->mode=0;rebuild(v);return 0;} /* native tab: leave Euclid */
 if(!s||!s->mode||s->view!=(u32)v||code!=0xcf||!piano_ok(s))return 0;
 u32 key=W(event,8),i=8;for(u32 j=0;j<8;j++)if(pe_keys[j]==key)i=j;if(i==8)return 0;
 capture(s);edit(s,i,(int)W(event,12));done(s);rebuild(v);return 1;
}
void melodic_locks_header(void*);int melodic_locks_event(void*,void*);void melodic_locks_menu(int);
/* Native header hooks: capture first, then CH1 chord capture. */
int chord_view_visible(void);void chord_view_set(int);
void piano_after_header(void *v){
 chord_capture(v);PianoEu *s=state(0);
 if(s&&s->view!=(u32)v){s->mode=0;s->e.valid=0;}
 if(s)s->view=(u32)v;else if(B(MODEL,0x12c)==PIANO_PAGE&&!B(v,0x125dae)&&eu_pitched_type(owner_type(current_owner()))){s=state(1);if(s)s->view=(u32)v;}
 if(chord_view_visible()){if(s)s->mode=0;chord_live_header(v);return;}
 piano_eu_header(v);
 if(!s||!s->mode){bars_header(v);melodic_locks_header(v);} /* CH8 */
}
int seq_nav_event(void*,void*);
static int piano_select_merge(void*,void*);
int piano_event(void *v,void *event){piano_select_merge(v,event);if(seq_nav_event(v,event))return 1;if(H(event,0)==PE_ACTION&&chord_live_active())chord_open_from_seq();if(chord_live_event(v,event))return 1;if(!chord_view_visible()&&!(state(0)&&state(0)->mode)&&melodic_locks_event(v,event))return 1;if(bars_event(v,event))return 1;if(piano_eu_event(v,event))return 1;return chord_piano_event(v,event);}
void piano_eu_nav(u32 page){PianoEu *s=state(0);if(s&&page!=PIANO_PAGE){s->mode=0;s->select=s->select_drag=0;s->view=0;}}
/* Header: an "Euclidean" tab in the free slot 0, left of Event / Sequence /
   Automation, as on one-shot tracks (P9; hidden since CH8). Hidden while live
   chord mode owns the piano roll.
   P11 (owner: the tab can't be seen on the device; "also give me Euclidean via
   the burger menu"): on a pitched piano roll the burger menu F9's Select cell
   (EU10, a one-shot feature) becomes Euclidean; elsewhere it stays Select. */
extern const char select_label[];
static void eu_menu(int pitched,int on){
 for(u32 m=0;m<20;m++){
  u8 *menu=(u8*)0x30030168u+m*0xe0u;if(W(menu,0)!=0xf9u)continue;u32 n=B(menu,0xcc);
  for(u32 i=0;i<n&&i<10;i++){u8 *c=menu+4+i*20;u32 code=W(c,0);
   if(code==0x1051u||code==PE_ACTION){W(c,0)=pitched?PE_ACTION:0x1051u;W(c,4)=(u32)(pitched?(on?"Euclidean ON":"Euclidean"):select_label);}}
 }
}
int piano_eu_toolbar(void *m,void *out){
 PianoEu *s=state(0);int ok=B(m,0x12c)==PIANO_PAGE&&eu_pitched_type(owner_type(current_owner()));
 extern void seq_nav_menus(int);seq_nav_menus(ok);if(!ok)return 0;
 int chord=chord_view_visible(),eu=s&&s->mode&&!chord;
 u32 tab=s&&s->view?B((void*)s->view,0x125dac):1;
 /* P20 (owner: keep the native striped tabs). The P18 flicker came from the
    piano view posting header event 68 {tab id, on} whenever it rebuilds;
    header_root_event drops those while Chord or Euclid is shown. */
 int changed=header_fixed_tab(out,0,0x1060,"Chord",chord);
 changed|=header_fixed_tab(out,1,0x1061,"Euclid",eu);
 changed|=header_fixed_tab(out,2,0x49,"Step",!chord&&!eu&&tab==0);
 changed|=header_fixed_tab(out,3,0x4a,"Seq",!chord&&!eu&&tab==1);
 changed|=header_fixed_action(out,4,0x1051,"Select",s&&s->select);
 changed|=header_fixed_action(out,5,0x4d,"Clear",0);
 return changed;
}
int piano_selecting(void *v){PianoEu *s=state(0);return s&&s->view==(u32)v&&piano_ok(s)&&s->select;}
int piano_select_toggle(void *v){PianoEu *s=state(1);if(!s)return 0;s->view=(u32)v;if(!piano_ok(s))return 0;s->select=!s->select;B((u8*)v+0x38,0xa50)=s->select?1:0; /* P18: own state; on = native box mode (owner: rectangle works, no note writing), off = native editing. */B((u8*)v+0x38,0x4f0)=1;s->select_drag=0;rebuild(v);return 1;}
void piano_mode_set(void *v,int mode){PianoEu *s=state(1);if(!s)return;s->view=(u32)v;if(!piano_ok(s))return;s->mode=mode;if(mode){capture(s);live_begin(&s->e);done(s);}rebuild(v);}

void *piano_current_view(void){PianoEu *s=state(0);return s&&piano_ok(s)?(void*)s->view:0;}

/* P17 piano hardware events (vtable slot 13 entry 0815B548), before native.
 * 1. Owner on P16: "the Row encoder is actually choosing a step". Native AD
 *    (encoder turn) sends encoder 1 in the Step tab to the grid cursor
 *    (081763F2) instead of the encoder bar. While the Euclid view owns the
 *    encoders, encoder 1 goes to the bar like encoders 2..8 (0817037C).
 * 2. Owner: Left/Right should go to the previous/next note in every view, not
 *    the previous/next sequence (native AE -> 0815B3EC). The note after (or
 *    before) the first selected one, in time then pitch order, becomes the
 *    only selected note (native selection 08174BAC/08174C4E). Live chord mode
 *    keeps its own Left/Right (chord walk). PROJ+Left stays Undo. */
int chord_live_hw(void*,void*);
static int note_key_less(const u32 *a,const u32 *b){return a[1]<b[1]||(a[1]==b[1]&&(a[4]&0xffffu)<(b[4]&0xffffu));}
static int piano_step_note(void *v,int dir){
 void *node=0,*root=(void*)W(MODEL,0);u32 seq=W(v,0x11cd00);
 if(!root)return 1;
 if(!seq||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,seq,&node)||!node){seq=W(MODEL,0x144);node=0; /* P18: view handle unset on hardware */
  if(!seq||!FN(0x0812dfe8,int(*)(void*,u32,void*))(root,seq,&node)||!node)return 1;}
 void *c=(u8*)node+12,*g=(u8*)v+0x38;u32 n=W(c,0x3000);if(n>511)return 1;
 u32 cur[6]={0},has=0,e[6];
 u32 sn=W(g,0x1254);if(sn>511)sn=0;
 for(u32 i=0;i<n;i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,e))break;if(B(e,0)!=1)continue;
  int sel=0;for(u32 j=0;j<sn&&!sel;j++){u32 x=0;FN(0x08174d70,int(*)(void*,u32,void*))(g,j,&x);if(x&&x==e[3])sel=1;} /* return value not a success flag */
  if(sel&&(!has||(dir>0?note_key_less(e,cur):note_key_less(cur,e)))){for(u32 k=0;k<6;k++)cur[k]=e[k];has=1;}}
 u32 best[6]={0},found=0;
 for(u32 i=0;i<n;i++){if(!FN(0x0810d2c0,int(*)(void*,u32,void*))(c,i,e))break;if(B(e,0)!=1)continue;
  int after=!has||(dir>0?note_key_less(cur,e):note_key_less(e,cur));if(!after)continue;
  if(!found||(dir>0?note_key_less(e,best):note_key_less(best,e))){for(u32 k=0;k<6;k++)best[k]=e[k];found=1;}}
 if(!found)return 1; /* at the first/last note: stay */
 FN(0x08174bac,void(*)(void*,u32))(g,0);FN(0x08174c4e,void(*)(void*,u32,u32))(g,best[3],0);rebuild(v);return 1;
}
__attribute__((used,retain)) int piano_hw(void *v,void *e){
 /* P21 (owner on P20: a pad in Euclid inserted a chord): in the Euclid view a
    pad press sets the selected row's Note to that pad's pitch (published by M7). */
 {PianoEu *s=state(0);u32 c=H(e,0);
  if((c==0xb0||c==0xb1)&&s&&s->mode&&s->view==(u32)v&&piano_ok(s)&&!chord_view_visible()){
   if(c==0xb0){extern int chord_pad_pitch(unsigned);int pitch=chord_pad_pitch(W(e,8));
    if(pitch>=0){u32 ev[5]={0xcf,0,0x18d,(u32)pitch+1u,0};piano_eu_event(v,ev);rebuild(v);}}
   return 1;}}
 if(chord_live_hw(v,e))return 1;
 u32 code=H(e,0);PianoEu *s=state(0);
 if(code==0xad&&W(e,8)==0&&s&&s->mode&&s->view==(u32)v&&piano_ok(s)&&!chord_view_visible()){ /* P18: any native tab (P17 required Step; hardware was on Seq) */
  FN(0x0817037c,void(*)(void*,u32,u32))((u8*)v+0x55f0,0,W(e,12));return 1;
 }
 if(code==0xae&&(W(e,8)==0||W(e,8)==9)&&!W((void*)0x24048d60u,8)&&B(MODEL,0x12c)==PIANO_PAGE)
  return piano_step_note(v,W(e,8)?1:-1);
 return 0;
}

/* P17 (owner on P16: "the selection rectangle always opens from the lower
 * middle, no matter where I tap"). The native piano grid's drag on empty space
 * (mode 5, 081762B0) spans the rectangle from the anchor at grid +A48, but the
 * native touch-down (08174998) stores that anchor only while box-select (+A50)
 * is on; otherwise a stale anchor is used. Store the first finger first. */
/* P17 (owner: "the behaviour I want from Select is to select multiple notes at
 * once by pointing at them"). While Select is on, each touch adds what it
 * touches to the selection kept from before the touch; touching one note that
 * was already selected takes it out again. The native box (+A50) does the hit
 * test; the selection before the first finger is snapshotted here. */
static int sel_has(PianoEu *s,u32 id){for(u32 i=0;i<s->snap_n;i++)if(s->snap[i]==id)return 1;return 0;}
__attribute__((used,retain)) void grid_touch_down(void *g,void *point,u32 id){
 if(g&&point&&!W(g,0x9bc)){
  W(g,0xa48)=W(point,0);W(g,0xa4c)=W(point,4);
  PianoEu *s=state(0);
  if(s&&piano_selecting((u8*)g-0x38)){B(g,0xa50)=1; /* P19 (owner on P18: with Select lit, touches still deleted notes): box mode is forced at every touch */
   u32 n=W(g,0x1254),x=0;if(n>128)n=128;s->snap_n=0;
   for(u32 i=0;i<n;i++){x=0;FN(0x08174d70,int(*)(void*,u32,u32*))(g,i,&x);if(x)s->snap[s->snap_n++]=x;}s->held=1;}
 }
 FN(0x08174999,void(*)(void*,void*,u32))(g,point,id);
}
/* The native touch selection reaches the view later, as event E6 (CH7). Merge
 * then, once per touch: union with the snapshot; a tap on one already selected
 * note removes it. */
static void select_merge_now(void *v,PianoEu *s){
 void *g=(u8*)v+0x38;u32 n=W(g,0x1254),x=0,now[128],k=0;if(n>128)n=128;
 for(u32 i=0;i<n;i++){x=0;FN(0x08174d70,int(*)(void*,u32,u32*))(g,i,&x);if(x)now[k++]=x;}
 u32 drop=k==1&&sel_has(s,now[0])?now[0]:0;
 FN(0x08174bac,void(*)(void*,u32))(g,0);
 for(u32 i=0;i<s->snap_n;i++)if(s->snap[i]!=drop)FN(0x08174c4e,void(*)(void*,u32,u32))(g,s->snap[i],0);
 for(u32 i=0;i<k;i++)if(now[i]!=drop&&!sel_has(s,now[i]))FN(0x08174c4e,void(*)(void*,u32,u32))(g,now[i],0);
 s->snap_n=0;rebuild(v);
}
/* P21 (owner on P20: with Select lit, touching a note still deleted it). A tap
 * (native mode 9C0 = 1, no drag) ends in the native note toggle (08176A28 ->
 * 08175200: delete or create). With Select lit the tap is turned into a tiny
 * rectangle (mode 5, rect +A34 around the touch) so the native up selects the
 * note under the finger instead; then the selection merges. */
__attribute__((used,retain)) void grid_touch_up(void *g,void *point,u32 id){
 void *v=(u8*)g-0x38;PianoEu *s=state(0);int sel=s&&s->held&&W(g,0x9bc)==1&&piano_selecting(v);
 /* P24 (owner 6c): in chord mode a tap never creates or deletes a note. On a
    note it selects (tiny native rect, as Select does): the E6 event then picks
    that chord. On empty space it moves the chord cursor there. */
 {extern int chord_view_visible(void);extern int chord_live_tap(void*,int);
  if(!sel&&W(g,0x9bc)==1&&B(g,0x9c0)==1&&chord_view_visible()&&!piano_selecting(v)){
   int x=(int)W(g,0x9c4),y=(int)W(g,0x9c8),hit=0;u8 *w=(u8*)W(g,0x34);
   for(u32 o=0;w&&o<0x9000;o+=0x48){if(!B(w+o,0x31))continue;int rx=(int)W(w+o,4),ry=(int)W(w+o,8),rw=(int)W(w+o,12),rh=(int)W(w+o,16);if(x>=rx-2&&x<rx+rw+2&&y>=ry-2&&y<ry+rh+2){hit=1;break;}}
   W(g,0xa34)=(u32)(x-2);W(g,0xa38)=(u32)(y-2);W(g,0xa3c)=5;W(g,0xa40)=5;B(g,0xa44)=1;B(g,0x9c0)=5;
   FN(0x08176a29,void(*)(void*,void*,u32))(g,point,id);
   if(!hit)chord_live_tap(g,x);
   return;
  }}
 if(!sel){FN(0x08176a29,void(*)(void*,void*,u32))(g,point,id);return;}
 s->held=0;
 if(B(g,0x9c0)==1){
  /* A tap. The native box apply (08174CE8) adds the notes touching the rect,
     so a tap on notes that were all selected already removes them instead. */
  int x=(int)W(g,0x9c4),y=(int)W(g,0x9c8);u32 hits[8],nh=0,all=1;u8 *w=(u8*)W(g,0x34);
  for(u32 o=0;w&&o<0x9000&&nh<8;o+=0x48){if(!B(w+o,0x31))continue;int rx=(int)W(w+o,4),ry=(int)W(w+o,8),rw=(int)W(w+o,12),rh=(int)W(w+o,16);
   if(x>=rx-2&&x<rx+rw+2&&y>=ry-2&&y<ry+rh+2){hits[nh++]=W(w+o,0x40);if(!sel_has(s,W(w+o,0x40)))all=0;}}
  W(g,0xa34)=(u32)(x-2);W(g,0xa38)=(u32)(y-2);W(g,0xa3c)=5;W(g,0xa40)=5;B(g,0xa44)=1;B(g,0x9c0)=5;
  FN(0x08176a29,void(*)(void*,void*,u32))(g,point,id);
  if(nh&&all){FN(0x08174bac,void(*)(void*,u32))(g,0);for(u32 i=0;i<s->snap_n;i++){int keep=1;for(u32 j=0;j<nh;j++)if(hits[j]==s->snap[i])keep=0;if(keep)FN(0x08174c4e,void(*)(void*,u32,u32))(g,s->snap[i],0);}}
  else{for(u32 i=0;i<s->snap_n;i++)FN(0x08174c4e,void(*)(void*,u32,u32))(g,s->snap[i],0);}
  s->snap_n=0;rebuild(v);return;
 }
 FN(0x08176a29,void(*)(void*,void*,u32))(g,point,id);
 select_merge_now(v,s); /* a drag: the native rectangle replaced the selection; add the earlier one */
}
static int piano_select_merge(void *v,void *event){
 PianoEu *s=state(0);if(H(event,0)!=0xe6||!s||!s->held||!piano_selecting(v))return 0;s->held=0;
 void *g=(u8*)v+0x38;u32 n=W(g,0x1254),x=0,now[128],k=0;if(n>128)n=128;
 for(u32 i=0;i<n;i++){x=0;FN(0x08174d70,int(*)(void*,u32,u32*))(g,i,&x);if(x)now[k++]=x;}
 u32 drop=k==1&&sel_has(s,now[0])?now[0]:0;
 FN(0x08174bac,void(*)(void*,u32))(g,0);
 for(u32 i=0;i<s->snap_n;i++)if(s->snap[i]!=drop)FN(0x08174c4e,void(*)(void*,u32,u32))(g,s->snap[i],0);
 for(u32 i=0;i<k;i++)if(now[i]!=drop&&!sel_has(s,now[i]))FN(0x08174c4e,void(*)(void*,u32,u32))(g,now[i],0);
 s->snap_n=0;rebuild(v);return 0; /* the event continues to the native/locks handlers */
}

/* P18 (owner on P17: with Select off the rectangle still opened at the lower
 * middle). Before the native drag turns into the rectangle (9C0 becomes 5),
 * take the anchor from the native first-touch point (+9C4), however the touch
 * started. */
__attribute__((used,retain)) void grid_touch_move(void *g,void *point,u32 id){
 if(g&&B(g,0x9c0)!=5&&W(g,0x9bc)==1){W(g,0xa48)=W(g,0x9c4);W(g,0xa4c)=W(g,0x9c8);}
 FN(0x08175f39,void(*)(void*,void*,u32))(g,point,id);
}

/* P20: Chord or Euclid is the visible melodic view (native tab lights must stay off). */
int piano_custom_view(void){PianoEu *s=state(0);if(B(MODEL,0x12c)!=PIANO_PAGE)return 0;return chord_view_visible()||(s&&s->mode&&piano_ok(s));}
