# CH1 / 1.6H1 integration

Base: exact K16 reconstructed from original stock, then exact EU10 DSP and prior
controls. Portable C0 composition core and native insertion adapter are linked
into the existing UI cave at081C0800. End is checked against 081CC000. No new
fixed memory reservation, MPU/stack change or M7/DSP change. State and12KiB edit
scratch use the existing checked native SDRAM bump allocator.

Native piano header 081599BC captures the distinct pitched view, sequence 11CD00,
owner 11CD08 and length 11CD18. Native event 0815A598 intercepts only action 1052;
all ordinary events replay the exact original prologue. Persistent header 08134800
chains through EU9's existing trampoline. Six native 48-byte action slots are
preserved; Chord, or Back/Insert, use empty slots. A full header is left unchanged.

The editor reuses GenericProperties page 1A, existing encoder/touch widgets and
row selection. Keys 196/197/19A/19B/19D/19E/19F/1D1/1D2/1D3/128..12D are empty
in the actual complete native registry, inside its 3E60-byte allocation (499
entries). Every owner is preflighted before any descriptor write. A draft first
used 1F4..1F9, which were outside the native allocation; this was caught before
packaging and corrected. A canary/bounds test prevents recurrence.

C0 adapter validates model sequence, raw owner type 17/18/19/22, clip length,
capacity, IDs, heap and same-pitch half-open overlaps before one native Undo
snapshot. Native records remain 24 bytes: H2=0, H16=pitch, H18=velocity. No note
metadata fields are stolen. Native publication carries the new notes to the
engine queue; there is no new playback engine or audio-rate chord processing.

Edits that invalidate range/clip geometry restore both phrase and editor settings
atomically and display an error. Key/scale changes preserve explicit quality and
manual inversion. Preset changes intentionally replace draft structure. Native
notes persist, but the unsaved draft and chord-group metadata do not.

Native UI tests include actual persistent header construction/application/touch,
actual encoder bubbling, descriptor bounds/canary, native insertion, duplicate
refusal, progression quality, invalid edit rollback and stale contexts. Font,
model, navigation, Undo storage and engine queue services remain fixtures.
Physical startup/display/audio/SD/Undo are not certified by these tests.

First hardware milestone deliberately uses Insert -> Back -> Play. Pad audition,
clocked preview, chord blocks, Update and saved group membership remain required
for the full approved design. The standalone audition callbacks are source only;
CH1 does not connect them to native note-on/off routing.
