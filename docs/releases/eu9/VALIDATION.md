EU9 / 1.6E9 — software validation PASS; device validation pending.

CONTROLS_E3_RESULTS.txt: 12 passed
DSP_RESULTS.txt: 38 passed
EDITABLE_EU_RESULTS.txt: 8 passed
EU7_RESULTS.txt: 11 passed
EU8_RESULTS.txt: 14 passed
EU9_RESULTS.txt: 6 passed
GESTURES_RESULTS.txt: 6 passed
INTEGRATION_RESULTS.txt: 12 passed
LIVE_RESULTS.txt: 20 passed
PATCHER_RESULTS.txt: 7 passed
PREVIOUS_CONTROLS_RESULTS.txt: 38 passed
SAFETY_RESULTS.txt: 7 passed
VISUAL_RESULTS.txt: 10 passed
K16_REGRESSIONS.txt: 61 passed
Total: 250 passed (243 firmware checks + 7 patcher checks).
Main SHA256: fd156059cd68951b194788b71a4a6565deeab8e655a3fa8f9985213a7433228c
Size: 1601856 bytes.

Independent isolated rebuild byte-identical. Stock/K16 reversibility, application bounds, input/source hashes, word alignment, controller and synth cave checked. Native persistent header construction/application/action emission and real widget turns execute in the new tests; clock formatting, parent routing and SD transport remain fixtures. Browser JS and Python patchers reconstruct the same release and refuse invalid inputs. Original bootloader, native note/voice/MPU/heap/stack/vector/recovery layouts and audio DSP unchanged. No device flash performed.
