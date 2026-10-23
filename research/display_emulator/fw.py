import struct, capstone, sys
BASE=0x08040000
class FW:
    def __init__(s,path):
        s.b=open(path,'rb').read()
        s.md=capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB|capstone.CS_MODE_MCLASS); s.md.detail=False
    def u32(s,a): return struct.unpack_from('<I',s.b,a-BASE)[0]
    def u16(s,a): return struct.unpack_from('<H',s.b,a-BASE)[0]
    def dis(s,a,n=40):
        out=[]
        for i in s.md.disasm(s.b[a-BASE:a-BASE+n*4],a):
            out.append(f"{i.address:08X}: {i.mnemonic:8s} {i.op_str}")
            if len(out)>=n: break
        return "\n".join(out)
    def callers(s,target):
        # scan for Thumb BL/B.W to target at every halfword
        res=[]
        b=s.b
        for off in range(0,len(b)-4,2):
            h1,h2=struct.unpack_from('<HH',b,off)
            if (h1&0xF800)==0xF000 and (h2&0xD000) in (0xD000,0x9000,0xC000):
                S=(h1>>10)&1; imm10=h1&0x3FF; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7FF
                I1=1-(J1^S); I2=1-(J2^S)
                imm=(S<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
                if S: imm-=1<<25
                pc=BASE+off+4
                t=pc+imm
                if (h2&0xD000)==0xC000: t&=~3  # BLX
                if t==target: res.append((BASE+off,{0xD000:'bl',0x9000:'b.w',0xC000:'blx'}[h2&0xD000]))
        return res
    def refs(s,val):
        v=struct.pack('<I',val); out=[]; i=s.b.find(v)
        while i>=0: out.append(BASE+i); i=s.b.find(v,i+1)
        return out
