/* CH1: native parameter editor and insertion-first hardware test. */
#include "device.h"
#include "native_insert.h"
#define W(p,o) (*(volatile uint32_t*)((uint8_t*)(p)+(o)))
#define H(p,o) (*(volatile uint16_t*)((uint8_t*)(p)+(o)))
#define B(p,o) (*(volatile uint8_t*)((uint8_t*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define MODEL ((void*)0x30024b00u)
#define CH_ACTION 0x1052u
#define CH_INSERT 0x1053u
/* Preflight full native registry; never replace an occupied descriptor. */
static const uint16_t keys[16]={0x196,0x197,0x19a,0x19b,0x19d,0x19e,0x19f,0x1d1,0x1d2,0x1d3,0x128,0x129,0x12a,0x12b,0x12c,0x12d};
static const char *const labels[16]={"Chord type","Voicing","Inversion","Strum ticks","Start","End","Velocity","Grid","Progression","Preset","Root","Key","Scale","Chord length","Edit chord","Auto voicing"};
static const char *const type_names[]={"Major","Minor","Dim","Aug","Sus2","Sus4","Maj7","Min7","7","Add9","Half-dim7","MinMaj7","Quartal","Dim7","AugMaj7"};
static const char *const voice_names[]={"Close","Open","Drop 2"};
static const char *const grid_names[]={"1/4","1/8","1/16","1/32","1/64"};
static const char *const scale_names[]={"Major","Minor","Dorian","Mixolydian","Harmonic minor"};
static const char *const key_names[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
static const unsigned grids[]={3840,1920,960,480,240};
typedef struct {
 uint32_t magic,view,piano,active,nav,seq,owner,clip,mode,preset,root,key,scale,duration,selected,auto_voice,grid,status,inserted;
 uint32_t context[4];ChordNative native;Progression phrase;
 char titles[3][72],roots[128][8];const char *root_choices[128],*preset_choices[12];
} Device;
static void zero(void *p,unsigned n){for(unsigned i=0;i<n;i++)((uint8_t*)p)[i]=0;}
static Device *state(int create){
 void **slot=chord_state_slot();if(!slot)return 0;Device *s=*slot;
 if(s)return s->magic==0x31484342u?s:0;if(!create)return 0;
 uint32_t cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(Device)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 s=FN(0x08104c08,void*(*)(unsigned))(bytes);if((uint32_t)s!=cursor)return 0;zero(s,sizeof(*s));s->magic=0x31484342u;s->root=48;s->duration=4;s->auto_voice=1;s->grid=2;
 for(unsigned i=0;i<128;i++){char *d=s->roots[i];const char *name=key_names[i%12];while(*name)*d++=*name++;int oct=(int)i/12-1;if(oct<0){*d++='-';oct=-oct;}*d++='0'+oct;*d=0;s->root_choices[i]=s->roots[i];}
 for(unsigned i=0;i<12;i++)s->preset_choices[i]=chord_preset_name(i);*slot=s;return s;
}
static unsigned current_owner(void){unsigned owner=0;if(!FN(0x08133cfc,int(*)(void*,void*))(MODEL,&owner))return 0;return owner;}
static int pitched(unsigned owner){unsigned t=owner?FN(0x08133f7c,unsigned(*)(void*,void*))(MODEL,&owner):0;return t==17||t==18||t==19||t==22;}
static unsigned valid_context(Device *s){return s&&s->seq&&s->owner&&W(MODEL,0x144)==s->seq&&current_owner()==s->owner&&pitched(s->owner);}
static int check(Device *s){ChordNote notes[CH_MAX_NOTES];int n=chord_render(&s->phrase,notes,CH_MAX_NOTES,s->clip);return n<0?(s->status=(unsigned)-n,0):(s->status=0,1);}
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
 for(unsigned i=0;i<16;i++){void *d=(void*)(r+keys[i]*32);if(H(d,0)&&W(d,4)!=(uint32_t)labels[i])return 0;}
 int lo[16]={0,0,0,-960,0,1,1,0,0,0,0,0,0,1,1,0};
 int hi[16]={CH_TYPES-1,2,3,960,(int)(s->clip/grids[s->grid]),(int)(s->clip/grids[s->grid]),127,4,1,11,127,11,4,256,(int)(s->phrase.count?s->phrase.count:1),1};
 int pitches[CH_MAX_VOICES];Chord plain=s->phrase.chords[s->selected];plain.inversion=0;plain.voicing=0;int count=chord_notes(&plain,pitches);hi[2]=count>0?count-1:2;
 const char *const *choices[16]={type_names,voice_names,0,0,0,0,0,grid_names,0,s->preset_choices,s->root_choices,key_names,scale_names,0,0,0};
 unsigned nums[16]={CH_TYPES,3,0,0,0,0,0,5,0,12,128,12,5,0,0,0};
 for(unsigned i=0;i<16;i++){void *d=(void*)(r+keys[i]*32);zero(d,32);H(d,0)=keys[i];B(d,2)=choices[i]?7:(i==8||i==15)?6:2;W(d,4)=(uint32_t)labels[i];W(d,8)=(uint32_t)choices[i];W(d,12)=nums[i];W(d,16)=(uint32_t)lo[i];W(d,20)=(uint32_t)hi[i];}return 1;
}
void chord_capture(void *v){
 if(!v||B(MODEL,0x12c)!=0x27)return;unsigned owner=current_owner();if(!pitched(owner)||B(v,0x125dae))return;
 Device *s=state(1);if(!s)return;unsigned seq=W(v,0x11cd00),length=W(v,0x11cd18);if(!seq||!length||length>256)return;
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
 FN(0x081420ec,void(*)(void*,unsigned,unsigned,unsigned,unsigned))(MODEL,0x27,0,0,0);B(MODEL,0x14c)=1;
}
void chord_nav(void *m,unsigned page){(void)m;Device *s=state(0);if(!s||s->nav)return;if(page!=0x1a){s->active=0;s->view=0;}if(page!=0x27)s->piano=0;}
int chord_header(void *m,void *handle,void *out,unsigned mode,unsigned caller){
 (void)m;(void)handle;(void)mode;Device *s=state(0);if(!s||!s->active||(caller&~1u)!=0x08145f22u||!registry(s))return 0;
 s->view=(uint32_t)out-0x93c4;title(s);zero(out,0x54);B(out,0)=3;for(unsigned i=0;i<3;i++)W(out,4+i*4)=(uint32_t)s->titles[i];for(unsigned i=0;i<16;i++)H(out,0x14+i*2)=keys[i];return 1;
}
int chord_get(void *m,void *handle,unsigned key,void *out){
 (void)m;(void)handle;Device *s=state(0);if(!s||!s->active||!out)return 0;if(!key){W(out,0)=0;return 1;}
 Chord *c=&s->phrase.chords[s->selected];unsigned values[16]={(unsigned)c->type,(unsigned)c->voicing,(unsigned)c->inversion,(unsigned)c->strum,c->start/grids[s->grid],c->end/grids[s->grid],c->velocity,s->grid,s->mode,s->preset,s->root,s->key,s->scale,s->duration,s->selected+1,s->auto_voice};
 for(unsigned i=0;i<16;i++)if(key==keys[i]){W(out,0)=values[i];return 1;}return 0;
}
static void insert(Device *s){
 if(!check(s))return;s->native.seq=s->seq;s->native.owner=s->owner;s->native.clip_end=s->clip;
 s->status=(unsigned)chord_native_insert(&s->native,MODEL,&s->phrase);if(!s->status)s->inserted=1;refresh(s);
}
static int action(Device *s,unsigned code){
 if(code==CH_ACTION){if(s->active)close(s);else open(s);return 1;}
 if(code==CH_INSERT&&s->active){insert(s);return 1;}return 0;
}
int chord_event(void *v,void *e){
 Device *s=state(0);if(!s||!s->active||s->view!=(uint32_t)v)return 0;if(action(s,H(e,0)))return 1;if(H(e,0)!=0xcf)return 0;
 unsigned key=W(e,8);int value=(int)W(e,12);unsigned i;for(i=0;i<16;i++)if(key==keys[i])break;if(i==16)return 0;
 Progression old=s->phrase;unsigned old_settings[9];for(unsigned j=0;j<9;j++)old_settings[j]=W(s,32+j*4);Chord *c=&s->phrase.chords[s->selected];s->inserted=0;s->status=0;
 if(i==0){if(value<0||value>=CH_TYPES)return 1;c->type=(int16_t)value;c->quality_override=1;if(c->inversion>2)c->inversion=0;}
 if(i==1)c->voicing=(int16_t)value;
 if(i==2){c->inversion=(int16_t)value;c->manual_inversion=1;}
 if(i==3)c->strum=(int16_t)value;
 if(i==4)c->start=(unsigned)value*grids[s->grid];
 if(i==5)c->end=(unsigned)value*grids[s->grid];
 if(i==6)c->velocity=(uint8_t)value;
 if(i==7){if(value<0||value>4)return 1;s->grid=(unsigned)value;s->phrase.grid=grids[s->grid];}
 if(i==8){s->mode=value?1:0;s->selected=0;generate(s);}
 if(i==9){if(value<0||value>=12)return 1;s->preset=(unsigned)value;if(s->scale<=CH_SCALE_MINOR)s->scale=chord_preset_minor(s->preset)?CH_SCALE_MINOR:CH_SCALE_MAJOR;generate(s);}
 if(i==10){if(value<0||value>127)return 1;s->root=(unsigned)value;s->key=s->root%12;generate(s);}
 if(i==11||i==12){if(value<0||value>(i==11?11:4))return 1;if(i==11)s->key=(unsigned)value;else s->scale=(unsigned)value;s->root=s->root-s->root%12+s->key;s->status=(unsigned)chord_reharmonize(&s->phrase,s->key,s->scale);}
 if(i==13){if(value<1||value>256)return 1;s->duration=(unsigned)value;generate(s);}
 if(i==14){if(value<1||(unsigned)value>s->phrase.count)return 1;s->selected=(unsigned)value-1;}
 if(i==15){s->auto_voice=value?1:0;s->phrase.auto_voice=s->auto_voice;if(s->auto_voice)s->status=(unsigned)chord_voicelead(&s->phrase);}
 if(!s->status)check(s);if(s->status){s->phrase=old;for(unsigned j=0;j<9;j++)W(s,32+j*4)=old_settings[j];}refresh(s);return 1;
}
int chord_piano_event(void *v,void *e){Device *s=state(0);if(!s||s->piano!=(uint32_t)v||!valid_context(s))return 0;return action(s,H(e,0));}
static int add_button(void *out,unsigned id,const char *label){
 int empty=-1,undo=-1;for(unsigned i=0;i<6;i++){unsigned key=H(out,0x74+i*48+44);if(key==id){void *d=(uint8_t*)out+0x74+i*48;int change=0;unsigned n=0;do{if(B(d,n)!=(uint8_t)label[n])change=1;B(d,n)=(uint8_t)label[n];}while(label[n++]);return change;}if(!key&&empty<0)empty=(int)i;if(key==0x1032)undo=(int)i;}
 if(empty<0)return 0;int target=undo>=0&&undo<empty?undo+1:empty;
 for(int i=empty;i>target;i--)for(unsigned j=0;j<12;j++)W(out,0x74+i*48+j*4)=W(out,0x74+(i-1)*48+j*4);
 void *d=(uint8_t*)out+0x74+target*48;zero(d,48);unsigned n=0;do{B(d,n)=(uint8_t)label[n];}while(label[n++]);H(d,44)=(uint16_t)id;return 1;
}
int chord_toolbar(void *m,void *out,int changed){
 Device *s=state(0);if(!s||!valid_context(s)||(!s->active&&(B(m,0x12c)!=0x27||!s->piano)))return changed;
 changed|=add_button(out,CH_ACTION,s->active?"Back":"Chord");if(s->active)changed|=add_button(out,CH_INSERT,"Insert");return changed;
}
