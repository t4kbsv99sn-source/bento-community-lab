// BENTO_MOD tracks-pad-select 0.4.0 -- calibrated TRACKS input.
// Entry: r4=new, r3=old, r7=logical pad, r11=receiver.
push.w {r0-r12, lr}
sub sp, #32
ldr r8, =@STATE@
ldr r0, [r8]
ldr r1, =@STATE_MAGIC@
cmp r0, r1
bne passthrough
ldrh r9, [r8, #4]
movs r0, #1
lsl.w r10, r0, r7
tst r9, r10
beq fresh
cmp r4, #0
bne consumed
bic.w r9, r9, r10
strh r9, [r8, #4]
b consumed
fresh:
cmp r3, #0
bne passthrough
cmp r4, #0
beq passthrough
ldrb r0, [r8, #12]
cmp r0, #1
bne passthrough
add.w r0, r11, #0x1000
ldrh r0, [r0, #0x338]
tst.w r0, #@TRACKS_MASK@
beq passthrough
add.w r0, r8, #16
ldrb r6, [r0, r7]
cmp r6, #7
bhi passthrough
orr.w r9, r9, r10
strh r9, [r8, #4]
ldr r0, =@PRODUCER_GLOBAL@
ldr r0, [r0]
add.w r1, r0, #0x2000
ldr r2, [r1, #0x1a0]
ldr r3, [r1, #0x180]
subs r2, r2, r3
cmp r2, #224
bhs dropped
movs r1, #0
str r1, [sp]
movs r1, #254
strb r1, [sp]
ldr r1, =@EVENT_MAGIC@
str r1, [sp, #4]
mvn r1, #1
str r1, [sp, #8]
str r6, [sp, #12]
movs r1, #0
str r1, [sp, #16]
ldr r1, =@EVENT_TAIL@
str r1, [sp, #20]
mov r1, sp
ldr r12, =@ENQUEUE@
blx r12
b consumed
dropped:
ldr r0, [r8, #8]
adds r0, #1
str r0, [r8, #8]
consumed:
add sp, #32
pop.w {r0-r12, lr}
push {r0, r1}
ldr r0, =@PAD_NEXT@
str r0, [sp, #4]
pop {r0, pc}
passthrough:
add sp, #32
pop.w {r0-r12, lr}
cmp r4, r3
beq equal
push {r0, r1}
ldr r0, =@PAD_CHANGED@
str r0, [sp, #4]
pop {r0, pc}
equal:
push {r0, r1}
ldr r0, =@PAD_NEXT@
str r0, [sp, #4]
pop {r0, pc}
