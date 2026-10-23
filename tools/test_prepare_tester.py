"""Check actual end-to-end tester outputs; supply both completed helper runs."""
import argparse,hashlib,io,json,os,subprocess,sys,tempfile,unittest,wave,zipfile
from pathlib import Path
from prepare_tester import TARGETS,CONTROLLER,ROOT
p=argparse.ArgumentParser();p.add_argument('--stock-dir',type=Path,required=True);p.add_argument('--eu10-out',type=Path,required=True);p.add_argument('--ch1-out',type=Path,required=True);a=p.parse_args()
OUTS={'eu10':a.eu10_out,'ch1':a.ch1_out}
def digest(b):return hashlib.sha256(b).hexdigest()
class Tests(unittest.TestCase):
 def test_images_stock_restore_controller_and_markers_match(self):
  for name,out in OUTS.items():
   t=TARGETS[name]
   with zipfile.ZipFile(out/f"Bento_{t['label']}_Tester.zip") as z:
    self.assertIsNone(z.testzip());self.assertEqual(digest(z.read('01_TEST_FIRMWARE/bento1.bin')),t['sha']);self.assertEqual(digest(z.read('01_TEST_FIRMWARE/bento2.bin')),CONTROLLER)
    for f in ['bento1.bin','bento2.bin']:self.assertEqual(z.read('03_STOCK_RESTORE/'+f),(a.stock_dir/f).read_bytes())
    waves=[f for f in z.namelist() if f.endswith('.wav')];self.assertEqual(len(waves),3)
    for f in waves:
     with wave.open(io.BytesIO(z.read(f))) as w:self.assertEqual((w.getframerate(),w.getnchannels(),w.getsampwidth()),(48000,1,2))
 def test_every_packaged_checksum_matches(self):
  for name,out in OUTS.items():
   with zipfile.ZipFile(out/f"Bento_{TARGETS[name]['label']}_Tester.zip") as z:
    lines=z.read('SHA256SUMS.txt').decode().splitlines()
    for line in lines:
     expected,path=line.split('  ',1);self.assertEqual(digest(z.read(path)),expected,path)
    self.assertEqual(len(lines),len(z.namelist())-1)
 def test_source_snapshot_and_recorded_tests_are_exact(self):
  for name,out in OUTS.items():
   t=TARGETS[name];commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',t['ref']+'^{commit}']).decode().strip();source=subprocess.check_output(['git','-C',str(ROOT),'archive','--format=zip',commit])
   with zipfile.ZipFile(io.BytesIO(source)) as s,zipfile.ZipFile(out/f"Bento_{t['label']}_Tester.zip") as z:
    for f in s.namelist():
     if not f.endswith('/'):self.assertEqual(z.read('05_SOURCE/repository/'+f),s.read(f),f)
    self.assertEqual(z.read('05_SOURCE/SOURCE_COMMIT.txt').decode().strip(),commit);self.assertEqual(json.loads(z.read('04_VALIDATION/VALIDATION_SUMMARY.json'))['total'],t['tests'])
 def test_wrong_stock_pair_is_refused_without_output(self):
  for field in ['bento1.bin','bento2.bin']:
   with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);stock=tmp/'stock';stock.mkdir()
    for f in ['bento1.bin','bento2.bin']:
     b=(a.stock_dir/f).read_bytes();(stock/f).write_bytes(b'X'+b[1:] if f==field else b)
    dest=tmp/'out';r=subprocess.run([sys.executable,str(ROOT/'tools/prepare_tester.py'),'--stock-dir',str(stock),'--out',str(dest)],capture_output=True)
    self.assertNotEqual(r.returncode,0);self.assertFalse(dest.exists())
 def test_existing_output_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp);sentinel=dest/'keep.txt';sentinel.write_text('keep this')
   r=subprocess.run([sys.executable,str(ROOT/'tools/prepare_tester.py'),'--stock-dir',str(a.stock_dir),'--out',str(dest)],capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertEqual(sentinel.read_text(),'keep this');self.assertEqual(list(dest.iterdir()),[sentinel])
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
