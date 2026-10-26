# Motion recording — first implementation (portable core, not yet installed)

Source: owner-supplied P19 source snapshot (25 Oct 2026); base stock 1.6.1.

This directory contains **working tested C code** for the independent A–D
motion timeline. This is **not a flashable P20/P21 image**, and it is not wired
to stock Bento's automation view, UI events, clock or project save/reload.
There is no bootloader/controller patch here.

## Decisions already coded

- One motion timeline for each of eight tracks × lanes A–D. Reuse the *native*
  lane target routing in the future adapter, do **not** introduce a second UI.
- PROJ + RECORD key-down arms capture; RECORD key-up ends it, even if PROJ was
  released first. A capture occurs when its *selected parameter* moves, not on
  every tick. Internal phase is anchored on the first take and independent of
  musical clip length and Euclidean row length.
- User selects Auto / 4 / 8 / 16 / 32 / 64 bars in a pre-recording menu.
  Fixed means **no auto-shortening on release**. Auto rounds up on release.
- Empty remainder of a selected loop **holds the last recorded value** and
  restarts at the loop boundary; it never repeats a three-bar recording inside
  a sixteen-bar loop.
- Automation pane length encoder moves among 4/8/16/32/64. Shrinking changes
  the period, never time-stretches notes or destroys hidden out-of-range events.
  An Undo adapter can snapshot the lane before a change.
- Subsequent recording supports Overdub (same-timestamp events update) and
  Replace (clear previous events on first parameter movement); capture is
  event-driven. Linear or stepped interpolation is available.
- Source is portable C with no allocation or firmware hardcoded addresses.
  Caller supplies storage and native song position in a 960-tick-per-16th
  domain. Other meters can supply their actual ticks-per-bar.
- v1 versioned serializer (little-endian) with strict bounds and ordering guards.

## Important unimplemented steps — DO NOT FLASH as a motion build

1. **Trace native A–D storage, routing and automation editor** on P19 and inspect
   clock / transport tick semantics. A–D currently belong to native clip state;
   intercept only on a recognized firmware image and preserve stock editing.
2. Route PROJ+RECORD through real button-down/up events, without starting native
   audio/pad recording. Map the selected A–D lane (and controlled parameter)
   to knob changes, without leaking other encoder movements.
3. Publish M4-owned snapshots to M7 through a verified, cache-safe ownership
   scheme. Playback must update A–D contribution on the audio path without
   writing native base values or changing per-step lock precedence.
4. Add independent Length encoder and expanded timeline navigation to the
   **existing** automation editor. Verify full repaint and scrollbar behavior.
5. Store motion v1 in versioned native project params, survive save/reload and
   clip changes, and integrate native Undo/Copy/Delete consistently.
6. Prove M4/M7 RAM/flash allocations, real-time timing and proper recovery;
   rebuild image from exact stock; exact reversal; run regression tests and
   **test on actual hardware** before any full firmware package.

Also includes `motion_controls.c`: native adapter interface for UI key-up,
pre-record menu, tapped A–D parameter changes, editor Length encoder and
a live bar/cycle counter. It does **not** create native buttons or intercept
firmware by itself.

Tests: `cc -std=c11 -O2 -Wall -Wextra -Werror motion_work/motion_core.c motion_work/test_motion.c -o /tmp/motion_test && /tmp/motion_test`

## Memory footprint

At the default 256 events per lane: 2,096 bytes per lane, 67,088 bytes
for the complete 8-track × 4-lane bank on the host ABI. This is **not** an
authorized M4 RAM allocation: before wiring into firmware, measure the real
allocator and establish core/cache ownership. An installation build must refuse
unverified address ranges.
