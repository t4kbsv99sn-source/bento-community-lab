# Integration candidate 0.2.0 — 17 October 2026

**Superseded placement:** see MPU_CORRECTION.md for the 0.3.0 correction. The
0.2.0 UI consumer address below was found incompatible with the original MPU
configuration. Version 0.3.0 appends the consumer in permitted UI-context flash;
it consequently changes image length and still needs loader acceptance verified.

## Work completed

This advances 0.1.0 from artificial code/state locations and host execution
redirection to an **in-memory image containing real patched ARM branches**.
No installable `.bin` is written. The original supplied firmware is unchanged.

Five new integration test methods pass, in addition to the 12 connected tests.
The new tests execute the original startup/heap code, patched startup/input/
consumer branches, our ARM modules and the original selected-track operation.
All eight target pad inputs are exercised through the real branches.

## Memory evidence and reservation

The original startup defines these regions:

| Purpose | Start | End (exclusive) |
|---|---|---|
| Initialized data | 0x24000000 | 0x240001D0 |
| Zeroed data | 0x240001D0 | 0x2401EDBC |
| Zeroed four-byte area | 0x2401EDBC | 0x2401EDC0 |
| Runtime heap | 0x2401EDC0 | 0x24048DA0 |
| Initial stack reservation | 0x24048DA0 | 0x2404CDA0 |

At 0x080404A6..0x080404B4 the original startup writes a zero next-pointer and
the heap length into the first free-list node. Original data copied from
0x080CF2CC initializes free-list head 0x24000178 to 0x2401EDC0.

The candidate reserves 32 bytes at **0x24048D80..0x24048DA0** by reducing the
heap end by 32. It leaves the stack reservation unchanged. The same end address
also occurs in allocator/free-pointer checks, so all three relevant literals
are changed consistently:

| Literal location | Consumer |
|---|---|
| 0x08040588 | Startup heap length |
| 0x080A3BDC | Free-pointer upper-bound check in 0x080A3BAC |
| 0x080A3E94 | Heap-span check in allocator 0x080A3DFC |

The other occurrences of 0x24048DA0 identify the original stack bottom and
stack sentinels; those are retained. A literal-address scan is evidence, not
proof against every computed access or an out-of-bounds stock memory write.

The new test executes the actual startup data copy and heap setup, then the
startup trampoline. Another executes the original allocator until its available
heap is exhausted and verifies that the reserved state is untouched. No
allocator or heap-size logic is replaced by a Python stub in those tests.

## Startup and branch connections

| Patch site | Candidate destination | Function |
|---|---|---|
| 0x080404B6 | 0x080D0300 | Initialize state before stock constructors |
| 0x0808D1FE | 0x080D0000 | Input ownership, musical-event suppression, tagged request |
| 0x0813F98C | 0x080D0200 | Validate tagged request and invoke existing track selection |

All three are real four-byte Thumb `B.W` instructions in the candidate image.
The emulator no longer changes the PC at those input/consumer hook sites.

The startup trampoline initializes the state/map, publishes its magic last,
preserves registers/stack, replays the displaced constructor-range literal
loads explicitly and resumes at 0x080404BA. The test stops before executing the
stock constructors; normal runtime objects are then supplied as fixtures.

The code addresses lie inside the large zero-filled gap before 0x080E0000.
The startup's initialized-data source ends at 0x080CF49C. This is substantially
better evidence than arbitrary RAM placement, but it does **not** establish all
real flash/MPU permissions, loader validation or reserved use of that flash gap.
The disk-mode image at 0x080E0000..0x08100000 is compared byte-for-byte unchanged.

An aligned pointer scan into the broad gap produced false positives from
instruction bytes and tables as well as the startup end-of-data literal.
These were not silently treated as genuine code references or proof of safety.

## Reversibility

`WRITE_MANIFEST.json` lists each of the nine candidate write spans with expected
original bytes, replacement bytes and purpose. All writes remain inside the
supplied application mapping and preserve file length.

`restore()` verifies every replacement span before restoring original bytes.
Its test recreates the exact original image and rejects unexpected changes.
The original SHA-256 check also rejects double application. The manifest does
not attest to installer erase boundaries outside the supplied image.

## Remaining boundaries, stated precisely

The source code now connects its own startup, input and consumer branches in
the emulator. It is no longer accurate to say those connections only exist as
Python callbacks. However, a real-device installer is still blocked by:

- **Physical mapping:** identity mapping is still a test fixture, not evidence
  that logical input 0 is physically top-left. No assumption is promoted to a
  verified production mapping.
- **Loader/write map:** original bootloader erase/program boundaries and image
  validation remain unavailable. Neither this candidate nor its manifest proves
  what the separate original installer will erase. No bootloader bytes have
  been obtained, modified or overwritten.
- **Hardware execution contract:** confirm the candidate flash gap is available
  and executable to both relevant contexts; verify cache/MPU and queue-writer
  concurrency. An emulator does not establish these properties.
- **Lifecycle:** disconnect/reset ownership recovery and full audio/recording
  operation remain outside these bounded tests.

The two manufacturer statements supplied by the owner are accepted as recovery
evidence and do not need to be requested again. They do not contain the missing
memory/erase map. No user device action is requested by this checkpoint.

## Reproduction

From the directory containing `bento_mods`:

```sh
python bento_mods/tests/test_connected.py
python bento_mods/tests/test_integration.py
```

The second suite runs the original byte-wise BSS initialization repeatedly and
therefore takes longer. The 0.1.0 dependency stubs still apply: transport objects,
ordinary UI handling, instrument enumeration and refresh are fixtures/stubs.
Selection's property setter and the allocator/startup instructions run directly.
No test connects to or flashes hardware.
