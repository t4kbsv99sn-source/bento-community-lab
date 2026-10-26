# Refinement pass — 26 October 2026

This revision improves the existing Measure direction, keeping the palette, 1280 × 480 canvas, eight encoder columns, 32 square one-shot steps and two lock rails.

## Visual decisions

- Euclidean: emphasize one cycle and dim repetitions across the 32-step window. A four-step ruler supports counting; a narrow white edge identifies the selected row. Cycle boundaries and playback use separate marks.
- Drum Sequence: show eight named drum lanes instead of the unrelated piano-roll study. Selected-pad Step edits appear in that pad's sequence lane. This lane geometry is a design proposal, not a trace of native firmware.
- Macros: separate target name, current value and range into distinct vertical positions. Track identity remains explicit. Selected assignments show start/end values; reverse ranges retain their direction. Macro values are 0–127, example target values are normalized percentages. The full-page editor remains a proposal; P27 implements a macro strip.
- Navigation: use the same upper/lower active-view rules in the sequencer footer. Preserve drum versus melodic routing through Sequence.

## Interaction corrections

Euclidean rows remember independent length, hit count and rotation. One-shot pads retain separate preview steps. Row graphics and macro target labels participate in the selection hit area. FX section graphs accept focus touches as well as section headers. EQ, compressor and soft clip remain visible together.

Euclidean generation and Step editing remain separate visual simulations: changing a Euclidean pattern does not rewrite Step notes. There is no audio engine or firmware behavioral emulator. Track-level project persistence is not implemented. The source label audit documents the remaining native encoder-label gaps.

## Verification

- `node tests/navigation.cjs`: drum and melodic routing, 32 step targets, independent pad edits and row settings, and rectangle bounds for the principal screens.
- Native-resolution SVG/PNG renders inspected for Euclidean and macro spacing.
- Source JavaScript syntax checked; regenerated both preview entry points from one build script.
- Full browser interaction validation was attempted but unavailable: local Playwright has no Chromium binary, and the remote review browser could not reach the local preview server. Do not describe this pass as browser-validated.

## Build

Run `node renderer/build.cjs` from this folder. PNG export uses optional `sharp`; SVG and browser preview require no external graphical assets. Firmware files are untouched.
