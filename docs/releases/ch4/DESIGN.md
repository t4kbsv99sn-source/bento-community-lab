# CH4 design notes

Base: CH3 (feature/ch3-melodic-euclid). Branch feature/ch4-live-layers.

## Live chord mode (chord_work/device.c)
- SEQ double-tap (fx_dispatch index 11, page 17, pitched context) toggles `live`.
  There is no navigation to page 1A any more; the GenericProperties editor
  remains for compatibility.
- After native piano header `081599BC`, `chord_live_header` binds chord keys
  (bank 0: keys[0..7], bank 1: keys[8..15]) into the piano bindings
  (+11BCC0/+11BCD0/+11BCA0) and overrides titles. The registry descriptors are
  the CH1 ones.
- Each accepted edit runs `draft()`:
  - `chord_native_remove` deletes exactly the IDs inserted for the previous
    draft in one native bulk delete (08136FB4);
  - `chord_native_insert` writes the new notes with new IDs and one snapshot.
  - Each edit is therefore an undo step. Notes the user added or edited are
    never touched.
- Header: on page 17 the free slot shows a lit `Chord 1/2` / `Chord 2/2`
  (id 1052) while live; tapping it switches bank. Euclid's header action is
  hidden while live.
- Root naming changed to C3 = MIDI 60 (owner); default root 60.

## Melodic Euclid as a layer (melodic_eu.c, live_ui.c, live_audio.cpp)
- Rows are procedural only (pattern bit 26 never set for melodic records). UI
  edits use `live_edit` / `live_set_gate` / `live_dynamic`; no clip note writes.
- 4 rows. Unassigned rows show and default to C3; the first edit assigns it.
- M7: melodic records don't scan the clip cursor and don't suppress native notes
  (`live_skip` returns 0). Hits use the row gate (quarter steps) and the native
  active-note table for note-offs, as in CH3.
- `eu_repitch`/`eu_gate_notes` remain in the source (tested) but are no longer
  called by the UI.

## Not done
- Drawing Euclid rows and per-lane playheads in the piano-roll layout: first for
  one-shots in piano mode, then melodic rows. See the backlog in the project.
