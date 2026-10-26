# Integration roadmap

## Approval boundary

These are prototypes. Obtain approval for the visual direction before firmware integration. Motion's proposed encoder arrangement and the future macro page require specific workflow approval. Preserve synth screens and all current gesture handlers. No firmware files were edited during this study.

## Incremental implementation

1. Branch from the latest owner-approved firmware, not from this documentation study's snapshot by assumption. Reconcile P19 and subsequent motion work first. Keep this kit in `design/bento-playground/`.
2. Introduce a presentation-only StepVisual snapshot: active, velocity, selected, playing, lock kinds/values, note probability, note trigger condition and lock condition as distinct fields. Read native state without modifying note objects or publishing audio commands.
3. Bind a painter to the existing one-shot rectangles. First retain native fonts, colors, touch handlers and header actions; add only velocity measures and distinct selection/playhead marks. Keep old painter selectable by a compile-time switch.
4. Add lock rails only after the target/value decoding is verified for each engine. Do not derive a fake normalized value from the lock-present bit. Preserve text fallback for unknown kinds. Preserve existing `*` modulation markings.
5. Apply typography and spacing refinements within existing bounds. Keep the header visibility lifecycle through `header_actions.c` and `header_sync`; do not bypass it.
6. Integrate motion graphics only after the native A–D editor adapter exists. Preserve clip ownership, hold/release capture, fixed duration semantics, event retention on shrink, Undo/Copy/Delete and existing automation precedence. Add a separate motion-period bracket; do not silently resize the clip.
7. Refine existing Performance controls before considering assignable macros. The concept requires assignment persistence, min/max and polarity semantics, precedence and a clear approved entry point.

## Renderer architecture

The pure `renderer/design.js` module separates visual input from browser interaction. It exports fixed-size SVGs using rectangles, straight lines and sampled procedural paths. `preview.js` owns simulation only. Port the drawing formulas to the existing native fill/outline/text primitives; an SVG interpreter is unnecessary on the device.

Painter contract: receive immutable visible state, bounds, native palette indices and a drawing context. Return dirty rectangles. Do not allocate, alter model values, call the transport, touch M7 state or change navigation from paint. Cache formatted strings until values change. Resolve selected pad/track colors through native APIs.

## Redraw and resource budget

The L8 frame is 1280×480 = 614,400 bytes. Avoid a second full frame or RGBA backing buffer. A 157×87 cell is13,659 pixels. A playhead transition should invalidate at most the old and new cell decorations, restoring from state so the cursor never erases a selection or lock. Use native redraw flags; understand that the existing partial grid paint only moves its cursor before adding a custom overlay.

Keep an initial32-step visible-state cache below1KiB and a curve cache of at most256 integer coordinate pairs (1KiB with16-bit coordinates). These are proposed upper bounds, not approved RAM reservations. Check linker and heap ownership before allocation. Full redraw on page entry; value-driven redraw thereafter. Start visual animation at20Hz and measure rather than assuming it is free. Long automation timelines should decimate to pixel columns without discarding stored data.

The proposed graphics need fills, outlines, integer line rasterization, tiny glyphs and text. Anti-aliasing, opacity and arbitrary RGB in browser exports are preview conveniences; quantize to existing CLUT colors and use solid lines on hardware. No audio waveform analysis, FFT or GPU effects are needed. Precompute curve points when control values change. Browser timings do not predict hardware load.

## Acceptance and rollback

Verify screenshots at native resolution with the firmware's own fonts and widget tree, then test on device: touch selection, pad hold/release, playback cursor, locks/probability/conditions together, long labels, mute feedback, track colors, transport stop/restart and all supported track engines. Measure M4 paint duration and missed UI deadlines while M7 runs a demanding project. Compare audio behavior and M7 application bytes when only M4 visuals change.

Retain exact original paint path behind the feature flag and a small scoped commit. Do not change bootloader/controller, introduce speculative memory addresses or ship a flashable artifact from this visual package. Native header harness output alone is not device validation.
