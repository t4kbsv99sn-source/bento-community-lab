# K14 — kick and synthetic snare, 1.6KE

Maintainer confirms K13 is visually clean. K14 rebuilds from the same K7 application integration and reapplies the confirmed K13 function-entry draw filters, with their temporary W/E/L title markers removed. The instrument title identifies Kick or Snare and the pad number.

## Changes
- DaisySP SyntheticSnareDrum (stable internal model ID 3, as in the preserved K8 experiment). It is the only added engine.
- Snare top row: Level, Tune, Decay, FM, Impact, Snappy, blank, blank. Bottom row retains pad, Load, Pan, Overdrive, Delay Send, Reverb Send, Filter, Resonance.
- Carrier BENTO_Synth_Snare.wav: mono 48 kHz, 144021 frames, existing signed 32-sample marker. Kick retains its exact 144019-frame carrier and sound.
- Both carriers are prepared through the native filesystem on Load. A fixed installer endpoint also covers the custom synth Load button. Existing unrelated/damaged files are never overwritten.
- Fivefold delta scaling for the seven private synth keys only. This targets the maintainer's reported approximately 20%-per-turn response. Native mix controls, pad and Load selection are unchanged. Exact physical feel remains a device check.
- Existing version-1 kick parameter attributes remain readable. bento_drum_model distinguishes ID 1 kick and ID 3 snare when saving/loading. No native automation lane reassignment or new synth-specific parameter-lock encoder.
- Per-block synth parameter updates, native pitch multiplier and downstream native processing are retained. Sixteen synth slots and the 128-pad parameter table remain.

## Reserved RAM
K7 send table size is 0x1810 at 24044000, ending 24045810. K7 lock table size is 0x1420 at 24046000, ending 24047420. Snare states are 288 bytes each: first seven at 24045820..24046000, remaining nine at 24047420..24047E40. Sixteen model IDs occupy 24047E40..24047E80. Compile-time size/bounds checks enforce these gaps. Neither table is moved or reduced; tests check their contents survive snare initialization/rendering. New state is owned only by M7 and initialized lazily during ordinary runtime. No extra startup hook, heap reservation or MPU change from the working K7/K13 setup.

## Scope and validation limits
No bootloader update, direct flash programmer, controller change or native vector modification. Patch records are restricted to the application range and reverse exactly to original stock. Startup/heap/MPU sites stay at the K7 integration's bytes. The bootloader's full internal layout has not been dumped/reverse-engineered; the known application base and restricted patch scope are the relevant boundaries. Unused RAM is unrelated to bootloader flash storage.

Tests exercise compiled Thumb DSP/UI, real native postprocessing, mixed kick/snare playback, frame/signature recognition, independent pad values, save/load attributes, filesystem no-overwrite/error cases, native Load and custom synth Load paths, the actual encoder wrapper, pool slot 15, existing sends/locks/conditions/navigation, alignment and exact reversal. Filesystem hardware, physical knob feel, startup, complete project reopen and live CPU headroom still need device testing. Existing K13 blank-area hit targets remain as before; this is not a new custom screen architecture.

The first broad run found one obsolete test expectation listing only one carrier. The corrected expectation covers both files. The focused follow-up passed, including new mixed-voice and custom Load integration tests. FINAL_TEST_RESULTS.txt records the subsequent final-image regression run.

Rebuild from an exact original stock main image:
python tools/build_k14.py --stock /path/to/stock/bento1.bin --out build/k14-rebuild --test

DaisySP MIT license stays alongside the source. The snare source retains the earlier per-voice even_ state and zero-drive filter corrections from the preserved K8 source; other K8 feature changes are not imported.

Final regression result: 246 tests passed. Isolated build matched SHA-256 13481d0a402e4a1b1a03e0aaac8a73f0a041194c60904346f713f9ff86756806.
