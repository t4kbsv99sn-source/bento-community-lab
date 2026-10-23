/* CH8 Bars encoder (owner): clip length in bars, 1 2 4 ... 256. Turning it sets
 * the native Step Count (property 62) through the piano view's own encoder
 * path; Step Len (property 60) decides the steps per bar. The value shows the
 * nearest bar count below, with "+" or "-" when the clip is not exactly that.
 * Step Len table 081A01F4 is in sixteenths: x960 gives native ticks per step
 * (stored Step Len 6 = 1/16 = 960 ticks). A bar is 15360 ticks. (CH8 used 3840,
 * a factor of 4 off: owner saw 4 bars counted as 1.) The piano grid uses the
 * same ticks per step while Snap Mode, property 61, is on.
 * Registry key 177 was empty in the stock registry; preflight like other keys. */
#include "fx_shared.h"
#define BARS_KEY 0x177u
static const char bars_title_text[]="Bars";
static const char *const names[9]={"1","2","4","8","16","32","64","128","256"};
static const char *const plus[9]={"1+","2+","4+","8+","16+","32+","64+","128+","256+"};
static const char *const minus[1]={"1-"};
static const u16 unit_q[15]={30720,15360,7680,3840,1920,1280,960,640,480,320,240,160,120,80,60};
const char *bars_title(void){return bars_title_text;}
const char *const *bars_names(void){return names;}
#define BAR 15360u
u32 step_unit(void *v){u32 i=W(v,0x11cd14);return i<15?unit_q[i]:960u;} /* ticks per step */ /* units per step */
/* Index of the largest listed bar count not above the clip; rel = +1/-1 when not exact. */
u32 bars_index(void *v,int *rel){
 u32 t=W(v,0x11cd18)*step_unit(v),i=0;for(u32 k=0;k<9;k++)if(t>=(BAR<<k))i=k;
 *rel=t==(BAR<<i)?0:t>(BAR<<i)?1:-1;return i;
}
const char *bars_text(void *v){int rel;u32 i=bars_index(v,&rel);return rel>0?plus[i]:rel<0?minus[0]:names[i];}
int bars_registry(void){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;void *d=(void*)(r+BARS_KEY*32);
 if(H(d,0)&&W(d,4)!=(u32)bars_title_text)return 0;
 for(u32 j=0;j<32;j++)B(d,j)=0;H(d,0)=BARS_KEY;B(d,2)=7;W(d,4)=(u32)bars_title_text;W(d,8)=(u32)names;W(d,12)=9;W(d,16)=0;W(d,20)=8;return 1;
}
/* Set the clip to 1<<index bars through the native Step Count encoder event. */
void bars_set(void *v,int index){
 u32 i=index<0?0:index>8?8:(u32)index,steps=(BAR<<i)/step_unit(v);if(!steps)steps=1;if(steps>256)steps=256;
 u32 e[5]={0xcf,0,0x62,steps,0};FN(0x0815a598,int(*)(void*,void*))(v,e);
}
/* Bind one encoder slot of the piano bar to Bars (after the native header). */
void bars_bind(void *v,u32 slot){
 if(slot>7||!bars_registry())return;int rel;u32 value=bars_index(v,&rel);void *bar=(u8*)v+0x55f0,*s=(u8*)bar+0x38+slot*0x468;
 H(v,0x11bcc0+slot*2)=BARS_KEY;W(v,0x11bcd0+slot*4)=value;W(v,0x11bca0+slot*4)=W(v,0x11cd00);
 FN(0x08170656,void(*)(void*,u32,const char*))(bar,slot,0);FN(0x08171c1c,void(*)(void*,u32,int,u32))(s,BARS_KEY,(int)value,1);
 FN(0x0817e85e,void(*)(void*,const char*))((u8*)s+0x3c8,bars_title_text);
 if(rel)FN(0x08170656,void(*)(void*,u32,const char*))(bar,slot,bars_text(v));
}
/* Sequence tab (view +125DAC == 1): Bars goes right of Step Count (slot 5). */
void bars_header(void *v){if(B(v,0x125dac)==1&&!H(v,0x11bcc0+4*2))bars_bind(v,4);}
int bars_event(void *v,void *e){
 if(H(e,0)!=0xcf||W(e,8)!=BARS_KEY)return 0;bars_set(v,(int)W(e,12));FN(0x081599bc,void(*)(void*))(v);return 1;
}
