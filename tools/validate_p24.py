"""Validate installed P24 and require complete unittest summaries."""
import argparse,os,subprocess,sys,re,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--stock',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--only',default='',help='comma-separated name parts, e.g. motion,safety (quick check, no summary)');a=p.parse_args();out=a.build.resolve()
env=dict(os.environ,MOTION_CANDIDATE=str(out),BENTO_CHORD_TEST_ORIGIN='0x081d8000',PYTHONPATH=os.pathsep.join([str(out/'workspace/chord_work'),str(out/'workspace/eu4_work/integration'),str(out/'workspace/motion_work')]),BENTO_FX_CANDIDATE=str(out),BENTO_K16_IMAGE=str(out/'baseline/bento1.bin'),BENTO_STOCK_IMAGE=str(a.stock.resolve()),BENTO_CHORD_BUILD=str(a.core.resolve()))
W=out/'workspace'
runs=[(name.upper()+'_RESULTS',[sys.executable,str(W/f'eu4_work/integration/test_{name}.py')]) for name in ['safety','gestures','integration','previous_controls','live','editable_eu','eu7','eu8','eu9','eu10','melodic','chord_audition','record_takeover','mod_matrix','analog_ui','perf','drum_menu','mod','p12']]
runs += [('CONTROLS_E3_RESULTS',[sys.executable,str(W/'eu4_work/test_controls_e3.py')]),('DSP_RESULTS',[sys.executable,str(W/'eu4_work/track_fx/build.py')]),('VISUAL_RESULTS',[sys.executable,str(R/'tools/test_visual_isolated.py'),'--suite',str(W/'eu4_work/test_eu5.py')]),('K16_REGRESSIONS',[sys.executable,str(W/'eu4_work/test_k16_regressions.py')]),('MOD_MATRIX_AUDIO_RESULTS',[sys.executable,str(W/'eu4_work/test_mod_matrix_audio.py')]),('ENGINE_RESULTS',[sys.executable,str(W/'eu4_work/test_engines.py')]),('CHORD_RESULTS',[sys.executable,'-m','unittest','discover','-s',str(W/'chord_work'),'-p','test_*.py','-v'])]
M=W/'motion_work'
if (out/'MOTION_MANIFEST.json').exists():runs += [('MOTION_PRODUCER_RESULTS',[sys.executable,str(M/'test_native_producer.py'),'--image',str(out/'fx/bento1.bin')]),('MOTION_AUDIO_RESULTS',[sys.executable,str(M/'test_native_audio.py'),'--image',str(out/'bento1.bin'),'--elf',str(out/'motion_audio.elf')]),('MOTION_END_TO_END_RESULTS',[sys.executable,str(M/'test_motion_end_to_end.py'),'--image',str(out/'fx/bento1.bin'),'--elf',str(out/'motion_audio.elf')]),('MOTION_SETTINGS_RESULTS',[sys.executable,str(M/'test_motion_settings_ui.py')])]
runs += [('SUBTRACTIVE_RESULTS',[sys.executable,str(W/'eu4_work/test_subtractive.py')]),('ANALOG_RESULTS',[sys.executable,str(W/'eu4_work/test_analog.py')])]
counts={}
if a.only:runs=[r for r in runs if any(k.strip().upper() in r[0] for k in a.only.split(','))];assert runs,'--only matched no suite'
for name,cmd in runs:
 previous=out/(name+'.txt')
 if a.resume and previous.exists():
  log=previous.read_text();m=re.findall(r'Ran (\d+) tests?\b',log)
  if m and log.rstrip().endswith('OK'):
   counts[name]=int(m[-1]);print(name,counts[name],'passed (already checked this image)',flush=True);continue
 if len(cmd)>1 and cmd[1].endswith('.py'):
  cmd=[cmd[0],str(R/'tools/run_arm_suite.py'),*cmd[1:]]
 print('Checking',name,flush=True)
 with (out/(name+'.txt')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=R,check=True)
 log=(out/(name+'.txt')).read_text();m=re.findall(r'Ran (\d+) tests?\b',log);assert m and log.rstrip().endswith('OK'),name+' incomplete or failed'
 counts[name]=int(m[-1]);print(name,counts[name],'passed',flush=True)
if a.only:print('Quick check passed:',counts);sys.exit(0)
(out/'VALIDATION_SUMMARY.json').write_text(json.dumps(dict(suites=counts,total=sum(counts.values())),indent=2)+'\n');print('Total',sum(counts.values()),'software checks passed')
