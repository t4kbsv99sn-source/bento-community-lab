"""Connected assembled extension + original receiver/queue/selection code.

Artificial RAM placement and debugger-style hook redirection only. Neither
stock image bytes nor hardware are changed. See README for dependency stubs.
"""
from pathlib import Path
import ctypes
import json
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT/'bento_mods'))
from receiver_fixture import Receiver, B, OBJ, ENGINE, HOOK
from extension import assemble, load_profile, require_installable, MODULE
from unicorn import UC_PROT_ALL
from unicorn.arm_const import *

STATE, MODEL, TABLE, UI_SP = 0x24062000, 0x30010000, 0x30020000, 0x24070000
PRODUCER, CONSUMER = 0x10040000, 0x30040000
COMPILED = assemble(B)


class Connected(Receiver):
    def __init__(self):
        super().__init__(False)
        self.u.mem_map(0x30000000, 0x40000)
        self.backing = ctypes.create_string_buffer(0x8000)
        for a in [PRODUCER, CONSUMER]:
            self.u.mem_map_ptr(a, 0x8000, UC_PROT_ALL, ctypes.addressof(self.backing))
        self.word(0x2401bd3c, PRODUCER)
        self.word(0x3000f650, CONSUMER)
        for segment in COMPILED.values():
            self.u.mem_write(segment['address'], segment['code'])
        self.word(STATE, 0x31534d42)
        self.u.mem_write(STATE+12, b'\x01')
        # Emulator fixture only: logical 0..7 stand for the NEW top-row labels
        # 1..8. Real physical-to-logical calibration is intentionally unresolved.
        self.u.mem_write(STATE+16, bytes(range(8))+bytes([255]*8))
        self.word(MODEL+12, TABLE)
        self.word(MODEL+16, 1)
        self.u.mem_write(TABLE, struct.pack('<IHBB', 99, 0x131, 1, 0))
        self.ui_messages = []
        self.engine_commands = []
        self.selections = []

    def callback(self, u, a, size, userdata):
        if a == HOOK:
            u.reg_write(UC_ARM_REG_PC, COMPILED['input']['address'] | 1)
            return
        if a == 0x0813f98c:
            u.reg_write(UC_ARM_REG_PC, COMPILED['consumer']['address'] | 1)
            return
        if a == 0x0813bc3c:
            self.selections.append(u.reg_read(UC_ARM_REG_R1))
            return  # Execute the ORIGINAL selection operation and property setter.
        if a in [0x0810b5c8, 0x0812d78a, 0x08139138, 0x08142afc, 0x08133cfc]:
            r = [u.reg_read(x) for x in [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]]
            if a == 0x0810b5c8:
                self.engine_commands.append(tuple(r))
            if a == 0x08142afc:
                self.ui_messages.append(bytes(u.mem_read(r[1], 20)))
            if a == 0x08133cfc:
                self.word(r[1], 7)  # Recording-context lookup dependency.
            u.reg_write(UC_ARM_REG_R0, 0)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            return
        super().callback(u, a, size, userdata)

    def drain(self):
        n = 0
        while self.readword(CONSUMER+0x21a0) != self.readword(CONSUMER+0x2180):
            if n >= 256:
                raise AssertionError('Queue cannot be drained safely')
            n += 1
            self.u.reg_write(UC_ARM_REG_R4, MODEL)
            self.u.reg_write(UC_ARM_REG_R10, 0)
            self.u.reg_write(UC_ARM_REG_SP, UI_SP)
            self.u.reg_write(UC_ARM_REG_LR, CONSUMER)
            self.u.emu_start(0x0813f931, 0x0813f2fc, count=50000)
            assert self.u.reg_read(UC_ARM_REG_PC) == 0x0813f2fc

    @property
    def selected(self):
        return self.readword(TABLE)

    def enqueue_test_record(self, record):
        i = self.readword(PRODUCER+0x21a0)
        self.u.mem_write(PRODUCER+0x980+24*(i&255), record)
        self.word(PRODUCER+0x21a0, i+1)


