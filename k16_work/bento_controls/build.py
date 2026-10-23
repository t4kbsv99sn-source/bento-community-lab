"""Private L3 application-only experiment. Always build from exact owner stock."""
from pathlib import Path
import sys, struct, subprocess, hashlib, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bento_mods'))
from extension import load_profile
from integration_candidate import restore
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
ROOT=Path(__file__).resolve().parent
BASE=0x08040000;STATE=0x24048ca0;OLD_END=0x24048da0
HEAP_END=0x24042000
INPUT=0x080d0000;STARTUP=0x080d0800;CONSUMER=0x081b3f40;C_CODE=0x081b4100;UI_STARTUP=0x081b5200;SELECTION=0x081b5300

def compile_code():
 profile=json.loads((ROOT/'bento-1.6.1.json').read_text())
 (ROOT/'bindings.h').write_text('/* Generated from the exact-version profile; do not edit. */\n'+''.join('#define NATIVE_'+k+' '+v+'u\n' for k,v in profile['native_api'].items()))
 subprocess.run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m4','-mfloat-abi=soft','-Oz','-ffreestanding','-fno-builtin','-fno-stack-protector','-ffunction-sections','-nostdlib','-Wl,--script='+str(ROOT/'link.ld'),'-Wl,--entry=controls_dispatch',str(ROOT/'controls.c'),'-o',str(ROOT/'controls.elf')],check=True)
 elf=(ROOT/'controls.elf').read_bytes();entry=struct.unpack_from('<I',elf,24)[0]
 if entry!=C_CODE|1:raise ValueError('Wrong C entry point')
 off=struct.unpack_from('<I',elf,32)[0];size,count=struct.unpack_from('<HH',elf,46)
 sections=[struct.unpack_from('<10I',elf,off+i*size) for i in range(count)]
 allocated=[s for s in sections if s[2]&2]
 if len(allocated)!=2 or [s[3] for s in allocated]!=[C_CODE,0x081b5000]:raise ValueError('Unexpected allocated ELF sections')
 code=bytearray()
 for s in allocated:
  code+=bytes(s[3]-C_CODE-len(code));code+=elf[s[4]:s[4]+s[5]]
 return bytes(code)

