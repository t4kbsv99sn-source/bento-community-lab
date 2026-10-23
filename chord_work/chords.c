#include "chords.h"
static const uint8_t scales[CH_SCALES][7]={
 {0,2,4,5,7,9,11},{0,2,3,5,7,8,10},{0,2,3,5,7,9,10},{0,2,4,5,7,9,10},{0,2,3,5,7,8,11}};
static const uint8_t tones[CH_TYPES][CH_MAX_VOICES]={
 {0,4,7},{0,3,7},{0,3,6},{0,4,8},{0,2,7},{0,5,7},
 {0,4,7,11},{0,3,7,10},{0,4,7,10},{0,4,7,14},{0,3,6,10},{0,3,7,11},{0,5,10},{0,3,6,9},{0,4,8,11}};
static const uint8_t voices[CH_TYPES]={3,3,3,3,3,3,4,4,4,4,4,4,3,4,4};
static const char *const types[CH_TYPES]={"Major","Minor","Dim","Aug","Sus2","Sus4","Maj7","Min7","7","Add9","Half-dim7","MinMaj7","Quartal","Dim7","AugMaj7"};
typedef struct {const char *name;uint8_t count,minor,degree[8],major_v;} Preset;
/* Original tables of harmonic degrees, not copied commercial content. Zero-based. */
static const Preset presets[]={
 {"I-V-vi-IV",4,0,{0,4,5,3},0},{"vi-IV-I-V",4,0,{5,3,0,4},0},
 {"ii-V-I",3,0,{1,4,0},0},{"I-vi-IV-V",4,0,{0,5,3,4},0},
 {"I-IV-V-IV",4,0,{0,3,4,3},0},{"I-iii-vi-IV",4,0,{0,2,5,3},0},
 {"i-VI-III-VII",4,1,{0,5,2,6},0},{"i-VII-VI-VII",4,1,{0,6,5,6},0},
 {"i-iv-V-i",4,1,{0,3,4,0},1},{"i-VI-iv-V",4,1,{0,5,3,4},1},
 {"i-iv-VII-III",4,1,{0,3,6,2},0},{"i-III-VII-iv",4,1,{0,2,6,3},0}};
