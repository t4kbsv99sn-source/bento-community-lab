# Developer guide

| Area | Location |
| --- | --- |
| Current build / validation | `tools/build_p27.py`, `tools/validate_p27.py` |
| Sequencing, navigation, modulation, macros | `eu4_work/integration/` |
| Synth DSP | `eu4_work/drums/` |
| Track EQ / compressor / clipping | `eu4_work/track_fx/` |
| Chord editing | `chord_work/` |
| Experimental motion capture | `motion_work/` |
| Reproducible baseline layers | `k16_work/`, `k16_overlay/`, `tf2_work/` |
| Firmware-rendering research | `research/display_emulator/` |
| Original visual preview | `design/bento-playground/` |

Start with QUICKSTART.md, KNOWN_ISSUES.md and the relevant version's DESIGN.md. Directory names are historical; their contents have evolved.

Do not patch the bootloader, alter original firmware input files, add generated firmware/binaries to Git or present passing software fixtures as hardware confirmation. Preserve vendored licences. Use small changes and targeted tests during development; validate the complete candidate before offering an installable release.

The highest-priority open work is reliable macro-strip access/mapping and a genuinely end-to-end motion capture/playback/save/reload path. Include image hash and reproduction steps with hardware reports.
