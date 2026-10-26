# Changes since the public CH10 / 1.6HA snapshot

26 October 2026 · P27 development snapshot. This describes additions to source, not a claim that every feature works on hardware.

- Added Clap and Tom/FM-percussion engines, drum DSP optimisations, kick Punch and a revised 909-style snare.
- Added subtractive/Analog synthesis work and oscillator graphics.
- Added drum-synth destinations to the native modulation matrix, quicker MOD/MATRIX access and modulation-source labels.
- Extended two per-note locks to supported melodic instruments, including envelope decay/release and individual delay/reverb sends. Multisample retains the inherited sampler implementation.
- Added the Performance page with tempo, tap tempo, swing, root/scale, fixed velocity, octave and chord controls.
- Reworked melodic SEQ navigation into Chord / Euclid / Step / Seq, plus Select and Clear. Added PROJ+Left Undo, note navigation and track-coloured pad selection feedback.
- Revised chord position/length editing, immediate pad insertion, whole-chord selection/deletion and edit Undo handling.
- Corrected multiple Euclidean timing, playback, selection and tab-state issues; see limitations for reduced melodic Euclidean behaviour.
- Added SD-card-mode access through PROJ+Up and further LAUNCH-hold fixes.
- Added experimental motion recording and a swipe-access macro strip. These remain unfinished on hardware.
- Added the separate Bento Playground design kit and interactive preview. Firmware UI remains unchanged by that kit.

CH10 already included Shift/hold shortcuts, drum step locks and conditions, Kick/Snare/Hi-hat, Euclidean drums, chord mode, melodic Euclidean lanes, the track channel strip and post-FX mixer meters. These are not new in this snapshot.
