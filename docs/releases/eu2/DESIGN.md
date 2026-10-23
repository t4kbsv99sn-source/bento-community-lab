# EU2: live native-clock Euclidean playback

Branch feature/euclidean-live starts from EU1 release d545913. EU1 remains in
its own directory/tag. EU2 retains K16 and TF2 but adds M7 timed generation;
it is no longer byte-identical to TF2's M7 application. Original bootloader,
controller, native MPU/vector/stack regions and the TF2 heap boundary stay
unchanged. All patches remain inside the application with exact stock reversal.

## Ownership
Ui remains 1448 bytes at 24041A00, now bounded below 24041FC0. The aligned
32-byte EuControl at 24041FC0 is M4-written/M7-read, inside TF2's existing UI
reservation. Startup already clears this full reservation, without FP use.
Eight descriptor IDs 190..197 are constructor-verified free; setup refuses
collisions. Mode 2 of GenericProperties 1A uses these eight controls and preview.

M4's checked native bump allocation supplies one aligned 44064-byte EuBank:
32-byte header; two 128-entry tables of 160-byte EuRecord (active and pending);
16 192-byte M7-only EuRuntime entries. M4 initializes the complete bank before
publishing its pointer, then never writes the runtime region. Project finish
replaces active settings with pending under a header seqlock and advances the
epoch. Each record has its own serial and holds owner, clip row and 16 pairs of
32-bit packed settings/velocity. M7 invalidates M4-owned cache lines before
reading and rejects invalid/torn data. No cache line is shared between owners.
No allocation, XML call, model lookup or UI draw occurs on the audio thread.

Native heap cursor/end 3000004C/30000048 are preflighted. Pointer ranges accept
aligned native SDRAM/D2 RAM only; the bank is reusable for the application
lifetime. No additional fixed SRAM or heap-end literal change is introduced.
Capacity is 128 clip records and 16 runtime contexts; allocation failure leaves
native playback available. Allocation is not evidence of hardware headroom.

## Scheduling and routing
08060820 is the native timed-note processor, receiving sequence, native clock,
frame offset/count and router as the fifth stack argument. An integer/FP
preserving wrapper runs live_render first, then replays the original prologue.
Native clip pointer 86C0 resolves the actually playing row among 16 slots of
848 bytes starting at sequence+240. Owner is sequence+12, and playing byte+20.
UI selection cannot choose the playing clip.

M7 reads the native step-size table 080BDBEC (indices 0..14), rounds scale*960
as native scheduling does, and uses the native 64-bit time conversion functions
080A21C0 and 080A2200. Default sixteenths are 240 playback-clock ticks, while
stored note positions use 960 units per step. Native signed division 080A34F4
sets the initial step near the current position. No UI millisecond timer drives
music. The timing fixture runs the actual native converter at 120 BPM.

A runtime keeps its origin and monotonically increasing step count across
native loop-start timestamp changes. Each pad evaluates step modulo its own
length. New settings are sampled for subsequent native timed-note chunks and
thus affect the next unevaluated step. Length changes retain the shared running
step count; they do not restart the clip. Grid changes recompute the cadence.
Work is bounded to 32 candidate grid steps per call. Duplicate callbacks do not
repeat a hit. Runtime/owner/row/epoch changes restart context. 08061740 chains
the existing condition-counter hook and resets generator phase only when native
step+14 is negative (launch/restart); ordinary wraps keep phase.

Hits call the real native 0805F8E0 route with drum index, velocity and native
sample offset. That retains ordinary sound routing, MIDI forwarding and pad
notifications. The native probability gate at 08060B64 skips native sequence
hits only for pads in the current valid generator snapshot; all other cases
chain the existing 080D2000 condition gate. Manual pad audition bypasses this
gate as before. Native notes/IDs/locks are not rewritten. Generated hits do not
currently inherit their conditions/locks. Native automation A–D is unmodified.

## Saving and clip operations
The known generic object params hooks call live_save/live_load for one-shot
tracks (native type 14), beside existing Track FX hooks. Versioned named
bento_eu2 attributes store pairs keyed by clip row/pad. Native XML services are
used; there is no extra project file. Missing/invalid settings become Manual
on project finish. Track FX's own versioned attributes remain separate.

This is explicitly slot-based persistence. Native Copy/Move/Delete Clip operations
are not yet hooked; settings do not follow these operations and must be managed
at the destination slot. Controls are not covered by native Undo. Displayed
manual SEQ steps remain the preserved manual layer. These limits are disclosed
in installation instructions, not represented as completed clip lifecycle work.

## Validation boundaries
Tests execute compiled UI/renderer/adapters, real native clock conversion and
note-message construction. Model properties, allocator service, XML attribute
services and final engine queues are fixtures. The patched entry test checks
the fifth argument, GPR/SP and FP preservation; gate tests check enabled-pad
suppression and chaining for native conditions. Playback tests compare actual
hit positions for 7 against 16 across a 48-step interval, separate clip settings,
step-size changes, stops, launches, live edits and duplicated callbacks.
Inherited tests cover MPU/startup, Track FX DSP and existing K16 controls/synths.
These are not full hardware, disk, cache-coherence or audio-deadline emulation.
Hardware checks remain necessary; last maintainer-confirmed baseline remains K14.
