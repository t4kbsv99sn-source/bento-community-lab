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
import unicorn
native_map=unicorn.Uc.mem_map
def full_application_map(self,address,size,*args,**kwargs):
 # Legacy fixture's 1.5 MiB flash window ended five KiB before the new UI.
 # Model the declared application region, without changing any firmware limit.
 if address==0x08040000 and size==0x180000:size=0x1c0000
 return native_map(self,address,size,*args,**kwargs)
unicorn.Uc.mem_map=full_application_map
modules=['test_k16','test_l8','test_holdstep','test_conditions','test_inst_lights','test_mixer_lights','test_drum_mute']
modules=[m for m in modules if (ROOT/'k16_work/bento_controls'/(m+'.py')).exists()]
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())
