/* CH6/CH7: Euclidean lanes in the native piano roll (owner's Option B).
 *
 * Each active lane is drawn once at its true length: the cells after its last
 * step are greyed, and the lane's current step gets its own playhead box, so
 * lanes with different lengths can be read against the clip.
 *
 * The piano grid is the widget at piano view +38 (class vtable 081B2BCC):
 *   +3C visible columns, +4F8 first column, +564+4i column x (i = 0..visible),
 *   +A20 ticks per column (960 per sixteenth), +44 visible rows, +4F4 first row,
 *   +4FC+4k row y (k = 0..rows), +A10 pad-row mapping (row = 081751EC(pad)),
 *   +34 note widgets (0x48 each: +4 rect, +30 hidden, +31 used, +32/+33 state,
 *   +46 colour), +4F0/+4F1 full/partial repaint requests read by its tick.
 * Geometry always comes from the native note layout 0817566A (CH7: the device
 * folds one-shot rows to used pads, +5276, so row != pad+8 there).
 * Paint gets ctx {full, partial, surface}. Notes are painted inside the grid's
 * own paint, so the overlay drawn after it lies on top of them. A partial paint
 * restores the old box cell (background and notes) before the native playhead
 * is drawn, then draws the new boxes.
 */
#include "live_ui.h"
#define PIANO_VTABLE 0x0819e7b0u
#define NATIVE_TICK 0x081773a4u
#define NATIVE_PAINT 0x08176d74u
#define FILL(r,c,s) FN(0x08166ef6,void(*)(const int*,u32,u32))(r,c,s)
#define OUTLINE(r,c,s) FN(0x08166e9e,void(*)(const int*,u32,u32))(r,c,s)
#define LANE_MAGIC 0x454e414cu
#define BG 0xf1u
#define BOX 0xf2u
#define GREY 0xf3u
u32 step_unit(void*);
int live_lanes(u32 seq,u32 owner,EuPad *pads,u8 *pitch,u32 *mel,u32 *step);
void **lane_state_slot(void);
typedef struct {u32 magic,grid,sign,shown,unit;int k[16],s[16];} Lanes;
typedef struct {u32 on,sign,unit;int k[16],s[16],end[16];} Want;
static Lanes *lanes(int create){
 void **slot=lane_state_slot();if(!slot)return 0;Lanes *l=(Lanes*)*slot;
 if(l)return l->magic==LANE_MAGIC?l:0;if(!create)return 0;
 u32 p=W((void*)0x3000004cu,0),end=W((void*)0x30000048u,0),n=(sizeof(Lanes)+31u)&~31u;
 if(p<0xc0000000u||end>0xc8000000u||p>end||end-p<n+32u)return 0;
 if(FN(0x08104c08,u32(*)(u32))(n)!=p)return 0;
 for(u32 i=0;i<n;i++)((u8*)p)[i]=0;l=(Lanes*)p;l->magic=LANE_MAGIC;*slot=l;return l;
}
/* Rectangle the native layout gives a note (time, length in ticks, row value):
   0817566A handles zoom, scroll and the "used rows only" fold (grid +5276, rows
   listed at +5278) exactly as the notes are drawn. Rows not on screen get h<=3. */
