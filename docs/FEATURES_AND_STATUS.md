# What this changes, and why

Bento Lab grew out of using Bento as a hands-on jam instrument: fewer touchscreen
trips, quicker track/drum selection, more expressive sequencing, and programmable
drums. These are application-firmware patches on original Bento 1.6.1. We are not
replacing the bootloader or pretending to have the manufacturer's source.

## The useful bits

| Change | What you do | Why it exists / evidence |
| --- | --- | --- |
| Track navigation | Hold TRACKS + top-row pad 1–8 for that track's instrument; bottom-row pad 9–16 for its sequencer. | Reach any track without a touchscreen detour. Maintainer tested. |
| Clip performance | Hold LAUNCH: top row stops the selected clip for each track; bottom row starts it. | Clip control while keeping the previous screen available. Maintainer tested; does not mean stop every clip. |
| Mixer performance | Hold MIXER and use the solo/mute pad layout. The existing mixer state and audio path are reused. | Quick mix changes; earlier screen-only mute bug was fixed. Maintainer tested. |
| Drum selection | From one-shot SEQ, hold INST, select a sound, release to return. If no selection is made, stay in INST. | Less navigation between choosing a drum and editing its pattern. Maintainer tested. |
| Inspect a step | Hold an existing step to inspect/edit without toggling it. | Velocity, offset, probability and locks should be accessible without destroying the trigger. Maintainer tested. |
| Trigger conditions | Extend the existing probability control with repeating conditions. | Make a short pattern vary over several passes. Maintainer reports it works; specific control revisions have had bugs. |
| Parameter locks | Two step-edit encoders 7/8; use PROJ to choose targets. PROJ + step clears its locks. | Give individual hits their own sound. Direct note/voice payloads; ordinary automation A–D remains separate. This is not four new automation lanes. |
| Drum synths | Load the generated Kick/Snare/HiHat WAV selectors into one-shot slots; edit the live synth parameters. | Programmable drums alongside sampled drums. Selectors identify engines; they are not rendered drum samples. Maintainer tested sound and controls. |
| Euclidean patterns | In one-shot SEQ, Right selects the Euclidean encoder bank; Left restores normal controls. Up/Down switch sequences. | Live length/hits/rotation with independent drum cycles, real editable notes and a playhead. Maintainer tested core operation and later visuals/editing. |
| Euclidean dynamics | Encoder 5 velocity shape, encoder 6 depth;7/8 remain locks. | Add accents, ramps and variation. Hit-based modes count actual pattern hits across loops. Maintainer tested mode/depth operation. |
| Track channel strip | Double-tap TRACKS for EQ, compressor/auto makeup and soft clipping. | Shape a track's combined output. Maintainer has used it and reported CPU cost; per-effect hardware coverage and worst-case timing remain open. |
| Select toggle | Button left of Undo in one-shot SEQ; lights up while on. Select several steps without toggling notes. | Maintainer confirmed working since CH2 / 1.6H2. See [DISPLAY.md](DISPLAY.md). |
| Melodic Euclidean (CH3–CH9) | 4 rows layered over a pitched clip, each with its own note, length, hits and gate. | Its header button is hidden in CH10 while the workflow is reconsidered. |
| Chord mode (CH4–CH10) | Pitched track piano roll: double-tap SEQ. Encoders: Type (incl. Diatonic / Diatonic 7 from the project scale), Voicing, Inversion, Rhythm, Start, End, Velocity, Bars; second bank for progressions. Left/Right walk chords, touching a note picks its chord, the current chord shows selected. | Write chords straight into the piano roll and hear them immediately. Maintainer tested chord mode and chord pads; Rhythm/recording are newer. |
| Chord pads | In chord mode, keyboard pads play the whole chord on the pad's note and set the root; the played chord's name shows on encoder 1. Stays on for that track in other views (e.g. INST). Recording captures full chords; with a Rhythm set, recorded chords are turned into that rhythm. | Play progressions live and record them. Chord pads maintainer tested; recording with Rhythm pending. |
| Bars encoder | Piano-roll Sequence view, encoder 5: clip length in bars (1…256); shows 4+ / 1- when not exact. | Faster than turning Step Count. Fixed in CH10 after a report. |
| Euclid lanes in the piano roll | One-shot SEQ piano-roll layout: each Euclid lane greyed after its own length, with its own playhead box. | See polymeters at a glance. Reworked twice after owner videos; hardware check pending. |
| Hold MIXER + encoders | Holding MIXER (or LAUNCH) and turning an encoder now also returns to the previous view on release. | Quick volume tweaks without losing your place. |
| Meters after the channel strip | Mixer meters now measure after the EQ/compressor/clipper and fader. | Before, meters ignored the clipper and showed red too early. |

Top row is pads 1–8; bottom row is9–16, both left to right. **PROJ acts as Shift**;
the project pages it used to open are on **PROJ + PLAY**. Hold-based performance views
return to the previous screen on release; TRACKS shortcuts deliberately stay on
the destination instrument/sequencer page.

## Pick a checkpoint

| Target | Device label | Use it for | Known limits |
| --- | --- | --- | --- |
| `eu10` |1.6EA| Reproduce the pre-chord feature set. Recommended first comparison. | Select visibility needs confirmation after earlier missing-button reports. Experimental, not a certified stable build. |
| `ch1` |1.6H1| Review/investigate the chord editor and shared header route. | Chord and Select missing on hardware. No live pad chord audition, grouped Update or saved chord groups. |
| `ch10` |1.6HA| Newest: live chord mode, chord pads and recording, Bars encoder, Euclid lanes in the piano roll, meters after the channel strip. | Newest features still being hardware tested; melodic Euclid button hidden. Not a certified stable build. |

Both include the existing synths, locks, navigation, Euclidean and channel-strip
work. Older experiments remain in Git for reference. K8/K9/F1 had hardware
startup failures; they are not recommended installation candidates.

## What the evidence means

Maintainer feedback establishes that particular operations worked on the maintainer's
Bento. It does not verify every feature on every project or every later binary.
The source log often records older checks as pending; read the latest feedback
in [STATUS.md](STATUS.md) before interpreting a historical release document.

The pinned EU10 image passed 249 software checks; CH1 passed 284. Several tests
execute native ARM widget/note/DSP code, but model, GUI-parent, SD, Undo storage
and engine services are substituted in places. There is no complete Bento
emulator. Display success in those fixtures did not predict the missing buttons.
Physical audio deadlines, power/recovery behaviour and full project save/load
coverage still require hardware work.

Other limits: Euclidean settings do not fully follow clip Copy/Move or native
Undo; probability/microtiming interactions need review; locks use finite storage;
ordinary automation and locks can interact. Drum-synth destinations in the
modulation matrix are unfinished. The compressor's auto makeup is a formula,
not perceived-loudness matching; the soft clipper is not a master true-peak limiter.

## The implementation in plain language

We keep most of the original firmware and redirect a small number of verified
functions into our added code. Native UI widgets, native note storage and native
playback are reused where possible. Extra synth/FX code runs in the audio
application. This keeps changes recognisable and comparatively removable, but
all offsets and assumptions are tied to one exact firmware version.

Each target checks its original image hash, patch bounds and reversibility.
The controller file is copied unchanged. A fixed input hash is not independent
proof of every bootloader erase/programming boundary; no bootloader change or
automatic flashing is part of this project.

For exact offsets, ownership and decisions, use [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
and the corresponding `docs/releases/<version>/DESIGN.md`. Historical documents
are evidence of that stage, not a promise about today's device behaviour.
