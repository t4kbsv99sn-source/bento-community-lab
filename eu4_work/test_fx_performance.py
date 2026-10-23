"""ARM instruction/audio comparison against the preserved TF2/EU3 DSP."""
from pathlib import Path
import importlib.util,sys,json
import numpy as np
from unicorn import UC_HOOK_CODE
R=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module('old_arm',R/'tf2_work/track_fx/tests/test_arm_track_fx.py')
new=module('new_arm',R/'eu4_work/track_fx/tests/test_arm_track_fx.py')
x=np.array([.35*np.sin(i*.073)+.2*np.sin(i*.381) for i in range(1024)],dtype=np.float32)
results=[]
for name,config in [('bypass',{}),('eq',dict(eq_enabled=1,low_db=6,mid_db=-8,high_db=4)),('compressor',dict(comp_enabled=1,threshold_db=-24,ratio=5,auto_makeup=1)),('clipper',dict(clip_enabled=1,clip_ceiling_db=-6)),('all',dict(eq_enabled=1,mid_db=-5,comp_enabled=1,threshold_db=-24,ratio=5,auto_makeup=1,clip_enabled=1,clip_ceiling_db=-6))]:
 outputs=[];costs=[]
 for m in [old,new]:
  p=m.Arm();p.config(**config)
  count=[0]
  def hook(*args):count[0]+=1
  h=p.u.hook_add(UC_HOOK_CODE,hook);p.process(np.zeros(14000,dtype=np.float32));count[0]=0;outputs.append(np.asarray(p.process(x,-x*.4)));p.u.hook_del(h);costs.append(count[0])
 error=float(np.max(np.abs(outputs[0]-outputs[1])));assert error<2e-5,(name,error)
 # Bypass is measured too; production bridge skips fully disabled strips.
 results.append(dict(effect=name,old_instructions=costs[0],new_instructions=costs[1],reduction_percent=100*(1-costs[1]/costs[0]),max_sample_error=error))
print(json.dumps(results,indent=2))
