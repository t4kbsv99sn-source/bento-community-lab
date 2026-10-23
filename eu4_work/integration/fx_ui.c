#include "fx_shared.h"
#include "live_ui.h"
#include "seq_bank.h"
typedef struct {u32 handle;int values[18];} Entry;
typedef struct {u32 magic,active,selected,view,nav,held,serial,pending_count;Entry live[8],pending[8];char titles[3][40];u32 armed,pressed,down_tick,up_tick,last_button;Euclid eu;u32 step_view,eu_mode,draw_pattern,draw_head,draw_pad,draw_seq;} Ui;
#define U ((Ui*)UI_ADDR)
_Static_assert(sizeof(Ui)<=0x5c0,"UI state exceeds reservation");
static const char *const names[19]={"EQ","Low Hz","Low dB","Mid Hz","Mid dB","Mid Q","High Hz","High dB","Compressor","Thresh dB","Ratio","Attack ms","Release ms","Auto Makeup","Makeup dB","Mix %","Soft Clip","Ceiling dB","Track"};
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static void defaults(Entry *e,u32 handle){e->handle=handle;for(u32 i=0;i<18;i++)e->values[i]=fx_default[i];}
static void init(){if(U->magic!=0x33555845u){zero(U,sizeof(*U));for(u32 i=0;i<8;i++)defaults(&U->live[i],0);U->magic=0x33555845u;}}
static void publish(){u32 s=(U->serial+2u)&~1u;if(!s)s=2;MAIL->serial=s|1;__asm__ volatile("dmb" ::: "memory");MAIL->magic=MAIL_MAGIC;for(u32 t=0;t<8;t++){MAIL->handles[t]=U->live[t].handle;for(u32 i=0;i<18;i++)MAIL->values[t][i]=U->live[t].values[i];}__asm__ volatile("dmb" ::: "memory");MAIL->serial=s;U->serial=s;}
static void sync(){
 init();int changed=0;Entry prior[8];for(u32 j=0;j<8;j++)prior[j]=U->live[j];
 for(u32 t=0;t<8;t++){
  u32 h=0;FN(0x08133960,u32(*)(void*,u32,u32*))(MODEL,t,&h);Entry e;defaults(&e,h);
  for(u32 j=0;j<8;j++)if(h&&prior[j].handle==h){e=prior[j];break;}
  for(u32 j=0;j<U->pending_count;j++)if(h&&U->pending[j].handle==h)e=U->pending[j];
  if(U->live[t].handle!=e.handle)changed=1;
  for(u32 i=0;i<18;i++)if(U->live[t].values[i]!=e.values[i])changed=1;
  U->live[t]=e;
 }
 U->pending_count=0;if(changed||!MAIL->serial)publish();
}
static int registry(){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;
 for(u32 i=0;i<19;i++){void *d=(void*)(r+fx_keys[i]*32);if(H(d,0)&&W(d,4)!=(u32)names[i])return 0;}
 for(u32 i=0;i<19;i++){
  void *d=(void*)(r+fx_keys[i]*32);zero(d,32);H(d,0)=fx_keys[i];B(d,2)=(i==0||i==8||i==13||i==16)?6:2;
  W(d,4)=(u32)names[i];W(d,16)=(u32)fx_lo[i];W(d,20)=(u32)fx_hi[i];
 }return 1;
}
static void refresh(){if(U->view)FN(0x08145cf4,void(*)(void*))((void*)U->view);}
static const u16 eu_keys[6]={0x190,0x191,0x192,0x193,0x194,0x195};
static const char *const eu_names[6]={"Pad","Length","Hits","Rotate","Vel Mode","Vel Depth"};
static const char *const vel_names[]={"Flat","Alternate","Hits 3","Hits 4","Grid 4","Rise","Fall","Wave","Humanize","Rnd Accent"};
static int eu_index(u32 key){for(u32 i=0;i<6;i++)if(eu_keys[i]==key)return (int)i;return -1;}
static int eu_registry(){
 u32 r=W((void*)0x30031484u,0);if(!r)return 0;
 for(u32 i=0;i<6;i++){void *d=(void*)(r+eu_keys[i]*32);if(H(d,0)&&W(d,4)!=(u32)eu_names[i])return 0;}
 EuPad p=live_value(&U->eu);u32 len=eu_length(p);int lo[6]={1,1,0,0,0,0},hi[6]={16,256,(int)len,(int)len-1,9,100};
 for(u32 i=0;i<6;i++){void *d=(void*)(r+eu_keys[i]*32);zero(d,32);H(d,0)=eu_keys[i];B(d,2)=i==4?7:2;if(i==4){W(d,8)=(u32)vel_names;W(d,12)=10;}W(d,4)=(u32)eu_names[i];W(d,16)=(u32)lo[i];W(d,20)=(u32)hi[i];}return 1;
}
extern int seq_selection_active(void*);
extern void seq_selection_reset(void*);
static int step_editing(void *v){
 if(seq_selection_active(v))return 1;
 for(u32 i=0;i<32;i++)if(W(v,0x11420+i*4))return 1;
 void *s=(void*)0x24048d80u;return W(s,0)==0x32495042u&&W(s,20)&&W(s,4)==(u32)v&&W(s,8)==W(v,0x113e4)&&W(s,12)==W(v,0x11400);
}
__attribute__((used)) void eu_view_capture(void *v){
 init();U->step_view=(u32)v;eu_capture(&U->eu,v);if(!U->eu.valid)return;
 EuPad p=live_value(&U->eu);u32 n=0;
 if(eu_native(p)&&eu_enabled(p))n=eu_length(p);
 else FN(0x08133614,int(*)(void*,void*,u32,void*))(MODEL,(u8*)v+0x113e4,0x62,&n);
 if(n&&n<=256){W(v,0x113f8)=n;if(W(v,0x113f4)>=n)W(v,0x113f4)=0;}
}
__attribute__((used)) int fx_dispatch(void *m,u32 code,u32 context,u32 index){
 (void)context;init();
 if(code==0xb0&&index==U->held&&U->held){U->held=0;return 1;}
 /* Native HAL_GetTick (081152C0) reads this millisecond counter. A first
    TRACKS press immediately follows K16; only a second short tap is consumed.
    Pad actions, shift, other buttons and a long hold cancel the tap sequence. */
 u32 tick=W((void*)0x3001fe2cu,0);
 if(index!=2 || (code!=0xaf&&code!=0xb0)){
  if(code==0xaf||code==0xb0||code==0xfe){U->armed=0;if(U->pressed)U->pressed=2;}return 0;
 }
 if(W((void*)0x24048d60u,8)){U->armed=0;U->pressed=0;return 0;}
 if(code==0xb0){
  if(U->last_button==index && U->pressed==1 && tick-U->down_tick<=300 && (index!=2||!W((void*)0x24048cc0u,8))){
   U->armed=1;U->up_tick=tick;
  }else U->armed=0;
  U->pressed=0;return 0;
 }
 if(code==0xaf){
  int second=U->armed && U->last_button==index && tick-U->up_tick<=350 && B(m,0x12c)==(index==2?2:0x27);U->armed=0;
  U->pressed=1;U->down_tick=tick;U->last_button=index;
  if(!second)return 0;
  U->pressed=0;
  {if(!registry())return 1;sync();u32 selected=FN(0x0812dc74,u32(*)(void*,u32))((u8*)m+4,0x131);U->selected=selected<8?selected:0;U->active=1;}
  U->held=index;U->nav=1;U->view=0;
  FN(0x081420ec,void(*)(void*,u32,u32,u32,u32))(m,0x1a,0,0,0);U->nav=0;
  return 1;
 }
 return 0;
}
__attribute__((used)) void fx_nav(void *m,u32 page){(void)m;(void)page;init();if(!U->nav){U->active=0;U->view=0;if(page!=0x27){U->eu_mode=0;U->step_view=0;}}}
__attribute__((used)) int fx_header(void *m,void *handle,void *out,u32 mode,u32 caller){
 (void)m;(void)handle;(void)mode;init();
 if(!U->active||(caller&~1u)!=0x08145f22u)return 0;

 if(!registry())return 0;sync();U->view=(u32)out-0x93c4;zero(out,0x54);B(out,0)=3;
 static const char *const suffix[3]={" EQ"," Compressor"," Soft Clip"};
 for(u32 row=0;row<3;row++){
  char *s=U->titles[row];s[0]='T';s[1]='r';s[2]='a';s[3]='c';s[4]='k';s[5]=' ';s[6]='1'+U->selected;u32 n=7;const char *p=suffix[row];while(*p)s[n++]=*p++;s[n]=0;W(out,4+row*4)=(u32)s;
 }
 for(u32 i=0;i<16;i++)H(out,0x14+i*2)=fx_keys[i];
 H(out,0x34)=fx_keys[18];H(out,0x36)=fx_keys[16];H(out,0x38)=fx_keys[17];return 1;
}
__attribute__((used)) int fx_get(void *m,void *handle,u32 key,void *out){
 (void)m;(void)handle;init();if(U->active&&out&&key==0){W(out,0)=0;return 1;}

 int i=key_index(key);if(i<0||!U->active||!out)return 0;
 W(out,0)=i==18?U->selected+1:(u32)U->live[U->selected].values[i];return 1;
}
__attribute__((used)) int fx_event(void *v,void *event){
 init();if(!U->active||U->view!=(u32)v||H(event,0)!=0xcf)return 0;

 int i=key_index(W(event,8));if(i<0)return 0;int value=(int)W(event,12);if(value<fx_lo[i])value=fx_lo[i];if(value>fx_hi[i])value=fx_hi[i];
 if(i==18){U->selected=(u32)value-1;FN(0x0813bc3c,void(*)(void*,u32))(MODEL,U->selected);u32 h=W(v,0x93bc);FN(0x08145efc,void(*)(void*,void*))(v,&h);}
 else {U->live[U->selected].values[i]=value;publish();FN(0x0813130c,void(*)(void*))(MODEL);refresh();}
 return 1;
}
static void attr(void *params,const char *name,u32 value){void *a=FN(0x08109cdc,void*(*)(void*,const char*))(params,name);if(a)FN(0x0810958e,void(*)(void*,u32))(a,value);}
static int read(void *params,const char *name,u32 *value){void *a=params?FN(0x08109c64,void*(*)(void*,const char*))(params,name):0;return a&&!FN(0x08109566,int(*)(void*,void*))(a,value);}
static void attrname(char name[16],u32 i){const char *s="bento_fx_v1_00";u32 j=0;do{name[j]=s[j];}while(s[j++]);name[12]='0'+i/10;name[13]='0'+i%10;}
__attribute__((used)) void fx_save(void *object,void *params){
 live_save(object,params);init();u32 h=W(object,0x10);if(!h||!params)return;sync();
 for(u32 t=0;t<8;t++)if(U->live[t].handle==h){attr(params,"bento_fx_version",1);for(u32 i=0;i<18;i++){char name[16];attrname(name,i);attr(params,name,(u32)U->live[t].values[i]);}return;}
}
__attribute__((used)) void fx_load(void *node,void *object){
 live_load(node,object);if(!node||!object||B(object,4)<14||B(object,4)>22||!W(object,0x10))return;init();
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");u32 ver=0;int valid=read(params,"bento_fx_version",&ver)&&ver==1;
 if(U->pending_count>=8){for(u32 i=1;i<8;i++)U->pending[i-1]=U->pending[i];U->pending_count=7;}
 Entry *e=&U->pending[U->pending_count++];defaults(e,W(object,0x10));
 if(valid)for(u32 i=0;i<18;i++){char name[16];attrname(name,i);u32 raw;int n=read(params,name,&raw)?(int)raw:fx_default[i];if(n<fx_lo[i])n=fx_lo[i];if(n>fx_hi[i])n=fx_hi[i];e->values[i]=n;}
}
__attribute__((used)) void fx_finish(void *pane,void *event){(void)pane;if(H(event,0)==0x3f){live_finish();init();U->eu.valid=0;if(U->active==2){U->active=0;U->view=0;}sync();}}

