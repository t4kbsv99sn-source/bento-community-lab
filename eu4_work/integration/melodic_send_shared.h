#pragma once
/* P15: pre-Track-FX note sends. M4 allocates; M7 alone owns this block. */
#define ML_FRAMES 1024u
typedef struct {u32 native[5];float left[ML_FRAMES],right[ML_FRAMES];} MelBuffer;
typedef struct {
 u32 root,input,router,strip,active,ready,n,pad;
 u32 level[6],duck[28];
 MelBuffer unlocked[2],locked[2];
} MelSendTrack;
typedef struct {
 u32 current,source,voice,pad;
 MelSendTrack tracks[8];
 MelBuffer isolated,weighted,post;
} MelSends;
