/* BENTO_MOD K7: UI-owned per-sound parameters. Activation remains K6's
 * exact native descriptor/content recognition; no file-ID assignment. */
typedef struct {volatile unsigned sequence,handle;volatile unsigned char values[7],reserved;} KickKnob;
typedef struct {volatile unsigned magic,serial,reserved[6];KickKnob entries[128];} KickKnobs;
#define KNOBS ((KickKnobs*)0x24043500u)
#define KNOBS_MAGIC 0x35424e4bu
static const unsigned char kick_defaults[7]={55,65,45,65,55,25,25};
static const unsigned short kick_keys[7]={0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9};

/* K15: UI-owned Click extension, one byte per original mailbox slot. Owns
 * aligned cache lines D80..DFF, after UI/cleanup metadata and before M7 diag. */
#define CLICKS ((volatile unsigned char*)0x24043d80u)
#define CLICK_KEY 0x1b0u
