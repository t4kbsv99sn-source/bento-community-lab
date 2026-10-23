# Maintaining and removing the feature

Stable feature ID: `tracks-pad-select`. Version: `0.4.0`.
Source and contract live in `modules/tracks-pad-select/`. Every assembled block
contains a readable `BENTO_MOD:tracks-pad-select:0.4.0:<block>` marker.

Version-dependent details are explicit: the JSON profile contains stock hashes,
hook bytes and dispatch symbols; `integration_candidate.py` contains flash/heap
placement and heap literals; `startup.s` contains state initialization and the
displaced constructor-table loads; `export_experimental.py` contains the
controller hash and permitted-write whitelist. Review all four when porting.
These are not universal addresses, and future ports are not automatic.

When official firmware changes:

1. Start from the new untouched official files, never from this patched image.
2. Check whether official behavior now replaces this feature. If so, omit the
   module and use official firmware normally.
3. Otherwise create a new profile and review every version-specific location,
   register/stack contract, memory permission and queue interface.
4. Preserve physical pad names: top row 1–8, bottom row 9–16. Calibrated wiring
   belongs in the input-to-track map. Row groups and TRACKS input were measured with D2; remaining column order requires the T1 check.
5. Rerun behavior, real-branch, startup, heap, MPU and export/restoration tests.
   Review real-device evidence and installer behavior separately.
6. Generate a fresh exact-byte manifest. Never relax hash checks or guess
   offsets to make an unsupported version build.

The exporter accounts for every byte and rejects unknown stock inputs.
It does not verify what the device installer erases. Unresolved profile flags
remain false, even though experimental export is explicitly available.

For complete removal, reinstall both files from `02_ORIGINAL_1.6.1_RESTORE`
through Bento's ordinary bootloader menu. This removes the active application
hooks. It does not claim to erase all trailing marker bytes from flash: the
installer's exact erase policy has not been measured.

The runtime enabled byte supports future disabling: fresh pads pass through,
while already-owned releases still finish cleanly. There is no user-facing
enable/disable setting in this first hardware test.
