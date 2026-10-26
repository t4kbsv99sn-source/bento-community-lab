/* P8 mod mode (M4): fast modulation on the native synth page.
 *
 * Synth page = native view class 0819E894 (Wavetable 18 incl. Analog, Granular
 * 19). Header (owner spec): MATRIX right next to the counter (opens the native
 * Mod Matrix exactly like the burger menu's "Modulation", action 0x0A) and MOD
 * left of it (toggles mod mode). The page's three tabs move one slot left.
 *
 * In mod mode a tap on a modulator tile (Envelope 1/2, LFO 1/2, Mod Seq; tile
 * touches arrive as event 79 {+8 tile id}) toggles it as a source (orange
 * outline) instead of selecting the tile. Turning an encoder whose parameter
 * is a native Mod Matrix destination then sets the depth of every selected
 * source on it: the encoder shows the depth (-100%..+100%, centre = 0) and
 * the parameter itself is not changed. Routes are the native ones (model event
 * D1 {D1, node, key|1<<16, source|slot<<16, amount -1000..1000}; three slots
 * per destination; source 0 removes), so the Mod Matrix shows them.
 * Switching tracks turns mod mode off.
 *
 * Native facts used (see docs/releases/p8/DESIGN.md):
 *  view +2430 track handle, +2434 track index, view+[+2434]+10238 selected
 *  tile, tile frames view+2700+40*i (record +34 colour, +38 width, +3C..+3E
 *  flags, written by 0815F0B6), encoder bar view+38, slots view+70+468*i
 *  (+9C key, +450/+454 range), 08170656 slot text, 08171C1C slot value,
 *  08131244 route lookup, destination tables 0819DE54 (60 x 24 bytes:
 *  node type, instance, key). */
