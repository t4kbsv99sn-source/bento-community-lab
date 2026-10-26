"""Run an ARM fixture suite with retained callbacks and exact service hooks.

Only Kick.extra's three already-substituted services and AudioProbe's stop
sentinel get narrower hook ranges. All firmware instructions still execute.
This avoids Python register reads on every DSP instruction and Unicorn callback
teardown crashes. No counters, emulated functions or assertions are replaced.
"""
import gc,runpy,sys
from pathlib import Path
import unicorn
gc.disable()
_keep=[]
_original=unicorn.Uc.hook_add
def hook_add(self,kind,callback,*args,**kwargs):
 _keep.append(callback)
 if kind==unicorn.UC_HOOK_CODE and not args and not kwargs:
  name=getattr(callback,'__qualname__','')
  if name=='Kick.extra':
   for at in (0x081be010,0x081be020,0x08092d00):
    handle=_original(self,kind,callback,begin=at,end=at)
   return handle
  if name=='AudioProbe.__init__.<locals>.<lambda>':
   at=callback.__closure__[0].cell_contents.stop
   return _original(self,kind,callback,begin=at,end=at)
 return _original(self,kind,callback,*args,**kwargs)
unicorn.Uc.hook_add=hook_add
suite=Path(sys.argv[1]).resolve();sys.argv=sys.argv[1:]
sys.path.insert(0,str(suite.parent))
runpy.run_path(str(suite),run_name='__main__')
