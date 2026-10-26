# Public snapshot verification — 26 October 2026

## Scope

This publication deliberately stops at **P27 / 1.6P27**, as requested by the maintainer. P28/P29 changes and arpeggiator code are excluded. It is an experimental source snapshot, not a new stable release or a binary distribution.

The previous CH10 public commit remains in the repository history. The separate design preview includes later visual refinements, clearly labelled as proposals based on the P27 audit.

## Checks performed for this export

- 458 retained non-Markdown source/configuration files matched the pinned P27 Git blob hashes exactly (excluding the public historical release registry). See SOURCE_SNAPSHOT.json.
- Rebuilt P27 from the exported source using the exact original Bento 1.6.1 main firmware supplied locally. Manufacturer firmware and generated build files are excluded from publication.
- The rebuilt main application matches the recorded P27 SHA256 exactly:
  `bfa9a21917c30b3d7429640784c26c78e5bb22cb19fbde0d1a84bd28d5b14671`
- Builder checks passed: alignment/application bounds, exact stock reversal and K16 baseline reversal. The motion layer performed its repeat-build verification.
- All exported Python source parsed successfully. Browser-preview navigation/state checks passed.
- Export scanned for prohibited binary formats, private-marked content, personal paths/account details and credential patterns. Vendored licensing notices retained.
- Public README, feature descriptions, known issues, build instructions and developer guide were rewritten for this stopping point. Private conversational status history was not mirrored.

The historical P27 development record reports 590 software checks. That complete suite was not rerun for this source-only export; no device was flashed or hardware functionality newly validated. Existing macro/motion failures remain documented.

The targeted exported-build safety suite passed all 7 checks (alignment, vectors, recovery, heap/permissions and patch reversal). The initial wrapper invocation could not locate the isolated Unicorn dependency; rerunning the same suite with its dependency path supplied passed. No firmware code was changed.
