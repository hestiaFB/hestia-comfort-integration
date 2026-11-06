// Confort's panel in English: every French text given to t() or fr() in panel.ts, model.ts, lights.ts, foyer.ts, sketch.ts, learning3.ts and habitudes.ts has its English words
// (in i18n-en.ts, or in the hub's dictionary), the dictionary keeps no word nothing shows, and a translation keeps the
// same {names} as its French.
import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';

const root=fileURLToPath(new URL('../',import.meta.url));
const temp=mkdtempSync(join(tmpdir(),'hestia-panel-i18n-'));
after(()=>rmSync(temp,{recursive:true,force:true}));
// One bundle, so that model.ts and the test share the same language.
writeFileSync(join(temp,'entry.ts'),[`export * from ${JSON.stringify(join(root,'model.ts'))};`,
 `export {setLanguage,addDictionary} from ${JSON.stringify(join(root,'socle/i18n.ts'))};`,
 `export {SOCLE_EN} from ${JSON.stringify(join(root,'socle/i18n-en.ts'))};`,`export {PANEL_EN} from ${JSON.stringify(join(root,'i18n-en.ts'))};`].join('\n'));
await build({entryPoints:[join(temp,'entry.ts')],bundle:true,platform:'node',format:'esm',outfile:join(temp,'entry.mjs'),logLevel:'silent'});
const m=await import(pathToFileURL(join(temp,'entry.mjs')).href);
const {PANEL_EN,SOCLE_EN}=m;

/** The French literals given to t() and fr(): both sides of a ternary, never a template string. */
function frenchTexts(source){
 const found=[],call=/\b(?:t|fr)\(/g;
 for(let x=call.exec(source);x;x=call.exec(source)){
  let depth=0,i=x.index+x[0].length;
  for(;i<source.length;i++){const c=source[i];
   if(c==="'"||c==='"'){let j=i+1,text='';while(source[j]!==c){if(source[j]==='\\')j++;text+=source[j++];}found.push(text);i=j;}
   else if(c==='`')break;else if('([{'.includes(c))depth++;else if(')]}'.includes(c)){if(!depth--)break;}else if(c===','&&!depth)break;}
 }
 return found;
}
const texts=new Set(['panel.ts','model.ts','lights.ts','foyer.ts','sketch.ts','learning3.ts','habitudes.ts','fieldtrial.ts'].flatMap(f=>frenchTexts(readFileSync(join(root,f),'utf8'))).filter(Boolean));
const names=text=>[...text.matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort().join();

test('the panel has English words for every French text it shows',()=>{
 assert.ok(texts.size>400);
 assert.deepEqual([...texts].filter(x=>!(x in PANEL_EN)&&!(x in SOCLE_EN)),[]);
});
test('the panel’s dictionary keeps no word nothing shows, nor one the hub already has',()=>{
 assert.deepEqual(Object.keys(PANEL_EN).filter(x=>!texts.has(x)||x in SOCLE_EN),[]);
});
test('a translation keeps the same {names} as its French',()=>{
 assert.deepEqual(Object.entries(PANEL_EN).filter(([french,english])=>names(french)!==names(english)).map(([french])=>french),[]);
});
test('the measures and their summaries follow the language, French staying the source',()=>{
 const room={sources:{indoor_temperature:'sensor.t',indoor_humidity:'sensor.h'},windows:['a','b']};
 m.addDictionary('en',PANEL_EN);
 m.setLanguage('en');
 try{
  assert.equal(m.labels.indoor_temperature,'Room temperature');
  assert.equal(m.coverage(room),'Temperature, humidity · 2 openings');
  assert.equal(m.exteriorSummary({rain:{entity_id:'sensor.r',adapter:'x'}}),'Rain');
  assert.equal(m.measurement({available:false}),'Not answering right now');
 }finally{m.setLanguage('fr');}
 assert.equal(m.labels.indoor_temperature,'Température de la pièce');
 assert.equal(m.coverage(room),'Température, humidité · 2 ouvrants');
});
