/* CH8 Bars encoder (owner): clip length in whole bars. Turning it sets the
 * native Step Count (property 62) through the piano view's own encoder path;
 * Step Len (property 60) decides the steps per bar. The value shows the bar
 * count at or below the clip, with "+" or "-" when the clip is not exactly that.
 *
 * P10 (owner: "set to one bar it's actually four bars"): Step Len is an index
 * into table 081A01F4, which holds the step length in quarter notes; the
 * firmware's own names for it (descriptor 60) are 8 bars, 4 bars, 2 bars,
 * 1 bar, 1/2, 1/2T, 1/4, 1/4T, 1/8, 1/8T, 1/16, 1/16T, 1/32, 1/32T, 1/64, so
 * 1/16 is index 10 (0.25 quarter). unit_q = quarters x 960, so a bar (4
 * quarters) is 3840 of these units: 16 steps at 1/16. CH8 had this right;
 * CH10 multiplied the bar by 4 on a wrong reading of the table, which made
 * "1 bar" four bars. Also (owner: "not the right resolution") the encoder now
 * steps in whole bars, 1, 2, 3 ... up to what 256 steps allow (64 at most),
 * instead of 1, 2, 4, 8 ...
 * Registry key 177 was empty in the stock registry; preflight like other keys. */
#include "fx_shared.h"
#define BARS_KEY 0x177u
#define BAR 3840u
#define MAX_BARS 64u
static const char bars_title_text[]="Bars";
static const char *const names[MAX_BARS]={"1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37","38","39","40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58","59","60","61","62","63","64"};
static const char *const plus[MAX_BARS]={"1+","2+","3+","4+","5+","6+","7+","8+","9+","10+","11+","12+","13+","14+","15+","16+","17+","18+","19+","20+","21+","22+","23+","24+","25+","26+","27+","28+","29+","30+","31+","32+","33+","34+","35+","36+","37+","38+","39+","40+","41+","42+","43+","44+","45+","46+","47+","48+","49+","50+","51+","52+","53+","54+","55+","56+","57+","58+","59+","60+","61+","62+","63+","64+"};
static const char *const minus[1]={"1-"};
static const u16 unit_q[15]={30720,15360,7680,3840,1920,1280,960,640,480,320,240,160,120,80,60};
const char *bars_title(void){return bars_title_text;}
const char *const *bars_names(void){return names;}
u32 step_unit(void *v){u32 i=W(v,0x11cd14);return i<15?unit_q[i]:240u;} /* Raw Step Len table; the lane renderer also uses this. */
static u32 duration_unit(void *v){return W(v,0x11cd10)?960u:step_unit(v);} /* Native 081599BC duration path. */
static u32 max_bars(void *v){u32 m=256u*duration_unit(v)/BAR;return m<1?1:m>MAX_BARS?MAX_BARS:m;}
unsigned bars_count(void *v){return max_bars(v);}
/* Index (bars - 1) of the largest whole bar count not above the clip; rel = +1/-1 when not exact. */
u32 bars_index(void *v,int *rel){
 u32 t=W(v,0x11cd18)*duration_unit(v),b=t/BAR,m=max_bars(v);
 if(!b){*rel=-1;return 0;}if(b>m)b=m;
 *rel=t==b*BAR?0:t>b*BAR?1:-1;return b-1;
}
const char *bars_text(void *v){int rel;u32 i=bars_index(v,&rel);return rel>0?plus[i]:rel<0?minus[0]:names[i];}
int bars_registry(void *v){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;void *d=(void*)(r+BARS_KEY*32);
 if(H(d,0)&&W(d,4)!=(u32)bars_title_text)return 0;u32 m=v?max_bars(v):MAX_BARS;
 for(u32 j=0;j<32;j++)B(d,j)=0;H(d,0)=BARS_KEY;B(d,2)=7;W(d,4)=(u32)bars_title_text;W(d,8)=(u32)names;W(d,12)=m;W(d,16)=0;W(d,20)=m-1;return 1;
}
/* Set the clip to index+1 whole bars through the native Step Count encoder event. */
void bars_set(void *v,int index){
 u32 m=max_bars(v),bars=index<0?1:(u32)index+1>m?m:(u32)index+1,steps=bars*BAR/duration_unit(v);if(!steps)steps=1;if(steps>256)steps=256;
 u32 e[5]={0xcf,0,0x62,steps,0};FN(0x0815a598,int(*)(void*,void*))(v,e);
}
/* Bind one encoder slot of the piano bar to Bars (after the native header). */
void bars_bind(void *v,u32 slot){
 if(slot>7||!bars_registry(v))return;int rel;u32 value=bars_index(v,&rel);void *bar=(u8*)v+0x55f0,*s=(u8*)bar+0x38+slot*0x468;
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
