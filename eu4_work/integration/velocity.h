#pragma once
/* Pattern-hit rank, independent of step gaps and skipped probability hits. */
static unsigned int vel_hash(unsigned int x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;return x^(x>>16);}
static unsigned int velocity_value(unsigned int base,unsigned int mode,unsigned int depth,unsigned int hit,unsigned int hits,unsigned int step,unsigned int seed){
 if(base<1)base=100;if(base>127)base=127;if(!mode||!depth)return base;if(depth>100)depth=100;
 int shape=0;
 if(mode==1)shape=hit%2?-100:100;
 else if(mode==2||mode==3)shape=hit%(mode==2?3:4)?-100:100;
 else if(mode==4)shape=step%4?-100:100;
 else if(mode==5||mode==6){if(hits)hit%=hits;shape=hits>1?(int)(hit*200/(hits-1))-100:0;if(mode==6)shape=-shape;}
 else if(mode==7){if(hits)hit%=hits;unsigned int phase=hits>1?hit*200/hits:50;shape=phase<=100?(int)phase*2-100:300-(int)phase*2;}
 else if(mode==8)shape=(int)(vel_hash(seed^hit)%61)-30;
 else if(mode==9)shape=vel_hash(seed^hit)%4?-40:100;
 int range=shape>=0?127-(int)base:(int)base-1;int result=(int)base+range*shape*(int)depth/10000;
 return result<1?1:result>127?127:(unsigned int)result;
}
