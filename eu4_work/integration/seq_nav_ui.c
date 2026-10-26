/* P16: native-style melodic tabs, selection, global Undo/settings access. */
#include "fx_shared.h"
#include "../../chord_work/device.h"
int chord_view_visible(void);void chord_view_set(int);
void piano_mode_set(void*,int);int piano_select_toggle(void*);int piano_selecting(void*);
#define PROJECTS 0x1062u
#define SETTINGS 0x1063u
#define DATETIME 0x1064u
int seq_nav_global(void *model,void *event){
 u32 code=H(event,0),page=code==PROJECTS?0x13:code==SETTINGS?0x1a:code==DATETIME?0x19:0;
 if(!page)return 0;
 FN(0x081420ec,void(*)(void*,u32,u32,u32,u32))(model,page,0,0,1);return 1;
}
int seq_nav_event(void *v,void *event){
 if(seq_nav_global(MODEL,event))return 1;
 u32 code=H(event,0);
 if(code==0x1070){FN(0x081403ec,int(*)(void*,void*))(MODEL,event);return 1;} /* P22: Motion Settings is a model action (motion layer) */
 /* P22 (owner: no way out of the automation view). Chord/Euclid draw over
    the Step editor, so leave the native Automation tab (2) first. */
 if((code==0x1060||code==0x1061)&&B(v,0x125dac)==2){u32 e[5]={0x49,0,0,0,0};FN(0x0815a598,int(*)(void*,void*))(v,e);}
 if(code==0x1060){if(!chord_view_visible()){piano_mode_set(v,0);chord_view_set(1);FN(0x081599bc,void(*)(void*))(v);}return 1;}
 if(code==0x1061){chord_view_set(0);piano_mode_set(v,1);return 1;}
 {extern int chord_clear_current(void);if(code==0x4d&&chord_view_visible()&&chord_clear_current())return 1;} /* P24 (owner): Clear in chord mode = the whole selected chord */
 if(code==0x1051)return piano_select_toggle(v);
 if(code==0x49||code==0x4a||code==0x4b){chord_view_set(0);piano_mode_set(v,0);return 0;}
 if(code==0x1059){u32 e[5]={B(v,0x125dac)==2?0x49u:0x4bu,0,0,0,0};chord_view_set(0);piano_mode_set(v,0);FN(0x0815a598,int(*)(void*,void*))(v,e);return 1;} /* P22: toggles; from Automation back to Step */
 return 0;
}
/* Rebuild F9 on every header apply. mode 0: native actions minus Undo;
 * 1: pitched SEQ (sequence actions, Automation, Chord Bank on the chord view);
 * 2 (P17, owner plan): the Performance page burger holds Projects, Settings and
 * Date / Time, and nothing else does. At most 9 cells. */
int chord_bank(void);
static void cells(u8 *menu,const u32 *keys,const char *const *names,u32 n){
 for(u32 i=0;i<n;i++){void *c=menu+4+i*20;for(u32 j=0;j<5;j++)W(c,j*4)=0;W(c,0)=keys[i];W(c,4)=(u32)names[i];W(c,16)=1;}B(menu,0xcc)=(u8)n;
}
static int ours(const u8 *menu,u32 n){
 if(!n)return 0;u32 first=W(menu,4),last=W(menu,4+(n-1)*20);
 return first==PROJECTS||(first==0x1041u&&(last==0x1059u||last==0x1070u||last==0x1052u||last==DATETIME));
}
void seq_nav_menus(int mode){
 static const char *const seq_names[]={"Double Seq","Halve Seq","Cut Seq","Copy Seq","Paste Seq","Automation","Motion Settings","Chord Bank 2","Chord Bank 1"};
 static const u32 seq_keys[]={0x1041,0x1042,0x102f,0x102e,0x1030,0x1059,0x1070,0x1052,0x1052}; /* P22: 1070 = motion recording settings */
 static const char *const perf_names[]={"Projects","Settings","Date / Time"};
 static const u32 perf_keys[]={PROJECTS,SETTINGS,DATETIME};
 for(u32 m=0;m<20;m++){
  u8 *menu=(u8*)0x30030168u+m*0xe0;u32 n=B(menu,0xcc);if(n>9)continue;int f9=W(menu,0)==0xf9u;
  if(f9&&mode==1){
   cells(menu,seq_keys,seq_names,7);
   {extern void *piano_current_view(void);void *pv=piano_current_view();if(pv&&B(pv,0x125dac)==2)W(menu,4+5*20+4)=(u32)"Close Automation";} /* P22 */
   if(chord_view_visible()){u32 b=chord_bank()?8:7;void *c=menu+4+7*20;for(u32 j=0;j<5;j++)W(c,j*4)=0;W(c,0)=seq_keys[b];W(c,4)=(u32)seq_names[b];W(c,16)=1;B(menu,0xcc)=8;}
   continue;
  }
  if(f9&&mode==2){cells(menu,perf_keys,perf_names,3);continue;}
  if(f9&&ours(menu,n)){
   static const u32 old[]={0x1041,0x1042,0x102f,0x1051,0x102e,0x1030,0x102c,0x102d};
   static const char *const labels[]={"Double Seq","Halve Seq","Cut Seq","Select","Copy Seq","Paste Seq","Clear Seq","Clear Auto"};
   cells(menu,old,labels,8);n=8;
  }
  u32 count=0;for(u32 i=0;i<n;i++){void *c=menu+4+i*20;if(W(c,0)==0x1032)continue;void *d=menu+4+count++*20;for(u32 j=0;j<5;j++)W(d,j*4)=W(c,j*4);}B(menu,0xcc)=(u8)count;
 }
}
void seq_nav_undo(void *model){
 extern void *piano_current_view(void);extern void *step_current_view(void);
 u32 e[5]={0x1032,W(model,0x144),0,0,0};void *v=0;
 if(B(model,0x12c)==0x17&&(v=piano_current_view()))FN(0x0815a598,int(*)(void*,void*))(v,e);
 else if(B(model,0x12c)==0x27&&(v=step_current_view()))FN(0x0815d600,int(*)(void*,void*))(v,e);
 else FN(0x081403ec,int(*)(void*,void*))(model,e);
}
