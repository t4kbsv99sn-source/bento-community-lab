# P13 software validation

Image SHA256: 53195037864f43bacc853d954c6852c1990973d860eacaf388acd0988b6950e6

1,649,328 bytes, four-byte aligned; application-only patch bounds, exact
stock/K16 reversal and unchanged controller required by the build/package.
Final full validation: **507/507 checks across 28 suites**, recorded in
VALIDATION_SUMMARY.json in the ZIP.
No hardware installation has taken place here.

Regression checks fail against P12 for native widget reset, free audio timing,
clock rewind and Bars in native unscaled length mode. Final candidate also
checks repeated native-renderer clip wraps and native note-offs. Native widget
render inspected for named MOD sources and orange selected source frames.

Imported Git history contains unavailable historical objects. The packaged
Git bundle is explicitly a self-contained, parentless source checkpoint with
an identical release tree, rather than a claim of restored full ancestry.
The release source commit is retained separately in SOURCE_COMMIT.txt.
