/* BENTO_MOD T2: native per-note A:B conditions; A-D and note payload unchanged. */
typedef unsigned int u32;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u8 *)(p)+(o)))
typedef struct {u32 sequence,owner,row,loop,boundaries,reserved[3];} Counter;
#define COUNTERS ((volatile Counter *)0x24048a60u)
static volatile Counter *entry(void *seq){
 u32 owner=W(seq,12),row=W(seq,0x86c0);
 volatile Counter *free=0;
 for(u32 i=0;i<16;i++){
  volatile Counter *c=COUNTERS+i;
  if(c->sequence==(u32)seq){
   if(c->owner!=owner || c->row!=row){c->owner=owner;c->row=row;c->loop=0;c->boundaries=0;}
   return c;
  }
  if(!c->sequence && !free)free=c;
 }
 if(!free)return 0;
 free->owner=owner;free->row=row;free->loop=0;free->boundaries=0;
 free->sequence=(u32)seq;return free;
}
__attribute__((used)) void condition_loop(void *seq){
 volatile Counter *c=entry(seq);if(!c)return;
 if(c->boundaries && (int)W(seq,0x14)>=0)c->loop++;
 else c->loop=0;
 c->boundaries=1;
}
/* 0=skip, 1=play, 2=original probability decision. */
__attribute__((used)) int condition_decide(void *seq,u32 cond){
 if(cond<100 || cond>=135)return 2;
 u32 i=cond-100,b=2;
 while(i>=b){i-=b;b++;}
 volatile Counter *c=entry(seq);
 if(!c)return 1; /* Capacity failure preserves native always behaviour. */
 return c->loop%b==i;
}
