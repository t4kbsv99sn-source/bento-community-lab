"""Behavior on actual patched branches plus export-boundary regressions.

Uses the same bounded fixtures as the connected tests, not a whole-device boot.
"""
import struct
import tempfile
import unittest
from pathlib import Path
import sys
import os
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_integration import Integrated, PATCHED, WRITES, B, STATE
from test_connected import PRODUCER
from export_experimental import verify, export

STOCK_MAIN = Path(os.environ.get('BENTO_STOCK_IMAGE',
    'handoff/Bento_Work_Handoff_2026-10-16/01_BENTO_FIRMWARE/1.6.1/bento1.bin'))
STOCK_CONTROLLER = Path(os.environ.get('BENTO_STOCK_CONTROLLER',str(STOCK_MAIN.with_name('bento2.bin'))))
CONTROLLER = STOCK_CONTROLLER.read_bytes()


def device():
    m = Integrated()
    m.startup()
    m.initialize_runtime_fixture()
    return m


class Tests(unittest.TestCase):
    def test_normal_preheld_and_unmapped_notes_on_real_branches(self):
        m=device()
        m.packet(0,[900]+[0]*15)
        self.assertEqual(m.events(),[(0xac,0,900),(0xae,0,900)])
        m.packet(0x2000,[1100]+[0]*15)
        self.assertEqual(m.events(),[(0xae,0,1100)])
        m.packet(0x2000)
        self.assertEqual(m.events(),[(0xad,0,0),(0xae,0,0)])
        m.packet(0x2000,[0]*8+[900]+[0]*7)
        self.assertEqual(m.events(),[(0xac,8,900),(0xae,8,900)])
        m.drain()
        self.assertEqual(m.selections,[])

    def test_both_release_orders_on_real_branches(self):
        for modifier_first in (True,False):
            m=device()
            m.packet(0x2000,[900]+[0]*15)
            m.drain()
            mask=0 if modifier_first else 0x2000
            m.packet(mask,[1400]+[0]*15)
            self.assertEqual(m.events(),[])
            m.packet(mask)
            self.assertEqual(m.events(),[])
            m.packet()
            m.drain()
            self.assertEqual(m.selections,[0])
            self.assertEqual(m.readword(STATE+4)&65535,0)
            m.packet(0,[800]+[0]*15)
            self.assertEqual(m.events(),[(0xac,0,800),(0xae,0,800)])

    def test_queue_full_on_real_branches(self):
        m=device();m.packet(0x2000);m.drain()
        m.word(PRODUCER+0x21a0,225);m.word(PRODUCER+0x2180,1)
        before=bytes(m.u.mem_read(PRODUCER+0x980,256*24))
        m.packet(0x2000,[900]+[0]*15)
        self.assertEqual(m.events(),[])
        self.assertEqual(m.readword(PRODUCER+0x21a0),225)
        self.assertEqual(bytes(m.u.mem_read(PRODUCER+0x980,256*24)),before)
        self.assertEqual(m.readword(STATE+8),1)
        m.packet(0x2000)
        self.assertEqual(m.events(),[])

    def test_counter_wrap_and_multiple_pads_on_real_branches(self):
        m=device();m.packet(0x2000);m.drain()
        m.word(PRODUCER+0x21a0,0xfffffffe);m.word(PRODUCER+0x2180,0xfffffffe)
        m.packet(0x2000,[900,1000,1100]+[0]*13)
        self.assertEqual(m.events(),[])
        m.drain()
        self.assertEqual(m.selections,[0,1,2])
        self.assertEqual(m.selected,2)
        self.assertEqual(m.readword(PRODUCER+0x21a0),1)
        m.packet()
        self.assertEqual(m.events(),[])

    def test_malformed_tag_on_real_consumer_branch(self):
        m=device()
        m.enqueue_test_record(struct.pack('<6I',254,0,0xfffffffe,0,0,0x31525442))
        m.drain()
        self.assertEqual(m.selections,[])

    def test_export_exact_inputs_reversible_and_aligned(self):
        report=verify(B,CONTROLLER,PATCHED,WRITES)
        self.assertEqual(report['appended_bytes'],144)
        self.assertEqual(len(PATCHED)%4,0)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'test'
            export(STOCK_MAIN,STOCK_CONTROLLER,out)
            self.assertEqual((out/'01_TEST_FIRMWARE/bento1.bin').read_bytes(),PATCHED)
            self.assertEqual((out/'01_TEST_FIRMWARE/bento2.bin').read_bytes(),CONTROLLER)
            self.assertEqual((out/'02_ORIGINAL_1.6.1_RESTORE/bento1.bin').read_bytes(),B)
            with self.assertRaises(FileExistsError):
                export(STOCK_MAIN,STOCK_CONTROLLER,out)

    def test_reject_unlisted_change_or_wrong_controller(self):
        bad=bytearray(PATCHED);bad[0]^=1
        with self.assertRaises(ValueError):verify(B,CONTROLLER,bytes(bad),WRITES)
        bad2=bytearray(CONTROLLER);bad2[0]^=1
        with self.assertRaises(ValueError):verify(B,bytes(bad2),PATCHED,WRITES)

    def test_only_measured_tracks_button_claims_top_row(self):
        m=device()
        for button in range(16):
            mask=1<<(15-button)
            m.selections=[]
            m.packet(mask,[1000]+[0]*15)
            expected=[] if button==2 else [(0xac,0,1000),(0xae,0,1000)]
            self.assertEqual(m.events(),expected,button)
            m.drain()
            self.assertEqual(m.selections,[0] if button==2 else [],button)
            m.packet();m.drain()


if __name__=='__main__':unittest.main(verbosity=2)
