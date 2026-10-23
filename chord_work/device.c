/* CH1: native parameter editor and insertion-first hardware test. */
#include "device.h"
#include "native_insert.h"
#include "../eu4_work/integration/header_actions.h"
#define W(p,o) (*(volatile uint32_t*)((uint8_t*)(p)+(o)))
#define H(p,o) (*(volatile uint16_t*)((uint8_t*)(p)+(o)))
#define B(p,o) (*(volatile uint8_t*)((uint8_t*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define MODEL ((void*)0x30024b00u)
#define CH_ACTION 0x1052u
#define CH_INSERT 0x1053u
/* Native SEQ handler 08142D58: pitched tracks always use page 17 (piano roll);
   page 27 is the one-shot step grid. CH1 wrongly assumed 27. */
#define PIANO_PAGE 0x17u
/* Preflight full native registry; never replace an occupied descriptor. */
static const uint16_t keys[16]={0x196,0x197,0x19a,0x19b,0x19d,0x19e,0x19f,0x177, /* CH8: encoder 8 = Bars (owner), was Grid 1D1 */0x1d2,0x1d3,0x128,0x129,0x12a,0x12b,0x12c,0x12d};
static const char *const labels[16]={"Chord type","Voicing","Inversion","Rhythm","Start","End","Velocity","Grid","Progression","Preset","Root","Key","Scale","Chord length","Edit chord","Auto voicing"};
static const char *const type_names[]={"Major","Minor","Dim","Aug","Sus2","Sus4","Maj7","Min7","7","Add9","Half-dim7","MinMaj7","Quartal","Dim7","AugMaj7","Diatonic","Diatonic 7"};
static const char *const voice_names[]={"Close","Open","Drop 2"};
/* CH7 Rhythm (owner choice, replaces Strum): the chord repeats inside its length. */
static const char *const rhythm_names[]={"Hold","2 hits","3 hits","4 hits","8ths","16ths","Offbeat","Tresillo"};
enum {RHYTHMS=8};
static const char *const grid_names[]={"1/4","1/8","1/16","1/32","1/64"};
static const char *const scale_names[]={"Major","Minor","Dorian","Mixolydian","Harmonic minor"};
static const char *const key_names[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
static const unsigned grids[]={3840,1920,960,480,240};
typedef struct {
 uint32_t magic,view,piano,active,nav,seq,owner,clip,mode,preset,root,key,scale,duration,selected,auto_voice,grid,status,inserted,live,bank,empty,diatonic,rhythm,held,aud,seen,quiet;char name[24];
 uint32_t context[4];ChordNative native;Progression phrase;
 char titles[3][72],roots[128][8];const char *root_choices[128],*preset_choices[12];
} Device;
static void live_off(Device *s);
const char *bars_title(void);const char *const *bars_names(void);unsigned bars_index(void*,int*);const char *bars_text(void*);void bars_set(void*,int);
#define LABEL(i) ((i)==7?bars_title():labels[i])
int chord_audition_publish(int active,const unsigned char *count,const signed char *off,unsigned velocity);
int chord_pad_pitch(unsigned pad);
unsigned chord_pads_held(void);
static uint32_t next_id(void){void *root=(void*)W(MODEL,0);return root?W(root,0x68):0;}
static void zero(void *p,unsigned n){for(unsigned i=0;i<n;i++)((uint8_t*)p)[i]=0;}
static Device *state(int create){
 void **slot=chord_state_slot();if(!slot)return 0;Device *s=*slot;
 if(s)return s->magic==0x31484342u?s:0;if(!create)return 0;
 uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(Device)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 s=FN(0x08104c08,void*(*)(unsigned))(bytes);if((uint32_t)s!=cursor)return 0;zero(s,sizeof(*s));s->magic=0x31484342u;s->root=48;s->duration=4;s->auto_voice=1;s->grid=2;
 for(unsigned i=0;i<128;i++){char *d=s->roots[i];const char *name=key_names[i%12];while(*name)*d++=*name++;int oct=(int)i/12-1;if(oct<0){*d++='-';oct=-oct;}*d++='0'+oct;*d=0;s->root_choices[i]=s->roots[i];} /* Bento naming: C0 = MIDI 12, C3 = MIDI 48 (owner) */
 for(unsigned i=0;i<12;i++)s->preset_choices[i]=chord_preset_name(i);*slot=s;return s;
}
static unsigned current_owner(void){unsigned owner=0;if(!FN(0x08133cfc,int(*)(void*,void*))(MODEL,&owner))return 0;return owner;}
static int pitched(unsigned owner){unsigned t=owner?FN(0x08133f7c,unsigned(*)(void*,void*))(MODEL,&owner):0;return t==15||t==18||t==19||t==22;} /* 15 multisample, 18 wavetable, 19 granular, 22 external */
static unsigned valid_context(Device *s){return s&&s->seq&&s->owner&&W(MODEL,0x144)==s->seq&&current_owner()==s->owner&&pitched(s->owner);}
/* Hit starts and lengths (ticks) of rhythm r inside a chord of len ticks. */
static unsigned hits(unsigned r,uint32_t len,uint32_t *at,uint32_t *dur){
 const uint32_t st=960;unsigned n=0;
 if(r==0||r>=RHYTHMS||len<2){at[0]=0;dur[0]=len;return 1;}
 if(r<=3){uint32_t slot=len/(r+1);for(unsigned i=0;i<=r;i++){at[n]=i*slot;dur[n]=slot/2?slot/2:1;n++;}return n;}
 if(r==7){static const uint8_t tr[3]={0,3,6};for(uint32_t b=0;b<len&&n<CH_MAX_CHORDS;b+=8*st)for(unsigned i=0;i<3&&n<CH_MAX_CHORDS;i++){uint32_t t=b+tr[i]*st;if(t<len){at[n]=t;dur[n]=st;n++;}}}
 else{uint32_t step=r==5?st:2*st,d=r==5?st/2:st;for(uint32_t t=r==6?st:0;t<len&&n<CH_MAX_CHORDS;t+=step){at[n]=t;dur[n]=d;n++;}}
 for(unsigned i=0;i<n;i++)if(at[i]+dur[i]>len)dur[i]=len-at[i];
 return n;
}
/* The phrase as written: every chord split into its rhythm hits. */
static int expand(const Device *s,Progression *out){
 *out=s->phrase;out->count=0;
 for(unsigned i=0;i<s->phrase.count;i++){
  const Chord *c=&s->phrase.chords[i];uint32_t at[CH_MAX_CHORDS],dur[CH_MAX_CHORDS];unsigned n=hits(s->rhythm,c->end-c->start,at,dur);
  for(unsigned j=0;j<n;j++){if(out->count>=CH_MAX_CHORDS)return CH_CAPACITY;Chord h=*c;h.strum=0;h.start=c->start+at[j];h.end=h.start+dur[j];out->chords[out->count++]=h;}
 }
 return CH_OK;
}
static int check(Device *s){
 Progression x;int r=expand(s,&x);if(r){s->status=(unsigned)r;return 0;}
 ChordNote notes[CH_MAX_NOTES];int n=chord_render(&x,notes,CH_MAX_NOTES,s->clip);return n<0?(s->status=(unsigned)-n,0):(s->status=0,1);
}
static void generate(Device *s){
 unsigned count=s->mode? (s->preset==2?3:4):1;
 unsigned duration=s->duration*960;if(!duration)duration=960;
 unsigned start=s->phrase.count?s->phrase.chords[0].start:0;
 Progression p;int r=chord_generate(&p,s->preset,s->key,s->scale,s->root,start,duration);
 if(r){s->status=r;return;}p.auto_voice=s->auto_voice;p.grid=grids[s->grid];
 if(!s->mode){Chord c=s->phrase.count?s->phrase.chords[s->selected]:p.chords[0];c.root=(int16_t)s->root;c.start=start;c.end=start+duration;c.degree=0;p.count=1;p.chords[0]=c;}
 else if(!s->auto_voice)for(unsigned i=0;i<count;i++){p.chords[i].root=(int16_t)(s->root+(p.chords[i].root-(int)s->root+120)%12);p.chords[i].inversion=0;}
 if(s->mode&&s->phrase.count==p.count&&s->phrase.preset==p.preset){for(unsigned i=0;i<p.count;i++){Chord *old=&s->phrase.chords[i],*c=&p.chords[i];if(old->quality_override){c->type=old->type;c->quality_override=1;}c->voicing=old->voicing;c->strum=old->strum;c->velocity=old->velocity;if(old->manual_inversion){c->inversion=old->inversion;c->manual_inversion=1;}}if(s->auto_voice)chord_voicelead(&p);}s->phrase=p;if(s->selected>=s->phrase.count)s->selected=0;check(s);
}
static int registry(Device *s){
 uint32_t r=W((void*)0x30031484u,0);if(!r)return 0;
 for(unsigned i=0;i<16;i++){void *d=(void*)(r+keys[i]*32);if(H(d,0)&&W(d,4)!=(uint32_t)LABEL(i))return 0;}
 int lo[16]={0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0};
 int hi[16]={CH_TYPES+1,2,3,RHYTHMS-1,(int)(s->clip/grids[s->grid]),(int)(s->clip/grids[s->grid]),127,8,1,11,127,11,4,256,(int)(s->phrase.count?s->phrase.count:1),1};
 int pitches[CH_MAX_VOICES];Chord plain=s->phrase.chords[s->selected];plain.inversion=0;plain.voicing=0;int count=chord_notes(&plain,pitches);hi[2]=count>0?count-1:2;
 const char *const *choices[16]={type_names,voice_names,0,rhythm_names,0,0,0,bars_names(),0,s->preset_choices,s->root_choices,key_names,scale_names,0,0,0};
 unsigned nums[16]={CH_TYPES+2,3,0,RHYTHMS,0,0,0,9,0,12,128,12,5,0,0,0};
 for(unsigned i=0;i<16;i++){void *d=(void*)(r+keys[i]*32);zero(d,32);H(d,0)=keys[i];B(d,2)=choices[i]?7:(i==8||i==15)?6:2;W(d,4)=(uint32_t)LABEL(i);W(d,8)=(uint32_t)choices[i];W(d,12)=nums[i];W(d,16)=(uint32_t)lo[i];W(d,20)=(uint32_t)hi[i];}return 1;
}
void chord_capture(void *v){
 if(!v||B(MODEL,0x12c)!=PIANO_PAGE)return;unsigned owner=current_owner();if(!pitched(owner)||B(v,0x125dae))return;
 Device *s=state(1);if(!s)return;unsigned seq=W(v,0x11cd00),length=W(v,0x11cd18);if(!seq||!length||length>256)return;
 if(s->owner&&s->owner!=owner&&s->live)live_off(s); /* CH9: opening another track's piano roll ends chord mode */
 if(s->seq!=seq||s->owner!=owner){s->active=0;s->seq=seq;s->owner=owner;s->clip=length*960;s->selected=0;s->inserted=0;zero(&s->phrase,sizeof(s->phrase));s->duration=length>=16?4:1;generate(s);}
 if(s->piano!=(uint32_t)v)B(MODEL,0x14c)=1;s->piano=(uint32_t)v;s->clip=length*960;
}
static void title(Device *s){
 char *d=s->titles[0];const char *t=s->mode?"Progression / ":"Chord / ";while(*t)*d++=*t++;t=s->root_choices[s->root];while(*t)*d++=*t++;*d=0;
 d=s->titles[1];t=s->mode?chord_preset_name(s->preset):"Single chord";while(*t)*d++=*t++;*d=0;
 const char *status=s->status==CH_CAPACITY?"Clip note limit":s->status==CH_CONFLICT?"Overlapping note":s->status==CH_RANGE?"Outside clip or pitch range":s->status==CH_STALE?"Sequence changed":s->status==CH_MEMORY?"No edit memory":s->status?"Invalid chord settings":s->inserted?"Inserted. Back to piano roll to play.":"Draft settings. Tap Insert to add notes.";
 d=s->titles[2];while(*status)*d++=*status++;*d=0;
}
static void refresh(Device *s){title(s);registry(s);B(MODEL,0x14c)=1;if(s->view)FN(0x08145cf4,void(*)(void*))((void*)s->view);}
static void open(Device *s){
 if(!valid_context(s)||!registry(s))return;
 for(unsigned i=0;i<4;i++)s->context[i]=W(MODEL,0x13c+i*4);
 s->active=1;s->nav=1;s->view=0;s->inserted=0;title(s);FN(0x081420ec,void(*)(void*,unsigned,unsigned,unsigned,unsigned))(MODEL,0x1a,0,0,0);s->nav=0;
}
static void close(Device *s){
 s->active=0;s->view=0;if(!valid_context(s))return;for(unsigned i=0;i<4;i++)W(MODEL,0x13c+i*4)=s->context[i];
 FN(0x081420ec,void(*)(void*,unsigned,unsigned,unsigned,unsigned))(MODEL,PIANO_PAGE,0,0,0);B(MODEL,0x14c)=1;
}
/* CH9 (owner): chord mode stays on for its track in other views; only the piano
   view (encoders, highlight) goes away. Pads keep playing chords (chord_track_tick). */
void chord_nav(void *m,unsigned page){(void)m;Device *s=state(0);if(!s||s->nav)return;if(page!=0x1a){s->active=0;s->view=0;}if(page!=PIANO_PAGE){s->piano=0;s->held=0;}}
int chord_header(void *m,void *handle,void *out,unsigned mode,unsigned caller){
 (void)m;(void)handle;(void)mode;Device *s=state(0);if(!s||!s->active||(caller&~1u)!=0x08145f22u||!registry(s))return 0;
 s->view=(uint32_t)out-0x93c4;title(s);zero(out,0x54);B(out,0)=3;for(unsigned i=0;i<3;i++)W(out,4+i*4)=(uint32_t)s->titles[i];for(unsigned i=0;i<16;i++)H(out,0x14+i*2)=keys[i];return 1;
}
int chord_get(void *m,void *handle,unsigned key,void *out){
 (void)m;(void)handle;Device *s=state(0);if(!s||!(s->active||s->live)||!out)return 0;if(!key){W(out,0)=0;return 1;}
 int rel=0;Chord *c=&s->phrase.chords[s->selected];unsigned values[16]={s->diatonic?(unsigned)CH_TYPES+s->diatonic-1:(unsigned)c->type,(unsigned)c->voicing,(unsigned)c->inversion,s->rhythm,c->start/grids[s->grid],c->end/grids[s->grid],c->velocity,s->piano?bars_index((void*)(uintptr_t)s->piano,&rel):0,s->mode,s->preset,s->root,s->key,s->scale,s->duration,s->selected+1,s->auto_voice};
 for(unsigned i=0;i<16;i++)if(key==keys[i]){W(out,0)=values[i];return 1;}return 0;
}
static void insert(Device *s){
 if(!check(s))return;s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
 Progression x;expand(s,&x);s->status=(unsigned)chord_native_insert(&s->native,MODEL,&x);if(!s->status)s->inserted=1;refresh(s);
}
static int action(Device *s,unsigned code){
 if(code==CH_ACTION){if(s->active)close(s);else open(s);return 1;}
 if(code==CH_INSERT&&s->active){insert(s);return 1;}return 0;
}
/* CH5 diatonic chord types (owner): quality from the root's degree in the
   project key/scale (native keys 8E root, index 0 = A; 8D scale, see
   docs/releases/ch5/DESIGN.md). Non-heptatonic scales use their parent. */
static const uint8_t scales[][7]={{0,2,4,5,7,9,11},{0,2,3,5,7,8,10},{0,2,3,5,7,8,11},{0,2,3,5,7,9,11},{0,2,3,5,7,9,10},{0,1,3,5,7,8,10},{0,2,4,6,7,9,11},{0,2,4,5,7,9,10},{0,1,3,5,6,8,10}};
static unsigned scale_row(unsigned native){
 switch(native){case 3:case 4:case 5:case 21:return 1;case 15:return 2;case 16:return 3;case 17:return 4;case 18:return 5;case 19:return 6;case 20:return 7;case 22:return 8;default:return 0;}
}
static int diatonic_type(int root,int seventh){
 unsigned h=0,r=3,m=1;FN(0x08133e54,void(*)(void*,void*))(MODEL,&h);
 FN(0x08133614,int(*)(void*,void*,unsigned,void*))(MODEL,&h,0x8e,&r);FN(0x08133614,int(*)(void*,void*,unsigned,void*))(MODEL,&h,0x8d,&m);
 const uint8_t *sc=scales[scale_row(m)];unsigned tonic=(r%12+9)%12,pc=(unsigned)((root%12+12-(int)tonic)%12),d=0;
 while(d<6&&sc[d+1]<=pc)d++;
 unsigned third=(sc[(d+2)%7]+12-sc[d])%12,fifth=(sc[(d+4)%7]+12-sc[d])%12,sev=(sc[(d+6)%7]+12-sc[d])%12;
 if(!seventh)return third==4?(fifth==8?CH_AUG:CH_MAJOR):(fifth==6?CH_DIM:CH_MINOR);
 if(third==4)return fifth==8?CH_AUG_MAJ7:sev==11?CH_MAJ7:CH_DOM7;
 if(fifth==6)return sev==9?CH_DIM7:CH_HALF_DIM;
 return sev==11?CH_MIN_MAJ7:CH_MIN7;
}
static void apply_diatonic(Device *s){if(!s->diatonic)return;for(unsigned i=0;i<s->phrase.count&&i<CH_MAX_CHORDS;i++)s->phrase.chords[i].type=(int16_t)diatonic_type(s->phrase.chords[i].root,s->diatonic==2);}
/* Apply one encoder value to the draft; returns 1 when the key is a chord key. */
static int edit(Device *s,unsigned key,int value){
 unsigned i;for(i=0;i<16;i++)if(key==keys[i])break;if(i==16)return 0;
 Progression old=s->phrase;unsigned old_rhythm=s->rhythm,old_settings[9];for(unsigned j=0;j<9;j++)old_settings[j]=W(s,32+j*4);Chord *c=&s->phrase.chords[s->selected];s->inserted=0;s->status=0;
 if(i==0){if(value<0||value>CH_TYPES+1)return 1;s->diatonic=value>=CH_TYPES?(unsigned)(value-CH_TYPES+1):0;if(!s->diatonic)c->type=(int16_t)value;c->quality_override=1;if(c->inversion>2)c->inversion=0;}
 if(i==1)c->voicing=(int16_t)value;
 if(i==2){c->inversion=(int16_t)value;c->manual_inversion=1;}
 if(i==3){if(value<0||value>=RHYTHMS)return 1;s->rhythm=(unsigned)value;c->strum=0;}
 if(i==4)c->start=(unsigned)value*grids[s->grid];
 if(i==5)c->end=(unsigned)value*grids[s->grid];
 if(i==6)c->velocity=(uint8_t)value;
 if(i==7)return 1; /* CH8: Bars, handled by chord_live_event (clip length) */
 if(i==8){s->mode=value?1:0;s->selected=0;generate(s);}
 if(i==9){if(value<0||value>=12)return 1;s->preset=(unsigned)value;if(s->scale<=CH_SCALE_MINOR)s->scale=chord_preset_minor(s->preset)?CH_SCALE_MINOR:CH_SCALE_MAJOR;generate(s);}
 if(i==10){if(value<0||value>127)return 1;s->root=(unsigned)value;s->key=s->root%12;generate(s);}
 if(i==11||i==12){if(value<0||value>(i==11?11:4))return 1;if(i==11)s->key=(unsigned)value;else s->scale=(unsigned)value;s->root=s->root-s->root%12+s->key;s->status=(unsigned)chord_reharmonize(&s->phrase,s->key,s->scale);}
 if(i==13){if(value<1||value>256)return 1;s->duration=(unsigned)value;generate(s);}
 if(i==14){if(value<1||(unsigned)value>s->phrase.count)return 1;s->selected=(unsigned)value-1;}
 if(i==15){s->auto_voice=value?1:0;s->phrase.auto_voice=s->auto_voice;if(s->auto_voice)s->status=(unsigned)chord_voicelead(&s->phrase);}
 apply_diatonic(s);if(!s->status)check(s);if(s->status){s->phrase=old;s->rhythm=old_rhythm;for(unsigned j=0;j<9;j++)W(s,32+j*4)=old_settings[j];}return 1;
}
int chord_event(void *v,void *e){
 Device *s=state(0);if(!s||!s->active||s->view!=(uint32_t)v)return 0;if(action(s,H(e,0)))return 1;if(H(e,0)!=0xcf)return 0;
 if(!edit(s,W(e,8),(int)W(e,12)))return 0;refresh(s);return 1;
}

/* CH4 live chord mode on the piano roll (page 17): SEQ double-tap toggles the
   eight piano encoders to chord bank 1 (Type..Grid) / bank 2 (Progression..Auto
   voicing). Every accepted edit replaces the previous draft notes, so the result
   is visible in the piano roll and plays immediately. Leaving keeps the notes. */
static void draft(Device *s){
 if(!check(s))return;s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;s->empty=0;
 int r=chord_native_clear_for(&s->native,MODEL,&s->phrase);if(r&&r!=CH_STALE){s->status=(unsigned)r;return;}
 Progression x;expand(s,&x);s->status=(unsigned)chord_native_insert(&s->native,MODEL,&x);if(!s->status)s->inserted=1;
 s->seen=next_id(); /* our own notes are not recordings (CH9) */
}
static void piano_rebuild(Device *s){if(s->piano)FN(0x081599bc,void(*)(void*))((void*)s->piano);}
int chord_live_active(void){Device *s=state(0);return s&&s->live&&s->piano;}
/* CH7: the current chord uses the native note selection (white, like a touch
   selection). Grid = piano view +38: 08174BAC clears, 08174C4E selects one ID
   (last argument 0 = don't post the E6 "selection changed" event). */
#define GRID(s) ((void*)((uint8_t*)(uintptr_t)(s)->piano+0x38))
static void highlight(Device *s){
 if(!s->piano)return;FN(0x08174bac,void(*)(void*,unsigned))(GRID(s),0);
 if(!s->live||s->empty)return;for(unsigned i=0;i<s->native.note_count&&i<CH_MAX_NOTES;i++)FN(0x08174c4e,void(*)(void*,uint32_t,unsigned))(GRID(s),s->native.note_ids[i],0);
}
static void live_off(Device *s){s->live=0;s->held=0;s->aud=0;highlight(s);s->native.note_count=0;chord_audition_publish(0,0,0,0);}
/* CH6: tell M7 the chord shape for every pitch class, so a keyboard pad plays the
   whole chord on its own pitch immediately (diatonic types follow the scale). */
static void publish(Device *s){
 unsigned char count[12];signed char off[12][CH_MAX_VOICES];Chord c=s->phrase.chords[s->selected];c.strum=0;
 for(unsigned pc=0;pc<12;pc++){
  c.root=(int16_t)(48+pc);if(s->diatonic)c.type=(int16_t)diatonic_type(c.root,s->diatonic==2);
  int p[CH_MAX_VOICES];int n=chord_notes(&c,p);if(n<=0){n=1;p[0]=c.root;}
  count[pc]=(unsigned char)n;for(int i=0;i<CH_MAX_VOICES;i++)off[pc][i]=(signed char)(i<n?p[i]-c.root:0);
 }
 chord_audition_publish(1,count,&off[0][0],s->phrase.chords[s->selected].velocity);s->aud=1;
}
/* CH5 navigation: Left/Right walk the chords already in the clip; Right past the
   last one opens an empty chord that starts where the previous one ends and is
   written only when an encoder is turned (owner choices). */
static unsigned chord_start(Device *s){return s->phrase.count?s->phrase.chords[0].start:0;}
static void single(Device *s,uint32_t start,uint32_t length){
 s->mode=0;s->selected=0;Chord c=s->phrase.count?s->phrase.chords[0]:(Chord){0};
 if(!s->phrase.count){Progression p;if(!chord_generate(&p,0,s->key,s->scale,s->root,0,960)){c=p.chords[0];}}
 c.root=(int16_t)s->root;c.start=start;c.end=start+(length?length:s->duration*960);c.degree=0;
 s->phrase.count=1;s->phrase.chords[0]=c;s->phrase.grid=grids[s->grid];s->phrase.auto_voice=s->auto_voice;
}
/* Group (same lowest note and pitch set) at a start, or 0. */
static int group(Device *s,uint32_t start,int *low,unsigned *mask,uint32_t *length,unsigned *velocity){return chord_native_adopt(&s->native,MODEL,start,low,mask,length,velocity)>0;}
static void adopt(Device *s,uint32_t start){
 int low;unsigned mask,velocity;uint32_t length;s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
 if(!group(s,start,&low,&mask,&length,&velocity))return;
 /* CH7: recognise a rhythm: consecutive identical groups that match a pattern
    become one chord with that rhythm (most hits wins, at least two). */
 uint32_t starts[64],g[CH_MAX_CHORDS]={0},gl[CH_MAX_CHORDS];unsigned m=0;int n=chord_native_starts(&s->native,MODEL,starts,64);
 for(int i=0;i<n&&m<CH_MAX_CHORDS;i++){if(starts[i]<start)continue;int l2;unsigned m2,v2;uint32_t len2;if(!group(s,starts[i],&l2,&m2,&len2,&v2)||l2!=low||m2!=mask)break;gl[m]=len2;g[m++]=starts[i]-start;}
 unsigned best=0,rhythm=0;uint32_t span=length;
 for(unsigned r=1;r<RHYTHMS&&m>=2;r++)for(uint32_t steps=1;steps<=64;steps++){
  uint32_t at[CH_MAX_CHORDS],dur[CH_MAX_CHORDS],L=steps*960;unsigned k=hits(r,L,at,dur);if(k<2||k>m||k<=best)continue;
  unsigned ok=1;for(unsigned j=0;j<k;j++)if(at[j]!=g[j]||dur[j]!=gl[j])ok=0;if(ok&&start+L<=s->clip){best=k;rhythm=r;span=L;}
 }
 /* Own exactly the notes of every hit (probing above overwrote the IDs). */
 {uint32_t ids[CH_MAX_NOTES];unsigned nid=0,k=best?best:1;int l2;unsigned m2,v2;uint32_t len2;
  for(unsigned j=0;j<k;j++){if(!group(s,start+g[j],&l2,&m2,&len2,&v2))continue;for(unsigned q=0;q<s->native.note_count&&nid<CH_MAX_NOTES;q++)ids[nid++]=s->native.note_ids[q];}
  for(unsigned q=0;q<nid;q++)s->native.note_ids[q]=ids[q];s->native.note_count=nid;}
 s->rhythm=rhythm;s->root=(unsigned)low;s->key=s->root%12;single(s,start,span);Chord *c=&s->phrase.chords[0];c->velocity=(uint8_t)(velocity?velocity:100);c->inversion=0;c->voicing=0;c->strum=0;
 for(int t=0;t<CH_TYPES;t++){Chord probe=*c;probe.type=(int16_t)t;int pitches[CH_MAX_VOICES];int k=chord_notes(&probe,pitches);if(k<=0)continue;
  unsigned mm=0;for(int i=0;i<k;i++)mm|=1u<<((pitches[i]-low)%24);if(mm==mask){c->type=(int16_t)t;break;}}
 s->empty=0;s->status=0;
}
/* Index of the first of the identical, back-to-back groups ending at starts[i]. */
static int first_hit(Device *s,const uint32_t *starts,int i){
 int low,l2;unsigned mask,m2,v;uint32_t len;if(!group(s,starts[i],&low,&mask,&len,&v))return i;
 while(i>0&&group(s,starts[i-1],&l2,&m2,&len,&v)&&l2==low&&m2==mask)i--;return i;
}
static void step_chord(Device *s,int dir){
 uint32_t starts[64];s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
 int n=chord_native_starts(&s->native,MODEL,starts,64);uint32_t here=chord_start(s);
 uint32_t end=s->phrase.count?s->phrase.chords[0].end:here+1;
 if(dir<0){
  /* Walk back to the first hit of the previous chord (same notes, back to back). */
  int i=n-1;while(i>=0&&starts[i]>=here)i--;if(i<0)return;
  adopt(s,starts[first_hit(s,starts,i)]);return;
 }
 for(int i=0;i<n;i++)if(starts[i]>here&&starts[i]>=end){adopt(s,starts[i]);return;}
 /* Past the last chord: empty slot after the current chord's end. */
 uint32_t next=s->phrase.count?s->phrase.chords[0].end:0;if(next>=s->clip)return;
 s->native.note_count=0;single(s,next,s->duration*960);s->empty=1;s->status=0;
}
/* SEQ double-tap on the pitched piano roll (fx_dispatch) toggles live chord mode. */
int chord_open_from_seq(void){
 Device *s=state(0);if(!s||!s->piano||s->active||!valid_context(s)||B(MODEL,0x12c)!=PIANO_PAGE)return 0;
 if(s->live)live_off(s);
 else{
  /* Enter on the last chord in the clip, or an empty slot at the start. */
  s->live=1;s->bank=0;s->seen=next_id();s->quiet=0;s->native.note_count=0;uint32_t starts[64];s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
  int n=chord_native_starts(&s->native,MODEL,starts,64);if(n>0)adopt(s,starts[first_hit(s,starts,n-1)]);else{single(s,0,s->duration*960);s->empty=1;}
  registry(s);title(s);
 }
 piano_rebuild(s);return 1;
}
/* CH8 live overlay (owner): while a pad is held, the Chord type encoder shows
   the chord being played, e.g. "Dm7" or "C/E" (Bento note names, no octave). */
static const char *const suffix[CH_TYPES]={"","m","dim","aug","sus2","sus4","maj7","m7","7","add9","m7b5","mMaj7","4ths","dim7","+maj7"};
static void chord_name(Device *s){
 Chord c=s->phrase.chords[s->selected];char *d=s->name;const char *t=key_names[c.root%12];while(*t)*d++=*t++;
 t=c.type>=0&&c.type<CH_TYPES?suffix[c.type]:"";while(*t)*d++=*t++;
 int p[CH_MAX_VOICES];int n=chord_notes(&c,p);if(n>0&&p[0]%12!=c.root%12){*d++='/';t=key_names[p[0]%12];while(*t)*d++=*t++;}
 *d=0;
}
static void overlay(Device *s,void *v){if(s->held&&!s->bank){chord_name(s);FN(0x08170656,void(*)(void*,unsigned,const char*))((uint8_t*)v+0x55f0,0,s->name);}}
/* After the native piano header: bind the current chord bank to the 8 encoders. */
void chord_live_header(void *v){
 Device *s=state(0);if(!s||!s->live||s->piano!=(uint32_t)v||!valid_context(s)||!registry(s))return;
 void *bar=(uint8_t*)v+0x55f0;
 for(unsigned i=0;i<8;i++){
  unsigned key=keys[s->bank*8+i],value=0;chord_get(MODEL,0,key,&value);
  H(v,0x11bcc0+i*2)=(uint16_t)key;W(v,0x11bcd0+i*4)=value;W(v,0x11bca0+i*4)=s->seq;
  void *slot=(uint8_t*)bar+0x38+i*0x468;FN(0x08170656,void(*)(void*,unsigned,const char*))(bar,i,0);
  FN(0x08171c1c,void(*)(void*,unsigned,int,unsigned))(slot,key,(int)value,1);
  FN(0x0817e85e,void(*)(void*,const char*))((uint8_t*)slot+0x3c8,LABEL(s->bank*8+i));
 }
 if(!s->bank){int rel;bars_index(v,&rel);if(rel)FN(0x08170656,void(*)(void*,unsigned,const char*))(bar,7,bars_text(v));} /* CH8 +/- */
 if(s->status){title(s);FN(0x08170656,void(*)(void*,unsigned,const char*))(bar,0,s->titles[2]);}
 publish(s);highlight(s);overlay(s,v);
}
/* Piano view hardware events (vtable slot 13, 0815B548): 0xAE = arrows with the
   button index at +8 (0 Left, 9 Right); native calls 0815B3EC(-1/+1). In live
   chord mode Left/Right walk chords instead (owner request). */
int chord_live_hw(void *v,void *e){
 Device *s=state(0);if(!s||!s->live||s->piano!=(uint32_t)v||!valid_context(s))return 0;
 /* CH6: pad press (0xB0, pad at +8). M7 already played the chord on the pad's
    pitch and published that pitch; it becomes the current chord's root. */
 if(H(e,0)==0xb0){int pitch=chord_pad_pitch(W(e,8));if(pitch<0)return 1;
  if(edit(s,0x128,pitch)&&!s->status)draft(s);s->held++;registry(s);piano_rebuild(s);return 1;}
 if(H(e,0)==0xb1){if(s->held)s->held--;piano_rebuild(s);return 1;}
 if(H(e,0)!=0xae||(W(e,8)!=0&&W(e,8)!=9)||W((void*)0x24048d60u,8))return 0;
 step_chord(s,W(e,8)?1:-1);registry(s);piano_rebuild(s);return 1;
}
int chord_live_event(void *v,void *e){
 Device *s=state(0);if(!s||!s->live||s->piano!=(uint32_t)v||!valid_context(s))return 0;
 unsigned code=H(e,0);
 if(code==CH_ACTION){s->bank^=1u;piano_rebuild(s);return 1;}
 /* CH7 (owner): a touch selection in chord mode picks the chord under it. */
 if(code==0xe6){
  uint32_t id=0,start=0;s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
  unsigned last=W(GRID(s),0x1254); /* selected IDs at grid +A54, count +1254: the touch adds the newest */
  if(last&&FN(0x08174d70,int(*)(void*,unsigned,uint32_t*))(GRID(s),last-1,&id)&&chord_native_find(&s->native,MODEL,id,&start)){
   uint32_t starts[64];int n=chord_native_starts(&s->native,MODEL,starts,64);
   for(int i=0;i<n;i++)if(starts[i]==start){adopt(s,starts[first_hit(s,starts,i)]);break;}
   registry(s);
  }
  piano_rebuild(s);return 1;
 }
 if(code!=0xcf)return 0;
 if(W(e,8)==0x177){bars_set((void*)(uintptr_t)s->piano,(int)W(e,12));piano_rebuild(s);return 1;} /* CH8 Bars = clip length */
 if(!edit(s,W(e,8),(int)W(e,12)))return 0;if(!s->status)draft(s);registry(s);piano_rebuild(s);return 1;
}
int chord_piano_event(void *v,void *e){Device *s=state(0);if(!s||s->piano!=(uint32_t)v||!valid_context(s))return 0;return action(s,H(e,0));}
static int add_button(void *out,unsigned id,const char *label){return header_action(out,id,label);}
int chord_toolbar(void *m,void *out,int changed){
 /* CH3: the piano roll header (page 17) has one free slot, used by Euclid.
    Chord opens by double-tapping SEQ; only the editor shows Back/Insert. */
 Device *s=state(0);(void)m;if(!s||!valid_context(s))return changed;
 if(s->live&&s->piano&&B(m,0x12c)==PIANO_PAGE)return changed|header_action_lit(out,CH_ACTION,s->bank?"Chord 2/2":"Chord 1/2",1);
 if(!s->active)return changed;
 changed|=add_button(out,CH_ACTION,s->active?"Back":"Chord");if(s->active)changed|=add_button(out,CH_INSERT,"Insert");return changed;
}

/* CH9: called for every UI message (fx_dispatch). Chord pads are on while the
   chord-mode track is the selected one, in any view; off for other tracks. */
void chord_track_tick(void){
 Device *s=state(0);if(!s||!s->live)return;unsigned want=current_owner()==s->owner&&pitched(s->owner);
 if(want!=s->aud){if(want)publish(s);else{chord_audition_publish(0,0,0,0);s->aud=0;}}
 /* CH9: chords the native recorder wrote get the Rhythm, once every chord pad
    has been up for 100 ms (the recorder finishes the note lengths on release). */
 uint32_t next=next_id();if(next==s->seen)return;
 if(!s->aud||!s->rhythm||W(MODEL,0x144)!=s->seq){s->seen=next;s->quiet=0;return;}
 if(chord_pads_held()){s->quiet=0;return;}
 uint32_t tick=W((void*)0x3001fe2cu,0);if(!s->quiet){s->quiet=tick|1u;return;}if(tick-s->quiet<100)return;
 s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
 chord_native_rhythmize(&s->native,MODEL,s->seen,s->rhythm,hits);s->seen=next_id();s->quiet=0;
}
