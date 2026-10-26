# P6 design notes (fixes to P5)

1. Reset on PROJ+PLAY: perf_get looked up the current track (08133CFC) for
   every key; 08133CFC reads project property 131 through the hooked getter
   08133614 -> fx_get -> perf_get -> 08133CFC ... until the stack overflowed.
   perf_get now answers key 0 (empty slots) and returns at once for keys that
   are not its own. Regression: test_perf RealPage builds the real native
   GenericProperties page (08145B7C/08145EFC) with the real 08133CFC entry and
   our hook chain; it raises on 1.6P5 and passes on 1.6P6.
   Rule for all getter hooks: never call 08133CFC / 08133614 before the key is
   known to be ours.
2. Analog waveforms: the Wavetable builder (0815F6DA) hides class 081B3A98
   (+2E90/+31F0, the Granular panes) and shows class 081B3A18 (+3550/+36C8,
   label child +104). Hooks moved to 081B3A18 [0] tick 081822A4 and [1] paint
   08182314. The tick sets pane +32 when a redraw is due (the native tick turns
   it into a partial repaint) instead of forcing it every frame.
   render_analog.py now sets pane visibility like the builder and paints
   through the widget tree.
3. Drum Synth entry: drum_menu_tick (from fx_dispatch, every UI message) keeps
   code 1056 in every menu that offers Load WAV and has fewer than nine
   entries while the current track is one-shot, and removes it otherwise. The
   action is taken from the model event entry and from the pad page view
   handler (0814888C via vtable slot 0819DC50, drum_view_event), once per press
   (300 ms guard, 24043D78).
