#pragma once
static const unsigned char snare_ui_defaults[7]={10,45,50,65,70,0,0}; /* P10: 909 Snare (Tone 50) */
static const char *const snare_labels[7]={"Tune","Decay","Tone","Impact","Snappy","",""};
static const unsigned char hat_ui_defaults[7]={10,70,65,65,30,0,0};
static const char *const hat_labels[7]={"Tune","Decay","Tone","Impact","Noise","",""};
/* CH12: Clap (engine 7) and Tom / FM perc (engine 9). Engine ids follow the
 * carrier lengths 144019 + id - 1; even ids stay reserved (K8 analog variants). */
static const unsigned char clap_ui_defaults[7]={40,40,50,65,40,0,0};
static const char *const clap_labels[7]={"Tune","Decay","Tone","Impact","Spread","",""};
static const unsigned char tom_ui_defaults[7]={86,50,40,65,40,30,10}; /* Tune shares the Kick's 25..180 range (Kick lock kinds); 86 = 180 Hz */
static const char *const tom_labels[7]={"Tune","Decay","Tone","Impact","Sweep","Sweep Dec","Dirt"};
static const unsigned char sub_ui_defaults[7]={20,50,35,60,25,35,45};
static const char *const sub_labels[7]={"Shape","Osc2 Semi","Fat","Cutoff","Resonance","Env Amt","Env Decay"};
/* A1: engine 13 marks an Analog Wavetable track (values[0] = Sync, 0 off). */
static const unsigned char analog_defaults[7]={0,0,0,0,0,0,0};
static const unsigned char *drum_defaults(unsigned m){if(m==13)return analog_defaults;return m==11?sub_ui_defaults:m==3?snare_ui_defaults:m==5?hat_ui_defaults:m==7?clap_ui_defaults:m==9?tom_ui_defaults:kick_defaults;}
static const char *drum_name(unsigned m){return m==11?"Subtractive":m==3?"Snare":m==5?"HiHat":m==7?"Clap":m==9?"Tom":"Kick";}
/* Knobs per engine (Kick's Click is the separate eighth control). */
static unsigned drum_count(unsigned m){return m==1||m==9||m==11?7u:5u;}
/* Step-lock kinds are per family: Tom locks use the Kick kinds, Clap the Snare kinds. */
static unsigned drum_family(unsigned m){return m==9?1u:m==7?3u:m;}
/* Tune readout in Hz (integers only, for the UI). 2^f ~ 1 + f(0.6565 + 0.3435f). */
static unsigned drum_exp2(unsigned base,unsigned num,unsigned den){unsigned whole=num/den,f=(num%den)*1024u/den;return ((base<<whole)*(1024u+(f*(672u+(352u*f>>10))>>10)))>>10;}
static unsigned drum_tune_hz(unsigned m,unsigned v){return m==3?drum_exp2(140,v,50):m==5?100+v*107/10:m==7?drum_exp2(400,v*3,100):m==9?drum_exp2(40,v<25?0:v-25,28):v;}
/* P7: the firmware's own folder "Drum Synths" (SD root) holds Kick.wav,
 * Snare.wav, HiHat.wav, Clap.wav and Tom.wav, chosen in the native browser. */
static unsigned drum_folder_name(const char *dir,const char *base){
 const char *want="drum synths";unsigned i=0;for(;want[i];i++){unsigned c=(unsigned char)dir[i];if(c>='A'&&c<='Z')c+=32;if(c!=(unsigned char)want[i])return 0;}
 if(dir+i!=base-1)return 0;
 const char *names[]={"kick.wav","snare.wav","hihat.wav","clap.wav","tom.wav"};const unsigned models[]={1,3,5,7,9};
 for(unsigned k=0;k<5;k++){unsigned j=0;for(;names[k][j]&&base[j];j++){unsigned c=(unsigned char)base[j];if(c>='A'&&c<='Z')c+=32;if(c!=(unsigned char)names[k][j])break;}if(!names[k][j]&&!base[j])return models[k];}
 return 0;
}
static unsigned drum_path(const char*s){
 const char *base=s,*dir=s;unsigned n=0;for(;n<256&&s[n];n++)if(s[n]=='/'||s[n]=='\\'){dir=base;base=s+n+1;}if(n==256)return 0;
 {unsigned m=drum_folder_name(dir,base);if(m)return m;}
 const char *names[]={"bento_kick.wav","bento_kick_k1.wav","bento_kick_k2.wav","bento_synth_snare.wav","bento_synth_hihat.wav","bento_synth_clap.wav","bento_synth_tom.wav","bento_synth_subtractive.wav"};
 for(unsigned k=0;k<8;k++){unsigned i=0;for(;names[k][i]&&base[i];i++){unsigned c=(unsigned char)base[i];if(c>='A'&&c<='Z')c+=32;if(c!=(unsigned char)names[k][i])break;}if(!names[k][i]&&!base[i])return k==7?11:k==6?9:k==5?7:k==4?5:k==3?3:1;}return 0;
}
