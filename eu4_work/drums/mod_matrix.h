/* CH11: drum-synth destinations in the native Mod Matrix.
 *
 * The native one-shot matrix stores routes per pad cell as (destination key,
 * slot, source, amount). The synth parameters reuse the existing synth knob
 * keys, so a route names "parameter n of this pad's synth"; the engine the
 * routes were made for is remembered separately (KickKnob.reserved bits 4..7)
 * and routes made for another engine stay saved but silent.
 *
 * M7 keeps synth routes in the native root's own route list (root+590, 12-byte
 * records {f32 amount, u16 key, u16 source, u8 slot}, count root+5FC, nine
 * records). The native voice binder ignores keys above 0x57, so these records
 * never reach a native parameter. */
#pragma once
#define MOD_PARAMS 8u
static const unsigned short mod_keys[MOD_PARAMS]={0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9,0x1b0};
/* Saved destination names. Engine-neutral on purpose (see above); never reuse
 * a token for a different parameter position. */
static const char *const mod_tokens[MOD_PARAMS]={"bento_synth_p1","bento_synth_p2","bento_synth_p3","bento_synth_p4","bento_synth_p5","bento_synth_p6","bento_synth_p7","bento_synth_click"};
static int mod_index(unsigned key){for(unsigned i=0;i<MOD_PARAMS;i++)if(mod_keys[i]==key)return (int)i;return -1;}
/* Parameters per engine: Kick seven knobs plus Click, Tom seven, Snare/HiHat/Clap five. */
static unsigned mod_count(unsigned engine){return engine==1||engine==11?8u:engine==9?7u:engine==3||engine==5||engine==7?5u:0u;}
static int mod_low(unsigned engine,unsigned j){return (engine==1||engine==9)&&j==0?25:0;}
static int mod_span(unsigned engine,unsigned j){return (engine==1||engine==9)&&j==0?155:100;}
#define MOD_RECORDS 9u
#define MOD_LIST 0x590u
#define MOD_COUNT 0x5fcu
#define MOD_ENGINE(r) ((r)&15u?(r)&15u:1u)
#define MOD_TAG(r) (((r)>>4)&15u)
