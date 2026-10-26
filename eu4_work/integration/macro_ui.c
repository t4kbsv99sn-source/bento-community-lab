/* P27 performance macros (M4). Owner decisions: docs/releases/p27/PLAN.md.
 *
 * Eight macros, each with up to eight targets (any parameter that is on an
 * encoder somewhere). A macro sets its targets directly, like turning their
 * knobs (model event CF {CF, node, key, value}), scaled from the value the
 * target had when it was mapped (macro 0) to where it was turned (macro 127).
 *
 * Native facts (stock 1.6.1, see docs/releases/p27/DESIGN.md):
 *  - Encoder strip = widget class vtable 081B2838 ("bar"); its eight slots are
 *    children at bar+38+468*i, parent pointer +2C, hidden flag +30. Its touch
 *    slots [4..6] are empty stubs and [7] ("takes touches") returns 0, so no
 *    native code reacts to touches on the strip. P27 makes [7] return 1 and
 *    handles down/move/up here.
 *  - Every encoder turn reaches 08171E44(slot, delta) through K15's
 *    kick_ui_increment (delta returned there). Delta 0 changes nothing.
 *  - Slot: +34 node handle, +9C key, +A0 last value, +450/+454 range,
 *    name label widget +3C8 (text +3F9, setter 0817E85E; +A8/+D9 is the value label), value text override
 *    08170656(bar, i, text) (0 = native text).
 *  - Hit test 0816FA10 style: vtable +28 (obj, point, &out); children +18,
 *    next sibling +20; vtable +10/+18 = touch down/up (obj, point, id). */
#include "fx_shared.h"
#define BAR_VT 0x081b2838u
#define MACRO_MAGIC 0x4f52434du
#define SWIPE 70
#define SHIFT_HELD() (W((void*)0x24048d68u,0)!=0)
typedef struct {u8 track,c1,c2,used;u16 key,pad;int lo,hi,min,max;u32 handle;} Target;
typedef struct {
 u32 magic,overlay,bar,seen_page,armed; /* armed = macro index + 1 */
 u8 value[8],count[8];Target t[8][8];
 char name[8][12];
 char backup[8][32];u32 backup_bar;
 int down,swiped,x0,y0,applying; /* touch on the strip */
 u32 pending_slot; /* last slot turned while armed (range, name) */
 u32 project,loaded;int frac[8];
 char hex[3000];
} Macro;
void **macro_state_slot(void);
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static Macro *state(int create){
 void **slot=macro_state_slot();if(!slot)return 0;Macro *s=*slot;
 if(s)return s->magic==MACRO_MAGIC?s:0;if(!create)return 0;
 u32 cursor=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),bytes=(sizeof(Macro)+31u)&~31u;
 if(cursor<0xc0000000u||end>0xc8000000u||cursor>end||end-cursor<bytes+32)return 0;
 s=FN(0x08104c08,void*(*)(u32))(bytes);if((u32)s!=cursor)return 0;zero(s,sizeof(*s));s->magic=MACRO_MAGIC;*slot=s;return s;
}
static int is_bar(u32 b){return b>=0x20000000u&&b<0xc8000000u&&W((void*)b,0)==BAR_VT;}
static void *slot_of(u32 bar,u32 i){return (u8*)bar+0x38+i*0x468;}
static int slot_index(void *slot,u32 *bar){
 u32 b=W(slot,0x2c);if(!is_bar(b))return -1;u32 off=(u32)slot-b-0x38;if(off%0x468||off/0x468>7)return -1;*bar=b;return (int)(off/0x468);
}
static int get(u32 h,u32 key,int *out){return h&&FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,&h,key,out);}
static void post(u32 h,u32 key,int value){u32 ev[5]={0xcf,h,key,(u32)value,0};FN(0x081403ec,int(*)(void*,void*))(MODEL,ev);}
static u32 settings(void){u32 h=0;return FN(0x08133e54,int(*)(void*,u32*))(MODEL,&h)?h:0;}
static u32 track_handle(u32 t){u32 h=0;return FN(0x08133960,int(*)(void*,u32,u32*))(MODEL,t,&h)?h:0;}
static u32 child_handle(u32 owner,u32 j){u32 c=0;return owner&&FN(0x0813391a,int(*)(void*,void*,u32,void*))(MODEL,&owner,j,&c)?c:0;}
/* Targets are kept as a path that survives project reload: track, child,
 * grandchild (0xFF = none); track 0xFE = project settings node. */
