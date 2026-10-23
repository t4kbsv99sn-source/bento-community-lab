# Project status — 23 October 2026

## Hardware observations
| Version | Maintainer-observed result | Next-use status |
|---|---|---|
| K7 | Kick plays; two rows of controls work; sampler visuals remain | Working baseline |
| K8 | Black screen, lit pads/buttons | Failed; preserve source, do not use as baseline |
| F1 | Black screen reported; built on K8 | Failed; preserve EQ/compressor/clipper work |
| K9 | Same black screen despite memory-permission repair | Failed; hypothesis incomplete |
| K10 | Unable to program / verify main firmware | Rejected; file was two bytes short of word alignment |
| K10a / 1.6KA | Installs and boots; visuals unchanged | Packaging corrected; visual approach failed |
| K11 / 1.6KB | C1 marker appears; visuals still present | Hook runs, visual cleanup failed |
| K12 / 1.6KC | Maintainer photo shows W1; sample waveform area blank, grey lines/envelope/LFO remain | Direct waveform interception confirmed on hardware |
| K13 / 1.6KD | Maintainer confirms page is clean | Confirmed display baseline |
| K14 / 1.6KE | Boots; snare plays after manual carrier installation. Snappy squeaks above ~20–25%, Impact weak, kick click needs separate control | Current hardware baseline; sonic fixes in K15 |

Earlier versions were imported for preservation, not newly hardware-validated during this Git setup.

## Current work
K16 / 1.6KG adds explicit native display restoration on synth-to-sample load, volume-only velocity and kick/snare/hi-hat targets on the existing two step-lock encoders. The maintainer reported stale snare labels when loading a sample; K15 had not yet been installed. New synth locks use model-specific IDs, preserve legacy lock encoding, and do not consume native A–D automation lanes. Final software validation is recorded below; hardware validation remains pending.

K15 / 1.6KF branches from K14. Maintainer chose a punchier existing snare attack (no added noise burst), an independent kick Click encoder on the third row, and an 808-style metallic hi-hat. Correct the Snappy filter/API mismatch rather than capping its range. Final isolated build passed 260 integration tests, 16 direct-drawing tests, the complete native registry constructor check and host DSP sweeps. Hardware validation remains pending.

K14 automatic snare carrier creation passed substituted filesystem tests but did not produce a discoverable file on the maintainer's device. Supplying the exact `BENTO_Synth_Snare.wav` manually worked. Future releases include explicit SD content. The device-side automatic-creation issue is not claimed resolved.

Native display entry interception is hardware-confirmed through K12/K13. Tests do not reproduce the complete physical display or establish real-time CPU headroom. Unicorn 2.1.3 is pinned because 2.1.4 produced inconsistent conditional-instruction execution.

## Preserved future work
- Additional drum synth engines: `k8_work/bento_controls`.
- EQ, compressor, Auto Makeup and soft clipper: `fx1_work/track_fx` and `fx1_work/integration`.
- Bring features back one at a time after a working base is established.
- LFO/modulation into custom kick parameters is not implemented. Native pitch processing is a promising route, not a confirmed complete modulation integration.
- A custom synth editor remains an alternative; a new sequencer is not currently authorized as the next implementation.

## Main-image identities
K7: b067a4889d3c0bce4b9f95705b3d7d8df7eea9a5128c4940b46c29d539fd6294
K8: 91c579e24ef93b0a0789df9521cc93dd687cba046c765954c0215410a4fa9e1c
K10a: f60df0a8e3d993b85ce2c4054418551d11a2c65ec9c453a38138f1762be27fce
K11: b0c4d4689d6457925e4b91bf141352dd88c575dc2dbd7a736722ff0c748579e5
K12: d75e14f1d659f379a4049f94beb0b59cb0693511be243bf35ac55c524ede3f0b
Unchanged controller: 8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d

## Boundaries
Never modify the original bootloader. Local commits and release builds are authorized; no public publication or automatic flashing. User is not a programmer and wants simple installation instructions and minimal questions.

K13 main SHA-256: 7c71586da21c977543d879424641ff377ade93f7c0310eb2ecf48ac362b6a92b

