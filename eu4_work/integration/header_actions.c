/* CH2: custom actions in the native persistent header.
 *
 * The header snapshot (0x1C4 bytes) holds six 48-byte action records at +0x74:
 *   +0x00 label (<=31 chars)  +0x20 empty  +0x21 active tab  +0x22 tab group
 *   +0x2C action id
 * Native apply 0817FAF8 always copies label/id, but it only applies the
 * per-slot visibility while the header root's layout flag (+0x117C) is set.
 * Page navigation (0818012C) arms that flag; the first apply clears it.
 * An action added on a later tick therefore keeps the hidden state of the
 * empty slot it replaced. header_sync re-arms the flag when the set of our
 * actions differs from the header that is currently applied (root+0x34).
 */
#include <stdint.h>
#include "header_actions.h"
#define ROOT ((uint8_t*)0x30034d48u)
#define ROOT_VTABLE 0x081b3680u
#define REC(p,i) ((uint8_t*)(p)+0x74u+(unsigned)(i)*48u)
static unsigned rid(const uint8_t *r){return (unsigned)r[44]|((unsigned)r[45]<<8);}
static int custom(unsigned id){return id>=0x1051u&&id<=0x1064u;}
static int free_slot(const uint8_t *r){return !rid(r)&&!r[0]&&!r[0x22];}
int header_action_lit(void *out,unsigned id,const char *label,int lit){
 for(unsigned i=0;i<6;i++){
  uint8_t *d=REC(out,i);if(rid(d)!=id)continue;
  int change=d[0x20]!=0||d[0x21]!=(lit?1:0);d[0x20]=0;d[0x21]=lit?1:0;unsigned n=0;
  do{if(d[n]!=(uint8_t)label[n])change=1;d[n]=(uint8_t)label[n];}while(label[n++]&&n<31);
  d[31]=0;return change;
 }
 /* Rightmost free normal slot: directly left of Undo on SEQ pages. */
 for(int i=5;i>=0;i--){
  uint8_t *d=REC(out,i);if(!free_slot(d))continue;
  for(unsigned j=0;j<48;j++)d[j]=0;unsigned n=0;
  do{d[n]=(uint8_t)label[n];}while(label[n++]&&n<31);
  d[31]=0;d[0x21]=lit?1:0;d[44]=(uint8_t)id;d[45]=(uint8_t)(id>>8);return 1;
 }
 return 0;
}
int header_action(void *out,unsigned id,const char *label){return header_action_lit(out,id,label,0);}
/* CH5: a custom view tab in slot 0, left of the native tab group (Step,
   Sequence). While it is active the native tabs are shown inactive. */
int header_tab(void *out,unsigned id,const char *label,int active){
 uint8_t *d=REC(out,0);int change=0;
 if(rid(d)!=id){if(rid(d)||d[0])return 0;for(unsigned j=0;j<48;j++)d[j]=0;d[44]=(uint8_t)id;d[45]=(uint8_t)(id>>8);change=1;}
 unsigned n=0;do{if(d[n]!=(uint8_t)label[n])change=1;d[n]=(uint8_t)label[n];}while(label[n++]&&n<31);d[31]=0;
 if(d[0x20]||d[0x22]!=1||d[0x21]!=(active?1:0))change=1;d[0x20]=0;d[0x22]=1;d[0x21]=active?1:0;
 if(active)for(unsigned i=1;i<6;i++){uint8_t *t=REC(out,i);if(t[0x22]&&t[0x21]){t[0x21]=0;change=1;}}
 return change;
}
/* P17 (owner on P16: Step/Seq stay lit while Chord or Euclid is selected).
 * The native apply sets each button's selected state (+AC, 0816A5E6) only
 * while the layout flag is armed, and a tap on a native tab changes that state
 * by itself. Comparing records with the applied snapshot therefore misses it;
 * compare with the buttons' actual state (normal +54C, tab +A2C, 0xD0 each). */
