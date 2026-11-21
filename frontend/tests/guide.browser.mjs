// The installation guide in the real built panel (fictitious data only): the house's guide sends nothing before its last
// screen, then each setting with its own command; a room's guide saves the room as its tabs do; every screen fits a phone.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync,existsSync,mkdirSync} from 'node:fs';
import {once} from 'node:events';
import {chromium,firefox} from '../../card/node_modules/playwright/index.mjs';
import {harness,comfort} from './hub-harness.mjs';
const root=new URL('../../custom_components/hestia_comfort/frontend/',import.meta.url),html=harness(false);
const server=createServer((req,res)=>{const path=new URL(req.url,'http://localhost').pathname;
 try{let file;if(path==='/shell.js')file=new URL('hestia-socle.js',root);else if(path==='/comfort.js')file=new URL('panel.js',root);else if(/^\/manrope-\d+\.ttf$/.test(path)||/^\/hub-\w+\.js$/.test(path))file=new URL(path.slice(1),root);
 if(file&&existsSync(file)){res.setHeader('Content-Type',path.endsWith('.ttf')?'font/ttf':'text/javascript');res.end(readFileSync(file));}
 else if(path.endsWith('/comfort.json')){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(comfort));}
 else if(path.endsWith('/weather.json')){res.setHeader('Content-Type','application/json');res.end(readFileSync(new URL('./fixtures/weather.json',import.meta.url)));}
 else{res.setHeader('Content-Type','text/html');res.end(html);}}catch(e){res.statusCode=500;res.end(String(e));}
});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const out=process.env.HESTIA_HUB_OUTPUT;if(out)mkdirSync(out,{recursive:true});
let checks=0;
async function noOverflow(panel){const size=await panel.evaluate(e=>({width:e.clientWidth,scroll:e.scrollWidth}));assert.ok(size.scroll<=size.width+1,JSON.stringify(size));}
const sent=page=>page.evaluate(()=>calls.map(c=>c.type).filter(x=>/save_config|set_foyer|set_lights|set_pollen_allergy/.test(x)));
const heading=panel=>panel.locator('.gd-guide h2').first().textContent();
/** « Suivant » until the last screen, each screen checked on the way; returns the headings seen. */
async function walk(panel,shots){const seen=[];
 for(let i=0;i<40;i++){const h=await heading(panel);seen.push(h);await noOverflow(panel);if(shots)await shots(h);
  const next=panel.locator('.gd-foot button.primary');if(['Enregistrer','Créer la pièce'].includes((await next.textContent()).trim()))return seen;
  await next.click();await panel.waitForFunction?.(()=>true);await panel.locator('.gd-guide h2').first().waitFor();}
 throw Error('Le guide ne finit pas : '+seen.join(' / '));}
