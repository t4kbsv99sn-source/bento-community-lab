# P3 design notes

- Row 3 of the performance page: keys 104 Chord (on/off), 132 Type (enum,
  17: chords.c types + Diatonic + Diatonic 7), 14A Voicing (enum), 144
  Inversion (0..3). All four are free in the real native registry and unused
  by other project code. Per track handle in PerfTrack; saved as
  `bento_perf_chord` = 1<<24 | inversion<<16 | voicing<<12 | type<<4 | on.
- perf_tick (every UI message) publishes the selected track's chord through
  the CH6 ChordMail (`chord_audition_publish`, velocity 127 = unscaled) when
  it is on and the track is pitched (15/18/19/22). The signature includes the
  project Root/Scale for the diatonic types. If anything else rewrote the
  mail (serial changed), it republishes. Live chord mode
  (`chord_live_owner`) keeps priority on its own track; P3 never clears the
  mail while live chord mode owns the selected track.
- Invalid inversion/voicing combinations step down (inversion) and Drop 2
  falls back to Open for triads.
- UI code bound raised from 081D0000 to 081E0000: still inside the 128 KB
  sector 081C0000 and the stock M4 MPU executable region 08100000..081FFFFF
  (as CH7 argued for 081D0000). M7 code has ~0.8 KB left below 080E0000.
- Drum Synth menu: added only to menus with fewer than nine entries (native
  menu apply shows at most nine, EU8).