K14 / 1.6KE is now built: synthetic snare, fivefold custom synth encoder response, confirmed K13 drawing filters retained. Final run: 246 checks passed. Exact isolated rebuild matched. Maintainer subsequently confirmed startup and snare playback after installing the explicit carrier. Physical knob feel is not separately confirmed.

K14 main SHA-256: 13481d0a402e4a1b1a03e0aaac8a73f0a041194c60904346f713f9ff86756806

K15 main SHA-256: a1af49ad4331d11552a8788222443a02f43018bbcc22aa14514da92357905ec3
K15 size: 1,562,816 bytes; 77 patch records, exact stock reversal; controller unchanged. All three explicit SD carriers and K14/stock restore pairs accompany the release.

## K16 final validation
K16 / 1.6KG validation: PASS, pending hardware testing.
Full suite: 273 tests, 272 passed; one obsolete invalid-ID fixture failed because ID 12 is now a valid kick Tune lock. Changed that invalid example to unassigned ID 30, reran the affected test successfully (FINAL_RECHECK.txt). No production source or firmware bytes changed for this correction. Original full log is preserved in TEST_RESULTS.txt.
13 new K16 checks passed in the full run: native display override/config reset, model-specific picker, save/load/clear, all new ordered pair encodings, note transport, send isolation, engine scoping, two synth locks matching manual knob audio, normalized native velocity and volume-only output.
Direct drawing checks: 16 passed. Native registry constructor: passed. Host DSP sweeps: passed.
Independent isolated rebuild matches byte for byte. All 115 source inputs match the isolated workspace. Exact stock reversal, file alignment, unchanged controller and existing application/heap/MPU boundaries checked.
Main SHA256: 5e72971b31388201454a71b0be7cc61ad40915bda3a75e635d104dd89346a03d
Main size: 1562816 bytes. Patch records: 77.

Hardware test remains pending. K14 remains the latest maintainer-confirmed boot/playback baseline.

## Separate feature branch: TF2 / 1.6T2
Maintainer authorized a K16-based branch with a second Tracks page opened by double-tap TRACKS, per-track EQ, compressor with Auto Makeup, and soft clipper. Branch `feature/k16-track-fx` leaves main/release K16 unchanged. Uses preserved DSP source with a new K16 bridge, not the failed K8/F1 binary. All effects default off; normal single tap and hold shortcuts stay immediate.
Known F1 memory placement is avoided: all new state is in 24040000..24042000, inside native M4 permissions. Reserve 8 KiB from the M7 heap; leave native MPU/stacks/vector/recovery code unchanged. M4 and early-startup adapters contain no floating-point save/restore. See docs/releases/tf2/DESIGN.md for ownership, hook addresses, save/load and first-version limits.
161 software checks pass. Three isolated builds match exactly. Source inputs match; exact stock and K16 reversal, alignment and unchanged controller checked. Native startup with explicit MPU enforcement and FPU disabled passes on both cores. This does not prove device boot or real-time CPU/heap headroom. Hardware test remains pending. K14 remains the latest maintainer-confirmed boot/playback baseline.
TF2 main SHA256: 86f55d87c79c2bcc500f574420e3854f0ab842a5fe9d43423db6f5ee0926400b
Main size: 1577828 bytes. Restores for K16, K14 and stock accompany the private release.

## EU1 / 1.6E1 — Euclidean feature branch
Double-tap SEQ from the one-shot step sequencer opens a native control page for the selected drum. Pulses, rotation, new-hit velocity and a paged text preview prepare a pattern; Apply replaces only that drum within the current clip, while Cancel changes nothing. Retained hits keep IDs/velocity/conditions/offsets/locks. New hits use native IDs and Always. No added automation lanes or audio engine. Native notes save through the existing project format; generator control values are temporary.

EU1 / 1.6E1 software validation: PASS; hardware pending.
SAFETY_RESULTS: 6 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
EUCLIDEAN_RESULTS: 17 passed
DSP_RESULTS: 38 passed
K16_REGRESSIONS: 61 passed
Total: 178 passed.
Main SHA256: 2a6d6cc628f53493c1430706fc0fc5f76a6c55e953a4b7613daf329acaea0129
Main size: 1581620 bytes; word aligned.
Independent isolated rebuild matches byte for byte.
Exact stock and K16 reversal; source inputs match; controller unchanged.
M7 application identical to TF2; MPU/stack/bootloader unchanged.
Native undo storage, engine queue and UI services are substituted in targeted fixtures.
Physical startup, screen, Undo and save/reload need maintainer testing.

