# CH10 design

The maintainer reported that the Bars encoder counted 4 bars as 1.

The stored Step Len value (property 60) indexes table `081A01F4` in
**sixteenths**:
- the stored value 6 is 1.0 sixteenth, i.e. 960 ticks per 1/16 step;
- so a bar is 15360 ticks.

CH8 assumed quarter notes and used 3840 ticks per bar. `bars_ui.c` now uses
`BAR` = 15360.

The lane unit (`step_unit` × ticks) was already right, because it only uses
ticks per step.

Validation: the chord suite was rerun on the CH10 image (85 tests). The other
17 suites are carried over from the CH9 full run, since only `bars_ui.c` and
the build label changed. See `VALIDATION_SUMMARY.json`.
