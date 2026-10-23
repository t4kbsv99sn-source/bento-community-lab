# Bento Track FX — F1

F1 connects this DSP to the native eight-track mixer and to three rows of
native controls. See the package's 00_START_HERE.md for installation and use.
The earlier T1 preparation package is superseded.

Each track has three RBJ EQ bands (DaisySP Biquads), a stereo-linked DaisySP
Compressor, optional DaisySP Auto Makeup, manual makeup, parallel mix and a
DaisySP MIT SoftClip stage. All three effects default off; Auto Makeup defaults
on, taking effect when compression is enabled. Auto Makeup uses DaisySP's
threshold/ratio compensation estimate, not a loudness measurement or continuous
normalizer. Manual Makeup is additional gain. One peak detector controls both
stereo channels to preserve balance.

The order is native track Level -> EQ -> compressor -> soft clip -> native
pan/ducking/sends/output combination. This processes the track's own scratch
buffer once per track call, not individual rack voices or a shared input bus.
There are no new graphs or meter widgets in F1. Native master processing remains.

The DSP bank needs 5,168 bytes for eight tracks. The bridge reserves 16 KiB from
the existing AXI heap ceiling, split into audio state, UI state and a sequenced
mailbox. The M7 invalidates mailbox cache lines before reading; the UI owns the
mailbox and never calls the DSP. Changes are smoothed. Resetting a runtime track
identity clears its filter/compressor history. No allocations or file I/O occur
in tf_process. The native bridge accepts at most 1,024 frames per channel.

38 DSP tests, 12 native integration tests and 38 existing shortcut regression
checks pass. These include compiled Thumb execution, actual native encoder event
bubbling, native gain/pan/buffer/mixer code, UI-to-audio changes and project XML
round trips with controlled allocator, model lookup, font metrics and XML I/O.
They do not emulate the whole device. Physical screen/touch appearance, SD I/O,
installer behavior and real-time CPU headroom require hardware testing.

The soft clipper rounds sample peaks. At full engagement its own output samples
respect the selected ceiling. It is not an oversampled true-peak limiter; the
bypass fade, later pan/summing and other tracks can exceed that ceiling. The
smooth bypass remainder snaps to exact bypass/full processing to avoid leakage.

The standalone CRC settings record is schema 3 (596 bytes). Schemas 1 and 2
migrate with Auto Makeup off. Native projects instead use named, versioned XML
attributes, bento_fx_version and bento_fx_v1_00 through _17. Missing/future data
loads defaults. Stock firmware does not apply these effects and can discard
custom fields on saving. New FX controls do not yet have native undo support.

## Rebuild and replace the LGPL components

Python 3, g++, numpy, unicorn 2.1.4, keystone-engine 0.9.2, ziglang 0.15.1.
Run `python track_fx/build.py` from fx1_work to rebuild and test the standalone
DSP. Integration build and test commands are in ../REBUILD.md.

Complete wrapper, bridge and modified compressor/biquad sources, LGPL license,
MIT utility attribution, ARM objects and linker scripts are included. The
integration builder recompiles and relinks them before applying guarded patches
to the supplied K8 application. It refuses other baseline hashes. Replace or
edit the LGPL sources and rerun that command to produce a replacement build;
there is no checksum/signature bypass step in this workflow. Keep application
binaries private to the maintainer's supplied firmware workflow.

Pinned DaisySP-LGPL c89d380c62620d6fee9105c5035e081c9b7ea843: Biquad and
Compressor are LGPL-2.1. The Utility SoftClip helpers are from MIT DaisySP
2c72eaf9eac5fc0dca1919d65d606da907832618. See vendor/UPSTREAM.json.
The EQ coefficients implement Robert Bristow-Johnson's audio EQ cookbook.
ARM math uses explicit freestanding approximations, tested against the host.
