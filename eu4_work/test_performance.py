"""Compare complete ARM synth renders with EU3: audio and executed instructions.
Instruction counts are NOT device cycles or a real-time CPU meter.
"""
from pathlib import Path
import sys,os,json,struct,importlib.util
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'k16_work'),str(ROOT/'k16_work/bento_controls')]
import release,kick_build
stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes();release.candidate(stock)
oldsyms=dict(kick_build.SYMS)
spec=importlib.util.spec_from_file_location('newkick',ROOT/'eu4_work/drums/kick_build.py');nk=importlib.util.module_from_spec(spec);spec.loader.exec_module(nk);nk.compile_kick();newsyms=dict(nk.SYMS)
old=Path(os.environ['BENTO_EU3_IMAGE']).read_bytes();new=(Path(os.environ['BENTO_FX_CANDIDATE'])/'bento1.bin').read_bytes()
release.native.candidate=lambda _: (old,[])
import unicorn
om=unicorn.Uc.mem_map
unicorn.Uc.mem_map=lambda self,a,n,*args,**kw:om(self,a,0x1c0000 if a==0x8040000 and n==0x180000 else n,*args,**kw)
from test_kick import Kick,FRAMES
import test_plock
from unicorn import UC_HOOK_CODE
results=[]
for model in [1,3,5]:
 audio=[];cost=[]
 for image,syms in [(old,oldsyms),(new,newsyms)]:
  release.native.candidate=lambda _,i=image:(i,[]);kick_build.SYMS.clear();kick_build.SYMS.update(syms)
  test_plock.IMAGE=image
  p=Kick();p.w(p.desc+0x24,FRAMES+model-1);p.start();a=[]
  counter=[0]
  def count(*args):counter[0]+=1
  hook=p.u.hook_add(UC_HOOK_CODE,count)
  for i in range(16):
   ok,out=p.render();assert ok==1;a.extend(out)
  p.u.hook_del(hook);cost.append(counter[0]);audio.append(a)
 error=max(abs(x-y) for x,y in zip(*audio));assert error<1e-6,(model,error)
 results.append(dict(model=model,old_instructions=cost[0],new_instructions=cost[1],reduction_percent=100*(1-cost[1]/cost[0]),max_sample_error=error))
print(json.dumps(results,indent=2))
