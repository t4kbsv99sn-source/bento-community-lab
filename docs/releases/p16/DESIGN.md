# P16 melodic SEQ navigation

P15 baseline. Native six-slot persistent header is rebuilt as four native tabs (Chord, Euclid, Step, Seq) and two ordinary buttons (Select, Clear). The header retains the native equal-width geometry. Chord editor visibility is separate from track-owned chord playback; changing editor does not disable that layer. Repeated Chord/Euclid tab actions are idempotent.

Select toggles the native grid selection flag; native piano touch handler pointers remain unchanged. Clear keeps native action 004D. Automation is reachable in the nine-cell F9 menu alongside the five retained sequence operations and three original PROJ pages. Native one-shot menu contents are restored when leaving melodic SEQ.

Undo is removed from native persistent headers and popup definitions and routed through PROJ+Left to the existing piano, drum or model Undo handler. Release is consumed without affecting plain Left or PROJ+Play. No other navigation changes are part of P16.

New menu/header actions 1060..1064 are owned by P16. No EuBank ABI, DSP formula, bootloader, controller, MPU, heap or native piano touch-handler change. Existing application bounds and reversible patch guards remain enforced.

Tests cover the actual installed ARM instructions, real native header templates/root/widgets, tab state, retained chord layer, native selection, Undo, native touch handler addresses and menu transitions. They do not establish physical display/touch timing or hardware reliability.

## Remaining decision

The former Chord 1/2 header action 1052 is displaced by the six requested slots. Chord re-tap deliberately does not switch banks, per owner scope. Bank 2 remains implemented but lacks visible access in this candidate. A separate bank control in the Chord view would restore access; its location has not been approved. No new gesture is installed.
