# Bento TRACKS + pad — experimental hardware test 0.4.0

Private, maintainer-authorized experiment for the exact original Bento 1.6.1 files.
D1/D2 established the core path and physical row/button identity on the maintainer's device. The corrected T1 shortcut is pending its device test.
Read the package's `00_READ_ME_FIRST.txt` for Mac installation and restoration.

## Behavior

Holding measured logical switch 2 (TRACKS) claims fresh internal pad inputs
0–7, sends a tagged selection request through the original shared queue, and
calls the original track-selection operation with track index 0–7. Claimed pad
onset, pressure and release events are suppressed. Already-held musical notes
and inputs 8–15 pass through. Releasing TRACKS first still consumes the claimed
pad's release. The ordinary TRACKS event remains in the stock path.

The maintainer's physical naming is top row 1–8, bottom row 9–16. D2 measured top-row group 0–7, bottom-row group 8–15 and TRACKS ID 2 (mask 0x2000). The first two columns were checked; verify the remaining column order in T1.

## Build and verification

- Exact stock SHA-256 and original hook bytes are required. New or modified
  firmware is rejected; the build cannot silently apply to a future release.
- The analyzed application base is 0x08040000. File offset = address minus base.
  Branches are assembled at their actual flash addresses. No header or leading
  padding is inserted, and no original content is shifted to a different offset.
- Real four-byte branches connect the input, consumer and startup trampolines.
- Input/startup code uses the zero-filled gap after the first application's
  initialized-data image. Aligned absolute pointer scanning found no references
  into the allocated gap. This supports placement but is not exhaustive proof
  of unused storage under all possible computed accesses.
- UI code is appended within its original configured executable MPU region.
  The output is four-byte aligned and 144 bytes longer than stock.
- State occupies 32 bytes removed from the top of the input application's heap.
  Startup initialization and allocator upper-bound literals are patched;
  stack boundaries remain unchanged.
- Ten declared write spans change 421 bytes within the original image plus
  144 appended bytes. Reconstructing only those spans reproduces the export;
  reversing them reproduces the exact original stock hash.
- Original vector-table areas, the disk-mode image and bento2.bin are unchanged.
- No bootloader image, bootloader update, direct flash writer or device-access
  command is added. The installer itself has not been recovered or audited.

`BUILD_VERIFICATION.json` in the package is the authoritative output report.
The production `require_installable()` gate intentionally remains closed.
`export_experimental.py` is a separate experimental export path; it does not
turn unresolved verification fields into true values.

## Tests and limits

27 test methods passed: 12 connected instruction tests, 5 startup/heap/branch
integration tests, 2 original MPU-configuration regressions and 8 additional
hardware-candidate/export tests. These cover selection, note preservation,
release ordering, queue saturation, counter wrap, multiple pads, malformed
messages, output alignment and exact restoration. See `ALL_TEST_RESULTS.txt`.

This is bounded instruction emulation, not a complete Bento emulator. It does
not boot the full UI, process audio, validate timing, or prove device behavior.
Fixtures stub packet validation, copy/comparison helpers, record initialization,
some transport-button behavior, ordinary UI handling, recording-context lookup,
instrument enumeration, UI refresh and engine-command transmission. The actual
selection routine and selected-property setter execute original instructions.
The recording-mode test checks notifications with dependencies stubbed; it is
not a recording/playback test.

Still unverified: original installer validation/erase/program ranges and append
acceptance; remaining physical column order; complete gap ownership; live queue
producer concurrency and namespace; disconnect/reset lifecycle; and instrument,
recording and audio side effects. The 32-slot queue margin does not prove
concurrent-producer correctness. Manufacturer reassurance about reinstallation
is evidence for recovery, not a measured erase-range guarantee.

## Source and removal

Feature source/contract: `modules/tracks-pad-select/`.
Stock hashes, hook addresses and symbols: `profiles/bento-1.6.1.json`.
Additional version-specific allocation/heap/startup details:
`integration_candidate.py`, `startup.s`, and the export whitelist. Review them
together when porting. Embedded markers identify module/version.

See `PORTING.md`. Removing this experiment means reinstalling the included
original pair; changing SD files alone does not uninstall an installed patch.
Future official updates must use untouched official files. Private stock
binaries are included only for the owner; do not publish this package.

## Reproduce (developer reference; no commands needed by the owner)

Install `requirements.txt`. Set `BENTO_STOCK_IMAGE` to an absolute path to the
original `bento1.bin`; `BENTO_STOCK_CONTROLLER` defaults to `bento2.bin` beside it.
From this source directory:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python export_experimental.py /path/to/original/bento1.bin /path/to/original/bento2.bin /path/to/new-output-folder
```

The exporter refuses an existing output directory. It creates a test pair,
unchanged restore pair and verification report, and never accesses hardware.

## Correction from the first hardware trial

D1 worked on the maintainer's Bento: pads selected tracks and suppressed notes when
the modifier/map gates were bypassed. D2 readings A=1, B=2, C=3, D=1 measured
TRACKS logical ID 2, raw mask 0x2000, top internal group 0..7 and bottom 8..15.
The earlier inferred ID 5/mask 0x0400 was wrong. The corrected mask now lives
in the version profile as TRACKS_MASK rather than in feature assembly.
T1 displays 1.6T1 and restores the intended modifier and row restrictions.
Hardware success of these diagnostic paths does not prove complete audio,
recording or concurrency behavior, or the installer's complete erase ranges.
