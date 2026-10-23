"""Rebuild/test K16 in an isolated workspace from owner stock; never flash."""
from pathlib import Path
import argparse,subprocess,shutil,sys,os,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--stock',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--test',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1];stock=a.stock.resolve();out=a.out.resolve()
if hashlib.sha256(stock.read_bytes()).hexdigest()!='14475e9d5068f5659d0fe0b00fc1278c1479c43ed9fda3d40654d5f3a7a6bbb3':raise SystemExit('Input is not the expected owner stock 1.6.1 image.')
if out.exists() and any(out.iterdir()):raise SystemExit('Choose an empty output directory.')
work=out/'workspace';work.mkdir(parents=True)
for name in ['k16_work','k16_overlay']:shutil.copytree(root/name,work/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.elf'))
env=dict(os.environ,BENTO_STOCK_IMAGE=str(stock))
subprocess.run([sys.executable,str(work/'k16_work/release.py'),str(stock)],check=True,env=env)
if a.test:
 with (out/'TEST_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'k16_work/test_release.py')],stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
 with (out/'DRAW_TEST_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'k16_overlay/test_draw.py')],stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
 with (out/'REGISTRY_TEST_RESULTS.txt').open('w') as log:subprocess.run([sys.executable,str(work/'k16_work/test_registry.py'),str(work/'build/k16_candidate/bento1.bin')],stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
 v=work/'k16_work/bento_controls/vendor/daisysp/Source';host=out/'host_audio_check'
 subprocess.run(['g++','-std=c++17','-O2','-I'+str(v),'-I'+str(v/'Utility'),str(work/'k16_work/test_audio.cpp'),str(v/'Drums/synthsnaredrum.cpp'),str(v/'Drums/hihat.cpp'),str(v/'Filters/svf.cpp'),'-o',str(host)],check=True)
 with (out/'HOST_AUDIO_RESULTS.txt').open('w') as log:subprocess.run([str(host)],stdout=log,stderr=subprocess.STDOUT,check=True)
for name in ['bento1.bin','FULL_MANIFEST.json','manifest.json']:shutil.copy2(work/'build/k16_candidate'/name,out/name)
records={}
for name in ['k16_work','k16_overlay']:
 for f in (work/name).rglob('*'):
  if not f.is_file() or f.suffix in ['.elf','.pyc'] or '__pycache__' in f.parts:continue
  rel=f.relative_to(work);assert f.read_bytes()==(root/rel).read_bytes(),str(rel)
  records[rel.as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
(out/'SOURCE_INPUTS.json').write_text(json.dumps(records,indent=2)+'\n')
print('Built K16:',out/'bento1.bin')
