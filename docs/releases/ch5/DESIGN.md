# CH5 design notes

Branch feature/ch4-live-layers (continues CH4).

## View tabs and arrows (one-shot page 27)
- Hardware events go to view vtable slot 13: drum `0815D4B4`, piano `0815B548`.
  Codes: 0xAE arrows (+8: 0 Left, 1 Up, 8 Down, 9 Right), 0xB0 pad press,
  0xB1 pad release, 0xAD encoder.
- `seq_eu_arrows` (patched arrow site `0815D57E`) now returns native for every
  arrow; only Shift+Left (shift flag `24048D60+8`) disables the selected pad's
  generator.
- The Euclidean tab is header record slot 0 with id 0x1055, tab group +22 = 1,
  active +21. While it is active, the native tab records' +21 are cleared.
  `header_sync` re-arms layout when any tab's +21 differs (native apply sets the
  selected state only while armed).
- Tab events arrive in the SEQ action dispatcher (`0815D600` hook,
  `seq_select_event`): 1055 enters the bank; native 0x49/0x4A (Step/Sequence)
  leave it, then native handling continues.
- Default view: `fx_nav` arms `auto_eu` on each navigation to page 27; the next
  drum header build (`seq_eu_header`) enters the bank. The flag lives in the step
  lock UI struct, because `Ui` is full.

## Chord navigation (piano page 17)
- New hook at piano hardware entry `0815B548` (prologue `f0b5 91b0` guarded):
  in live chord mode 0xAE Left/Right call `step_chord`; otherwise the native
  `0815B3EC(±1)` runs.
- Chords in the clip = pitched notes (H+2 = 0) sharing a start tick, ≥ 2 notes
  (`chord_native_starts`). `chord_native_adopt` takes a chord's IDs as the draft
  and infers root (lowest pitch), length, velocity and type (pitch-class match
  against root-position types).
- Right past the last chord: empty single chord at the previous end; `draft()` is
  called only on the first edit.
- `chord_native_clear_for` replaces CH4's remove: one bulk delete of the previous
  draft IDs plus any same-pitch notes overlapping the rendered chord, then insert.

## Diatonic types
- Type choices 15 = Diatonic, 16 = Diatonic 7 (UI-level; stored chords keep real
  types).
- Quality from the project root (key 8E, index 0 = A) and scale (key 8D) read
  via `08133E54` handle + `08133614`.
- Scale rows: Major/Ionian, Minor (also Minor Pent, Blues, Aeolian), Harmonic
  Minor, Mel Minor, Dorian, Phrygian, Lydian, Mixolydian, Locrian; others → Major.

## Pending
- Pads → chord root + audition: piano slot 13 ignores 0xB0/0xB1, so pads are
  played by a global path that still needs tracing.
- Piano-roll lane display (option B).
