#pragma once
#include "fx_shared.h"
typedef unsigned long long u64;typedef long long i64;
#define EU_CONTROL_ADDR 0x24041fc0u
#define EU_MAGIC 0x324c5545u
#define EU_RECORDS 128u
/* M4 publishes config; M7 exclusively owns Runtime. Boundaries cache aligned. */
typedef struct {u32 pattern,velocity;} EuPad;
typedef struct {u32 serial,owner,row,reserved[5];EuPad pads[16];} EuRecord;
typedef struct {u32 sequence,row,epoch,ready; i64 next,origin; u32 step,owner,reserved[6];EuPad pads[16];} EuRuntime;
typedef struct {u32 epoch,serial,count,pending_count,reserved[4];EuRecord records[EU_RECORDS],pending[EU_RECORDS];EuRuntime runtime[16];} EuBank;
typedef struct {u32 magic,pointer,bytes,epoch,reserved[4];} EuControl;
#define EC ((volatile EuControl*)EU_CONTROL_ADDR)
_Static_assert(sizeof(EuRecord)%32==0,"record alignment");
_Static_assert(sizeof(EuRuntime)%32==0,"runtime alignment");
static inline u32 eu_length(EuPad p){return (p.pattern&255u)+1;}
static inline u32 eu_pulses(EuPad p){return (p.pattern>>8)&511u;}
static inline u32 eu_rotation(EuPad p){return (p.pattern>>17)&255u;}
static inline int eu_native(EuPad p){return (p.pattern>>26)&1u;}
static inline int eu_enabled(EuPad p){return (p.pattern>>25)&1u;}
static inline u32 eu_base(EuPad p){return p.velocity&127u;}
static inline u32 eu_mode(EuPad p){return (p.velocity>>8)&15u;}
static inline u32 eu_depth(EuPad p){return (p.velocity>>16)&127u;}
static inline u32 eu_dynamics(u32 base,u32 mode,u32 depth){return base|(mode<<8)|(depth<<16);}
static inline int eu_pad_valid(EuPad p){return !(p.pattern>>27)&&!(p.velocity&~0x007f0f7fu)&&eu_base(p)>=1&&eu_mode(p)<=9&&eu_depth(p)<=100&&eu_pulses(p)<=eu_length(p)&&eu_rotation(p)<eu_length(p);}
static inline EuPad eu_pack(u32 len,u32 hits,u32 rot,u32 vel,u32 on){EuPad p={(len-1)|(hits<<8)|(rot<<17)|(on<<25),vel};return p;}
static inline int eu_memory(u32 p,u32 n){return p && !(p&31) && p+n>=p && ((p>=0xc0000000u&&p+n<=0xc8000000u)||(p>=0x30000000u&&p+n<=0x30040000u));}
