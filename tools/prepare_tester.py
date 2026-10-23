"""Reproduce a pinned release and make a private tester ZIP from stock files.
Python build dependencies + native C/C++ compiler required; never flashes a device.
"""
from pathlib import Path
import argparse,hashlib,io,json,os,shutil,subprocess,sys,zipfile
from make_drum_carriers import make
ROOT=Path(__file__).resolve().parents[1]
STOCK='14475e9d5068f5659d0fe0b00fc1278c1479c43ed9fda3d40654d5f3a7a6bbb3'
CONTROLLER='8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d'
# Releases this helper reproduces. A public mirror may pin by tag + image hash
# only (commit null), because its commit IDs differ from the private history.
TARGETS=json.loads((Path(__file__).resolve().with_name('release_targets.json')).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def checked_inputs(directory):
 main=(directory/'bento1.bin').read_bytes();controller=(directory/'bento2.bin').read_bytes()
 if sha(main)!=STOCK or sha(controller)!=CONTROLLER:raise ValueError('Supply the exact original Bento 1.6.1 bento1.bin AND bento2.bin. Modified/other versions are refused.')
 return main,controller

def verify_build(build,main,target):
 image=(build/'bento1.bin').read_bytes();manifest=json.loads((build/'FULL_MANIFEST.json').read_text())
 if sha(image)!=target['sha'] or manifest['sha256']!=target['sha'] or manifest['label']!=target['label']:raise ValueError('Build differs from the pinned release; refusing tester package.')
 if len(image)%4 or len(image)>=0x1c0000:raise ValueError('Invalid application image bounds/alignment')
 restored=bytearray(image)
 for w in reversed(manifest['writes']):
  off=w['address']-0x08040000
  if off<0 or off+w['size']>len(image) or image[off:off+w['size']].hex()!=w['replacement_hex']:raise ValueError('Invalid patch bounds or bytes')
  restored[off:off+w['size']]=bytes.fromhex(w['original_hex'])
 if bytes(restored[:len(main)])!=main:raise ValueError('Exact original-image reversal failed')
 summary=json.loads((build/'VALIDATION_SUMMARY.json').read_text())
 if summary['total']!=target['tests']:raise ValueError('Incomplete release checks')
 return image

def write_package(out,main,controller,image,target,source_archive):
 readme=f'''Bento Lab {target['label']} / {target['ref']} — experimental device test

{target.get('notes',"Current CH1 feedback: Chord and Select buttons are missing. EU10 predates Chord; its shared Select UI still needs confirmation after earlier missing-button reports. These issues are not fixed here. EU10 is not a certified stable release.")}

PROJ NOW WORKS AS SHIFT: the project pages it used to open are on PROJ + PLAY.

1. Back up your card/projects and keep your original firmware download.
2. Copy BOTH files inside 01_TEST_FIRMWARE to the microSD top level.
3. If needed, copy the three files in 02_SD_CONTENT/Projects into your existing
   Projects folder. Do not replace the folder. These WAVs select live synths.
4. Use the normal Bento SD firmware installation procedure. Confirm {target['label']}.
5. If restoring, use BOTH files in 03_STOCK_RESTORE through the same procedure.

No automatic flashing. Controller unchanged; original bootloader never patched.
Software checks do not establish device display, audio timing or project storage.
See FEATURES_AND_STATUS.md for controls and the actual known limitations.

Source commit: {target['commit']}
Main SHA256: {target['sha']}
'''
 files={'00_START_HERE.txt':readme.encode(),'01_TEST_FIRMWARE/bento1.bin':image,'01_TEST_FIRMWARE/bento2.bin':controller,'03_STOCK_RESTORE/bento1.bin':main,'03_STOCK_RESTORE/bento2.bin':controller,'FEATURES_AND_STATUS.md':(ROOT/'docs/FEATURES_AND_STATUS.md').read_bytes()}
 for doc in ['DEVELOPER_GUIDE.md','QUICKSTART.md','STATUS.md']:files[doc]=(ROOT/'docs'/doc).read_bytes()
 for f in make(out/'carriers').iterdir():files['02_SD_CONTENT/Projects/'+f.name]=f.read_bytes()
 for f in (out/'build').iterdir():
  if f.is_file() and f.suffix in ['.json','.txt']:files['04_VALIDATION/'+f.name]=f.read_bytes()
 files['04_VALIDATION/RELEASE.json']=(json.dumps(target,indent=2)+'\n').encode()
 with zipfile.ZipFile(io.BytesIO(source_archive)) as z:
  for n in z.namelist():
   if not n.endswith('/'):files['05_SOURCE/repository/'+n]=z.read(n)
 files['05_SOURCE/SOURCE_COMMIT.txt']=(target['commit']+'\n').encode()
 files['SHA256SUMS.txt']=''.join(sha(data)+'  '+n+'\n' for n,data in sorted(files.items())).encode()
 archive=out/f"Bento_{target['label']}_Tester.zip"
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for n,data in files.items():z.writestr(n,data)
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None or any(z.read(n)!=data for n,data in files.items()):raise ValueError('ZIP verification failed')
 return archive

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stock-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--target',choices=TARGETS,default='eu10');a=p.parse_args()
 target=TARGETS[a.target];stock_dir=a.stock_dir.resolve();out=a.out.resolve()
 main_image,controller=checked_inputs(stock_dir) # Refuse bad inputs before writing anything.
 if out.exists() and any(out.iterdir()):p.error('Choose an empty output directory; existing files are never replaced.')
 if not shutil.which('git') or not shutil.which('cc') or not shutil.which('g++'):p.error('Install Git and native C/C++ compilers first (cc and g++).')
 for module in ['ziglang','unicorn','capstone','keystone','numpy']:
  try:__import__(module)
  except ImportError:p.error('Missing build dependencies. Activate your environment and install requirements.txt.')
 actual=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',target['ref']+'^{commit}']).decode().strip()
 if target.get('commit') and actual!=target['commit']:p.error('Release tag does not match the pinned commit. Fetch the original tags; do not substitute another version.')
 target=dict(target,commit=actual)
 source_archive=subprocess.check_output(['git','-C',str(ROOT),'archive','--format=zip',actual]);out.mkdir(parents=True,exist_ok=True);source=out/'source';source.mkdir()
 with zipfile.ZipFile(io.BytesIO(source_archive)) as z:
  for n in z.namelist():
   if Path(n).is_absolute() or '..' in Path(n).parts:raise ValueError('Unsafe source archive path')
  z.extractall(source)
 print('Reproducing',target['ref'],'from',actual,flush=True)
 subprocess.run([sys.executable,str(source/'tools'/target['builder']),'--stock',str(stock_dir/'bento1.bin'),'--out',str(out/'build')],check=True)
 subprocess.run([sys.executable,str(ROOT/'tools/validate_tester.py'),'--build',str(out/'build'),'--stock',str(stock_dir/'bento1.bin'),'--target',a.target],check=True)
 image=verify_build(out/'build',main_image,target);archive=write_package(out,main_image,controller,image,target,source_archive)
 print('Verified tester package:',archive,flush=True);print('No device was connected or flashed. Firmware ZIP contains your stock files: share privately, not as source.')
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
