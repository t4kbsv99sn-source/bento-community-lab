// BENTO_MOD tracks-pad-select 0.4.0 -- experimental hardware-test candidate.
// Entry is the existing low-level dispatcher. Preserve stock event semantics.
push.w {r0-r12, lr}
cmp r5, #254
bne stock
ldr r0, [sp, #604]
ldr r1, =@EVENT_MAGIC@
cmp r0, r1
bne stock
ldr r0, [sp, #620]
ldr r1, =@EVENT_TAIL@
cmp r0, r1
bne stock
mvn r0, #1
cmp r6, r0
bne stock
cmp r7, #7
bhi stock
mov r0, r4
mov r1, r7
ldr r12, =@SELECT_TRACK@
blx r12
pop.w {r0-r12, lr}
push {r0, r1}
ldr r0, =@DISPATCH_NEXT@
str r0, [sp, #4]
pop {r0, pc}
stock:
pop.w {r0-r12, lr}
sub.w r3, r5, #17
push {r0, r1}
ldr r0, =@DISPATCH_STOCK@
str r0, [sp, #4]
pop {r0, pc}