static int stale_buttons(const uint8_t *out){
 int ours=0,stale=0;for(unsigned i=0;i<6;i++)if(custom(rid(REC(out,i))))ours=1;if(!ours)return 0;
 for(unsigned i=0;i<6;i++){
  const uint8_t *a=REC(out,i);if(!rid(a)||a[0x20])continue;
  const uint8_t *w=ROOT+(a[0x22]?0xa2cu:0x54cu)+i*0xd0u;
  if(*(volatile const uint8_t*)(w+0xac)!=(a[0x21]?1:0)){
   /* P18 (owner on P17: Seq stayed lit beside Chord/Euclid): set the widget's
      selected state directly too (0816A5E6, the native apply's own setter). */
   ((void(*)(const uint8_t*,unsigned))0x0816a5e7u)(w,a[0x21]?1u:0u);stale=1;
  }
 }
 return stale;
}
void header_sync(const void *out){
 if(*(volatile uint32_t*)ROOT!=ROOT_VTABLE)return;
 if(stale_buttons((const uint8_t*)out)){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;}
 const uint8_t *cur=ROOT+0x34u;
 if(((const uint8_t*)out)[0x194]!=cur[0x194]||((const uint8_t*)out)[0x195]!=cur[0x195]){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;} /* P17 burger */
 int tab=0;for(unsigned i=0;i<6;i++)if(rid(REC(out,i))==0x1055u||rid(REC(cur,i))==0x1055u||rid(REC(out,i))==0x1054u||rid(REC(cur,i))==0x1054u)tab=1;
 for(unsigned i=0;i<6;i++){
  const uint8_t *a=REC(out,i),*b=REC(cur,i);
  if(tab&&a[0x22]&&a[0x21]!=b[0x21]){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;}
  if(!custom(rid(a))&&!custom(rid(b))&&rid(a)!=0x1032u&&rid(b)!=0x1032u)continue;
  if(rid(a)!=rid(b)||a[0x20]!=b[0x20]||a[0x21]!=b[0x21]||a[0x22]!=b[0x22]){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;}
 }
}

/* P12: slot 0 overlaps the native pad selector on hardware. Use an explicit
 * visible slot and normal button, independently of the native tab group. */
int header_fixed_action(void *out,unsigned slot,unsigned id,const char *label,int lit){
 if(slot>=6)return 0;uint8_t *d=REC(out,slot);int changed=rid(d)!=id||d[0x20]||d[0x22]||d[0x21]!=(lit?1:0);
 unsigned n=0;do{if(d[n]!=(uint8_t)label[n])changed=1;d[n]=(uint8_t)label[n];}while(label[n++]&&n<31);d[31]=0;
 d[0x20]=0;d[0x21]=lit?1:0;d[0x22]=0;d[44]=(uint8_t)id;d[45]=(uint8_t)(id>>8);return changed;
}
/* Final native apply boundary: some device callers bypass the model snapshot
 * hook. Prepare the exact snapshot that is about to become visible. */
int header_remove_undo(void *out){int changed=0;for(unsigned i=0;i<6;i++){uint8_t *r=REC(out,i);if(rid(r)!=0x1032u)continue;for(unsigned j=0;j<48;j++)r[j]=0;r[0x20]=1;changed=1;}return changed;}
extern int mod_toolbar(void*,void*);extern int piano_eu_toolbar(void*,void*);extern int drum_seq_toolbar(void*,void*);
__attribute__((used,retain)) void device_header_prepare(void *out){
 void *model=(void*)0x30024b00u;extern void macro_periodic(void*);macro_periodic(out);mod_toolbar(model,out);piano_eu_toolbar(model,out);drum_seq_toolbar(model,out);
 header_remove_undo(out);
 /* P17: Projects / Settings / Date-Time live only in the Performance page burger. */
 extern int perf_page_active(void);unsigned page=*(volatile uint8_t*)((uint8_t*)model+0x12c);
 int mode=page==0x1a&&perf_page_active()?2:page==0x17?1:0;
 if(mode==2){((uint8_t*)out)[0x194]=0xf9;((uint8_t*)out)[0x195]=0;}
 extern void seq_nav_menus(int);seq_nav_menus(mode);header_sync(out);
}

int header_fixed_tab(void *out,unsigned slot,unsigned id,const char *label,int active){
 int changed=header_fixed_action(out,slot,id,label,active);uint8_t *r=REC(out,slot);if(r[0x22]!=1)changed=1;r[0x22]=1;return changed;
}

/* P20 (owner on P18/P19: Step flickered beside Chord; plain buttons rejected).
 * Root vtable slot 13 (0817FFB8) handles header events 68/69/6A {id at +8,
 * on at +C}; 68 lights the tab with that id (0817FEEC). The piano view posts
 * 68 {49/4A/4B, on} for its own tab when it rebuilds. While Chord or Euclid is
 * shown those requests are dropped, so the native tab lights stay off. */
extern int piano_custom_view(void);extern int drum_eu_view(void);
__attribute__((used,retain)) void header_root_event(void *root,void *event){
 const uint8_t *e=(const uint8_t*)event;unsigned code=e[0]|(e[1]<<8),id=e[8]|(e[9]<<8);
 unsigned on=e[12]|e[13]|e[14]|e[15];
 if(code==0x68u&&on&&(id==0x49u||id==0x4au||id==0x4bu)&&(piano_custom_view()||drum_eu_view()))return; /* P21: also the one-shot Euclidean view (owner on P20) */
 ((void(*)(void*,void*))0x0817ffb9u)(root,event);
}
