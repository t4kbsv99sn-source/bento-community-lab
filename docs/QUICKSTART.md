# Build the P27 development snapshot

This builds source locally; it is not a recommendation to install P27. Read [known issues](KNOWN_ISSUES.md) first. No firmware files are supplied by this repository.

You need Python 3, Git, a native C/C++ compiler (`cc` and `g++`), and your own exact original Bento **1.6.1** firmware. The builder checks the main image SHA256 and refuses other inputs. Never substitute an already-modified image.

```sh
git clone https://github.com/t4kbsv99sn-source/bento-community-lab.git
cd bento-community-lab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tools/build_p27.py --stock /absolute/path/to/original/bento1.bin --out /absolute/path/to/empty/p27-build --test
```

The output directory must be empty. The builder creates the main application image, patch manifests and validation records; it does not flash a device. Keep the matching original controller firmware and original restore pair yourself. No modified controller or bootloader is produced.

To inspect a build without the unfinished motion layer, add `--no-motion` and choose a different empty output directory. This does **not** fix the macro issues and produces a different image hash.

Expected historical P27 main-image SHA256, with motion enabled:

`bfa9a21917c30b3d7429640784c26c78e5bb22cb19fbde0d1a84bd28d5b14671`

See [publication checks](PUBLICATION.md) for whether this export independently reproduced it. A matching hash is not a hardware-functionality guarantee.

## Previous public CH10

Check out commit `302ebf4a7e63f857c509705933f81e000dbd8a6d` to use its original instructions and pinned build path. Do not run an old version's builder against the current moving source and expect the old firmware.

`prepare_tester.py` and its target registry are retained for historical pinned releases. They do not provide a P27 target. Use `build_p27.py` above for this snapshot.

## Design preview

Open `design/bento-playground/Bento_Playground_Preview.html` directly in a browser. It needs no firmware, server or installation and produces no audio.
