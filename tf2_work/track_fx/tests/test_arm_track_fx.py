"""Execute the fully linked Thumb-2/M7 image with its freestanding math.
This is isolated DSP execution, not a Bento mixer or peripheral simulation.
"""
import struct,unittest,sys
from pathlib import Path
import numpy as np
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_track_fx import Settings,Bank,tone,lib
ROOT=Path(__file__).resolve().parents[1]
def elf():
    b=(ROOT/'track_fx_test.elf').read_bytes();off=struct.unpack_from('<I',b,32)[0];stride,n=struct.unpack_from('<HH',b,46)
    sections=[struct.unpack_from('<10I',b,off+i*stride) for i in range(n)];symbols={};code=[];undefined=[]
    for s in sections:
        if s[2]&2:code.append((s[3],b[s[4]:s[4]+s[5]]))
        if s[1]!=2:continue
        st=sections[s[6]];names=b[st[4]:st[4]+st[5]]
        for i in range(0,s[5],s[9]):
            name,value,size,info,_,index=struct.unpack_from('<IIIBBH',b,s[4]+i)
            name=names[name:].split(b'\0')[0].decode()
            if name and index==0:undefined.append(name)
            if info&15==2:symbols[name]=value&~1
    return code,symbols,undefined
class Arm:
    def __init__(self):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7);self.u.mem_map(0x1000000,0x100000);self.u.mem_map(0x20000000,0x40000)
        self.code,self.symbols,self.undefined=elf()
        for a,b in self.code:self.u.mem_write(a,b)
        self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
        self.p=0x20004000;self.stop=0x10ff000;self.instructions=0
        self.call('tf_init',self.p,float0=48000)
    def call(self,name,*args,float0=None):
        sp=0x2003f000
        for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(r,v)
        for i,v in enumerate(args[4:]):self.u.mem_write(sp+i*4,struct.pack('<I',v))
        if float0 is not None:self.u.reg_write(UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',float0))[0])
        self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,self.stop|1)
        self.u.emu_start(self.symbols[name]|1,self.stop,count=10000000)
        assert self.u.reg_read(UC_ARM_REG_PC)==self.stop,'emulation did not return'
        return self.u.reg_read(UC_ARM_REG_R0)
    def config(self,track=0,**kwargs):
        kwargs.setdefault("auto_makeup",0)
        s=Settings();lib.tf_defaults(__import__('ctypes').byref(s))
        for k,v in kwargs.items():setattr(s,k,v)
        self.u.mem_write(0x20002000,bytes(s));assert self.call('tf_configure',self.p,track,0x20002000)
    def process(self,l,r=None,track=0):
        l=np.array(l,dtype='float32');r=None if r is None else np.array(r,dtype='float32');out=[];outr=[]
        for i in range(0,len(l),64):
            a=l[i:i+64];n=len(a);self.u.mem_write(0x20010000,a.tobytes())
            if r is not None:self.u.mem_write(0x20011000,r[i:i+n].tobytes())
            assert self.call('tf_process',self.p,track,0x20010000,0 if r is None else 0x20011000,n)
            out.extend(struct.unpack('<%df'%n,self.u.mem_read(0x20010000,n*4)))
            if r is not None:outr.extend(struct.unpack('<%df'%n,self.u.mem_read(0x20011000,n*4)))
        return np.array(out) if r is None else (np.array(out),np.array(outr))
class Tests(unittest.TestCase):
    def test_fully_linked_image_has_no_unresolved_or_software_float_helpers(self):
        a=Arm();self.assertEqual(a.undefined,[])
        for forbidden in ['__aeabi_fmul','__aeabi_fadd','__aeabi_dmul','__aeabi_dadd','malloc','free','_Znwj']:
            self.assertNotIn(forbidden,a.symbols)
        self.assertLess(sum(len(b) for _,b in a.code),20000)
        self.assertEqual(a.call('tf_bank_bytes'),lib.tf_bank_bytes())
    def test_m7_default_bypass_and_stereo_link(self):
        a=Arm();x=tone(220,.03,amp=.7)
        l,r=a.process(x,-x*.25);self.assertEqual(l.astype('float32').tobytes(),x.tobytes())
        a.config(comp_enabled=1,threshold_db=-30,ratio=10,attack_ms=.1)
        l,r=a.process(x,-x*.25);self.assertLess(float(np.max(np.abs(l+r*4))),1e-6)
        self.assertLess(float(np.max(np.abs(l[-200:]))),.3)
    def test_m7_matches_host_audio_with_real_eq_and_compression(self):
        s=dict(eq_enabled=1,comp_enabled=1,low_db=6,mid_db=-8,mid_q=2,high_db=4,threshold_db=-24,ratio=5,attack_ms=1,makeup_db=2)
        a=Arm();a.config(**s);b=Bank();b.config(**s)
        x=(tone(87,.08,amp=.4)+tone(1000,.08,amp=.2)+tone(6500,.08,amp=.1)).astype('float32')
        actual=a.process(x);expected=b.process(x)
        # Different FPU contraction and freestanding math perturb recursive
        # filter state slightly; bound peak AND relative RMS error independently.
        error=actual-expected
        self.assertLess(float(np.max(np.abs(error))),.0002)
        self.assertLess(float(np.sqrt(np.mean(error**2))/np.sqrt(np.mean(expected**2))),.0005)
    def test_m7_eight_tracks_and_nonfinite_recovery(self):
        a=Arm();x=tone(1000,.01)
        for track in range(8):
            a.config(track,eq_enabled=1,mid_db=track-4,comp_enabled=1)
            y=a.process(x,track=track);self.assertTrue(np.all(np.isfinite(y)))
        x[0]=float('nan');x[1]=float('inf');y=a.process(x);self.assertTrue(np.all(np.isfinite(y)));self.assertEqual(y[0],0);self.assertEqual(y[1],0)
    def test_m7_soft_clip_is_bounded_and_matches_host(self):
        a=Arm();a.config(clip_enabled=1,clip_ceiling_db=-6);b=Bank();b.config(clip_enabled=1,clip_ceiling_db=-6)
        a.process(np.zeros(14000));b.process(np.zeros(14000))
        x=np.linspace(-8,8,1024,dtype='float32');actual=a.process(x);expected=b.process(x)
        self.assertLessEqual(float(np.max(np.abs(actual))),10**(-6/20)+1e-6)
        self.assertLess(float(np.max(np.abs(actual-expected))),2e-6)
if __name__=='__main__':unittest.main(verbosity=2)
