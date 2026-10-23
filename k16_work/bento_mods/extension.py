"""Version-checked assembly shared by emulation and experimental export."""
from pathlib import Path
import hashlib
import json
import re
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / 'modules' / 'tracks-pad-select'


def load_profile(image, path=None):
    p = json.loads((Path(path) if path else ROOT/'profiles'/'bento-1.6.1.json').read_text())
    if hashlib.sha256(image).hexdigest() != p['sha256']:
        raise ValueError('Unsupported or modified firmware: exact original SHA-256 required')
    for hook in p['hooks'].values():
        offset = int(hook['address'], 0) - p['base']
        expected = bytes.fromhex(hook['original'])
        if image[offset:offset+len(expected)] != expected:
            raise ValueError('Hook byte mismatch')
    return p


def assemble(image, *, state=0x24062000, input_code=0x24060000, consumer_code=0x24061000):
    """Defaults are emulator RAM; the integration builder supplies flash/state addresses."""
    p = load_profile(image)
    module = json.loads((MODULE/'module.json').read_text())
    symbols = dict(p['symbols'], STATE=hex(state), STATE_MAGIC=module['state_magic'],
                   EVENT_MAGIC=module['experimental_message']['magic'],
                   EVENT_TAIL=module['experimental_message']['tail'])
    result = {}
    for name, address in [('input', input_code), ('consumer', consumer_code)]:
        source = (MODULE/(name+'.s')).read_text()
        source = '\n'.join(line.split('//')[0] for line in source.splitlines())
        for key, value in symbols.items():
            source = source.replace('@'+key+'@', value)
        if re.search(r'@[A-Z_]+@', source):
            raise ValueError('Unresolved assembly symbol')
        encoded, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(source, address)
        marker = (module['source_marker']+':'+name+'\0').encode('ascii')
        result[name] = {'address': address, 'code': bytes(encoded)+marker}
    return result


def require_installable(profile):
    """Production-qualification gate, distinct from explicit experimental export."""
    required = ['physical_pad_map', 'code_storage', 'state_storage', 'bootloader_protected_ranges',
                'installer_erase_ranges_verified', 'installable']
    missing = [key for key in required if not profile.get(key)]
    if missing:
        raise ValueError('Not installable; unverified: '+', '.join(missing))
    raise ValueError('Production release is not implemented; experimental export is separate')