try{for(const engine of [chromium,firefox]){const browser=await engine.launch();try{for(const width of [1440,390,320]){
 const page=await browser.newPage({viewport:{width,height:900},hasTouch:width<600});page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/hestia');await page.getByRole('button',{name:'Ouvrir Confort',exact:true}).click();const panel=page.locator('hestia-comfort-setup');
 await panel.getByRole('heading',{name:'Confort',exact:true}).waitFor();
 // The house's guide, from the overview: its summary, then every screen; nothing sent before the end.
 await panel.getByRole('button',{name:/Le guide de la maison/}).click();await panel.getByRole('heading',{name:'Installons votre maison',exact:true}).waitFor();
 assert.ok(page.url().endsWith('/hestia/confort/guide'),page.url());checks++;
 const topics=await panel.locator('.gd-topics li span:nth-child(2)').allTextContents();
 assert.deepEqual(topics,['Le dehors','Votre maison','Le sommeil','Vos habitudes','Les conseils','La lumière du conseil']);checks++;
 await panel.getByRole('button',{name:'Commencer',exact:true}).click();
 const shot=engine===chromium&&out?async h=>{await page.screenshot({path:`${out}/guide-maison-${width}-${h.replace(/[^\p{L}\d]+/gu,'-')}.png`,fullPage:true});}:undefined;
 // An answer on the way: the week-days' question, then the house's draft holds it.
 let houseSeen=[];
 for(let i=0;i<40;i++){const h=await heading(panel);houseSeen.push(h);await noOverflow(panel);if(shot)await shot(h);
  if(h.startsWith('En semaine'))await panel.getByRole('button',{name:'Souvent vide',exact:true}).click();
  if(h==='Combien de conseils ?')await panel.getByRole('switch',{name:'Allergie aux pollens'}).or(panel.getByRole('checkbox',{name:'Allergie aux pollens'})).first().click();
  const next=panel.locator('.gd-foot button.primary');if((await next.textContent()).trim()==='Enregistrer')break;await next.click();}
 assert.deepEqual(houseSeen.slice(0,3),['D’où vient le dehors ?','Comment est votre maison ?','Quand dormez-vous ?']);assert.ok(houseSeen.includes('En semaine, dans la journée, la maison est…'),houseSeen.join(' / '));
 assert.equal(houseSeen.at(-1),'Tout est prêt');checks++;
 assert.deepEqual(await sent(page),[]);checks++;
 // « Précédent » keeps the answers: the draft is the guide's, not the screen's.
 await panel.getByRole('button',{name:'‹ Précédent',exact:true}).click();await panel.getByRole('button',{name:'‹ Précédent',exact:true}).click();
 await panel.getByRole('button',{name:'Suivant',exact:true}).click();await panel.getByRole('button',{name:'Suivant',exact:true}).click();
 await panel.getByRole('button',{name:'Enregistrer',exact:true}).click();
 await panel.getByText('La maison est enregistrée.',{exact:false}).waitFor();
 assert.deepEqual(await sent(page),['set_foyer','set_pollen_allergy'].map(x=>'hestia_comfort/'+x));
 assert.ok(await page.evaluate(()=>!!state.home.foyer.journee_vide&&state.home.pollen_allergy===true));checks++;
 // A room's guide, from the overview: one screen an opening, saved as its tabs save it.
 const room=comfort.snapshot.rooms[0];
 await panel.getByRole('button',{name:`Le guide de « ${room.title} »`}).click();await panel.getByRole('heading',{name:`Le guide de « ${room.title} »`,exact:true}).waitFor();
 assert.ok(page.url().endsWith(`/hestia/confort/${room.entry_id}/guide`),page.url());checks++;
 await panel.getByRole('button',{name:'Commencer',exact:true}).click();
 const roomSeen=await walk(panel,engine===chromium&&out?async h=>{await page.screenshot({path:`${out}/guide-piece-${width}-${h.replace(/[^\p{L}\d]+/gu,'-')}.png`,fullPage:true});}:undefined);
 assert.equal(roomSeen[0],'Quelle température suivre ?');assert.equal(roomSeen.at(-1),'Tout est prêt');
 assert.equal(roomSeen.filter(h=>h==='Comment la pièce est-elle chauffée ?').length,1);
 assert.equal(roomSeen.length,8+room.config.windows.length,roomSeen.join(' / '));checks++;
 const before=(await sent(page)).length;
 await panel.getByRole('button',{name:'Enregistrer',exact:true}).click();
 await panel.getByText(`« ${room.title} » est enregistrée.`).waitFor().catch(async e=>{console.log(await panel.evaluate(x=>x.shadowRoot.querySelector('main').innerText),await page.evaluate(()=>calls.slice(-4).map(c=>c.type)));throw e;});
 assert.deepEqual((await sent(page)).slice(before),['hestia_comfort/save_config']);assert.ok(page.url().endsWith('/hestia/confort'),page.url());checks++;
 // From a room's tabs, the guide works on their draft, and « Réglages de la pièce » comes back to the same tab with it.
 await panel.getByRole('button',{name:room.title,exact:true}).first().click();await panel.getByRole('tab',{name:'La pièce',exact:true}).click();
 await panel.getByLabel('Nom',{exact:true}).fill('Salon du guide');await panel.getByRole('button',{name:'Ouvrir le guide',exact:true}).click();
 await panel.getByRole('heading',{name:'Le guide de « Salon du guide »',exact:true}).waitFor();
 await panel.getByRole('button',{name:/Réglages de la pièce/}).click();await panel.getByRole('tab',{name:'La pièce',exact:true,selected:true}).waitFor();
 assert.equal(await panel.getByRole('heading',{level:1}).first().textContent(),'Salon du guide');checks++;
 // The Pièces page offers to add a room with the guide.
 await page.evaluate(()=>{history.pushState(null,'','/hestia/confort/pieces');window.dispatchEvent(new CustomEvent('location-changed'));});
 await panel.getByRole('button',{name:'Ajouter avec le guide',exact:true}).waitFor();checks++;
 assert.deepEqual(errors,[]);await page.close();
}}finally{await browser.close();}}}finally{server.close();}
console.log(JSON.stringify({checks,engines:['Chromium','Firefox'],widths:[1440,390,320]}));
