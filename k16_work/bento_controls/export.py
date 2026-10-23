"""Build the private K7 kick handoff test package; never connect to or flash a device."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,zipfile,re
from build import candidate,restore,ROOT,BASE
CONTROLLER_SHA='8100906327093463fb58f531ee28583423a9881ea3a7d5b77874a7700735e99d'
T3_SHA='5e2e4e5ce5f3f156437975a7aa17012bddea99bf707bb4a0657a2380b1712787'
def sha(x):return hashlib.sha256(x).hexdigest()
def export(stock_dir,t3_dir,dest):
 stock_dir,t3_dir,dest=map(Path,(stock_dir,t3_dir,dest))
 stock=(stock_dir/'bento1.bin').read_bytes();controller=(stock_dir/'bento2.bin').read_bytes()
 t3=(t3_dir/'bento1.bin').read_bytes()
 if sha(controller)!=CONTROLLER_SHA or sha(t3)!=T3_SHA or (t3_dir/'bento2.bin').read_bytes()!=controller:raise ValueError('Restore input hash mismatch')
 k6_paths=[ROOT.parent.parent/'Bento_Daisy_Kick_K6/01_K6_TEST_FIRMWARE/bento1.bin',ROOT.parent.parent/'05_PREVIOUS_K6_RESTORE/bento1.bin']
 k6=next(p for p in k6_paths if p.is_file()).read_bytes()
 if sha(k6)!='154ff6320430dd5aeef5e565dd0910e907a1e6ddcdb3cbb55452823483373a68':raise ValueError('K6 restore hash mismatch')
 image,writes=candidate(stock)
 if restore(image,writes)!=stock:raise ValueError('Cannot exactly restore')
 run=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT),'-p','test_*.py','-v'],capture_output=True,text=True,env=__import__('os').environ|{'BENTO_STOCK_IMAGE':str((stock_dir/'bento1.bin').resolve())})
 if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 dest.mkdir(parents=True,exist_ok=False)
 for folder,data in [('01_K7_TEST_FIRMWARE',image),('02_PREVIOUS_L8_RESTORE',t3),('03_ORIGINAL_1.6.1_RESTORE',stock),('05_PREVIOUS_K6_RESTORE',k6)]:
  p=dest/folder;p.mkdir();(p/'bento1.bin').write_bytes(data);(p/'bento2.bin').write_bytes(controller)
 source=dest/'04_SOURCE';source.mkdir()
 for name in ['bento_controls','bento_mods']:
  shutil.copytree(ROOT.parent/name,source/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.elf'))
 shutil.copyfile(ROOT/'DEVICE_TEST.md',dest/'00_START_HERE.md')
 (dest/'TEST_RESULTS.txt').write_text(run.stdout+run.stderr)
 report=dict(module='daisy-live-kick-K7',version='0.14.0',label='1.6K7',device_test_passed=False,software_tests=int(re.search(r'Ran (\d+) tests',run.stderr).group(1)),
  original_sha256=sha(stock),candidate_sha256=sha(image),l8_restore_sha256=sha(t3),k6_restore_sha256=sha(k6),unchanged_controller_sha256=sha(controller),
  original_size=len(stock),candidate_size=len(image),appended_bytes=len(image)-len(stock),
  changed_bytes_within_original=sum(a!=b for a,b in zip(stock,image)),
  all_changes_accounted_for=True,byte_exact_restore_verified=True,original_vectors_unchanged=True,original_disk_mode_unchanged=True,
  bootloader_image_included=False,bootloader_updater_included=False,installer_erase_ranges_independently_verified=False,
  notes=['K7 retains the K6 descriptor/provider fix confirmed audible on the device and adds native individual-pad instrument controls.',
   'Top row: Level, Tune, Decay, Tone, Impact, Sweep, Sweep Decay, Dirt. Second row: Kick/pad, Load, Pan, Overdrive, Delay Send, Reverb Send, Filter, Resonance.',
   'Seven synth settings are keyed by actual sound handle, read by M7 via a versioned shared table and saved as explicit versioned pad params XML attributes. Native automation A-D is unchanged; dedicated new synth step-lock targets are not implemented.',
   'Native sample editor, load browser, pad selection and Mix/FX processing are reused. Ordinary samples restore their original row bindings and waveform. The kick graph is an illustrative native envelope, not a scope.',
   'Software tests use native code with controlled widget/XML/provider dependencies. New physical editor interaction, project recall and performance require device verification.',
   'All prior L8 features and strict marker validation are retained. Load creates or validates Projects/BENTO_Kick_K2.wav. Existing diagnostics remain Projects/BENTO_K7_DIAGNOSTICS.txt. No audio-thread filesystem I/O.',
   'Source and MIT DaisySP license, exact working K6, L8 and stock restore pairs included.',
   'Original module headers/vectors, disk/recovery image, native SD installer and controller unchanged. No bootloader bytes modified or bootloader updater supplied. Installer erase ranges not independently verified.'],writes=writes)
 (dest/'BUILD_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
 hashes={str(p.relative_to(dest)):sha(p.read_bytes()) for p in sorted(dest.rglob('*')) if p.is_file()}
 (dest/'SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n')
 zpath=dest.with_suffix('.zip')
 if zpath.exists():raise ValueError('Zip already exists')
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_STORED,allowZip64=False) as z:
  for p in sorted(dest.rglob('*')):
   if p.is_file():z.write(p,str(Path(dest.name)/p.relative_to(dest)))
 with zipfile.ZipFile(zpath) as z:
  if z.testzip():raise ValueError('ZIP integrity failure')
  for folder,data in [('01_K7_TEST_FIRMWARE',image),('02_PREVIOUS_L8_RESTORE',t3),('03_ORIGINAL_1.6.1_RESTORE',stock),('05_PREVIOUS_K6_RESTORE',k6)]:
   assert z.read(dest.name+'/'+folder+'/bento1.bin')==data
   assert z.read(dest.name+'/'+folder+'/bento2.bin')==controller
 print(json.dumps({k:v for k,v in report.items() if k!='writes'},indent=2));print(zpath.resolve())
 return zpath
if __name__=='__main__':export(*sys.argv[1:])