Controls initially collided with three occupied native descriptor IDs; the registry guard refused to open instead of overwriting them. Corrected to six constructor-verified empty IDs 190..195. Early failed test evidence remains outside the release logs. No failed candidate was delivered. See docs/releases/eu1 for scope and first-device checks.

## EU2 / 1.6E2 — live Euclidean branch
The maintainer requested independent lengths for each drum pad, live encoder edits and clip-scoped settings. EU1 is preserved; feature/euclidean-live adds an M7 native-clock renderer and per-pad Manual/Euclid mode, leaving manual notes intact. Controls are Pad, Length, Hits, Rotate, Velocity, Mode, Preview Page and Return. Settings save under versioned track params keyed by clip slot/pad; native Copy/Move/Delete Clip operations and Undo are explicitly not integrated yet. Generated notes do not inherit manual step locks or conditions; those return in Manual mode.

EU2 / 1.6E2 software validation: PASS; hardware pending.
SAFETY_RESULTS: 6 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
LIVE_RESULTS: 18 passed
DSP_RESULTS: 38 passed
K16_REGRESSIONS: 61 passed
Total: 179 passed.
Main SHA256: 8435e0539cb324bccefccaa887a062349eea21b84d5dcee2b9fc744c95ffefc5
Main size: 1583412 bytes; four-byte alignment.
Independent isolated rebuild identical. All 164 isolated source inputs match.
Exact stock and K16 reversal; controller unchanged; original bootloader untouched.
Native MPU, vector/recovery region, stack and TF2 heap boundaries unchanged.
Compiled live tests use real native clock conversion, note routing and adapters; allocator/model/XML services/queues are fixtures.
Hardware boot, CPU/cache behavior, screen, physical save/reload and swing remain unconfirmed.
Native clip copy/move/delete does not carry/reset these slot-based settings; native Undo does not cover controls.

During development, timing tests corrected the difference between stored 960-unit step positions and native playback ticks (240 for default sixteenths). Final playback tests compare actual 7-step versus 16-step hit times across 48 steps and run the patched entry/gate. K14 remains the latest hardware-confirmed baseline. See docs/releases/eu2.

## EU3 / 1.6E3 — access correction and encoder integration
Maintainer reports testing E1 but double-tap SEQ reaches the native piano roll, preventing Euclid testing. Maintainer also reports kick controls 7/8 bleeding into snare UI, synth-lock displayed values not matching instrument units, snare sonic fix satisfactory, and hi-hat marker not found. E1 boot/navigation are supported by the report; the installed device hash was not independently read. No E1 Euclidean playback success is claimed.

EU3 preserves the native SEQ gesture, uses Right/Left encoder banks and Up/Down native sequence actions, removes EU2 controls 6–8 and puts lock controls on 7/8. Normal Step/Sequence choice remains. Synth blank widgets are explicitly cleared; displayed synth-lock units match the editor without changing stored raw values or DSP. Existing note locks can feed matching generated cycle steps through the native cursor and lock transport. Exact HiHat marker accompanies the release explicitly.

EU3 / 1.6E3 software validation: PASS; hardware pending.
SAFETY_RESULTS: 6 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
LIVE_RESULTS: 19 passed
CONTROLS_E3_RESULTS: 11 passed
DSP_RESULTS: 38 passed
K16_REGRESSIONS: 61 passed
Total: 191 passed.
Main SHA256: 4fc3c619634ed0c4159a95f394fe16189c0daff36de5a6db2c11ee14ba7b02ac
Main size: 1595152 bytes; word aligned.
Independent isolated rebuild identical; 173 source inputs match.
Exact stock and K16 reversal; controller unchanged; original bootloader untouched.
Native MPU/vector/recovery/stack and TF2 heap boundaries unchanged.
UI relocation, real arrow branch, actual widget clearing, lock units, native time conversion/cursor and generated-lock transport checked.
Physical arrow mapping, display, audio deadlines/cache behavior and SD save/reload still require device testing.

