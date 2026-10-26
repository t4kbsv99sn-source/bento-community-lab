# S1 handoff

Continue on `feature/subtractive-sync`, based on CH12 `1d4a6806`.
Read DESIGN.md and VALIDATION.md here, then the repository AGENTS.md.

Main code:
- `eu4_work/drums/subtractive.h`: voice, fractional sync, oversampling and tone.
- `eu4_work/drums/kick.cpp`: native voice routing, pitch, lifetime and rendering.
- `eu4_work/integration/kick_ui.c`: controls, persistence and matrix destinations.
- `eu4_work/integration/synth_draw.c`: third-row display correction.
- `eu4_work/test_subtractive.py`: installed-ARM checks.
- `research/display_emulator/render_subtractive.py`: native widget render.

Build the actual worktree from original 1.6.1:

```sh
python tools/build_s1.py --stock /path/to/stock/bento1.bin --out /path/to/new-build --test
```

Do not use the pinned CH10 reproduction target to build S1. Hardware testing is
the next step: load the selector on a One-shot track, verify the three control
rows, Sync, keyboard pitch, held notes/release, small chords, persistence and CPU.
No automatic flashing. Preserve the CH12 restore and the stock restore pair.

Current limits: no dedicated glide, extra unison bank, drift control or full
filter ADSR. Native locks remain functional, including amp ADSR; S1-specific
sound-lock kinds are not added. Real-time polyphony is unmeasured.

