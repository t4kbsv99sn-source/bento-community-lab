# CH6 design: chord pad audition and piano-roll Euclid lanes

Base: CH5 / 1.6H5 (branch feature/ch4-live-layers). The bootloader and controller
are unchanged.

## Chord pad audition
**How a pad becomes a note (traced).** The audio core scans the pads (`0808D3xx`)
and posts record `AC` (press) or `AD` (release) to router handle -2: `+0C` is the
pad and `+10` is the pressure. The pad module (`08085540`, case `AC` →
`08084760`, case `AD` → `08083FE0`) switches on pad mode `+490`:
- **Mode 3 (keyboard)** maps the pad. Pads 0–7 and 8–15 are swapped. The mapping
  is `0809DB40` (chromatic: `root-3 + idx + octave*12`) or `080A1E40` (scale).
- It then posts one note record through `0809ECA0`:
  - type 2 for on, type 3 for off;
  - `+08` is the selected track handle `+2CC[sel]`;
  - `+0C` is the pitch and `+10` the velocity.
- A second copy goes to `+2EC[sel]` when that handle differs (a layer).

The record is then forwarded, and the UI gets `AC`/`AD` back through its ring as
event `B0`/`B1` with the pad at `+08` (`081335CC`). The piano view ignores those
events natively.

**Patch.** The four `bl 0809ECA0` sites go through `chord_press` and
`chord_release` (M7):
- `08084918` (track) and `0808494E` (layer) on press;
- `0808414A` and `08084180` on release.

While the UI's ChordMail is active, a press sends every chord tone (pitch +
offset[pc]) and records ownership. Notes are reference-counted per handle slot,
and a release sends offs only for the notes that press started. When the mail is
missing, torn or inactive, the original single post runs. A release whose press
was not taken over also stays native.

**Shared memory** (appended to EuBank, so the bank is 45920 bytes):

| Block | Size | Written by | Contents |
|---|---|---|---|
| ChordMail | 128 B | UI | Odd/even serial, active flag, `count[12]`, `off[12][6]` |
| ChordPub | 32 B | Audio | `pitch[16]` of the last press (bit 7 = valid); cache line cleaned |
| ChordOwn | 1184 B | Audio only | refs[2][128], held bits, notes per root |

**UI side.** In live mode, `chord_live_header` publishes the shape for all 12
pitch classes from the selected chord. Diatonic types are recomputed per pitch
class from the project key and scale. Leaving live mode withdraws it.
`chord_live_hw` takes `B0`: it reads the published pitch for that pad and
applies it as Root (key 128), then drafts the chord.

**Audio code location.** The audio code now starts at `080DC400`. The adapters
use under 0x200 bytes of the old 0x800 adapter block, and the cave is still
bounded below `080E0000`.

## Piano-roll lanes (option B)
**The grid.** The piano grid is the widget at view+38, class vtable `081B2BCC`.
Its fields:

| Offset | Meaning |
|---|---|
| +3C | Visible columns |
| +4F8 | First column |
| +564+4i | Column x |
| +A20 | Ticks per column |
| +44 | Visible rows |
| +4F4 | First row |
| +4FC+4k | Row y |
| +A10 | Pad rows; the row is `081751EC(pad)` |
| +34 | Note widgets, 0x48 bytes each |
| +4F0 | Full-repaint request, read by its tick |
| +4F1 | Partial-repaint request, read by its tick |

**Paint.** Paint ctx = `{full, partial, surface}`. The grid's paint also paints
its notes, and in partial mode it redraws only the playhead.

**Patch.** vtable[0] (tick) → `lane_tick`, vtable[1] (paint) → `lane_paint`.
Both call the originals.
- `lane_tick` compares the wanted lanes with what was drawn. A changed set or
  length requests a full repaint; moved boxes request a partial one.
- `lane_paint`:
  - in partial mode, it first restores each moved box's old cell (background,
    then the parts of notes inside);
  - it then runs the native paint;
  - on a full repaint, it greys the cells from the lane's length to the right
    edge;
  - it then draws a box (white outline, black inner ring) at each lane's step.

**Data.** `live_lanes` reads the committed EuRecord for (owner, clip row) and
the published EuRuntime phase. The step is `step % length`, the same as on the
audio core. There is no box while the generator isn't playing.

**State.** 64 bytes, from the native bump heap, with its slot in the lock UI
struct (`lane_state`).

Colours: `F1` background, `F2` box, `F3` grey (the grid-line colour).

## Evidence
- `eu4_work/integration/test_chord_audition.py` runs the real pad-module press
  and release on the CH6 image.
- `chord_work/test_device.py` covers pad root, publish and withdraw, and the
  diatonic shapes.
- `chord_work/test_lanes.py` checks pixels from the real grid paint and tick,
  including partial-repaint restore.
- Screenshot: `research/display_emulator/render_lanes.py`.
