"""ARM instruction counts, not device CPU percentages. Uses native parameters."""
from pathlib import Path
import sys,argparse,json,struct
from unicorn import UC_HOOK_CODE
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'chord_work'),str(R/'eu4_work/integration')]
from test_melodic_locks import Audio
from test_integration import AA
p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
x=Audio();results={}
def measure(name,fn):
 count=[0]
 def tick(*args):count[0]+=1
 h=x.u.hook_add(UC_HOOK_CODE,tick)
 try:fn()
 finally:x.u.hook_del(h)
 results[name]=count[0]
x.note(0);x.context();new=bytes(x.u.mem_read(0x0809fd80,4));old=a.reference.read_bytes()[0x0809fd80-0x08040000:][:4]
x.u.mem_write(0x0809fd80,old);x.u.ctl_remove_cache(0x0809fd80,0x0809fd90);measure('reference_native_filter_evaluation',lambda:x.evaluate())
x.u.mem_write(0x0809fd80,new);x.u.ctl_remove_cache(0x0809fd80,0x0809fd90);measure('p14_unlocked_filter_evaluation',lambda:x.evaluate())
x.note(x.pack(0x510405dc,0x510502ee));measure('p14_voice_context_with_two_locks',lambda:x.context());measure('p14_locked_filter_evaluation',lambda:x.evaluate())
x.note(0x51010384);x.context();measure('p14_level_64_mono_samples',lambda:x.gain([1.]*64))
measure('p14_level_note_initialization',lambda:x.note(0x51010384))
assert results['p14_locked_filter_evaluation']<1500 and results['p14_level_64_mono_samples']<1500,results
report=dict(note='Emulated ARM instructions per operation; not device CPU or latency.',audio_state_bytes=3200,results=results)
a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