#include "fx_shared.h"
#define MOD_MAGIC 0x444f4d50u
#define MOD_ACTION 0x1057u
#define MATRIX_ACTION 0x1058u
#define NATIVE_MATRIX 0x0bu /* P11: the synth page burger (menu F3) posts 0B "Modulation"; 0A is the pad menus */
#define TICK W((void*)0x3001fe2cu,0)
#define SYNTH_TICK 0x0815d7d0u
#define SYNTH_EVENT 0x0815f148u
#define DEST_TABLE 0x0819de54u
#define DEST_COUNT 60u
#define ORANGE 0xf6u
typedef struct {
 u32 magic,on,sources,view,seen,track,tile,node;
 u16 key[8];u32 slot_node[8];int amount[8],shown[8];u8 marked[8];
 u8 painted;
 u8 star[8];u16 star_key[8];int star_val[8]; /* P17: modulated-target marks */
 u32 star_sig[8]; /* P26: which source tags are shown */
 void *melodic_locks;
 void *drum_cache; /* P11: kick_ui's carrier cache (the UI struct is full) */
 void *macros; /* P27 */
} Mod;
void **mod_state_slot(void);
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static Mod *mod(int create){
 void **slot=mod_state_slot();if(!slot)return 0;Mod *s=*slot;
 if(s)return s->magic==MOD_MAGIC?s:0;if(!create)return 0;
 u32 cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(Mod)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 s=FN(0x08104c08,void*(*)(u32))(bytes);if((u32)s!=cursor)return 0;zero(s,sizeof(*s));s->magic=MOD_MAGIC;*slot=s;return s;
}
void **macro_state_slot(void){Mod *s=mod(1);return s?&s->macros:0;}
void **drum_cache_slot(void){Mod *s=mod(1);return s?&s->drum_cache:0;}
static u32 type_of(u32 h){return h?FN(0x08133f7c,u32(*)(void*,void*))(MODEL,&h):0;}
static int synth(u32 track){u32 t=type_of(track);return t==18||t==19;}
/* Tiles 3 Env1, 4 Env2, 8 LFO1, 9 LFO2, 7 Mod Seq -> source bit / native id. */
static const u8 src_tile[5]={3,4,8,9,7},src_id[5]={1,2,4,5,8};
static int source_bit(u32 tile){for(int i=0;i<5;i++)if(src_tile[i]==tile)return i;return -1;}
/* Section node of a tile: (node type, instance). */
static int tile_node(u32 tile,u32 track_type,u32 *type,u32 *idx){
 static const u8 t[10]={0,0,8,9,9,10,10,0,11,11},n[10]={0,1,0,0,1,0,1,0,0,1};
 if(tile>9||tile==7)return 0;*type=tile<2?(track_type==19?7u:6u):t[tile];*idx=n[tile];return 1;
}
static u32 child(u32 track,u32 type,u32 idx){
 u32 c=0,k=0;
 for(u32 i=0;i<64;i++){if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&track,i,&c))return 0;if(type_of(c)==type&&k++==idx)return c;}
 return 0;
}
static int kind(u32 track,u32 h,u32 *type,u32 *idx){
 u32 c=0,count[16];zero(count,sizeof count);
 for(u32 i=0;i<64;i++){
  if(!FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&track,i,&c))return 0;
  u32 t=type_of(c);if(c==h){*type=t;*idx=t<16?count[t]:0;return 1;}if(t<16)count[t]++;
 }
 return 0;
}
static int dest_ok(u32 type,u32 idx,u32 key){
 for(u32 i=0;i<DEST_COUNT;i++){const u32 *d=(const u32*)(DEST_TABLE+24*i);if(d[0]==type&&d[1]==idx&&d[2]==key)return 1;}
 return 0;
}
/* Route of source on (h,key): returns its slot, or -1 with *free = first free slot. */
static int route(u32 h,u32 key,u32 source,int *amount,int *free){
 *free=-1;*amount=0;
 for(u32 slot=0;slot<3;slot++){
  u32 out[3]={0,0,0};
  if(!FN(0x08131244,u32(*)(void*,u32*,u32,u32,u32*))(MODEL,&h,key,slot,out)){if(*free<0)*free=(int)slot;continue;}
  if((out[1]&0xffffu)==source){*amount=(int)out[0];return (int)slot;}
 }
 return -1;
}
static void post_route(u32 h,u32 key,u32 source,u32 slot,int amount){
 u32 ev[5]={0xd1,h,(key&0xffffu)|1u<<16,source|slot<<16,(u32)amount};
 FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);
}
static int shown_amount(Mod *s,u32 h,u32 key){
 for(u32 b=0;b<5;b++){if(!(s->sources>>b&1))continue;int a,f;if(route(h,key,src_id[b],&a,&f)>=0)return a;}
 return 0;
}
static void set_all(Mod *s,u32 h,u32 key,int amount){
 for(u32 b=0;b<5;b++){
  if(!(s->sources>>b&1))continue;int a,f,slot=route(h,key,src_id[b],&a,&f);
  if(slot>=0){if(amount)post_route(h,key,src_id[b],(u32)slot,amount);else post_route(h,key,0,(u32)slot,0);}
  else if(amount&&f>=0)post_route(h,key,src_id[b],(u32)f,amount);
 }
 FN(0x0813130c,void(*)(void*))(MODEL);
}
static void *slot_widget(void *v,u32 i){return (u8*)v+0x70+i*0x468;}
static void depth_text(char *t,int a){
 u32 n=0,p=(u32)(a<0?-a:a);p=(p+5)/10;if(a>0)t[n++]='+';else if(a<0&&p)t[n++]='-';
 if(p>=100)t[n++]=(char)('0'+p/100);if(p>=10)t[n++]=(char)('0'+p/10%10);t[n++]=(char)('0'+p%10);t[n++]='%';t[n]=0;
}
static int range(void *w,int *lo,int *hi){*lo=(int)W(w,0x450);*hi=(int)W(w,0x454);return *hi>*lo;}
static void show(Mod *s,void *v,u32 i,u32 h,u32 key,int amount){
 void *w=slot_widget(v,i);int lo,hi;if(!range(w,&lo,&hi))return;
 int value=lo+(int)(((long long)(amount+1000)*(hi-lo)+1000)/2000);char t[8];depth_text(t,amount);
 FN(0x08171c1c,void(*)(void*,u32,int,u32))(w,key,value,0);FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0x38,i,t);
 s->marked[i]=1;s->key[i]=(u16)key;s->slot_node[i]=h;s->amount[i]=amount;s->shown[i]=value;
}
static void unmark(Mod *s,void *v,u32 i){
 if(!s->marked[i])return;s->marked[i]=0;void *w=slot_widget(v,i);
 FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0x38,i,0);
 u32 h=s->slot_node[i],key=H(w,0x9c);int value=0;
 if(key==s->key[i]&&FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&h,key,&value))FN(0x08171c1c,void(*)(void*,u32,int,u32))(w,key,value,0);
}
static u32 selected_tile(void *v){return B(v,W(v,0x2434)+0x10238u);}
static void frame(void *v,u32 tile,u32 colour,u32 width){
 u8 *r=(u8*)v+0x2734+tile*0x40;if(W(r,0)==colour&&W(r,4)==width)return;
 W(r,0)=colour;W(r,4)=width;if(B(r,8))B(r,10)=1;else B(r,9)=1;
}
/* Mod tiles: orange outline when selected as a source; otherwise as native
 * 0815F0B6 draws them (white/2 selected tile, grey/1 others). */