/* EU3 edits the native SEQ encoder bar, never navigates to GenericProperties. */
extern void locks_header_before(void*);
int seq_eu_active(void *v){init();return U->eu_mode&&U->step_view==(u32)v&&B(MODEL,0x12c)==0x27;}
int seq_eu_arrows(void *v,void *event){
 init();if(!v||B(MODEL,0x12c)!=0x27||!W(v,0x113e4)||W(v,0x11400)>=16||FN(0x08133f7c,u32(*)(void*,void*))(MODEL,(u8*)v+0x113e8)!=14)return 0;
 u32 id=W(event,8);if(id!=0&&id!=1&&id!=8&&id!=9)return 0;
 U->step_view=(u32)v;eu_capture(&U->eu,v);
 if(id==1||id==8){FN(0x0815bc4c,void(*)(void*,int))(v,id==1?-1:1);return 1;}
 if(id==0){U->eu_mode=0;if(W((void*)0x24048d60u,8))live_edit(&U->eu,5,0);}
 else {if(!live_begin(&U->eu)||!eu_registry())return 1;W((void*)0x24048d80u,20)=0;seq_selection_reset(v);U->eu_mode=1;live_generate(&U->eu,5,1);}
 if(id==0)FN(0x0815c4b8,void(*)(void*))(v);else FN(0x0815c27c,void(*)(void*))(v);return 1;
}
void seq_eu_header(void *v){
 if(!seq_eu_active(v)||!eu_registry()||step_editing(v))return;eu_capture(&U->eu,v);EuPad p=live_value(&U->eu);
 u32 values[6]={U->eu.pad+1,eu_length(p),eu_pulses(p),eu_rotation(p),eu_mode(p),eu_depth(p)};
 for(u32 i=0;i<6;i++){
  u32 key=eu_keys[i],value=values[i];H(v,0x113ac+i*2)=(u16)key;W(v,0x113bc+i*4)=value;
  void *slot=(u8*)v+0xebf0+0x38+i*0x468;FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0xebf0,i,0);
  FN(0x08171c1c,void(*)(void*,u32,int,u32))(slot,key,(int)value,1);
  if(i==4)FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0xebf0,4," ");
  if(i==5){FN(0x0817e85e,void(*)(void*,const char*))((u8*)slot+0x3c8,eu_names[i]);
   if(U->eu.status==EU_FULL||U->eu.status==EU_MEMORY)FN(0x08170656,void(*)(void*,u32,const char*))((u8*)v+0xebf0,5,U->eu.status==EU_FULL?"Clip note limit":"No edit memory");}
 }
}
int seq_eu_encoder(void *v,u32 key,int value){
 if(!seq_eu_active(v))return 0;int i=eu_index(key);if(i<0||i>5)return 0;
 if(i==0){u32 pad=value<1?0:value>16?15:(u32)value-1;W(v,0x11400)=pad;U->eu.pad=pad;U->eu.hits=0;FN(0x0815c4b8,void(*)(void*))(v);}
 else if(i==4||i==5){live_dynamic(&U->eu,i==4?4:6,value);}
 else {live_generate(&U->eu,(u32)i,value);}
 FN(0x0815c27c,void(*)(void*))(v);return 1;
}

