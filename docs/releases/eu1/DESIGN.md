# EU1 integration

Branch feature/euclidean-sequencer starts from a07ecc0, the TF2/K16 feature
branch plus generative-sequencing research. EU1 adds only M4 application UI
and native note editing. The entire first 0xC0000 bytes (M7 application) match
TF2 exactly, SHA256 748bcbc3e9c338d46f592fed438e31e1190f043c0a2f0e5aa78484ecdec8859c.
No bootloader, MPU table, vector, controller or native stack limit changes.

## State and UI
Existing TF2 reservation 24040000..24042000 is unchanged. UI state begins at
24041A00, occupies 1448 bytes within its 1536-byte allowance; Euclid starts at
24041F6C. No floating-point instructions enter M4 adapters or early startup.
New mode 2 uses native GenericProperties page 1A, six controls and a text preview.
Mode 1 remains Track FX. Native descriptor constructor confirmed six empty
slots 190..195; registry setup refuses collisions instead of overwriting them.

SEQ button index 11 shares the existing double-tap dispatcher with TRACKS
index 2. First taps remain immediate. A release within 300 ms followed by a
matching second press within 350 ms opens the custom page. Shift, pad gestures,
other buttons and long holds cancel arming. EU1 requires page 27, valid captured
one-shot context and current owner/length checks. The native step-header entry
0815C27C calls context capture then chains the exact K16 adapter 081B7008.

## Editing
The original integer distribution uses modular buckets; positive rotation
moves hits forward. Current native clip length is used, 1..256 steps, with
960 native ticks per step. Preview changes do not alter notes. Apply validates
the current context and preflights the native 511-event capacity before editing.
Only type-1 events for the selected pad inside the clip are affected. Retained
events are byte-preserved, including duplicate hits and microtiming. New events
use native Always byte zero, requested velocity, no locks and native project IDs.

Root sequence lookup 0812DFE8 resolves the authoritative native event container.
Native bulk deletion 08136FB4 requests one undo snapshot, removes events and
publishes audio/UI notifications. Add-only edits explicitly request snapshot
081338DC. New IDs come from 0812E070; upsert/publish 08136544 sends the actual
native audio commands, and C7 refreshes the sequencer. Native project saving
therefore stores ordinary notes, with no Euclidean sidecar or runtime audio hook.
No-op edits allocate nothing and create no undo entry.

The native UI bump allocator 08104C08 supplies one reusable 0x3004-byte temporary
event container (rounded to 0x3020 by the allocator). Actual cursor 3000004C and
end 30000048 are checked first to avoid its fatal overflow path. Allocation is
not on the audio thread. Project replacement invalidates captured context.

## Evidence and limits
Compiled ARM tests execute the real native registry/page setup, note containers,
ID allocation, bulk delete, native publication and patched capture entry.
Model-property services, native undo storage allocation, engine queue and display
services are fixtures. Tests prove the requested snapshot and queue contents,
not a complete device Undo cycle, filesystem save/reload or physical screen.
Inherited tests cover Track FX, MPU/startup, previous controls and K16 regressions.
Exact stock reversal and repeat-build identity are required for packaging.
Hardware testing remains pending; K14 is the last maintainer-confirmed baseline.

Independent per-pad periods, melodic tracks, non-960 grids and live audio-rate
Euclidean generation are outside this first build. Existing native note metadata
is preserved where a generated hit already exists; New Vel applies only to added
hits. Controls reset on context changes and are not persisted as generator state.