def candidate(stock):
 p=load_profile(stock,ROOT/'bento-1.6.1.json');image=bytearray(stock);writes=[];ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
 def put(a,data,expected,reason):
  o=a-BASE
  if not BASE<=a<a+len(data)<=0x08200000:raise ValueError('Outside application')
  if o>len(image) or bytes(image[o:o+len(data)])!=expected:raise ValueError('Original mismatch '+hex(a))
  if expected and len(expected)!=len(data):raise ValueError('Length drift')
  if any(a<w['address']+w['size'] and w['address']<a+len(data) for w in writes):raise ValueError('Overlap')
  image[o:o+len(data)]=data;writes.append(dict(address=a,size=len(data),original_hex=expected.hex(),replacement_hex=data.hex(),reason=reason))
 def asm(name,a):
  src='\n'.join(x.split('//')[0] for x in (ROOT/(name+'.s')).read_text().splitlines())
  symbols=dict(p['symbols'],STATE=hex(STATE),STATE_MAGIC='0x31534d42',EVENT_MAGIC='0x314d5442',EVENT_TAIL='0x31525442')
  for k,v in symbols.items():src=src.replace('@'+k+'@',v)
  code=bytes(ks.asm(src,a)[0]);return code+('BENTO_MOD:hold-controls:0.13.0:'+name+'\0').encode()
 for name,a,limit in [('input',INPUT,0x800),('startup',STARTUP,0x100)]:
  code=asm(name,a)
  if len(code)>limit:raise ValueError('Code overlap')
  put(a,code,bytes(len(code)),name+' hook implementation')
 wrapper=asm('consumer',CONSUMER)
 if len(wrapper)>C_CODE-CONSUMER:raise ValueError('Consumer overlap')
 payload=bytes(CONSUMER-(BASE+len(stock)))+wrapper+bytes(C_CODE-CONSUMER-len(wrapper))+compile_code()
 ui=asm('ui_startup',UI_STARTUP)
 gap=UI_STARTUP-(BASE+len(stock)+len(payload))
 if gap<0 or len(ui)>256:raise ValueError('UI startup overlaps implementation')
 payload+=bytes(gap)+ui
 selection=asm('selection',SELECTION)
 gap=SELECTION-(BASE+len(stock)+len(payload))
 if gap<0 or len(selection)>256:raise ValueError('Selection observer overlaps implementation')
 payload+=bytes(gap)+selection
 payload+=b'\xff'*(-(len(stock)+len(payload))%4)
 put(BASE+len(stock),payload,b'','Appended UI implementation')
 for a,target,old,name in [(0x0808d1fe,INPUT,'9c42f6d0','input'),(0x0813f98c,CONSUMER,'a5f11103','consumer'),(0x080404b6,STARTUP,'24482449','startup'),(0x081004b6,UI_STARTUP,'24482449','UI startup'),(0x0813bd10,SELECTION,'f0b589b0','Drum selection observer')]:
  put(a,bytes(ks.asm('b.w '+hex(target),a)[0]),bytes.fromhex(old),name+' branch')
 for a in [0x08040588,0x080a3bdc,0x080a3e94]:put(a,struct.pack('<I',HEAP_END),struct.pack('<I',OLD_END),'Reserve 28064 bytes: kick, lock, condition and UI state; stack unchanged')
 from plock_hooks import payloads,COMMAND,SEQUENCE,EVALUATE
 for a,data in payloads()[0]:put(a,data,bytes(len(data)),'L3 M7 application implementation')
 for a,target,old in [(0x0808f39c,COMMAND,'0d9a93b2'),(0x08061040,SEQUENCE,'90f82030'),(0x0809fd80,EVALUATE,'036b002b')]:
  put(a,bytes(ks.asm('b.w '+hex(target),a)[0]),bytes.fromhex(old),'L3 M7 application hook')
 from conditions import writes_for
 for a,data,old,reason in writes_for(stock,BASE+len(image)):
  put(a,data,old,reason)
 from holdstep import writes_for as hold_writes
 for a,data,old,reason in hold_writes(stock,BASE+len(image)):
  put(a,data,old,reason)
 from step_locks import writes_for as lock_writes
 for a,data,old,reason in lock_writes(stock,BASE+len(image)):
  put(a,data,old,reason)
 from kick_build import writes_for as kick_writes
 for a,data,old,reason in kick_writes(stock,BASE+len(image)):
  put(a,data,old,reason)
 from kick_install_build import writes_for as install_writes
 for a,data,old,reason in install_writes(stock,BASE+len(image)):
  put(a,data,old,reason)
 from kick_ui_build import writes_for as kick_ui_writes
 for a,data,old,reason in kick_ui_writes(stock,BASE+len(image)):
  put(a,data,old,reason)
 put(0x0819dd20,struct.pack('<I',0x081b5001),struct.pack('<I',0x0814b631),'Native mixer render adapter runs on UI thread')
 color=p['empty_step_color']
 put(int(color['address'],0),bytes.fromhex(color['replacement_hex']),bytes.fromhex(color['original_hex']),'Unlit empty steps; native active-step track color remains unchanged')
 put(0x0818bad4,b'1.6K7\0',b'1.6.1\0','Visible experiment identifier')
 result=bytes(image)
 assert restore(result,writes)==stock
 for a,n in [(BASE,0x400),(0x080e0000,0x20000),(0x08100000,0x400)]:assert result[a-BASE:a-BASE+n]==stock[a-BASE:a-BASE+n]
 assert len(result)%4==0 and len(result)<0x1c0000
 return result,writes

if __name__=='__main__':
 stock=Path(sys.argv[1]).read_bytes();data,writes=candidate(stock)
 dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=False)
 (dest/'bento1.bin').write_bytes(data)
 (dest/'manifest.json').write_text(json.dumps(dict(version='0.14.0',label='1.6K7',stock_sha256=hashlib.sha256(stock).hexdigest(),candidate_sha256=hashlib.sha256(data).hexdigest(),writes=writes),indent=2)+'\n')
 print('Built',len(data),'bytes; exact restoration verified')
