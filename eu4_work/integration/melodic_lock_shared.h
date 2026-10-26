#pragma once
/* Separately allocated on M4. Config is M4-owned; all later lines M7-only. */
#define ML_MARK 0xb8u
#define ML_SIGNATURE 0x4d4cu
#define ML_ENTRIES 128u
typedef struct {u32 voice,root,word;float gain;u32 filter,resonance,decay,release,delay,reverb;} MelVoice;
typedef struct {
 u32 serial,owners[8],next,config_pad[6];
 u32 queue,word,note_root,note_word,voice,active_word;float gain;u32 pad;
 u32 active_filter,active_resonance,context_pad[6];
 MelVoice entries[ML_ENTRIES];
 u32 sends;u32 send_pad[7];
} MelAudio;
_Static_assert(sizeof(MelAudio)==5280,"melodic lock allocation/cache ownership");
