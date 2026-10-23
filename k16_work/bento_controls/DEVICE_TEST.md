# K7 — hands-on kick controls

This build adds the kick instrument controls to the K6 version whose sound you
confirmed working. The previous shortcuts, step editing, locks and mutes remain.

## Install on your Mac

1. Unzip this download. Save your project and keep a copy of its folder first.
2. Connect Bento's USB-C Device port to your Mac.
3. Press PROJ + PLAY, then open Menu → SD Reader Mode.
4. In Finder, copy BOTH files inside **01_K7_TEST_FIRMWARE** to the top level of
   the Bento card. Replace the existing bento1.bin and bento2.bin.
5. Wait for copying to finish, eject the card in Finder, and press **<** on Bento
   to leave SD Reader Mode. After it restarts, turn it off.
6. Connect external power and hold power until the bootloader screen appears.
7. Press **REC** directly to install. Do not press >; that opens Hardware Test.
8. Check the version is **1.6K7**.

## Open and test the controls

1. Open your one-shot track and select the pad with the working kick.
   If needed, use Load → Projects → BENTO_Kick_K2.wav as before.
2. Open that pad's individual instrument editor (tap the selected on-screen pad
   if you are still looking at the bank of 16 pads).
3. The top row should read:
   **Level | Tune | Decay | Tone | Impact | Sweep | Sweep Dec | Dirt**.
4. The second row should read:
   **Kick | Load | Pan | Overdrive | Delay Send | Reverb Send | Filter | Resonance**.
   The selected pad is also named **Kick / Pad 1** (or its actual pad number).
5. Select the row on the screen, then use the matching physical encoder.
   Try Tune and Decay while playing or sequencing the kick. Tune is in Hz;
   the other synth controls use percentages. Level and all six Mix/FX controls
   use Bento's existing sound processing and units.
6. The Kick control selects the pad. Load opens the normal sample browser.
   Check that selecting an ordinary sample brings its ordinary editor back.
7. Save a COPY of the project, change Tune, then reload the saved copy.
   Confirm the saved tune returns. Please report if the screen or sound differs.
8. Check that another ordinary sample still plays and edits normally.

The graph underneath is a simple decay illustration using Bento's existing
envelope widget, not an oscilloscope or exact picture of the kick waveform.
The extra third control row and sampler waveform are hidden for the kick.
There is no extra pad-bank grid added to this individual editor.

## Save behaviour and limits

The seven synth settings are stored as named, versioned attributes in each pad's
existing project params. They do not consume automation lanes A–D. This build
adds ordinary instrument editing; dedicated step-lock targets for these seven
new synth controls are not added yet. Native Mix/FX behaviour remains in place.
Unknown or absent kick settings use the established K6 defaults. Stock firmware
ignores the additional attributes; saving in stock can discard those settings.
The reserved kick WAV remains silent in stock firmware.

## Restore

To return to the version with the working kick, install BOTH files from
**05_PREVIOUS_K6_RESTORE** using the same steps. Exact L8 and stock pairs are in
**02_PREVIOUS_L8_RESTORE** and **03_ORIGINAL_1.6.1_RESTORE**.

## If something differs

Please say which row or control is affected, whether the kick still sounds,
and whether the issue happens before or after saving/reloading. For an audio
failure, press Load in the one-shot bank, then cancel. The existing report is
**Projects/BENTO_K7_DIAGNOSTICS.txt**. Send it back if needed.

## Verification

Compiled-code software tests exercise row order, ordinary-sample fallback,
control changes, XML save/load, CPU register preservation and DSP parameter
transfer, together with previous regressions. These are software fixtures;
the new editor and project persistence still require this device test.

Only the application firmware is patched. Original bootloader bytes are not
modified and no bootloader updater is supplied. Original module headers,
vectors, disk/recovery image, native SD installer and controller stay unchanged.
The installer's erase ranges have not been independently verified.
