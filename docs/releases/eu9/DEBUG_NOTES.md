# EU9 debugging evidence

Maintainer reports EU8 velocity modes/depth work, but wants white symbols instead of text and faster depth. Lock-condition dial remained near 98% and first A:B choices; Select still absent.

Reproduced no-lock editor rejection: EU8 locks_encoder only processes has_locks, while refresh restores Always. EU9 condition-only immutable records retain the choice before lock creation. Native turn tests cover both endpoints.

EU8's popup geometry tests passed but did not cover the permanent native header; EU9 tests that separate header path. Early local fixture called 08134800 with model display-disabled flag14C=0, which correctly zeroed output; revised fixture runs native header copy with display active and substitutes only clock/metronome formatting. Early test also looked at alternate dropdown buttons+A2C; actual normal buttons are+54C. Corrected before delivery.

First full-test invocation used relative PYTHONPATH entries; the DSP runner changes cwd and could not import Unicorn. Repeated with absolute pinned dependency paths. This was a test-environment error, not a firmware change. Failing attempt retained outside the delivered validation folder.

One isolated run exited during the glyph test without a unittest summary despite exit 0; the wrapper correctly rejected it. New fixtures now keep ARM emulator instances alive until process exit in addition to disabling GC, avoiding callback destruction during the suite. Validation requires every complete Ran/OK summary.

The patcher packaging guard caught a copied EU8 label in the new build wrapper manifest (the firmware itself already displayed 1.6E9). Corrected the wrapper metadata and checked it against an independent rebuild before packaging.
