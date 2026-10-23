#include "fx_shared.h"
typedef struct {u32 handle;int values[18];} Entry;
typedef struct {u32 magic,active,selected,view,nav,held,serial,pending_count;Entry live[8],pending[8];char titles[3][40];u32 armed,pressed,down_tick,up_tick;} Ui;
#define U ((Ui*)UI_ADDR)
_Static_assert(sizeof(Ui)<=0x600,"UI state exceeds reservation");
static const char *const names[19]={"EQ","Low Hz","Low dB","Mid Hz","Mid dB","Mid Q","High Hz","High dB","Compressor","Thresh dB","Ratio","Attack ms","Release ms","Auto Makeup","Makeup dB","Mix %","Soft Clip","Ceiling dB","Track"};
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static void defaults(Entry *e,u32 handle){e->handle=handle;for(u32 i=0;i<18;i++)e->values[i]=fx_default[i];}
static void init(){if(U->magic!=0x32555846u){zero(U,sizeof(*U));for(u32 i=0;i<8;i++)defaults(&U->live[i],0);U->magic=0x32555846u;}}
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
__attribute__((used)) int fx_dispatch(void *m,u32 code,u32 context,u32 index){
 (void)context;init();
 if(code==0xb0&&index==2&&U->held){U->held=0;return 1;}
 /* Native HAL_GetTick (081152C0) reads this millisecond counter. A first
    TRACKS press immediately follows K16; only a second short tap is consumed.
    Pad actions, shift, other buttons and a long hold cancel the tap sequence. */
 u32 tick=W((void*)0x3001fe2cu,0);
 if(index!=2 || (code!=0xaf&&code!=0xb0)){
  if(code==0xaf||code==0xb0||code==0xfe){U->armed=0;if(U->pressed)U->pressed=2;}return 0;
 }
 if(W((void*)0x24048d60u,8)){U->armed=0;U->pressed=0;return 0;}
 if(code==0xb0){
  if(U->pressed==1 && tick-U->down_tick<=300 && !W((void*)0x24048cc0u,8)){
   U->armed=1;U->up_tick=tick;
  }else U->armed=0;
  U->pressed=0;return 0;
 }
 if(code==0xaf){
  int second=U->armed && tick-U->up_tick<=350 && B(m,0x12c)==2;U->armed=0;
  U->pressed=1;U->down_tick=tick;
  if(!second)return 0;
  U->pressed=0;
  if(!registry())return 1;sync();u32 selected=FN(0x0812dc74,u32(*)(void*,u32))((u8*)m+4,0x131);U->selected=selected<8?selected:0;
  U->active=1;U->held=1;U->nav=1;U->view=0;
  FN(0x081420ec,void(*)(void*,u32,u32,u32,u32))(m,0x1a,0,0,0);U->nav=0;
  return 1;
 }
 return 0;
}
__attribute__((used)) void fx_nav(void *m,u32 page){(void)m;(void)page;init();if(!U->nav){U->active=0;U->view=0;}}
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
 (void)m;(void)handle;init();if(U->active&&out&&key==0){W(out,0)=0;return 1;}int i=key_index(key);if(i<0||!U->active||!out)return 0;
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
 init();u32 h=W(object,0x10);if(!h||!params)return;sync();
 for(u32 t=0;t<8;t++)if(U->live[t].handle==h){attr(params,"bento_fx_version",1);for(u32 i=0;i<18;i++){char name[16];attrname(name,i);attr(params,name,(u32)U->live[t].values[i]);}return;}
}
__attribute__((used)) void fx_load(void *node,void *object){
 if(!node||!object||B(object,4)<14||B(object,4)>22||!W(object,0x10))return;init();
 void *params=FN(0x08109268,void*(*)(void*,const char*))(node,"params");u32 ver=0;int valid=read(params,"bento_fx_version",&ver)&&ver==1;
 if(U->pending_count>=8){for(u32 i=1;i<8;i++)U->pending[i-1]=U->pending[i];U->pending_count=7;}
 Entry *e=&U->pending[U->pending_count++];defaults(e,W(object,0x10));
 if(valid)for(u32 i=0;i<18;i++){char name[16];attrname(name,i);u32 raw;int n=read(params,name,&raw)?(int)raw:fx_default[i];if(n<fx_lo[i])n=fx_lo[i];if(n>fx_hi[i])n=fx_hi[i];e->values[i]=n;}
}
__attribute__((used)) void fx_finish(void *pane,void *event){(void)pane;if(H(event,0)==0x3f){init();sync();}}
