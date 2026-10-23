// Observe native drum selection from touchscreen OR pads, including same-cell picks.
// Opening INST runs its initialization before the hold is armed, so it is excluded.
push.w {r0-r3, r12, lr}
mrs r12, apsr
push.w {r12, lr}
ldr r3, =0x24048cf0
ldr r0, [r3]
cmp r0, #0
beq replay
cmp r2, #15
bhi replay
movs r0, #1
str r0, [r3, #20]
replay:
pop.w {r12, lr}
msr apsr_nzcvq, r12
pop.w {r0-r3, r12, lr}
// Replay both displaced native instructions exactly.
push {r4-r7, lr}
sub sp, #36
push {r0, r1}
ldr r0, =0x0813bd15
str r0, [sp, #4]
pop {r0, pc}
