"""Export the explicitly authorized private hardware experiment, NOT a qualified release.

Exact stock inputs only. No device access or flashing. No bootloader image,
flash programming routine, vector-table edit or controller modification is added.
Installer erase/program behavior is not established by this host-side audit.
"""
import argparse
import hashlib
import json
from pathlib import Path

from extension import MODULE, load_profile
from integration_candidate import candidate, restore, BASE, INPUT, CONSUMER, STARTUP, VERSION_ADDRESS

CONTROLLER_SHA256 = '8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(stock, controller, image, writes):
    load_profile(stock)
    if sha(controller) != CONTROLLER_SHA256:
        raise ValueError('Controller firmware is not the exact original 1.6.1 file')
    if len(image) % 4 or not 0 < len(image)-len(stock) <= 512:
        raise ValueError('Unexpected output length or alignment')
    if restore(image, writes) != stock:
        raise ValueError('Candidate does not restore byte-for-byte to original')
    allowed = {
        INPUT: (0x200, True),
        STARTUP: (0x100, True),
        BASE+len(stock): (512, False),
        0x0808d1fe: (4, False), 0x0813f98c: (4, False),
        0x080404b6: (4, False), 0x08040588: (4, False),
        0x080a3bdc: (4, False), 0x080a3e94: (4, False),
        VERSION_ADDRESS: (6, False),
    }
    if len(writes) != len(allowed) or {w['address'] for w in writes} != set(allowed):
        raise ValueError('Unexpected write locations')
    reconstructed = bytearray(stock)
    covered = set()
    for w in sorted(writes, key=lambda w:w['address']):
        address, size = w['address'], w['size']
        limit, zero_gap = allowed[address]
        if not 0 < size <= limit or not BASE <= address < address+size <= 0x08200000:
            raise ValueError('Write outside reviewed application bounds')
        off = address-BASE
        original, replacement = bytes.fromhex(w['original_hex']), bytes.fromhex(w['replacement_hex'])
        if stock[off:off+size] != original or len(replacement) != size:
            raise ValueError('Write manifest mismatch')
        if zero_gap and original != bytes(size):
            raise ValueError('Candidate flash gap is not zero-filled')
        if covered.intersection(range(off, off+size)):
            raise ValueError('Overlapping writes')
        covered.update(range(off, off+size))
        reconstructed[off:off+size] = replacement
    if bytes(reconstructed) != image:
        raise ValueError('Changes exist outside the manifest')
    for vector in (0x08040000, 0x080e0000, 0x08100000):
        off = vector-BASE
        if image[off:off+0x400] != stock[off:off+0x400]:
            raise ValueError('Vector table or adjacent startup header changed')
    if image[0xa0000:0xc0000] != stock[0xa0000:0xc0000]:
        raise ValueError('Disk-mode image changed')
    return {
        'status': 'experimental-hardware-test-not-production-qualified',
        'module_version': json.loads((MODULE/'module.json').read_text())['version'],
        'original_bento1_sha256': sha(stock),
        'experimental_bento1_sha256': sha(image),
        'unchanged_bento2_sha256': sha(controller),
        'original_bytes': len(stock), 'experimental_bytes': len(image),
        'appended_bytes': len(image)-len(stock),
        'changed_bytes_within_original': sum(a != b for a,b in zip(stock,image)),
        'file_length_multiple_of_four': True,
        'original_vectors_unchanged': True,
        'original_disk_mode_image_unchanged': True,
        'controller_file_unchanged': True,
        'all_changes_accounted_for': True,
        'byte_exact_restore_verified': True,
        'address_mapping': {'base': hex(BASE), 'consumer': hex(CONSUMER),
                            'exclusive_image_end': hex(BASE+len(image))},
        'bootloader_image_included': False,
        'bootloader_protected_ranges_verified': False,
        'installer_erase_ranges_verified': False,
        'appended_image_acceptance_verified': False,
        'physical_row_groups_verified': True,
        'physical_all_columns_individually_verified': False,
        'physical_test_mapping': 'Measured top row group 0..7 selects tracks 1..8; bottom row group 8..15 passes through. First two columns measured; remaining column order inferred pending test.',
        'tracks_logical_switch_id': 2,
        'tracks_raw_mask': '0x2000',
        'running_version_label': '1.6T1',
        'hardware_test_passed': False,
        'writes': writes,
    }


def export(stock_path, controller_path, output_path):
    stock = Path(stock_path).read_bytes()
    controller = Path(controller_path).read_bytes()
    image, writes = candidate(stock)
    report = verify(stock, controller, image, writes)
    out = Path(output_path)
    # Refuse an existing directory, including any original input directory.
    out.mkdir(parents=True, exist_ok=False)
    for folder, main in [('01_TEST_FIRMWARE',image), ('02_ORIGINAL_1.6.1_RESTORE',stock)]:
        target = out/folder
        target.mkdir()
        (target/'bento1.bin').write_bytes(main)
        (target/'bento2.bin').write_bytes(controller)
    (out/'BUILD_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stock_bento1')
    parser.add_argument('stock_bento2')
    parser.add_argument('new_output_directory')
    args = parser.parse_args()
    report = export(args.stock_bento1,args.stock_bento2,args.new_output_directory)
    print(json.dumps({k:v for k,v in report.items() if k != 'writes'},indent=2))
