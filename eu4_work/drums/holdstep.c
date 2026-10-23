/* BENTO_MOD T2: extend native held-step selection, do not synthesize notes. */
typedef unsigned int u32;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u8*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
typedef struct {u32 magic,view,sequence,drum,step,active,reserved[2];} Inspect;
#define S ((volatile Inspect*)0x24048d80u)
#define MAGIC 0x32495042u
static int held(void *v){for(u32 i=0;i<32;i++)if(W(v,0x11420+i*4))return 1;return 0;}
static int local(void *v){
 if(S->magic!=MAGIC || !S->active || S->view!=(u32)v || !W(v,0x113e4) || S->sequence!=W(v,0x113e4) || S->drum!=W(v,0x11400))return -1;
 u32 base=W(v,0x113f4);
 if(S->step<base || S->step-base>=32 || S->step>=W(v,0x113f8))return -1;
 return (int)(S->step-base);
}
static void remember(void *v,u32 i){
 S->magic=MAGIC;S->active=0;
 if(i>31 || !W(v,0x113e4) || !W(v,0x113dc))return;
 if(!FN(0x0815bcb4,int(*)(void*,u32))(v,i))return;
 S->view=(u32)v;S->sequence=W(v,0x113e4);S->drum=W(v,0x11400);
 S->step=W(v,0x113f4)+i;S->active=1;
}
__attribute__((used)) void step_press(void *v,u32 encoded){
 u32 i=encoded-0x4508u;remember(v,i);
 if(*(volatile u32*)0x24048d68u)FN(0x081b8e00,void(*)(void*,u32))(v,i);
}
__attribute__((used)) void step_touch(void *v){remember(v,W(v,0x114a4));}
__attribute__((used)) int step_match(void *v,u32 absolute){
 if(held(v))return FN(0x081b6600,int(*)(void*,u32))(v,absolute);
 return local(v)>=0 && S->step==absolute;
}
__attribute__((used)) int step_selected(void *v){
 if(held(v))return 1;
 int i=local(v);
 return i>=0 && W(v,0x113dc) && FN(0x0815bcb4,int(*)(void*,u32))(v,(u32)i);
}
__attribute__((used)) void step_edit(void *v){
 /* Keep nonzero held entries so native multi-step editing still works, but
  * make release take its native long-hold path after any encoder edit. */
 u32 now=*(volatile u32*)0x30035f40u;
 u32 past=now-1001u;if(!past)past=0xffffffffu;
 for(u32 i=0;i<32;i++)if(W(v,0x11420+i*4))W(v,0x11420+i*4)=past;
}

