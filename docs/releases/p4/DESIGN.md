# P4 design notes: Analog oscillator display

- Wavetable page view class 0819E894 (constructor 0815E228). WT wave panes:
  class 081B3A98 at view +2E90 (oscillator index 0, rect 11,271,622,142) and
  +31F0 (index 1, 11,85,622,144); their "No WAV" label child is at pane +284.
  The page caches Position (0..255) at view +10154 + 4 x index.
- Pane vtable [0] tick (081852B0) and [1] paint (08184920) now point to
  analog_wave_tick/paint, which call the native ones first. On Analog tracks
  only: tick hides the label (and gives it back when the track is no longer
  Analog), picks the shape and marks a redraw (at most ~30/s per pane); paint
  fills the pane (F1), a centre line (F3) and two cycles in F6 with 08166EF6.
  Integer only (no FP in UI code).
- Live shape: M7 kick_analog_osc writes {track handle, shape 1 | shape2<<8 |
  counter<<16} to kick State +14F8 (0x240434F8, M7-owned cache line, cleaned
  with DCCMVAC). The UI uses it while the counter moved in the last 150 ms and
  the handle is the current track, otherwise the page's Position value.
- Orientation from the emulator: native y grows towards the top of the
  screen, so higher values are drawn at larger y. Render:
  `research/display_emulator/render_analog.py`. Hardware decides.