static int locate(u32 h,Target *t){
 if(h==settings()){t->track=0xfe;t->c1=t->c2=0xff;return 1;}
 for(u32 i=0;i<16;i++){u32 tr=track_handle(i);if(!tr)continue;
  if(tr==h){t->track=(u8)i;t->c1=t->c2=0xff;return 1;}
  for(u32 j=0;j<64;j++){u32 c=child_handle(tr,j);if(!c)break;
   if(c==h){t->track=(u8)i;t->c1=(u8)j;t->c2=0xff;return 1;}
   for(u32 k=0;k<64;k++){u32 g=child_handle(c,k);if(!g)break;if(g==h){t->track=(u8)i;t->c1=(u8)j;t->c2=(u8)k;return 1;}}
  }
 }
 return 0;
}
static u32 resolve(Target *t){
 u32 h=t->track==0xfe?settings():t->track<16?track_handle(t->track):0;
 if(h&&t->c1!=0xff)h=child_handle(h,t->c1);if(h&&t->c2!=0xff)h=child_handle(h,t->c2);
 return h;
}
static void apply(Macro *s,u32 m){
 int any=0;s->applying=1;
 for(u32 i=0;i<s->count[m];i++){Target *t=&s->t[m][i];u32 h=resolve(t);if(!h)continue;
  int v=t->min+(int)(((long long)(t->max-t->min)*s->value[m]+(t->max>t->min?63:-63))/127);
  if(v<t->lo)v=t->lo;if(v>t->hi)v=t->hi;post(h,t->key,v);any=1;}
 if(any)FN(0x0813130c,void(*)(void*))(MODEL);
 s->applying=0;
}
/* While armed, every parameter change reaching the model (CF {CF, node, key,
 * value}: encoders on any page, already with their real node) maps it: the
 * value before the change is the macro's 0, the latest value its 127. The last
 * turned slot with the same key gives the parameter range and name. Turning a
 * target back to where it started unmaps it when the macro is disarmed. */
