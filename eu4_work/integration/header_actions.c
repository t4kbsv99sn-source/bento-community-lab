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
static int custom(unsigned id){return id>=0x1051u&&id<=0x1055u;}
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
void header_sync(const void *out){
 if(*(volatile uint32_t*)ROOT!=ROOT_VTABLE)return;
 const uint8_t *cur=ROOT+0x34u;
 int tab=0;for(unsigned i=0;i<6;i++)if(rid(REC(out,i))==0x1055u||rid(REC(cur,i))==0x1055u)tab=1;
 for(unsigned i=0;i<6;i++){
  const uint8_t *a=REC(out,i),*b=REC(cur,i);
  if(tab&&a[0x22]&&a[0x21]!=b[0x21]){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;}
  if(!custom(rid(a))&&!custom(rid(b)))continue;
  if(rid(a)!=rid(b)||a[0x20]!=b[0x20]||a[0x21]!=b[0x21]||a[0x22]!=b[0x22]){*(volatile uint8_t*)(ROOT+0x117cu)=1;return;}
 }
}
