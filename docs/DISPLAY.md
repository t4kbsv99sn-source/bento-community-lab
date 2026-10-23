# How the Bento display works (stock 1.6.1 UI core)

Established 23 October 2026 by disassembly of the maintainer's stock `bento1.bin`
(`14475e9d…bbb3`) and by running the firmware's own drawing code under Unicorn
(`research/display_emulator/`). Addresses are absolute flash addresses.

## Hardware path

- UI code is the Cortex-M4 image at `0x08100000` (reset `081003CC`). The M7 image
  at `0x08040000` does audio; the controller (`bento2.bin`) is not involved.
- One LTDC layer scans an **8-bit palette (L8) framebuffer** in SDRAM. Pixel values
  are palette indices (`F1` black, `F2` white, `F6` orange accent, …).
- The panel is **480 × 1280 portrait, mounted sideways**. The UI draws in
  1280 × 480 landscape coordinates. Surface descriptors (`08167A1E`) carry
  `{ptr, w=480, h=1280, type=5 (L8), rotation=4, bpp=1}`, and every primitive maps
  a UI rectangle to framebuffer `row = 1280 − x − w`, `col = 480 − y − h`.
  Upright glyphs then imply that native `y = 0` lies along the panel edge where the
  persistent header is drawn. (This is inferred from rendering. Check it against
  the device.)
- Fills: `08167EB4` → HAL DMA 2D register-to-memory (`08101640`). The L8 colour is
  replicated into 32-bit words; unaligned edges are written by the CPU. DMA 2D handle
  `30000E68`.
- Text: a mcufont-style renderer (`081244A4`, fonts table `300000CC` → flash fonts at
  `081A…`) draws into a 128-entry **text cache** of 64 × 426 L8 surfaces
  (`30035F44`, allocated at boot by `0817E3A4` from the bump heap `3000004C`/`30000048`).
  Cached labels are copied to the framebuffer with DMA 2D memory-to-memory.

## Widget tree

Common widget layout: `+0` vtable, `+4..+0x10` x, y, w, h, `+0x14` id,
`+0x18/+0x1C` child list, `+0x20/+0x24` siblings, `+0x30` **hidden**.
Vtable: `[0]` tick, `[1]` paint self, `[2]` paint children (`0816F9E8`, skips hidden
children), `[9]` set id, `[11]` set hidden (`08143ADA`: `strb r1,[r0,#0x30]`),
`[12]` event.

## Persistent header (the top action bar)

Root object `30034D48` (vtable `081B3680`), constructed once by `08180198`. It owns
12 buttons: six **normal** buttons at `+0x54C` and six **tab** buttons at `+0xA2C`,
each `0xD0` bytes. Fixed geometry: x = 163, 322, 481, 640, 799, 958; width 157,
y 6 (tabs y 8, height 39). Label text lives at button `+0x3C+0x31`.

The model holds the header *description*: a `0x1C4`-byte snapshot at `model+0x3A00`
(`model = 30024B00`). Six 48-byte action records at `+0x74`:

| Offset | Meaning |
|---|---|
| `+0x00` | label (≤ 31 chars) |
| `+0x20` | empty slot (1 = hide) |
| `+0x21` | active tab |
| `+0x22` | tab group: record goes to the tab button, otherwise the normal button |
| `+0x2C` | action id posted on release |

`+0x194` is the dropdown/popup id (`F9`/`FA`), `+0x196` bar:beat text,
`+0x1B2` tempo text, `+0x1C2` page key.

### Lifecycle

1. **Page change** `08141944(model, page)`: `0818012C` hides all 12 buttons and
   **arms the layout flag** `root+0x117C`; the page's template is copied from the
   flash table `08199008` (38 × `0x1C4`, keyed by `+0x1C2`) to `model+0x3A00`.
2. **Every UI tick** (`08180088`, also `0817FE70` on events, `0816E064`):
   `08134800` copies `model+0x3A00` and formats clock/tempo. `0817F8F8` compares
   it with the applied copy at `root+0x34`; any difference calls the apply step.
