"""Host render verifies unchanged lower range and audible long upper decay."""
from pathlib import Path
import subprocess,tempfile,json
R=Path(__file__).resolve().parents[1]
program=r'''
#include "Drums/hihat.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
int main(){
 for(float decay:{.5f,.7f,1.f}){
  srand(123);daisysp::HiHat<> h;h.Init(48000);h.SetFreq(207);h.SetDecay(decay);h.SetTone(.65f);h.SetAccent(.65f);h.SetNoisiness(.3f);h.Trig();
  double late=0,energy=0;float peak=0;unsigned late_n=0;
  for(int i=0;i<48000*6;i++){float x=h.Process();if(!std::isfinite(x))return 2;energy+=double(x)*x;if(fabs(x)>peak)peak=fabs(x);if(i>=48000*2&&i<48000*3){late+=double(x)*x;late_n++;}}
  printf("%.2f %.12g %.12g %.12g\n",decay,energy,sqrt(late/late_n),double(peak));
 }
}
'''.replace('#include <cstdlib>','#include <cstdlib>\n#include <initializer_list>')
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.cpp').write_text(program);results=[]
 for folder in [R/'k16_work/bento_controls',R/'eu4_work/drums']:
  v=folder/'vendor/daisysp/Source';exe=d/('new' if folder.name=='drums' else 'old')
  subprocess.run(['g++','-O2','-I'+str(v),'-I'+str(v/'Utility'),str(d/'test.cpp'),str(v/'Drums/hihat.cpp'),str(v/'Filters/svf.cpp'),'-o',str(exe)],check=True)
  results.append([[float(v) for v in line.split()] for line in subprocess.check_output([str(exe)],text=True).splitlines()])
 old,new=results
 assert old[:2]==new[:2],(old,new)
 assert new[2][2]>.005 and new[2][2]>old[2][2]*10,(old,new)
 print(json.dumps(dict(columns=['decay','energy','RMS_seconds_2_to_3','peak'],EU4=old,EU5=new,lower_range_exact=True),indent=2))