/* Native cell setters: visibility, number, track colour, trigger and playhead.
   The generator is a view over native notes: no note/clip-length mutation. */
int seq_eu_grid(void *v,int force){
 if(U->magic!=0x33555845u||U->step_view!=(u32)v||B(MODEL,0x12c)!=0x27)return 0;eu_capture(&U->eu,v);EuPad p=live_value(&U->eu);
 if(!U->eu_mode&&!(eu_native(p)&&eu_enabled(p)))return 0;
 u32 length=eu_length(p),head=0,playing=eu_enabled(p)&&live_position(&U->eu,&head);
 if(playing)head%=length;else head=0xffffffffu;
 u32 base=playing&&!step_editing(v)?(head/32)*32:W(v,0x113f4);if(base>=length)base=0;
 if(eu_native(p)&&eu_enabled(p)){W(v,0x113f8)=length;W(v,0x113f4)=base;}
 u32 signature=(base<<9)|(playing?head:256);
 if(!force&&U->draw_pattern==p.pattern&&U->draw_head==signature&&U->draw_pad==U->eu.pad&&U->draw_seq==U->eu.seq)return 1;
 U->draw_pattern=p.pattern;U->draw_head=signature;U->draw_pad=U->eu.pad;U->draw_seq=U->eu.seq;
 u32 active=0,marked=0,event[6];
 if(eu_native(p))for(u32 i=0;i<511;i++){
  if(!FN(0x0810d2c0,int(*)(void*,u32,void*))((void*)W(v,0x113dc),i,event))break;
  if(B(event,0)!=1||H(event,2)!=W(v,0x11400))continue;
  int t=(int)event[1],q=t%960;if(q>480)q-=960;int at=(t-q)/960;
  if(at<(int)base||at>=(int)(base+32)||(u32)at>=length)continue;
  active|=1u<<((u32)at-base);if(event[5])marked|=1u<<((u32)at-base);
 }
 for(u32 i=0;i<32;i++){
  u32 n=base+i,visible=n<length;void *cell=(u8*)v+0x34+i*0x704;
  FN(0x08143ada,void(*)(void*,u32))(cell,!visible);
  FN(0x0817e174,void(*)(void*,u32))(cell,n+1);
  FN(0x0817e1d8,void(*)(void*,u32))(cell,B(v,0x1140c));
  FN(0x0817e1fe,void(*)(void*,u32))(cell,visible&&(eu_native(p)?(active>>i)&1u:eu_hit(n,length,eu_pulses(p),eu_rotation(p))));
  FN(0x0817e19c,void(*)(void*,u32))(cell,visible&&playing&&n==head);
  if(eu_native(p)&&visible){
   char text[12];u32 at=0;int selected=FN(0x0815b9c0,int(*)(void*,u32))(v,n);if(selected)text[at++]='[';
   u32 number=n+1;if(number>=100)text[at++]='0'+number/100;if(number>=10)text[at++]='0'+number/10%10;text[at++]='0'+number%10;
   if(marked&(1u<<i))text[at++]='*';if(selected)text[at++]=']';text[at]=0;
   FN(0x0817e85e,void(*)(void*,const char*))((u8*)cell+0x13c,text);
  }
  B(cell,0xf9)=1;
 }

 return 1;
}
void seq_eu_tick(void *model){(void)model;if(U->magic==0x33555845u&&U->step_view)seq_eu_grid((void*)U->step_view,0);}
int seq_eu_native_head(void *v,int position){if(!seq_eu_grid(v,1))return 0;W(v,0x11408)=(u32)position;return 1;}

