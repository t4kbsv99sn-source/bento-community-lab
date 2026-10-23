"""Recover stock MPU regions by executing its original configuration routines.

Unicorn does not enforce these Cortex-M MPU settings in our harness. Capture
register writes and evaluate execute permission explicitly as a regression.
This checks configured MPU access, not loader acceptance or physical flash use.
"""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from receiver_fixture import B,BASE
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *


def configuration(entry):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    u.mem_map(BASE,0x180000);u.mem_write(BASE,B)
    u.mem_map(0x24000000,0x80000)
    u.mem_map(0xe000e000,0x1000)
    regions={}
    def capture(uc,access,address,size,value,userdata):
        if address==0xe000eda0:
            number=struct.unpack('<I',uc.mem_read(0xe000ed98,4))[0]
            base=struct.unpack('<I',uc.mem_read(0xe000ed9c,4))[0]
            regions[number]={'base':base,'rasr':value}
    u.hook_add(UC_HOOK_MEM_WRITE,capture)
    u.reg_write(UC_ARM_REG_SP,0x2407e000)
    u.reg_write(UC_ARM_REG_LR,0x2407f001)
    u.emu_start(entry|1,0x2407f000,count=10000)
    assert u.reg_read(UC_ARM_REG_PC)==0x2407f000
    control=struct.unpack('<I',u.mem_read(0xe000ed94,4))[0]
    return control,regions


def executable(address,control,regions):
    if not control&1:return True
    for number,region in sorted(regions.items(),reverse=True):
        r=region['rasr']
        if not r&1:continue
        length=1<<(((r>>1)&31)+1)
        base=region['base']&~(length-1)
        if not base<=address<base+length:continue
        subregion=(address-base)*8//length
        if length>=256 and ((r>>(8+subregion))&1):continue
        ap=(r>>24)&7
        return not bool(r&(1<<28)) and ap in [1,2,3,5,6]
    # The unmatched areas tested here are normal flash addresses, whose default
    # map is executable only if privileged background access is enabled.
    return bool(control&4)


class Tests(unittest.TestCase):
    def test_old_consumer_location_is_not_executable_by_ui_context(self):
        ctrl,regions=configuration(0x08114d74)
        self.assertEqual(ctrl,1)
        self.assertFalse(executable(0x080d0200,ctrl,regions))
        self.assertTrue(executable(0x0813f98c,ctrl,regions))

    def test_candidate_locations_are_in_their_own_executable_regions(self):
        from integration_candidate import INPUT,CONSUMER,STARTUP
        ctrl,regions=configuration(0x0804fa00)
        self.assertTrue(executable(INPUT,ctrl,regions))
        self.assertTrue(executable(STARTUP,ctrl,regions))
        ctrl,regions=configuration(0x08114d74)
        self.assertTrue(executable(CONSUMER,ctrl,regions))


if __name__=='__main__':unittest.main(verbosity=2)