static void frames(Mod *s,void *v){
 u32 sel=selected_tile(v);
 for(u32 b=0;b<5;b++){u32 t=src_tile[b];
  if(s->on&&(s->sources>>b&1))frame(v,t,ORANGE,3);else if(s->painted)frame(v,t,t==sel?0xf2u:0xf3u,t==sel?2u:1u);}
 s->painted=s->on&&s->sources;
}
/* P17 (owner: "I need to see whether a modulation target is blocked ... the
 * actual value but with a * behind it"). Outside mod mode, an encoder whose
 * parameter has a Mod Matrix route shows its native value text plus "*".
 * Clearing the slot override (08170656 with 0) makes the native code format
 * the value again (label +D9); it is re-read whenever the value changes. */
/* P26 (owner: "instead of just the * ... little symbols for the modulation
 * sources and the automation lanes"): tiny tags per active route, in slot
 * order: E1 E2 (envelopes, ids 1/2), L1 L2 (LFOs 4/5), S (Mod Seq 8), A-D
 * (automation lanes 9-12, which motion recording also uses), + (other). */
static u32 routed(u32 h,u32 key,char *tags){
 u32 n=0,k=0;tags[0]=0;
 for(u32 slot=0;slot<3;slot++){u32 out[3]={0,0,0};if(!FN(0x08131244,u32(*)(void*,u32*,u32,u32,u32*))(MODEL,&h,key,slot,out)||!(out[1]&0xffffu)||!out[0])continue;
  u32 id=out[1]&0xffffu;const char *t=id==1?"E1":id==2?"E2":id==4?"L1":id==5?"L2":id==8?"S":id==9?"A":id==10?"B":id==11?"C":id==12?"D":"+";
  if(k&&k<10)tags[k++]=' ';while(*t&&k<10)tags[k++]=*t++;tags[k]=0;n++;}
 return n;
}
static void star(Mod *s,void *v,u32 i,const char *tags){
 void *w=slot_widget(v,i);u32 key=H(w,0x9c);int val=(int)W(w,0xa0);
 if(!tags||!tags[0]){if(s->star[i]){s->star[i]=0;FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0x38,i,0);}return;}
 u32 sig=0;for(u32 j=0;tags[j];j++)sig=sig*31u+(u8)tags[j];
 if(s->star[i]&&s->star_key[i]==key&&s->star_val[i]==val&&s->star_sig[i]==sig)return;s->star_sig[i]=sig;
 FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0x38,i,0); /* native text again */
 char t[32];const char *n=(const char*)w+0xd9;u32 k=0;while(n[k]&&k<16){t[k]=n[k];k++;}t[k++]=' ';for(u32 j=0;tags[j]&&k<30;j++)t[k++]=tags[j];t[k]=0;
 FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0x38,i,t);
 s->star[i]=1;s->star_key[i]=(u16)key;s->star_val[i]=val;
}
static void encoders(Mod *s,void *v){
 u32 track=W(v,0x2430),tile=selected_tile(v),type=0,idx=0;
 if(s->track!=track||s->tile!=tile){s->tile=tile;s->node=tile_node(tile,type_of(track),&type,&idx)?child(track,type,idx):0;}
 u32 node=s->node,nt=0,ni=0;if(node)kind(track,node,&nt,&ni);
 for(u32 i=0;i<8;i++){
  u32 key=H(slot_widget(v,i),0x9c);
  int want=s->on&&s->sources&&node&&key&&dest_ok(nt,ni,key);
  if(!want){unmark(s,v,i);char tags[12];tags[0]=0;if(node&&key&&!(s->on&&s->sources)&&dest_ok(nt,ni,key))routed(node,key,tags);star(s,v,i,tags);continue;}
  if(s->star[i])s->star[i]=0;
  int a=shown_amount(s,node,key);
  if(!s->marked[i]||s->key[i]!=key||s->slot_node[i]!=node||s->amount[i]!=a||(int)W(slot_widget(v,i),0xa0)!=s->shown[i])show(s,v,i,node,key,a);
 }
}
static void off(Mod *s,void *v){s->on=0;s->sources=0;if(v){frames(s,v);for(u32 i=0;i<8;i++)unmark(s,v,i);}}
/* P11 (owner: MOD and MATRIX never appeared on 1.6P10). The P8 header waited
 * for the view's vtable entry [0], assumed to be its per-frame tick; on the
 * device it evidently isn't called per frame, so the buttons never showed.
 * Now the header is driven by what is certain: the synth page's own header
 * template (tab ids EE/EF) and a Wavetable/Granular current track; the view
 * is remembered from any event it gets (the MOD press itself is one), and the
 * per-frame work runs from the header tick (seq_toolbar, every UI tick). */
