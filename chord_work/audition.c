#include "audition.h"
void chord_pad_off(ChordAudition *a,unsigned pad,ChordMidi off,void *context){
 if(!a||!off||pad>=16||!a->held[pad])return;
 for(unsigned i=0;i<a->count[pad];i++){unsigned p=a->pitch[pad][i];if(a->references[p]&&!--a->references[p])off(context,p,0);}
 a->held[pad]=a->count[pad]=0;
}
int chord_pad_on(ChordAudition *a,unsigned pad,const Chord *c,ChordMidi on,ChordMidi off,void *context){
 if(!a||!on||!off||pad>=16)return CH_INVALID;int notes[CH_MAX_VOICES],n=chord_notes(c,notes);if(n<0)return -n;
 /* Validate new chord before releasing an old one. Release always uses the
    pitches actually played, even if the encoders/root/scale later change. */
 chord_pad_off(a,pad,off,context);a->held[pad]=1;a->count[pad]=(uint8_t)n;
 for(int i=0;i<n;i++){unsigned p=(unsigned)notes[i];a->pitch[pad][i]=(uint8_t)p;if(!a->references[p]++)on(context,p,c->velocity);}
 return CH_OK;
}
void chord_audition_stop(ChordAudition *a,ChordMidi off,void *context){
 if(!a||!off)return;for(unsigned i=0;i<16;i++)chord_pad_off(a,i,off,context);
}
