# Known issues — P27 stopping point

## Hardware evidence

- **Startup/project load:** reported working on P27.
- **Macro strip:** left/right swipe opens/closes it, confirmed. Tapping shows ARM, but parameter movement does not map. The sample instrument page does not respond to the swipe. A freeze was reported; its scope was not established.
- **Motion recording:** source is included, but working end-to-end capture/playback/save/reload has not been established. Earlier hardware feedback found no recorded movement and interference with normal recording. Later gate, encoder and indicator fixes need device verification.
- **P21** was the recovery reference in the P27 development notes, not a certified stable release. Keep a known working image for your own device.

## Boundaries

- The snapshot deliberately stops at P27. It contains no P28/P29 arpeggiator implementation or macro rework.
- Melodic Euclidean playback uses the native sequencer with cycles tiled across the clip. Independent loop-spanning melodic cycles and velocity modes were paused; drum/melodic parity is not claimed.
- Generic synth per-note send locks tap before shared Track FX while active. Inherited sampler/multisample sends retain their existing behaviour.
- Software checks do not establish hardware CPU headroom, audio timing, display correctness or persistence for every feature.
- The separate browser design kit is a proposal, with a P27 label audit and explicit native-label gaps. It does not replace firmware screens. Its Euclidean generator and Step editor remain separate visual simulations.

Treat historical version DESIGN.md files as engineering notes, not guarantees.
