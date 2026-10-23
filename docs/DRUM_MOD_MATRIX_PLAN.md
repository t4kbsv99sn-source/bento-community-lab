# Drum synth modulation matrix — integration plan and evidence

Status: NOT implemented in EU10. The EU10 image changes the p-lock target list only. Do not claim that selecting synth controls in the instrument editor or p-lock picker makes them native modulation destinations. No nonfunctional modulation rows have been added.

## Desired behavior

A sampled one-shot keeps its original modulation rows and sources. A synthesized one-shot exposes only its own engine's controls (kick 8, snare 5, hi-hat5), alongside meaningful existing mixing/filter/LFO controls; sample ADSR rows are hidden for synths. Switching pads or loading a sample refreshes the list immediately. Other engines' controls must never leak between rows or pads.

Retain the native matrix interaction: target row in the first column, three source/amount pairs, existing amount/source gestures, scroll and project save/load. A synth route must affect the corresponding audio parameter. Native automation A–D and p-lock data remain separate. Apply modulation as an additive contribution to the current base or per-hit locked value, bounded to that parameter's actual range; do not record the computed result as a base edit.

Use stable engine-specific target identities so a Snare Snappy route never becomes Kick Sweep after a sound replacement. Compatible routes remain, incompatible synth routes remain saved but inactive for other engines. Decide how to migrate old sample ADSR routes before changing their audio behavior; EU10 does not delete or disable any old route or lock.

## Proven current architecture

- Current synth parameters are custom M4-owned values in KickKnobs (24043500), plus Click bytes 24043D80. M7 reads these and accepted voice locks in eu4_work/drums/kick.cpp parameters/apply. The native matrix does not feed those custom values.
- Native sampler root 080AC66C, native modulation parameters copied by08092F20 into the voice (e.g. Level+180, Pitch+300). Native per-parameter data is64bytes, with base, up to three user sources and A–D contribution. Existing p-lock code preserves other native modulation when replacing a base contribution.
- Within 08092F20: voice-specific route records are read from root+590, count at+5FC, stride 12; record float amount+0, targetH+4, sourceH+6, slotB+8. This is ONE stage, not a full map of all native sources.
- Its source dispatch 4..33 explicitly binds4→voice+610 (LFO 1),13→voice+B4 (velocity),14→voice+BC (key),32/33→voice+C4 (pressure). Other/global sources can be bound at different stages; do not restrict the user-visible list to these four based on this one routine.
- Native 0809FD00 attaches a source pointer/amount into one parameter's user slot and rebuilds its active-source list. Native 0809FD80 evaluates the parameter through the current lock adapter.
- Generic M4 descriptors at30031484 are not the audio parameter objects. Merely registering a custom key/name cannot make it an audible matrix destination.
- Native shared target table 0819E428 has keys 2,3,4,1E,1F,21,4C,4B,32,33. This is referenced by native propagation 081332A4, metadata builders around 0814C1E6/0814CD60, and the separate automation target mapper 081576B8. These uses must not be conflated.
- Native 0813325C emits parameter modulation commands; it packages the target key and source/slot fields. The current destination-specific binding/serialization path for adding arbitrary new synth keys has not yet been fully traced.
- Native registry has spare IDs, but current overlay ownership must be checked too (EU, FX, kick and lock IDs). Original registry emptiness alone is insufficient. No new IDs are allocated by EU10.

## Work needed before a modulation firmware

1. Trace the actual one-shot matrix row construction/selection/scrolling and destination setter, with the selected one-shot handle carried through. Verify capacities and native callback routing. Several nearby target tables also serve automation; changing a shared constant globally would leak synth controls to samples and other views.
2. Allocate distinct, versioned synth destination IDs with descriptors/token names available before project loading. Keep the instrument's existing reused knob IDs separate from stable saved modulation identities.
3. Bridge native source evaluation to synth parameters per voice/block, including both global and voice-specific sources. Prefer native source values and amounts over implementing another LFO/MIDI subsystem. Prove zero routing is sample-identical and p-lock+modulation interaction follows the agreed rule.
4. Implement save/load and compatible/incompatible engine switching. Corrupt/unsupported destinations must be ignored safely, not redirected to an unrelated control.
5. Test actual native UI routing, LFO/velocity and a global MIDI source, live edits, per-pad isolation, save/load, engine replacement, per-voice lock interaction, bounds and CPU headroom. Then deliver an installable matrix build.

No bootloader, controller, startup/MPU/stack/heap-layout changes are authorized by this plan. Do not reuse sample ADSR as hidden carrier controls: their existing audio paths could alter the amplitude envelope as well as the synth parameter.

## Primary reference

1010music bento v1.3.17b manual, printed pages 255–256, documents the existing target-row/three-source layout:
https://1010music.com/wp-content/uploads/2026/01/bento_v1.3.17b_user_manual.pdf
The 1.6.1 binary remains authoritative for offsets and implementation. Manual descriptions do not prove current native capacities.

## Findings 23 October 2026 (CH3 session, stock 1.6.1)

- **Route model is a list, keyed by registry key.** XML `<modsource dest src slot
  amount [mchan ccnum]>` is written by `0812F68E..`: route record `+0x0C` amount
  (u32), `+0x10` source (s16; negative = MIDI CC with channel bits 7..10, CC bits
  0..6), `+0x12` destination key (u16), `+0x14` slot (s16).
- **Destination token = registry descriptor `+0x18`** (`081666F8`, keys <= 1F2).
  Custom descriptors currently leave `+0x18` zero, so a synth destination needs a
  stable token string (e.g. `bento_kick_sweep`) to save/load. Token -> key lookup
  on load is `08166720` (searches the registry, including the lazy area +3E40).
- **Sources** come from a 34-entry table (12-byte records, id at +0, name at +4;
  `08166A18` id -> token): lfo 1..4, modseq, velocity, key, pressure, mod 1..10,
  modwheel, … M7 holds a parallel name table at `080A94xx`.
- **Registry descriptors have no "modulatable" flag.** Destination availability is
  decided by UI/target lists, not by the descriptor.
- `0819E428` (10 keys: Level, Pitch, Pan, Attack, Decay, Release, LFO Depth, LFO
  Rate, Filter, Resonance) is iterated by propagation `081332A4`, which sends
  `0813325C(model, track, key, 3, 0, 0, …)` for sampler track types 1/3/4.
- `0814C196` expands a const table at `081916A8` (128 × 12 bytes: key, type byte)
  into per-type lists at model+8B1C4 (0x18-byte entries). Types 0..15 there carry
  Level/Filter/Pitch/Resonance/sends (and Mute/Solo/mixer for 0): these look like
  track/mixer-level targets, not per-instrument synth targets. Not yet confirmed.
- Mod matrix pages are header templates 12/13 (keys 0E/0F, "Mod Matrix"). The
  list widget formats rows at `0817A82C` (row kinds 1..3; kind 3 prints
  "[No open mod slots]").

### Still to trace before implementing
1. The Mod Matrix page view class (page 0E/0F constructor) and how it builds its
   destination choices for the selected one-shot pad; where to append synth keys
   only when the selected pad is a synth carrier.
2. `0813325C` command format and the M7 receiver that binds a route to the voice
   parameter (`0809FD00` attach). Unknown keys must be intercepted there and stored
   in an M7-owned synth route table instead of reaching native parameter objects.
3. Evaluate sources per voice/block in `kick_render` (LFO 1 voice+610, velocity
   +B4, key +BC, pressure +C4; global sources TBD) and add to synth parameters
   within range. Zero routes must stay sample-identical.
