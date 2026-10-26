# P14 implementation

User: melodic Event encoders 7/8 become two p-lock controls; PROJ chooses
targets; move encoder-8 automation visibility into the burger menu. User also
asks about performance. New feature is based on delivered P13; hardware
validation remains pending.

M4: melodic_lock_ui.c uses native piano selection IDs (08174D70), reads
native 24-byte note containers, reserves complete results, takes native Undo
(081338DC), then publishes one bulk edit (08136544). It preserves existing
lock codec/XML, lock conditions and all note fields. Native descriptor keys
1DA/1E4 are reused through the existing registry owner; no new registry IDs.
Only the ordinary Event bank is rebound. Chord/Euclidean banks retain priority.
The native F9 menu has nine cells: Event replaces Clear Auto with Show/Hide
Automation, while the Automation tab retains Clear Auto. No tenth cell.

M7: legacy sampler lock code only accepts root vtable 080AC66C, so exposing
UI alone would not make Wavetable/Granular locks audible. A separate melodic
path tags only the primary queue (B8/4D4C), captures the native generic note
entry at 0807EBE0, attaches to the initialized voice at 0807C0F6, and scopes
filter evaluation around the native per-voice render call at 0807A80E. Filter
parameters are native voice+5C4/60C. Native source/range/modulation evaluation
is retained via the original evaluator at 080D1F00. Level scales the voice
buffer before native pan/mix; Pan uses the native voice-local +18 value.
Unmodified sampler evaluation is chained through 080D1100. No global synth
base edit, per-block allocation, or extra oscillators. Decoded filter/resonance
words and gain are cached on note start, not unpacked per sample.

Allocation: MelAudio is a separately checked 3,200-byte M4 bump allocation,
published through previously unused EuBank.reserved[0]. Its first 64 bytes
are M4-owned track registration; subsequent cache lines are M7-owned.
EuBank's existing layout/bytes, fixed memory boundaries, MPU and stacks stay
unchanged. Tracks are registered on Event entry, completed project load, and
before PLAY, so saved locks do not require opening SEQ first.

New code lives in checked zero application caves 080D4400..080D5800 and
080DAC00..080DC000. Both bounds and original bytes are guarded, and merged
manifest reversal returns the exact stock and K16 images. No historical K16
source, bootloader or controller change.

Tests use the native encoder-turn path, real piano selection and note storage,
XML, two voices, the actual Wavetable constructor and note-on entry, original
filter parameter evaluation and real audio gain buffers. Model/engine queues
and allocation services are controlled fixtures. The full-page render fixture
was inconclusive; native widget titles/bindings are checked by the ARM tests.
No claim of hardware UI appearance or measured device CPU.
