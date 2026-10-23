"""K16 shortcut assertions through TF2's real outer consumer adapter."""
import sys,types,unittest,os
from pathlib import Path
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import build
image=(Path(os.environ['BENTO_FX_CANDIDATE'])/'bento1.bin').read_bytes()
build.candidate=lambda stock:(image,[])
m=types.ModuleType('previous_controls');m.__file__=str(ROOT/'k16_work/bento_controls/test_controls.py')
source=Path(m.__file__).read_text().replace('count=10000','count=100000')
exec(compile(source,m.__file__,'exec'),m.__dict__)
m.CONSUMER=0x0813f98c
original=m.Fixture.event
def event(self,*args,**kwargs):
 self.w(0x3001fe2c,self.r(0x3001fe2c)+1000)
 return original(self,*args,**kwargs)
m.Fixture.event=event
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(m.Tests));sys.exit(not result.wasSuccessful())
