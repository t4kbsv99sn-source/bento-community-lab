#pragma once
typedef unsigned int u32;typedef unsigned char u8;typedef unsigned short u16;
#define W(p,o) (*(volatile u32*)((u8*)(p)+(o)))
#define H(p,o) (*(volatile u16*)((u8*)(p)+(o)))
#define B(p,o) (*(volatile u8*)((u8*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define MAIL_MAGIC 0x324d5846u
/* All UI-owned state is inside the native M4 MPU's RW region, >=24040000.
   Reserve exactly 8 KiB below K16's heap ceiling; never change the MPU. */
#define DSP_ADDR 0x24040000u
#define DSP_BYTES 0x1440u
#define MAIL_ADDR 0x24041440u
#define META_ADDR 0x240416c0u
#define UI_ADDR 0x24041a00u
#define MODEL ((void*)0x30024b00u)
enum {PARAMS=18,TRACKS=8};
typedef struct {u32 magic,serial,handles[8];int values[8][18];} FxMail;
typedef char MailFits[(sizeof(FxMail)<=0x280)?1:-1];
#define MAIL ((volatile FxMail*)MAIL_ADDR)
static const u16 fx_keys[19]={0x1b1,0x1b2,0x1b3,0x1b4,0x1b5,0x1b6,0x1b7,0x1b9,0x1bc,0x1bf,0x1c0,0x1c1,0x1c2,0x1c3,0x1c4,0x1c5,0x1c6,0x1ca,0x1d0};
static const int fx_lo[19]={0,20,-12,20,-12,1,20,-12,0,-60,1,1,10,0,0,0,0,-12,1};
static const int fx_hi[19]={1,20000,12,20000,12,6,20000,12,1,0,20,100,2000,1,12,100,1,0,8};
static const int fx_default[18]={0,120,0,1000,0,1,6000,0,0,-18,3,10,120,1,0,100,0,-1};
static inline int key_index(u32 key){for(int i=0;i<19;i++)if(fx_keys[i]==key)return i;return -1;}
