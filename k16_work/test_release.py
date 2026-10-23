"""Run relevant native integration regressions and K15 tests on the final image."""
from pathlib import Path
import sys,os,unittest
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('BENTO_STOCK_IMAGE',str(ROOT.parent/'handoff/Bento_Work_Handoff_2026-10-16/01_BENTO_FIRMWARE/1.6.1/bento1.bin'))
sys.path.insert(0,str(ROOT/'k16_work/bento_controls'))
import release
stock=Path(os.environ['BENTO_STOCK_IMAGE']).read_bytes();image,writes=release.candidate(stock)
release.native.candidate=lambda stock:(image,writes)
modules=['test_controls','test_conditions','test_holdstep','test_editable_locks','test_l4','test_l5','test_l6','test_l7','test_l8','test_inst_lights','test_mixer_lights','test_drum_mute','test_kick','test_kick_ui','test_kick_install','test_kick_assignment','test_kick_bridge','test_kick_diagnostic','test_kick_k6','test_k14','test_k15','test_k16']
if '--focused' in sys.argv:modules=['test_kick_ui','test_kick_install','test_k14','test_k15','test_k16']
if '--k16-only' in sys.argv:modules=['test_k16']
modules=[m for m in modules if (ROOT/'k16_work/bento_controls'/(m+'.py')).exists()]
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not r.wasSuccessful())
