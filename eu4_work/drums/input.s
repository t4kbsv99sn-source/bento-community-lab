// BENTO_MOD hold-controls L8 0.12.0 -- calibrated rows, native button IDs.
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
add.w r0, r11, #@LAUNCH_MASK@
ldrh r0, [r0, #0x338]
and.w r0, r0, #@MODIFIERS_MASK@
cmp r0, #0
beq passthrough
cmp.w r0, #@TRACKS_MASK@
beq tracks
cmp.w r0, #@LAUNCH_MASK@
beq launch
cmp.w r0, #@MIXER_MASK@
beq mixer
cmp.w r0, #0x100
beq project
// Ambiguous multi-button chord: silence the pad without changing anything.
orr.w r9, r9, r10
strh r9, [r8, #4]
b consumed
project:
// Instrument rack only: snapshot the native selected-cell handle to guard
// against navigation before this queued request reaches the UI thread.
ldr r0, =0x30024b00
ldrb.w r1, [r0, #0x12c]
cmp r1, #7
bne passthrough
ldr.w r1, [r0, #0x13c]
cmp r1, #0
beq passthrough
str r1, [sp, #24]
movs r5, #9
b mapped
mixer:
movs r5, #5
b mapped
launch:
movs r5, #3
b mapped
tracks:
movs r5, #1
mapped:
cmp r5, #9
beq map_index
cmp r7, #8
it hs
addhs r5, #1
map_index:
add.w r0, r8, #16
ldrb r6, [r0, r7]
cmp r6, #15
bhi passthrough
orr.w r9, r9, r10
strh r9, [r8, #4]
ldr r0, =@PRODUCER_GLOBAL@
ldr r0, [r0]
add.w r1, r0, #@TRACKS_MASK@
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
cmp r5, #9
beq drum_request
and.w r6, r6, #7
b request_index
drum_request:
ldr r1, [sp, #24]
str r1, [sp, #8]
request_index:
str r6, [sp, #12]
str r5, [sp, #16]
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
