#pragma once
#include "fx_shared.h"
typedef unsigned long long u64;typedef long long i64;
#define EU_CONTROL_ADDR 0x24041fc0u
#define EU_MAGIC 0x324c5545u
#define EU_RECORDS 128u
/* M4 publishes config; M7 exclusively owns Runtime. Boundaries cache aligned. */
typedef struct {u32 pattern,velocity;} EuPad;
/* CH3 melodic rows: reserved[0] bit0 marks a pitched-track record; reserved[1..4]
   hold one MIDI pitch byte per pad/row. Drum records keep these words zero. */
typedef struct {u32 serial,owner,row,reserved[5];EuPad pads[16];} EuRecord;
#define EU_MELODIC 1u
static inline int eu_record_melodic(const volatile EuRecord *r){return (int)(r->reserved[0]&EU_MELODIC);}
static inline u32 eu_record_pitch(const volatile EuRecord *r,u32 pad){return pad<16?(r->reserved[1+pad/4]>>((pad%4)*8))&127u:0;}
static inline void eu_record_set_pitch(volatile EuRecord *r,u32 pad,u32 pitch){if(pad>=16)return;u32 w=1+pad/4,sh=(pad%4)*8;r->reserved[w]=(r->reserved[w]&~(255u<<sh))|((pitch&127u)<<sh);}
/* CH3 adds one M7-owned cache line: melodic flag and the playing row pitches. */
typedef struct {u32 sequence,row,epoch,ready; i64 next,origin; u32 step,owner,reserved[6];EuPad pads[16];u32 melodic,spare[3];u8 pitch[16];} EuRuntime;
/* CH6 chord pad audition (keyboard pads on the pitched piano roll).
   ChordMail: M4-written under an odd/even serial; per pitch class, the chord
   tones as offsets from the pad's pitch. ChordPub: M7-written pitch of the last
   press per pad (bit7 = valid). ChordOwn: M7-only ownership so note-offs always
   use the pitches that were actually started. Separate cache lines. */
#define CA_VOICES 6
typedef struct {u32 serial,active,velocity,spare;u8 count[12],pad0[4];signed char off[12][CA_VOICES];u8 pad1[24];} ChordMail;
typedef struct {u32 serial;u8 pitch[16];u32 held,spare[2];} ChordPub; /* CH9 held: chord pads currently down */
typedef struct {u8 refs[2][128];u32 held[2][4];u8 count[128];u8 notes[128][CA_VOICES];u8 vel[128];u8 pad[32];} ChordOwn;
typedef struct {u32 epoch,serial,count,pending_count,reserved[4];EuRecord records[EU_RECORDS],pending[EU_RECORDS];EuRuntime runtime[16];ChordMail chord_mail;ChordPub chord_pub;ChordOwn chord_own;} EuBank;
typedef struct {u32 magic,pointer,bytes,epoch,reserved[4];} EuControl;
#define EC ((volatile EuControl*)EU_CONTROL_ADDR)
_Static_assert(sizeof(EuRecord)%32==0,"record alignment");
_Static_assert(sizeof(EuRuntime)%32==0,"runtime alignment");
_Static_assert(sizeof(ChordMail)==128&&sizeof(ChordPub)==32&&sizeof(ChordOwn)%32==0,"chord audition alignment");
static inline u32 eu_length(EuPad p){return (p.pattern&255u)+1;}
static inline u32 eu_pulses(EuPad p){return (p.pattern>>8)&511u;}
static inline u32 eu_rotation(EuPad p){return (p.pattern>>17)&255u;}
static inline int eu_native(EuPad p){return (p.pattern>>26)&1u;}
static inline int eu_enabled(EuPad p){return (p.pattern>>25)&1u;}
static inline u32 eu_base(EuPad p){return p.velocity&127u;}
static inline u32 eu_mode(EuPad p){return (p.velocity>>8)&15u;}
static inline u32 eu_depth(EuPad p){return (p.velocity>>16)&127u;}
static inline u32 eu_gate(EuPad p){return (p.velocity>>24)&63u;} /* quarter steps, 0 = one step */
static inline u32 eu_dynamics(u32 base,u32 mode,u32 depth){return base|(mode<<8)|(depth<<16);}
static inline u32 eu_dynamics_gate(u32 base,u32 mode,u32 depth,u32 gate){return eu_dynamics(base,mode,depth)|((gate&63u)<<24);}
static inline int eu_pad_valid(EuPad p){return !(p.pattern>>27)&&!(p.velocity&~0x3f7f0f7fu)&&eu_base(p)>=1&&eu_mode(p)<=9&&eu_depth(p)<=100&&eu_pulses(p)<=eu_length(p)&&eu_rotation(p)<eu_length(p);}
static inline EuPad eu_pack(u32 len,u32 hits,u32 rot,u32 vel,u32 on){EuPad p={(len-1)|(hits<<8)|(rot<<17)|(on<<25),vel};return p;}
static inline int eu_memory(u32 p,u32 n){return p && !(p&31) && p+n>=p && ((p>=0xc0000000u&&p+n<=0xc8000000u)||(p>=0x30000000u&&p+n<=0x30040000u));}
