# P12 implementation and evidence

Base: private feature/performance at 4d7948c4 (including the late P11
header-driven mod-toolbar change). Maintainer reports: Analog plays, grey lines;
MOD/MATRIX absent; shifted PLAY still starts; no performance octave arrows;
no melodic Euclid entry; uncertain drum-engine identity. Installed binary hash
was not supplied, so the report is not attributed to an exact image hash.

- Final header apply entry 0817FAF8 is guarded and wrapped. Integer-only
  adapter prepares the exact outgoing snapshot, then replays the original
  push and continues at 0817FAFC. This also covers native callers that bypass
  08134800. Existing header_sync rearms native visibility, including late
  insertion; real native constructor/apply tests check actual hidden/id fields.
- Piano Euclid uses normal slot 4 beside Undo, replacing the direct Clear
  shortcut; native Clear Seq/Clear Auto remain in F9. Slot 0 stays free for
  the overlapping selector/chord indicator. F9 entry is driven by page and
  pitched owner, without waiting for the piano view to tick. Its click still
  validates the actual piano context. Existing real-note Euclid model retained.
- Analog draws with native 08140EBC(selected track index), the very mapping
  native sequencer setup 0815CD22 uses. A colour change marks the pane dirty.
  Native palette indexes F7..FE are verified; the emulator's default PNG palette
  does not reproduce those hardware colours, so raw drawing-colour checks
  are the colour evidence.
- Native queue stub 08058600 gets an additional PLAY (8F) guard: producer raw
  PROJ mask 0100 at global 2401BD3C -> +2338, or UI shift 24048D68. The UI
  cache line is invalidated on M7 before reading. Other event codes and plain
  PLAY pass to original 08059980. r2/r3 are preserved. The prior scan guard
  remains. Native device scheduling is still not emulated fully; no claim
  that the single cause of the hardware playback report is proven.
- Performance Up/Down presses set the selected track's native 178 Pad Row
  Offset through the model; 08139138 refreshes pad mapping. Limits -5..5,
  releases consumed, only pitched tracks while Performance is active. Readout
  and encoder use the same native property; no parallel transpose store.
- No kick/snare DSP changes: P10 Punch and Snare 909 remain, verified by the
  existing engine/audio suite. No bootloader/controller/MPU/heap boundary edit.

New test_p12 covers final native header application without view ticks,
visible Euclid on all four pitched types without a captured view, direct
queue suppression, performance arrows, native palette mapping, and the
compiled waveform paint's actual fill colours. Broader inherited checks and
fresh builds are recorded alongside the private delivery. SD/model and device
transport concurrency remain hardware checks.
