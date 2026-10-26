# Licensing and asset register

This package contains original procedural graphics and interface layouts. No Torso, Ozon, Fors, Bitwig, Arturia, Elektron or Polyend artwork, logos, font binaries, screenshots or proprietary code are bundled. Reference websites and the owner's Opal screenshot were inspected as design references. They are not redistribution sources.

No open license for Torso/Ozon's identity artwork was found in the inspected case study. Treat that artwork as unavailable for reuse unless its owner grants permission. Likewise, access to a Fors product or manual does not grant permission to redistribute its artwork. This is an asset-policy conclusion, not a claim to have exhaustively searched trademark registrations.

| Asset / candidate | Status | License and action |
|---|---|---|
| Kit SVG paths, icons and JS/C source | Original for this project | GPL-3.0-or-later, consistent with the inspected private project policy |
| System-rendered DejaVu Sans | Used to rasterize previews; binary not bundled | Bitstream Vera terms with DejaVu changes in public domain. Font binary redistribution would require its notice. No proprietary font is embedded |
| Native Bento font | Not distributed | Retain the user's firmware font engine when integrating; do not extract and redistribute font data |
| Inter | Investigated, not used/bundled | SIL OFL1.1. Include license with fonts; comply with reserved font names when modifying. Documents rendered with it do not inherit OFL |
| Lucide | Investigated, not used/bundled | ISC; some Feather-derived icons carry MIT. Preserve appropriate copyright and permission notices with any imported icons |
| Tabler Icons | Investigated, not used/bundled | MIT. Preserve copyright and permission notice if later imported |

The small icon vocabulary here is drawn independently with simple geometric primitives, avoiding external dependencies and attribution ambiguity. An eventual icon import should record upstream version, exact filenames, source URL, license text and modifications before inclusion. Do not replace this register with an unsupported “royalty-free” statement.

Sources checked26 October2026:

- https://lucide.dev/license
- https://tabler.io/license
- https://github.com/rsms/inter
- Local DejaVu package copyright notice at `/usr/share/doc/fonts-dejavu-core/copyright`.

The kit's license does not relicense manufacturer firmware, inherited project code or third-party assets. No firmware binaries are included. Reference brand names identify sources only; no affiliation is implied.
