"""P15 ARM routing counts; excludes oscillators, native FX and device CPU%."""
from pathlib import Path
import argparse,sys,json,struct
from unicorn import UC_HOOK_CODE
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'chord_work'),str(R/'eu4_work/integration')]
from test_melodic_targets import Sends
from test_integration import AA
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
x=Sends();x.n=128
for b in [x.src,x.out,x.buffers[17],x.buffers[18]]:x.w(b+4,x.n)
results={}
def measure(name,fn):
 count=[0]
 def tick(*a):count[0]+=1
 h=x.u.hook_add(UC_HOOK_CODE,tick)
 try:fn()
 finally:x.u.hook_del(h)
 results[name]=count[0]
x.begin([0,0]);measure('begin_no_send_locks',lambda:x.call(AA['mel_send_begin'],x.synth,x.ctx))
x.begin([0x510a03e8,0]);measure('begin_one_locked_and_one_unlocked_voice',lambda:x.call(AA['mel_send_begin'],x.synth,x.ctx))
measure('locked_voice_routing_128_stereo_frames',lambda:x.contribution(x.voice,.2))
measure('unlocked_voice_routing_128_stereo_frames',lambda:x.contribution(x.other,.3))
measure('publish_track_submixes',lambda:x.call(AA['mel_send_end'],x.synth))
measure('native_track_mixer_with_note_sends_128_stereo_frames',lambda:x.call(0x080a04c0,x.mixroot,x.src,0,x.strip,x.out,x.ctx))
x.note(x.pack(0x510701f4,0x510902ee));measure('locked_envelope_parameter_evaluation',lambda:x.call(AA['mel_envelope'],x.voice+0x240,9))
# Actual UI allocator requested bytes, rounded to the native cache-line boundary.
report=dict(note='Emulated ARM instructions per operation, not hardware CPU percentages. Voice DSP excluded from routing counts. Mixer count includes its native dry processing.',audio_allocation_bytes=294080,results=results)
args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