static void settle(Macro *s){
 if(!s->armed)return;u32 m=s->armed-1;
 for(u32 i=0;i<s->count[m];i++){Target *t=&s->t[m][i];if(t->max==t->min){for(u32 j=i;j+1<s->count[m];j++)s->t[m][j]=s->t[m][j+1];s->count[m]--;i--;}}
}
static void capture(Macro *s,u32 h,u32 key,int value){
 u32 m=s->armed-1;if(!h||!key)return;
 Target *t=0;for(u32 i=0;i<s->count[m];i++){Target *x=&s->t[m][i];if(x->key==key&&resolve(x)==h){t=x;break;}}
 if(!t){if(s->count[m]>=8)return;Target n;zero(&n,sizeof n);if(!locate(h,&n))return;
  int v;if(!get(h,key,&v))v=value;n.key=(u16)key;n.min=v;n.lo=-0x40000000;n.hi=0x40000000;
  void *slot=(void*)s->pending_slot;
  if(slot&&H(slot,0x9c)==key&&(int)W(slot,0x454)>(int)W(slot,0x450)){n.lo=(int)W(slot,0x450);n.hi=(int)W(slot,0x454);
   if(!s->count[m]){const char *l=(const char*)slot+0x3f9;u32 k=0;while(l[k]&&k<11){s->name[m][k]=l[k];k++;}s->name[m][k]=0;}}
  t=&s->t[m][s->count[m]++];*t=n;}
 t->max=value;
}
/* ---- strip display ---- */
static void number(char *p,u32 v){u32 n=0;if(v>=100)p[n++]=(char)('0'+v/100);if(v>=10)p[n++]=(char)('0'+v/10%10);p[n++]=(char)('0'+v%10);p[n]=0;}
static void label(Macro *s,u32 m,char *out){
 if(s->count[m]&&s->name[m][0]){u32 k=0;while(s->name[m][k]){out[k]=s->name[m][k];k++;}out[k]=0;return;}
 const char *d="MACRO ";u32 k=0;while(d[k]){out[k]=d[k];k++;}out[k++]=(char)('1'+m);out[k]=0;
}
static int same(const char *a,const char *b){u32 i=0;while(a[i]&&a[i]==b[i])i++;return a[i]==b[i];}
static void restore(Macro *s){
 u32 b=s->backup_bar;s->backup_bar=0;if(!is_bar(b))return;
 for(u32 i=0;i<8;i++){void *slot=slot_of(b,i);FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,s->backup[i]);FN(0x08170656,void(*)(void*,u32,const char*))((void*)b,i,0);}
}
static void paint(Macro *s,u32 b){
 if(!is_bar(b))return;
 if(s->backup_bar!=b){restore(s);for(u32 i=0;i<8;i++){const char *l=(const char*)slot_of(b,i)+0x3f9;u32 k=0;while(l[k]&&k<31){s->backup[i][k]=l[k];k++;}s->backup[i][k]=0;}s->backup_bar=b;}
 for(u32 i=0;i<8;i++){
  void *slot=slot_of(b,i);char name[16],text[8];label(s,i,name);
  const char *now=(const char*)slot+0x3f9;
  if(!same(now,name)){u32 k=0;while(now[k]&&k<31){s->backup[i][k]=now[k];k++;}s->backup[i][k]=0; /* native relabelled it meanwhile */
   FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,name);}
  if(s->armed==i+1){text[0]='A';text[1]='R';text[2]='M';text[3]=0;}else number(text,s->value[i]);
  if(!same((const char*)slot+0x2c8,text))FN(0x08170656,void(*)(void*,u32,const char*))((void*)b,i,text);
 }
}
static void open(Macro *s,u32 b){settle(s);s->overlay=1;s->bar=b;paint(s,b);}
static void close(Macro *s){s->overlay=0;restore(s);}
/* The visible strip after a page change: walk the widget tree from the root
 * of the header (top ancestor) and take the first visible strip. */
static u32 find_bar(void){
 u32 r=0x30034d48u;for(u32 i=0;i<16&&W((void*)r,0x2c);i++)r=W((void*)r,0x2c);
 u32 stack[24],n=0,seen=0;stack[n++]=r;
 while(n&&seen<3000){u32 o=stack[--n];seen++;if(o<0x20000000u||o>=0xc8000000u||B((void*)o,0x30))continue;
  if(W((void*)o,0)==BAR_VT)return o;
  u32 c=W((void*)o,0x20);if(c&&n<24)stack[n++]=c; /* sibling */
  c=W((void*)o,0x18);if(c&&n<24)stack[n++]=c;}    /* first child */
 return 0;
}
void macro_project_reset(void);
int macro_overlay(void){Macro *s=state(0);return s&&s->overlay;}
/* Header tick (every UI tick): keep the strip showing macros on whatever
 * page is visible, and show "MACRO n" in the transport readout while armed. */
