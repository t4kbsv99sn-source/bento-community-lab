# BENTO_MOD K7 — implementation boundary

This module is specific to the exact supplied Bento 1.6.1 image. Re-run the
profile/hash/instruction guards before considering a different official version.
Never carry these offsets into another release without re-identifying them.

K6's hardware-confirmed carrier recognition and live DaisySP engine are retained.
The marker is not an audio sample: it selects SyntheticBassDrum only when the
native sample descriptor passes the existing content/rate/length/mono checks.

## Editor

`kick_ui.c`, `kick_ui_build.py`, `kick_ui.ld` add before/after adapters around
08152144 and intercept only private CF parameter events at 08152C50.
The editor is the native individual one-shot sample editor, not the bank grid.
Only the reserved kick filenames on one-shot children receive the new layout.
Native binding records keep Level and six Mix/FX properties on the actual
sound handle. Private parameter IDs are checked against the live registry
before registration, and ordinary sample bindings are restored on exit.
The third row and waveform are hidden; the native envelope gives a simple
illustration. No synthetic waveform rendering or new UI framework is installed.

## Sound controls

The UI-owned 128-entry table is at 24043500..24043D20, separate from M7 DSP
state, view state at 24043D20, and existing diagnostics at 24043E00/24043F00.
It is keyed by native SOUND handles, not the distinct sample FILE handles.
An odd/even sequence commit and memory barriers protect reads; M7 invalidates
reader cache lines and validates ranges. Each audio block updates coefficients
without restarting oscillation or retriggering the envelope.

Private keys and values, in order:

| Key | Parameter | Range | Default |
| --- | --- | --- | --- |
| 1A0 | Tune | 25–180 Hz | 55 |
| 1A1 | Decay | 0–100 | 65 |
| 1A2 | Tone | 0–100 | 45 |
| 1A4 | Impact / accent | 0–100 | 65 |
| 1A5 | Sweep / FM amount | 0–100 | 55 |
| 1A6 | Sweep decay | 0–100 | 25 |
| 1A9 | Dirt | 0–100 | 25 |

1AA selects a pad via native 08152ACC; 1AD opens native Load via 08152BB0.
New synth parameter changes mark the native project dirty. Native Level,
Overdrive, Pan, sends and Filter/Resonance continue through their existing paths.
Automation A–D and earlier step-lock storage are not extended by this module.

## Persistence

The params-node save hook at 0812F5EA and load-entry hook at 0812FAAC add/read
`bento_kick_version=1` plus seven `bento_kick_v1_*` integer attributes.
These are explicit extension fields; no native property bag/schema is expanded.
Missing/unknown-version values reset to K6 defaults; individual values clamp to
the supported ranges. Non-sampler objects are untouched. Stock ignores unknown
attributes and may discard them when saving. New controls currently target
instrument settings, not new lock targets or a new automation lane.

## Verification limits

`test_kick_ui.py` executes compiled ARM code for ordering, fallback, bounds,
native calls, actual sound/file ID distinction, separate-pad state, versioned
save/load, wrapper preservation and DSP handoff/audio differences. Widget/XML
services are controlled substitutes. The regression suite includes previous
native audio processing and strict marker recognition tests. These establish
software behaviour, not physical UI layout, SD timing, CPU headroom or audible
hardware success for the new controls. The prior K6 sound is hardware-confirmed.

Application patch writes are guarded and byte-reversible. The bootloader,
controller binary, native installer and disk/recovery region are not modified.
