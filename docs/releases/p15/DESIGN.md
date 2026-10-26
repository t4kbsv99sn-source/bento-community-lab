# P15 melodic targets and interaction rules

Based on P14. Maintainer approved per-note sends and the base/lock/modulation priority.
New Analog/Wavetable/Granular picker targets: Env 1 Decay, Env 1 Release,
Delay Send and Reverb Send. Existing target encodings, native note size, two
slots, Undo and project XML are preserved. Multisample retains its inherited
sampler implementation; its shared send semantics are not upgraded here.

## Envelope evaluation

Env 1 Decay and Release are native voice+200/+240 parameters. Decay is evaluated
when the phase starts; Release at note-off, including outside the active voice
render context. Specific native phase call sites 0808773A/08087AAE use a hashed
voice lookup. Each voice retains its lock until reuse. Env 2 stays native.
The native parameter evaluator receives a temporary parameter copy with the
locked base, without its direct automation pair. Three user modulation pairs
remain, and the native range clamp remains. Source objects/routes are unchanged.
Filter/Resonance retain P14's equivalent native evaluation. Existing Level is
additional note gain; Pan is native voice pan. Track fader remains independent.

## Per-note send routing and the insert point

Native generic synth sends exist only AFTER all voices have been mixed. Editing
those gains cannot implement per-note locks. P15 isolates each voice's native
output before it reaches the track sum, then restores exactly that output to the
dry sum. While a send-locked voice is active, two stereo submixes per effect
hold unlocked contributions and locked, weighted contributions. Each locked
voice owns its own amount; an unlocked voice continues using the automated
native track send amount. Either effect may be locked independently.

**While send locks are active on a generic synth track, its wet sends tap before
shared Track FX (EQ/compression/clipper).** They retain native voice filtering,
envelopes, note Level/Pan, the track fader ramp, balance and duck/mute. The dry
track still uses its normal Track FX. This also means the unlocked voices on
that track use the pre-Track-FX send tap during that time. Without active send
locks, exact native post-Track-FX sending resumes. Separate nonlinear per-voice
Track FX would require extra DSP instances and is not implemented.

The native send smoother advances once per effect. Fader and duck state are
snapshotted before native dry processing and replayed on temporary copies for
wet submixes. Original automation/model values are never overwritten. Effect
buses are only added to; old delay/reverb tails are not cleared. New note send
locks replace the shared direct send amount for that note. There is no new
per-voice send modulation destination: native envelope/filter matrix routes,
including Mod Seq sources, remain; shared send automation does not override
a note's send lock.

## Memory, code and ownership

EuBank remains 46,080 bytes. The separate MelAudio header/voice table is now
5,280 bytes, plus 288,780 bytes of fixed-capacity routing buffers/metadata;
the UI requests 294,060 bytes (native allocation rounds to 294,080). Allocation
and initialization happen once on M4 before publishing the pointer, never in
an audio render. Each buffer supports up to 1,024 stereo frames. Above that
bound routing falls back to native rather than touching out-of-bounds memory.
All post-publication send state is M7-owned. First 64 bytes of MelAudio remain
M4 registration data, with the existing cache ownership.

Melodic parameter code stays at 080D4400..080D5800. Send C code owns
080DAC00..080DBA00, preserving adapters move to 080DBA00..080DC000. Checked
zero cave and no-overlap guards are retained. Native M7/M4 MPU settings,
heap bounds, stacks, bootloader and controller are unchanged.

Native hooks: generic voice loop begin 0807A7C8/end0807AB60; existing context
adapter substitutes only that voice's output stack argument, then adds the
voice back to the normal dry sum. Mixer snapshots 080A050C/0526 and send calls
080A0532/053E. No send locks means original native mixer calls remain chained.

## Validation limits

Tests run actual native envelope phase transitions, parameter/source evaluation,
native gain ramps, mixer/fader/pan/mute, native Track FX and bus mixing under
ARM emulation. Oscillator data in send tests is a controlled stereo signal;
one test exercises the installed voice-output adapter itself. Hardware sound,
real-time CPU load and UI appearance still require device testing. Instruction
counts describe operations, not device CPU percentages.
