# Piano-roll chord entry — proposal, not implemented

Goal: insert an entire chord quickly using the pads, encoders and touchscreen, then edit/save it as ordinary Bento notes. This is an editing tool, not a new playback engine.

## Entry and flow

Add an on-screen Chord toggle in the piano roll for pitched tracks. Keep the existing SEQ double-tap and arrow gestures. Entering Chord mode changes the pad/encoder assignments only while the tool is open. Leaving without Insert discards the preview.

1. A pad chooses a root note using the existing keyboard/pad mapping and octave/scale view. Show the root and octave clearly, e.g. D3. Do not silently snap generated chord tones to the project scale: the chosen chord type determines its intervals. A later diatonic mode could choose chord qualities from the scale.
2. Choose chord type and voicing, inversion and register. Show every proposed note as a distinct outline in the actual piano roll, plus a readable chord label and note names.
3. Set Start and End. The plan assumes these are time positions in the sequence, not the highest/lowest pitches or a strum range. Touching the timeline chooses Start; dragging the right edge changes End. Encoders provide the same controls without precise touchscreen dragging.
4. Tap Insert. The whole chord becomes native notes in one atomic edit, with one Undo. Keep the tool open and move Start/End to the next location only when explicitly requested; do not silently advance or overwrite.

## Proposed encoder bank

| Encoder | Control |
|---|---|
| 1 | Chord type |
| 2 | Voicing |
| 3 | Inversion |
| 4 | Octave/register |
| 5 | Start position |
| 6 | End position |
| 7 | Velocity |
| 8 | Grid resolution |

The pads choose the root. The screen also offers root/octave selection, the same parameter choices, Insert and Cancel. A separate Preview control auditions the proposed chord on request; editing positions/voicings does not automatically play notes. This follows the earlier preference for explicit audition.

## Initial musical choices

Keep chord quality separate from voicing. Initial types: major, minor, diminished, augmented, sus2, sus4, major7, minor7, dominant7 and add9. Initial voicings: close, open and drop 2 where meaningful. Inversion cycles through the notes of the chosen chord. Root/register plus inversion should have predictable absolute pitch results rather than an automatic voicing search.

Example: D3 root, minor7, close, first inversion produces F3–A3–C4–D4. Start and End move/resize all four preview notes together.

Automatic voice leading, scale-derived harmony, strum, humanization, chord detection and live chord recording are later options, not requirements for version 1.

## Predictability and limits

- Insert adds notes; it never removes an existing different note. For the same pitch/time, preflight overlapping notes and clearly identify any conflict rather than silently replacing or duplicating an exact note.
- Refuse the entire insert if the native clip note capacity is exceeded. No partial chord.
- Reject out-of-range MIDI notes and an End at/before Start. Show the problem in the preview. Do not silently drop chord voices.
- Stay within the existing clip length in version 1. Do not resize a clip as a side effect.
- Existing notes are visible behind the preview. Cancel does not affect them.
- Native project save/load, copy/paste, velocity edits and Undo operate on the inserted notes. No new mandatory chord data format or playback dependency.
- The generated notes stay independent after insertion. Selecting them together can use the native multiple-note editing workflow; persistent named chord groups are not required.
- Chord-tool preferences may be session state initially; the music itself saves as ordinary native notes.

## Implementation path

First verify the pitched-track piano-roll note container, bulk-add, coordinate/time/pitch mapping, selection and Undo path. The Euclidean work already uses native bulk-note edits, but drum-note semantics cannot be assumed to be identical to pitched notes. Build the preview and bounded insertion separately, then attach the native controls and touchscreen handles. Test round trips, capacity failures, overlapping notes, clip boundaries, pitch limits and one-gesture Undo before a device build.
