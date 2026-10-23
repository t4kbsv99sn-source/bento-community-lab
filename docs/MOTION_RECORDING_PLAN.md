# Motion recording — plan (not implemented)

Maintainer request, 23 October 2026: record knob movements live (e.g. Hi-Hat Decay)
on loops whose length is independent of the clip length and of any Euclidean
row length. Native 1010 automation is too slow to use on the fly. This document
is a design; no firmware is built from it yet.

## What is wrong with native automation for this
- Lanes are tied to the sequence's step grid and clip length (the "Automation"
  tab on the page-17 header; A–D contributions in each parameter's native data).
- Writing is per step through menus, not a performance gesture.
- A lane cannot run at, say, 5 steps against a 16-step clip and a 7-step
  Euclid row.

## Goal
**Hold a performance gesture, turn a knob, and the movement loops.** Each recorded
lane loops at its own length, in sync with the native clock, and can be cleared
or re-recorded without opening any menu.

## Design

### 1. Lanes
A *motion lane* is `{target, length, mode, events[]}`.
- **target**: track owner + pad (one-shots) + parameter key. First release covers
  the drum-synth controls (Kick 8, Snare 5, Hi-Hat 5 incl. Decay), because their
  values are already M7-owned and re-applied every audio block (`kick_render` ->
  `parameters()`/`apply()`), so a lane can change a ringing hat's decay mid-note.
  Native parameters (Level, Filter, Pitch…) come later through the mod-matrix
  binding (see DRUM_MOD_MATRIX_PLAN.md); that path is not traced yet.
- **length**, independent of clip and Euclid length:
  - *Fixed*: 1–256 steps, chosen with an encoder (odd values such as 3/5/7/13
    are allowed);
  - *Free*: length = the time from the first touch to the moment you press the
    gesture again (rounded to 1/16 step, clamped to 256 steps). This is the
    fast performance option.
  - Phase follows the native clock from the lane's own origin (the transport
    position at first record). Restart on clip launch, like Euclid's
    `live_restart`.
- **mode**:
  - *Absolute*: the lane replaces the knob's base value.
  - *Offset*: the lane adds to the base, so turning the knob afterwards still
    shifts the whole movement.
  - Default to Offset for Decay-type controls.
- **events**: `(time in 1/96 step, value 0..1000)` pairs, sorted, at most 256
  per lane. Stored only on change: an encoder tick produces one event, so a
  sweep is a few dozen pairs, not a full sample stream. Playback interpolates
  linearly between events (with a "step" option for switched controls).

### 2. Recording gesture (to be confirmed on hardware)
Use a button you're not already using in SEQ/instrument views.
- Proposal: **hold REC + turn a synth encoder** → arms and records that
  control's lane while the transport runs.
  - *Touch* behaviour: while the encoder is being turned (and for ~300 ms
    after), the lane is overwritten at the playhead. Release and it plays back.
  - Each pass overwrites only where you moved: overdub without erasing the rest.
- **REC + press the encoder** (or Shift+Clear) clears that lane.
- Header feedback through the now-working custom header path (DISPLAY.md): a
  lit **Motion ON** action on the instrument page, and a small dot on encoders
  whose lane is active.
- Optional encoder-row "Motion" bank, like the Euclid bank: Lane select, Length,
  Mode, Clear.

### 3. Runtime split (follows the Euclid/EuBank pattern)
- **M4 (UI)**
  - Capture in `kick_ui_increment` (all synth encoder turns already pass through
    it) and stamp each event with the transport position read from M7's
    published phase, the same idea as `EuRuntime.reserved[1]` for Euclid.
  - Write events into an M4-owned lane store from the checked native bump heap
    (~1 KiB per lane, 32 lanes ≈ 32 KiB).
  - Publish to M7 with a seqlock serial per lane, never sharing a cache line
    (as EuRecord does).
- **M7 (audio)**
  - Once per audio block, per active lane:
    `phase = (clock - origin) mod length`, then binary-search the events and
    interpolate. That's about 32 lanes × O(log 256), negligible next to the
    synth DSP.
  - Feed the result into `kick_render` before `apply()`, as base override or
    offset.
  - Never allocate; the M7 side reads only.
- **Precedence at a hit**: per-step p-lock (existing lock codec) > motion lane >
  knob base. A locked hit keeps its locked value for its own voice; the lane
  continues for unlocked hits. (Alternative to decide: lane offsets apply on top
  of locks.)

### 4. Persistence
Per instrument XML, versioned like `bento_eu2_*`:
`bento_motion_v1_<pad>_<key>` = length|mode|count, plus packed event words
(time<<16 | value) in numbered attributes. Older firmware ignores them. Lanes
for a pad whose engine changes (Kick → sample) stay saved but inactive, as the
modulation plan requires for synth routes.

## Open questions for the owner
1. Gesture: is REC+encoder free and comfortable on Bento, or prefer Shift+encoder?
2. Default length for *Fixed*: clip length, 1 bar, or the length of the pad's
   Euclid row?
3. Absolute vs Offset default per control?
4. Should a lane follow clip changes (per clip) or belong to the pad/track
   (per pattern-independent instrument)? Proposal: per pad, independent of
   clips, since the point is to be unlinked.
5. Quantise recording to 1/96 step or keep the raw tick? (1/96 step at 120 BPM
   is about 1.3 ms, finer than encoder resolution.)

## Prerequisites and risks
- Needs the M7-published transport phase. Euclid already publishes per-sequence
  phase; a sample-accurate song-position word is still to be added.
- Encoder event rate and the native 2–3 ms UI tick bound capture timing; fine
  for decay sweeps, not for audio-rate wiggles.
- CPU and RAM headroom must be measured on hardware (emulator counts ≠ device CPU).
- Native parameters (non-synth) depend on finishing the mod-matrix trace.
