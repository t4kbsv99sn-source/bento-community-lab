# Superseded software experiments, not delivered

EU7's descriptor-only tests missed native Attack at1E5 and could not verify popup geometry. Those are superseded by real constructor/header/menu application tests.

Early EU8 F9 count 10 was rejected by native menu apply 0817818C, whose check is count-1<=8. Corrected by reusing a blank cell and keeping 9 entries.

Native popup test showed index 1 above Undo: layout is vertical, bottom-up. Final Select is index 4 with four rows, producing the same y/width/height and greater x. Original actions are preserved.

An intermediate attempt to change FA rows at081415EE split the following Thumb32 instruction. Native menu constructor test rejected it with an invalid fetch before delivery. Final patch starts at081415F0 and guards original 32-bit CDF804B0; real constructor and popup tests pass. No intermediate EU8 binaries were offered for installation.

Original development output hashes and logs remain in the workspace; final validated image is identified in VALIDATION.md. No device flashing occurred here.