static int rect(u8 *g,u32 t,u32 d,u32 row,int *r){
 FN(0x0817566a,void(*)(int*,void*,u32,u32,u32))(r,g,t,d,row);return r[2]>0&&r[3]>3;
}
/* Lanes of the sequence the piano view shows: native row values and current steps. */
static int want(u8 *g,Want *w){
 u8 *v=g-0x38;w->on=0;w->sign=0;if(W(v,0)!=PIANO_VTABLE||B(g,0x30))return 0;
 EuPad pads[16];u8 pitch[16];u32 mel=0,step=0;
 u32 unit=W(v,0x11cd10)?step_unit(v):960u; /* CH8: Snap Mode on = one step is step_unit grid ticks (owner: 3-step lane drew 4x long) */
 w->unit=unit;
 if(!live_lanes(W(v,0x11cd00),W(v,0x11cd08),pads,pitch,&mel,&step))return 0;
 for(u32 i=0;i<16;i++){
  w->k[i]=-1;w->s[i]=-1;w->end[i]=0;EuPad p=pads[i];if(!eu_enabled(p)||!eu_pad_valid(p))continue;
  u32 r=mel?pitch[i]:i;if(B(g,0xa10))r=FN(0x081751ec,u32(*)(void*,u32))(g,r);
  u32 n=eu_length(p);w->k[i]=(int)r;w->end[i]=(int)n;w->s[i]=step==~0u?-1:(int)(step%n);w->on|=1u<<i;
  w->sign=w->sign*31u+r*257u+n;
 }
 w->sign=w->sign*31u+W(g,0x4f8)*7u+W(g,0x4f4)+W(g,0xa20)+unit*13u; /* scroll/zoom changes redraw the grey */
 return w->on!=0;
}
static int cell(u8 *g,int k,int s,u32 unit,int *r){return rect(g,(u32)s*unit,unit,(u32)k,r);}
static void box(u8 *g,int k,int s,u32 unit,u32 surface){
 int r[4];if(!cell(g,k,s,unit,r)||r[2]<3)return;OUTLINE(r,BOX,surface);
 r[0]++;r[1]++;r[2]-=2;r[3]-=2;OUTLINE(r,BG,surface);
}
/* Put back what a box covered: background, then the parts of notes inside. */
static void restore(u8 *g,int k,int s,u32 unit,u32 surface){
 int r[4];if(!cell(g,k,s,unit,r))return;FILL(r,BG,surface);
 u8 *notes=(u8*)W(g,0x34);if(!notes)return;
 for(u32 i=0;i<0x200;i++){
  u8 *n=notes+i*0x48;if(!B(n,0x31)||B(n,0x30))continue;
  int a[4]={(int)W(n,4),(int)W(n,8),(int)W(n,12),(int)W(n,16)};
  int x0=a[0]>r[0]?a[0]:r[0],y0=a[1]>r[1]?a[1]:r[1],x1=a[0]+a[2]<r[0]+r[2]?a[0]+a[2]:r[0]+r[2],y1=a[1]+a[3]<r[1]+r[3]?a[1]+a[3]:r[1]+r[3];
  if(x1<=x0||y1<=y0)continue;int c[4]={x0,y0,x1-x0,y1-y0};
  FILL(c,B(n,0x32)&&!B(n,0x33)?0xf2u:B(n,0x46),surface);
 }
}
__attribute__((used,retain)) void lane_paint(void *grid,void *ctx){
 u8 *g=(u8*)grid;Want w;int have=want(g,&w);Lanes *l=have?lanes(1):lanes(0);
 u32 surface=W(ctx,4),full=B(ctx,0),partial=B(ctx,1);
 if(l&&l->grid!=(u32)g){l->grid=(u32)g;l->shown=0;}
 if(l&&!full&&partial&&l->shown)for(u32 i=0;i<16;i++){
  if(l->k[i]<0||l->s[i]<0)continue;if(have&&w.k[i]==l->k[i]&&w.s[i]==l->s[i])continue;
  restore(g,l->k[i],l->s[i],l->unit?l->unit:960u,surface);
 }
 FN(NATIVE_PAINT,void(*)(void*,void*))(grid,ctx);
 if(!l)return;
 if(!have){l->shown=0;return;}
 if(full){
  u32 end=(W(g,0x4f8)+W(g,0x3c))*W(g,0xa20);
  for(u32 i=0;i<16;i++){
   u32 t=(u32)w.end[i]*w.unit;int r[4];if(w.k[i]<0||t>=end)continue;
   if(rect(g,t,end-t,(u32)w.k[i],r))FILL(r,GREY,surface);
  }
 }
 if(full||partial){
  for(u32 i=0;i<16;i++){l->k[i]=w.k[i];l->s[i]=w.s[i];if(w.k[i]>=0&&w.s[i]>=0)box(g,w.k[i],w.s[i],w.unit,surface);}
  l->sign=w.sign;l->unit=w.unit;l->shown=1;
 }
}
__attribute__((used,retain)) void lane_tick(void *grid,void *flags){
 u8 *g=(u8*)grid;Want w;int have=want(g,&w);Lanes *l=lanes(have);
 if(have&&l){
  if(l->grid!=(u32)g||!l->shown||l->sign!=w.sign)B(g,0x4f0)=1; /* lanes appeared or changed: full repaint */
  else for(u32 i=0;i<16;i++)if(w.k[i]!=l->k[i]||w.s[i]!=l->s[i]){B(g,0x4f1)=1;break;}
 }else if(l&&l->grid==(u32)g&&l->shown)B(g,0x4f0)=1; /* lanes gone: repaint without them */
 FN(NATIVE_TICK,void(*)(void*,void*))(grid,flags);
}
