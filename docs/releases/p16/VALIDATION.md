# P16 draft software validation

551/551 checks across 28 suites, including 14 navigation checks. Exact candidate
SHA256 edaa6b60ba68353db8021683a0d8dbea7dcf71540f09a4e3c9aebb07a3216c0d,
1,655,756 bytes, four-byte aligned. All source-input hashes match. Entire M7
region byte-identical to delivered P15. Native header rendered with the real
widget/font code. Exact stock/K16 reversal and native safety suites pass.

The first full attempt stopped at an old menu fixture that had not initialized
the native menu definitions. The fixture now initializes them through 081412EC;
all remaining assertions are retained. Legacy layout assertions were updated
for the approved replacement of Undo and the melodic view tabs. The custom
note-touch handlers are gone and tests assert the original vtable addresses.

Not a released build: second Chord bank access awaits a navigation decision.
No hardware test, controller/bootloader change, publication or device flash.

An independent isolated rebuild matches the candidate byte for byte. Tester ZIP includes the known bank-access limitation, source snapshot and P15/stock restore pairs.