void macro_periodic(void *out){
 Macro *s=state(0);if(!s)return;
 u32 project=settings(); /* a new project: its macros come from its file, else none */
 if(project!=s->project){if(s->project&&!s->loaded)macro_project_reset();s->project=project;s->loaded=0;}
 if(s->overlay){u32 page=B(MODEL,0x12c);
  if(page!=s->seen_page||!is_bar(s->bar)||B((void*)s->bar,0x30)){s->seen_page=page;u32 b=find_bar();if(b)s->bar=b;}
  paint(s,s->bar);}
 if(s->armed&&out){char *p=(char*)out+0x196;if(!(p[0]=='R'&&p[1]=='E'&&p[2]=='C')&&!(p[0]=='N'&&p[1]=='O')){const char *w="MACRO ";u32 k=0;while(w[k]){p[k]=w[k];k++;}p[k++]=(char)('0'+s->armed);p[k]=0;}}
}
/* From kick_ui_increment: returns 1 when the turn belongs to a macro. */
int macro_model_event(void *event){
 Macro *s=state(0);if(!s||!event||!s->armed||s->overlay||s->applying||H(event,0)!=0xcf)return 0;
 capture(s,W(event,4),W(event,8),(int)W(event,12));return 0;
}
int macro_increment(void *slot,int delta){
 Macro *s=state(0);if(!s||!slot)return 0;
 u32 bar=0;int i=slot_index(slot,&bar);
 if(s->overlay&&i>=0){
  /* Native slots turn their full range in about 160000 raw encoder units
     (08171E44, measured at slow speed); a macro does the same over 0..127. */
  s->bar=bar;settle(s);s->frac[i]+=delta*127;int step=s->frac[i]/160000;s->frac[i]-=step*160000;int v=(int)s->value[i]+step;if(v<0)v=0;if(v>127)v=127;
  if(v!=s->value[i]){s->value[i]=(u8)v;apply(s,(u32)i);}paint(s,bar);return 1;
 }
 if(s->armed&&!s->overlay)s->pending_slot=(u32)slot;
 return 0;
}
/* ---- touches on the strip ---- */
__attribute__((used,retain)) int macro_bar_takes(void *bar){(void)bar;return 1;}
__attribute__((used,retain)) void macro_bar_down(void *bar,void *point,u32 id){
 (void)id;Macro *s=state(1);if(!s||!point)return;s->down=1;s->swiped=0;s->x0=(int)W(point,0);s->y0=(int)W(point,4);
}
__attribute__((used,retain)) void macro_bar_move(void *bar,void *point,u32 id){
 (void)id;Macro *s=state(0);if(!s||!s->down||s->swiped||!point)return;
 int dx=(int)W(point,0)-s->x0,dy=(int)W(point,4)-s->y0;if(dy<0)dy=-dy;
 if(dx<-SWIPE&&dy*2<-dx){s->swiped=1;if(!s->overlay)open(s,(u32)bar);}
 else if(dx>SWIPE&&dy*2<dx){s->swiped=1;if(s->overlay)close(s);}
}
/* A tap: in the macro strip it arms/disarms that macro (PROJ + tap clears
 * it); otherwise it goes to whatever native widget lies under the strip. */
