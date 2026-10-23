EU8 / 1.6E8 — software validation PASS; hardware validation pending.

CONTROLS_E3_RESULTS.txt: 12 passed
DSP_RESULTS.txt: 38 passed
EDITABLE_EU_RESULTS.txt: 8 passed
EU7_RESULTS.txt: 11 passed
EU8_RESULTS.txt: 14 passed
GESTURES_RESULTS.txt: 6 passed
INTEGRATION_RESULTS.txt: 12 passed
K16_REGRESSIONS.txt: 61 passed
LIVE_RESULTS.txt: 20 passed
PREVIOUS_CONTROLS_RESULTS.txt: 38 passed
SAFETY_RESULTS.txt: 7 passed
VISUAL_RESULTS.txt: 10 passed
Total: 237 passed.
Main SHA256: 880cee6992eb4ebdd296ace06a386fdc3ac2674c03176dd669019ea6be8c0dd0
Size: 1601460 bytes.
Independent isolated rebuild matches exactly. Exact stock and K16 reversibility, source-input hashes, word alignment and application bounds verified. Native controller and synth cave remain unchanged. Original bootloader/vector/recovery/MPU/stack regions unchanged. Native menu construction/application/layout/action emission, complete registry/header widgets, hit-count modes across loops, saved-step preservation and mode XML compatibility execute in the targeted tests. Native GUI-parent routing/SD storage/audio deadlines and physical output still require hardware checks.
