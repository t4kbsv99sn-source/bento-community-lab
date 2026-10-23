"""Construct a candidate in memory; export_experimental.py owns file export.

This does not establish loader erase bounds, physical input mapping, complete
flash-gap availability or real-device behavior. Production qualification stays
separate from the explicitly experimental hardware-test package.
"""
from pathlib import Path
import struct
import json
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from extension import ROOT, MODULE, load_profile, assemble

BASE = 0x08040000
HEAP_START, OLD_HEAP_END, STATE = 0x2401edc0, 0x24048da0, 0x24048d80
INPUT, CONSUMER, STARTUP = 0x080d0000, 0x081b3f40, 0x080d0300
VERSION_ADDRESS = 0x0818bad4


def candidate(stock):
    load_profile(stock)
    image = bytearray(stock)
    writes = []

    def write(address, new, expected, reason):
        offset = address-BASE
        append = not expected and offset == len(image)
        if offset < 0 or address+len(new) > 0x08200000:
            raise ValueError('Write outside candidate application mapping')
        if not append and (offset+len(new)>len(stock) or len(new)!=len(expected)):
            raise ValueError('Unexpected non-append size change')
        if bytes(image[offset:offset+len(new)]) != expected:
            raise ValueError('Unexpected original bytes at '+hex(address))
        if any(address < w['address']+w['size'] and w['address'] < address+len(new) for w in writes):
            raise ValueError('Overlapping writes')
        image[offset:offset+len(new)] = new
        writes.append({'address':address, 'size':len(new), 'original_hex':expected.hex(),
                       'replacement_hex':new.hex(), 'reason':reason})

    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    blocks = assemble(stock, state=STATE, input_code=INPUT, consumer_code=CONSUMER)
    source = (MODULE/'startup.s').read_text()
    source = '\n'.join(line.split('//')[0] for line in source.splitlines())
    encoded, _ = ks.asm(source, STARTUP)
    marker = json.loads((MODULE/'module.json').read_text())['source_marker']
    blocks['startup'] = {'address':STARTUP,'code':bytes(encoded)+(marker+':startup\0').encode('ascii')}
    for name, block in blocks.items():
        if name=='consumer':
            gap=CONSUMER-(BASE+len(stock))
            if not 0<=gap<=15:raise ValueError('Unexpected consumer alignment gap')
            payload = bytes(gap)+block['code']
            # Preserve the stock file's four-byte length alignment. This is a
            # conservative packaging choice, not a verified Bento loader rule.
            payload += b'\xff' * (-(len(stock)+len(payload)) % 4)
            write(BASE+len(stock),payload,b'',
                  'Append UI consumer inside its executable MPU flash region; loader acceptance unverified')
        else:
            write(block['address'],block['code'],bytes(len(block['code'])),name+' code in candidate zero-filled flash gap')
    for a,target,original,name in [(0x0808d1fe,INPUT,'9c42f6d0','pad input branch'),
                                 (0x0813f98c,CONSUMER,'a5f11103','consumer branch'),
                                 (0x080404b6,STARTUP,'24482449','startup branch')]:
        branch, _ = ks.asm('b.w '+hex(target),a)
        if len(branch) != 4:
            raise ValueError('Unexpected branch length')
        write(a,bytes(branch),bytes.fromhex(original),name)
    for a,reason in [(0x08040588,'startup heap size'),(0x080a3bdc,'free-pointer upper bound'),
                     (0x080a3e94,'allocator heap-span check')]:
        write(a,struct.pack('<I',STATE),struct.pack('<I',OLD_HEAP_END),reason)
    write(VERSION_ADDRESS,b'1.6T1\0',b'1.6.1\0','Visible calibrated shortcut test identifier')
    return bytes(image),writes


def restore(candidate_bytes, writes):
    """Strict in-memory restoration; reject drift before changing any bytes."""
    for w in writes:
        off=w['address']-BASE
        if candidate_bytes[off:off+w['size']] != bytes.fromhex(w['replacement_hex']):
            raise ValueError('Modified candidate does not match its write manifest')
    image=bytearray(candidate_bytes)
    for w in sorted(writes,key=lambda w:w['address'],reverse=True):
        off=w['address']-BASE
        image[off:off+w['size']]=bytes.fromhex(w['original_hex'])
    load_profile(bytes(image))
    return bytes(image)