unsigned chord_preset_count(void){return sizeof(presets)/sizeof(presets[0]);}
const char *chord_preset_name(unsigned i){return i<chord_preset_count()?presets[i].name:0;}
unsigned chord_preset_minor(unsigned i){return i<chord_preset_count()?presets[i].minor:0;}
const char *chord_type_name(unsigned i){return i<CH_TYPES?types[i]:0;}
static unsigned absolute_degree(unsigned scale,unsigned degree){return scales[scale][degree%7]+12*(degree/7);}
int chord_degree_type(unsigned scale,unsigned degree,unsigned seventh){
 if(scale>=CH_SCALES||degree>=7||seventh>1)return -1;
 unsigned a=absolute_degree(scale,degree),third=absolute_degree(scale,degree+2)-a,fifth=absolute_degree(scale,degree+4)-a;
 if(!seventh){if(third==4&&fifth==7)return CH_MAJOR;if(third==3&&fifth==7)return CH_MINOR;if(third==3&&fifth==6)return CH_DIM;if(third==4&&fifth==8)return CH_AUG;return -1;}
 unsigned last=absolute_degree(scale,degree+6)-a;
 if(third==4&&fifth==7&&last==11)return CH_MAJ7;
 if(third==4&&fifth==7&&last==10)return CH_DOM7;
 if(third==3&&fifth==7&&last==10)return CH_MIN7;
 if(third==3&&fifth==6&&last==10)return CH_HALF_DIM;
 if(third==3&&fifth==7&&last==11)return CH_MIN_MAJ7;
 if(third==3&&fifth==6&&last==9)return CH_DIM7;
 if(third==4&&fifth==8&&last==11)return CH_AUG_MAJ7;
 return -1;
}
static void sort(int *p,unsigned n){for(unsigned i=1;i<n;i++){int v=p[i];unsigned j=i;while(j&&p[j-1]>v){p[j]=p[j-1];j--;}p[j]=v;}}
int chord_notes(const Chord *c,int p[CH_MAX_VOICES]){
 if(!c||!p||c->type<0||c->type>=CH_TYPES||c->root<0||c->root>127||c->voicing<0||c->voicing>=CH_VOICINGS||c->inversion<0||c->inversion>=voices[c->type]||!c->velocity||c->velocity>127||c->strum<-960||c->strum>960||c->end<=c->start)return -CH_INVALID;
 unsigned n=voices[c->type];if(c->voicing==CH_DROP2&&n<4)return -CH_INVALID;
 for(unsigned i=0;i<n;i++)p[i]=c->root+tones[c->type][i];
 for(int i=0;i<c->inversion;i++)p[i]+=12;sort(p,n);
 if(c->voicing==CH_OPEN){for(unsigned i=1;i<n;i+=2)p[i]+=12;}
 if(c->voicing==CH_DROP2)p[n-2]-=12;sort(p,n);
 for(unsigned i=0;i<n;i++){if(p[i]<0||p[i]>127)return -CH_RANGE;if(i&&p[i]==p[i-1])return -CH_INVALID;}
 return (int)n;
}
static int valid(const Progression *p){
 if(!p||!p->count||p->count>CH_MAX_CHORDS||p->key>11||p->scale>=CH_SCALES||p->tonic>127||p->tonic%12!=p->key||!p->grid||p->grid>61440||p->auto_voice>1||p->preset>=chord_preset_count())return 0;
 for(unsigned i=0;i<p->count;i++){
  const Chord *c=&p->chords[i];int notes[CH_MAX_VOICES];if(chord_notes(c,notes)<0||c->degree>6||c->seventh>1||c->quality_override>1||c->manual_inversion>1||c->pinned>1)return 0;
  if(i&&c->start<p->chords[i-1].end)return 0;
 }return 1;
}
static int lead(Progression *p){
 for(unsigned i=1;i<p->count;i++){
  Chord *c=&p->chords[i];if(c->manual_inversion)continue;int prior[CH_MAX_VOICES],best[CH_MAX_VOICES];
  int n=chord_notes(&p->chords[i-1],prior);if(n<0)return CH_INVALID;Chord chosen=*c;unsigned score_best=0xffffffffu;int found=0;
  /* Register candidates stay within an octave of the root pad's register.
     Deterministic ties prefer fewer octave changes, then lower inversion. */
  for(unsigned distance=0;distance<3;distance++)for(unsigned inv=0;inv<voices[c->type];inv++){
   Chord candidate=*c;candidate.root+=(distance==1?-12:distance==2?12:0);candidate.inversion=(int16_t)inv;
   int m=chord_notes(&candidate,best);if(m<0)continue;unsigned score=0;
   for(int v=0;v<m;v++){int delta=best[v]-prior[(unsigned)v*(unsigned)n/(unsigned)m];score+=(unsigned)(delta<0?-delta:delta);}
   if(score<score_best){score_best=score;chosen=candidate;found=1;}
  }if(!found)return CH_RANGE;*c=chosen;
 }return CH_OK;
}
int chord_voicelead(Progression *p){if(!valid(p))return CH_INVALID;Progression work=*p;for(unsigned i=1;i<work.count;i++)if(!work.chords[i].manual_inversion)work.chords[i].root=(int16_t)(work.tonic+scales[work.scale][work.chords[i].degree]);int result=lead(&work);if(!result)*p=work;return result;}
int chord_generate(Progression *p,unsigned preset,unsigned key,unsigned scale,unsigned tonic,uint32_t start,uint32_t duration){
 if(!p||preset>=chord_preset_count()||key>11||scale>=CH_SCALES||tonic>127||tonic%12!=key||!duration||duration>0x7fffffffu/presets[preset].count||start>0x7fffffffu-duration*presets[preset].count)return CH_INVALID;
 Progression work={0};work.key=key;work.scale=scale;work.tonic=tonic;work.grid=960;work.count=presets[preset].count;work.preset=preset;work.auto_voice=1;
 for(unsigned i=0;i<work.count;i++){
  Chord *c=&work.chords[i];c->degree=presets[preset].degree[i];c->root=tonic+scales[scale][c->degree];c->type=chord_degree_type(scale,c->degree,0);c->velocity=100;c->start=start+i*duration;c->end=c->start+duration;
  if(presets[preset].major_v&&c->degree==4){c->type=CH_MAJOR;c->quality_override=1;}
 }
 if(!valid(&work))return CH_RANGE;int result=lead(&work);if(result)return result;*p=work;return CH_OK;
}
int chord_reharmonize(Progression *p,unsigned key,unsigned scale){
 if(!valid(p)||key>11||scale>=CH_SCALES)return CH_INVALID;Progression work=*p;
 /* Preserve tonic octave; changing key does not drift the register. */
 work.tonic=p->tonic-p->key+key;if(work.tonic>127)return CH_RANGE;work.key=key;work.scale=scale;
 for(unsigned i=0;i<work.count;i++){
  Chord *c=&work.chords[i];int old_unvoiced=(int)p->tonic+scales[p->scale][c->degree];int octave=(c->root-old_unvoiced)/12;
  c->root=(int16_t)(work.tonic+scales[scale][c->degree]+octave*12);
  if(!c->quality_override){c->type=chord_degree_type(scale,c->degree,c->seventh);if(c->type<0)return CH_INVALID;}
  if(c->inversion>=voices[c->type])return CH_INVALID;
 }if(!valid(&work))return CH_RANGE;
 /* Rebase automatic roots before solving, so repeat changes do not drift. */
 if(work.auto_voice){for(unsigned i=1;i<work.count;i++)if(!work.chords[i].manual_inversion)work.chords[i].root=(int16_t)(work.tonic+scales[scale][work.chords[i].degree]);int r=lead(&work);if(r)return r;}
 *p=work;return CH_OK;
}
int chord_render(const Progression *p,ChordNote *out,unsigned capacity,uint32_t clip_end){
 if(!valid(p)||!out||!clip_end)return -CH_INVALID;ChordNote temp[CH_MAX_NOTES];unsigned count=0;
 for(unsigned i=0;i<p->count;i++){
  const Chord *c=&p->chords[i];int notes[CH_MAX_VOICES],n=chord_notes(c,notes);if(n<0)return n;
  if(c->end>clip_end)return -CH_RANGE;if(count+(unsigned)n>capacity)return -CH_CAPACITY;
  unsigned gap=(unsigned)(c->strum<0?-c->strum:c->strum);
  if(gap&&(unsigned)(n-1)>(c->end-c->start-1)/gap)return -CH_RANGE;
  for(int v=0;v<n;v++){
   unsigned rank=c->strum<0?(unsigned)(n-1-v):(unsigned)v;
   ChordNote *e=&temp[count++];e->start=c->start+rank*gap;e->end=c->end;e->pitch=(uint16_t)notes[v];e->velocity=c->velocity;e->chord=(uint8_t)i;e->voice=(uint8_t)v;e->reserved=0;
  }
 }for(unsigned i=0;i<count;i++)out[i]=temp[i];return (int)count;
}
static void put32(uint8_t *b,uint32_t v){for(unsigned i=0;i<4;i++)b[i]=(uint8_t)(v>>(i*8));}
static uint32_t get32(const uint8_t *b){uint32_t v=0;for(unsigned i=0;i<4;i++)v|=(uint32_t)b[i]<<(i*8);return v;}
static uint32_t checksum(const uint8_t *b,unsigned n){uint32_t h=2166136261u;for(unsigned i=0;i<n;i++)h=(h^b[i])*16777619u;return h;}
int chord_encode(const Progression *p,uint8_t out[CH_SERIAL_BYTES]){
 if(!valid(p)||!out)return CH_INVALID;for(unsigned i=0;i<CH_SERIAL_BYTES;i++)out[i]=0;
 put32(out,0x31484342u);put32(out+4,1);put32(out+8,p->key|(p->scale<<8)|(p->tonic<<16)|(p->auto_voice<<24));put32(out+12,p->grid);put32(out+16,p->count);put32(out+20,p->preset);
 for(unsigned i=0;i<p->count;i++){
  const Chord *c=&p->chords[i];uint8_t *b=out+24+i*24;
  put32(b,c->start);put32(b+4,c->end);put32(b+8,(uint16_t)c->root|((uint32_t)(uint16_t)c->type<<16));put32(b+12,(uint16_t)c->voicing|((uint32_t)(uint16_t)c->inversion<<16));
  put32(b+16,(uint16_t)c->strum|((uint32_t)c->velocity<<16)|((uint32_t)c->degree<<24));put32(b+20,c->seventh|((uint32_t)c->quality_override<<8)|((uint32_t)c->manual_inversion<<16)|((uint32_t)c->pinned<<24));
 }put32(out+CH_SERIAL_BYTES-4,checksum(out,CH_SERIAL_BYTES-4));return CH_OK;
}
int chord_decode(Progression *p,const uint8_t *in,unsigned size){
 if(!p||!in||size!=CH_SERIAL_BYTES||get32(in)!=0x31484342u||get32(in+4)!=1||get32(in+CH_SERIAL_BYTES-4)!=checksum(in,CH_SERIAL_BYTES-4))return CH_INVALID;
 Progression work={0};uint32_t h=get32(in+8);work.key=h&255;work.scale=(h>>8)&255;work.tonic=(h>>16)&255;work.auto_voice=h>>24;work.grid=get32(in+12);work.count=get32(in+16);work.preset=get32(in+20);if(work.count>CH_MAX_CHORDS)return CH_INVALID;
 for(unsigned i=0;i<work.count;i++){
  Chord *c=&work.chords[i];const uint8_t *b=in+24+i*24;uint32_t w;
  c->start=get32(b);c->end=get32(b+4);w=get32(b+8);c->root=(int16_t)w;c->type=(int16_t)(w>>16);w=get32(b+12);c->voicing=(int16_t)w;c->inversion=(int16_t)(w>>16);
  w=get32(b+16);c->strum=(int16_t)w;c->velocity=(uint8_t)(w>>16);c->degree=(uint8_t)(w>>24);w=get32(b+20);c->seventh=(uint8_t)w;c->quality_override=(uint8_t)(w>>8);c->manual_inversion=(uint8_t)(w>>16);c->pinned=(uint8_t)(w>>24);
 }if(!valid(&work))return CH_INVALID;*p=work;return CH_OK;
}
