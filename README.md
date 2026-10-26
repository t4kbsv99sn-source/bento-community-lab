# Bento Community Lab 

An experimental community-driven project exploring firmware modifications, workflow improvements, new instruments, and expanded sequencing capabilities for the **1010music Bento**.

**Bento Playground** is the current development direction: immediate access, deeper sequencing and expressive sound design while keeping Bento's minimal workflow.

## Current state — 26 October 2026

This repository now contains the **P27 / 1.6P27 development source snapshot**, plus the separate Playground design preview. **P27 is not a stable release:** hardware reports still identify incomplete macro mapping and unverified motion recording. Publishing their source does not mean these features are finished.

The previous public **CH10 / 1.6HA** snapshot remains available at commit [`302ebf4`](https://github.com/t4kbsv99sn-source/bento-community-lab/tree/302ebf4a7e63f857c509705933f81e000dbd8a6d). It is an earlier experimental version, not a stability guarantee.

## What's included

- **Sequencing:** two parameter locks per step/note, trigger conditions, drum and melodic Euclidean tools, chord editing, and Chord / Euclid / Step / Sequence navigation.
- **Sound design:** programmable Kick, Snare, Hi-hat, Clap and Tom/FM-percussion engines; Analog/subtractive synthesis work; drum-synth modulation matrix destinations; MOD/MATRIX editing access.
- **Performance and workflow:** tempo, tap tempo, swing, key/scale, velocity, octave and chord controls; track-selection pad feedback, Undo shortcut and navigation fixes.
- **Mixing:** per-track EQ, compressor and soft clipping; supported melodic note-owned delay/reverb sends.
- **Experimental source:** motion recording and assignable macros. See the known issues before treating these as usable features.
- **Visual design:** original palette, square step grid, two lock strips, macro, mixer, channel-strip and modulation studies in an interactive browser preview. These designs have **not** replaced the firmware screens.

Read the [changes since CH10](docs/CHANGELOG.md), [feature status](docs/FEATURES_AND_STATUS.md), [known issues](docs/KNOWN_ISSUES.md) and [publication checks](docs/PUBLICATION.md).

## Explore or build

- [Open/download the design preview source](design/bento-playground/README.md).
- [Build instructions](docs/QUICKSTART.md): supply your own original Bento 1.6.1 firmware. No manufacturer firmware or installable binaries are distributed here.
- [Developer guide](docs/DEVELOPER_GUIDE.md): source map, tests and contribution guidance.

PROJ acts as Shift. In the current development source, **PROJ + PLAY** opens Performance, **PROJ + Left** is Undo and **PROJ + Up** enters SD-card mode. Original project/settings entries are reached through the Performance burger menu. Earlier snapshots have different bindings.

## Contributions

Bug reports, reproducible hardware observations, code reviews and design feedback are welcome. Include the exact version, build hash, reproduction steps and what you expected. Software tests and actual device results are tracked separately. Much of this project was developed with AI coding assistants and tested incrementally on hardware.

## Disclaimer

Bento Lab is unofficial and is not affiliated with or endorsed by 1010music. Firmware modifications are performed at your own risk and may cause instability or data loss. Do not modify or overwrite the bootloader. Keep original firmware and project backups and understand the device's recovery process before flashing modified firmware. No automatic flashing is performed by these tools.

## Related projects

- [romanjeff/bento_enhanced](https://github.com/romanjeff/bento_enhanced)
- [viktorakos95/blackbox-mod](https://github.com/viktorakos95/blackbox-mod)
- [pocketrave/blackbox](https://github.com/pocketrave/blackbox)
- [Blindsmyth/custom-blackbox-fw](https://github.com/Blindsmyth/custom-blackbox-fw)

## License

Project code is GPL-3.0-or-later. Bundled third-party code keeps its original MIT/LGPL-2.1 licences; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No proprietary reference artwork or fonts are bundled with the design preview.
