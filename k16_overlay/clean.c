/* K13: direct draw filters for the lower native kick editor. */
typedef unsigned int u32;typedef unsigned char u8;
#define W(p,o) (*(volatile u32*)((u8*)(p)+(o)))
#define B(p,o) (*(volatile u8*)((u8*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define D ((volatile u32*)0x24043d40u)
#define MAGIC 0x33314455u
static int supported(void *v){return FN(0x081bb400,int(*)(void*))(v);}
/* Follow actual widget parents, never a remembered page pointer. Bounded depth.
 * The two control rows occupy +38..4828; the lower sampler uses later members. */
static void *target(void *widget){
 void *p=(void*)W(widget,0x2c);
 for(u32 depth=0;p && depth<6;depth++,p=(void*)W(p,0x2c)){
  if(W(p,0)!=0x0819e624u)continue;
  u32 off=(u32)widget-(u32)p;
  if(off>=0x8790u)return 0;
  int lower=off>=0x710cu && !(off>=0x80b4u && off<0x8124u);
  int third=off>=0x4828u && off<0x6c20u && supported(p)!=1;
  int tab=(off>=0x6d44u && off<0x6db4u)||(off>=0x6ef0u && off<0x6fbcu);
  return (lower||third||tab)&&supported(p)?p:0;
 }
 return 0;
}
static void draw(void *w,void *paint,u32 kind){
 void *v=target(w);
 if(!v){FN(0x081bd800u+kind*32u,void(*)(void*,void*))(w,paint);return;}
 if(D[0]!=MAGIC || D[1]!=(u32)v){D[0]=MAGIC;D[1]=(u32)v;D[2]=0;}
 u32 before=D[2];D[2]=before|(1u<<kind);

 if(paint && (B(paint,0)||B(paint,1)) && W(paint,4) && W(w,12)>0 && W(w,12)<=1280 && W(w,16)>0 && W(w,16)<=800)
  FN(0x08166e9e,void(*)(void*,u32,void*))((u8*)w+4,0xf1,(void*)W(paint,4));
}
__attribute__((used)) void clean_refresh(void *v){FN(0x081bb040,void(*)(void*))(v);}
__attribute__((used)) void wave_paint(void*w,void*p){draw(w,p,0);}
__attribute__((used)) void envelope_paint(void*w,void*p){draw(w,p,1);}
__attribute__((used)) void lfo_paint(void*w,void*p){draw(w,p,2);}
__attribute__((used)) void button_paint(void*w,void*p){draw(w,p,3);}
__attribute__((used)) void label_paint(void*w,void*p){draw(w,p,4);}
__attribute__((used)) void rect_paint(void*w,void*p){draw(w,p,5);}
