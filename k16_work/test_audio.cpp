#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#define private public
#include "Drums/synthsnaredrum.h"
#include "Drums/hihat.h"
#include "Drums/synthbassdrum.h"
#undef private
int main(){
 printf("sizes kick=%zu snare=%zu hat=%zu\n",sizeof(daisysp::SyntheticBassDrum),sizeof(daisysp::SyntheticSnareDrum),sizeof(daisysp::HiHat<>));
 double previous=0;
 for(int sn=0;sn<=100;sn+=5){
  daisysp::SyntheticSnareDrum s;s.Init(48000);s.SetFreq(200);s.SetDecay(.45);s.SetAccent(.65);s.SetSnappy(sn*.01f);srand(123);s.Trig();double sum=0;float peak=0;int clipped=0;
  for(int i=0;i<48000;i++){float x=s.Process();if(fabs(x*.6f)>1)clipped++;if(!std::isfinite(x))return 1;sum+=x*x;if(fabs(x)>peak)peak=fabs(x);}
  printf("snappy %d rms %.7f peak %.7f damp %.7f clipped %d\n",sn,sqrt(sum/48000),peak,s.snare_lp_.damp_,clipped);
  double rms=sqrt(sum/48000);if(previous && (rms/previous>1.3 || rms/previous<.7))return 6;previous=rms;
  if(s.snare_lp_.damp_<.399 || s.snare_lp_.damp_>2.001)return 2;
 }
 for(int sn=0;sn<=100;sn+=5){
  daisysp::SyntheticSnareDrum s;s.Init(48000);s.SetFreq(200);s.SetSnappy(sn*.01);s.Process();float expected=1/(.5f+2*std::fmin(1.f,std::fmax(0.f,sn*.011f-.05f)));
  if(fabs(s.snare_lp_.damp_-expected)>1e-4)return 3;
 }
 for(int f:{100,207,1170,9360})for(int tone:{0,50,100})for(int noise:{0,30,100})for(int decay:{0,35,100}){
  daisysp::HiHat<> h;h.Init(48000);h.SetFreq(f);h.SetTone(tone*.01);h.SetNoisiness(noise*.01);h.SetDecay(decay*.01);h.SetAccent(.65);h.Trig();double energy=0;float peak=0;
  for(int i=0;i<48000;i++){float x=h.Process();if(!std::isfinite(x))return 4;energy+=x*x;peak=std::fmax(peak,fabs(x));}
  if(energy==0)return 5;
  printf("hat %d %d %d %d rms %.7f peak %.7f damp %.7f\n",f,tone,noise,decay,sqrt(energy/48000),peak,h.noise_coloration_svf_.damp_);
 }
 // Impact changes the first milliseconds; same engine/seed and decayed tail.
 for(float accent:{0.f,1.f}){daisysp::SyntheticSnareDrum s;s.Init(48000);s.SetAccent(accent);srand(123);s.Trig();double start=0,tail=0;for(int i=0;i<24000;i++){float x=s.Process();if(i<480)start+=x*x;if(i>12000)tail+=x*x;}printf("impact %.1f first10ms %.8f tail %.8f\n",accent,start,tail);}
 return 0;
}
