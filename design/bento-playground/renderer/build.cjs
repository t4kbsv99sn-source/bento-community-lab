// Rebuild both preview entry points from the same source, preventing stale copies.
const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
execFileSync(process.execPath,[path.join(__dirname,'export.cjs')],{stdio:'inherit'});
let html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const source of ['renderer/design.js','renderer/views.js','renderer/preview.js'])html=html.replace(`<script src="${source}"></script>`,()=>'<script>\n'+fs.readFileSync(path.join(root,source),'utf8')+'\n</script>');
fs.writeFileSync(path.join(root,'Bento_Playground_Preview.html'),html);
fs.mkdirSync(path.join(root,'dist'),{recursive:true});
for(const name of ['index.html','Bento_Playground_Preview.html','renderer','docs'])fs.cpSync(path.join(root,name),path.join(root,'dist',name),{recursive:true});
console.log('Built matching self-contained and multi-file previews.');
