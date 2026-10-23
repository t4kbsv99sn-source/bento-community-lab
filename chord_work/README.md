## CH1 firmware integration

`device.c` now connects this core to a native editor and Insert action. See [integration](../docs/releases/ch1/DESIGN.md). The following C0 notes describe the earlier standalone checkpoint; its remaining-work list is historical. CH1 is insertion-first; audition and group persistence remain unfinished.

# Chord composer — implementation checkpoint C0

This directory is development source, NOT installable firmware. EU10 remains unchanged. No new hooks, UI, fixed SRAM, original bootloader, controller or DSP changes are installed by these scripts.

## Implemented

- Portable integer-only C chord generator: 15 chord qualities, Close/Open/Drop2 where valid, explicit inversions and signed strum timing.
- Twelve original degree-based progression presets; five scales (major, natural minor, Dorian, Mixolydian, harmonic minor), transposition and absolute register.
- Automatic voicing search, deterministic results, explicit inversion overrides, and reharmonization preserving explicit quality overrides. Repeated edits do not drift register.
- Rendering into bounded note previews, keeping a shared endpoint for strummed voices. Invalid time/pitch/capacity is rejected without partial output.
- Versioned 440-byte pointer-free progression-settings codec with corruption detection. This is NOT yet wired to Bento XML and does NOT store inserted native-note membership.
- Pad audition ownership: full chord note-on/off callbacks; releases use the actually played notes, not later encoder settings; overlapping pads share pitch ownership; stop clears owned notes. Strummed live audition scheduling is NOT implemented.
- Standalone native ARM insertion proof: revalidates selected sequence/owner/length, checks capacity and same-pitch overlaps, obtains native IDs and publishes native records after one Undo snapshot. Native scratch is allocated once with bounds checks. Notes use H+16 for pitch, H+2=0 for the single pitched instrument. Adapter is restricted to raw track types 17/18/19/22 and is not hooked into any screen.

## Reproduce

Use the pinned root requirements and stock/EU10 fixtures outside Git:

```
python chord_work/build.py --out /absolute/path/chord-core
BENTO_CHORD_BUILD=/absolute/path/chord-core python chord_work/test_chords.py
BENTO_CHORD_BUILD=/absolute/path/chord-core python -m unittest discover -s chord_work -p test_audition.py -v
BENTO_CHORD_BUILD=/absolute/path/chord-core BENTO_FX_CANDIDATE=/absolute/path/eu10 BENTO_K16_IMAGE=/absolute/path/k16/bento1.bin python chord_work/test_native_insert.py
```

The build emits a standalone host library and Thumb binary at a test-only081E0000. It does not modify an image. That address is NOT an allocated release code owner until a guarded integration build proves the full layout. Never copy `chords.bin` to an SD card or rename it `bento1.bin`.

## Verified limits

26 tests pass: 13 host/ARM core tests, five host audition-ownership tests, six native ARM insertion tests and two native piano-roll constructor/projection tests. The core parity test covers 720 preset/scale/key combinations, checking host and Cortex-M4 generation and rendered notes byte for byte. The native tests execute the original note container/ID/publish functions; model lookup, Undo storage and engine-queue delivery are substituted. They prove the insertion boundary/records, not physical playback or native Undo UI behavior.

Standalone ARM payload after audition integration: 4781 bytes. No added audio-rate synthesis or per-sample chord processing. Device CPU/load remains unmeasured.

## Required before first firmware

1. Add Chord toggle and Insert/Update actions to the actual pitched piano-roll header without removing native actions. Verify actual widget placement/event dispatch, not descriptor presence alone.
2. Confirm pitched piano-roll capture, pad keyboard mapping and native audition note-on/off for each supported track. Ensure release, navigation, stop and project change release only tool-owned notes.
3. Add outlined preview and a chord-block strip; select whole chords while retaining individual-note editing.
4. Define saved group membership using native note IDs and explicit group/phrase IDs; integrate XML, copy/paste, deletion, native edits and Undo/Redo. Settings serialization alone is insufficient. Do not steal native note fields or treat a lock token as a group ID.
5. Implement Insert and Update atomically, including group metadata and original-note preservation. Preflight capacities/overlaps/stale context.
6. Connect a clocked looping preview; apply pending edits at the next chord boundary, as approved. No such timing behavior is implemented in C0.
7. Integrate preset and individual-chord encoder banks, key/scale controls and root/register choice. Preset names are template identifiers; actual Roman numerals must reflect the generated qualities and overrides.
8. Run native UI/transport/save-load/Undo regressions, exact-image reversibility and startup guards, then produce a labeled application-only build with the exact EU10 restore pair.

Future rhythm templates, substitution suggestions, pinned-chord variation and reusable user-preset browsing remain planned. `pinned` is a persisted settings flag only in C0; no variation command consumes it yet.
