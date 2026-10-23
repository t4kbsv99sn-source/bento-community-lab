// Candidate startup trampoline; hardware behavior remains unverified.
push.w {r0-r12, lr}
ldr r0, =0x24048ca0
movs r1, #0
movs r2, #8
zero:
str r1, [r0], #4
subs r2, #1
bne zero
ldr r0, =0x24048c60
movs r2,#8
lock_zero:
str r1,[r0],#4
subs r2,#1
bne lock_zero
ldr r0, =0x24048a60
movs r2,#128
condition_zero:
str r1,[r0],#4
subs r2,#1
bne condition_zero
ldr r0, =0x24042000
movw r2,#6144
new_lock_zero:
str r1,[r0],#4
subs r2,#1
bne new_lock_zero
ldr r0, =0x24048ca0
movs r1, #1
strb r1, [r0, #12]
// Measured row groups: top 0..7, bottom 8..15. Remaining columns follow stock order; verify on C2.
movs r1, #0
map:
add.w r2, r0, #16
strb r1, [r2, r1]
adds r1, #1
cmp r1, #16
bne map
ldr r1, =0x31534d42
dsb
str r1, [r0]
pop.w {r0-r12, lr}
// Replay displaced literal loads; absolute addresses avoid moved-PC semantics.
ldr r0, =0x080a5f9c
ldr r1, =0x080a5fe8
push {r0, r1}
ldr r0, =0x080404bb
str r0, [sp, #4]
pop {r0, pc}
