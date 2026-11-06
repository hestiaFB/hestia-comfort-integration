// Socle 1.22: a brick's tab takes the pieces of the newest hub on the page, and keeps its own under an older one.
// Two hubs are built from this copy of the socle, one stamped later and one earlier, each marking its pageHead.
import {createServer} from 'node:http';
import {readFileSync,mkdirSync,cpSync,writeFileSync,existsSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {once} from 'node:events';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {chromium} from '../../card/node_modules/playwright/index.mjs';
import {harness,SHELL} from './hub-harness.mjs';
const at=path=>fileURLToPath(new URL(path,import.meta.url));
const socle=at('../socle/'),comfort=at('../../custom_components/hestia_comfort/frontend/'),weather=at('../../../niak-weather-integration/custom_components/hestia_weather/frontend/');
const withWeather=existsSync(join(weather,'panel.js'));
const out=mkdtempSync(join(tmpdir(),'hestia-hub-'));
async function variant(name,stamp){
 const dir=join(out,name);mkdirSync(dir);
 for(const f of ['shell.ts','ui.ts','i18n.ts','i18n-en.ts','i18n-de.ts'])cpSync(join(socle,f),join(dir,f));
 const ui=readFileSync(join(dir,'ui.ts'),'utf8').replace(/export const SOCLE_BUILD='[^']*';/,`export const SOCLE_BUILD='${stamp}';`)
  .replace('<div class="nk-page-head">',`<div class="nk-page-head" data-copie="${name}">`);
 writeFileSync(join(dir,'ui.ts'),ui);
 await build({entryPoints:[join(dir,'shell.ts')],bundle:true,format:'esm',target:'es2022',outfile:join(dir,'shell.js'),nodePaths:[at('../node_modules')],logLevel:'error'});
 return join(dir,'shell.js');
}
const shells={newer:await variant('newer','99999999.9999'),older:await variant('older','00000000.0001')};
let shell=shells.newer;
const server=createServer((req,res)=>{const p=new URL(req.url,'http://x').pathname;
 const files={'/shell.js':shell,'/comfort.js':join(comfort,'panel.js'),'/weather.js':join(weather,'panel.js')};
 if(files[p]){res.setHeader('Content-Type','text/javascript');return res.end(readFileSync(files[p]));}
 // Socle 1.23: the pieces loaded when needed (hub-<sum>.js), from whichever brick built them.
 const piece=/^\/hub-\w+\.js$/.test(p)&&[comfort,weather].map(d=>join(d,p.slice(1))).find(f=>existsSync(f));
 if(piece){res.setHeader('Content-Type','text/javascript');return res.end(readFileSync(piece));}
 if(p.endsWith('.ttf')){res.setHeader('Content-Type','font/ttf');return res.end(readFileSync(join(comfort,'manrope-400.ttf')));}
 if(p.endsWith('/comfort.json')){res.setHeader('Content-Type','application/json');return res.end(readFileSync(at('../../card/preview/evolution/setup-fixture.json')));}
 if(p.endsWith('/weather.json')){res.setHeader('Content-Type','application/json');return res.end(readFileSync(at('./fixtures/weather.json')));}
 res.setHeader('Content-Type','text/html');res.end(harness(withWeather));});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const tabs=[['confort','hestia-comfort-setup'],...(withWeather?[['meteo','hestia-weather-setup']]:[])];
const browser=await chromium.launch();let checks=0;
try{for(const name of ['newer','older']){shell=shells[name];
 for(const [slug,el] of tabs){
  const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${origin}/hestia/${slug}`);
  const head=page.locator(SHELL).locator(el).locator('.nk-page-head').first();await head.waitFor({timeout:15000});
  // Under the newer hub the tab draws with its pieces; under the older one, with its own copy.
  assert.equal(await head.getAttribute('data-copie'),name==='newer'?'newer':null,`${name} ${slug}`);checks++;
  assert.deepEqual(errors,[],`${name} ${slug}`);checks++;await page.close();
 }}}finally{await browser.close();server.close();rmSync(out,{recursive:true,force:true});}
console.log(JSON.stringify({checks,weather:withWeather}));
