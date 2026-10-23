# EU10 target list filtering

Branch feature/eu10-synth-targets from EU9 commit 6babf993. This release implements the p-lock list portion of the request. The modulation-matrix expansion and piano-roll chord entry remain planned, not implemented. Read docs/DRUM_MOD_MATRIX_PLAN.md and docs/CHORD_ENTRY_PLAN.md.

For samples, picker indices and kinds remain 0..11 exactly. For synths, compact picker 0..5 maps native kinds 0..5;6/7 maps Delay/Reverb kinds 10/11;8 onward maps the engine's own synth kinds (kick 12..19, snare 20..24, hat 25..29). Counts become 16/13/13. Every choice label uses the mapped stored kind, not a stale array index. Stored kinds, lossless pair codec and XML do not change.

A selected old sample ADSR lock on a synth is preserved in the note/project but no longer binds the synth lock encoder to a hidden target. The encoder falls back to its ordinary default target. No old lock is erased, reinterpreted or converted to a synth control. Loading/selecting a sample restores the original target list.

Only UI list/header code changes. Synth cave and M7 audio implementation remain identical to EU9. No native parameter/voice/note layout, fixed RAM, MPU, stack, heap reservation, controller, vectors, recovery or original bootloader changes.

New native ARM tests exercise every engine's filtered names, sample restoration, both send mappings, first/last engine target encoding, and preserving a saved legacy ADSR lock. Inherited synth picker tests are adapted in the regression wrapper; historical K16 source remains unchanged. Earlier EU9 UI/condition/velocity regressions remain required. Native model/SD transport fixtures still limit what the tests establish.
