# TF2: independent Track FX branch from K16

Branch: feature/k16-track-fx. Baseline: release/k16-1.6KG, commit 82f3910.
K16 main SHA256: 5e72971b31388201454a71b0be7cc61ad40915bda3a75e635d104dd89346a03d.
Hardware validation of K16 itself remains pending; K14 is the last maintainer-confirmed
boot/playback baseline. TF2 does not inherit K8 or F1 firmware bytes.

## Preserved DSP, new bridge
Reuse the preserved DaisySP-LGPL biquad/compressor and DaisySP MIT soft-clip
processing in fx1_work/track_fx. Retain the sound defaults, stereo linking,
Auto Makeup, smoothing, range checks and bypass behavior. Licenses and pinned
upstream revisions remain beside the sources. tf2_work holds independent source
so later K16 fixes can be merged without overwriting the preserved experiments.

The native per-track hook is 080A0510, after gain has populated that track's
owned scratch and before native pan/ducking/sends/summing. It does not process
the shared input or replace buffers. At most 1024 frames per channel are accepted.
No allocation, filesystem calls or UI widgets occur in the audio callback.
The DSP bank is initialized lazily when an effect is first enabled. Unchanged
mailbox serials require only a header cache invalidation, rather than copying
all eight settings every callback.

## Avoid known failure classes
The old F1 UI state at 2403A400 was outside the native M4's permitted SRAM range.
K9's MPU repair did not fix the full hardware boot, so there is no claim that
this was the only cause. F1 also used floating-point save/restore wrappers even
at early startup. TF2's M4 wrappers and both startup wrappers are integer only.
Native M7/M4 MPU setup, vector tables, stacks and recovery/disk region stay
byte-identical to K16. No permission expansion or bootloader code is added.

Reserve exactly 8192 more bytes by changing the same three application heap-end
literals from 24042000 to 24040000. This stays inside the native M4 region
24040000..24080000. K16 state from 24042000 upward is unchanged.

| Range | Owner/use |
| --- | --- |
| 24040000..24041440 | M7 DSP bank: 5168 bytes, 5184 reserved |
| 24041440..240416C0 | M4-written settings mailbox, 32-byte aligned |
| 240416C0..24041A00 | M7-only metadata, 832 reserved |
| 24041A00..24042000 | M4-only UI/gesture state, 1536 reserved |

Compile-time bounds, M7 bank-size checks and explicitly separate startup clears
guard ownership. The M7 never writes the mailbox/UI state; the M4 never calls
the DSP. The sequenced mailbox rejects torn, invalid and odd-serial updates.
M7 cache maintenance does not share state-owner cache lines.

Application code: M7 adapters at 080DC000 and DSP from 080DC800, bounded below
080E0000; M4 adapters at 081C0000 and UI from 081C0800, bounded below 081C4000.
Builders enforce the exact K16 hash, unused zero M7 cave, nonoverlapping writes,
four-byte output alignment, application bounds and byte-exact reversibility.
The combined manifest reverses all the way to exact original stock.

## Navigation and native controls
Intercept the outer consumer at 0813F98C and chain K16's original consumer when
unhandled. Single press is immediate and unchanged. A release within 300 ms can
arm the second press for 350 ms, only while the normal Tracks page remains open.
TRACKS-hold pad actions, Shift and other buttons cancel the gesture. Native
HAL_GetTick at 081152C0 confirms the counter at 3001FE2C; unsigned subtraction
handles wrapping. Consume the second press/release; subsequent TRACKS press
returns normally. There is no timer, event-loop delay or delayed single press.

Reuse native GenericProperties page 1A only while our explicit mode is active.
Ordinary navigation, including to page 1A itself, clears that mode. The native
registry constructor is exercised in tests; the 19 FX keys do not overlap the
ten K16 synth descriptors. Refuse nonmatching occupied descriptors.

Project save/load hooks chain the actual K16 targets 081BB200/081BB300/081BA000.
Named versioned bento_fx attributes preserve the prior settings design. Two
step-lock encoders and native automation A–D are unchanged; new FX parameters
are not added as automation/lock targets in this version.

## Validation scope
See saved results. Tests execute the actual compiled startup, native MPU setup,
native mixer, native GenericProperties constructors and encoder event bubbling.
Heap services, SD/XML services, physical display and some model lookups are
controlled fixtures. M4 SRAM permission enforcement is explicit because Unicorn
does not itself enforce the MPU. Early startup is tested with FPU access off.

The inherited test fixture's flash mapping ended at 081C0000. The branch runner
extends this test-only mapping to the declared application end 08200000; firmware
flash/MPU bounds are not extended. Initial fixture failures were unmapped writes,
not application execution failures. Historical sources/failed binaries remain
preserved separately. Actual device boot, audio deadlines and heap headroom are
not established by software tests.

## Rebuild
Use the repository's pinned Python dependencies and g++:

    python tools/build_tf2.py --stock /path/to/stock/bento1.bin --out build/tf2 --test

The wrapper first reproduces exact K16, then recompiles this separate module.
All LGPL sources, bridge sources, freestanding headers and linker scripts are
included for replacement/relinking; supplied stock remains a private input.

Merge source commits into the desired branch later and rebuild. Do not merge
finished binary images. Keep these RAM/code reservations and hook ownership in
view when future work changes K16's current layout.
