# P1 design notes

- Buttons: `perf_dispatch` runs first in `fx_dispatch` (before K16). With PROJ
  held (LOCK_UI 24048D60 +8): PLAY press toggles the page, sets bit 15 of the
  consumed-release mask 24048D70 (K16 consumes and clears the release) and
  marks PROJ used; Left press sends the native button event {0x73,0,7}
  (08142AFC, the old PROJ+PLAY action) and its release is consumed here.
  Arrows reach the dispatcher as 0xAF/0xB0 with index 0 Left, 9 Right, 1/8
  Up/Down (08142A88).
- Page: native GenericProperties 0x1A, two rows from `perf_header`, checked
  before chord and FX headers; any navigation not made by the page closes it.
- Project keys 8C BPM (40–250), 8D Scale, 8E Root, 8F Swing (1–99, global):
  reads go to the native getter 08133614 with the project handle pointer
  30030164; edits call the model event 081403EC with {CF, project handle,
  key, value}. Nothing is duplicated, so the settings pages stay in sync.
- Private keys (free in the stock registry): 101 Tap, 102 Fixed Vel,
  11C Velocity. Tap: intervals 0.2–2 s, mean of the last four.
- Fixed velocity per track handle (16 entries, heap state through
  `perf_state_slot`), saved as `bento_perf_velocity` = on<<8 | velocity.
  M4 publishes the selected track's setting to EuControl.reserved[1] =
  0x56454C00 | velocity on every UI message. M7: the pad module's press call
  080857D6 goes through `perf_press`, which sets the record pressure to
  ceil(v·0xD000/127); the native press maps min(p,0xD000)·127/0xD000 back to
  exactly v.
- test_safety: the "no FP in new UI code" scan now disassembles FUNC symbols
  only (A2 label tables happened to decode as vmov after layout moved).
