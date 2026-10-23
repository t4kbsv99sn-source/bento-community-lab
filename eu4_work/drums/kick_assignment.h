/* BENTO_MOD K5: UI-owned assignment table, audio-owned DSP state stays separate.
 * 128 current pads; updates replace by handle or oldest entry. 16-byte entries
 * commit using an even sequence after a DSB; readers reject torn entries.
 * Header + entries fit 43500..43D1F, before diagnostics at 43E00. */
typedef struct {volatile unsigned sequence,handle,enabled,reserved;} KickAssignment;
typedef struct {volatile unsigned magic,serial,pad[6];KickAssignment entries[128];} KickAssignments;
#define ASSIGN ((KickAssignments*)0x24043500u)
#define ASSIGN_MAGIC 0x3541534bu
