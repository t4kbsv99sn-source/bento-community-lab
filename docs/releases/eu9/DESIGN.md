# EU9 integration

Branch fix/eu9-device-feedback, from EU8 commit 24ac051. No audio DSP changes, new fixed SRAM, native note-size changes, MPU/heap/stack/vector/recovery/controller or bootloader modifications. Synth cave remains byte-identical to EU5/EU8.

## Lock condition dial
EU8's editor skipped notes without parameter locks. Its header then reread Always, so each small turn restarted near 98% or the first A:B entries. EU9 permits immutable conditional records whose underlying lock word is zero. The existing guarded codec already accepts these records; no new tag/version/structure is introduced. Native notes retain the condition before any lock exists; adding a lock carries it forward. XML retains the existing bento_lock_condition_v1 field alongside zero L1/L2. A condition-only record changes no audio or note trigger condition. Explicit clear-both removes it. Allocation failures still refuse atomically. Removing one lock can retain the shared condition for later edits. The same finite pool is used.

Tests now execute repeated native 08171E44 encoder turns through the native0xCF event handler, header refresh and note storage, rather than supplying finished values to the lock handler only. Both range endpoints and later lock creation are covered.

## Permanent Select
The earlier F9/FA changes affect the pop-up menu. The permanent top header uses a separate 1C4-byte structure with six 48-byte action records at+74. Native 08134800 generates this structure;0817FAF8 builds its actual buttons.

A guarded prologue trampoline at08134800 calls the unmodified native body 08134804, then seq_toolbar(model,out,native_changed). On supported one-shot SEQ pages it finds Undo 1032, inserts Select 1051 into the following free action (shifting occupied records only as far as a free slot), preserves all other actions, and returns changed when its text/state differs. If full, unsupported or uninitialized, it leaves native data unchanged. It copies Undo's native dimensions/style and changes only label/ID/visibility/disabled flags. Select ON updates the existing action rather than adding another. Original pop-up changes are retained.

The native generator's clock/metronome-formatting portion and GUI-parent routing are fixtures in the new header test. Actual native header copy/prologue return, header constructor 08180198, application 0817FAF8 and action emission 0817FE70 run on ARM. Tests confirm same-size adjacent visible buttons and routing to existing Select handler. A hardware screen is still required to confirm actual presentation.

## Velocity UI
Native Euclidean encoder 5 value override becomes a blank; eu_glyph_paint replaces that value rectangle with paletteF1 black and five paletteF2 white bars. It uses the real native value label's rectangle and16px font-height region, not a colored extra row. The original sequencer painter still runs first. Mode order/state and DSP velocity algorithms do not change. Encoder 6 key 195 joins the existing guarded kick_ui_increment multiplier of5; all other nonsynth encoders retain their original response.

## Patcher
A minimal byte delta is derived only from the exact supported original main image and the verified EU9 result. Browser and Python implementations check original main/controller hashes, input/output sizes, sorted nonoverlapping bounds, and finished image hash before creating output. Both emit the unchanged controller, synth markers and the tester's own original pair for restore. The browser is a self-contained local HTML file using Web Crypto and an uncompressed ZIP writer; Python uses only its standard library. No network requests, device connection or flashing. The downloadable patcher does not include original firmware image files. No legal/license conclusions are claimed for binary deltas; inherited source licenses remain intact.

