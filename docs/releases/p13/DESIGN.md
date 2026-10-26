# P13 fixes and evidence

Owner P12 report: MOD encoders feel as if they reset while turning, selected
source unclear, melodic Euclidean notes heard only at insertion with a running
playhead, Bars reports one when actual duration is four bars. Device image
hash not independently supplied. No claim that P12 passed hardware validation.

MOD: periodic reconciliation previously compared only route amount and target,
so a native slot refresh to the unmodulated value was invisible. Compare actual
widget +A0 with the displayed depth; reapply when native refresh overwrites it.
Regression runs native 08171C1C between turns and verifies continued depth.
Header identifies selected source(s), with an explicit select prompt and a
bounded count label for 3+ sources. No route format or model storage change.

Bars: native 081599BC reads Snap Mode (61) to view+11CD10. When nonzero it
uses multiplier 1, bypassing Step Len (60); the old custom encoder always used
the Step Len table. With Step Len 1/16 this gives the reported factor of four.
Use native unscaled 960 units in that mode and retain the table otherwise.
Keep step_unit itself raw: the lane renderer uses the table separately for
native display coordinates, so its existing Snap Mode projection is unchanged.

Euclidean: native 08060820 likewise bypasses the grid table when clip+38 is
zero. Match its period in free mode. Retain the most recent block time in the
existing M7-only EuRuntime.spare words; if time rewinds, reanchor scheduling
using the same initialization as an owner/period/epoch change. This fixes a
reproducible permanent future-timestamp stall without changing shared layout,
heap or MPU ownership. Clock rewind is a reproduced failure mode, not proof
of the hardware report's sole cause.

New checks cover native MOD refresh, selected-source names, unscaled-mode Bars,
melodic free timing, rewind, multiple native clip wraps, and the complete
installed native renderer including note-offs. Four regressions fail on the
delivered P12 image before the changes.

Historical binaries remain untouched. Application-only guarded patching and
exact stock/K16 reversal remain required. Hardware validation pending.
