# MPU placement correction — candidate 0.3.0

17 October 2026. Supersedes the consumer location proposed in 0.2.0.

## Concrete issue found

Executing the original UI-context memory-protection configuration at
0x08114D74 shows MPU control value 1: enabled, without privileged default-map
access. Its executable flash region covers 0x08100000..0x08200000.

The earlier candidate put the UI consumer at 0x080D0200, outside that context's
configured executable regions. The original connected/integration tests passed
because the emulator did not enforce this MPU configuration. They therefore
did not prove that the location was executable on the device. This is an
identified defect in the earlier candidate, not merely an untested concern.

The input-context configuration at 0x0804FA00 separately permits executable
flash at 0x08000000..0x08100000, which covers the proposed input and startup
trampolines. No MPU settings are changed by this correction.

`tests/test_mpu.py` executes both original configuration routines, captures the
register writes and explicitly evaluates region priority, disabled subregions,
access permissions, execute-never and privileged default-map behaviour for the
candidate flash addresses. These are bounded configuration tests; they do not
prove that those routines remain the final MPU state in every runtime mode.

## Correction implemented

The UI consumer now starts at **0x081B3F40**, aligned just after the original
image's end at 0x081B3F3C, inside the UI context's executable flash region.
The in-memory candidate therefore appends a four-byte alignment gap plus that
consumer block. Its actual branch is reassembled for the new destination.

Unlike 0.2.0, this candidate changes image length. Loader acceptance of appended
bytes and validation rules are **not established**. This is explicit in the
version profile and write manifest. Moving the code removes the identified MPU
conflict; it does not resolve the separate original-loader integration gap.

The strict restoration function now removes the appended data as well as
restoring original byte spans, then checks the restored full stock hash.
The original disk-mode image remains byte-for-byte unchanged.

## Regression results

- 12 connected test methods: pass.
- 5 real-branch/startup/heap integration methods: pass.
- 2 MPU configuration/placement methods: pass.

The first MPU test rejects the old 0x080D0200 location, so it would fail if that
placement were reintroduced. The second checks both contexts' proposed blocks.
Complete logs and the captured configuration are included.

## What is genuinely still needed

- Original installer validation and erase/program boundaries, including whether
  it accepts the appended consumer block while preserving the original loader.
- Verification that the input/startup flash gap is available, plus lifecycle,
  concurrency and physical pad calibration work already listed in INTEGRATION.md.

The next read-only owner input is the installed bootloader version shown on
its ordinary menu. That identifies the loader we need evidence about; a photo
alone will not reveal its memory/write map. No update or hardware test is needed
to collect the version.

Architectural interpretation uses Arm's official CMSIS documentation:
https://arm-software.github.io/CMSIS_6/main/Core/structMPU__Type.html
The captured register values come from the maintainer's original firmware bytes.
