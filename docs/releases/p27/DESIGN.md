# P27 design: performance macros

Owner decisions: PLAN.md (same folder). Source: eu4_work/integration/macro_ui.c,
tests: test_macro.py, render: research/display_emulator/render_macros.py.

## Native facts (stock 1.6.1, verified in the emulator)
- Encoder strip = widget class vtable 081B2838 (constructor 08170598 area,
  literal at 08170590). Eight slot widgets (class 081B28C4) at bar+38+468*i,
  parent +2C = bar. Slot rects: x = 6 + 159*i, y = 406, 158/159 x 70
  (08170F04). The bar's own rect is 0; its contains() (0816FA5C) asks the
  children, so a point on any slot "is in" the bar.
- Stock: the bar's touch entries [4] down, [5] move, [6] up are `bx lr` stubs
  (08143AC1/3/5) and [7] takes-touches (08143AC7) returns 0. No native widget
  in the strip takes touches. The firmware hit test 0816FA10 tests children
  first, then the container (vt[3] contains, vt[7] takes touches).
- Slot: +34 node handle, +9C key, +A0 last posted value, +450/+454 range.
  Labels (class 081B35C0): +A8 value (text +D9), +118 second value copy,
  +3C8 name (text +3F9); 0817E85E sets a label's text; 08170656(bar,i,text)
  overrides the value text (+2C8; 0 = native); 08172066 highlights the three
  labels for 1 s after a turn.
- Bar tick 081703CC drains per-encoder deltas (bar+2398+4*i) into
  08171E44(slot, delta) (only caller). K15 already enters 08171E44 through
  kick_ui_increment(slot, delta). Delta 0 = no change. Native scaling: a full
  0..1000 range is ~160000 raw units at slow speed (acceleration on top).
- Parameter changes reach the model as CF {CF, node, key, value} (081403EC,
  FX wrapper analog_model_event).

## Behaviour
- Bar vtable [4..7] -> macro_bar_down/move/up/takes. A horizontal drag of 70 px
  (|dy| < |dx|/2) opens (left) or closes (right) the macro strip. A tap with the
  strip closed is passed to whatever the firmware's hit test finds with the
  strip hidden (bar +30 set for the test). A tap in the macro strip arms or
  disarms that macro; PROJ + tap clears it.
- Strip open: macro_increment consumes every slot turn (returns delta 0) and
  moves macro i (0..127, 160000 raw units for the full range, remainder kept).
  Each target gets min + (max-min)*value/127, clamped to its range, posted as
  CF to the model, then 0813130C.
- Armed (strip closed): every model CF maps (node, key): value before the
  change = min (macro 0), latest value = max (macro 127). Range and name come
  from the last turned slot with that key. Up to 8 targets per macro; the first
  target's name becomes the macro name. A target whose max equals its min is
  removed when the macro is disarmed / the strip reopens.
- Targets are stored as paths (track index, child, grandchild; FE = project
  settings node) and resolved on every use, so they survive reload.
- Display: names on the name labels, values (or ARM) as value-text override;
  native labels are backed up and restored on close (re-backed-up if the page
  relabels a slot meanwhile). The header tick (device_header_prepare ->
  macro_periodic) repaints, looks for the visible strip after a page change
  (tree walk from the header root's top ancestor; unverified on hardware) and
  writes "MACRO n" into the transport readout (+196) while armed, unless motion
  shows REC/NO LANE there. mod_ui skips its encoder texts while the macro strip
  is open.
- Project file: one attribute `playground_macros_v1` (hex) on track 1's params
  (kick_ui_save/kick_ui_load). A project without it starts with no macros
  (detected when the project settings handle changes).

## Not done / unverified
- Hardware: touch coordinates, swipe direction and feel, whether the strip on
  every page is this class, the 160000 scale, save/reload.
- Macro editor (min/max per target, remove) from the Performance page: P28,
  modelled on the native Mod Matrix page. FX code has ~2.3 KB left below
  081D8000, so the editor needs a new code area.
- Performance page encoders are unchanged (BPM/Swing/...): owner to decide.
