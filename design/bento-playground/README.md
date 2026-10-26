# Bento Playground design preview

Open `Bento_Playground_Preview.html` in a browser, or download the repository and open `index.html`. No device connection or audio.

Original charcoal palette, eight track colours, 32 square steps with two lock rails, Euclidean and chord studies, macros, mixer, Track FX and modulation matrix. These are design proposals, not firmware screenshots. The preview label audit is based on P27 and has known gaps; the firmware source snapshot is P27.

Rebuild with `node renderer/build.cjs`; run `node tests/navigation.cjs`. PNG exports optionally use `sharp`; editable SVG exports need no graphics package.

See [design rules](docs/DESIGN_KIT.md), [licensing](docs/LICENSING.md) and [limitations](docs/REFINEMENT_PASS.md).
