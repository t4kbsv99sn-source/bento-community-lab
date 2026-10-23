# K15 / 1.6KF — snare repair, kick Click, 808-style hi-hat

Baseline: K14 / 1.6KE, maintainer-confirmed boot and snare playback after manually copying the exact carrier. K15 is a device test, not hardware validated.

## Authorized sound choices

Maintainer selected punchier existing snare attack and an 808-style metallic hi-hat. No added separate crack/noise-burst layer. Third row for kick Click explicitly authorized. Native mix row remains intact.

## Snappy repair

The inherited DaisySP snare passes `0.5 + 2*snappy` to `Svf::SetRes`. That setter accepts normalized 0..1 and clamps it. At raw UI ~27.27% (and approaching it earlier), damping reaches zero. K8/K14 had disabled the SVF's nonlinear drive for high-pitch stability, exposing very strong ringing. This matches the maintainer's approximate 20–25% threshold.

The original Plaits algorithm supplies a true Q value to stmlib. stmlib `set_f_q` uses damping `1/Q`: https://github.com/pichenettes/stmlib/blob/master/dsp/filter.h
The intended snare Q=.5..2.5 is translated to Daisy resonance with `r=(1-1/(2Q))^4`. Daisy's damping expression `2*(1-r^.25)` then yields `1/Q`, bounded .4..2. No cap/remapping of the Snappy blend. The existing Daisy filter type is retained; this is not a claim of bit-identical Plaits sound. Existing zero drive is retained because explicit linear damping now controls the filters.

Impact adds `1 + .7*accent*fm_envelope` to the existing combined body/noise signal. The existing ~7ms envelope removes the boost into the tail. No extra oscillator or noise generator is introduced. The existing final output clamp remains.

## Independent kick transient

A new `SetClick` parameter controls the dedicated click + attack-noise level. Tone retains its original final lowpass/brightness function. Click uses descriptor 0x1B0, verified empty/in-bounds by executing the complete native registry constructor. The initial 0x1AE candidate is a native occupied descriptor and was rejected during pre-delivery testing. Click=0 removes this dedicated path, not the oscillator/pitch-sweep transient. Default 45% matches the existing default Tone; old projects lacking the new attribute migrate to their saved Tone value. New `bento_drum_v2_click` attribute persists independently. Other native properties/automation lanes are unchanged.

Kick state grows 200 -> 204 bytes; native slot 232 -> 236 bytes. Total original state remains within the existing 0x1500 reservation. The UI-owned 128-byte Click extension uses aligned 24043D80..24043DFF, after the view/cleanup state and before M7 diagnostics. It is committed under the original entry sequence and serial; M7 invalidates reader-only lines. No new heap limit, MPU region or startup hook.

## Hi-hat

Only the square-noise DaisySP model is linked: six detuned square oscillators, tone filter, adjustable clocked noise and decay. RingMod source is preserved in earlier snapshots but is not implemented/linked here. Its Q-style resonance arguments are corrected using the same damping conversion. Final HP Q=.5 maps to normalized resonance 0.

Engine ID 5, exact carrier length 144023 at mono 48k/16-bit with the existing signature. Snare stays ID 3 / 144021; kick ID 1 / 144019. Hi-hat 220-byte DSP state reuses the same per-slot 288-byte auxiliary pool as snare. A slot owns one model at a time; separate slots permit mixed kick/snare/hat playback. No new audio pool or heap carve-out.

Hi-hat UI: Level, Tune, Decay, Tone, Impact, Noise; native mix row. Initial Tune 207Hz gives nominal metallic source 414Hz before oscillator ratios. Tune range 100..1170Hz before native pitch modulation. Starting Decay 70, Tone 65, Impact 65, Noise 30. The initial Decay 35 preset was too short in native-output testing; 70 is a longer closed-hat starting setting. Control ranges otherwise follow the inherited engine.

## Display and scope

K13/K14 leaf draw filters are retained. Third native row becomes visible for kick Click; it remains hidden for snare and hi-hat. Lower sampler graphics, buttons and tabs stay suppressed. Ordinary samples use native fallbacks. Existing hidden lower-page hit targets remain an inherited limitation; visual suppression is not a complete custom editor.

No bootloader modifications, automatic flashing, native note/automation-format change or controller change. Build uses exact original stock guard, word alignment, application-only bounds and exact reverse-to-stock patch validation. Software emulation cannot establish physical display behaviour, real-time performance headroom or device installation success.

## Validation and limits

Final main image SHA-256: `a1af49ad4331d11552a8788222443a02f43018bbcc22aa14514da92357905ec3`.
Image size 1,562,816 bytes, aligned to four bytes. 77 declared patch records reverse exactly to original stock. All write ranges lie in 08040000..08200000. Controller remains SHA-256 `8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d`.

Earlier pre-delivery checks caught the newly added save attribute count, the initial too-short hi-hat preset, and the occupied 1AE descriptor. They were corrected before packaging. Passing fixtures with a zero-filled registry alone were insufficient; the complete native-constructor check is now part of the reproducible wrapper. No failed candidate was delivered.

Final test evidence is saved beside these notes. Host output uses the fork's actual C++ DSP with host math; compiled ARM tests exercise the embedded math and native audio routes. The host sweep covers 21 Snappy values, expected damping 1/Q and bounded adjacent RMS change, plus 108 hi-hat tuning/tone/noise/decay combinations. High Snappy/Impact settings can engage the existing output clamp on transient peaks; no new limiter/clipper is added. Physical audio character, encoder feel and sustained multi-track CPU load remain device checks.

Final results: 260 integration tests passed; 16 direct draw tests passed; full native registry constructor passed (15,968-byte allocation, all ten custom slots empty and in bounds); host sweeps passed. Exact isolated input source hashes are recorded in SOURCE_HASHES.json.
