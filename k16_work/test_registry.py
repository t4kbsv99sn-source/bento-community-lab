"""Execute the entire native registry constructor to verify the new Click slot."""
from pathlib import Path
import struct,sys
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
image=Path(sys.argv[1]).read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
for a,n in [(0xe000e000,0x2000),(0x08040000,0x1c0000),(0x20000000,0x40000),(0x24000000,0x50000),(0x30000000,0x40000)]:u.mem_map(a,n)
u.mem_write(0x08040000,image);sizes=[]
def hook(u,a,n,d):
 if a==0x08104c08:
  sizes.append(u.reg_read(UC_ARM_REG_R0));u.reg_write(UC_ARM_REG_R0,0x20020000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 if a==0x081b0000:u.emu_stop()
u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_SP,0x2003f000);u.reg_write(UC_ARM_REG_LR,0x081b0001);u.emu_start(0x081639a9,0,count=100000)
assert u.reg_read(UC_ARM_REG_PC)==0x081b0000
assert sizes and sizes[0]>=(0x1b0+1)*32,sizes
for key in [0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9,0x1aa,0x1ad,0x1b0]:assert bytes(u.mem_read(0x20020000+key*32,32))==bytes(32),hex(key)
print('Native registry allocated',sizes[0],'bytes; all ten custom descriptor slots are empty and in bounds; PASS')
