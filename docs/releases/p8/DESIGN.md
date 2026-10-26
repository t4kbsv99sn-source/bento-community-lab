# P8 design: mod mode (and the P7 fixes it ships with)

P7's fixes are described in perf_ui.c, kick_ui.c and build_fx.py comments
(PLAY scan at 0808D34E, settings node 08133E54, Smooth voicing, played chord
name, versioned shared chord, Drum Synths folder, pane colours).

## Synth page (view class 0819E894)
One view serves Wavetable (track type 18, also Analog) and Granular (19).
Constructor 0815E228, vtable [0] tick 0815D7D0 and [12] event 0815F148. P8
replaces both vtable entries with mod_view_tick / mod_view_event, and each
calls the native function.

| Offset | Meaning |
|---|---|
| +2430 | track handle |
| +2434 | track index; view+[+2434]+10238 = selected tile |
| +246C+3C·i | tile panels, widget id = tile index i |
| +2700+40·i | tile frames; 0815F0B6 writes +34 colour (F2 selected / F3), +38 width (2/1), then +3E or +3D dirty |
| +29C0+70·i | tile titles |
| +38 | encoder bar; slots +70+468·i (+9C key, +9E type, +450/+454 range, +2C8 override text) |

Tiles: 0/1 WT1/WT2 (or GR1/GR2), 2 Osc, 3 Envelope 1, 4 Envelope 2,
5 Filter 1, 6 Filter 2, 7 Mod Seq, 8 LFO 1, 9 LFO 2.

Events: a widget touch posts {79, 0, id} upward (0817C5EC/0816A2F4 via
0816FC34, parent at +2C, a nonzero return keeps bubbling). The view handles
79 by selecting the tile (0815F0B6), 7B {+8 0/1/7} opens pages, and CF
{CF, node, key, value} from an encoder becomes D0 for the model. Codes ≤ 0A
bubble on; the burger menu's "Modulation" entry is action 0A (menu cells
081983D8/08198568).

## Routes
The model event D1 {D1, node, key|1<<16, source|slot<<16, amount} goes to
08133388 (via 08140924, where CH11's mod_edit also hooks in). It finds the
node by handle and then the route child with type 1, +14 slot and +12 key:
- if one exists, it is updated (+0C amount, +10 source);
- if not, one is created (0812E7DC);
- source 0 removes it (0812E518).
The native matrix uses three slots per destination (columns 0x171..0x176:
Source/Amount pairs). Amounts run from −1000 to 1000 (the matrix rejects
|amount| > 1000).

Lookup: 08131244(MODEL, &node, key, slot, out) returns a nonzero value and
fills out = {amount, source | key<<16, slot}.

Destinations (Mod Matrix rows): table 0819DE54, 60 entries of 24 bytes
{node type, instance, key, label, …}, Wavetable rows 0–22 and Granular rows
23–59. The nodes are the track's children (0813391A walk; type 08133F7C):
6 WT, 7 GR, 8 Osc, 9 Env, 10 Filter, 11 LFO; instance = order among
same-type children.

Source ids (table 08166AB0 → 300312EC): 1 Env 1, 2 Env 2, 4 LFO 1, 5 LFO 2,
8 Mod Seq.

## Mod mode
- The header (seq_toolbar → mod_toolbar) acts only on the synth page's own
  template, recognised by the tab ids EE/EF in slots 3/4, and only while the
  synth view ticked in the last 300 ms on a type 18/19 track. Tabs move from
  slots 2–4 to 1–3. Slot 4 is MOD (1057, lit when on), slot 5 is MATRIX
  (1058). header_sync treats 1051–1058 as custom, so a late change re-arms
  visibility.
- MATRIX: the event code is rewritten to 0A and passed to the native
  handler, which bubbles it like the menu entry.
- Tile taps 79/7A/7B on tiles 3, 4, 7, 8, 9 are consumed in mod mode; 79
  toggles the source. Each tick enforces the frames: orange F6/width 3 for
  selected sources, the native look when they are deselected or mode is off.
- Encoders: for each slot whose key is a destination of the selected tile's
  node, the slot shows the first selected source's amount as text, and its
  value is set to lo + (amount+1000)·(hi−lo)/2000 (centre = 0%).
- An encoder CF with that key: delta = value − shown, and
  step = delta·2000/(hi−lo) (at least ±10). Every selected source gets
  amount + step (clamped), creating a route in the first free slot or
  removing it at 0. The CF is consumed, so the parameter doesn't change.
  The CF's own node handle decides, and nodes that aren't destinations go
  native.
- Track change (view +2430) or a non-synth track turns mod mode off. Off
  restores the slot text and values (model getter) and the frames.

State: one Mod block from the native bump heap, with a pointer in the UI
struct (mod_state).

Tests: test_mod.py (18) runs the native constructor, event handler, encoder
slot functions and registry. The model tree, the lookup and the route store
are fixtures that follow 08133388.

## Not verified
Hardware: everything. In particular, these are inferred from code and not
seen:
- the event's node handle on the device;
- that the 0A action from the synth view opens the matrix;
- the orange (palette F6) outline.
