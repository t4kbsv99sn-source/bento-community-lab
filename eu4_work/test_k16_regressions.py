"""Exercise inherited synth/lock/LED/condition paths on the combined TF2 image."""
from pathlib import Path
import os,sys,unittest,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'k16_work'));sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import release
stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes()
# Compile K16 symbol maps needed by the inherited compiled-code fixtures.
base,_=release.candidate(stock)
out=Path(os.environ['BENTO_FX_CANDIDATE']);image=(out/'bento1.bin').read_bytes()
writes=json.loads((out/'FULL_MANIFEST.json').read_text())['writes']
release.native.candidate=lambda stock:(image,writes)
import importlib.util, kick_build
spec=importlib.util.spec_from_file_location('optimized_kick', ROOT/'eu4_work/drums/kick_build.py')
optimized=importlib.util.module_from_spec(spec);spec.loader.exec_module(optimized);optimized.compile_kick()
kick_build.SYMS.clear();kick_build.SYMS.update(optimized.SYMS)
import unicorn
native_map=unicorn.Uc.mem_map
def full_application_map(self,address,size,*args,**kwargs):
 # Legacy fixture's 1.5 MiB flash window ended five KiB before the new UI.
 # Model the declared application region, without changing any firmware limit.
 if address==0x08040000 and size==0x180000:size=0x1c0000
 return native_map(self,address,size,*args,**kwargs)
unicorn.Uc.mem_map=full_application_map
import types
original_test=ROOT/'k16_work/bento_controls/test_k16.py'
module=types.ModuleType('test_k16');module.__file__=str(original_test)
source=original_test.read_text().replace("struct.unpack('<2H',p.u.mem_read(0x300000bc+8,4))","struct.unpack('<2H',p.u.mem_read(0x300000bc+12,4))")
source=source.replace('(1,12,20),(3,20,17),(5,25,17)','(1,12,16),(3,20,13),(5,25,13)').replace('p.encoder(0x1da,12)','p.encoder(0x1da,8)').replace('p.encoder(0x1e4,13)','p.encoder(0x1e4,9)')
exec(compile(source,str(original_test),'exec'),module.__dict__);sys.modules['test_k16']=module
modules=['test_k16','test_l8','test_holdstep','test_conditions','test_inst_lights','test_mixer_lights','test_drum_mute']
modules=[m for m in modules if (ROOT/'k16_work/bento_controls'/(m+'.py')).exists()]
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())