The earlier isolated controller run failed due to test service limitations (owner type resolution by pointer identity, NULL caption handling and too-small instruction budget for first bank allocation); the corrected fixture plus actual widget test pass. Production checks do not constitute hardware confirmation. Clip Copy/Move/Delete and generator-control Undo remain outside this build.

## EU4 — CPU optimization and inaccessible Euclidean mode
Maintainer reports high CPU use from drum synths and a smaller increase from Track FX, and still cannot enter Euclidean mode. Installed device hash was not independently read. EU4 branches from EU3. It preserves the original bootloader/controller and all previous features.

The concrete Euclidean entry failure is the EU2/EU3 pointer guard: native M4 allocator starts at C6000000 but the guard rejected that region. Confirmed in native reset data and a test entering the real event handler with the real native allocator. EU4 accepts the native C6..C8 pool; no MPU changes. Audio-generation test uses the same pool.

Snare/hat coefficients move from every sample to block setup with unchanged formulas and state layout. Kick diagnostics accumulate peak locally; DSP LTO inlines calls. Channel-strip steady controls and coefficients skip redundant updates; normalized EQ avoids division by one. Polyphony, tails, lock semantics and project encoding remain unchanged.

Measured ARM instruction savings (not device cycles/CPU meter): kick 2.8%, snare 78.0%, hi-hat 68.1%; EQ 27.0%, compressor 26.9%, clipper 18.3%, complete strip 22.0%. Tested audio matches sample for sample. Hardware CPU/cache timing and audio confirmation remain pending.

EU4 / 1.6E4 software validation PASS; hardware pending.
SAFETY_RESULTS.txt: 7 passed
GESTURES_RESULTS.txt: 6 passed
INTEGRATION_RESULTS.txt: 12 passed
PREVIOUS_CONTROLS_RECHECK.txt: 38 passed
LIVE_RESULTS.txt: 20 passed
CONTROLS_E3_RESULTS.txt: 12 passed
DSP_RESULTS.txt: 38 passed
K16_REGRESSIONS.txt: 61 passed
Total: 194
Main SHA256: bf3c1dc83c2bd88b5c85ed9db44734fea9cbecd9cc6d505c7f752f213a4b5919
Main size: 1595152
Independent rebuild identical; exact stock/K16 reversal and source inputs verified.
Controller and original bootloader unchanged. Native MPU/heap/stack boundaries unchanged.
Initial previous-controls log ended without a test summary despite process exit 0; explicit rerun passes all 38 (included).
Synth and FX instruction/audio comparisons are included separately; counters are not hardware cycles.

## Maintainer confirmation of EU4
Maintainer reports EU4 is working, including access to Euclidean mode. The delivered image is bf3c1dc83c2bd88b5c85ed9db44734fea9cbecd9cc6d505c7f752f213a4b5919; device hash was not independently read. Maintainer requests generated step/playhead/length feedback and longer hi-hat decay. No device CPU percentage or sonic comparison was separately quantified.

## EU5 Euclidean display and longer hi-hat
EU5 / 1.6E5 software validation PASS; hardware pending.
SAFETY_RESULTS: 7 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
LIVE_RESULTS: 20 passed
CONTROLS_E3_RESULTS: 12 passed
DSP_RESULTS: 38 passed
EU5_RESULTS: 7 passed
K16_REGRESSIONS: 61 passed
Total: 201
Main SHA256: a7ad3565213729d8bee88daa6f204d0adf93a83b098933b6a0e3e695e1f8f1d9
Main size: 1595876
Independent isolated rebuild matches. Exact stock/K16 reversal, alignment and source input hashes verified. Controller and original bootloader unchanged. Native MPU/heap/stack boundaries unchanged.
Additional actual M7->M4 phase publication/stop check passes. Host hat render confirms unchanged 50/70% output and audible 2..3sec tail at100%.
Initial grid test setup compilation raced with another test process; all final checks ran sequentially. An initial phase fixture expected 15 but the last audio block also included boundary 16; final check compares against the actual processed M7 step.

