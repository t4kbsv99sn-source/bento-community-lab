# Bento generative sequencing research — 21 October 2026

Research only: no new firmware changes or hardware claims. TF2 remains the
separate Track FX test branch; K16 remains its baseline. Source candidates below
were inspected, not compiled or integrated into Bento.

## Best source candidates

### Westlicht PER|FORMER — embedded sequencer, root MIT license
Repository: https://github.com/westlicht/performer
Software license: https://westlicht.github.io/performer/license/
Manual: https://westlicht.github.io/performer/manual/

Inspected files:
- src/apps/sequencer/engine/generators/EuclideanGenerator.cpp
- src/apps/sequencer/engine/generators/Rhythm.cpp and Rhythm.h
- src/apps/sequencer/engine/generators/RandomGenerator.cpp
- src/apps/sequencer/engine/ArpeggiatorEngine.cpp and ArpeggiatorEngine.h
- src/core/utils/Random.h
- LICENSE

Euclidean generator has Steps, Beats and Offset, and writes generated values
through its SequenceBuilder. Rhythm.cpp implements a Bjorklund-style algorithm
and credits an earlier Bitbucket implementation: trace that component's
provenance before direct copying. A small independently written Euclidean core
may be simpler than importing Pattern/SequenceBuilder abstractions.

RandomGenerator uses a reproducible seed, smoothing, bias and scale. This is a
useful model for previewing variations before committing them to native steps.
ArpeggiatorEngine accepts noteOn/noteOff/tick and exposes NoteOn/NoteOff events;
it uses fixed arrays (eight held notes) and a bounded 16-entry event queue.
Its model, groove, queue, logging and clock dependencies need adaptation.
Most relevant overall code reference for an embedded Bento note-processing layer.

### Mutable Instruments Plaits — compact arp note-order component, MIT header
Repository: https://github.com/pichenettes/eurorack
File: plaits/dsp/engine2/arpeggiator.h

Small note-index/octave generator with Up, Down, Up/Down and Random. It does not
handle held MIDI notes, transport, note duration or recording. Requires valid
positive note count/range and a configured range after Init. Random mode has an
unbounded rejection loop to avoid repeating the same note/octave: replace with
bounded behavior before use in a real-time callback. Good building block or
algorithm reference, not a complete ready-made MIDI arpeggiator.

### Mutable Instruments Marbles — looping random variation, MIT headers
Files: marbles/random/random_sequence.h and random_stream.h in the same repo.

RandomSequence has a 16-value loop/history, replay, adjustable length and Deja Vu
behavior. Useful for repeatable randomness, controlled mutation and frozen
phrases. It depends on RandomStream, random generators, stmlib and standard
algorithm helpers. We need the small sequence logic, not the full CV module.
Marbles is a source reference for the musical concept; do not claim it is the
same implementation as the Torso T1.

### MIDIpal — complete MIDI examples, inspected files GPL-3.0-or-later
Repository: https://github.com/pichenettes/midipal
Manual: https://pichenettes.github.io/mutable-instruments-diy-archive/midipal/manual/
Files: midipal/apps/arpeggiator.cc, apps/randomizer.cc, event_scheduler.h.

Arpeggiator includes note order, octave range, latch, clock events and transport.
Randomizer processes notes, velocity and CC. Scheduler illustrates delayed note
events. This is compact embedded code but AVR/application-specific; do not assume
all Mutable code is MIT. Prefer permissive components for a direct Bento port,
and use these GPL files as behavior references pending any reuse decision.

### Deluge community firmware — extensive feature reference, GPLv3 family
Repository: https://github.com/SynthstromAudible/DelugeFirmware
File: src/deluge/modulation/arpeggiator.cpp (78,406 bytes at inspected revision).
License: repository LICENSE and source header.

Contains drum/kit/melodic arpeggiators, ratchet scheduling, repeats, randomized
parameters and locked random values. It is substantially coupled to Deluge's
playback/model systems. Useful for transport/retrigger behavior and edge cases;
a whole-file port would be a poor first step. Ratchets here do not by themselves
establish a complete MPC-style live note-repeat implementation for Bento.

Exact inspected content identifiers and hashes are saved in the adjacent
GENERATIVE_SOURCE_INDEX.json. Third-party source remains outside production
modules; no third-party implementation was silently copied into firmware.

## Torso T1 workflow ideas (official current documentation)

Primary documentation: https://docs.torsoelectronics.com/t1/introduction/

