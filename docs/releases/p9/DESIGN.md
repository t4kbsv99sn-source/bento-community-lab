# P9 design: P8 + melodic Euclid as real notes

P9 is P8 (mod mode, see ../p8/DESIGN.md) plus melodic Euclid restored with
the CH3 native-note model. The owner asked for this so that the steps can be
selected and edited.

- melodic_eu.c:
  - Length/Hits/Rotate go through `live_generate`, which writes native
    notes (EU6 bulk APIs, one undo gesture) and sets pattern bit 26.
  - Note uses `eu_repitch`, so existing row notes move.
  - Gate updates the note lengths (`eu_gate_notes`).
  - An unassigned row starts on C3 (MIDI 48).
  - There are 4 rows (CH4).
- Header: `header_tab(…, 1054, "Euclidean")` in slot 0 of the piano-roll
  template (page 17), the same as the one-shot tab 1055. The native tabs are
  shown inactive while it is on; Event/Sequence/Automation (49/4A/4B) leave
  Euclid and go native. header_sync treats 1054 as a tab. The tab is hidden
  during live chord mode, which uses slot 0.
- live_ui.c: `live_edit` keeps bit 26 for melodic rows.
- live_audio.cpp (M7):
  - melodic native rows read the clip cursor and match notes by pitch;
  - `live_skip` suppresses the native playback of an enabled row's pitch;
  - M7 plays the row's own notes on the row cycle (as CH3/EU6).
- Tests: chord_work/test_piano_eu.py (10, actual piano view) and
  test_melodic.py (10).
