# Bento Community Lab

An experimental community-driven project exploring firmware modifications, workflow improvements, new instruments, and expanded sequencing capabilities for the **1010music Bento**.

## Goals

- **Workflow & Navigation:** Improve navigation speed, performance controls, and overall usability while staying true to Bento's original design philosophy.
- **Advanced Sequencing:** Expand sequencing capabilities with parameter locks, conditional triggers, chord and progression tools, generative sequencing, and more.
- **Sound Design & Synthesis:** Experiment with new synthesis engines, programmable drum instruments, and expanded sound-shaping possibilities.
- **Creative Exploration:** Explore the possibilities of Bento's hardware beyond the stock firmware, experimenting with new ideas and features.
- **Community Collaboration:** Encourage experimentation, knowledge sharing, and contributions from other developers and Bento enthusiasts.

## Project Status

🚧 **Early Experimental Development**

Bento Lab is an evolving project. Features are being actively explored, implemented, and tested on hardware.

Some modifications may already be functional, while others remain experimental or under development. Stability and compatibility are not guaranteed.

What's in there so far:

- Hold TRACKS + a pad to jump straight to a track, launch/stop clips and mix from the pads
- Hold a step to tweak it, trigger conditions and two parameter-lock encoders
- Programmable Kick, Snare and Hi-hat synths
- Euclidean drum patterns with their own lengths, velocity shapes and editable notes
- A per-track channel strip: EQ, compressor and soft clipping
- A chord and progression editor (very early: its button doesn't show up on the device yet)

The full rundown, including what's still wonky, is in [docs/FEATURES_AND_STATUS.md](docs/FEATURES_AND_STATUS.md).

## Try it

You build it yourself from your own original Bento 1.6.1 firmware. No 1010music firmware lives in this repo. The [quick start](docs/QUICKSTART.md) walks you through it: one command builds a release, checks it, and gives you a ZIP with the firmware plus a way back to stock.

## Contributions

Ideas, experimentation, testing, and code contributions are welcome!

Take a look around, try it on your Bento, open an issue with a feature idea or something you noticed, or fork it and go your own way. The goal is to create a collaborative environment where Bento enthusiasts can explore new possibilities, share discoveries, and improve the instrument together.

If you want to dig into the code, [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) shows where things live.

## Disclaimer

Bento Lab is an unofficial community project and is not affiliated with or endorsed by 1010music.

**Firmware modifications are performed at your own risk.** Experimental firmware may cause instability, data loss, or potentially render your device unusable.

**Do not modify or overwrite the bootloader.** Always keep backups of your original firmware and project data, and make sure you understand the recovery process before flashing modified firmware.

The contributors cannot guarantee the safety or reliability of experimental builds.

## A note on how it's made

Much of the code was written with AI coding assistants and then tried out on a real Bento.

## Related projects

- [romanjeff/bento_enhanced](https://github.com/romanjeff/bento_enhanced): Bento hardware and firmware research
- Blackbox mods that inspired this: [viktorakos95/blackbox-mod](https://github.com/viktorakos95/blackbox-mod), [pocketrave/blackbox](https://github.com/pocketrave/blackbox), [Blindsmyth/custom-blackbox-fw](https://github.com/Blindsmyth/custom-blackbox-fw)

## License

GPL-3.0-or-later. Bundled DaisySP code keeps its MIT / LGPL-2.1 licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
