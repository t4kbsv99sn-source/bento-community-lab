/* Host audio sweeps of the exact S1 voice, with DaisySP filters. */
#include "drums/subtractive.h"
#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
static_assert(sizeof(bento::Subtractive)<=288,"Existing voice pool exceeded");
int main(int argc,char **argv){
 if(argc>1 && !strcmp(argv[1],"render")){
  int patch=argc>2?atoi(argv[2]):0;
  float v[8]={20,50,35,60,25,35,45,0};
  if(patch==1){v[0]=0;v[1]=75;v[3]=45;v[4]=65;v[5]=25;v[6]=65;v[7]=65;}
  if(patch==2){v[0]=75;v[2]=85;v[3]=65;v[4]=35;v[5]=10;v[6]=70;}
  for(unsigned note=0;note<8;note++){
   bento::Subtractive s;s.Init(48000);
   const int notes[]={0,0,7,3,0,10,7,-5};
   float ratio=powf(2.f,notes[note]/12.f);
   for(unsigned b=0;b<375;b++){
    auto c=s.Prepare(v,ratio,64);
    for(unsigned j=0;j<64;j++){
     unsigned frame=b*64+j;
     float amp=fminf(1.f,frame/120.f)*fminf(1.f,(24000-frame)/2400.f);
     float x=s.Process(c)*amp*.6f;
     fwrite(&x,4,1,stdout);
    }
   }
  }
  return 0;
 }
 unsigned cases=0;double worst=0;
 for(unsigned mask=0;mask<256;mask++)for(float ratio:{.0625f,1.f,8.f}){
  bento::Subtractive s;s.Init(48000);float v[8];
  for(unsigned j=0;j<8;j++)v[j]=(mask&(1u<<j))?100:0;
  double energy=0;
  for(unsigned b=0;b<48;b++){
   auto c=s.Prepare(v,ratio,64);
   for(unsigned j=0;j<64;j++){
    float x=s.Process(c);
    if(!std::isfinite(x)||fabs(x)>1.500001f){fprintf(stderr,"bad audio mask=%u ratio=%f\n",mask,ratio);return 1;}
    energy+=x*x;worst=fmax(worst,fabs(x));
   }
  }
  if(energy<1e-10){fprintf(stderr,"silent mask=%u ratio=%f\n",mask,ratio);return 2;}
  cases++;
 }
 printf("PASS %u extreme parameter/pitch combinations; size %zu bytes; peak %.6f\n",cases,sizeof(bento::Subtractive),worst);
}