/* EU9: replace the value text with a white glyph at its native text size. */
__attribute__((used,retain)) void eu_glyph_paint(void *v,void *paint){
 if(!paint||(!B(paint,0)&&!B(paint,1))||!W(paint,4)||!seq_eu_active(v)||step_editing(v)||H(v,0x113ac+8)!=0x194)return;
 void *slot=(u8*)v+0xebf0+0x38+4*0x468;u32 width=W(slot,12),height=W(slot,16);
 if(B(slot,0x30)||width<140||width>320||height<64||height>160)return;
 static const u8 bars[10][5]={{6,6,6,6,6},{12,3,12,3,12},{12,3,3,12,3},{12,3,3,3,12},{12,1,1,1,12},{2,4,7,9,12},{12,9,7,4,2},{2,7,12,7,2},{6,7,5,8,6},{3,12,3,4,9}};
 EuPad p=live_value(&U->eu);u32 mode=eu_mode(p);void *label=(u8*)slot+0xa8;
 u32 lx=W(label,4),ly=W(label,8),lw=W(label,12),lh=W(label,16);
 if(lw<45||lw>320||lh<12||lh>48)return;
 u32 x=lx+(lw-45)/2,y=ly+(lh-12)/2;
 u32 rect[4]={lx,ly,lw,lh};FN(0x08166e9e,void(*)(void*,u32,void*))(rect,0xf1,(void*)W(paint,4));
 for(u32 i=0;i<5;i++){rect[0]=x+i*9;rect[1]=y+12-bars[mode][i];rect[2]=6;rect[3]=bars[mode][i];FN(0x08166e9e,void(*)(void*,u32,void*))(rect,0xf2,(void*)W(paint,4));}
}
