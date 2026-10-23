# Bento DaisySP kick K6 / 0.13.5

Private exact-version Bento 1.6.1 application experiment retaining working L8.
Read DEVICE_TEST.md. Audible hardware success and CPU headroom are unverified.

## Hardware evidence and correction

K5_DEVICE_REPORT.txt is the unmodified supplied report. It shows 43 voice
entries, 0x2310 render entries and no synth starts/blocks. The native class is
correct. Descriptor provider is 100455E0; marker reason 1 rejects that pointer
before reading metadata. Native MPU_REGIONS.json input region 5 has base
10040000 and RASR 1307001F: a 64KB accessible region ending 1004FFFF.
K6 includes that precise range. It still requires exact length, mono/48kHz
metadata, 32 signed one-LSB marker samples, and a valid descriptor.

The last rendered sound handle is 13E; last recognised kick file handle is 13F.
These fields describe last-seen events and do not by themselves establish a
complete file-to-sound mapping. They show that assuming identical IDs is
unjustified. K6's real loader path therefore neither emits private activation
commands nor writes the K5 assignment table. Audio selection no longer consults
that table. A stale K5 enable cannot affect unrelated sounds, and a stale disable
cannot block a genuine marker. Legacy explicit command endpoint and bounded
mailbox helpers remain compiled for regression/reference, disconnected from
normal UI loading and audio selection. No new memory reservation is introduced.

The successful software reproduction uses root C5A2AFA0, descriptor 24040158,
provider 100455E0, sound ID 13E and loader file ID 13F. It executes the compiled
marker recognition, DaisySP generator and original native audio postprocessing.
Native provider I/O is a controlled fixture; actual on-device metadata and PCM
format remain subject to the next device report, not assumed proved by tests.

The report is now Projects/BENTO_K6_DIAGNOSTICS.txt, saved only by UI Load.
Marker Projects/BENTO_Kick_K2.wav stays unchanged and is never overwritten.
No audio-thread filesystem operations. Existing K4 diagnostic fields retained.

## Existing functionality

All L8 holds, native mute/solo, LED fixes, conditions, held-step inspection,
two editable parameter locks including sends, PROJ shift and PROJ+PLAY remain.
Native A-D automation unchanged. Fixed kick timbre and normal sampler interface;
no dedicated synthesis control page. Native level/pitch/pan/envelopes/filter/
mute/send processing remains. Original bootloader bytes are not modified.

DaisySP SyntheticBassDrum is MIT, Plaits-derived, vendored at commit
2c72eaf9eac5fc0dca1919d65d606da907832618. Notices/adaptation provenance included.

Install requirements.txt, run export.py STOCK_DIRECTORY L8_DIRECTORY DEST.
The exporter checks exact stock/restore input hashes, original bytes, overlaps,
unchanged regions, full regression suite and byte-exact restoration. Software
checks and packaged hashes do not prove hardware sound or timing. Exact working
L8 and stock restore pairs included. No bootloader updater supplied.
