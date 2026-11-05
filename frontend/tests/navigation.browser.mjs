import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync,mkdirSync,existsSync} from 'node:fs';
import {once} from 'node:events';
import {chromium,firefox} from '../../card/node_modules/playwright/index.mjs';
import {harness,comfort,SHELL} from './hub-harness.mjs';
const comfortRoot=new URL('../../custom_components/hestia_comfort/frontend/',import.meta.url),weatherRoot=new URL('../../../hestia-weather-integration/custom_components/hestia_weather/frontend/',import.meta.url);
const withWeather=process.env.HESTIA_TEST_COMFORT_ONLY!=='1'&&existsSync(weatherRoot);const html=harness(withWeather),id=comfort.snapshot.rooms[0].entry_id;
const server=createServer((req,res)=>{const path=new URL(req.url,'http://localhost').pathname;
 try{let file;if(path==='/shell.js')file=new URL('hestia-socle.js',comfortRoot);else if(path==='/comfort.js')file=new URL('panel.js',comfortRoot);else if(path==='/weather.js')file=new URL('panel.js',weatherRoot);else if(/^\/manrope-\d+\.ttf$/.test(path))file=new URL(path.slice(1),comfortRoot);
 if(file){res.setHeader('Content-Type',path.endsWith('.ttf')?'font/ttf':'text/javascript');res.end(readFileSync(file));}
 else if(path.endsWith('/comfort.json')){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(comfort));}
 else if(path.endsWith('/weather.json')){res.setHeader('Content-Type','application/json');res.end(readFileSync(new URL('./fixtures/weather.json',import.meta.url)));}
 else{res.setHeader('Content-Type','text/html');res.end(html);}}catch(e){res.statusCode=500;res.end(String(e));}
});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
let checks=0;const out=process.env.HESTIA_HUB_OUTPUT;if(out)mkdirSync(out,{recursive:true});
async function nav(page,label,group){const shell=page.locator(SHELL);if(await shell.locator('.mobile-bar').isVisible())await shell.getByRole('button',{name:'Ouvrir la navigation Hestia-FB',exact:true}).click();const group_=shell.getByRole('navigation',{name:group,exact:true});const fold=group_.locator('.nav-fold[aria-expanded=false]');if(await fold.count())await fold.click();await group_.getByRole('link',{name:label,exact:true}).click();}
// The Confort tab opens on its technical home, with every room one click away, even while the report loads.
async function toRooms(panel){await panel.getByRole('heading',{name:'Confort',exact:true}).waitFor();await panel.getByRole('button',{name:'Salon',exact:true}).first().waitFor();}
async function noOverflow(panel){const size=await panel.evaluate(e=>({width:e.clientWidth,scroll:e.scrollWidth,main:e.shadowRoot.querySelector('main')?.scrollWidth}));assert.ok(size.scroll<=size.width+1,JSON.stringify(size));checks++;}
try{for(const engine of [chromium,firefox]){const browser=await engine.launch();try{for(const width of [1440,390,320]){
 const page=await browser.newPage({viewport:{width,height:950},hasTouch:width<600});page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/hestia');await page.getByRole('button',{name:'Ouvrir Confort',exact:true}).waitFor();await page.evaluate(()=>healthMode='hold');await page.getByRole('button',{name:'Ouvrir Confort',exact:true}).click();const panel=page.locator('hestia-comfort-setup');await toRooms(panel);
 // The overview is immediate, even with a fourteen-second technical report.
 await page.waitForFunction(()=>healthQueue.length>0);if(engine===chromium&&width===1440)await page.waitForTimeout(14000);
 await toRooms(panel);checks++;
 const links=page.locator(SHELL).locator('nav[aria-label=Confort] a');assert.deepEqual(await links.allTextContents(),['Vue d’ensemble','Pièces','Réglages','Apprentissage','Extensions','Bilan']);checks++;
 // From one page to a slow one, the home never shows for an instant in between: « Chargement… », then the page.
 await nav(page,'Bilan','Confort');await panel.locator('hestia-comfort-review').waitFor();
 await page.evaluate(()=>{window.discoverDelay=400;window.seen=[];let on=false;window.addEventListener('click',()=>{on=true;},{capture:true,once:true});const tick=()=>{if(on){const h=window.shell.shadowRoot.querySelector('hestia-comfort-setup')?.shadowRoot?.querySelector('main h1');window.seen.push(h?.textContent??'');}if(window.seen.length<200)requestAnimationFrame(tick);};requestAnimationFrame(tick);});
 await nav(page,'Réglages','Confort');await panel.getByRole('heading',{name:'Réglages',exact:true}).waitFor();{const seen=await page.evaluate(()=>window.seen);assert.ok(!seen.includes('Confort'),JSON.stringify([...new Set(seen)]));}checks++;
 await page.evaluate(()=>{window.discoverDelay=0;});await nav(page,'Vue d’ensemble','Confort');await toRooms(panel);
 // The panel's own buttons go there too (« Réglages généraux » on its home, « Régler » of WLED): not only the side menu (30 October).
 await nav(page,'Vue d’ensemble','Confort');await panel.getByRole('button',{name:'Salon',exact:true}).first().click();await panel.getByRole('heading',{name:'Salon',exact:true}).waitFor();checks++;
 await nav(page,'Pièces','Confort');await panel.getByRole('button',{name:'Cuisine',exact:true}).click();await panel.getByRole('heading',{name:'Cuisine',exact:true}).waitFor();assert.ok(page.url().includes('cuisine-demo/mesures'));checks++;
 for(const name of ['Mesures','Ouvertures','Chauffage','Équipements','La pièce','Apprentissage']){await panel.getByRole('tab',{name,exact:true}).click();await noOverflow(panel);}
 await panel.getByRole('tab',{name:'La pièce',exact:true}).click();await panel.getByLabel('Nom',{exact:true}).fill('Cuisine brouillon');await nav(page,'Vue d’ensemble','Confort');await toRooms(panel);
 await nav(page,'Pièces','Confort');await panel.getByRole('button',{name:'Salon',exact:true}).click();await panel.getByRole('heading',{name:'Salon',exact:true}).waitFor();await panel.getByRole('tab',{name:'La pièce',exact:true}).click();assert.equal(await panel.getByLabel('Nom',{exact:true}).inputValue(),'Salon');checks++;
 await nav(page,'Vue d’ensemble','Confort');await nav(page,'Pièces','Confort');await panel.getByRole('button',{name:'Cuisine',exact:true}).click();await panel.getByRole('tab',{name:'La pièce',exact:true}).click();
 // A retained draft must not be overwritten by Configurer reopening its server copy.
 assert.equal(await panel.getByLabel('Nom',{exact:true}).inputValue(),'Cuisine brouillon');checks++;
 await panel.getByRole('tab',{name:'Mesures',exact:true}).click();await panel.getByRole('heading',{name:'Cuisine brouillon',exact:true}).waitFor();{const text=await panel.evaluate(e=>e.shadowRoot.querySelector('main').textContent);for(const name of ['CO₂','Particules fines','COV','Plage de confort','Aérer à partir de'])assert.ok(text.includes(name),name);}checks++;
 assert.equal(await panel.getByLabel('Aérer à partir de',{exact:true}).inputValue(),'1000');checks++;
 const help=panel.getByRole('button',{name:'Aide : Plage de confort',exact:true});await help.click();await panel.getByRole('tooltip').waitFor();await page.keyboard.press('Escape');await panel.getByRole('tooltip').waitFor({state:'hidden'});checks++;
 const initial=await page.evaluate(()=>JSON.stringify(state));if(out&&engine===chromium)await page.screenshot({path:out+'/production-air-dark-'+width+'.png',fullPage:true});await panel.getByRole('button',{name:'Enregistrer',exact:true}).waitFor();assert.equal(await page.evaluate(()=>JSON.stringify(state)),initial);checks++;
 await nav(page,'Réglages','Confort');await panel.getByRole('heading',{name:'Réglages',exact:true}).waitFor();await noOverflow(panel);
 if(withWeather){
  // Hestia Weather's pages (socle 1.21, like Confort's): its overview, its places, then one place in tabs.
  await nav(page,'Vue d’ensemble','Météo');const weather=page.locator('hestia-weather-setup');await weather.getByRole('heading',{name:'Météo',exact:true}).waitFor();checks++;
  await nav(page,'Lieux','Météo');await weather.getByRole('heading',{name:'Lieux',exact:true}).waitFor();await weather.getByRole('button',{name:'Maison',exact:true}).click();await weather.getByRole('heading',{name:'Maison',exact:true}).waitFor();checks++;
  for(const name of ['Sources','Station','Air','Pollens','Eau et jardin','Entités','État']){await weather.getByRole('tab',{name,exact:true}).click();await weather.getByRole('tab',{name,exact:true,selected:true}).waitFor();await noOverflow(weather);}
  await nav(page,'Réglages','Météo');await weather.getByRole('heading',{name:'Réglages',exact:true}).waitFor();checks++;
  await page.evaluate(()=>toggleTheme());await noOverflow(weather);}else await page.evaluate(()=>toggleTheme());await nav(page,'Vue d’ensemble','Confort');await toRooms(panel);
 if(out&&engine===chromium)await page.screenshot({path:out+'/production-overview-'+width+'.png',fullPage:true});
 if(engine===chromium&&width===1440){await nav(page,'Pièces','Confort');await panel.getByRole('button',{name:'Cuisine',exact:true}).click();await panel.getByRole('tab',{name:'La pièce',exact:true}).click();await panel.getByRole('button',{name:'Enregistrer',exact:true}).click();await panel.getByRole('heading',{name:'Cuisine brouillon',exact:true}).waitFor();await panel.getByText('Enregistré',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>state.rooms[0].title),'Salon');assert.equal(await page.evaluate(()=>state.rooms.find(r=>r.entry_id==='cuisine-demo').title),'Cuisine brouillon');const saved=await page.evaluate(()=>calls.filter(c=>c.type==='hestia_comfort/save_config').at(-1));assert.equal(saved.entry_id,'cuisine-demo');checks+=3;
 await nav(page,'Vue d’ensemble','Confort');await nav(page,'Pièces','Confort');await panel.getByRole('button',{name:'Salon',exact:true}).click();await panel.getByRole('tab',{name:'La pièce',exact:true}).click();await panel.getByLabel('Nom',{exact:true}).fill('Salon bis');await page.evaluate(()=>validationMode='hold');const writes=await page.evaluate(()=>calls.filter(c=>c.type==='hestia_comfort/save_config').length);await panel.getByRole('button',{name:'Enregistrer',exact:true}).click();await page.waitForFunction(()=>validationQueue.length===1);await nav(page,'Réglages','Confort');await panel.getByRole('heading',{name:'Réglages',exact:true}).waitFor();await page.evaluate(()=>{for(const resolve of validationQueue.splice(0))resolve();validationMode='ready';});await page.waitForFunction(()=>!window.shell.shadowRoot.querySelector('hestia-comfort-setup').busy);assert.equal(await page.evaluate(()=>calls.filter(c=>c.type==='hestia_comfort/save_config').length),writes);await panel.getByRole('heading',{name:'Réglages',exact:true}).waitFor();checks+=2;
 }
 // Each third-party integration has its switch, on the Extensions page (socle 1.12); Alarmo no longer lists alarms.
 await page.evaluate(()=>{healthMode='ready';for(const q of healthQueue.splice(0))q.resolve();});await nav(page,'Extensions','Confort');await panel.getByRole('switch').first().waitFor();assert.deepEqual(await panel.getByRole('switch').evaluateAll(l=>l.map(e=>[e.getAttribute('aria-label'),e.checked])),[['Utiliser Versatile Thermostat',true],['Utiliser Adaptive Cover Pro',false],['Utiliser Alarmo',true]]);assert.equal(await panel.getByLabel('Alarme utilisée').count(),0);checks++;
 await page.evaluate(()=>{healthMode='ready';for(const q of healthQueue.splice(0))q.resolve();});assert.deepEqual(errors,[]);checks++;page.on('dialog',d=>d.accept());await page.close();
 // Direct URLs, reload, and back always keep the explicit room.
 const direct=await browser.newPage({viewport:{width,height:950}});direct.setDefaultTimeout(10000);await direct.goto(origin+'/hestia/confort/'+id+'/mesures');await direct.getByRole('heading',{name:'Salon',exact:true}).waitFor();await direct.getByRole('tab',{name:'Mesures',exact:true,selected:true}).waitFor();checks++;direct.on('dialog',d=>d.accept());await direct.reload();await direct.getByRole('tab',{name:'Mesures',exact:true,selected:true}).waitFor();checks++;await nav(direct,'Vue d’ensemble','Confort');await direct.goBack();await direct.getByRole('heading',{name:'Salon',exact:true}).waitFor();await direct.getByRole('tab',{name:'Mesures',exact:true,selected:true}).waitFor();checks++;await direct.close();

 }
 for(const mode of (withWeather?['comfort','weather','none']:['comfort','none'])){const page=await browser.newPage();await page.goto(origin+'/hestia?bricks='+mode);const shell=page.locator(SHELL);await shell.getByRole('heading',{name:'Votre logement, connecté',exact:true}).waitFor();assert.equal(await shell.locator('nav[aria-label=Confort]').count(),mode==='comfort'?1:0);assert.equal(await shell.locator('nav[aria-label="Météo"]').count(),mode==='weather'?1:0);checks+=2;await page.goto(origin+'/hestia/meteo?bricks=comfort');await shell.getByText('La brique correspondante n’est pas installée ou cette adresse est inconnue.').waitFor();checks++;await page.close();}
 const failure=await browser.newPage();await failure.goto(origin+'/hestia');await failure.getByRole('button',{name:'Ouvrir Confort',exact:true}).waitFor();await failure.evaluate(()=>healthMode='error');await failure.getByRole('button',{name:'Ouvrir Confort',exact:true}).click();await failure.getByRole('heading',{name:'Confort',exact:true}).waitFor();await failure.getByRole('alert').filter({hasText:'Le bilan technique'}).waitFor();await failure.evaluate(()=>healthMode='ready');await failure.getByRole('button',{name:'Réessayer',exact:true}).click();await failure.getByRole('heading',{name:'À régler',exact:true}).waitFor();checks++;await failure.close();
 }finally{await browser.close();}}}finally{server.close();}
console.log(JSON.stringify({checks,engines:['Chromium','Firefox'],widths:[1440,390,320]}));