1. Rhythm generation: Steps, Pulses, Rotate and Division work together. Generate
   a rhythm, manually adjust hits, then edit selected steps.
   https://docs.torsoelectronics.com/t1/core-concepts/euclidean-rhythms/
   https://docs.torsoelectronics.com/t1/core-concepts/per-step-editing/
2. Note Repeater: extra triggers follow an existing pulse. Repeats controls count,
   Time controls spacing, Ramp changes velocity and Pace accelerates/decelerates.
   https://docs.torsoelectronics.com/t1/core-concepts/note-repeater/
3. Repeatable randomness: each assigned destination gets its own 16-step
   modulation sequence. Amount, variance, rate, phase, slew and random lock are
   distinct concepts. Probability decides whether a note occurs; random
   modulation changes its attributes. Some destinations advance per cycle.
   https://docs.torsoelectronics.com/t1/parameter-reference/setup/random-rate/
4. Temporary Control: momentary performance changes revert on release. This
   maps well to Bento's existing hold workflow, but needs a deliberate new
   binding and audible-value overlay. Do not simply overwrite saved values.
   https://docs.torsoelectronics.com/t1/miscellaneous/temporary-control/
5. Cycles: track variations unfold across repeated passes without changing the
   entire pattern. Bento's existing A:B condition loop tracking is relevant,
   but does not constitute a full per-cycle parameter engine.
   https://docs.torsoelectronics.com/t1/core-concepts/cycles/

These are workflow inspirations, not a claim that T1 firmware source is available
for reuse or that any Torso code has been inspected.

## Proposed Bento stages — engineering assessment, not verified integration

1. Euclidean clip generation. Select one one-shot sound, choose pulse count and
   rotation against the existing clip length, preview, then Apply to ordinary
   native trigger events. Leave other sounds intact; preserve untouched note
   locks and native automation. Native editing/save/load can then be retained.
   Before implementation, verify native event insertion/deletion and undo hooks.
   Preview must not destroy existing notes; cancel should restore original data.
2. Bounded randomization. Select targets such as velocity, timing or pitch; set
   ranges, seed and amount. Regenerate/preview/apply. For pitched tracks constrain
   pitch to the selected scale; for drums do not randomize sound identity unless
   explicitly requested. Keep rhythm generation and sound randomization distinct.
3. Live note repeat. Hold a playing pad in Repeat mode; tempo divisions determine
   repeated hits. Start with straight/triplet divisions and velocity response.
   Use the existing musical clock rather than UI milliseconds or a second clock.
   Later support recording repeated hits through native recording.
4. Per-step ratchets. Repeats belong to a stored step. Reuse the same event timing
   core as live repeat, with a distinct event source and persistence strategy.
   Keep the existing two sound-parameter lock slots available.
5. Melodic arp. Manage held notes, order, octave range, gate, latch, transport and
   scale behavior. Westlicht is the strongest complete embedded starting point;
   Plaits supplies a smaller note-order-only alternative.
6. Runtime Euclidean and evolving randomness. Per-pad pulse/rotation changes,
   frozen random loops, mutation, temporary performance controls and cycles.
   Independent per-pad loop lengths require a separate runtime timing assessment.

The easiest Euclidean first version shares the native clip length. A seven-step
pattern printed into a sixteen-step clip will reset at the clip boundary; it is
not true independently running seven-step polymeter. Do not promise independent
drum cycle lengths merely because a Euclidean pattern generator exists.

## Shared integration rules to resolve during implementation
- Single native musical clock and explicit fixed-capacity queues; no allocation
  or unbounded loops in the real-time path.
- Keep generated notes' track/pad, velocity, timing, duration and lock metadata
  together; route them through native mute, voice allocation and note-off paths.
- Proposed ratchet behavior: condition/probability evaluated once for the parent
  trigger; child hits inherit its sound locks. This is a design proposal, not an
  assertion about current firmware behavior.
- Stop, pad release, track/project change and transport jumps must cancel the
  appropriate pending events and finish their outstanding notes.
- Live Repeat, per-step Ratchet and delayed echoes are distinct behaviors despite
  sharing scheduling machinery. Do not select one accidentally through naming.
- PROJ+pad is already used for drum mutes and step-lock clearing in different
  views. Do not reuse that combination for note repeat without a binding review.
- Save seeds and frozen random values if deterministic replay is promised.
- Event logic should cost less than audio DSP in principle, but dense repeats
  trigger extra voices and can increase Bento's actual audio workload.

Recommended first implementation: native Euclidean clip generation and bounded
velocity randomization, then tempo-synchronized live note repeat. No new firmware
was requested or produced by this research task.
