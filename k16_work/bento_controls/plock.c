/* BENTO_MOD L2: fixed Level lock proof. One runtime target; no project writes. */
typedef unsigned int u32;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u8 *)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u8 *)(p)+(o)))
typedef struct {u32 magic,enabled,owner,target,sequence,target_handle,seen,reserved;} LockState;
#define L ((volatile LockState *)0x24048c60u)
#define MAGIC 0x314c5042u
typedef void (*Eval)(void *);

__attribute__((used)) int lock_command(void *object, const u32 *record) {
 if(record[3]==0x7ffcu){
  ((void(*)(void*,const u32*))0x080d58f5u)(object,record);
  if(object && W(object,12)==record[2] && W(object,0)==0x080ac66cu)
   ((void(*)(void*,u32))0x080d58f1u)(object,record[4]!=0);
  return 1;
 }
 if(record[3]!=0x7ffeu && record[3]!=0x7ffdu)return 0;
 /* The extended key is never passed to a native property setter. */
 if(record[3]==0x7ffdu){
  if(L->magic==MAGIC && L->target_handle==record[2])L->enabled=0;
  return 1;
 }
 if(W(object,12)!=record[2])return 1;
 /* Only the exact native class/Level layout traced for this experiment. */
 if(W(object,0)!=0x080ac66cu)return 1;
 if(!record[4] || record[4]==0xffffffffu)return 1;
 L->enabled=0;L->magic=MAGIC;L->owner=record[4];
 L->target=(u32)object+0x138u;L->target_handle=record[2];
 L->sequence=0;L->seen=0;L->enabled=1;
 return 1;
}

__attribute__((used)) void lock_sequence(void *sequence) {
 if(L->magic==MAGIC && L->enabled && W(sequence,12)==L->owner){
  L->sequence=(u32)sequence;L->seen++;
 }
}

__attribute__((used)) int lock_evaluate(void *parameter) {
 Eval original=(Eval)0x080d1f01u;
 if(L->magic!=MAGIC || !L->enabled || !L->target || !L->sequence)
  return 0;
 void *root=(void*)L->target;
 /* Native 0x08092F20 copies this parameter into each voice at +0x180.
  * Copies retain the original, sound-specific base-source pointer. */
 u32 source_id=W(root,0);
 if(!source_id || W(parameter,0)!=source_id)return 0;
 void *seq=(void*)L->sequence;
 if(W(seq,12)!=L->owner || !B(seq,0x20))return 0;
 u32 step=W(seq,0x14);
 if(step>255 || (step&3u)!=0)return 0;
 void *obj=(u8*)root-0x138;
 if(W(obj,0)!=0x080ac66cu || W(obj,12)!=L->target_handle)return 0;
 /* Native base + three user modulators + A-D slot. Only the local copy
  * replaces the base contribution and removes A-D during the locked step.
  * Original source pointers, coefficients, curves and model remain intact. */
 u32 copy[16];for(u32 i=0;i<16;i++)copy[i]=W(parameter,i*4);
 struct {u32 opaque;float value;} source={0,0.25f};
 copy[0]=(u32)&source;copy[1]=0x3f800000u;copy[8]=0;copy[9]=0;
 u32 count=0;
 for(u32 i=0;i<5;i++)if(copy[i*2])((u8*)copy)[0x28+count++]=(u8)i;
 copy[12]=count;
 original(copy);
 W(parameter,0x3c)=copy[15];
 return 1;
}
