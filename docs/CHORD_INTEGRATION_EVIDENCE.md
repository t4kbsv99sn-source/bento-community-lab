# Chord integration evidence — C0, 23 October 2026

Basis: original stock 1.6.1 and EU10 main SHA2564ed81f1604459f338624fcfd4a22e40b29b992f4e9df4303de1a0564b8b32a37. New module is offline/unhooked, branch feature/chord-composer.

## Native piano-roll evidence

- Piano-roll controller event handler 0815A598 is referenced by vtable entry 0819E7E0 (value 0815A599). It has a different object layout from the one-shot32-step view at0815D600. Do not reuse offsets 113DC/113E4 for it.
- Piano-roll view sequence at+11CD00, owner+11CD08, length+11CD18; native container starts+11CD20, secondary container+122D28. Other native UI state is around+125Dxx. These are view-relative offsets in a large SDRAM object, not proposed fixed RAM allocations.
- Native header refresh 081599BC reads sequence properties 61/60/62 and uses its parameter bar at+55F0. It contains floating-point calculations: any trampoline must preserve its ABI and original prologue. This does not authorize calling it from early startup.
- Native 0815ABB8 projects note records into the piano-roll child. At0815AC80 it checks record byte0==1; at0815AC88 it chooses H+2 when view+125DAE is true, otherwise H+16. Pitched view uses the latter branch. Native track-type branching around 0815B00E normalizes UI mode; full track behavior still requires verification per supported type.
- Native note record is24bytes; byte0=kind 1, byte1=probability/condition, H+2=instrument/drum address, W+4=time, W+8=length, W+12=ID, H+16=pitch, H+18=velocity, W+20=existing extension/native data. C0 writes H+2=0 and uses H+16 for pitched tracks, leaving W+20=0.
- Native 0812E070 assigns the project next ID and inserts the note. Native 08136544 upserts/publishes the provided IDs to the audio queue. Calling ID assignment twice would duplicate music; C0 tests the exact model IDs and publish command IDs.
- Native 081338DC snapshots before editing. Test fixture records this snapshot but substitutes its backing storage; full native Undo/Redo remains a device/integration task.

## Current release boundaries

No hooks at the addresses above are installed. Existing EU10 files retain their prior hashes. Standalone test binary is NOT firmware. No fixed state reservation or new registry IDs have been assigned; future work must perform real native registry collision checks.

## Approved design after the earlier proposal

Root pads must audition full chords. Single-chord encoder 4 is Strum, not Octave. Root contains the register. Progression presets need an explicit root/register source. Entry is a proposed touchscreen Chord toggle, with Insert/Update beside it, subject to native layout verification. Single and Progression banks have different assignments.

Use visible chord blocks for group selection. Presets generate the whole phrase; each chord remains editable. Live preview edits apply at the next chord boundary. Scale changes adapt degree roots/qualities while preserving explicit quality overrides. Auto inversion must respect explicit individual choices.

Keep harmony and rhythm separate for later rhythm presets. Use the native clip/notes instead of adding a mandatory new playback engine. These are design requirements, not currently installed functions.

## Primary workflow references

- Hapax: https://squarp.net/hapax/manual/modelive/ — scale-degree chords, modifiers and auto inversion.
- OXI: https://docs.oxiinstruments.com/oxi-one-mkii-manual/chord-mode/ — play/remember/place, user chord slots and auto voicing.
- Aline: https://audiotato.com/ — interchangeable tools editing a sequence; Progress engine with voice leading; independent rhythm/pitch/velocity concepts. Google Docs manual could not be read through the research tool; no unverified details from it are asserted.
- Scaler: https://scalermusic.com/products/scaler-3/ — progression sets, harmonic suggestions, substitutions and performances.
- Captain: https://mixedinkey.com/captain-plugins/how-to-guide/captain-chords/ — editable degree presets, voicing, separate timing/rhythm and user presets.

Original degree tables were written for this project. No commercial preset library or device code was copied.

## Native piano constructor/projection recheck

The native piano-roll constructor at0815930C executes successfully in the fixture and installs vtable 0819E7B0. All eight parameter slots are constructed at view+55F0+38+i*468. Native coordinates are logical 1280-wide; encoder slots are159px wide (last 158), y406, height 70. These are original native slots, not new chord controls.

After C0 insertion, actual native 0815ABB8 copies the inserted sequence notes and invokes native 08176708 with expected time, duration and pitch (first chord 48/52/55 at0, duration 3840). This directly verifies the chosen H+16 pitch branch. The fixture does not initialize the full scale-keyboard mapping from a real project; resulting cell row coordinates are not a physical screen rendering proof. No new preview/chord labels are drawn.

Complete native registry constructor inspection identifies candidate free keys, but many apparent empties belong to lazy mod registries:1A0/1A1/1A2/1A4/1A5/1A6/1A9/1AA/1AD/1B0 are already owned by synth UI;1B1..1D0 includes Track FX;198/199 are lock conditions. Candidate 196/197/19A/19B/19D/19E/19F/1D1 must still be checked against every active owner before registration. No new keys allocated.
