"""Build the isolated Track FX preparation. Does not patch any firmware."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
V=ROOT/'vendor/DaisySP-LGPL'
SOURCES=[ROOT/'track_fx.cpp',V/'Source/Dynamics/compressor.cpp',V/'Source/Filters/biquad.cpp']
includes=['-I'+str(V),'-I'+str(V/'Utility')]
def host():
    subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-fno-exceptions','-fno-rtti','-Wall','-Wextra','-Werror',*includes,*map(str,SOURCES),'-o',str(ROOT/'libtrack_fx.so')],check=True)
def arm():
    d=ROOT/'arm_objects';d.mkdir(exist_ok=True)
    common=[sys.executable,'-m','ziglang','c++','-target','thumb-freestanding-eabihf','-mcpu=cortex_m7+fp_armv8d16sp+fpregs+fpregs16+vfp4d16sp','-mfloat-abi=hard','-mfpu=fpv5-sp-d16','-std=c++17','-Os','-flto','-g','-ffreestanding','-fno-builtin','-fno-exceptions','-fno-rtti','-fno-stack-protector','-I'+str(ROOT/'arm_support'),*includes]
    objects=[]
    for p in [*SOURCES,ROOT/'arm_support/math_runtime.cpp']:
        obj=d/(p.stem+'.o');objects.append(obj)
        subprocess.run([*common,'-c',str(p),'-o',str(obj)],check=True)
    subprocess.run([*common,'-nostdlib','-nostdlib++','-Wl,--entry=tf_init','-Wl,--script='+str(ROOT/'arm_support/test_link.ld'),*map(str,objects),'-o',str(ROOT/'track_fx_test.elf')],check=True)
if __name__=='__main__':
    host();arm()
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],check=True,cwd=ROOT)
