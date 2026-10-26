# S1 final software validation — 23 October 2026

Main image: `9160cd379b0f38c84fee5cba25281833e41b95abe595ec56d899558d51e90da7`; 1,631,140 bytes.

**PASS: 406 checks in 22 suites. Hardware testing pending.**

| Suite | Passed |
|---|---:|
| SAFETY_RESULTS | 7 |
| GESTURES_RESULTS | 6 |
| INTEGRATION_RESULTS | 12 |
| PREVIOUS_CONTROLS_RESULTS | 38 |
| LIVE_RESULTS | 20 |
| EDITABLE_EU_RESULTS | 8 |
| EU7_RESULTS | 11 |
| EU8_RESULTS | 14 |
| EU9_RESULTS | 8 |
| EU10_RESULTS | 6 |
| MELODIC_RESULTS | 10 |
| CHORD_AUDITION_RESULTS | 10 |
| RECORD_TAKEOVER_RESULTS | 5 |
| MOD_MATRIX_RESULTS | 10 |
| CONTROLS_E3_RESULTS | 12 |
| DSP_RESULTS | 38 |
| VISUAL_RESULTS | 10 |
| K16_REGRESSIONS | 61 |
| MOD_MATRIX_AUDIO_RESULTS | 10 |
| ENGINE_RESULTS | 10 |
| CHORD_RESULTS | 85 |
| SUBTRACTIVE_RESULTS | 15 |

- Two independent isolated stock-to-S1 builds match byte for byte; all source input hashes match.
- Original stock hash guards, complete declared patch reversal, word alignment, application-only bounds, unchanged controller, native MPU/stack/vector/recovery guards pass.
- 768 host extreme parameter/pitch combinations pass; output finite and bounded. S1 state is 248 bytes in the existing 288-byte pools.
- Optimisation: 768 host cases and three representative ARM cases have bit-identical reference/optimised samples. Default plain/sync instruction counts fall from 756.30/836.28 to 628.80/708.78; these are emulated instructions, not device CPU percentages.
- Existing Kick/Snare/HiHat golden hashes and all inherited engine instruction budgets pass. Tom/Clap and modulation regressions pass.
- Native constructors, descriptor configuration, widget/font paint and three-row layout rendered with fixture model/file services.
- High pitched notes have a synth-only cold path up to native ratio 64; drums keep their old ratio guard. The direct shared guard briefly exceeded the kick budget; that rejected candidate was never delivered.
- No device flash, boot claim or real-time voice-count claim. Check the owner hardware report against this exact image hash.

Release evidence (full logs, source input hashes, reversible manifest, screen and reproducibility record) accompanies the private tester ZIP.

