# P5 design notes

- Shared chord per track: the performance page store (PerfTrack type/voicing/
  inversion, saved as bento_perf_chord) is the one chord of a track.
  perf_chord_share / perf_chord_shared (perf_ui.c) are used by device.c:
  SEQ chord mode edits of Type/Voicing/Inversion (keys 196/197/19A) write it
  (editor and live mode), and entering live chord mode on an empty clip seeds
  the empty chord from it (invalid combinations keep the default).
  Type numbering is identical in both (0..14, 15 Diatonic, 16 Diatonic 7).
- Hand-over: unchanged mechanism — live chord mode owns the ChordMail on its
  track (chord_live_owner); when it ends it withdraws the mail, perf_tick sees
  the serial change and republishes the performance chord.
- Chord symbol: header root vtable [1] (0817F8F0, paints all header widgets)
  -> header_root_paint, which calls it and then draws at 1156..1176 x 18..42
  (header coordinates; battery at 1186,20). Drawn while ChordMail is active
  (chord_mail_active, live_ui.c); erased once with F1 when it stops
  (state word 24043D70). Render: research/display_emulator/render_chord_symbol.py.
