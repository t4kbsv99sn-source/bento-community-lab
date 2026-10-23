/* BENTO_MOD L7: lossless two-lock coding in the existing native +20 word. */
typedef unsigned int u32;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u8*)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u8*)(p)+(o)))
#define H(p,o) (*(volatile unsigned short *)((u8*)(p)+(o)))
#define FN(a,t) ((t)((a)|1u))
#define LOCK_TAG 0x51000000u
#define LOCK_PAIR_COUNT 1519176901u
static u32 value_count(u32 k){return k==0?1:k==1?1081:k==2?48001:(k==3||k==4)?2001:k<=11?1001:k==12?156:k<=29?101:0;}
static u32 lock_kind(u32 w){
 u32 k=(w>>16)&255,v=w&65535;
 return (w&0xff000000u)==LOCK_TAG && k && k<=29 && v<value_count(k)?k:0;
}
static u32 synth_model(u32 k){return k>=12&&k<=19?1:k>=20&&k<=24?3:k>=25&&k<=29?5:0;}
static u32 synth_index(u32 k){return k-(k<=19?12:k<=24?20:25);}
static u32 native_key(u32 k){static const u32 keys[]={0,2,3,4,0x32,0x33,0x1e,0x1f,0x20,0x21,0x36,0x37};static const u32 synthkeys[]={0x1a0,0x1a1,0x1a2,0x1a4,0x1a5,0x1a6,0x1a9,0x1b0};return k<=11?keys[k]:k<=29?synthkeys[synth_index(k)]:0;}
static int decode_value(u32 w){u32 k=lock_kind(w),v=w&65535;return k==1?(int)v*100-96000:k==2?(int)v-24000:k==12?(int)v+25:(int)v-((k==3||k==4)?1000:0);}
static u32 encode_value(u32 k,int v){
 int lo=k==1?-96000:k==2?-24000:(k==3||k==4)?-1000:k==12?25:0,hi=k==1?12000:k==2?24000:k==12?180:k>11?100:1000;
 if(!k || k>29)return 0;if(v<lo)v=lo;if(v>hi)v=hi;
 return LOCK_TAG|(k<<16)|(u32)(k==1?(v+96000)/100:k==2?v+24000:k==12?v-25:v+((k==3||k==4)?1000:0));
}
/* K16: legacy pair order is frozen. Synth pairs append after all legacy pairs.
 * Enumerate all ordered, distinct target pairs and their full value ranges.
 * 1,290,761,893 combinations fit in 31 bits. Bit 31 tags v2; v1 stays exact.
 * No pointers, mutable dictionary, quantization loss or new native note size. */
/* Skip complete target rows rather than scanning every value-pair group. */
static u32 row_count(u32 a,u32 pass){
 u32 sum=pass?(a<=11?1873u:61965u):60092u;
 if(a && (!pass || a>11))sum-=value_count(a);
 return value_count(a)*sum;
}
static u32 lock_slot(u32 packed,u32 slot){
 if(!(packed&0x80000000u))return slot==0 && lock_kind(packed)?packed:0;
 u32 code=packed&0x7fffffffu;if(code>=LOCK_PAIR_COUNT)return 0;
 for(u32 pass=0;pass<2;pass++)for(u32 a=0;a<=(pass?29u:11u);a++){
  u32 row=row_count(a,pass);if(code>=row){code-=row;continue;}
  for(u32 b=pass&&a<=11?12:0;b<=(pass?29u:11u);b++){
   if(a && a==b)continue;u32 n=value_count(a)*value_count(b);
   if(code>=n){code-=n;continue;}
   u32 k=slot?b:a,v=slot?code%value_count(b):code/value_count(b);
   return k?LOCK_TAG|(k<<16)|v:0;
  }
 }return 0;
}
static u32 lock_pair(u32 first,u32 second){
 u32 a=lock_kind(first),b=lock_kind(second);if(a && a==b)return 0xffffffffu;
 if(!b)return a?first:0;
 u32 code=0;
 for(u32 pass=0;pass<2;pass++)for(u32 i=0;i<=(pass?29u:11u);i++){
  if(i!=a || ((a>11 || b>11)!=pass)){code+=row_count(i,pass);continue;}
  for(u32 j=pass&&i<=11?12:0;j<=(pass?29u:11u);j++){
   if(i && i==j)continue;if(j==b)return 0x80000000u|code;
   code+=value_count(i)*value_count(j);
  }
 }return 0xffffffffu;
}
static u32 pack_locks(u32 first,u32 second){
 u32 base=lock_pair(first,second);if(base==0xffffffffu || !(base&0x80000000u))return base;
 return base+(lock_kind(first)?(first&65535u)*value_count(lock_kind(second)):0)+(second&65535u);
}
static int has_locks(u32 w){return lock_slot(w,0)!=0 || lock_slot(w,1)!=0;}
