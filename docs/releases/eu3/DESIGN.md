# EU3 integration and ownership

EU3 branches from EU2 2b06731 on feature/euclidean-arrow-controls. EU1/EU2 and
exact K16 remain preserved. It fixes the maintainer-observed access conflict:
native SEQ double-tap reaches the piano roll before EU1's gate could open.
EU3 removes custom SEQ double-tap handling completely.

## Native view, not a replacement page
The existing one-shot SEQ view stays on page 27. The adapter at 0815D57E handles
the native arrow event branch before its original index switch. Left=0,
Up=1, Down=8, Right=9: native dispatch originally called 0815BC4C(-1/+1) for
0/9 and page scrolling for 1/8. EU3 reuses the exact 0815BC4C action on Up/Down.
Right enables the selected pad and switches its encoder bank; Left restores
native controls while retaining the current B(view,113E0) Step/Sequence flag.
PROJ+Left explicitly disables the selected pad's generator. Other views/types
fall back unchanged. The physical arrow mapping still needs maintainer confirmation.

Five descriptors 190..194 serve Pad/Length/Hits/Rotate/Velocity. Mode/preview/
return controls are removed. No GenericProperties Euclid navigation remains.
After native SEQ header refresh, EU3 replaces the first six bar slots (sixth
blank) and their view-side key/value binding arrays at 113AC/113BC. The native
parameter widget configuration and event path are retained. Native notes/grid
and selection/hold/edit behavior remain present.

## Relocated K16 UI APIs
EU3 independently copies step_lock_ui and kick_ui sources. Exact K16 compiler
symbol maps locate exported APIs; guarded branch redirections lead to appended
EU3 implementations. Original K16 wrappers/XML hooks and fixed PROJ/clear entry
addresses remain callable. The input is still hash-guarded exact K16, and the
combined manifest reverses to stock. Historical sources are not edited.

Lock slots move from bar indices 4/5 to 6/7, including static header keys,
view binding arrays, values, titles, error overrides and PROJ pickers. Native
Sequence mode is not overwritten when the Euclidean bank is off. EU mode permits
the same selected-note lock editing while either native encoder choice is set.
Lock codec, stored raw values and synth DSP mapping remain byte-compatible.
Synth lock text now matches instrument units: kick Hz; snare 80+12*raw Hz;
hi-hat 100+107*raw/10 Hz; remaining synth controls percent. Missing synth locks
show the actual background value rather than hiding it behind --. Existing step
asterisks remain the lock indicator.

The instrument editor clears both native text overrides and titles/config for
all zero-key controls before redrawing a synth. This addresses kick encoders
7/8 leaking stale values into five-parameter snare/hi-hat layouts. Existing
sample fallback, display cleanup and audio engines remain intact.

## Generated hit lock transport
EU3 uses the original M7 lock_pending/lock_route APIs, resolved by compiling the
exact K16 symbols into generated lock_api.h. At a generated grid boundary one
bounded pass over the native clip note cursor gathers existing lock words for
all firing drum pads. A six-word private cursor copy uses native 08095DA0 and
leaves the native scheduling index unchanged. Native stored note steps use 960
units; match them against each pad's own cycle step. Only matching type-1 notes
with a lock word are used; maximum 511 records per grid boundary. Native queue/
voice routing then transports the same lock word as ordinary hits, with pending
state cleared after each generated hit. Unlocked hits do not inherit prior locks.
This does not create triggers or add probability/offset/condition behavior to
generated hits. Native A–D automation and preserved manual note storage remain.

## Memory and validation boundaries
Existing TF2 heap end 24040000, all native MPU/startup/stack/vector/recovery
boundaries and original bootloader/controller remain unchanged. Ui grows by
two words to 1456 bytes, still below shared control at 24041FC0. The EU2 dynamic
44064-byte bank and cache-line ownership are unchanged. M4 appended code remains
bounded below 081CC000, within the existing application flash region; native
flash permissions are not enlarged. Audio code remains below 080E0000.

Tests execute actual compiled arrow adapter, parameter widget functions for
model switching, lock codec/editing, native time conversion, note cursor reads
and lock-pending transport. Display services, model/allocator/XML services and
final queue sinks are fixtures. The E3 regression runner updates one inherited
header-location assertion from offset 8 to 12; no production workaround is
introduced for tests. Physical display, CPU deadlines, cache coherence and
filesystem round-trip remain device checks. K14 remains the last recorded
hardware-confirmed boot/playback baseline. Maintainer confirms E1 boots, snare sonic
fix satisfactory and hi-hat marker not found; no E1 Euclid behavior was tested
because of the native SEQ gesture conflict.

Clip settings remain slot-based: Copy/Move/Delete and generator-control Undo
are not integrated, as disclosed in EU2 and EU3 instructions.
