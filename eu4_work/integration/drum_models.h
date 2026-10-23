#pragma once
static const unsigned char snare_ui_defaults[7]={10,45,10,65,70,0,0};
static const char *const snare_labels[7]={"Tune","Decay","FM","Impact","Snappy","",""};
static const unsigned char hat_ui_defaults[7]={10,70,65,65,30,0,0};
static const char *const hat_labels[7]={"Tune","Decay","Tone","Impact","Noise","",""};
static const unsigned char *drum_defaults(unsigned m){return m==3?snare_ui_defaults:m==5?hat_ui_defaults:kick_defaults;}
static const char *drum_name(unsigned m){return m==3?"Snare":m==5?"HiHat":"Kick";}
static unsigned drum_path(const char*s){
 const char *base=s;unsigned n=0;for(;n<256&&s[n];n++)if(s[n]=='/'||s[n]=='\\')base=s+n+1;if(n==256)return 0;
 const char *names[]={"bento_kick.wav","bento_kick_k1.wav","bento_kick_k2.wav","bento_synth_snare.wav","bento_synth_hihat.wav"};
 for(unsigned k=0;k<5;k++){unsigned i=0;for(;names[k][i]&&base[i];i++){unsigned c=(unsigned char)base[i];if(c>='A'&&c<='Z')c+=32;if(c!=(unsigned char)names[k][i])break;}if(!names[k][i]&&!base[i])return k==4?5:k==3?3:1;}return 0;
}
