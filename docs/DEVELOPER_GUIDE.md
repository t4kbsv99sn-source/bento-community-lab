# Poking around the code

Everything here patches one exact firmware: original Bento **1.6.1**. Most of the
original firmware stays as it is; a handful of its functions are redirected into
our added code, which reuses Bento's own screens, notes and playback wherever
possible.

## Where things live

| What | Where |
| --- | --- |
| Building a release and making the install ZIP | `tools/prepare_tester.py` (see [QUICKSTART](QUICKSTART.md)) |
| Building your own changes | `tools/build_ch1.py --stock … --out … --test` |
| Shortcuts, step locks, Euclidean sequencer, Select | `eu4_work/integration/` |
| Drum synths (Kick, Snare, Hi-hat) | `eu4_work/drums/` |
| Channel strip: EQ, compressor, soft clipper | `eu4_work/track_fx/` |
| Chord and progression editor | `chord_work/` |
| The base layer everything builds on | `k16_work/`, `k16_overlay/`, `tf2_work/` |
| Why each hook exists, per version | `docs/releases/<version>/DESIGN.md` |
| Everything we tried and what happened on the device | [STATUS.md](STATUS.md) |
| Ghidra scripts for exploring the firmware | `research/ghidra_scripts/` |

The folder names (`eu4_work` and so on) are just history; later versions kept
building on those folders.

## Open puzzles, if you're looking for one

- **The missing buttons.** The Chord button (CH1) and the Select toggle don't show
  up on the device, even though the software tests think they should.
- **CPU headroom.** How many drum synths and channel strips can run at once
  before audio suffers?
- **Saving and copying.** Euclidean settings don't fully follow clip copy/move
  or Undo yet.

## A few ground rules

- Never touch the bootloader. It's what lets anyone recover a bricked Bento.
- Don't commit firmware images (`.bin`) to the repo.
- Addresses only fit 1.6.1. A new official firmware means re-checking everything.
