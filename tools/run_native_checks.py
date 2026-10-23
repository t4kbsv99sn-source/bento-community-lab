"""Run a native test script with cyclic callback owners retained until exit.
Unicorn callback cycles must not be collected midway through a test suite.
This changes process lifetime only; assertions and firmware code are unchanged.
"""
import gc,runpy,sys
from pathlib import Path
gc.disable()
script=Path(sys.argv[1]).resolve();sys.argv=[str(script),*sys.argv[2:]];sys.path.insert(0,str(script.parent))
runpy.run_path(str(script),run_name='__main__')
