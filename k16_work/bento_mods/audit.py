"""Read-only compatibility audit. Does not create or modify firmware."""
import argparse
import hashlib
import json
from pathlib import Path
from extension import ROOT, MODULE, load_profile, assemble


def audit(path):
    image = Path(path).read_bytes()
    profile = load_profile(image)
    module = json.loads((MODULE/'module.json').read_text())
    compiled = assemble(image)
    return {
        'schema': 1,
        'module': module['id'],
        'module_version': module['version'],
        'firmware_version': profile['firmware_version'],
        'stock_sha256': profile['sha256'],
        'status': 'offline-emulator-only',
        'pad_numbering': module['pad_labels'],
        'stock_hooks': profile['hooks'],
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(MODULE.iterdir()) if p.is_file()},
        'assembled_emulator_blocks': {name: {'emulator_address': hex(x['address']),
                                  'bytes': len(x['code']),
                                  'sha256': hashlib.sha256(x['code']).hexdigest()}
                                  for name,x in compiled.items()},
        'device_allocations': {'code': None, 'state': None},
        'installation_authorized_by_this_audit': False,
        'firmware_bytes_written': 0,
        'porting_rule': 'New firmware requires a new reviewed profile; unknown hashes are rejected',
        'removal_rule': module['removal'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stock_image')
    args = parser.parse_args()
    print(json.dumps(audit(args.stock_image),indent=2))
