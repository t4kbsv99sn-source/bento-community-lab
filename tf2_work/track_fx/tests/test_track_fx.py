"""Measure compiled DSP through its public C ABI, independently of implementation."""
import ctypes as C
import math,random,struct,unittest,zlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
lib=C.CDLL(str(ROOT/'libtrack_fx.so'))
class Settings(C.Structure):
    _fields_=[('eq_enabled',C.c_uint32),('comp_enabled',C.c_uint32),('clip_enabled',C.c_uint32),('auto_makeup',C.c_uint32)]+[(n,C.c_float) for n in 'low_hz low_db mid_hz mid_db mid_q high_hz high_db threshold_db ratio attack_ms release_ms makeup_db comp_mix clip_ceiling_db'.split()]
class Meters(C.Structure):
    _fields_=[(n,C.c_float) for n in ['input_peak','output_peak','reduction_db']]+[('faults',C.c_uint32)]
P=C.c_void_p;U=C.c_uint;N=C.c_size_t
for name,args in {'tf_init':[P,C.c_float],'tf_configure':[P,U,C.POINTER(Settings)],'tf_get_settings':[P,U,C.POINTER(Settings)],'tf_process':[P,U,P,P,N],'tf_meters':[P,U,C.POINTER(Meters)],'tf_reset_track':[P,U],'tf_save':[P,P,N],'tf_load':[P,P,N]}.items():
    getattr(lib,name).argtypes=args;getattr(lib,name).restype=C.c_int
for n in ['tf_bank_bytes','tf_bank_alignment','tf_record_bytes']:getattr(lib,n).restype=N
lib.tf_defaults.argtypes=[C.POINTER(Settings)]
def tone(hz,seconds=1,amp=.1,rate=48000):return (amp*np.sin(np.arange(int(rate*seconds))*2*np.pi*hz/rate)).astype('float32')
def rms(x):return float(np.sqrt(np.mean(x.astype('float64')**2)))
class Bank:
    def __init__(self,rate=48000):
        self.raw=C.create_string_buffer(lib.tf_bank_bytes()+64);self.p=(C.addressof(self.raw)+31)&~31
        assert lib.tf_init(self.p,rate);self.rate=rate
    def settings(self,track=0):
        s=Settings();assert lib.tf_get_settings(self.p,track,C.byref(s));return s
    def config(self,track=0,**kwargs):
        s=self.settings(track)
        kwargs.setdefault("auto_makeup",0)
        for k,v in kwargs.items():setattr(s,k,v)
        assert lib.tf_configure(self.p,track,C.byref(s));return s
    def process(self,l,r=None,track=0,block=64):
        l=np.array(l,dtype='float32',copy=True);r=None if r is None else np.array(r,dtype='float32',copy=True)
        for i in range(0,len(l),block):
            assert lib.tf_process(self.p,track,l.ctypes.data+i*4,None if r is None else r.ctypes.data+i*4,min(block,len(l)-i))
        return l if r is None else (l,r)
    def meters(self,track=0):m=Meters();assert lib.tf_meters(self.p,track,C.byref(m));return m
    def save(self):
        r=C.create_string_buffer(lib.tf_record_bytes());assert lib.tf_save(self.p,r,len(r));return r.raw
    def load(self,data):r=C.create_string_buffer(bytes(data));return lib.tf_load(self.p,r,len(data))
