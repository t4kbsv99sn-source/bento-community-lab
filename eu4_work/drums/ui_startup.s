// Initialize UI-owned state on every CM4 application start, including warm reset.
// CM4 has no D-cache. Never touch the adjacent M7-owned input cache line.
push.w {r0-r12, lr}
ldr r0, =0x24048cc0
movs r1, #0
movs r2, #56
zero:
str r1, [r0], #4
subs r2, #1
bne zero
ldr r0,=0x24048000
movw r2,#512
step_ui_zero:
str r1,[r0],#4
subs r2,#1
bne step_ui_zero
dsb
pop.w {r0-r12, lr}
ldr r0, =0x081891fc
ldr r1, =0x08189258
push {r0, r1}
ldr r0, =0x081004bb
str r0, [sp, #4]
pop {r0, pc}