class Tests(unittest.TestCase):
    def test_top_row_pad1_to8_select_tracks1_to8(self):
        for index in range(8):
            with self.subTest(label=index+1):
                m = Connected()
                pads = [0]*16
                pads[index] = 1000
                m.packet(0x2000, pads)
                self.assertEqual(m.events(), [])
                m.drain()
                self.assertEqual(m.selected, index)
                self.assertEqual(m.selections, [index])
                self.assertIn((CONSUMER, 0xfffffffe, 0xb6, index), m.engine_commands)
                self.assertEqual(m.readword(STATE+4) & 65535, 1<<index)

    def test_both_release_orders_no_leaked_pressure(self):
        for modifier_first in [False, True]:
            m = Connected()
            m.packet(0x2000, [1000]+[0]*15)
            m.drain()
            m.packet(0x2000, [1500]+[0]*15)
            self.assertEqual(m.events(), [])
            if modifier_first:
                m.packet(0, [1500]+[0]*15)
                self.assertEqual(m.events(), [])
            m.packet(0 if modifier_first else 0x2000)
            self.assertEqual(m.events(), [])
            m.drain()
            self.assertEqual(m.selections, [0])
            self.assertEqual(m.readword(STATE+4)&65535, 0)

    def test_ordinary_pad_notes_and_preheld_releases(self):
        m = Connected()
        m.packet(0, [1000]+[0]*15)
        self.assertEqual(m.events(), [(0xac,0,1000),(0xae,0,1000)])
        m.packet(0x2000, [1200]+[0]*15)
        self.assertEqual(m.events(), [(0xae,0,1200)])
        m.packet(0x2000)
        self.assertEqual(m.events(), [(0xad,0,0),(0xae,0,0)])
        m.drain()
        self.assertEqual(m.selections, [])

    def test_bottom_row_labels9_to16_play_normally(self):
        for index in range(8,16):
            m = Connected()
            pads = [0]*16
            pads[index] = 900
            m.packet(0x2000,pads)
            self.assertEqual(m.events(), [(0xac,index,900),(0xae,index,900)])
            m.drain()
            self.assertEqual(m.selections, [])

    def test_disabled_module_passes_new_notes_and_finishes_owned_release(self):
        m = Connected()
        m.packet(0x2000,[1000]+[0]*15)
        m.u.mem_write(STATE+12,b'\0')
        m.packet(0,[1200,800]+[0]*14)
        self.assertEqual(m.events(),[(0xac,1,800),(0xae,1,800)])
        m.packet()
        self.assertEqual(m.events(),[(0xad,1,0),(0xae,1,0)])
        self.assertEqual(m.readword(STATE+4)&65535,0)

    def test_full_queue_does_not_overwrite_or_play_note(self):
        m = Connected()
        m.packet(0x2000)  # Stock TRACKS event already emitted.
        m.drain()
        m.word(PRODUCER+0x21a0,225)
        m.word(PRODUCER+0x2180,1)  # Admission threshold 224, including reserved slots.
        before = bytes(m.u.mem_read(PRODUCER+0x980,256*24))
        m.packet(0x2000,[1000]+[0]*15)
        self.assertEqual(m.events(),[])
        self.assertEqual(m.readword(PRODUCER+0x21a0),225)
        self.assertEqual(bytes(m.u.mem_read(PRODUCER+0x980,256*24)),before)
        self.assertEqual(m.readword(STATE+8),1)
        m.packet(0x2000)
        self.assertEqual(m.events(),[])

    def test_recording_branch_uses_existing_selection_notifications(self):
        m = Connected()
        m.u.mem_write(MODEL+0x9ca0,b'\x01')
        m.packet(0x2000,[0,0,1000]+[0]*13)
        m.drain()
        self.assertEqual(m.selected,2)
        self.assertEqual([(r[2],r[3]) for r in m.engine_commands],[(0xa5,0),(0xb6,2),(0xa5,1)])

    def test_tag_validation_ignores_unrelated_or_malformed_messages(self):
        for code,magic,tail,index,context in [(254,0,0x31525442,0,-2),
                (254,0x314d5442,0,0,-2),(253,0x314d5442,0x31525442,0,-2),
                (254,0x314d5442,0x31525442,8,-2),(254,0x314d5442,0x31525442,0,0)]:
            m = Connected()
            r = struct.pack('<6I',code,magic,context&0xffffffff,index,0,tail)
            m.enqueue_test_record(r)
            m.drain()
            self.assertEqual(m.selections,[])

    def test_same_packet_modifier_release_does_not_claim_new_note(self):
        m = Connected()
        m.packet(0x2000)
        m.drain()
        m.packet(0,[1000]+[0]*15)
        self.assertEqual(m.events(),[(0xac,0,1000),(0xae,0,1000)])
        m.drain()
        self.assertEqual(m.selections,[])

    def test_mapping_is_configurable_without_changing_hook_source(self):
        m = Connected()
        m.u.mem_write(STATE+16,bytes([255]*8)+bytes(range(8)))
        m.packet(0x2000,[0]*8+[1000]+[0]*7)
        m.drain()
        self.assertEqual(m.selected,0)

    def test_original_image_stays_unmodified(self):
        m = Connected()
        m.packet(0x2000,[1000]+[0]*15)
        m.drain()
        self.assertEqual(bytes(m.u.mem_read(0x08040000,len(B))),B)

    def test_version_guard_and_installation_gate(self):
        bad = bytearray(B)
        bad[100] ^= 1
        with self.assertRaises(ValueError): load_profile(bad)
        with self.assertRaises(ValueError): require_installable(load_profile(B))
        module = json.loads((MODULE/'module.json').read_text())
        self.assertEqual(module['pad_labels']['top'],list(range(1,9)))
        self.assertEqual(module['pad_labels']['bottom'],list(range(9,17)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
