# CH8 design

## Bars encoder (`bars_ui.c`)
The piano view keeps the Snap Mode, Step Len and Step Count properties at
`+11CD10`, `+11CD14` and `+11CD18` (properties 61, 60, 62; header `081599BC`).
The Sequence tab (view `+125DAC == 1`) binds keys 68, 61, 60 and 62 from RAM
table `3000009C` and leaves slots 5–8 empty.

Bars uses the free registry key 177 (preflighted). It is bound to slot 5 after
the native header, unless the Euclid mode owns the encoders.

Step Len table `081A01F4` is in quarter notes. One step = `table × 960` units,
and a bar = 3840 units:
- the value shown is the largest of 1…256 at or below the clip length;
- `+` or `1-` marks a clip that isn't exactly that.

Turning Bars sends the native event `CF/62/steps` back through the piano
view's event entry (`0815A598`), clamped to 1..256 steps, then rebuilds the
header. Chord mode puts the same key on encoder 8 (keys[7]: 177 replaces Grid
1D1).

## Lane timing
The projection `0815ABB8` scales note times when Snap Mode is on: the grid time
is `round(t/960) × round(table[StepLen] × 960)`. Lanes use the same unit
(`step_unit`); otherwise they use 960 per step.

## MIXER hold
K16 already returns to the previous view when a held MIXER or LAUNCH was used
(`controls.c`: state `24048CC0` = {magic, button, used, ...}; `restore()` on
release). Its "used" flag was set by pads only. Encoders reach the UI as
message `AB`, and `fx_dispatch` (before the K16 consumer) sets `used` when an
`AB` arrives while button 3 or 5 is held.

## Chord name and velocity
- **Chord name.** The device's `held` count follows pad `B0`/`B1`. The name is
  root + type suffix, plus `/bass` when the lowest note isn't the root. It is
  set on encoder 1 by `08170656` and reapplied on every chord header rebuild
  while a pad is held.
- **Velocity.** `ChordMail.velocity` carries the chord's Velocity. On note-on,
  `chord_press` scales the pad velocity by `velocity/127`. ChordOwn gains
  `vel[128]` and padding, so the bank is now 46080 bytes.

## Hidden
`piano_eu_toolbar` returns 0, so the Euclid header button is hidden. The code
stays in place.
