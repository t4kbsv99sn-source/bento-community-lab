# Developer quick start

You need your own **original Bento 1.6.1** firmware
pair, Git, Python 3.12, and native C/C++ compilers (`cc`, `g++`). Python supplies
the pinned Zig compiler and ARM emulation packages. No separate Ghidra install
is needed to reproduce the firmware. Start here rather than following old
release-by-release packaging commands.

## Reproduce and make an install ZIP

```sh
git clone https://github.com/t4kbsv99sn-source/bento-community-lab.git
cd bento-community-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/prepare_tester.py --stock-dir /absolute/path/to/original-1.6.1 --out /absolute/path/to/bento-eu10-test
```

`--stock-dir` must contain `bento1.bin` **and** `bento2.bin` from the original
1.6.1 download, not another modified build. Use a new/empty output directory.
For the newest checkpoint, CH10 / 1.6HA (chord mode, Euclid lanes, Bars encoder), add `--target ch10`. For CH1, add `--target ch1`; the default is `--target eu10`.

The helper extracts the pinned source commit into an isolated workspace, builds
it, runs all release checks and compares the final firmware hash to the known
release. It then creates **Bento_1.6EA_Tester.zip** (or **Bento_1.6H1_Tester.zip** / **Bento_1.6HA_Tester.zip**).
No earlier ZIP, firmware download, build-time GitHub token or Ghidra export is
required.

The ZIP includes the test firmware pair, all three generated synth selectors,
your exact stock restore pair, checksums, source and validation records. It does
not connect to or flash Bento. Follow its `00_START_HERE.txt` on a test project.
The ZIP contains the stock files you supplied; keep it separate from source
commits. It restores to stock, not automatically to your previous custom build.

**Current CH1 feedback reports missing Chord and Select buttons. EU10 predates
Chord; its shared Select UI still needs independent confirmation after earlier
missing-button reports. This tool reproduces checkpoints; it does not fix UI.**
Read [features/status](FEATURES_AND_STATUS.md) before choosing a target.

## Exact inputs and outputs

| Item | SHA256 |
| --- | --- |
| Original 1.6.1 main | `14475e9d5068f5659d0fe0b00fc1278c1479c43ed9fda3d40654d5f3a7a6bbb3` |
| Original controller (unchanged) | `8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d` |
| EU10 / 1.6EA | `4ed81f1604459f338624fcfd4a22e40b29b992f4e9df4303de1a0564b8b32a37` |
| CH1 / 1.6H1 | `20c36100c2d44d3d0743e8e9ab7833eafe6c3517b68b0eca688d9e01dc3e9bca` |

Check local files with `shasum -a 256 bento1.bin bento2.bin`. The helper refuses
wrong inputs before creating output. It never silently uses a newer stock version.

## Environment notes

On macOS, Apple's Command Line Tools provide Git and the native compilers;
`xcode-select --install` installs them if missing. On Linux install Python's venv
support, Git and a native C/C++ toolchain using your distro's packages. The
end-to-end helper is checked on Linux/Python3.12; a fresh macOS run still needs
community confirmation. Windows users can try a Linux environment such as WSL;
no native Windows setup is currently verified.

If `git` cannot resolve a pinned tag, run `git fetch origin --tags`; retain the
original tags. If you install dependencies with a custom `PYTHONPATH`, make it
absolute: the DSP runner changes working directory. Prefer the venv above.

An aborted/truncated test run is a failure even if a native process exits 0.
Native integration suites retain cyclic callback owners until process exit.
The visual checks also run in separate processes to avoid a known Unicorn
cleanup problem. If a run fails, retain its log and use a new output directory when
retrying; never label an incomplete run as passed.

## Work on your own changes

The reproduction helper intentionally builds fixed release tags. Editing main
will not change the firmware it produces. For development, create a branch and
build the actual worktree instead:

```sh
git switch -c your-feature
python tools/build_ch1.py --stock /absolute/path/to/original-1.6.1/bento1.bin --out /absolute/path/to/your-development-build --test
```

This produces a main firmware image and logs, not an install ZIP. Its hash
may differ after code changes. Keep your stock controller/restore separately.
Do not use `prepare_tester.py` as a packager for an arbitrary changed binary: it
will rightly reject an unrecognised image. Include your source commit, hash,
logs and precise hardware observations in a review request.

