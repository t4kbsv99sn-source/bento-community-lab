"""Actual branch-patched image and startup/heap tests, all in emulator memory."""
from pathlib import Path
import sys
import struct
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_connected import Connected, B, MODEL
from integration_candidate import candidate, restore, BASE, HEAP_START, OLD_HEAP_END, STATE, CONSUMER
from unicorn.arm_const import *

PATCHED, WRITES = candidate(B)
STOP=0x2407f000


class Integrated(Connected):
    def __init__(self):
        super().__init__()
        self.u.mem_write(BASE,PATCHED)
        # Artificial overlay code from the older harness remains mapped but is
        # not entered. Both real hook sites execute patched B.W instructions.
        self.entries=[]

    def callback(self,u,a,size,userdata):
        if a in [0x0808d1fe,0x0813f98c]:
            return  # No host PC redirection: execute the actual branch bytes.
        if a in [0x080d0000,CONSUMER,0x080d0300]:
            self.entries.append(a)
        super().callback(u,a,size,userdata)

    def startup(self):
        # Execute original data copy, BSS clearing and heap setup, then the
        # actual patched startup branch. Stop before stock constructors.
        self.u.mem_write(STATE,bytes([0xa5]*32))
        self.u.reg_write(UC_ARM_REG_SP,0x2404cda0)
        self.u.emu_start(0x0804044d,0x080404ba,count=2000000)
        assert self.u.reg_read(UC_ARM_REG_PC)==0x080404ba

    def initialize_runtime_fixture(self):
        # Startup deliberately cleared synthetic transport fixtures. Restore
        # them as stand-ins for later original constructors/main initialization.
        self.word(0x2401bd3c,0x10040000)
        self.word(0x3000f650,0x30040000)
        self.word(0x24010000+0x8c8,0x24040000)
        self.u.mem_write(0x24010000+0x1321,b'\1')

    def allocate(self,size):
        self.u.reg_write(UC_ARM_REG_R0,size)
        self.u.reg_write(UC_ARM_REG_SP,0x2404cda0)
        self.u.reg_write(UC_ARM_REG_LR,STOP|1)
        self.u.emu_start(0x080a3dfd,STOP,count=10000)
        assert self.u.reg_read(UC_ARM_REG_PC)==STOP
        return self.u.reg_read(UC_ARM_REG_R0)


class Tests(unittest.TestCase):
    def test_original_startup_reserves_and_initializes_state(self):
        m=Integrated();m.startup()
        self.assertEqual(m.readword(HEAP_START+4),STATE-HEAP_START)
        self.assertEqual(m.readword(0x24000178),HEAP_START)
        self.assertEqual(m.readword(STATE),0x31534d42)
        self.assertEqual(bytes(m.u.mem_read(STATE+16,16)),bytes(range(8))+bytes([255]*8))
        self.assertEqual(m.u.reg_read(UC_ARM_REG_R0),0x080a5f9c)
        self.assertEqual(m.u.reg_read(UC_ARM_REG_R1),0x080a5fe8)
        self.assertEqual(m.u.reg_read(UC_ARM_REG_SP),0x2404cda0)
        self.assertIn(0x080d0300,m.entries)

    def test_real_branches_drive_selection_after_startup(self):
        for p in range(8):
            m=Integrated();m.startup();m.initialize_runtime_fixture()
            pads=[0]*16;pads[p]=1000
            m.packet(0x2000,pads);self.assertEqual(m.events(),[])
            m.drain()
            self.assertEqual(m.selected,p)
            self.assertIn(0x080d0000,m.entries)
            self.assertIn(CONSUMER,m.entries)
            m.packet();self.assertEqual(m.events(),[])

    def test_real_allocator_exhaustion_preserves_reserved_state(self):
        m=Integrated();m.startup()
        before=bytes(m.u.mem_read(STATE,32))
        pointer=m.allocate(STATE-HEAP_START-16)
        self.assertTrue(HEAP_START <= pointer < STATE)
        self.assertEqual(m.allocate(64),0)
        self.assertEqual(bytes(m.u.mem_read(STATE,32)),before)

    def test_manifest_restores_exact_original_and_rejects_drift(self):
        self.assertEqual(restore(PATCHED,WRITES),B)
        bad=bytearray(PATCHED);bad[WRITES[0]['address']-BASE]^=1
        with self.assertRaises(ValueError):restore(bad,WRITES)

    def test_all_writes_stay_in_application_and_disk_image_unchanged(self):
        self.assertEqual(PATCHED[0xa0000:0xc0000],B[0xa0000:0xc0000])
        self.assertTrue(all(BASE <= w['address'] and w['address']+w['size'] <= 0x08200000 for w in WRITES))
        self.assertGreater(len(PATCHED),len(B))
        self.assertEqual(restore(PATCHED,WRITES),B)


if __name__=='__main__':unittest.main(verbosity=2)