## EU5 final lifetime refinement
EU5 / 1.6E5 FINAL software validation PASS; hardware pending.
SAFETY_RESULTS: 7 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
LIVE_RESULTS: 20 passed
CONTROLS_E3_RESULTS: 12 passed
DSP_RESULTS: 38 passed
EU5_RESULTS: 8 passed
K16_REGRESSIONS: 61 passed
Total: 202
Main SHA256: da6cb63772f52eb7f191374368980baba9b62365a227b0635da8b82ca278d6ed
Main size: 1595876
Independent fresh-source rebuild equals tested eu5_release image. Exact stock/K16 reversal, alignment, source inputs, native MPU/heap/stack boundaries verified. Controller and original bootloader unchanged.
Additional M7 phase/stop check and host hi-hat decay comparison pass. Short hats retain the old lifetime; accepted Decay locks above 70% enable the longer lifetime.
New suite initially exited without summary under Unicorn callback GC; complete recheck and final gc-disabled suite pass all 8. Test gate rejects missing summaries. Prior 201-check package was superseded before delivery to avoid increasing the processing lifetime of short hats. Existing 194 checks passed on the final image; new 8-check suite rerun from the fresh-source workspace.

## Maintainer feedback on EU5
Maintainer confirms the Euclidean visuals/generator work well and loves the hi-hat. Reports that native additions are silent and generated steps cannot be selected/velocity-edited/locked. This is the procedural generator/native-note separation documented in EU5, now being integrated. Delivered EU5 hash da6cb63772f52eb7f191374368980baba9b62365a227b0635da8b82ca278d6ed; device hash not independently read.

## EU6 native editable Euclidean patterns
EU6 / 1.6E6 software validation PASS; device testing pending.
SAFETY_RESULTS: 7 passed
GESTURES_RESULTS: 6 passed
INTEGRATION_RESULTS: 12 passed
PREVIOUS_CONTROLS_RESULTS: 38 passed
LIVE_RESULTS: 20 passed
EDITABLE_EU_RESULTS: 8 passed
CONTROLS_E3_RESULTS: 12 passed
DSP_RESULTS: 38 passed
EU6_RESULTS: 10 passed
K16_REGRESSIONS: 61 passed
Total: 212
Main SHA256: 9c02957a375987caf9a8734048e631f4f9eac0cbe614e3c8836a01183e6abc3b
Main size: 1597456
Independent isolated rebuild matches; exact stock/K16 reversal, source-input hashes, alignment and controller checked. Original bootloader/MPU/stack/heap reservations unchanged.
EU5 synth cave identical; longer hi-hat preserved. One-time native scratch allocation12KiB is guarded and reused.
Additional per-pad1:2 condition/phase/stop and editable-setting XML round-trip checks pass (PHASE_RESULTS).
Native GUI-parent and engine-queue transport are substituted in targeted tests; physical screen/cache/audio timing/SD round-trip still need device checks.
Manual now keeps the generated/edited native notes. Regeneration changes native notes with Undo; generator controls are not Undo-integrated. Timing offsets/repeats still use the generated-grid limitation.

## EU7 / 1.6E7 — Select and conditional locks
EU7 / 1.6E7 — software validation PASS; hardware testing pending.

EDITABLE_EU_RESULTS.txt: 8 passed
DSP_RESULTS.txt: 38 passed
GESTURES_RESULTS.txt: 6 passed
SAFETY_RESULTS.txt: 7 passed
LIVE_RESULTS.txt: 20 passed
CONTROLS_E3_RESULTS.txt: 12 passed
INTEGRATION_RESULTS.txt: 12 passed
VISUAL_RESULTS.txt: 10 passed
PREVIOUS_CONTROLS_RESULTS.txt: 38 passed
EU7_RESULTS.txt: 11 passed
K16_REGRESSIONS.txt: 61 passed
Total: 223 passed.
Main SHA256: 8041ea563b86b41920b8641c57df32abfa0afc40192ca27a27af24ae9efd1674
Size: 1600176 bytes.
Independent isolated rebuild byte-identical. Exact stock and K16 reversal, source input matching, application bounds and word alignment verified. Unchanged controller/synth DSP, original bootloader/vector/recovery/MPU/stack regions checked.

Select 1051 beside native Undo; persistent 256-step selection; PROJ+encoder 3 changes a separate condition shared by both locks. Encoder 6 displays Locks when. Supports existing probability/A:B labels, normal and Euclidean cycles, XML save/load and existing native note edits. 64KiB bounded immutable conditional records retain old references for Undo/copy. No Fill support added. EU6 restore included. Private Git restored from durable backup version 12 before this branch because the available local EU5 worktree was stale.

