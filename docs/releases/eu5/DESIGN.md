# EU5 — incremental change from maintainer-confirmed EU4

Baseline delivered EU4 hash bf3c1dc83c2bd88b5c85ed9db44734fea9cbecd9cc6d505c7f752f213a4b5919. Device hash not independently read. Code remains in eu4_work on feature/eu5-visual-feedback; release/eu4-1.6E4 preserves the previous source.

The existing 32 native grid cells display the same integer Euclidean distribution as M7. Native visibility, numbering, colour, trigger-fill and playhead setters are reused. No native notes or clip lengths are rewritten. Native grid reconstruction restores manual visuals on Left. The view caches pattern, phase/page, pad and sequence in the last 16 bytes of the existing UI reservation (Ui<=1472, ending at the unchanged 24041FC0 control). No new fixed SRAM or MPU/heap change.

M7 publishes the last processed grid step and valid flag through existing EuRuntime reserved words 1..3. That runtime is wholly M7-owned. M4 reads an even/stable serial, owner/row/epoch and phase, never writes runtime. Publication cleans the two existing metadata cache lines. Periodic seq_lights_clean and native playback events refresh the display; the native 0815BDE2 adapter is consumed only in Euclid mode. Empty native manual steps do not suppress generated hit display. Long cycles auto-follow in32-box pages. Full screen/hardware cache timing is not simulated.

HiHat retains SetDecay through 70%. Above this, internal decay adds (input-.7)*(.8/.3), extending its existing envelope formulas. Carrier recognition and user-facing0..100 values/locks remain unchanged. Only hats triggered with effective Decay above 70% (including step locks) increase their voice lifetime from 3 to8 seconds, with the native carrier cursor clamped below end until the synth terminates. Kick/snare lifetime unchanged. This allows the new decay to ring without native sample-end truncation. Monophonic retrigger per sound remains.

Historical initial tests and candidates remain outside the delivery. A legacy fixture has a10k-instruction callback budget; avoid initializing the unrelated Euclid UI from seq_lights_clean when no Euclid view is active. The final tick guard checks magic/view/mode first, preserving the native feedback path.

Short hats retain the previous lifetime/CPU cost. The high model-ID bit0x100 tracks this lifetime within the existing M7-owned model word; model() masks it, with no RAM layout change.
