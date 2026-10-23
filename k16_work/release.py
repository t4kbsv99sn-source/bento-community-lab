"""Build K15 from owner stock; retain K7 memory/boot boundaries and K13 cleanup."""
from pathlib import Path
import sys,json,hashlib,importlib.util
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import build as native
from integration_candidate import restore
OUT=ROOT/'build/k16_candidate'
def candidate(stock):
 base,writes=native.candidate(stock)
 temp=ROOT/'build/k16_base';temp.mkdir(parents=True,exist_ok=True);(temp/'bento1.bin').write_bytes(base)
 spec=importlib.util.spec_from_file_location('k14_cleanup_overlay',ROOT/'k16_overlay/build.py');overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)
 report=overlay.build(temp/'bento1.bin',OUT,expected_sha=hashlib.sha256(base).hexdigest());final=(OUT/'bento1.bin').read_bytes()
 merged=[]
 for w in writes:
  w=dict(w);off=w['address']-native.BASE
  if not w['original_hex']:w['size']=len(final)-off
  w['replacement_hex']=final[off:off+w['size']].hex();merged.append(w)
 for r in report['patches']:
  a=int(r['address'],16);n=len(bytes.fromhex(r['new']))
  if not r['old']:continue
  if any(w['address']<=a and a+n<=w['address']+w['size'] for w in merged):continue
  o=a-native.BASE;merged.append(dict(address=a,size=n,original_hex=stock[o:o+n].hex(),replacement_hex=final[o:o+n].hex(),reason='K13 proven direct lower-editor draw filter'))
 assert restore(final,merged)==stock
 assert final[0xc0000:0xc0400]==stock[0xc0000:0xc0400]
 for a,n in [(0x080404b6,4),(0x081004b6,4),(0x08040588,4),(0x080a3bdc,4),(0x080a3e94,4),(0x08114d74,0x180)]:
  # Startup/heap/MPU remain exactly K7's implementations/limits (native baseline generation).
  off=a-native.BASE;assert final[off:off+n]==base[off:off+n]
 assert len(final)%4==0
 (OUT/'FULL_MANIFEST.json').write_text(json.dumps(dict(label='1.6KG',sha256=hashlib.sha256(final).hexdigest(),stock_sha256=hashlib.sha256(stock).hexdigest(),writes=merged),indent=2))
 return final,merged
if __name__=='__main__':
 b,w=candidate(Path(sys.argv[1]).read_bytes());print('K16',len(b),'bytes;',len(w),'patch records; exact restoration verified')
