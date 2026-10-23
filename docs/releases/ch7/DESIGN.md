# CH7 design

Base: CH6 / 1.6H6 on `feature/ch4-live-layers`.

## Track types
The class registration (`0812EFxx`) gives these type ids (`08133F7C`):

| Id | Track type |
|---|---|
| 14 | Sample (one-shot) |
| 15 | Multisample |
| 16 | Slicer |
| 17 | Loop |
| 18 | Wavetable |
| 19 | Granular |
| 20 | Grain chop |
| 21 | Master |
| 22 | External |

The pitched set used by chord mode, melodic Euclid and native insert is now
{15, 18, 19, 22}. Before, it was {17, 18, 19, 22}: loop tracks were included by
mistake, and multisample was missing.

## Piano-roll lane geometry (owner video)
On the device, the one-shot piano roll folds rows to the pads in use:
- grid `+5276` turns folding on;
- the rows are listed at `+5278`, with the count at `+5478` and the scroll at
  `+547C`;
- `08175600` maps a row value to a visible index.

All lane rectangles now come from `0817566A(out, grid, tick, length, row)`. This
is the call the grid uses to place note widgets, so it handles zoom, scroll and
folding. A rect with height 3 or less is off screen and is skipped. A change in
scroll or zoom requests a full repaint.

## Chord selection
The grid selection API:

| Address | What it does |
|---|---|
| `08174BAC(grid, notify)` | Clear the selection |
| `08174C4E(grid, id, notify)` | Select a note by id: sets the widget `+32` and adds the id to the list at `+A54` (count `+1254`) |
| `08174D70(grid, i, &id)` | Read the i-th selected id |

With notify set, the grid posts `E6` to the view.

The chord's note ids (owned by insert or adopt) are selected quietly after every
chord-mode header rebuild, which follows each re-projection. In chord mode, an
`E6` from a touch reads the newest selected id. It then looks up that note's
start (`chord_native_find`) and adopts the chord whose hits include it.

## Rhythm
`hits(r, len)` gives the hit offsets and lengths for each rhythm. `expand()`
splits each chord into its hits, and those hits are inserted and checked
(maximum 16 chord entries). The clear before an insert still uses the full span.

`adopt()` recognises a rhythm when back-to-back groups with identical notes
match a pattern's hit starts and lengths (the most hits wins, at least two). It
owns the notes of every hit, so later edits rewrite all of them.
- Left moves to the first hit of the previous chord.
- Right skips to the first start at or after the chord's end.
- Entering chord mode lands on the first hit of the last chord.

## Recording vs Euclid
`live_record_check()` runs from `fx_dispatch`, which sees every message from the
audio core to the UI. It only scans when the project's next note id
(`project+68`) has changed, and keeps the last value in `EuControl.reserved[0]`.

The scan covers the current one-shot clip. A note on a generator pad counts as
foreign if any of these holds:
- the pad's pattern isn't stored as notes (no EU6 native bit);
- the tick isn't a whole step;
- the step is past the lane length;
- the step isn't a pattern hit.

Foreign pads have their enable bit cleared under the record seqlock, which is
the same effect as Shift+Left.

## Flash
The UI code bound is raised from `081CC000` to `081D0000`. Stock M4 MPU
region 1 makes `08100000..081FFFFF` executable, and the code stays in the
128 KB sector `081C0000` that it already used.
