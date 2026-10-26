# P15 validation — 25 October 2026

Image 1.6P15 SHA256:
`abfd082a9dc539809d525b5d8360d2604d7b5788b8ae30add927fc4cefe37d78`

1,653,964 bytes, four-byte aligned. Two isolated builds (p15-dev2 and
p15-release) match. Complete source-input hashes match the delivered build.
Exact stock and K16 reversal, application bounds, unchanged vectors, MPU,
heap/stack/recovery regions and unchanged controller are verified.
Additional native M7 MPU checks cover both melodic caves and the C6 allocation.

**537/537 software checks across 28 suites**, including 12 new P15 interaction
tests and all 18 P14 melodic-lock checks. Coverage includes actual envelope
phase call sites, release outside the render context, preserved matrix sources,
overridden direct automation, independent stereo overlapping note sends,
unlocked send automation, native gain ramps, track fader/pan/settled mute,
existing bus audio, repeated blocks and the installed stack-argument adapter.
A real native Track FX clipper test verifies the documented pre-Track-FX wet tap.

The first validation invocation used a relative Python dependency path; a nested
DSP test changed its working directory and could not import Unicorn. No failed
firmware assertion. It was rerun with an absolute dependency path, retaining
already-completed suite results for this identical image; all 28 suites finish
with complete Ran/OK summaries. The initially interrupted build log and resumed
validation log are included separately in the package.

M4 allocation: 294,060 requested, 294,080 rounded bytes (about 287 KiB total).
No extra effect instances or per-block heap allocations in the routing helper.
Buffers support 1,024 frames; DSP fixtures use 16 and 128 stereo frames.
Emulated ARM instructions (not hardware CPU percentages):

| Operation | Instructions |
|---|---:|
| Track begin, no send locks | 1,037 |
| Track begin, one send-locked voice | 3,158 |
| Locked voice send routing, 128 stereo frames | 4,820 |
| Unlocked voice routing while another voice has a send lock | 4,876 |
| Publish completed track submixes | 80 |
| Native track mixer with note sends, 128 stereo frames | 20,473 |
| Locked envelope parameter evaluation | 268 |

Routing counts exclude oscillator synthesis. The mixer count includes native dry
processing. These operation counts cannot predict actual device CPU load.
Device playback, screen appearance and real-time performance remain untested.
No device flashing or repository publication performed.
