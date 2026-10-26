const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const D=require('../renderer/design.js');require('../renderer/views.js');
const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',value:'',classList:{toggle(){},contains(){return false}}});return elements.get(id)};
const ctx=vm.createContext({BentoDesign:D,document:{getElementById:el,querySelectorAll:()=>[]},window:{addEventListener(){}},requestAnimationFrame(){},performance:{now:()=>0}});
vm.runInContext(fs.readFileSync(require.resolve('../renderer/preview.js'),'utf8'),ctx);
const run=code=>vm.runInContext(code,ctx);
run("switchPage('euclid'); action('eurow:3'); action('viewnav:Step')");assert.equal(run('page'),'seq');assert.match(el('display').innerHTML,/04 Clap/);assert.equal((el('display').innerHTML.match(/data-action="step:/g)||[]).length,32);
run("action('nav:Sequence')");assert.equal(run('page'),'sequence');assert.match(el('display').innerHTML,/viewnav:Euclidean/);
run("action('viewnav:Step')");assert.equal(run('page'),'seq');
run("action('nav:Euclidean')");assert.equal(run('page'),'euclid');
run("switchPage('chord'); action('viewnav:Seq'); action('viewnav:Step')");assert.equal(run('page'),'melodic');
for(const page of ['seq','euclid','meleuclid','sequence','chord','fx','matrix']){const svg=D.render({...D.defaultState(),page});assert(!/NaN|undefined/.test(svg));for(const m of svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)){const [x,y,w,h]=m.slice(1).map(Number);assert(x>=0&&y>=0&&x+w<=1280&&y+h<=480,`${page}: rectangle outside display ${m[0]}`);}}
console.log('PASS: drum Euclid → one-shot → Sequence → one-shot; melodic routing; 32 steps; rectangle bounds.');

run("switchPage('euclid'); selectRow(0); state.steps[1].on=true; selectRow(3); state.steps[1].on=false; selectRow(0)");assert.equal(run('state.steps[1].on'),true);run('selectRow(3)');assert.equal(run('state.steps[1].on'),false);
run("state.euLength=7; state.euHits=3; state.euRotate=2; rowBank()[3]={length:7,hits:3,rotate:2}; selectRow(0); selectRow(3)");assert.equal(run('state.euLength'),7);assert.equal(run('state.euHits'),3);assert.equal(run('state.euRotate'),2);
const eu=D.render({...D.defaultState(),page:'euclid'});assert.equal((eu.match(/data-action="eurow:/g)||[]).length,8);assert(eu.includes('Faint: repeats'));console.log('PASS: independent pad edits and Euclid row settings; complete row hit groups.');
