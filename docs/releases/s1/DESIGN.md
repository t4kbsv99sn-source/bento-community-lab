# S1 / 1.6S1 — first subtractive workhorse voice

Branches from CH12, commit `1d4a68064a2668ae2ee9e17e629cfcbd67b8ac3d`.
Experimental hardware-test build; software validation is not hardware validation.

## Voice and controls

Engine 11, `BENTO_Synth_Subtractive.wav`, 144029 frames. Uses the existing
one-shot sample-root render path, native pitch, amp ADSR/note-off, pan,
overdrive, filter, sends and mute. The carrier identifies the real-time engine;
it does not contain the synthesized sound. No Max or Ableton runtime.

| Control | Meaning |
|---|---|
| Shape | Saw to pulse, then pulse width down to 8%; both main oscillators |
| Osc 2 Semi | Second oscillator interval, -24..+24 semitones |
| Fat | 0..18 cents of oscillator-2 detune, triangle sub weight and mixer drive, with mixer gain compensation |
| Cutoff | Approx. 35 Hz..12.7 kHz before envelope; 16 kHz ceiling |
| Resonance | First filter stage resonance, with output compensation |
| Env Amt | Positive filter sweep, up to eight octaves |
| Env Decay | Exponential filter decay, 12 ms..12.288 s |
| Sync | 0 off; 1 on with no sweep; 2..100 adds up to 48 semitones of slave sweep |

Three native control rows: Level and seven sound controls; sample/pad browser
and existing mix controls; Sync plus native Attack/Decay/Sustain/Release.
The display uses the native widgets and fonts. The old cleanup filter suppressed
every third row except Kick; an independent current filter now also allows
Subtractive. Historical K16 overlay source and its hash stay unchanged.

Filter: two cascaded nonlinear DaisySP SVFs (MIT), giving a nominal 24 dB/octave
lowpass. Drive happens before the filter; its feedback has the existing SVF
cubic nonlinearity. Soft output levelling prevents hard clipping at high
resonance. This is its own voice, not a Lode port or an analogue-circuit clone.

Oscillators: project code with fractional, two-sample BLEP discontinuity
corrections for saw/pulse transitions and hard-sync resets. A master wrap splits
the slave advance at the actual fractional event time. Two-times internal
sampling, a seven-tap halfband output filter and DC removal reduce artifacts;
do not describe this as alias-free. The base generator frequency is
130.81278 Hz at native pitch ratio 1; physical key naming/root follows the
native sample/keyboard configuration.

Native amp ADSR supplies gate, sustain and release. Filter/sync sweep currently
uses a retriggered decay, not a second full ADSR. No dedicated glide, chord mode
inside the voice, extra unison bank or drift control in S1. Native modulation
sources can reach all eight synth controls through the existing matrix.

## Voice ownership and persistence

Shares the existing 16 custom-synth slots and the two existing 288-byte auxiliary
pools. S1 state is 248 bytes per slot, no new fixed RAM, heap reservation or MPU
change. Matching is per native voice for engine 11; the other engines retain
their existing monophonic retrigger behaviour. Long notes keep the carrier
cursor in range while the native ADSR terminates released voices. The slot pool
size is not a promise that 16 voices fit the device's real-time CPU budget.

Reuses seven UI mailbox bytes and the eighth Click extension, scoped to engine
11. Engine and Sync round-trip through existing versioned XML attributes. No
new parameter descriptor IDs. The existing packed lock format is unchanged:
S1 offers native locks including amp ADSR; custom S1 sound locks are deferred.
Mod Matrix destinations are engine-scoped as on CH12.

## Optimisation and evidence

Prepared resonance damping, explicit halfband state moves, block-invariant
gains, and a separate non-inlined synth render path reduce work and keep the
larger synth stack out of the drum loop. Existing drum golden hashes and CPU
budgets pass. A first shift-loop experiment was slightly slower and was replaced
by explicit state moves; do not assume a tidy-looking loop is faster.

Measured instructions per sample in the same 64-sample ARM fixture:

| Case | Initial | Final | Reduction |
|---|---:|---:|---:|
| Default, Sync off | 756.30 | 628.80 | 16.9% |
| Default, Sync 75 | 836.28 | 708.78 | 15.2% |

These are emulated instruction counts, not hardware cycles or CPU percentages.
768 host extreme parameter/pitch cases pass. Optimised/reference host samples
match bit for bit across 768 cases; three representative ARM cases also match
bit for bit. Native ARM checks cover audible controls, sync switching, pitch,
overlapping voices, carrier wrap, real amp ADSR note-off, native mute, matrix
routes and parameter persistence. Model/file services are fixtures.

`research/display_emulator/render_subtractive.py` runs native constructors,
descriptor configuration, font rendering and painting with fixture model reads.
Its screenshot is layout evidence; touch, LCD palette and device timing still
need hardware testing. Sound examples use the same host voice and a demonstration
amplitude envelope; they are not recordings from Bento.

Application-only patching, stock hash guards, alignment, reversible manifest,
unchanged controller, vector/recovery/stack/MPU checks remain mandatory.