## EU7 maintainer feedback / EU8 correction
Maintainer reports lock-condition control/readout and Select button missing. Full native registry inspection proves 1E5 collides with Attack; native empty-widget hiding also explains missing readout. EU8 fixes these, restores ordinary Prob after shift, and places Select beside Undo in both menus using native popup layout/emission tests. Adds live velocity modes/depth on encoders 5/6 and five-bar glyphs; new hits 100, retained velocities preserved. Hardware validation remains pending.

EU8 / 1.6E8 — software validation PASS; hardware validation pending.

CONTROLS_E3_RESULTS.txt: 12 passed
DSP_RESULTS.txt: 38 passed
EDITABLE_EU_RESULTS.txt: 8 passed
EU7_RESULTS.txt: 11 passed
EU8_RESULTS.txt: 14 passed
GESTURES_RESULTS.txt: 6 passed
INTEGRATION_RESULTS.txt: 12 passed
K16_REGRESSIONS.txt: 61 passed
LIVE_RESULTS.txt: 20 passed
PREVIOUS_CONTROLS_RESULTS.txt: 38 passed
SAFETY_RESULTS.txt: 7 passed
VISUAL_RESULTS.txt: 10 passed
Total: 237 passed.
Main SHA256: 880cee6992eb4ebdd296ace06a386fdc3ac2674c03176dd669019ea6be8c0dd0
Size: 1601460 bytes.
Independent isolated rebuild matches exactly. Exact stock and K16 reversibility, source-input hashes, word alignment and application bounds verified. Native controller and synth cave remain unchanged. Original bootloader/vector/recovery/MPU/stack regions unchanged. Native menu construction/application/layout/action emission, complete registry/header widgets, hit-count modes across loops, saved-step preservation and mode XML compatibility execute in the targeted tests. Native GUI-parent routing/SD storage/audio deadlines and physical output still require hardware checks.

## EU8 maintainer feedback / EU9 repairs
Maintainer confirms velocity modes and depth function, asks white symbols instead of text and faster depth. Reports lock condition stops near 98%/first conditions and permanent Select missing. Device image not independently read. EU9 retains condition choices before a lock exists and inserts Select in the separate persistent header.

EU9 / 1.6E9 — software validation PASS; device validation pending.

CONTROLS_E3_RESULTS.txt: 12 passed
DSP_RESULTS.txt: 38 passed
EDITABLE_EU_RESULTS.txt: 8 passed
EU7_RESULTS.txt: 11 passed
EU8_RESULTS.txt: 14 passed
EU9_RESULTS.txt: 6 passed
GESTURES_RESULTS.txt: 6 passed
INTEGRATION_RESULTS.txt: 12 passed
LIVE_RESULTS.txt: 20 passed
PATCHER_RESULTS.txt: 7 passed
PREVIOUS_CONTROLS_RESULTS.txt: 38 passed
SAFETY_RESULTS.txt: 7 passed
VISUAL_RESULTS.txt: 10 passed
K16_REGRESSIONS.txt: 61 passed
Total: 250 passed (243 firmware checks + 7 patcher checks).
Main SHA256: fd156059cd68951b194788b71a4a6565deeab8e655a3fa8f9985213a7433228c
Size: 1601856 bytes.

Independent isolated rebuild byte-identical. Stock/K16 reversibility, application bounds, input/source hashes, word alignment, controller and synth cave checked. Native persistent header construction/application/action emission and real widget turns execute in the new tests; clock formatting, parent routing and SD transport remain fixtures. Browser JS and Python patchers reconstruct the same release and refuse invalid inputs. Original bootloader, native note/voice/MPU/heap/stack/vector/recovery layouts and audio DSP unchanged. No device flash performed.

Offline browser/CLI patcher and private reviewer source package prepared.

## EU10 / 1.6EA — synth p-lock list cleanup


249 firmware tests passed across 14 suites. Six new tests cover engine-specific target lists, original sample ADSR, send mappings, first/last synth target encoding, sample restoration and preservation of saved legacy ADSR locks. All inherited UI, native note/lock, Euclidean, condition, Track FX and DSP regressions passed.