static void periodic(Mod *s,void *v){
 u32 track=W(v,0x2430);
 if(s->on&&(track!=s->track||!synth(track)))off(s,v); /* owner: switching tracks turns mod mode off */
 extern int macro_overlay(void);
 frames(s,v);if(!macro_overlay())encoders(s,v);s->track=track; /* P27: the macro strip owns the encoder texts */
}
static void adopt(Mod *s,void *v){if(s->view!=(u32)v){if(s->view)off(s,(void*)s->view);s->view=(u32)v;}s->seen=TICK;}
__attribute__((used,retain)) void mod_view_tick(void *v,void *a){
 FN(SYNTH_TICK,void(*)(void*,void*))(v,a);
 Mod *s=mod(1);if(!s)return;adopt(s,v);periodic(s,v);
}
static int modulate(Mod *s,void *v,void *e){
 u32 key=W(e,8)&0xffffu,track=W(v,0x2430);int i=-1;
 for(u32 k=0;k<8;k++)if(s->marked[k]&&s->key[k]==key){i=(int)k;break;}
 u32 h=W(e,4)?W(e,4):i>=0?s->slot_node[i]:0,type,idx;
 if(!h||!kind(track,h,&type,&idx)||!dest_ok(type,idx,key))return 0;
 if(i<0||s->slot_node[i]!=h){for(u32 k=0;k<8;k++)if(H(slot_widget(v,k),0x9c)==key){show(s,v,k,h,key,shown_amount(s,h,key));break;}return 1;}
 void *w=slot_widget(v,(u32)i);int lo,hi;if(!range(w,&lo,&hi))return 1;
 int delta=(int)W(e,12)-s->shown[i];if(!delta)return 1;
 int step=(int)(((long long)delta*2000)/(hi-lo));if(step>-10&&step<10)step=delta>0?10:-10;
 int a=s->amount[i]+step;if(a>1000)a=1000;if(a<-1000)a=-1000;
 set_all(s,h,key,a);show(s,v,(u32)i,h,key,shown_amount(s,h,key));return 1;
}
__attribute__((used,retain)) int mod_view_event(void *v,void *e){
 u32 code=H(e,0);Mod *s=mod(1);if(s)adopt(s,v);
 if(code==MATRIX_ACTION){H(e,0)=NATIVE_MATRIX;return FN(SYNTH_EVENT,int(*)(void*,void*))(v,e);} /* as the burger menu's Modulation */
 if(code==MOD_ACTION){
  s=mod(1);if(!s)return 0;u32 track=W(v,0x2430);
  if(s->on)off(s,v);else if(synth(track)){s->on=1;s->sources=0;s->track=track;}
  frames(s,v);encoders(s,v);return 0;
 }
 if(s&&s->on&&s->view==(u32)v){
  if(code==0x79||code==0x7a||code==0x7b){int b=source_bit(W(e,8));if(b>=0){if(code==0x79)s->sources^=1u<<b;frames(s,v);encoders(s,v);return 0;}}
  if(code==0xcf&&s->sources&&modulate(s,v,e))return 0;
 }
 return FN(SYNTH_EVENT,int(*)(void*,void*))(v,e);
}
/* Header: ... [tabs moved one left] [MOD] [MATRIX] | counter. */
#define REC(p,i) ((u8*)(p)+0x74u+(u32)(i)*48u)
static u32 rid(const u8 *r){return (u32)r[44]|((u32)r[45]<<8);}
static int empty(const u8 *r){return !rid(r)&&!r[0]&&!r[0x22];}
static int put(u8 *d,u32 id,const char *label,int lit){
 int change=rid(d)!=id||d[0x20]||d[0x22]||d[0x21]!=(lit?1:0);
 if(rid(d)!=id)zero(d,48);
 u32 n=0;do{if(d[n]!=(u8)label[n])change=1;d[n]=(u8)label[n];}while(label[n++]&&n<31);d[31]=0;
 d[0x20]=0;d[0x22]=0;d[0x21]=lit?1:0;d[44]=(u8)id;d[45]=(u8)(id>>8);return change;
}
__attribute__((used,retain)) int mod_toolbar(void *model,void *out){
 (void)model;u8 *m=REC(out,4),*x=REC(out,5);
 int page=(rid(REC(out,3))==0xeeu&&rid(m)==0xefu)||(rid(m)==MOD_ACTION&&rid(REC(out,3))==0xefu);
 u32 t=0;if(!page||!FN(0x08133cfc,int(*)(void*,void*))(MODEL,&t)||!synth(t))return 0;
 Mod *s=mod(1);if(!s)return 0;
 if(s->view&&W((void*)s->view,0x2430)==t)periodic(s,(void*)s->view);else if(s->on){s->on=0;s->sources=0;}
 if(rid(m)!=MOD_ACTION){
  if(empty(m))return 0;
  if(!empty(x)&&rid(x)!=MATRIX_ACTION)return 0;
  if(!empty(m)){
   /* Only the synth page's own header: tabs ... Grain/WT 1 (EE), 2 (EF). */
   if(rid(REC(out,3))!=0xeeu||rid(m)!=0xefu||!empty(REC(out,1)))return 0;
   for(u32 i=1;i<4;i++){u8 *d=REC(out,i),*f=REC(out,i+1);for(u32 j=0;j<48;j++)d[j]=f[j];}
   zero(m,48);
  }
 }
 char label[32];const char *title="MOD";
 if(s->on){
  static const char *const names[5]={"ENV1","ENV2","LFO1","LFO2","SEQ"};
  u32 count=0;for(u32 b=0;b<5;b++)count+=(s->sources>>b)&1;
  u32 n=0;const char *prefix=s->sources?"MOD ":"MOD: SELECT";
  while(prefix[n]){label[n]=prefix[n];n++;}
  if(s->sources)for(u32 b=0;b<5;b++)if(s->sources>>b&1){if(n>4&&n<30)label[n++]='+';const char *t=names[b];while(*t&&n<30)label[n++]=*t++;}
  if(count>2){label[0]='M';label[1]='O';label[2]='D';label[3]=' ';label[4]=(char)('0'+count);const char *tail=" SOURCES";n=5;while(*tail)label[n++]=*tail++;}
  label[n]=0;title=label;
 }
 int change=put(m,MOD_ACTION,title,s->on!=0);
 change|=put(x,MATRIX_ACTION,"MATRIX",0);return change;
}

void **melodic_lock_state_slot(void){Mod *s=mod(1);return s?&s->melodic_locks:0;}
