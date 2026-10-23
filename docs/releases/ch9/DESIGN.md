# CH9 design

## Chord mode per track
`chord_nav` no longer ends chord mode when you leave the piano roll. It only
drops the piano-specific state (`piano`, `held`).

`chord_track_tick()` runs from `fx_dispatch` on every message from the audio
core to the UI. It keeps ChordMail active only while the selected track is the
chord-mode track (pitched). Opening another track's piano roll ends chord mode
(`chord_capture`).

## Recorded chords + Rhythm
The maintainer confirmed that the native recorder records the full chords: the audio
core's chord posts arrive at the track as real notes, with held length and
native quantise.
- **ChordPub.held** counts chord pads that are down, on slot 0. The audio core
  updates it on press and release, then cleans the cache line.
- **Watermark.** When the project's next note ID changes, the device remembers
  the last ID it had seen. Its own drafts move that mark forward, so they are
  never treated as recordings.
- **When it runs.** Once no chord pad has been down for 100 ms,
  `chord_native_rhythmize()` regroups the new pitched notes of the current
  clip by start. Each group of two or more notes is replaced by the Rhythm's
  hits over the group's length, with one Undo snapshot, a native bulk delete
  and add, and a refresh.
- **When it doesn't.** Nothing happens with Rhythm = Hold, on other tracks or
  clips, or for single notes.

## Meter after Track FX
The per-track mix function `080A04C0` used to measure:
- `r6`, the raw track buffer, via `08052EA0` at `080A0566`;
- plus a level offset from `[r5+70/28/40]`.

The Track FX (TF2 hook at `080A0510`) process `r4`, the post-Level buffer.

The patches:
- `080A0566 mov r0,r4`;
- `080A055C movs r3,#0; vmov s16,r3` (zero offset);
- the two other track-type branches `080A05C0` and `080A05E0` jump there.

The meter now reads after Level and Track FX, before pan and sends. Original
bytes are guarded.