Independent fresh-source rebuild is byte-identical. All 288 isolated source inputs match the repository. Exact stock/K16 reversal, application bounds, four-byte alignment, unchanged controller and unchanged EU9 synth cave are checked. Original bootloader, vectors/recovery, MPU, heap/stack reservations and audio DSP are unchanged. No device flash performed.

Main SHA256: 4ed81f1604459f338624fcfd4a22e40b29b992f4e9df4303de1a0564b8b32a37
Size: 1,601,924 bytes. Label: 1.6EA.

Native model/SD and parent services are substituted in targeted fixtures. Physical startup, display, SD round-trip and real-time CPU behavior remain device checks. The existing EU9 offline patcher was not changed and cannot produce EU10.

The first full run's visual suite silently ended without a summary inside Unicorn callback cleanup despite exit 0. The completion gate correctly rejected it. Retaining probe instances until process exit fixes the harness; the complete 10-test visual recheck passes. Production firmware bytes were unaffected. Other suites completed normally; no failing assertion was waived.

Scope: sample ADSR hidden for drum synth pickers, engine-specific targets retained, old locks preserved. Modulation-matrix engine destinations remain unfinished; evidence and next steps are in docs/DRUM_MOD_MATRIX_PLAN.md. Chord insertion is planned in docs/CHORD_ENTRY_PLAN.md and not implemented.

## Chord composer C0 — source checkpoint, NOT firmware

Maintainer approved chord/progression design and requested implementation. A separate feature/chord-composer branch adds the portable musical core, audition note-ownership logic and a standalone native insertion proof. 26 software tests pass, including host/Cortex-M4 parity across 720 combinations and native note/ID/publish tests. Settings codec exists; saved native-note group membership does not. No screen controls, pad routing, clocked live preview or project integration are installed. No new firmware is delivered. EU10 main SHA remains 4ed81f1604459f338624fcfd4a22e40b29b992f4e9df4303de1a0564b8b32a37. See chord_work/README.md and docs/CHORD_INTEGRATION_EVIDENCE.md for exact remaining work and fixture limits.

## CH1 / 1.6H1 — installable chord/progression insertion test

First device firmware connects C0 to a native three-row editor, a persistent
Chord header action and Insert/Back. Fifteen chord types, voicings/inversions,
strum, start/end, velocity/grid, twelve progression presets, root/key/five scales,
per-chord edit selection, duration and automatic voice leading are available.
Inserted chords are ordinary native notes with one native Undo snapshot.
No automatic flashing; device results remain pending.

284 checks passed across 15 suites (249 inherited firmware checks plus 35 chord
core/native/UI checks). Native widgets and encoder events execute, as do native
note containers, IDs and publication. Model/navigation/font, Undo storage and
engine-queue services remain fixtures; hardware startup/display/audio/SD/Undo
must still be verified. The earlier visual-suite process again truncated once;
the completion gate rejected it. A fresh complete run passed all 10 tests. A
fresh-process runner is provided for future native-runtime isolation. No test
assertion was skipped or weakened.

Two independent isolated builds match byte for byte.
Main SHA256: 20c36100c2d44d3d0743e8e9ab7833eafe6c3517b68b0eca688d9e01dc3e9bca
Size:1,610,892 bytes. Label:1.6H1.
Controller SHA256:8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d.
Entire M7 application is byte-identical to EU10. Exact stock/K16 reversibility,
four-byte alignment, code bounds, unchanged vectors/recovery regions and source
inputs verified. No new fixed RAM/MPU/stack reservations; bootloader untouched.
Native descriptor allocation is3E60 bytes/499 entries; proposed out-of-bounds
keys were corrected before release, with a canary regression test.

This is insertion-first. No pad chord audition, outlined preview, looping live
preview, saved chord groups, whole-chord block selection or Update is installed.
Draft controls are not saved; inserted notes use normal native project storage.
Keep the approved full workflow as the next integration work, rather than
presenting this test as its completion.


## CH1 maintainer feedback

Maintainer reports that neither Chord nor Select is visible on the device. CH1's
software header fixtures therefore did not establish visibility in the real UI.
The shared header generation/application path is under investigation; no fix is
confirmed and no replacement firmware has been built. Display work is paused at
the maintainer's request.
