/* AArch64 reboot(RESTART2, "recovery"), using the validated kernel reboot path. */
.text
.global _start
_start:
    movz x0, #0xdead
    movk x0, #0xfee1, lsl #16
    movz x1, #0x1969
    movk x1, #0x2812, lsl #16
    movz x2, #0xc3d4
    movk x2, #0xa1b2, lsl #16
    adr x3, recovery_cmd
    mov x8, #142
    svc #0
    mov x0, #1
    mov x8, #93
    svc #0
recovery_cmd:
    .asciz "recovery"