3. **Apply** `0817FAF8`: per slot, picks normal vs tab button, sets label and id
   **every time**, but sets visibility from `+0x20` **only while `root+0x117C` is
   armed**. It then posts event `0xCD` and clears the flag. Later applies change text
   only. A slot that was empty at the first apply stays hidden even if a label and
   id appear later.

### Real SEQ templates

| Page | Template | Slots 0–5 |
|---|---|---|
| `0x27` SEQ (drum and piano roll) | 36 | empty · **Step** (tab) · **Sequence** (tab) · empty · empty · **Undo** |
| `0x17` | 8 | empty · Event (tab) · Sequence (tab) · Automation (tab) · Clear · Undo |
| `0x1A` property editor | 20 | all empty |

Undo is always the last slot. Stock firmware has no handler for `0x1051` (Select)
or `0x1052` (Chord). Those IDs exist only in the EU9/CH1 view patches.

## Why EU8, EU9 and CH1 showed nothing on hardware

- **EU8** edited the popup menus `F9`/`FA`, not the persistent header.
- **EU9 Select**: `seq_toolbar` inserted Select only into a free slot *after* Undo
  and returned early when `undo >= 5`. On the real page `0x27` header Undo is slot 5,
  so Select was never inserted. Its tests passed because the fixture wrote a fake
  header with Undo in slot 0 and skipped the native snapshot copy.
- **CH1 Chord**: `chord_toolbar` only adds Chord once the piano-header hook has set
  `s->piano`. When that happens after the first header tick, the label and id reach
  the button but it stays hidden (lifecycle step 3). The emulator reproduces both
  orders: Chord appears only if the state is ready before the first tick.
- The tests applied headers to freshly constructed roots, where the layout flag is
  still armed, so they could not see the latch.

## CH2 fix

`eu4_work/integration/header_actions.c`:

- `header_action` puts custom actions in the **rightmost free normal slot**. On page
  `0x27` that is slot 4, directly left of Undo. On the empty editor page, Back and
  Insert take slots 5 and 4. An existing action only has its label updated
  (`Select` / `Select ON`).
- `header_sync` re-arms `root+0x117C` when any slot holding one of our actions
  (`1051/1052/1053`) differs in id, empty flag or tab flag from the applied header
  at `root+0x34`. The native apply then recomputes visibility exactly as it does on
  a page change. Native-only differences never re-arm it. The guard checks the root
  vtable first.

## Rendering locally

```
python research/display_emulator/render_headers.py --image /path/to/bento1.bin --out shots/
```

This renders the stock templates and, for CH-layout images, the drum and piano
headers with custom state arriving one tick late. Only DMA 2D is emulated; widgets,
fonts and text cache are native code. It is evidence for layout and visibility,
not a substitute for the device: palette colours, LTDC timing and touch are not
emulated.

## Piano grid (SEQ piano-roll layout), traced for CH6
- The grid is the widget at piano view `+38`, class vtable `081B2BCC`. vtable[0] is
  its tick, vtable[1] its paint. The paint also paints the note widgets.
- Columns: `+3C` visible count, `+4F8` first, `+564+4i` x of column i
  (i = 0..count), `+A20` ticks per column (1920 = 2 sixteenths by default).
- Rows: `+44` visible count, `+4F4` first, `+4FC+4k` y of row k (k = 0..count).
  With `+A10` set (one-shots), the row is `081751EC(pad)`: pads 0–7 → 8–15,
  8–15 → 0–7. Otherwise the row is the pitch.
- Notes: `+34` array of 0x48-byte widgets. Each has its rect at `+4`, hidden at
  `+30`, used at `+31`, state at `+32/+33` and colour at `+46`. A note is painted
  only on full repaints.
- Repaint requests: `+4F0` asks for a full repaint and `+4F1` for a partial one.
  The tick ORs them into the frame flags and clears them. A partial paint only
  moves the playhead: it erases the old column `+478` and draws the new one `+38`
  (`0817481A` sets `+38` and `+4F1`).
- Primitives: `08166EF6(rect, colour, surface)` fills, `08166E9E` outlines.
  Colours seen: `F1` background, `F2` notes and playhead, `F3` lines, `F6` bar
  lines.
- `research/display_emulator/render_lanes.py` renders the grid with CH6 lanes
  from the real paint code (fonts are stubbed).
