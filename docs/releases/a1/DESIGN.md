# A1 design: Analog as a native Wavetable track

Built on S1 (`feature/subtractive-sync`, on top of CH12). An Analog track is a
native Wavetable track (track type 18, M7 root vtable 080AC798) whose WT1/WT2
oscillators play analog waveforms. Everything else stays native: 10 voices,
Osc (sub: Level, Pitch, Waveform Rev Saw/Triangle/Square/Sine/Noise,
Pulse Width), 2 filters, 2 envelopes, 2 LFOs, Poly/Unison/Detune/Pan Spread,
Mod Matrix, keyboard, MIDI and chord mode.

## M7
- **Voice hook.** Wavetable root vtable slot 18 (per-voice render, 0809BE80)
  → `kick_analog_enter(root, voice)`. It records the voice and the track's mode
  (KickKnob entry with engine 13 keyed by root+0C, cached per root and UI
  serial).
- **Oscillator hook.** WT oscillator class vtable 080AC3E4 slot 0 (08081360) →
  `kick_analog_osc`. For voice+7A4 (WT1) and voice+994 (WT2) of an analog
  voice, it repeats the native steps with the native helpers:
  - pitch: 0809FD80/0804F680/0804F5E0, where note 60 = 261.63 Hz and the rate
    is 2^oct/23.4375 steps of a 2048-step cycle;
  - Position (×255), the level curve (0804F360) and the level smoother
    (08071240/08071040), then the mix (080526C0).

  Only the wavetable read (080A1860) and its "table loaded" gate are replaced.
- **Oscillator kernel** (`drums/analog.h`):
  - saw → square blend, then pulse width down to 8%;
  - fractional two-sample BLEP edges (from S1);
  - one sample per output sample, because the native filters follow.

  State lives in the oscillator's unused native kernel area (+10C, ≤0xC0
  bytes).
- **Hard sync.** WT1 writes its wrap fractions per sample into WT2's state;
  WT2 resets on them with a BLEP jump. WT1 renders first (voice list +178),
  and WT1 still runs when its level is 0, so it can drive the sync.

## M4
- **Menu.** "Analog" (action 1052) goes in the ninth cell of the native
  instrument menu F6 (081981F8). The menu count at 08141370 changes from 8 to
  9, the native maximum.
- **Menu handler.** The view vtable 0819E52C is wrapped by
  `analog_menu_event`:
  - 1052 posts the native Wavetable change (event 42, type 6, track index from
    property 131) and then marks the current track (type 18);
  - 102A (plain Wavetable) clears the mark.
- **Persistence.** `kick_ui_save/load` for objects of type 18 write and read
  `bento_analog` and `bento_analog_sync`.
- **Sync control.** Key 1D1 (free in the stock registry, descriptor created
  lazily) goes in WT2's empty fourth slot of the osc-page key table (0819E92E).
  It is read through `fx_get` and set at the model event entry 081403EC
  (`analog_model_event`), so the model never stores it.

## Not covered
- Hardware. In particular, these need the device to confirm:
  - root+0C equals the track handle used on M4;
  - B(object,4) == 18 for the saved track object;
  - the ninth menu cell is shown.
- Waveform pane, "Position" label, type name, glide.
- The S1 one-shot Subtractive engine is still present; retire it once Analog
  is confirmed.

# A1 validation (24 October 2026)

422/422 software checks across 24 suites (S1's 22 plus ANALOG 7 and ANALOG_UI 9).

Image SHA256 `020a58924c028a4b91d58a9e1dac50e2571fa3f617cd15ca939206ad5cabd8df`.

Hardware test pending.
