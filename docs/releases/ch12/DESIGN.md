# CH12 design: Clap, Tom, and cheaper synth engines

## Engines
Engine ids follow the carrier length: 144019 + id − 1 frames.
- 7 Clap: `BENTO_Synth_Clap.wav`, 144025 frames.
- 9 Tom / FM perc: `BENTO_Synth_Tom.wav`, 144027 frames.

Even ids stay reserved for the K8 analog variants.

**Clap** (`eu4_work/drums/clap.h`, our own code):
- xorshift noise into a Chamberlin band-pass, plus some of the high-pass
  output for Tone;
- three bursts (decay to −30 dB within the spacing), then a tail with a
  −60 dB time of 40 ms × 25^Decay;
- every coefficient is made once per block.

It lives in the shared 288-byte snare/hat pool (static_assert).

**Tom** is the Slot's `SyntheticBassDrum` with `Tune` = 40 Hz × 2^((v−25)/28)
for v = 25..180, and no Click (its transient follows Tone, as in the DaisySP
default).

## Locks and modulation
Lock kinds are per family, so the frozen K16 pair encoding is unchanged:
- Tom uses the Kick kinds 12..18, with the same 25..180 tune range; Kick Click
  (19) does not apply.
- Clap uses the Snare kinds 20..24.

The lock picker labels them Tom … / Clap ….

Mod Matrix: Tom 7 rows, Clap 5.

## Optimisation (bit-identical)
- `Svf::ProcessLow/High/Band`: the same two passes and statements as
  `Process`, returning one output and keeping the state in registers. Used by
  the kick click, the snare (3 filters) and the hi-hat (2 filters).
- HiHat: the six square-oscillator increments, the noise clock rate and the
  sustain gain move from every sample to `PrepareBlock`.
- Snare: the reset-noise amount moves to `PrepareBlock`.

`test_engines.py` checks the CH11 output hashes for six Kick/Snare/HiHat
settings, and per-sample instruction budgets.

Emulated instructions per sample, CH11 → CH12:
| Engine | CH11 | CH12 |
|---|---|---|
| Kick | 331 | 304 |
| Snare | 352–362 | 275–285 |
| HiHat | 388–391 | 225–228 |
| Clap | – | under 200 |
| Tom | – | about 320 |

## Not covered
- No hardware test yet; the Clap and Tom sounds are tuned on numbers, not by
  ear.
- Native Pitch on Tom/Clap behaves as on the other synths (ratio on Tune).
