"""Guarded native node allocation/deep-copy extension, not a firmware release."""
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
BASE=0x08040000
PREFIX=0x820
LANE_BYTES=2096
NODE_BYTES=PREFIX+16+4*LANE_BYTES
def patches(image):
    k=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
    result=[]
    for address,old,new,reason in [
        (0x0812e8c6,'movw r1,#0x814',f'movw r1,#{NODE_BYTES}','type-5 allocation'),
        (0x0812e3b6,'movw r10,#0x814',f'movw r10,#{NODE_BYTES}','type-5 deep copy including native Undo'),
        (0x0812e8e6,'mov.w r2,#0x800',f'movw r2,#{NODE_BYTES-10}','zero entire enlarged payload'),
    ]:
        original=bytes(k.asm(old,address)[0]);replacement=bytes(k.asm(new,address)[0])
        assert len(original)==len(replacement)==4
        assert image[address-BASE:address-BASE+4]==original,hex(address)
        result.append((address,original,replacement,reason))
    return result
