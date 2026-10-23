#include "fx_shared.h"
#include "../track_fx/track_fx.h"
struct Meta {u32 magic,serial,ready;int prior[8][18];u32 handles[8],active[8],calls[8],bad;};
#define A ((Meta*)META_ADDR)
static_assert(sizeof(Meta)<=0x340,"Audio metadata overlaps UI state");
static void invalidate(u32 a,u32 end){
 __asm__ volatile("dsb" ::: "memory");
 if(W((void*)0xe000ed14u,0)&(1u<<16))for(;a<end;a+=32)W((void*)0xe000ef5cu,0)=a;
 __asm__ volatile("dsb" ::: "memory");
}
static int memory(u32 p,u32 n){return p && !(p&3) && p+n>=p && ((p>=0x20000000u&&p+n<=0x20040000u)||(p>=0x24000000u&&p+n<=0x24080000u)||(p>=0x30000000u&&p+n<=0x30040000u)||(p>=0xc0000000u&&p+n<=0xc6000000u));}
static void sync(){
 if(A->magic!=0x32415846u){for(u32 j=0;j<sizeof(Meta)/4;j++)((u32*)A)[j]=0;A->magic=0x32415846u;}
 invalidate(MAIL_ADDR,MAIL_ADDR+32);
 u32 serial=MAIL->serial;if(MAIL->magic!=MAIL_MAGIC||!serial||(serial&1)||serial==A->serial)return;
 invalidate(MAIL_ADDR,MAIL_ADDR+sizeof(FxMail)+31);
 int values[8][18];u32 handles[8];int any=0;
 for(int t=0;t<8;t++)handles[t]=MAIL->handles[t];
 for(int t=0;t<8;t++)for(int i=0;i<18;i++){int v=MAIL->values[t][i];if(v<fx_lo[i]||v>fx_hi[i])return;values[t][i]=v;}
 __asm__ volatile("dmb" ::: "memory");invalidate(MAIL_ADDR,MAIL_ADDR+32);
 if(serial!=MAIL->serial)return;
 for(int t=0;t<8;t++)if(values[t][0]||values[t][8]||values[t][16])any=1;
 if(!A->ready&&any){if(tf_bank_bytes()>DSP_BYTES||!tf_init((void*)DSP_ADDR,48000))return;A->ready=1;}
 for(int t=0;t<8;t++){
  int changed=!A->serial;
  for(int i=0;i<18;i++)if(A->prior[t][i]!=values[t][i])changed=1;
  if(A->ready&&(changed||A->handles[t]!=handles[t])){
   TfSettings s;tf_defaults(&s);int *v=values[t];
   s.eq_enabled=v[0];s.low_hz=v[1];s.low_db=v[2];s.mid_hz=v[3];s.mid_db=v[4];s.mid_q=v[5];s.high_hz=v[6];s.high_db=v[7];
   s.comp_enabled=v[8];s.threshold_db=v[9];s.ratio=v[10];s.attack_ms=v[11];s.release_ms=v[12];s.auto_makeup=v[13];s.makeup_db=v[14];s.comp_mix=(float)v[15]*.01f;
   s.clip_enabled=v[16];s.clip_ceiling_db=v[17];if(!tf_configure((void*)DSP_ADDR,t,&s))return;
   if(A->handles[t]!=handles[t])tf_reset_track((void*)DSP_ADDR,t);
  }
  for(int i=0;i<18;i++)A->prior[t][i]=values[t][i];
  A->handles[t]=handles[t];
  A->active[t]=values[t][0]||values[t][8]||values[t][16]||A->active[t];
 }
 A->serial=serial;
}
extern "C" __attribute__((used)) void fx_audio(void *mixer,void *buffer,u32 track,void *strip){
 // Native 080A04C0 is called once per track; hook AFTER input gain copied to
 // the track-owned scratch, before pan, ducking, sends and dry-bus combination.
 if(track>=8||W(mixer,0)!=0x080aca1cu||W(mixer,0x860)>8||(u32)strip!=(u32)mixer+0x18+track*0x108||(u32)buffer!=(u32)strip+12)return;
 sync();if(A->magic!=0x32415846u||!A->ready||!A->active[track])return;
 u32 n=W(buffer,4);if(!n)n=W(buffer,0);u32 left=W(buffer,8),right=B(buffer,0x11)?W(buffer,12):0;
 if(!n||n>1024||W(buffer,0)<n||!memory(left,n*4)||(right&&!memory(right,n*4))||(right&&(left>right?left-right<n*4:right-left<n*4))){A->bad++;return;}
 if(B(buffer,0x10)){for(u32 i=0;i<n;i++){((float*)left)[i]=0;if(right)((float*)right)[i]=0;}B(buffer,0x10)=0;W(buffer,4)=n;}
 if(tf_process((void*)DSP_ADDR,track,(float*)left,(float*)right,n))A->calls[track]++;
 // Preserve tails during the bypass fade. The DSP will make its inactive path
 // exact bypass; no native buffer pointers, counts or routing are replaced.
}
