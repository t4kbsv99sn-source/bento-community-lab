"""Validate pinned EU10/CH1/CH10 and require complete unittest summaries."""
import argparse,os,subprocess,sys,re,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--stock',type=Path,required=True);p.add_argument('--target',choices=['eu10','ch1','ch10'],required=True);a=p.parse_args();out=a.build.resolve()
env=dict(os.environ,BENTO_FX_CANDIDATE=str(out),BENTO_K16_IMAGE=str(out/'baseline/bento1.bin'),BENTO_STOCK_IMAGE=str(a.stock.resolve()),BENTO_CHORD_BUILD=str(out/'chord-core'))
W=out/'workspace'
if a.target in ('ch1','ch10'):subprocess.run([sys.executable,str(W/'chord_work/build.py'),'--out',str(out/'chord-core')],check=True,env=env)
runs=[(name.upper()+'_RESULTS',[sys.executable,str(R/'tools/run_native_checks.py'),str(W/f'eu4_work/integration/test_{name}.py')]) for name in ['safety','gestures','integration','previous_controls','live','editable_eu','eu7','eu8','eu9','eu10']+(['melodic','chord_audition','record_takeover'] if a.target=='ch10' else [])]
runs += [('CONTROLS_E3_RESULTS',[sys.executable,str(W/'eu4_work/test_controls_e3.py')]),('DSP_RESULTS',[sys.executable,str(W/'eu4_work/track_fx/build.py')]),('VISUAL_RESULTS',[sys.executable,str(R/'tools/test_visual_isolated.py'),'--suite',str(W/'eu4_work/test_eu5.py')]),('K16_REGRESSIONS',[sys.executable,str(W/'eu4_work/test_k16_regressions.py')])]
if a.target in ('ch1','ch10'):runs.append(('CHORD_RESULTS',[sys.executable,'-m','unittest','discover','-s',str(W/'chord_work'),'-p','test_*.py','-v']))
counts={}
for name,cmd in runs:
 print('Checking',name,flush=True)
 with (out/(name+'.txt')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=R,check=True)
 log=(out/(name+'.txt')).read_text();m=re.findall(r'Ran (\d+) tests',log);assert m and log.rstrip().endswith('OK'),name+' incomplete or failed'
 counts[name]=int(m[-1]);print(name,counts[name],'passed',flush=True)
(out/'VALIDATION_SUMMARY.json').write_text(json.dumps(dict(suites=counts,total=sum(counts.values())),indent=2)+'\n');print('Total',sum(counts.values()),'software checks passed')
