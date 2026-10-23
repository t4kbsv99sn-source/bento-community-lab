"""Isolated EU10 branch build from exact owner stock through exact K16."""
from pathlib import Path
import argparse,subprocess,sys,os,shutil,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--stock',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--test',action='store_true');a=p.parse_args()
out=a.out.resolve();stock=a.stock.resolve()
if out.exists() and any(out.iterdir()):raise SystemExit('Choose an empty output directory')
out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(ROOT/'tools/build_k16.py'),'--stock',str(stock),'--out',str(out/'baseline')],check=True)
work=out/'workspace';work.mkdir()
for name in ['eu4_work','tf2_work','k16_work','k16_overlay']:
 shutil.copytree(ROOT/name,work/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.elf','*.o','*.so','arm_objects'))
baseline=out/'baseline/bento1.bin'
subprocess.run([sys.executable,str(work/'eu4_work/integration/build_fx.py'),str(baseline),str(out)],check=True)
image=(out/'bento1.bin').read_bytes();base=baseline.read_bytes();original=stock.read_bytes()
assert len(image)%4==0 and len(image)<0x1c0000
fm=json.loads((out/'baseline/FULL_MANIFEST.json').read_text());extra=json.loads((out/'manifest.json').read_text())
merged=[]
for w in fm['writes']:
 w=dict(w);o=w['address']-0x08040000
 if not w['original_hex']:w['size']=len(image)-o
 w['replacement_hex']=image[o:o+w['size']].hex();merged.append(w)
for w in extra['writes']:
 lo=w['address'];hi=lo+w['size']
 if any(x['address']<=lo and hi<=x['address']+x['size'] for x in merged):continue
 if lo>=0x08040000+len(original):continue
 assert not any(lo<x['address']+x['size'] and x['address']<hi for x in merged)
 w=dict(w);o=lo-0x08040000;w['original_hex']=original[o:o+w['size']].hex();merged.append(w)
restored=bytearray(image)
for w in reversed(merged):
 o=w['address']-0x08040000;restored[o:o+w['size']]=bytes.fromhex(w['original_hex'])
assert bytes(restored[:len(original)])==original
report=dict(label='1.6EA',sha256=hashlib.sha256(image).hexdigest(),stock_sha256=digest(stock),baseline_sha256=digest(baseline),writes=merged)
(out/'FULL_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n')
env=dict(os.environ,BENTO_STOCK_IMAGE=str(stock),BENTO_K16_IMAGE=str(baseline),BENTO_FX_CANDIDATE=str(out))
if a.test:
 for name in ['safety','gestures','integration','previous_controls','live','editable_eu','eu7','eu8','eu9','eu10']:
  with (out/(name.upper()+'_RESULTS.txt')).open('w') as log:
   subprocess.run([sys.executable,str(work/f'eu4_work/integration/test_{name}.py')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
 with (out/'CONTROLS_E3_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'eu4_work/test_controls_e3.py')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
 with (out/'DSP_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'eu4_work/track_fx/build.py')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
 with (out/'VISUAL_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'eu4_work/test_eu5.py')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
 with (out/'K16_REGRESSIONS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'eu4_work/test_k16_regressions.py')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
if a.test:
 for n in ['SAFETY_RESULTS','GESTURES_RESULTS','INTEGRATION_RESULTS','PREVIOUS_CONTROLS_RESULTS','LIVE_RESULTS','CONTROLS_E3_RESULTS','DSP_RESULTS','VISUAL_RESULTS','K16_REGRESSIONS','EDITABLE_EU_RESULTS','EU7_RESULTS','EU8_RESULTS','EU9_RESULTS','EU10_RESULTS']:
  log=(out/(n+'.txt')).read_text()
  assert re.search(r'Ran \d+ tests',log) and log.rstrip().endswith('OK'),n+' incomplete or failed'
records={}
for name in ['eu4_work','tf2_work','k16_work','k16_overlay']:
 for f in (work/name).rglob('*'):
  if not f.is_file() or f.suffix in ['.elf','.pyc','.o','.so'] or '__pycache__' in f.parts:continue
  rel=f.relative_to(work);assert f.read_bytes()==(ROOT/rel).read_bytes(),str(rel)
  records[rel.as_posix()]=digest(f)
(out/'SOURCE_INPUTS.json').write_text(json.dumps(records,indent=2)+'\n')
print('EU10',report['sha256'],len(image),'bytes; exact stock and K16 reversal verified')
