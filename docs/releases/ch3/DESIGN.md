# CH3 integration — melodic Euclidean rows

Base: CH2 (fix/ch2-header-visibility). Branch feature/ch3-melodic-euclid.

## Maintainer feedback on CH2 and the page correction
Native SEQ handler `08142D58`: non-one-shot tracks always go to **page 17**
(piano roll, header template 8: empty · Event · Sequence · Automation · Clear ·
Undo); one-shots toggle between 27 (step grid) and 17 using property 188.
CH1 keyed Chord capture/toolbar/close to page 27, so Chord could never appear on
melodic tracks. CH3 uses page 17 for all piano-roll features. With only slot 0
free, the header carries **Euclid**; **Chord opens by SEQ double-tap** (index 11,
same 300/350 ms gate as the TRACKS double-tap) when the page is 17 and the
captured pitched context is valid. A single SEQ press on page 17 is a native
no-op for pitched tracks; one-shot double-taps leave page 17 on the first press
and stay native. Select ON / Euclid ON set record +21; native apply maps it to
the button's selected state (+AC, filled) only while layout is armed, so
header_sync compares +21 too.

## Data
- `EuRecord.reserved[0]` bit 0 marks a pitched-track record; `reserved[1..4]` hold
  one pitch byte per row. Drum records keep these zero (test asserts it).
- `EuPad.velocity` bits 24..29 hold the row gate in quarter steps (0 = one step);
  `eu_pad_valid` accepts them. Older firmware rejects such pads (by design).
- `EuRuntime` gains one M7-owned cache line (melodic flag + 16 pitches); the bank
  allocation grows by 512 bytes to 44576 (native bump heap, preflighted).
- XML adds `bento_eu2_RR_PP_4` (pitch) and `_5` (gate) for melodic records; save/
  load accept owner types 17/18/19/22 as well as one-shot 14.
- `Euclid.preview` carries `EU_MEL|gate<<8|pitch` for melodic edits; the struct
  size is unchanged because `Ui` fills its reservation exactly.

## M4 / UI (melodic_eu.c)
- Notes are matched by pitch (H+16, H+2=0) instead of pad (H+2); new notes get
  pitch, `gate*240` ticks length and native IDs through the same EU6 bulk APIs.
  `eu_repitch` and `eu_gate_notes` edit existing row notes in one undo gesture.
- Header action `1054` ("Euclid"/"Euclid ON", lit when on) takes the free slot 0
  on the page-17 header via header_actions.
- After the native piano header `081599BC`, the eight piano bindings (keys
  view+11BCC0, values +11BCD0, handles +11BCA0) are replaced by Row 190, Note 18D,
  Length 191, Hits 192, Rotate 193, Gate 18F, Vel Mode 194, Vel Depth 195. Keys
  18D/18F are empty in the constructed native registry and have no native
  immediate uses. Descriptors 190..195 are registered with the drum title pointers
  so the drum and piano registrations accept each other; visible titles are
  overridden per slot. Turning Euclid off rebuilds the native header unchanged.
- One 12 KiB edit scratch is shared with drum Euclid (single-threaded UI).

## M7 / audio (live_audio.cpp)
- Melodic rows match native notes by pitch; hits go through the native note-on
  `0805F8E0(seq, pitch, vel, frame, 0, router)` and are registered in the native
  active-note table (count seq+238; entry i at seq+i*16: +38 active, +3A pad,
  +3C note, i64 +40 end). The stock renderer loop at `08060494` sends the
  note-off (`0805FE00`) when the end passes. A held pitch is released first, as
  native retrigger does. End = now + period*length/960.
- `live_skip(seq, pad, pitch)` suppresses native notes of enabled melodic rows by
  pitch; the patch passes the event pitch from the native stack copy (+0x38).

## Tests
`eu4_work/integration/test_melodic.py` (real note containers, IDs, bulk edits,
M7 renderer and emitter) and `chord_work/test_piano_eu.py` (actual piano view
constructor, header builder and event entry). The native release loop itself is
not executed by the fixture; its entry layout is verified by disassembly.