class Tests(unittest.TestCase):
    def test_defaults_are_bit_exact_bypass_on_all_eight_tracks(self):
        rng=np.random.default_rng(93);x=rng.uniform(-1,1,1537).astype('float32');b=Bank()
        for track in range(8):
            l,r=b.process(x,-x,track);self.assertEqual(l.tobytes(),x.tobytes());self.assertEqual(r.tobytes(),(-x).tobytes())
    def test_eq_mid_gain_matches_db_at_center(self):
        for db in [-12,-6,6,12]:
            b=Bank();b.config(eq_enabled=1,mid_db=db);x=tone(1000);y=b.process(x)
            actual=20*math.log10(rms(y[-12000:])/rms(x[-12000:]));self.assertAlmostEqual(actual,db,delta=.05)
    def test_low_shelf_measures_low_boost_and_leaves_highs_alone(self):
        for hz,expected in [(30,11.9),(10000,0)]:
            b=Bank();b.config(eq_enabled=1,low_hz=200,low_db=12);x=tone(hz);y=b.process(x)
            self.assertAlmostEqual(20*math.log10(rms(y[-12000:])/rms(x[-12000:])),expected,delta=.2)
    def test_high_shelf_measures_high_cut_and_leaves_lows_alone(self):
        for hz,expected in [(30,0),(12000,-12)]:
            b=Bank();b.config(eq_enabled=1,high_hz=2000,high_db=-12);x=tone(hz);y=b.process(x)
            self.assertAlmostEqual(20*math.log10(rms(y[-12000:])/rms(x[-12000:])),expected,delta=.2)
    def test_comp_static_gain_matches_threshold_and_ratio(self):
        b=Bank();b.config(comp_enabled=1,threshold_db=-18,ratio=4,attack_ms=1,release_ms=100)
        x=np.full(96000,.5,dtype='float32');y=b.process(x)
        expected=-18+(20*math.log10(.5)+18)/4
        self.assertAlmostEqual(20*math.log10(float(y[-1])),expected,delta=.04)
    def test_stereo_compression_keeps_channel_ratio_with_antiphase(self):
        b=Bank();b.config(comp_enabled=1,threshold_db=-24,ratio=8,attack_ms=1)
        x=tone(100,amp=.8);l,r=b.process(x,-x*.25)
        self.assertLess(float(np.max(np.abs(l+4*r))),1e-6);self.assertLess(rms(l[-12000:]),rms(x[-12000:])*.6)
    def test_right_channel_alone_triggers_linked_detector(self):
        b=Bank();b.config(comp_enabled=1,threshold_db=-24,ratio=8,attack_ms=1)
        l,r=b.process(np.full(48000,.05),np.full(48000,.8))
        self.assertLess(float(l[-1]),.02);self.assertAlmostEqual(float(r[-1]/l[-1]),16,places=5)
    def test_ratio_one_is_unity_after_fade(self):
        b=Bank();b.config(comp_enabled=1,ratio=1,threshold_db=-60);x=tone(220);y=b.process(x)
        self.assertLess(float(np.max(np.abs(y-x))),1e-6)
    def test_parallel_mix_zero_is_exactly_dry(self):
        b=Bank();b.config(comp_enabled=1,comp_mix=0,threshold_db=-60);x=tone(220,amp=.9);y=b.process(x)
        self.assertEqual(y.tobytes(),x.tobytes())
    def test_makeup_is_manual_and_only_in_wet_path(self):
        b=Bank();b.config(comp_enabled=1,ratio=1,makeup_db=6);x=tone(400);y=b.process(x)
        self.assertAlmostEqual(rms(y[-12000:])/rms(x[-12000:]),10**(.3),delta=.001)
    def test_silence_is_finite_and_zero(self):
        b=Bank();b.config(eq_enabled=1,comp_enabled=1,low_db=12,mid_db=12,high_db=12,threshold_db=-60)
        y=b.process(np.zeros(192000));self.assertTrue(np.all(y==0));self.assertEqual(b.meters().faults,0)
    def test_tracks_do_not_share_filter_or_detector_history(self):
        b=Bank();b.config(0,eq_enabled=1,comp_enabled=1,low_db=12,threshold_db=-30);b.process(tone(50,amp=.9),track=0)
        x=tone(800);self.assertEqual(b.process(x,track=1).tobytes(),x.tobytes());self.assertEqual(b.meters(1).faults,0)
    def test_reset_and_reload_produce_reproducible_audio(self):
        b=Bank();b.config(eq_enabled=1,comp_enabled=1,mid_db=6);saved=b.save();x=tone(1000)
        y=b.process(x);self.assertTrue(b.load(saved));z=b.process(x);self.assertEqual(y.tobytes(),z.tobytes())
    def test_processing_is_independent_of_block_partition(self):
        x=tone(317,.7);a=Bank();a.config(eq_enabled=1,comp_enabled=1,mid_db=-8)
        b=Bank();b.config(eq_enabled=1,comp_enabled=1,mid_db=-8)
        self.assertEqual(a.process(x,block=64).tobytes(),b.process(x,block=97).tobytes())
    def test_turning_off_fades_to_bit_exact_bypass(self):
        b=Bank();b.config(eq_enabled=1,comp_enabled=1,mid_db=12);x=tone(1000);b.process(x)
        b.config(eq_enabled=0,comp_enabled=0);y=b.process(x);self.assertEqual(y[-12000:].tobytes(),x[-12000:].tobytes())
    def test_enable_transition_does_not_jump(self):
        b=Bank();x=np.full(24000,.2,dtype='float32');b.config(eq_enabled=1,low_db=12)
        y=b.process(x);self.assertLess(abs(float(y[0])-.2),.002)
    def test_invalid_settings_refused_without_partial_change(self):
        b=Bank();before=b.save()
        for key,value in [('low_db',13),('mid_q',0),('low_hz',24000),('ratio',0),('attack_ms',0),('comp_mix',2),('eq_enabled',2),('threshold_db',float('nan')),('makeup_db',float('inf'))]:
            s=b.settings();setattr(s,key,value);self.assertEqual(lib.tf_configure(b.p,0,C.byref(s)),0);self.assertEqual(b.save(),before)
    def test_corrupt_and_future_records_fail_atomically(self):
        b=Bank();b.config(3,eq_enabled=1,low_db=7);before=b.save()
        for offset in [0,4,8,12,30,len(before)-1]:
            data=bytearray(before);data[offset]^=4;self.assertFalse(b.load(data));self.assertEqual(b.save(),before)
        for field,value in [(4,4),(8,9),(16,2),(28,0x7fc00000)]:
            data=bytearray(before);struct.pack_into('<I',data,field,value);struct.pack_into('<I',data,len(data)-4,zlib.crc32(data[:-4]));self.assertFalse(b.load(data));self.assertEqual(b.save(),before)
        self.assertFalse(b.load(before[:-1]));self.assertEqual(b.save(),before)
    def test_saved_settings_keep_eight_separate_tracks(self):
        a=Bank()
        for i in range(8):a.config(i,eq_enabled=1,mid_db=i-4,comp_enabled=i%2,ratio=i+1)
        b=Bank();self.assertTrue(b.load(a.save()));self.assertEqual(a.save(),b.save())
    def test_nonfinite_input_is_contained_and_recovers(self):
        b=Bank();b.config(eq_enabled=1,comp_enabled=1);x=tone(200,.1);x[0]=float('nan');x[4]=float('inf')
        y=b.process(x);self.assertTrue(np.all(np.isfinite(y)));self.assertEqual(b.meters().faults,2)
        self.assertGreater(rms(b.process(tone(200))),.001)
    def test_overlapping_channels_and_invalid_track_are_no_write(self):
        b=Bank();x=np.arange(128,dtype='float32');old=x.tobytes()
        for args in [(0,x.ctypes.data,x.ctypes.data,64),(0,x.ctypes.data,x.ctypes.data+4,64),(8,x.ctypes.data,None,64),(0,x.ctypes.data,None,4097)]:
            self.assertEqual(lib.tf_process(b.p,*args),0);self.assertEqual(x.tobytes(),old)
    def test_eq_extremes_and_live_changes_are_finite(self):
        rng=np.random.default_rng(42)
        for rate in [32000,44100,48000,96000]:
            b=Bank(rate);b.config(eq_enabled=1,comp_enabled=1,attack_ms=.1,release_ms=10,threshold_db=-60,ratio=20)
            for i in range(80):
                b.config(low_hz=float(rng.uniform(20,rate*.45)),mid_hz=float(rng.uniform(20,rate*.45)),high_hz=float(rng.uniform(20,rate*.45)),low_db=float(rng.choice([-12,12])),mid_db=float(rng.choice([-12,12])),high_db=float(rng.choice([-12,12])),mid_q=float(rng.choice([.3,6])))
                y=b.process(rng.uniform(-.4,.4,512));self.assertTrue(np.all(np.isfinite(y)));self.assertLess(float(np.max(np.abs(y))),100)
            self.assertEqual(b.meters().faults,0)
    def test_attack_and_release_behave_in_time(self):
        b=Bank();b.config(comp_enabled=1,threshold_db=-24,ratio=8,attack_ms=10,release_ms=80)
        b.process(np.full(24000,.005));y=b.process(np.full(24000,.8));self.assertGreater(float(y[0]),float(y[-1])*2)
        y=b.process(np.full(48000,.005));self.assertGreater(float(y[-1]),float(y[0])*2)
    def test_meter_reports_gain_reduction_without_makeup_bias(self):
        b=Bank();b.config(comp_enabled=1,threshold_db=-24,ratio=8,makeup_db=12,attack_ms=1)
        b.process(np.full(48000,.8));m=b.meters();self.assertGreater(m.reduction_db,15);self.assertAlmostEqual(m.input_peak,.8,places=5);self.assertEqual(m.faults,0)
    def test_soft_clip_bounds_samples_at_adjustable_ceiling_after_fade(self):
        for db in [-12,-6,-1,0]:
            b=Bank();b.config(clip_enabled=1,clip_ceiling_db=db);b.process(np.zeros(48000))
            x=np.linspace(-20,20,4096,dtype='float32');l,r=b.process(x,-x)
            ceiling=10**(db/20);self.assertLessEqual(float(np.max(np.abs(l))),ceiling+1e-6)
            self.assertTrue(np.all(np.diff(l)>=-2*np.finfo('float32').eps*ceiling));self.assertLess(float(np.max(np.abs(l+r))),1e-6)
    def test_soft_clip_is_rounded_and_low_level_is_nearly_linear(self):
        b=Bank();b.config(clip_enabled=1,clip_ceiling_db=0);b.process(np.zeros(48000))
        y=b.process(np.array([.001,.01,.5,1,2,3,4],dtype='float32'))
        self.assertAlmostEqual(float(y[0]),.001,delta=1e-7)
        self.assertLess(float(y[2]),.5);self.assertGreater(float(y[3]),float(y[2]));self.assertLess(float(y[3]),1)
        self.assertGreater(float(y[4]),float(y[3]));self.assertAlmostEqual(float(y[-1]),1,places=6)
    def test_soft_clip_after_compressor_makeup_and_eq(self):
        b=Bank();b.config(eq_enabled=1,low_db=12,comp_enabled=1,ratio=1,makeup_db=12,clip_enabled=1,clip_ceiling_db=-1)
        x=tone(30,1,amp=1);y=b.process(x)
        self.assertLessEqual(float(np.max(np.abs(y[-12000:]))),10**(-1/20)+1e-6);self.assertEqual(b.meters().faults,0)
    def test_soft_clip_switch_off_returns_to_exact_bypass(self):
        b=Bank();b.config(clip_enabled=1);b.process(tone(100));b.config(clip_enabled=0)
        x=tone(100,amp=2);y=b.process(x);self.assertEqual(y[-12000:].tobytes(),x[-12000:].tobytes())
    def test_soft_clip_settings_survive_save_and_t1_records_migrate_disabled(self):
        b=Bank();b.config(3,clip_enabled=1,clip_ceiling_db=-6);saved=b.save();c=Bank();self.assertTrue(c.load(saved));self.assertEqual(c.save(),saved)
        # Construct the old documented v1 layout with no clip fields.
        old=bytearray(struct.pack('<4I',0x31584654,1,8,500))
        for i in range(8):
            s=b.settings(i);old.extend(struct.pack('<2I13f',s.eq_enabled,s.comp_enabled,*[getattr(s,n) for n,_ in Settings._fields_[4:-1]]))
        old.extend(struct.pack('<I',zlib.crc32(old)));self.assertEqual(len(old),500);self.assertTrue(c.load(old))
        for i in range(8):self.assertEqual(c.settings(i).clip_enabled,0);self.assertEqual(c.settings(i).clip_ceiling_db,-1)
        before=c.save();struct.pack_into('<I',old,4,2);struct.pack_into('<I',old,496,zlib.crc32(old[:-4]))
        self.assertFalse(c.load(old));self.assertEqual(c.save(),before)
    def test_invalid_clip_controls_refused(self):
        b=Bank();before=b.save()
        for key,value in [('clip_enabled',2),('clip_ceiling_db',1),('clip_ceiling_db',-13),('clip_ceiling_db',float('nan'))]:
            s=b.settings();setattr(s,key,value);self.assertFalse(lib.tf_configure(b.p,0,C.byref(s)));self.assertEqual(b.save(),before)
    def test_auto_makeup_uses_daisy_threshold_ratio_compensation(self):
        a=Bank();self.assertEqual(a.settings().auto_makeup,1)
        a.config(comp_enabled=1,auto_makeup=1,threshold_db=-18,ratio=3,attack_ms=1)
        b=Bank();b.config(comp_enabled=1,auto_makeup=0,threshold_db=-18,ratio=3,attack_ms=1,makeup_db=6)
        x=np.full(48000,.4,dtype='float32');y=a.process(x);z=b.process(x)
        self.assertLess(float(np.max(np.abs(y-z))),1e-6)
        self.assertAlmostEqual(a.meters().reduction_db,b.meters().reduction_db,places=5)
    def test_auto_makeup_ratio_one_never_adds_gain(self):
        b=Bank();b.config(comp_enabled=1,auto_makeup=1,ratio=1,threshold_db=-60)
        x=tone(1000);self.assertLess(float(np.max(np.abs(b.process(x)-x))),1e-6)
    def test_auto_switch_and_parameter_changes_update_compensation(self):
        b=Bank();b.config(comp_enabled=1,auto_makeup=0,ratio=3,threshold_db=-18,attack_ms=1)
        x=np.full(48000,.4,dtype='float32');a=b.process(x)[-1]
        b.config(auto_makeup=1);z=b.process(x)[-1];self.assertAlmostEqual(float(z/a),10**(.3),delta=.001)
        b.config(auto_makeup=1,ratio=5,threshold_db=-30);saved=b.save();c=Bank();self.assertTrue(c.load(saved));self.assertEqual(c.settings().auto_makeup,1)
if __name__=='__main__':unittest.main(verbosity=2)
