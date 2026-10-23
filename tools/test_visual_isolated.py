"""Run each Unicorn visual test in a fresh process; reject truncated runs.
The multi-emulator process sometimes exits0 inside native callback cleanup.
This isolates the runtime, without skipping or changing any assertion.
"""
import ast,argparse,subprocess,sys,re,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--suite',type=Path,required=True);a=p.parse_args();started=time.monotonic()
tree=ast.parse(a.suite.read_text());names=[c.name+'.'+f.name for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Tests' for f in c.body if isinstance(f,ast.FunctionDef) and f.name.startswith('test_')]
assert len(names)==10
for name in names:
 r=subprocess.run([sys.executable,str(a.suite.resolve()),name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print(r.stdout,flush=True)
 if r.returncode or not re.search(r'Ran 1 test\b',r.stdout) or not r.stdout.rstrip().endswith('OK'):raise SystemExit('Incomplete or failed isolated test: '+name)
print('Ran',len(names),'tests in',round(time.monotonic()-started,3),'s (one fresh process per test)\n\nOK',flush=True)
