/* Bento Playground / Measure study. Original procedural artwork. GPL-3.0-or-later. */
(function(root){
'use strict';
const T={w:1280,h:480,bg:'#191b1c',surface:'#202324',raised:'#292d2e',line:'#3b4142',muted:'#a0aaa9',text:'#e9eeea',faint:'#626c6c',track:'#e9aa73',record:'#f27979',white:'#ffffff',font:'DejaVu Sans, sans-serif'};
const COLORS=['#e9aa73','#8bbbd1','#c5a4d0','#9fc5a8','#d58f9a','#d3c57e','#87c4bc','#a9afd8'];
const NAMES=['Drums','Bass','Glass','Texture','Percussion','Keys','Atmosphere','External'];
const TYPES=['One-shots','Analog','Wavetable','Granular','One-shots','Multisample','Loop','External'];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const rect=(x,y,w,h,c,more='')=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${c}" ${more}/>`;
const line=(x,y,x2,y2,c=T.line,w=1,more='')=>`<path d="M${x} ${y}L${x2} ${y2}" fill="none" stroke="${c}" stroke-width="${w}" ${more}/>`;
const text=(x,y,s,size=20,c=T.text,more='')=>`<text x="${x}" y="${y}" fill="${c}" font-size="${size}" ${more}>${esc(s)}</text>`;
const path=(d,c,w=2,more='')=>`<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" ${more}/>`;
const dot=(x,y,r,c)=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;
function icon(name,x,y,c=T.text){
 let p='';
 if(name==='lock')p=rect(x+3,y+8,12,9,'none',`stroke="${c}" stroke-width="2"`)+path(`M${x+6} ${y+8}V${y+4}H${x+12}V${y+8}`,c);
 if(name==='condition')p=path(`M${x+2} ${y+15}V${y+3}H${x+16}M${x+9} ${y+3}V${y+15}`,c)+dot(x+16,y+15,2,c);
 if(name==='auto')p=path(`M${x} ${y+14}L${x+5} ${y+4}L${x+12} ${y+12}L${x+19} ${y+2}`,c);
 if(name==='mod')p=line(x,y+8,x+19,y+8,c)+line(x,y+3,x,y+13,c)+line(x+19,y+3,x+19,y+13,c)+dot(x+9,y+8,3,c);
 if(name==='menu')p=[0,7,14].map(d=>line(x,y+d,x+29,y+d,c,2)).join('');
 return p;
}
function svg(body,label){return `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="480" viewBox="0 0 1280 480" role="img" aria-label="${esc(label)}"><style>text{font-family:${T.font};font-variant-numeric:tabular-nums} [data-action]{cursor:pointer} [data-action]:focus{outline:none;filter:brightness(1.25)}</style>${rect(0,0,1280,480,T.bg)}${body}</svg>`;}
function hit(action,body,label){return `<g data-action="${action}" tabindex="0" role="button" aria-label="${esc(label||action)}">${body}</g>`;}
function param(i,name,val,marked=false){let x=6+i*159;return hit('encoder:'+i,rect(x,0,157,72,T.bg)+text(x+10,23,name,16,T.muted)+text(x+10,55,val,25,marked?T.track:T.text)+line(x+10,68,x+145,68,T.line)+ (marked?line(x+10,68,x+63,68,T.track,2):''),name+' '+val);}
function nav(page,s){let b=line(0,428,1280,428,T.line);b+=text(15,460,s.trackName||'1 · Drums',19,T.track);
 const pad=String((s.euRow||0)+1).padStart(2,'0')+' '+['Kick','Snare','Hi-hat','Clap','Tom','Shaker','Rim','Perc'][s.euRow||0];
 const names=page==='seq'?[pad,'Euclidean','Step','Sequence','Select','Clear']:page==='auto'?['','Event','Sequence','Automation','Clear Auto','']:['','','','','',''];
 names.forEach((n,i)=>{if(!n)return;let x=163+i*159;let active=(page==='seq'&&i===2)||(page==='auto'&&i===3);let action=i===4||i===5; b+=hit('nav:'+n,rect(x,434,157,40,active?T.surface:T.bg)+(active?line(x+5,433,x+152,433,T.text,3)+line(x+5,474,x+152,474,T.text,2):'')+(action?rect(x+3,434,151,39,'none',`stroke="${T.line}" rx="3"`):'')+text(x+78.5,460,n,20,active?T.text:T.muted,'text-anchor="middle"'),n);});
 b+=text(1139,448,s.play?'1:3':'1:1',16,T.text)+text(1139,469,'120',16,T.muted)+hit('menu',rect(1218,432,55,44,T.bg)+icon('menu',1230,444),'Menu');return b;
}
function defaultState(){return {page:'seq',seqKind:'drum',trackName:'1 · Drums',track:T.track,selected:12,play:false,phase:0.38,variant:'bar',selectMode:false,lane:0,length:8,clip:2,record:false,armed:false,menu:false,macro:[.62,.37,.48,.26,.42,.58,.31,.66],points:[[0,.22],[.12,.22],[.23,.66],[.36,.39],[.48,.8],[.62,.47],[.75,.28],[.87,.62],[1,.62]],steps:Array.from({length:32},(_,i)=>({on:[0,4,8,10,12,16,20,24,27,28,30].includes(i),velocity:[108,76,92,64,116,88,54,100][i%8],prob:i===10?60:100,filterLock:[18,35,63,80,58,44,92,27][i%8],sendLock:[65,12,40,8,32,85,20,54][i%8],locks:[4,10,12,20,28,30].includes(i),condition:i===28?'2:4':''}))};}
function seq(s){const e=s.steps[s.selected],target=s.lockTarget||'filter',lv=q=>target==='filter'?q.filterLock:q.sendLock;let b='';
 const val=q=>q===undefined?'—':(0.02*Math.pow(1000,q/100)).toFixed(2)+' kHz';
 ['Pad','Velocity','Prob','Offset','','Locks when','Lock Filter','Lock 2 Send'].forEach((v,i)=>b+=param(i,v,[String((s.euRow||0)+1).padStart(2,'0')+' '+['Kick','Snare','Hi-hat','Clap','Tom','Shaker','Rim','Perc'][s.euRow||0],String(e.velocity),e.prob+'%','0 ticks','',e.condition||'Always',e.locks?val(e.filterLock):'—',e.locks?e.sendLock+'%':'—'][i],i>5&&e.locks));
 // Keep native 157x87 hit rectangles. Original inset geometry, Opal-informed data separation.
 s.steps.forEach((e,i)=>{const col=i%8,row=Math.floor(i/8),x=6+col*159,y=74+row*89,sel=i===s.selected,head=s.play&&i===Math.floor(s.phase*32),locked=e.locks&&e.on;
 let cell=rect(x,y,157,87,T.bg);if(col===0||col===4)cell+=line(x+2,y+8,x+2,y+79,T.line,1);
 cell+=text(x+14,y+21,String(i+1).padStart(2,'0'),15,sel?T.text:T.muted);
 cell+=`<circle cx="${x+76}" cy="${y+7}" r="3.5" fill="${head?T.text:T.bg}" stroke="${head?T.text:T.faint}" stroke-width="1.5"/>`;
 if(e.prob<100)cell+=text(x+141,y+21,e.prob+'%',14,T.muted,'text-anchor="end"');
 const bx=x+48,by=y+17,bw=56,bh=56;
 cell+=rect(bx,by,bw,bh,T.bg,`rx="4" stroke="${e.on?T.track:T.faint}" stroke-width="${e.on?2:1}"`);
 if(e.on){const h=Math.max(2,(bh-8)*e.velocity/127);cell+=rect(bx+4,by+bh-4-h,bw-8,h,T.track,'rx="1"');}
 if(sel)cell+=rect(bx-4,by-4,bw+8,bh+8,'none',`rx="6" stroke="${T.text}" stroke-width="1.5"`);
 if(e.condition)cell+=text(x+141,y+54,e.condition,13,T.muted,'text-anchor="end"');
 
 // A full-width thin rail is always distinct from the trigger/velocity body.
 cell+=rect(bx,y+78,bw,2,T.raised)+rect(bx,y+84,bw,2,T.raised);
 if(locked){cell+=rect(bx,y+78,Math.max(2,bw*e.filterLock/100),2,T.track);cell+=rect(bx,y+84,Math.max(2,bw*e.sendLock/100),2,T.track);}
 if(head)cell+=line(bx,by-3,bx+bw,by-3,T.text,2);
 b+=hit('step:'+i,cell,'Step '+(i+1)+(e.on?', on':', off')+(sel?', selected':'')+(locked?', '+target+' lock '+lv(e)+'%':''));});
 return b+nav('seq',s);
}
function automation(s){let b='';['Lane','Value','Position','Motion length','Clip length','Interpolation','Capture','State'].forEach((v,i)=>b+=param(i,v,[String.fromCharCode(65+s.lane),'62%','3:1',s.length+' bars',s.clip+' bars','Linear','Overdub',s.record?'Recording':s.armed?'Armed':'Playing'][i],i===3));
 b+=text(24,104,'Clip 01  /  '+String.fromCharCode(65+s.lane)+' → Filter',20,T.text)+text(1256,104,'MOTION  '+s.length+' BARS',16,s.record?T.record:T.track,'text-anchor="end"');
 const x=92,y=171,w=1158,h=192,px=t=>x+t*w,py=v=>y+(1-v)*h;
 // Separate clip and motion rails share time; lengths remain explicitly labelled.
 for(let i=0;i<s.length;i++){let xx=px(i/s.length);b+=line(xx,143,xx,153,T.faint)+text(xx+5,140,i+1,14,T.muted);if(i%s.clip===0)b+=line(xx,119,px(Math.min(s.length,i+s.clip)/s.length)-4,119,T.faint,2);}
 b+=text(24,125,'CLIP',12,T.muted)+text(24,151,'LOOP',12,T.track)+line(x,153,x+w,153,T.track,2)+line(x,147,x,159,T.track,2)+line(x+w,147,x+w,159,T.track,2);
 [0,.25,.5,.75,1].forEach(v=>b+=line(x,py(v),x+w,py(v),T.line,1)+text(75,py(v)+5,Math.round(v*100),13,T.muted,'text-anchor="end"'));
 for(let i=0;i<=s.length;i++)b+=line(px(i/s.length),y,px(i/s.length),y+h,T.line);
 const d=s.points.map((p,i)=>(i?'L':'M')+px(p[0]).toFixed(1)+' '+py(p[1]).toFixed(1)).join('');b+=`<defs><clipPath id="plotClip">${rect(x-4,y-4,w+8,h+8,'white')}</clipPath></defs><g clip-path="url(#plotClip)">`+path(d,T.track,2);
 s.points.forEach((p,i)=>{if(p[0]<=1)b+=dot(px(p[0]),py(p[1]),3,T.track)+`<circle data-point="${i}" cx="${px(p[0])}" cy="${py(p[1])}" r="15" fill="transparent" style="cursor:ns-resize"/>`;});b+='</g>';
 b+=line(px(s.phase),y-5,px(s.phase),y+h,s.record?T.record:T.text,2)+dot(px(s.phase),y-9,4,s.record?T.record:T.text);
 for(let i=0;i<4;i++){let xx=92+i*96;b+=hit('lane:'+i,rect(xx,382,80,32,i===s.lane?T.raised:T.bg)+text(xx+40,405,String.fromCharCode(65+i),18,i===s.lane?T.text:T.muted,'text-anchor="middle"')+(i===s.lane?line(xx,415,xx+80,415,T.track,2):''),'Lane '+String.fromCharCode(65+i));}
 b+=text(522,405,s.record?'● RECORDING · release REC to finish':s.armed?'ARMED · turn a routed parameter':'Clip-owned · independent loop',17,s.record?T.record:T.muted);
 b+=text(1255,405,'BAR '+(1+Math.floor(s.phase*s.length))+' / '+s.length,17,T.text,'text-anchor="end"');return b+nav('auto',s);
}
const macros=[['Open','Filter',220,14000,'Hz'],['Grain','Overdrive',0,85,'%'],['Space','Reverb send',0,65,'%'],['Echo','Delay send',0,75,'%'],['Weight','Level',-12,0,'dB'],['Spread','Pan',-70,70,'%'],['Shape','Decay',60,900,'ms'],['Air','Resonance',0,70,'%']];
function macroGraph(i,x,y,w,h,v){let b='',col=T.track;
 if(i===0){let d='';for(let k=0;k<=40;k++){let t=k/40,z=1/(1+Math.pow(t/(.14+.7*v),6));d+=(k?'L':'M')+(x+t*w)+' '+(y+h-z*h*.8);}b+=path(d,col,2);}
 else if(i===7){let d='';for(let k=0;k<=40;k++){let t=k/40,z=.35+.55*v*Math.exp(-Math.pow((t-.58)/.12,2));d+=(k?'L':'M')+(x+t*w)+' '+(y+h-z*h);}b+=path(d,col,2);}
 else if(i===1){let d='';for(let k=0;k<=40;k++){let t=k/40,z=Math.tanh((t*2-1)*(1+v*5));d+=(k?'L':'M')+(x+t*w)+' '+(y+h/2-z*h*.44);}b+=path(d,col,2);}
 else if(i===2||i===3){for(let k=0;k<9;k++){let ht=h*v*Math.pow(i===2?.82:.68,k);b+=line(x+k*w/9,y+h,x+k*w/9,y+h-ht,col,2);}}
 else if(i===4){b+=line(x,y+h,x+w,y+h,T.line)+rect(x,y+h*(1-v),w,h*v,col);}
 else if(i===5){b+=line(x,y+h/2,x+w,y+h/2,T.line)+line(x+w/2,y+8,x+w/2,y+h-8,T.muted)+dot(x+v*w,y+h/2,5,col);}
 else {b+=path(`M${x} ${y+h}L${x+12} ${y+4}L${x+22+v*(w-25)} ${y+h}`,col,2);}
 return b;
}
const MAPS=[[[3,'Filter',20,85],[3,'Resonance',12,44],[4,'Filter',80,25]],[[1,'Reverb send',0,65],[2,'Reverb send',10,55],[4,'Delay send',0,50],[5,'Reverb send',5,75]],[[0,'P2 Decay',15,80],[0,'P3 Decay',10,75],[0,'P1 Click',10,90]],[[0,'P1 Drive',0,65],[0,'Clipper',10,50]],[[3,'Tune',25,75]],[[3,'Env 1 Decay',10,85],[4,'Grain size',70,15],[3,'LFO rate',5,95],[0,'P3 Tune',40,80],[4,'Pan',80,20]],[[4,'Pan',0,55],[5,'Pan',100,45]],[]];
function macro(s){let b='',labels=['Cutoff','Space','Decay','Drive','Pitch','Density','Mix','Empty'];for(let i=0;i<8;i++){let x=6+i*159,v=s.macro[i],rows=MAPS[i],sel=i===(s.selectedMacro||0);b+=hit('macro:'+i,rect(x+4,8,149,406,sel?T.surface:T.bg)+text(x+14,29,'M'+(i+1)+' '+labels[i],16,rows.length?T.text:T.faint)+text(x+14,62,rows.length?Math.round(v*127):'—',27,rows.length?T.text:T.faint)+(rows.length?line(x+14,77,x+143,77,T.line)+line(x+14+v*129,73,x+14+v*129,81,T.text,2):'')+text(x+143,62,rows.length?rows.length+'×':'',14,T.muted,'text-anchor="end"')+line(x+4,90,x+153,90,sel?T.text:T.line,sel?2:1), 'Macro '+(i+1)+' '+labels[i]);
 rows.forEach((m,k)=>{let y=109+k*58,c=COLORS[m[0]],value=m[2]+v*(m[3]-m[2]),xx=t=>x+14+t*1.29;
 let row=text(x+14,y+7,'T'+(m[0]+1),12,c)+text(x+40,y+7,m[1],12,T.muted)+text(x+143,y+27,Math.round(value),17,T.text,'text-anchor="end"')+text(x+14,y+27,sel?m[2]+' → '+m[3]:'',11,T.muted)+line(xx(0),y+38,xx(100),y+38,T.line)+line(xx(m[2]),y+38,xx(m[3]),y+38,T.faint,3)+line(xx(m[2]),y+38,xx(value),y+38,c,3)+line(xx(m[2]),y+34,xx(m[2]),y+42,T.muted)+line(xx(m[3]),y+34,xx(m[3]),y+42,T.muted)+line(xx(value),y+32,xx(value),y+44,T.text,2);
 b+=hit('macro:'+i,rect(x+5,y-6,147,56,'transparent')+row,'Macro '+(i+1)+' target '+m[1]);});if(!rows.length)b+=text(x+78,235,'Unassigned',14,T.faint,'text-anchor="middle"');if(sel)b+=line(x+4,412,x+153,412,T.text,2);}
 return b+line(0,428,1280,428,T.line)+text(20,460,'PERFORMANCE',18,T.text)+text(330,460,'MACROS / COLUMN STUDY',16,T.muted)+text(850,460,'MACRO 0–127 · TARGET %',14,T.muted)+text(1140,460,'120',18,T.muted)+icon('menu',1230,444);}
function performance(s){let b='';const rows=[['Tempo & Key',['BPM','Tap Tempo','Swing','Root','Scale'],['120','Tap','54%','D','Dorian']],['Pads / Track 1',['Fixed Vel','Velocity','Octave'],['On','100','0']],['Chord / Dm7',['Chord','Type','Voicing','Inversion'],['On','Diatonic 7','Smooth','0']]];
 rows.forEach((r,j)=>{let y=j*139;b+=text(16,y+26,r[0],17,T.muted)+line(16,y+37,1264,y+37,T.line);r[1].forEach((name,i)=>{let x=6+i*159;b+=hit('perf:'+j+':'+i,rect(x,y+43,157,88,T.bg)+text(x+10,y+65,name,16,T.muted)+text(x+10,y+101,r[2][i],24,T.text)+line(x+10,y+120,x+145,y+120,T.line),name);});
 if(j===0){for(let k=0;k<8;k++)b+=line(875+k*48,y+99,875+k*48,y+99-(k%2?25:42),k%2?T.faint:T.track,2);}
 if(j===1){b+=line(875,y+99,1211,y+99,T.line)+line(875+100/127*336,y+65,875+100/127*336,y+112,T.track,3)+text(1211,y+64,'100 / 127',15,T.muted,'text-anchor="end"');}
 if(j===2){[0,3,7,10].forEach((n,i)=>b+=line(875+i*94,y+110-n*3,910+i*94,y+110-n*3,T.track,3));b+=text(875,y+64,'D   F   A   C',15,T.muted);}
 });return b+nav('perf',s);
}
function outputs(s){let b='';['Phones','Out 3','Out 2','Out 1','Metronome','','','Main'].forEach((n,i)=>{if(n)b+=param(i,n,['−12 dB','0 dB','0 dB','−3 dB','−18 dB','','','−1 dB'][i]).replace('encoder:'+i,'outputs');});return b;}
function bottom(s,mode){let b=line(0,428,1280,428,T.line)+text(18,459,mode==='tracks'?'Night studies':'Mixer',19,T.text);
 if(mode==='tracks'){b+=text(340,459,'D Dorian',18,T.muted)+text(570,459,'Sample pool  38 / 128',16,T.muted);}
 else ['Level','Mute','Delay','Reverb'].forEach((n,i)=>{let x=322+i*159;b+=hit('mixmode:'+n,rect(x,433,157,41,T.bg)+(n===(s.mixMode||'Level')?line(x+8,433,x+149,433,T.text,3):'')+text(x+78,460,n,20,n===(s.mixMode||'Level')?T.text:T.muted,'text-anchor="middle"'),n);});
 return b+text(1138,449,'1:3',16)+text(1138,470,'120',16,T.muted)+hit('menu',rect(1218,432,55,44,T.bg)+icon('menu',1230,444),'Menu');}
function trackIcon(i,x,y,c){let b='';if(i===0||i===4){for(let k=0;k<4;k++)b+=rect(x+k%2*16,y+Math.floor(k/2)*16,10,10,'none',`stroke="${c}" stroke-width="1.5"`);}else if(i===7)b+=path(`M${x} ${y+14}H${x+27}M${x+19} ${y+6}L${x+27} ${y+14}L${x+19} ${y+22}`,c,2);else{let d='';for(let k=0;k<=24;k++)d+=(k?'L':'M')+(x+k*1.2)+' '+(y+14+Math.sin(k/24*Math.PI*2)*(i===3?7:12));b+=path(d,c,1.5);}return b;}
function tracks(s){let b=outputs(s);for(let i=0;i<8;i++){let x=6+i*159,c=COLORS[i],sel=i===(s.selectedTrack||0),muted=!!(s.mutes&&s.mutes[i]);let cell=rect(x+4,89,149,319,sel?T.surface:T.bg)+line(x+14,90,x+139,90,c,2)+text(x+14,119,String(i+1).padStart(2,'0'),16,c)+trackIcon(i,x+60,146,c)+text(x+78,212,NAMES[i],19,muted?T.muted:T.text,'text-anchor="middle"')+text(x+78,239,TYPES[i],14,T.muted,'text-anchor="middle"');
 for(let k=0;k<2;k++){let w=90*(.45+(i%3)*.16-k*.08)*(s.play?.8+.2*Math.sin(s.phase*25+i):.65);cell+=rect(x+33,282+k*8,92,3,T.raised)+rect(x+33,282+k*8,muted?0:w,3,c);}
 cell+=text(x+78,332,muted?'MUTED':'Track '+(i+1),14,muted?T.text:T.muted,'text-anchor="middle"');if(sel)cell+=path(`M${x+4} 108V89H${x+22}M${x+134} 89H${x+153}V108M${x+4} 389V408H${x+22}M${x+134} 408H${x+153}V389`,T.text,1.5);b+=hit('track:'+i,cell,'Select Track '+(i+1)+' '+NAMES[i]);}return b+bottom(s,'tracks');}
function mixer(s){let b=outputs(s),mode=s.mixMode||'Level';b+=text(20,106,(s.outputGroup?'OUTPUTS':'TRACKS')+' / '+mode,14,T.muted);for(let i=0;i<8;i++){let x=6+i*159,c=COLORS[i],mute=!!(s.mutes&&s.mutes[i]),level=(s.levels||[78,62,71,55,67,70,48,58])[i],send=(mode==='Reverb'?[18,9,48,65,12,32,75,8]:[8,12,38,20,18,27,42,6])[i];let cell=rect(x+5,120,147,292,T.bg)+text(x+14,144,String(i+1).padStart(2,'0'),15,c)+text(x+14,171,NAMES[i],17,mute?T.muted:T.text);
 for(let k=0;k<2;k++){let h=mute?0:(76+i*11%70)*(s.play?.75+.25*Math.sin(s.phase*25+i+k):.7);cell+=rect(x+39+k*10,193,6,157,T.raised)+rect(x+39+k*10,350-h,6,h,c);}
 cell+=line(x+88,193,x+88,350,T.line,2)+line(x+77,350-level/100*157,x+99,350-level/100*157,T.text,3);
 if(mode==='Delay'||mode==='Reverb')cell+=rect(x+117,193,3,157,T.raised)+rect(x+117,350-send/100*157,3,send/100*157,c);
 cell+=text(x+78,379,mode==='Mute'?(mute?'MUTED':'ON'):mode==='Level'?Math.round(-36+level*.36)+' dB':send+'%',20,mute?T.muted:T.text,'text-anchor="middle"');if(mute&&mode!=='Mute')cell+=text(x+78,402,'M',14,T.muted,'text-anchor="middle"');b+=hit('mixtrack:'+i,cell,'Mixer Track '+(i+1));}return b+bottom(s,'mixer');}
function render(s){let old=T.track;T.track=s.track||old;let body=({seq,auto:automation,macro,perf:performance,tracks,mixer}[s.page]||api.views?.[s.page]||seq)(s);let out=svg(body,'Bento Playground '+s.page+' design prototype');T.track=old;return out;}
function sheet(){let b=text(24,42,'BENTO PLAYGROUND / MEASURE',25)+text(24,73,'Functional minimalism. Expressive feedback.',17,T.muted);let colors=['bg','surface','raised','line','muted','text','track','record'];colors.forEach((k,i)=>{let x=24+i*155;b+=rect(x,102,134,48,T[k])+text(x,177,k,16)+text(x,201,T[k],14,T.muted);});
 ['lock','condition','auto','mod'].forEach((k,i)=>{let x=24+i*310;b+=icon(k,x,239,T.track)+text(x+34,255,['Parameter lock','Conditional trigger','Automation','Modulation range'][i],18);});
 b+=text(24,311,'01  Immediate',28)+text(450,311,'02  Deep',22)+text(850,311,'03  Playable',18);b+=text(24,354,'Value / 25 px',25)+text(450,354,'Label / 16 px',16,T.muted)+text(850,354,'Detail / 14 px',14,T.muted);
 b+=line(24,390,1256,390,T.line)+text(24,425,'Selection: corner brackets',18)+text(450,425,'Playback: white top rule',18)+text(850,425,'Track color: musical ownership',18);return svg(b,'Design kit component sheet');}
const api={T,COLORS,NAMES,defaultState,render,sheet,rect,line,text,path,dot,param,hit,icon,macroGraph};if(typeof module!=='undefined')module.exports=api;else root.BentoDesign=api;
})(typeof window!=='undefined'?window:globalThis);