__attribute__((used,retain)) void macro_bar_up(void *bar,void *point,u32 id){
 Macro *s=state(0);if(!s||!s->down)return;s->down=0;if(s->swiped||!point)return;
 int x=(int)W(point,0),dx=x-s->x0,dy=(int)W(point,4)-s->y0;if(dx<0)dx=-dx;if(dy<0)dy=-dy;if(dx>30||dy>30)return;
 if(s->overlay){
  int i=-1;for(u32 k=0;k<8;k++){void *slot=slot_of((u32)bar,k);int sx=(int)W(slot,4),sw=(int)W(slot,12);if(x>=sx&&x<sx+sw){i=(int)k;break;}}
  if(i<0)return;settle(s);
  if(SHIFT_HELD()){s->count[i]=0;s->name[i][0]=0;s->value[i]=0;if(s->armed==(u32)i+1)s->armed=0;}
  else s->armed=s->armed==(u32)i+1?0:(u32)i+1;
  paint(s,(u32)bar);return;
 }
 u32 root=(u32)bar;for(u32 k=0;k<16&&W((void*)root,0x2c);k++)root=W((void*)root,0x2c);
 B(bar,0x30)=1;void *hit=0;FN(W((void*)W((void*)root,0),0x28),int(*)(void*,void*,void**))((void*)root,point,&hit);B(bar,0x30)=0;
 if(hit&&hit!=bar){FN(W((void*)W(hit,0),0x10),void(*)(void*,void*,u32))(hit,point,id);FN(W((void*)W(hit,0),0x18),void(*)(void*,void*,u32))(hit,point,id);}
}
/* ---- project file: one versioned attribute on track 1's params ---- */
static const char hexd[]="0123456789ABCDEF";
static void put8(Macro *s,u32 *n,u32 v){if(*n+2<sizeof(s->hex)){s->hex[*n]=hexd[(v>>4)&15];s->hex[*n+1]=hexd[v&15];*n+=2;}}
static void put32(Macro *s,u32 *n,u32 v){for(u32 i=0;i<4;i++)put8(s,n,v>>(i*8)&255);}
void macro_save(void *object,void *params){
 Macro *s=state(0);if(!s||!object||!params||W(object,0x10)!=track_handle(0))return;settle(s);
 u32 n=0,any=0;put8(s,&n,1);
 for(u32 m=0;m<8;m++){put8(s,&n,s->value[m]);put8(s,&n,s->count[m]);any|=s->count[m];
  for(u32 k=0;k<12;k++)put8(s,&n,(u8)s->name[m][k]);
  for(u32 i=0;i<s->count[m];i++){Target *t=&s->t[m][i];put8(s,&n,t->track);put8(s,&n,t->c1);put8(s,&n,t->c2);put8(s,&n,t->key&255);put8(s,&n,t->key>>8);
   put32(s,&n,(u32)t->lo);put32(s,&n,(u32)t->hi);put32(s,&n,(u32)t->min);put32(s,&n,(u32)t->max);}}
 s->hex[n]=0;if(!any)return;
 void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,"playground_macros_v1");if(a)FN(0x08109582,void(*)(void*,const char*))(a,s->hex);
}
static int nib(char c){return c>='0'&&c<='9'?c-'0':c>='A'&&c<='F'?c-'A'+10:-1;}
static int get8(const char **p){int h=nib((*p)[0]),l=h<0?-1:nib((*p)[1]);if(l<0)return -1;*p+=2;return h*16+l;}
static int get32(const char **p,u32 *v){*v=0;for(u32 i=0;i<4;i++){int b=get8(p);if(b<0)return 0;*v|=(u32)b<<(i*8);}return 1;}
void macro_load(void *node,void *object){
 if(!node||!object)return;void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");if(!params)return;
 void *a=FN(0x08109c64,void*(*)(void*,const char*))(params,"playground_macros_v1");if(!a)return;
 const char *p=FN(0x081094c2,const char*(*)(void*))(a);if(!p||get8(&p)!=1)return;
 Macro *s=state(1);if(!s)return;s->loaded=1;
 Macro *t=s; /* parse into place; on a bad record keep what was read so far */
 for(u32 m=0;m<8;m++){int v=get8(&p),c=get8(&p);if(v<0||c<0||v>127||c>8){t->count[m]=0;return;}t->value[m]=(u8)v;t->count[m]=0;
  for(u32 k=0;k<12;k++){int ch=get8(&p);if(ch<0)return;t->name[m][k]=(char)ch;}t->name[m][11]=0;
  for(int i=0;i<c;i++){Target x;zero(&x,sizeof x);int a1=get8(&p),a2=get8(&p),a3=get8(&p),k1=get8(&p),k2=get8(&p);u32 lo,hi,mn,mx;
   if(a1<0||a2<0||a3<0||k1<0||k2<0||!get32(&p,&lo)||!get32(&p,&hi)||!get32(&p,&mn)||!get32(&p,&mx))return;
   x.track=(u8)a1;x.c1=(u8)a2;x.c2=(u8)a3;x.key=(u16)(k1|k2<<8);x.lo=(int)lo;x.hi=(int)hi;x.min=(int)mn;x.max=(int)mx;t->t[m][t->count[m]++]=x;}}
}
/* A new project: no macros until its file says otherwise (load runs later). */
void macro_project_reset(void){Macro *s=state(0);if(!s)return;if(s->overlay)close(s);s->armed=0;for(u32 m=0;m<8;m++){s->count[m]=0;s->value[m]=0;s->name[m][0]=0;}}
