push.w {r0-r12, lr}
sub sp, #8
add.w r0, sp, #608
str r0, [sp]
mov r0, r4
mov r1, r5
mov r2, r6
mov r3, r7
ldr r12, =0x081b4101
blx r12
cmp r0, #0
add sp, #8
pop.w {r0-r12, lr}
bne consumed
sub.w r3, r5, #17
push {r0, r1}
ldr r0, =@DISPATCH_STOCK@
str r0, [sp, #4]
pop {r0, pc}
consumed:
push {r0, r1}
ldr r0, =@DISPATCH_NEXT@
str r0, [sp, #4]
pop {r0, pc}
