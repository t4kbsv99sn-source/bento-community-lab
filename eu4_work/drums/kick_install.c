/* BENTO_MOD K2: self-contained kick entry, created through native SD I/O.
 * Called on the UI thread immediately before the ordinary one-shot Load action.
 * Only our fixed path is created. Existing files are never overwritten.
 * No filesystem or UI operations occur in the audio renderer. */
typedef unsigned int u32;
typedef unsigned char u8;
#include "kick_assignment.h"
#define FN(a,t) ((t)((a)|1u))
#define FRAMES 144019u
#define DATA_BYTES (FRAMES*2u)
static const char path[]="\\Projects\\BENTO_Kick_K2.wav";
static const u32 header[11]={0x46464952,36u+DATA_BYTES,0x45564157,
 0x20746d66,16,0x00010001,48000,96000,0x00100002,0x61746164,DATA_BYTES};
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8*)p)[i]=0;}
static int equal(const void *a,const void *b,u32 n){
 for(u32 i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;
}
static void signature(u8 *p){for(u32 i=0;i<32;i++){
 u32 v=(0xb1e70a5cu&(1u<<i))?1u:65535u;p[i*2]=(u8)v;p[i*2+1]=(u8)(v>>8);
}}
static int write_all(void *f,const void *data,u32 n){
 u32 done=0;return !FN(0x08120604,u32(*)(void*,const void*,u32,u32*))(f,data,n,&done) && done==n;
}
/* Native FatFS FIL is 0x58 bytes, as used by the stock WAV reader/writer.
 * API addresses and creation flags checked against the original recording path. */
static int install_one(const char *path,u32 frames){
 u32 data_bytes=frames*2u;u32 local_header[11];for(u32 i=0;i<11;i++)local_header[i]=header[i];local_header[1]=36+data_bytes;local_header[10]=data_bytes;
 u32 file[22];u8 buffer[512];u32 got=0;zero(file,sizeof(file));
 u32 result=FN(0x08120148,u32(*)(void*,const char*,u32))(file,path,1);
 if(!result){
  u32 size=file[4],high=file[5];zero(buffer,108);
  result=FN(0x08120464,u32(*)(void*,void*,u32,u32*))(file,buffer,108,&got);
  u32 closed=FN(0x08120974,u32(*)(void*))(file);
  u8 signs[64];signature(signs);
  return !result && !closed && got==108 && size==44u+data_bytes && !high
   && equal(buffer,local_header,44) && equal(buffer+44,signs,64);
 }
 if(result!=4)return 0; /* FR_NO_FILE only. No truncate/recovery writes. */
 zero(file,sizeof(file));
 if(FN(0x08120148,u32(*)(void*,const char*,u32))(file,path,6))return 0;
 int ok=write_all(file,local_header,sizeof(local_header));
 signature(buffer);if(ok)ok=write_all(file,buffer,64);zero(buffer,sizeof(buffer));
 for(u32 left=data_bytes-64;ok && left;){
  u32 count=left>sizeof(buffer)?sizeof(buffer):left;ok=write_all(file,buffer,count);left-=count;
 }
 result=FN(0x08120974,u32(*)(void*))(file);return ok && !result;
}
__attribute__((used)) int kick_install(void){int k=install_one(path,FRAMES);int s=install_one("\\Projects\\BENTO_Synth_Snare.wav",FRAMES+2);int h=install_one("\\Projects\\BENTO_Synth_HiHat.wav",FRAMES+4);return k&&s&&h;}
static void kick_report(void);
__attribute__((used)) void kick_load_entry(void *pane,void *event){
 (void)pane;
 if(*(volatile unsigned short*)event==0x3f){kick_install();kick_report();}
}
static u32 lower(u32 c){return c>='A' && c<='Z'?c+32:c;}
__attribute__((used)) int kick_path(const char *s){
 if(!s)return 0;const char *base=s;u32 n=0;
 for(;n<256 && s[n];n++)if(s[n]=='/' || s[n]=='\\')base=s+n+1;
 if(n==256)return 0;
 const char *names[3]={"bento_kick.wav","bento_kick_k1.wav","bento_kick_k2.wav"};
 for(u32 k=0;k<3;k++){
  u32 i=0;while(names[k][i] && base[i] && lower((u8)base[i])==(u8)names[k][i])i++;
  if(!names[k][i] && !base[i])return 1;
 }return 0;
}
__attribute__((used)) void kick_assign(u32 handle,u32 enabled){
 if(!handle || handle>=0xfffffff0u)return;
 if(ASSIGN->magic!=ASSIGN_MAGIC){zero(ASSIGN,sizeof(*ASSIGN));ASSIGN->magic=ASSIGN_MAGIC;}
 KickAssignment *chosen=0;u32 age=0;
 for(u32 i=0;i<128;i++){
  KickAssignment *e=&ASSIGN->entries[i];
  if(e->sequence && e->handle==handle){chosen=e;break;}
  if(!e->sequence && !chosen)chosen=e;
 }
 if(!chosen)for(u32 i=0;i<128;i++){
  KickAssignment *e=&ASSIGN->entries[i];u32 a=ASSIGN->serial-e->sequence;
  if(!chosen || a>age){age=a;chosen=e;}
 }
 u32 serial=ASSIGN->serial+2;if(!serial)serial=2;
 chosen->sequence=serial|1u;__asm__ volatile("dsb" ::: "memory");
 chosen->handle=handle;chosen->enabled=enabled!=0;
 __asm__ volatile("dsb" ::: "memory");chosen->sequence=serial;
 __asm__ volatile("dsb" ::: "memory");ASSIGN->serial=serial;
 __asm__ volatile("dsb" ::: "memory");
}
__attribute__((used)) void kick_sample_loading(void *manager,u32 handle,const char *s,u32 async){
 (void)manager;(void)async;
 volatile u32 *u=(volatile u32*)0x24043f00u;
 if(u[0]!=0x3455494bu){for(u32 i=0;i<32;i++)u[i]=0;u[0]=0x3455494bu;}
 u[1]++;u[2]=handle;u[3]=(u32)s;
 int match=kick_path(s);if(match){u[4]++;u[5]=handle;}
 if(!handle || handle>=0xfffffff0u){u[6]++;return;} /* Native browser preview is temporary. */
 /* K6: loader handles identify files, not necessarily native sound roots.
  * Hardware K5: loaded kick file 13F, rendered sound 13E. Do not post a
  * property or populate a sound assignment from this unverified ID mapping.
  * Audio recognition uses the native descriptor's content instead. */
 void *engine=*(void * volatile *)0x3000f650u;u[7]=(u32)engine;
}

/* K4 diagnostic snapshot: fixed mod-owned report, only on the UI Load action.
 * No card I/O, formatting, or allocations occur on the audio thread.
 * The existing nearly silent marker is deliberately unchanged for this test. */
static const char *const m7_names[32]={
 "m7_magic","commands","command_root","command_class","object_handle","command_handle","command_enable","arms",
 "voice_entries","voice_root","voice_class","voice_descriptor","voice_reason",
 "render_entries","render_root","render_class","render_descriptor","render_reason",
 "synth_starts","synth_blocks","block_frames","temp_buffer","temp_capacity","temp_data",
 "generated_peak_f32","descriptor_provider","marker_frames","marker_rate","marker_stereo","marker_magnitude_f32","marker_reason","render_handle"};
static const char *const ui_names[10]={"ui_magic","loader_entries","last_handle","last_path_address","kick_name_matches","kick_name_handle","ignored_preview","engine_address","commands_sent","kick_commands_sent"};
static int report_line(void *file,const char *name,u32 value){
 char line[64];u32 n=0;while(*name && n<48)line[n++]=*name++;
 line[n++]='=';line[n++]='0';line[n++]='x';
 for(u32 i=0;i<8;i++)line[n++]="0123456789abcdef"[(value>>(28-4*i))&15];
 line[n++]='\r';line[n++]='\n';return write_all(file,line,n);
}
static void kick_report(void){
 u32 snapshot[45];volatile u32 *d=(volatile u32*)0x24043e00u,*u=(volatile u32*)0x24043f00u;
 for(u32 i=0;i<32;i++)snapshot[i]=d[i];for(u32 i=0;i<10;i++)snapshot[32+i]=u[i];
 snapshot[42]=ASSIGN->magic;snapshot[43]=ASSIGN->serial;snapshot[44]=sizeof(*ASSIGN);
 u32 file[22];zero(file,sizeof(file));
 if(FN(0x08120148,u32(*)(void*,const char*,u32))(file,"\\Projects\\BENTO_K7_DIAGNOSTICS.txt",10))return;
 static const char title[]="BENTO K6 diagnostic snapshot - all values hexadecimal\r\n";
 int ok=write_all(file,title,sizeof(title)-1);
 for(u32 i=0;ok && i<32;i++)ok=report_line(file,m7_names[i],snapshot[i]);
 for(u32 i=0;ok && i<10;i++)ok=report_line(file,ui_names[i],snapshot[32+i]);
 if(ok)ok=report_line(file,"assignment_magic",snapshot[42]);
 if(ok)ok=report_line(file,"assignment_serial",snapshot[43]);
 if(ok)ok=report_line(file,"assignment_bytes",snapshot[44]);
 FN(0x08120974,u32(*)(void*))(file);
}
