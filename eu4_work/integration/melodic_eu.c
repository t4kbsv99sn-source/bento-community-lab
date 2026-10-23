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
typedef struct {u32 magic,view,mode,row,assigned;Euclid e;char note[8],gate[8];} PianoEu;
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
 EuPad p=live_value(&s->e);u32 gate=(s->e.preview>>8)&127u,pitch=eu_mel_pitch(&s->e),on=!s->assigned||eu_enabled(p); /* unassigned rows show C3 */
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
/* CH4: separate live layer. Rows never write, move or delete clip notes; the
   clip keeps playing underneath and M7 adds the row hits on top. */
static void ensure(PianoEu *s){if(!s->assigned){live_assign_pitch(&s->e,eu_mel_pitch(&s->e));s->assigned=1;}}
static void edit(PianoEu *s,u32 i,int value){
 Euclid *e=&s->e;EuPad p=live_value(e);e->status=EU_OK;
 if(i==0){s->row=value<1?0:value>4?3:(u32)value-1;e->pad=s->row;return;}
 if(i==1){
  if(value<=0){if(s->assigned&&eu_enabled(p))live_edit(e,5,0);return;}
  u32 pitch=(u32)(value>128?128:value)-1;
  if(live_pitch_owner(e,pitch,s->row)>=0){e->status=EU_USED;return;}
  live_assign_pitch(e,pitch);e->preview=(e->preview&~127u)|pitch;s->assigned=1;
  if(!eu_enabled(p)&&eu_pulses(p))live_edit(e,5,1);
  return;
 }
 if(i>=2&&i<=4){ensure(s);live_edit(e,i-1,value);p=live_value(e);live_edit(e,5,eu_pulses(p)>0);return;}
 if(i==5){ensure(s);u32 g=value<1?1:value>64?64:(u32)value;live_set_gate(e,g);e->preview=(e->preview&~(127u<<8))|(g<<8);return;}
 if(i==6||i==7){ensure(s);live_dynamic(e,i==6?4:6,value);}
}
int piano_eu_event(void *v,void *event){
 PianoEu *s=state(0);u32 code=H(event,0);
 if(code==PE_ACTION){
  s=state(1);if(!s)return 0;s->view=(u32)v;if(!piano_ok(s))return 0;
  s->mode=!s->mode;if(s->mode){capture(s);live_begin(&s->e);done(s);}rebuild(v);return 1;
 }
 if(!s||!s->mode||s->view!=(u32)v||code!=0xcf||!piano_ok(s))return 0;
 u32 key=W(event,8),i=8;for(u32 j=0;j<8;j++)if(pe_keys[j]==key)i=j;if(i==8)return 0;
 capture(s);edit(s,i,(int)W(event,12));done(s);rebuild(v);return 1;
}
/* Native header hooks: capture first, then CH1 chord capture. */
void piano_after_header(void *v){
 chord_capture(v);PianoEu *s=state(0);
 if(s&&s->view!=(u32)v){s->mode=0;s->e.valid=0;}
 if(s)s->view=(u32)v;else if(B(MODEL,0x12c)==PIANO_PAGE&&!B(v,0x125dae)&&eu_pitched_type(owner_type(current_owner()))){s=state(1);if(s)s->view=(u32)v;}
 if(chord_live_active()){if(s)s->mode=0;chord_live_header(v);return;}
 piano_eu_header(v);
 if(!s||!s->mode)bars_header(v); /* CH8 */
}
int piano_event(void *v,void *event){if(chord_live_event(v,event))return 1;if(bars_event(v,event))return 1;if(piano_eu_event(v,event))return 1;return chord_piano_event(v,event);}
void piano_eu_nav(u32 page){PianoEu *s=state(0);if(s&&page!=PIANO_PAGE){s->mode=0;s->view=0;}}
/* Header: "Euclid" beside Chord on the pitched piano roll. */
int piano_eu_toolbar(void *m,void *out){
 return 0; /* CH8 (owner): Euclid button removed from the piano roll for now */
 PianoEu *s=state(0);if(!s||B(m,0x12c)!=PIANO_PAGE||!piano_ok(s)||chord_live_active())return 0;
 return header_action_lit(out,PE_ACTION,s->mode?"Euclid ON":"Euclid",s->mode!=0);
}
