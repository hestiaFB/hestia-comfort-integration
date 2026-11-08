import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root=new URL('../',import.meta.url),temp=await mkdtemp(join(tmpdir(),'hestia-comfort-card-'));
await build({entryPoints:['src/types.ts','src/view.ts','src/live.ts','src/views/room.ts','src/views/full.ts','src/views/horizon.ts','src/ui/scene.ts','src/editor.ts','src/hass-change.ts'].map(p=>fileURLToPath(new URL(p,root))),outdir:temp,
  bundle:true,platform:'node',format:'esm',outExtension:{'.js':'.mjs'},logLevel:'silent'});
const {cleanConfig,cleanHomeConfig,homeAction,cleanReviewConfig,kindOf,KINDS}=await import(pathToFileURL(join(temp,'types.mjs')));
const {isView,numeric,summary,readingStatus,coverageText,windFrom,evolutionLines,co2Metric,solarMetric}=await import(pathToFileURL(join(temp,'view.mjs')));
const {LiveView}=await import(pathToFileURL(join(temp,'live.mjs')));
const {roomChoices}=await import(pathToFileURL(join(temp,'editor.mjs')));
const {hassMatters}=await import(pathToFileURL(join(temp,'hass-change.mjs')));
const {outsideGaps,advice,slides,roomCard,facts,factList,factBox,trendOf,modules,whyRoom}=await import(pathToFileURL(join(temp,'views/room.mjs')));
const fixtures=JSON.parse(await readFile(new URL('../preview/card-fixtures.json',import.meta.url),'utf8'));
const fresh=()=>({...structuredClone(fixtures[0].view),computed_at:new Date().toISOString()});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
after(()=>rm(temp,{recursive:true,force:true}));

test('the twelve Python snapshots conform to the card contract',()=>{for(const f of fixtures)assert.equal(isView(f.view),true,f.id);});
test('humidity graduation stays consistent on room and home cards, including dry air',async()=>{
  const {humidityLabel,tiles,needs}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  for(const [status,degree,value,label] of [['high',1,60.6,'Légèrement humide'],['high',2,67,'Air humide'],['high',3,75,'Très humide'],
    ['low',1,39,'Légèrement sec'],['low',2,35,'Air sec'],['low',3,25,'Très sec']]){
    const v=fresh();v.observations.indoor_humidity={value,quality:'valid',source:'sensor.h'};
    v.assessment={...v.assessment,level:'calm',reason:'within_comfort',action:'ok',needs:[],missing:[],features:{humidity:{status,degree,measured:value,reachable:20},air:{co2_status:'ok',pm25_status:'ok',voc_status:'ok'}}};
    assert.equal(humidityLabel(v),label);assert.equal(advice(v).pill,'Au mieux');assert.equal(advice(v).level,'calm');
    if(status==='high')assert.equal(facts(v)[0].title,label);
    const tile=tiles(v,cleanConfig({type:'custom:hestia-comfort-card',modules:['humidity']}))[0];
    assert.equal(tile.note,label.toLowerCase());assert.equal(tile.out,degree>=2);
    assert.equal(needs(v,false).length,degree>=2?1:0);assert.match(needs(v)[0],new RegExp(label.toLowerCase()));
    if(status==='low')assert.match(facts(v)[0].text,/assécherait davantage/);
  }
});
test('humidity severity never masks another gesture or interprets an unavailable sensor',async()=>{
  const {humidityLabel}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v=fresh();v.assessment={...v.assessment,level:'urgent',action:'fermer',reason:'rain_open_windows',features:{humidity:{status:'low',degree:3}}};
  assert.equal(advice(v).title,'Fermez, il pleut');assert.equal(advice(v).pill,undefined);
  v.observations.indoor_humidity={value:25,quality:'stale'};assert.equal(humidityLabel(v),null);
});
test('reject incompatible versions, invalid levels and non-finite measures',()=>{
  for(const mutate of [v=>v.version=2,v=>v.assessment.level='normal',v=>v.observations.co2.value=Infinity,v=>v.assessment.needs=null,v=>v.computed_at='bad']){
    const v=fresh();mutate(v);assert.equal(isView(v),false);
  }
});
test('unavailable or estimated measures never become current numeric readings',()=>{
  assert.equal(numeric({value:600,quality:'stale'}),null);
  assert.equal(numeric({value:600,quality:'estimated'}),null);
  assert.equal(numeric(undefined),null);
  assert.equal(numeric({value:600,quality:'valid'}),600);
});
test('config keeps hidden modules and order without mutating input',()=>{
  const input={type:'custom:hestia-comfort-card',modules:['air','windows','air']};
  assert.deepEqual(cleanConfig(input).modules,['air','windows']);assert.equal(input.modules.length,3);
  assert.deepEqual(cleanConfig({...input,modules:[]}).modules,[]);
  assert.throws(()=>cleanConfig({...input,format:'bad'}));
});
test('an airing underway keeps the measured need and red situation',()=>{
  const v=fixtures.find(f=>f.id==='expired').view;
  assert.equal(summary(v)[0],'L’aération est en cours');assert.equal(v.assessment.level,'urgent');
});
test('an incomplete bilan names the measure that is out of date',()=>{
  const v=fresh();v.assessment={...v.assessment,reason:'incomplete_data',level:'neutral',action:'unknown',partial:true,missing:['pollution']};
  v.observations.pollution={value:null,quality:'stale',source:'sensor.atmo',received_at:null,detail:'expired',unit:null};
  const [title,body]=summary(v);
  assert.equal(title,'Une mesure n’est pas à jour');assert.match(body,/^Qualité de l’air dehors : /);
});
test('a stale contact is named as the person knows it',()=>{
  const v=fresh();v.names={'binary_sensor.w':'Fenêtre Ouest'};v.assessment={...v.assessment,missing:['window:binary_sensor.w']};
  v.observations['window:binary_sensor.w']={value:null,quality:'stale',source:'binary_sensor.w',received_at:null,detail:'expired',unit:null};
  assert.equal(coverageText(v),'Mesures à vérifier : Fenêtre Ouest');
});
test('late old-room callbacks and pending subscriptions cannot leak',async()=>{
  let finish,oldCallback,newCallback,removed=0,shown=[];
  const old={subscribeMessage:async cb=>{oldCallback=cb;return await new Promise(resolve=>finish=resolve);}};
  const next={subscribeMessage:async cb=>{newCallback=cb;return ()=>removed++;}};
  const live=new LiveView(v=>shown.push(v.entry_id),()=>{},()=>{});
  try {
    live.start(old,'old');live.start(next,'new');
    oldCallback({version:1,view:{...fresh(),entry_id:'old'}});
    newCallback({version:1,view:{...fresh(),entry_id:'new'}});
    finish(()=>removed++);await flush();
    assert.deepEqual(shown,['new']);assert.equal(removed,1);
    live.stop();await flush();assert.equal(removed,2);
  }finally{live.stop();}
});
test('same connection and room has one subscription',async()=>{
  let starts=0;const conn={subscribeMessage:async()=>{starts++;return ()=>{};}};
  const live=new LiveView(()=>{},()=>{},()=>{});
  try {live.start(conn,'salon');live.start(conn,'salon');await flush();assert.equal(starts,1);}finally{live.stop();}
});
test('reload immediately invalidates old callbacks during the retry delay',async()=>{
  let cb,starts=0,shown=0;const conn={subscribeMessage:async callback=>{starts++;cb=callback;return ()=>{};}};
  const live=new LiveView(()=>shown++,()=>{},()=>{});
  try {
    live.start(conn,'salon');await flush();
    cb({version:1,view:{...fresh(),entry_id:'salon'}});assert.equal(shown,1);
    cb({version:1,reload:true});cb({version:1,view:{...fresh(),entry_id:'salon'}});
    live.start(conn,'salon');assert.equal(shown,1);assert.equal(starts,1);
  }finally{live.stop();}
});
test('old, wrong-room, unavailable and malformed snapshots clear the view',async()=>{
  let cb,clears=0;const problems=[];
  const conn={subscribeMessage:async callback=>{cb=callback;return ()=>{};}};
  const live=new LiveView(()=>{},code=>problems.push(code),()=>clears++);
  try {
    live.start(conn,'salon');
    cb({version:1,view:{...fresh(),entry_id:'salon',computed_at:new Date(Date.now()-120000).toISOString()}});
    cb({version:1,view:{...fresh(),entry_id:'bureau'}});
    cb({version:1,unavailable:true});cb({version:1,view:{version:5}});
    assert.deepEqual(problems,['stale','version','unavailable','version']);assert.ok(clears>=4);
  }finally{live.stop();}
});
test('two cards of a room share one subscription, kept while one of them listens (PLAN-OPTIMISATION.md, point 13)',async()=>{
  let active=0,send;const conn={subscribeMessage:async(cb)=>{active++;send=cb;return ()=>active--;}};
  const seen={a:0,b:0,c:0};
  const a=new LiveView(()=>seen.a++,()=>{},()=>{}),b=new LiveView(()=>seen.b++,()=>{},()=>{}),c=new LiveView(()=>seen.c++,()=>{},()=>{});
  try {
    a.start(conn,'salon');b.start(conn,'salon');await flush();assert.equal(active,1);
    const v=fresh();v.entry_id='salon';send({version:1,view:v});assert.deepEqual([seen.a,seen.b],[1,1]);
    // A card added later gets the last view at once.
    c.start(conn,'salon');await flush();await flush();assert.equal(active,1);assert.equal(seen.c,1);
    a.stop();c.stop();await flush();assert.equal(active,1);
  }
  finally{a.stop();b.stop();c.stop();await flush();assert.equal(active,0);}
});

test('intentional absence differs from unavailable, stale and invalid readings',()=>{
  assert.equal(readingStatus(undefined),'Non configuré');
  assert.equal(readingStatus({quality:'unknown',detail:'unavailable'}),'Temporairement indisponible');
  assert.equal(readingStatus({quality:'stale'}),'Mesure trop ancienne');
  assert.equal(readingStatus({quality:'unknown',detail:'incompatible_unit'}),'Unité incompatible');
  const v=fresh();v.assessment.missing=['rain','pollution'];delete v.observations.rain;delete v.observations.pollution;
  assert.match(coverageText(v),/non configuré/);assert.doesNotMatch(coverageText(v),/à vérifier/);
  v.assessment.missing=['co2'];v.observations.co2={quality:'unknown',source:'sensor.co2',value:null};
  assert.match(coverageText(v),/Mesures à vérifier : CO₂/);
});
test('wind names say where the wind comes from, in plain French',()=>{
  assert.equal(windFrom(270),'vent d’ouest');
  assert.equal(windFrom(0),'vent du nord');
  assert.equal(windFrom(359),'vent du nord');
  assert.equal(windFrom(45),'vent de nord-est');
  assert.equal(windFrom(null),'');
});

const floorFixtures=JSON.parse(await readFile(new URL('../preview/floors.json',import.meta.url),'utf8'));
test('floor scenarios keep every room compatible with the card, including missing temperatures',()=>{
  for(const scene of floorFixtures)for(const room of scene.event.rooms)assert.equal(isView(room),true,scene.id+':'+room.title);
});

test('evolution preserves manual unknown positions, empty-room tracking and indicative estimates',()=>{
 const v=fresh();v.assessment.features={shutters:[{entity_id:'binary_sensor.w',mode:'manual',position:null,message:'Si le volet est ouvert, fermez-le.'}],presence:{state:'empty',message:'Pièce vide ; suivi maintenu.'},ventilation:{opened_minutes:null,duration_minutes:{min:5,max:10},message:'Durée indicative.'},air:{message:'Les polluants non mesurés restent inconnus.',coverage:'CO₂ uniquement'},humidity:{condensation_risk:null,message:'Risque non calculable.'}};
 const lines=evolutionLines(v,['shutters','air','windows','humidity']);
 const text=lines.map(l=>l.text).join(' ');assert.match(text,/Position non mesurée/);assert.match(text,/Pièce vide/);assert.match(text,/5–10 min/);assert.match(text,/indicati/);assert.match(text,/non mesurés/);assert.doesNotMatch(text,/depuis 0/);
 assert.deepEqual(evolutionLines(v,[]),[]);assert.deepEqual(evolutionLines({...v,assessment:{...v.assessment,features:undefined}},['air']),[]);
});

test('CO₂ verdict follows its own observation and verdict despite high particles',()=>{
 const v=fresh();v.assessment.needs=['air'];v.assessment.level='action';v.assessment.features={air:{co2_status:'ok',pm25_status:'high'}};
 v.observations.co2={value:500,quality:'valid'};
 assert.equal(co2Metric(v).state,'ok');assert.equal(co2Metric(v).note,'Dans vos repères CO₂');
 v.observations.co2={value:null,quality:'unknown'};v.assessment.features.air.co2_status='unknown';
 assert.equal(co2Metric(v).state,'off');assert.doesNotMatch(co2Metric(v).note,/renouveler/);
 v.observations.co2={value:1500,quality:'valid'};v.assessment.features.air.co2_status='high';
 assert.equal(co2Metric(v).state,'need');assert.match(co2Metric(v).note,/renouveler/);
});
test('condensation has three explicit estimated outcomes and empty histories stay honest',()=>{
 const v=fresh();for(const [risk,text] of [[true,'Risque de buée estimé'],[false,'Aucun risque de buée estimé'],[null,'Risque de buée inconnu']]){
  v.assessment.features={humidity:{condensation_risk:risk,message:'Modèle estimé.'},trends:{indoor:null,outdoor:null,message:'Pentes estimées.'},ventilation:{opened_minutes:null,duration_minutes:null,message:'Durée indicative.'}};
  const lines=evolutionLines(v,['humidity','temperature','windows']);assert.match(lines.find(l=>l.title==='Humidité et buée').text,new RegExp(text));
  assert.equal(lines.find(l=>l.title==='Évolution des températures').text,'Historique insuffisant pour estimer une tendance.');
  assert.equal(lines.some(l=>l.title==='Aération'),false);
 }
 v.assessment.sun=null;assert.equal(solarMetric(v).value,'—');assert.equal(solarMetric(v).note,'Position du soleil inconnue');
});
test('an open contact with no reliable timer keeps its unknown duration visible',()=>{
 const v=fresh();v.observations['window:binary_sensor.open']={value:true,quality:'valid',source:'binary_sensor.open',received_at:new Date().toISOString(),detail:null,unit:null};
 v.assessment.features={ventilation:{opened_minutes:null,duration_minutes:null,message:'Ouvert depuis une durée inconnue.'}};
 assert.match(evolutionLines(v,['windows']).map(l=>l.text).join(' '),/durée inconnue/);
});
test('humidity and shutter reasons introduced by the engine have readable summaries',()=>{
 const v=fresh();for(const reason of ['rehumidification_risk','shutter_protection','voc_outdoor']){v.assessment.reason=reason;assert.notEqual(summary(v)[0],'Conseil à vérifier');}
});
const evolutionFixtures=JSON.parse(await readFile(new URL('../preview/evolution/real-fixtures.json',import.meta.url),'utf8'));
test('the sixteen evolution engine scenes keep a readable compatible card',()=>{
 for(const scene of evolutionFixtures){assert.equal(isView(scene.view),true,scene.id);assert.notEqual(summary(scene.view)[0],'Conseil à vérifier',scene.id);}
});

test('an outdoor source that does not answer is « indisponible », a missing one « non suivi », the rest is not called outdoor',()=>{
  const v=fresh();v.assessment={...v.assessment,reason:'verify_exterior',missing:['heating','pollution'],unverified:[]};
  v.observations.pollution={value:null,quality:'unknown',source:'sensor.atmo',received_at:null,detail:'unavailable',unit:null};
  v.observations.heating={value:null,quality:'unknown',source:'climate.poele',received_at:null,detail:'unavailable',unit:null};
  assert.equal(outsideGaps(v),'Air extérieur indisponible');
  v.assessment.unverified=['rain'];
  assert.equal(outsideGaps(v),'Air extérieur indisponible, pluie non suivie');
  v.assessment.missing=[];v.assessment.unverified=['rain','pollution'];
  assert.equal(outsideGaps(v),'Pluie et air extérieur non suivis');
});
test('card display settings are booleans, kept as given',()=>{
  const c=cleanConfig({type:'custom:hestia-comfort-card',measures_open:false,details_open:true,rotate:false,show_scale:false});
  assert.equal(c.measures_open,false);assert.equal(c.details_open,true);assert.equal(c.rotate,false);assert.equal(c.show_scale,false);
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',rotate:'non'}));
});

// A lit template read as plain text, as the banner shows it.
const flat=t=>t==null?'':typeof t==='string'||typeof t==='number'?String(t):Array.isArray(t)?t.map(flat).join(''):t.strings?t.strings.map((s,i)=>s+flat(t.values[i])).join(''):'';
const plain=t=>flat(t).replace(/<[^>]+>/g,'');
test('the drying advice speaks of what this room really gains, how long, and when it is better',()=>{
  const v=fresh(),drying={minutes:35,now:76,after:70,gain:6,tau:35,openings:7,later:null};
  v.observations.indoor_humidity={value:76,quality:'valid',source:'sensor.h',received_at:null,detail:null,unit:'%'};
  v.observations.outdoor_humidity={value:81,quality:'valid',source:'sensor.o',received_at:null,detail:null,unit:'%'};
  v.assessment={...v.assessment,reason:'drying_possible',action:'ouvrir',features:{...v.assessment.features,drying,ventilation:{opened_minutes:null,duration_minutes:{min:25,max:35},message:'',capacity:null}}};
  let a=advice(v);assert.equal(a.title,'Aérez 25 à 35 min');assert.match(plain(a.line),/environ 70 % après l’aération/);assert.doesNotMatch(plain(a.line),/il ferait/);
  v.assessment.features.drying={...drying,later:{minutes:35,now:76,after:62,gain:14,time:'2026-10-17T20:00:00+00:00'}};
  assert.equal(slides(v).filter(s=>s.title.startsWith('Encore mieux vers')).length,1);
  v.assessment={...v.assessment,reason:'drying_later',action:'attendre'};
  a=advice(v);assert.match(a.title,/^Aérez vers /);assert.match(plain(a.line),/environ 62 % après 35 min/);
  v.assessment={...v.assessment,reason:'ventilation_possible',level:'action',features:{...v.assessment.features,drying:{...drying,after:74,gain:2},air:{...(v.assessment.features?.air??{}),ventilation:{on:false,boost:false}}}};
  // Never the losing remedy's numbers under « Lancez la VMC » (20 Oct.: « 85 → 85 % seulement »).
  a=advice(v);assert.equal(a.title,'Lancez la VMC');assert.match(plain(a.line),/la fenêtre la baisse à peine/);assert.doesNotMatch(plain(a.line),/→| de [0-9]+ à [0-9]+ %/);
  // Chambre P, 27 Oct.: 78 % under « Lancez la VMC » keeps its degree in « À savoir », not a bare « Humidité ».
  v.assessment.features.humidity={...(v.assessment.features.humidity??{}),status:'high',degree:3,lasting:true};
  const humid=facts(v).find(f=>/au-dessus de votre plage/.test(plain(f.text)));
  assert.equal(humid?.title,'Très humide');
});
test('the weather’s own humidity and a coming rain are said plainly',()=>{
  const v=fresh();
  v.assessment={...v.assessment,reason:'humid_outdoor',action:'ok',level:'calm',features:{...v.assessment.features,humidity:{dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:78,mould:false,excess:0.1,source:'outside',reachable:72}}};
  assert.equal(advice(v).title,'Rien à faire');
  assert.deepEqual(facts(v).map(f=>f.title+' · '+plain(f.text)),['Air humide dehors · aérer ne ferait pas baisser l’humidité']);
  v.assessment={...v.assessment,reason:'rain_soon',action:'fermer',rain_soon_minutes:12,features:{...v.assessment.features,rain_ahead:{minutes:12,precise:true}}};
  assert.match(plain(advice(v).line),/Pluie dans 12 min/);
  v.assessment.features.rain_ahead={minutes:0,precise:false};v.assessment.rain_soon_minutes=0;
  assert.match(plain(advice(v).line),/Pluie annoncée dans l’heure/);assert.doesNotMatch(plain(advice(v).line),/0 min/);
});
test('a « keep closed » that brings nothing leaves the banner calm',()=>{
  const v=fresh();
  for(const reason of ['drying_unavailable','drying_slow','opening_blocked','cooling_unavailable','precool_later']){
    v.assessment={...v.assessment,reason,level:'calm',action:'attendre'};
    const a=advice(v);assert.equal(a.title,'Rien à faire',reason);assert.match(plain(a.line),reason==='opening_blocked'?/n’est pas possible/:/n’apporterait rien/);
  }
  v.assessment={...v.assessment,reason:'opening_blocked',level:'action',action:'attendre'};
  assert.notEqual(advice(v).title,'Rien à faire');
});
test('the banner carries a gesture or « Rien à faire »; what is worth knowing goes to « À savoir »',()=>{
  const v=fresh();
  // 20 Oct. audit: outdoor air bad and a window open, the engine said close and the card said nothing to do.
  v.assessment={...v.assessment,reason:'opening_blocked',level:'neutral',action:'fermer',constraints:['pollution']};
  assert.equal(advice(v).title,'Refermez');
  const cold=(w,level='calm')=>{v.assessment={...v.assessment,reason:'heat_needed',level,action:'ok',constraints:[],features:{...v.assessment.features,warmth:w}};return v;};
  assert.equal(advice(cold({occupied:true,heating:'off'},'action')).title,'Rallumez le chauffage');
  assert.equal(advice(cold({occupied:false,heating:'off'})).title,'Rien à faire');
  assert.deepEqual(facts(v).map(f=>f.title+' · '+plain(f.text)),['Pièce fraîche · maison vide : pas besoin de chauffer']);
  assert.match(plain(facts(cold({occupied:true,heating:'on'}))[0].text),/le chauffage s’en charge/);
  // 20 Oct.: « Murs humides » as a banner title under « Tout va bien » read as nonsense. Now a plain line below.
  v.assessment={...v.assessment,reason:'drying_slow',level:'calm',action:'attendre',features:{...v.assessment.features,warmth:null,humidity:{dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:88,mould:true,excess:0.2,source:'outside',reachable:75}}};
  assert.equal(advice(v).title,'Rien à faire');
  const lines=facts(v).map(f=>f.title+' · '+plain(f.text));
  assert.equal(lines[0],'Humidité élevée · risque de moisissure : ne séchez pas de linge ici, écartez les meubles du mur');
  // 26 Oct.: one line for the humidity, never two about the same thing.
  assert.equal(lines.filter(l=>/umid|Aération/.test(l)).length,1,lines.join(' / '));
  assert.ok(lines.every(l=>!/%|µg|murs froids|retour du sec/.test(l)),lines.join(' / '));
  v.assessment={...v.assessment,reason:'open_neutral',level:'calm',action:'ok',features:{...v.assessment.features,humidity:undefined}};
  assert.equal(advice(v).title,'Rien à faire');assert.equal(facts(v)[0].title,'Fenêtre ouverte');
  // Remedies at work are information, never a banner slide.
  v.assessment={...v.assessment,reason:'within_comfort',features:{...v.assessment.features,air:{co2_status:'ok',pm25_status:'ok',voc_status:'ok',voc_unit:null,purifier:{on:true,speed:40},ventilation:{on:true,boost:false},coverage:'',message:''}}};
  assert.equal(slides(v).length,1);assert.deepEqual(facts(v).map(f=>f.title),['Purificateur','VMC']);
});
test('a cool room the heating takes care of is no problem on the banner, only in « À savoir »',()=>{
  // 26 Oct., Chambre P at 18.7 °C for 19 °C, thermostat in comfort: « Un peu frais » beside « Rien à faire » read as « heat it ».
  const v=fresh();
  v.assessment={...v.assessment,reason:'heat_needed',level:'calm',action:'ok',needs:['heat'],constraints:[],
    features:{...v.assessment.features,humidity:undefined,warmth:{occupied:true,heating:'on',slight:true}}};
  let a=advice(v);
  assert.equal(a.title,'Rien à faire');assert.equal(a.pill,'Au mieux');assert.equal(a.level,'calm');assert.equal(a.disk,'temp');
  assert.equal(slides(v)[0].pill,'Au mieux');
  assert.deepEqual(facts(v).map(f=>f.title+' · '+plain(f.text)),['Un peu frais · le chauffage s’en charge']);
  // Damp walls remain the room's problem: the pill names it, never the cold.
  v.assessment.features.humidity={status:'high',degree:2,dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:88,mould:true,excess:0.2,source:'outside',reachable:75};
  v.assessment.needs=['heat','dry'];
  a=advice(v);assert.equal(a.title,'Rien à faire');assert.equal(a.pill,'Au mieux');
  // Beyond the tolerance with the heating off, the engine asks the gesture: no more « Rien à faire ».
  v.assessment={...v.assessment,level:'action',features:{...v.assessment.features,humidity:undefined,warmth:{occupied:true,heating:'off',slight:false}}};
  assert.equal(advice(v).title,'Rallumez le chauffage');
  // Clearly cold with no heating known (a towel rail not yet linked): « Tout va bien » would be wrong.
  v.assessment={...v.assessment,level:'calm',needs:['heat'],features:{...v.assessment.features,warmth:{occupied:true,heating:null,slight:false}}};
  assert.equal(advice(v).pill,'Trop frais');
  v.assessment.features.warmth.slight=true;assert.equal(advice(v).pill,'Au mieux');
});
test('« Au mieux » under « Rien à faire »: « À savoir » says first what counts most',()=>{
  // 26 Oct., Chambre A at 63.5 %: « Air humide » beside « Rien à faire » read as « do something ».
  const v=fresh();v.observations.indoor_humidity={value:63.5,quality:'valid',source:'sensor.h'};
  v.assessment={...v.assessment,reason:'drying_slow',action:'attendre',level:'calm',needs:['dry'],constraints:[],
    features:{...v.assessment.features,warmth:null,humidity:{status:'high',degree:2,lasting:true,measured:63.5,reachable:70}}};
  v.feedback={last:{measure:'co2',before:1072,after:702,predicted:986}};
  assert.equal(advice(v).title,'Rien à faire');assert.equal(slides(v)[0].pill,'Au mieux');assert.equal(slides(v)[0].level,'calm');
  assert.deepEqual(facts(v).map(f=>f.title==='Dernière aération'?f.title:f.title+' · '+plain(f.text)),['Air humide · depuis plusieurs heures, aérer ne gagnerait presque rien','Dernière aération']);
  // A risk comes before the state; the pill keeps naming it.
  v.assessment.features.humidity={...v.assessment.features.humidity,mould:true};
  assert.equal(advice(v).pill,'Au mieux');
  assert.deepEqual(facts(v).map(f=>f.title==='Dernière aération'?f.title:f.title+' · '+plain(f.text)),['Humidité élevée · risque de moisissure, depuis plusieurs heures : ne séchez pas de linge ici, écartez les meubles du mur','Dernière aération']);
  // Salon · Cuisine, 26 Oct.: « Air humide » then « Humidité · aérer refroidirait… » said the humidity twice.
  const s=fresh();s.observations.indoor_humidity={value:65,quality:'valid',source:'sensor.h'};
  s.assessment={...s.assessment,reason:'heat_needed',action:'ok',level:'calm',needs:['heat','dry'],constraints:[],
    features:{...s.assessment.features,humidity:{status:'high',degree:2,lasting:false,measured:65,reachable:70},warmth:{occupied:true,heating:'on',slight:true,thermostat:{name:'Versatile Thermostat',preset:'frost',target:14,off_reason:null,lowered:true,reference:20}}}};
  assert.deepEqual(facts(s).map(f=>f.title+' · '+plain(f.text)),['Air humide · aérer refroidirait une pièce déjà fraîche','Un peu frais · thermostat en hors-gel : 14 °C visés']);
});
test('a room damp in the night waits for the morning: no « Aérez » at midnight',()=>{
  // Chambre P, 27 Oct. 00:13: « Aérez 60 min » while everyone slept; the humidity came down alone by 3 h.
  const v=fresh();v.observations.indoor_humidity={value:80,quality:'valid',source:'sensor.h'};
  v.assessment={...v.assessment,reason:'drying_night',action:'attendre',level:'calm',needs:['dry'],constraints:[],
    features:{...v.assessment.features,warmth:null,drying:{minutes:60,now:80,after:74,gain:6,tau:75,openings:6,morning:8,later:null},
      humidity:{status:'high',degree:3,lasting:false,measured:80,reachable:70}}};
  assert.equal(advice(v).title,'Rien à faire');assert.equal(plain(advice(v).line),'La nuit, aérez plutôt au réveil');
  assert.equal(slides(v)[0].pill,'Au mieux');
  assert.deepEqual(facts(v).map(f=>f.title+' · '+plain(f.text)),['Très humide · dès 8 h, si l’humidité reste haute']);
});
test('a room shedding its water by itself is not told to air',()=>{
  const v=fresh();v.observations.indoor_humidity={value:80,quality:'valid',source:'sensor.h'};
  v.assessment={...v.assessment,reason:'drying_alone',action:'attendre',level:'calm',needs:['dry'],constraints:[],
    features:{...v.assessment.features,warmth:null,drying:{minutes:45,now:80,after:75,gain:5,tau:45,openings:6,alone:77,net:2,later:null},
      humidity:{status:'high',degree:3,lasting:false,measured:80,reachable:70}}};
  assert.equal(advice(v).title,'Rien à faire');assert.equal(plain(advice(v).line),'Elle sèche d’elle-même, fenêtres fermées');
  assert.ok(facts(v).some(f=>plain(f.text)==='redescend seule : environ 77 % dans 45 min'),JSON.stringify(facts(v).map(f=>f.title+' · '+plain(f.text))));
});
test('damp walls: a remedy at work, a gesture, or a tip, never a fatality',()=>{
  const lines=v=>facts(v).map(f=>f.title+' · '+plain(f.text));
  const v=fresh();v.observations.indoor_humidity={value:68,quality:'valid',source:'sensor.h'};
  const mould={status:'high',degree:2,lasting:true,mould:true,surface:84,measured:68,reachable:70};
  // 26 Oct., Chambre P: the ventilation runs, it is the answer.
  v.assessment={...v.assessment,reason:'drying_slow',action:'attendre',level:'neutral',needs:['dry'],constraints:[],
    features:{...v.assessment.features,warmth:null,humidity:mould,air:{co2_status:'ok',pm25_status:'ok',voc_status:'ok',ventilation:{on:true,boost:false},coverage:'',message:''}}};
  assert.equal(advice(v).title,'Rien à faire');assert.equal(slides(v)[0].pill,'Au mieux');assert.equal(slides(v)[0].level,'calm');
  assert.deepEqual(lines(v),['Humidité élevée · risque de moisissure, depuis plusieurs heures, la VMC l’assèche']);
  // Nothing at work, one degree more is enough: the engine asks it.
  v.assessment={...v.assessment,reason:'warm_walls',action:'ok',level:'action',features:{...v.assessment.features,air:undefined,warm_walls:{degrees:1,target:19.7,surface:84,after:79}}};
  const a=advice(v);assert.equal(a.title,'Chauffez un peu plus');assert.match(plain(a.line),/Visez 19,7 °C/);
  assert.ok(!lines(v).some(l=>/linge/.test(l)),lines(v).join(' | '));
});
test('every banner title is a gesture or « Rien à faire »',()=>{
  const v=fresh(),GESTURE=/^(Aérez|Ouvrez|Refermez|Fermez|Gardez fermé|Lancez la VMC|Laissez ouvert|Rallumez le chauffage|Chauffez un peu plus|Adaptez les volets|Aération en cours|Encore \d+ min|Vous pouvez refermer|Renouvelez|Vérifiez|Rien à faire|Mesures (absentes|en chargement)|Bilan partiel)/;
  const reasons=['within_comfort','rain_open_windows','opening_blocked','verify_exterior','air_needed','cooling_possible','warming_possible','drying_possible','exchange_harmful','cooling_unavailable','heat_needed','drying_unavailable','drying_later','drying_slow','drying_night','drying_alone','ventilation_possible','incomplete_data','optional_air_change','gust_open_windows','short_air_change','sun_entering','rain_soon','precool_possible','precool_later','shared_volume','warm_walls','humid_outdoor','open_neutral','rehumidification_risk','shutter_protection'];
  for(const reason of reasons)for(const action of ['ok','ouvrir','fermer','attendre'])for(const level of ['calm','benefit','action','urgent','neutral']){
    v.assessment={...v.assessment,reason,action,level,features:{...v.assessment.features,warmth:{occupied:true,heating:'off'},humidity:{dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:90,mould:true,excess:2,source:'inside',reachable:70}}};
    const t=advice(v).title;assert.match(t,GESTURE,`${reason}/${action}/${level} → ${t}`);
  }
});
test('rooms sharing one air show the same advice, with the leading room’s measures',()=>{
  const v=fresh();
  v.assessment={...v.assessment,reason:'shared_volume',action:'ok',level:'action',features:{...v.assessment.features,
    volume:{lead:'Salon',reason:'air_needed',action:'ok',assessment:{reason:'air_needed',action:'ok',level:'action',features:{air:{co2_status:'high',pm25_status:'ok',voc_status:'ok',voc_unit:null,purifier:{on:null,speed:null},coverage:'',message:''}}},
      observations:{...v.observations,co2:{value:1250,quality:'valid',source:'sensor.co2',received_at:null,detail:null,unit:'ppm'}}}}};
  const a=advice(v);assert.equal(a.title,'Aération en cours');assert.match(plain(a.line),/CO₂ 1\s250 ppm/);
  assert.equal(plain(facts(v)[0].text),'conseil commun avec : Salon');
});

test('the home card keeps its display settings and refuses wrong ones',()=>{
  const c=cleanHomeConfig({type:'custom:hestia-comfort-home-card',rotate:false,show_rooms:false,rooms_open:true,animations:false,glass_effect:false});
  assert.equal(c.rotate,false);assert.equal(c.show_rooms,false);assert.equal(c.glass_effect,false);
  assert.throws(()=>cleanHomeConfig({type:'custom:hestia-comfort-home-card',show_scale:'oui'}));
  assert.throws(()=>cleanHomeConfig({type:'custom:hestia-comfort-card'}));
});

test('silent sensors are a state, not advice: loading after a start, then muted; one secondary sensor keeps the banner calm',()=>{
  const silent={value:null,quality:'unknown',source:'sensor.x',received_at:null,detail:'unavailable',unit:null};
  const v=fresh();v.observations={...v.observations,indoor_temperature:silent,indoor_humidity:silent,co2:silent};
  v.assessment={...v.assessment,reason:'incomplete_data',level:'neutral',action:'unknown',missing:['co2','indoor_humidity','indoor_temperature']};
  v.starting=true;let a=advice(v);assert.equal(a.title,'Mesures en chargement');assert.equal(a.pill,'Démarrage');
  v.starting=false;a=advice(v);assert.equal(a.title,'Mesures absentes');assert.match(plain(a.line),/3 capteurs ne répondent pas/);
  const w=fresh();w.observations={...w.observations,co2:silent};w.assessment={...w.assessment,reason:'incomplete_data',level:'neutral',missing:['co2']};
  a=advice(w);assert.equal(a.title,'Rien à faire');assert.equal(a.pill,'Un capteur muet');
});

test('the new formats and their settings: lists checked, alert hidden when nothing is asked',()=>{
  const c=cleanConfig({type:'custom:hestia-comfort-card',format:'alert',banner_blocks:['later'],scale_marks:[],tile_chips:['humidity','humidity'],hold_action:'page',hold_path:'/confort'});
  assert.deepEqual(c.tile_chips,['humidity']);assert.equal(c.format,'alert');
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',format:'grand'}));
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',scale_marks:['nuit']}));
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',hold_action:'vibrer'}));
  const st={why:false,tilesOpen:false,detailsOpen:false,uid:'t',toggle(){}};
  const calm=fresh();calm.assessment={...calm.assessment,level:'calm',reason:'within_comfort'};
  assert.equal(roomCard(calm,cleanConfig({type:'custom:hestia-comfort-card',format:'alert'}),st,'alert'),null);
  const asked=fresh();asked.assessment={...asked.assessment,level:'action',reason:'air_needed',action:'ouvrir'};
  assert.notEqual(roomCard(asked,cleanConfig({type:'custom:hestia-comfort-card',format:'alert'}),st,'alert'),null);
  assert.match(flat(roomCard(asked,cleanConfig({type:'custom:hestia-comfort-card',format:'mini'}),st,'mini')),/nc-mini-card/);
  // The alert is a low strip, never a banner: no « Synthèse », no module.
  assert.match(flat(roomCard(asked,cleanConfig({type:'custom:hestia-comfort-card',format:'alert'}),st,'alert')),/nc-alert-card/);
  const h=cleanHomeConfig({type:'custom:hestia-comfort-home-card',format:'list',list_order:'floor',banner_blocks:['rooms']});
  assert.equal(h.list_order,'floor');assert.throws(()=>cleanHomeConfig({type:'custom:hestia-comfort-home-card',format:'grille'}));
});

test('right after a start, one or two late secondary sensors do not hide the advice',()=>{
  const silent={value:null,quality:'unknown',source:'sensor.fp2',received_at:null,detail:'unavailable',unit:null};
  const v=fresh();v.starting=true;v.observations={...v.observations,illuminance:silent,'presence:binary_sensor.fp2':silent};
  v.assessment={...v.assessment,reason:'drying_slow',level:'calm',action:'attendre',missing:['illuminance','presence:binary_sensor.fp2']};
  assert.notEqual(advice(v).title,'Mesures en chargement');
});

test('the home card can open a page on a long press, in every format',()=>{
  assert.equal(homeAction(cleanHomeConfig({type:'custom:hestia-comfort-home-card'})),'none');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:hestia-comfort-home-card',hold_path:'/lovelace/maison'})),'page');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:hestia-comfort-home-card',format:'list'})),'popup');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:hestia-comfort-home-card',format:'list',hold_action:'page',hold_path:'/maison'})),'page');
});
test('a running ventilation or purifier is never counted out of your range',()=>{
  const v=fresh();v.assessment={...v.assessment,level:'calm',reason:'within_comfort',needs:[],features:{...v.assessment.features,air:{...(v.assessment.features?.air??{}),co2_status:'ok',ventilation:{on:true,boost:false}}}};
  v.observations={...v.observations,purifier:{value:true,quality:'valid',source:'fan.p'}};
  const st={why:false,tilesOpen:false,detailsOpen:false,uid:'t',toggle(){}};
  const text=plain(roomCard(v,cleanConfig({type:'custom:hestia-comfort-card',format:'measures',modules:['air','humidity']}),st,'measures'));
  // The devices at work are said in « Appareils », as on the full card (6 November).
  assert.match(text,/Purificateur en marche/);assert.match(text,/VMC en marche/);assert.doesNotMatch(text,/à surveiller/);
});
test('the home card names what a room needs, as measured',async()=>{
  const {needs}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v=fresh();v.observations={...v.observations,indoor_humidity:{value:68,quality:'valid',unit:'%'},voc:{value:282,quality:'valid',unit:'ppb'}};
  v.assessment={...v.assessment,level:'action',needs:['dry'],openings:[],features:{...v.assessment.features,air:{...(v.assessment.features?.air??{}),co2_status:'ok',voc_status:'high',ventilation:{on:true,boost:false}}}};
  assert.deepEqual(needs(v),['68 % trop humide','282 COV élevés']);
  // 26 Oct., Salon · Cuisine on the home card: « un peu frais » came first though the heating had it in hand.
  v.assessment={...v.assessment,level:'calm',needs:['heat','dry'],features:{...v.assessment.features,warmth:{occupied:true,heating:'on',slight:true}}};
  assert.equal(needs(v)[0],'68 % trop humide');assert.equal(needs(v).at(-1),'un peu frais');
});
test('a cover driven by Adaptive Cover Pro has its own tile, and asks nothing while it drives',async()=>{
  const {tiles}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v=fresh(),base={entity_id:'binary_sensor.w',mode:'connected',position:100,state:'open',advice:null,message:'',shade_fraction:null,shade_model:'unknown',manual_override:false,automatic:true,cover:'cover.v',driver:'adaptive_cover_pro',sun_front:true,target:30};
  v.assessment={...v.assessment,features:{...v.assessment.features,shutters:[base]}};
  const c=cleanConfig({type:'custom:hestia-comfort-card',modules:['shutters']});
  let t=tiles(v,c).find(x=>x.label==='Volet');
  assert.deepEqual([t.value,t.note,t.out,t.entity],['Ouvert','automatique · soleil devant',false,'cover.v']);
  v.assessment.features.shutters=[{...base,automatic:false,advice:'close'}];
  t=tiles(v,c).find(x=>x.label==='Volet');assert.deepEqual([t.note,t.out,t.level],['à fermer',true,'action']);
  v.assessment.features.shutters=[{...base,automatic:false,advice:'close',soon:true,sun_start:'2026-10-19T13:50:00+02:00'}];
  t=tiles(v,c).find(x=>x.label==='Volet');assert.match(t.note,/^à fermer avant \d\d h \d\d$/);
});

test('rooms sharing one air are one choice in the card editor, led by the best equipped room',()=>{
  const entries=[{entry_id:'b',title:'Buanderie',area_id:null,volume:[],volume_name:null},
    {entry_id:'c',title:'Cuisine',area_id:null,volume:['s'],volume_name:'Salon · Cuisine'},
    {entry_id:'s',title:'Salon',area_id:null,volume:['c'],volume_name:'Salon · Cuisine'}];
  assert.deepEqual(roomChoices(entries),[{value:'b',label:'Buanderie'},{value:'s',label:'Salon · Cuisine'}]);
  // A card already set on the kitchen keeps its room: nothing moves on the dashboard.
  assert.deepEqual(roomChoices(entries,'c').find(o=>o.label==='Salon · Cuisine'),{value:'c',label:'Salon · Cuisine'});
});

test('high humidity is said without guessing its cause',()=>{
  // 20 Oct.: two days of rain, a bedroom told « douche, cuisine ou linge », then « la respiration »: neither had happened.
  const v=fresh(),hum={dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:88,mould:true,excess:1,source:'inside',reachable:75};
  for(const title of ['Chambre P','Salle de bain','Cuisine','Salon']){
    v.title=title;v.assessment={...v.assessment,reason:'drying_unavailable',level:'calm',action:'attendre',features:{...v.assessment.features,humidity:hum}};
    assert.deepEqual(facts(v).map(f=>f.title+' · '+plain(f.text)),['Humidité élevée · risque de moisissure : ne séchez pas de linge ici, écartez les meubles du mur']);
  }
});
test('rooms sharing one air show each measure once, under the room that has it',()=>{
  const r=(value,source,unit=null)=>({value,quality:'valid',source,unit});
  const calm=v=>{v.assessment={...v.assessment,level:'calm',reason:'within_comfort',needs:[],features:{...v.assessment.features,air:{...(v.assessment.features?.air??{}),co2_status:'ok',voc_status:'ok'}}};return v;};
  // Salon, 21 October: its CO₂ sensor, the kitchen's VOC sensor and purifier; the kitchen reads the living room's CO₂.
  const salon=calm(fresh());salon.title='Salon';salon.volume=[{entry_id:'c',title:'Cuisine'}];salon.volume_name='Salon · Cuisine';
  salon.observations={...salon.observations,indoor_temperature:r(20.2,'sensor.st','°C'),co2:r(441,'sensor.co2','ppm'),voc:r(29,'sensor.voc'),purifier:r(false,'fan.p')};
  salon.inherited={voc:'Cuisine',purifier:'Cuisine'};
  const cuisine=calm(fresh());cuisine.title='Cuisine';
  cuisine.observations={...cuisine.observations,indoor_temperature:r(20.1,'sensor.ct','°C'),co2:r(441,'sensor.co2','ppm'),voc:r(29,'sensor.voc'),purifier:r(false,'fan.p')};
  cuisine.inherited={co2:'Salon'};
  const st={why:false,tilesOpen:true,detailsOpen:false,uid:'t',toggle(){}};
  const text=plain(roomCard(salon,cleanConfig({type:'custom:hestia-comfort-card',format:'measures',modules:['air','temperature'],scale_marks:[]}),st,'measures',[cuisine]));
  // The air as a list grouped by room (31 October): CO₂ under the living room, VOC and the purifier under the kitchen.
  const air=modules(salon,cleanConfig({type:'custom:hestia-comfort-card',modules:['air']}),[cuisine]).find(m=>m.key==='air');
  assert.deepEqual(air.slides.map(x=>[x.label,x.room]),[['CO₂','Salon'],['COV','Cuisine'],['Purificateur','Cuisine']]);
  assert.equal((text.match(/Purificateur/g)??[]).length,1);
  // The full card's Ressenti (6 November): the leading room's warmth; humidity not ticked, so not shown at all.
  assert.match(text,/20,2/);assert.doesNotMatch(text,/Humidité/);
  // A room shown alone says where a borrowed measure comes from.
  assert.match(plain(roomCard(cuisine,cleanConfig({type:'custom:hestia-comfort-card',format:'measures',modules:['air']}),st,'measures')),/Salon/);
  const alone=modules(cuisine,cleanConfig({type:'custom:hestia-comfort-card',modules:['air']})).find(m=>m.key==='air');
  assert.deepEqual(alone.slides.map(x=>[x.label,x.room]),[['CO₂','Salon'],['COV','Cuisine'],['Purificateur','Cuisine']]);
});
test('an open window that changes nothing is not told that opening would bring nothing',()=>{
  const v=fresh();v.assessment={...v.assessment,reason:'open_neutral',action:'ok',level:'calm',needs:[]};
  v.observations={...v.observations,'window:w':{value:true,quality:'valid',source:'w'}};
  const a=advice(v);
  assert.equal(a.title,'Rien à faire');assert.doesNotMatch(plain(a.line),/Ouvrir/);
});
test('a damp room with nothing to do is not « Tout va bien », and a « Refermez » says why the humidity stays',async()=>{
  const {facts}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  // Chambre A, 21 October: 68.9 %, airing would barely help.
  const a=fresh();a.assessment={...a.assessment,reason:'drying_slow',action:'attendre',level:'calm',needs:['dry']};
  assert.equal(advice(a).pill,'Au mieux');assert.notEqual(slides(a)[0].pill,'Tout va bien');
  assert.equal(advice(a).disk,'drop');
  const ok=fresh();ok.assessment={...ok.assessment,reason:'within_comfort',action:'ok',level:'calm',needs:[]};
  assert.equal(advice(ok).pill,undefined);
  assert.equal(advice(ok).disk,'check');
  // Chambre P: 73 %, the open window cools it for one point of humidity.
  const p=fresh();p.twin={status:'ready',days:10,samples:400,next_hour:null,precision:{hours:24,temperature:0.2,humidity:2},progress:{percent:89,complete:false,parts:{heating:0},seen:{days:10,airings:7}}};
  p.assessment={...p.assessment,reason:'exchange_harmful',action:'fermer',level:'action',needs:['dry'],features:{...p.assessment.features,drying:{minutes:60,now:73,after:72,gain:1.1,tau:170,openings:7,later:null}}};
  const lines=facts(p).map(x=>`${x.title} · ${x.text}`);
  assert.ok(lines.includes('Humidité · l’aération ne la baisserait que d’un point à peine'),lines.join(' | '));
  assert.ok(!lines.some(l=>l.startsWith('Apprentissage')),lines.join(' | '));
});
test('the replay of 10 days at home, 21 October: what is held back, unread or already said is never said wrong',()=>{
  const lines=v=>facts(v).map(x=>`${x.title} · ${plain(x.text)}`);
  // Rain on the exposed windows, a sheltered one open: the others stay shut, the banner does not say opening brings nothing.
  const blocked=fresh();blocked.assessment={...blocked.assessment,reason:'opening_blocked',action:'attendre',level:'calm',needs:['dry'],constraints:['rain']};
  assert.match(plain(advice(blocked).line),/n’est pas possible/);
  assert.ok(lines(blocked).includes('Fenêtres · à garder fermées : pluie sur les ouvrants exposés'),lines(blocked).join(' | '));
  assert.ok(lines(blocked).includes('Humidité · elle attendra que l’on puisse aérer'),lines(blocked).join(' | '));
  blocked.observations={...blocked.observations,'window:w':{value:true,quality:'valid',source:'w'}};
  assert.ok(lines(blocked).some(l=>l.startsWith('Autres fenêtres')),lines(blocked).join(' | '));
  // « Gardez fermé … le besoin attendra »: not said again underneath.
  const keep=fresh();keep.assessment={...keep.assessment,reason:'opening_blocked',action:'attendre',level:'action',needs:['dry'],constraints:['rain']};
  assert.ok(!lines(keep).some(l=>/garder fermées|attendra/.test(l)),lines(keep).join(' | '));
  // A room that cannot be read explains no advice.
  const blind=fresh();blind.assessment={...blind.assessment,reason:'drying_slow',action:'attendre',level:'neutral',needs:['dry'],missing:['indoor_temperature']};
  blind.observations={...blind.observations,indoor_temperature:{value:null,quality:'unknown',source:'sensor.t',detail:'unavailable'}};
  assert.equal(advice(blind).title,'Mesures absentes');assert.deepEqual(facts(blind),[]);
  // Asked to air for the steam: no « it will barely lower it » underneath.
  const steam=fresh();steam.assessment={...steam.assessment,reason:'short_air_change',action:'ouvrir',level:'action',needs:['dry']};
  assert.ok(!lines(steam).some(l=>/baissera peu|baisserait|pas assez baisser/.test(l)),lines(steam).join(' | '));
});
test('the sun that helps is said, and each learned measure gets its optimised advice',()=>{
  const lines=v=>facts(v).map(x=>`${x.title} · ${plain(x.text)}`);
  // Chambre A, 21 October at 15 h: cool, the sun on its south window.
  const a=fresh();a.assessment={...a.assessment,reason:'within_comfort',action:'ok',level:'calm',needs:[],features:{...a.assessment.features,benefits:[{kind:'sun_warms',openings:['w'],watts:430,keep_shut:true}]}};
  assert.ok(lines(a).includes('Soleil · il réchauffe la pièce : volets et rideaux ouverts, fenêtre fermée'),lines(a).join(' | '));
  // Asked to air, the window is not told to stay shut.
  a.assessment={...a.assessment,reason:'air_needed',action:'ouvrir',level:'action'};
  assert.ok(lines(a).includes('Soleil · il réchauffe la pièce : volets et rideaux ouverts'),lines(a).join(' | '));
  // « Refermez », learned: the open window's cost in the banner, « Conseil optimisé » in the pill.
  const p=fresh();p.assessment={...p.assessment,reason:'exchange_harmful',action:'fermer',level:'action',needs:['dry'],
    features:{...p.assessment.features,learned:{now:18.3,after:17.6,minutes:30,measure:'temperature',openings:7,days:10,precision:{temperature:0.17,humidity:1.9},closing:true}}};
  const ad=advice(p);assert.equal(ad.pill,'Conseil optimisé');assert.match(plain(ad.line),/de 18,3 à 17,6 °C en 30 min/);
  // Not learned yet: the line names the measure that lacks, not the whole room.
  const m=fresh();m.twin={status:'ready',days:10,samples:480,next_hour:null,precision:{hours:24,temperature:0.24,humidity:1.3},
    progress:{percent:68,complete:false,parts:{windows:0},seen:{days:10,airings:0,open:0},ready:{humidity:false,temperature:false,air:[]}}};
  m.assessment={...m.assessment,reason:'drying_possible',action:'ouvrir',level:'action',needs:['dry']};
  assert.ok(lines(m).includes('Apprentissage · humidité : 0 aération sur 5, résultat estimé'),lines(m).join(' | '));
});
test('an airing later says its source and is not denied underneath',()=>{
  // Chambre P, 21 October: « Aérez vers … h », from its 7 learned airings.
  const p=fresh();p.assessment={...p.assessment,reason:'drying_later',action:'attendre',level:'benefit',needs:['dry'],
    features:{...p.assessment.features,drying:{minutes:60,now:73,after:72,gain:1.1,tau:170,openings:7,later:{minutes:60,now:73,after:68,gain:5,time:'2026-10-22T08:00:00+02:00'}}}};
  const ad=advice(p);assert.match(ad.title,/^Aérez vers /);assert.equal(ad.learned,'d’après 7 aérations');
  assert.ok(!facts(p).some(f=>/baisserait|pas assez baisser/.test(plain(f.text))),facts(p).map(f=>plain(f.text)).join(' | '));
  // Fewer than five airings: the figure is the ordinary room's, no flask.
  p.assessment.features.drying={...p.assessment.features.drying,openings:2};
  assert.equal(advice(p).learned,undefined);
});
test('the season changes what the card says',()=>{
  const lines=v=>facts(v).map(x=>`${x.title} · ${plain(x.text)}`);
  // Winter: a warm room is not cooled by opening; the heating is turned down.
  const w=fresh();w.observations={...w.observations,heating:{value:'off',quality:'valid',source:'climate.t'}};
  w.assessment={...w.assessment,reason:'cooling_unavailable',action:'attendre',level:'calm',needs:['cool'],features:{...w.assessment.features,season:{known:true,weight:0,outdoor_mean:6,minimum:19,maximum:24,heated:true,name:'winter',group:'winter'}}};
  assert.match(plain(advice(w).line),/refroidirait trop vite/);
  assert.ok(lines(w).includes('Pièce chaude · baissez le chauffage plutôt que d’ouvrir'),lines(w).join(' | '));
  // Winter: a short, brisk airing, said why.
  w.assessment={...w.assessment,reason:'drying_possible',action:'ouvrir',level:'action',needs:['dry']};
  assert.ok(lines(w).some(l=>l.startsWith('Aération d’hiver')),lines(w).join(' | '));
});

test('the four sections are settings of their own: À savoir topics and count, detail lines, the graph',async()=>{
  const {factBox,details}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const c=cleanConfig({type:'custom:hestia-comfort-card',insight_topics:['sun'],insight_max:2,detail_rows:['range'],horizon_subjects:['humidity'],show_horizon:false});
  assert.deepEqual([c.insight_topics,c.insight_max,c.detail_rows,c.horizon_subjects,c.show_horizon],[['sun'],2,['range'],['humidity'],false]);
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',insight_topics:['weather']}),/À savoir/);
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',insight_max:0}),/de 1 à 8/);
  const v=fresh();v.assessment={...v.assessment,features:{...(v.assessment.features??{}),season:{minimum:19,maximum:23,heated:true,known:true,name:'autumn'},
    benefits:[{kind:'sun_warms',openings:[],watts:300,keep_shut:true}],humidity:{status:'high',degree:2,lasting:true,measured:70}}};
  const text=r=>JSON.stringify(r);
  assert.match(text(factBox(v,[],cleanConfig({type:'custom:hestia-comfort-card',insight_topics:['sun']}))),/Soleil/);
  assert.doesNotMatch(text(factBox(v,[],cleanConfig({type:'custom:hestia-comfort-card',insight_topics:['sun']}))),/Humidité/);
  // Hidden: nothing is drawn (Lit's « nothing », not a template).
  assert.equal(factBox(v,[],cleanConfig({type:'custom:hestia-comfort-card',show_insights:false})).strings,undefined);
  assert.equal(details(v,cleanConfig({type:'custom:hestia-comfort-card',detail_rows:[]})).length,0);
  assert.ok(text(details(v,cleanConfig({type:'custom:hestia-comfort-card',detail_rows:['range']}))).includes('Votre plage de confort'));
});

test('« À savoir » of the 3.0 advisor follows the card’s settings: shown or not, its headings, its lines (4 November)',async()=>{
  const {factBox}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v={...fresh(),advisor:{title:'Rien à faire',attributes:{regle:'nothing',geste:'nothing',a_essayer:'Ouvrez 5 min à 14 h',douteuses:'COV',bon_a_savoir:['Il fera doux demain','La VMC tourne']}}};
  const text=r=>JSON.stringify(r),box=o=>text(factBox(v,[],cleanConfig({type:'custom:hestia-comfort-card',...o})));
  assert.match(box({}),/Pour le geste.*À surveiller.*Bon à savoir/);
  assert.equal(factBox(v,[],cleanConfig({type:'custom:hestia-comfort-card',show_insights:false})).strings,undefined);
  assert.doesNotMatch(box({insight_groups:['know']}),/Pour le geste|À surveiller/);
  assert.match(box({insight_groups:['know']}),/La VMC tourne/);
  // So many lines at most, the first headings first.
  assert.doesNotMatch(box({insight_max:2}),/Bon à savoir/);
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',insight_groups:['météo']}),/À savoir/);
});

test('the scale switch turns the scale off and on, even though the form sends back its hidden list of marks',async()=>{
  const {nextConfig,scaleShown}=await import(pathToFileURL(join(temp,'editor.mjs')));
  const base=cleanConfig({type:'custom:hestia-comfort-card',format:'full'});
  // What Home Assistant's form sends: every field, the hidden marks included.
  const off=cleanConfig(nextConfig(base,{show_scale:false,scale_marks:['band','day','out'],rotate:true}));
  assert.equal(scaleShown(off),false);
  const on=cleanConfig(nextConfig(off,{show_scale:true,scale_marks:['band','day','out']}));
  assert.equal(scaleShown(on),true);
  // Another switch leaves a card's own marks untouched.
  const kept=cleanConfig(nextConfig(cleanConfig({type:'custom:hestia-comfort-card',scale_marks:['band']}),{show_scale:true,scale_marks:['band','day','out'],rotate:false}));
  assert.deepEqual(kept.scale_marks,['band']);
});

test('the graph shows when the gesture changes something, or always with the trend, and folds away instead of jumping',async()=>{
  const {horizonShown,horizonBox}=await import(pathToFileURL(join(temp,'views/horizon.mjs')));
  const subject=(kind,needed,subject='temperature')=>({subject,kind,needed,unit:'°C',start:'2026-10-26T22:00:00+01:00',step_minutes:30,base:[19.8,19.7,19.7,19.8],
    gesture:kind==='trend'?null:[19.8,19.6,19.7,19.8],bands:[],extra:[],result:{drop:0,top:19.8,low:19.7}});
  const barely=[subject('air',false),subject('trend',false)],clear=[subject('air',true),subject('trend',false)];
  assert.deepEqual(horizonShown(barely).map(h=>h.kind),[]);
  assert.deepEqual(horizonShown(barely,'always').map(h=>h.kind),['trend']);
  assert.deepEqual(horizonShown(clear,'always').map(h=>h.kind),['air']);
  assert.deepEqual(horizonShown([subject('dry',true,'humidity'),subject('trend',false)],'always',['temperature']).map(h=>h.kind),['trend']);
  assert.deepEqual(horizonShown([subject('air',false),subject('sun',false),subject('trend',false)],'always').map(h=>h.kind),['sun']);
  // An older engine, without `needed`: drawn as before.
  assert.deepEqual(horizonShown([{...subject('air'),needed:undefined}]).map(h=>h.kind),['air']);
  assert.equal(cleanConfig({type:'custom:hestia-comfort-card',horizon_mode:'always'}).horizon_mode,'always');
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',horizon_mode:'parfois'}),/graphique/);
  const o={plage:()=>null,second:false,onTab:()=>{},uid:'test'};
  const text=r=>JSON.stringify(r);
  assert.equal(horizonBox(barely,{...o,uid:'never'}),Symbol.for('lit-nothing'));
  assert.equal(horizonBox(clear,o).values[0],'open');
  // The advice no longer needs it: the last drawing stays while it folds, hidden from screen readers.
  const folding=horizonBox(barely,o);
  assert.deepEqual(folding.values.slice(0,3),['','true',true]);
  assert.match(text(folding),/en aérant/);
});
test('where to open is said under the advice, only while airing is asked',()=>{
  const v=fresh();v.names={ouest:'Fenêtre Ouest',cuisine:'Fenêtre Cuisine',sd:'Porte-fenêtre SD'};
  v.observations={...v.observations,co2:{value:1300,quality:'valid',source:'sensor.co2'}};
  const plan={open:['ouest','cuisine'],keep:[],path:'opposite',into:null,faster:null,learned:0,avoid:[{entity_id:'sd',why:'rain'}]};
  v.assessment={...v.assessment,action:'ouvrir',level:'action',reason:'air_needed',needs:['air'],constraints:[],missing:[],features:{...v.assessment.features,airflow:plan}};
  const said=()=>facts(v).map(f=>f.title+' · '+f.text);
  assert.deepEqual(said().slice(0,2),['Ouvrez Fenêtre Ouest et Fenêtre Cuisine · l’air traverse de part en part','Pas Porte-fenêtre SD · la pluie y entrerait']);
  // Already open: complete it, with the learned speed once known.
  v.assessment.features.airflow={...plan,open:['ouest'],keep:['cuisine'],faster:2,learned:4,avoid:[]};
  assert.equal(said()[0],'Ouvrez aussi Fenêtre Ouest · l’air traverse de part en part · 2 fois plus rapide (d’après 4 aérations)');
  // Nothing asked: nothing said, the banner stays the only gesture.
  v.assessment={...v.assessment,action:'ok',level:'calm',reason:'within_comfort',needs:[]};
  assert.equal(said().some(t=>t.startsWith('Ouvrez')),false);
});

test('the trend is green only when it heads back to your range (30 October)',()=>{
  const v=fresh(),curve=way=>({slope:way==='stable'?0:way==='up'?5:-5,way,points:[[28,66],[16,66],[2,66]]});
  v.assessment={...v.assessment,features:{...v.assessment.features,trends:{indoor:null,outdoor:null,window_minutes:30,message:'',curves:{humidity:curve('down'),co2:null}}}};
  assert.equal(trendOf(v,'humidity','high').tone,'better');
  assert.equal(trendOf(v,'humidity','low').tone,'worse');
  // In your range it may move: said in grey, never green.
  assert.equal(trendOf(v,'humidity',null).tone,'steady');
  v.assessment.features.trends.curves.humidity=curve('stable');
  assert.equal(trendOf(v,'humidity','high').tone,'steady');
  // Under ten minutes of measures: no arrow at all.
  assert.equal(trendOf(v,'co2','high'),undefined);
});
test('« À savoir » says how to act and what to watch; the last airing goes to the « i » (30 October, evening)',()=>{
  const flat=t=>t==null?'':Array.isArray(t)?t.map(flat).join(''):typeof t!=='object'?String(t):t.strings?t.strings.map((x,i)=>x+(i<t.values.length?flat(t.values[i]):'')).join(''):'';
  const v=fresh();v.names={ouest:'Fenêtre Ouest'};
  v.observations={...v.observations,co2:{value:1300,quality:'valid',source:'sensor.co2'}};
  v.feedback={last:{measure:'voc',before:384,after:313,predicted:null}};
  v.assessment={...v.assessment,action:'ouvrir',level:'action',reason:'air_needed',needs:['air'],constraints:[],missing:[],
    features:{...v.assessment.features,airflow:{open:['ouest'],keep:[],path:'one_side',into:null,faster:null,learned:0,avoid:[]}}};
  const box=flat(factBox(v));
  assert.match(box,/data-group=gesture|Pour le geste/);assert.doesNotMatch(box,/Appris|Dernière aération/);
  // Whether to trust the advice is the « i »'s: the last airing and what the room learned.
  assert.match(flat(whyRoom(v,slides(v)[0])),/Dernière aération/);
});
test('the formats come in three kinds, as Hestia Weather’s editor (30 October)',()=>{
  assert.deepEqual(['full','tile','intermediate','temperature','measures','horizon','mini','alert'].map(f=>kindOf(f)),['large','large','large','piece','piece','piece','small','small']);
  // One foldable large card only (30 October, evening): « Intermédiaire » is no longer offered, an older card keeps it.
  assert.deepEqual(Object.values(KINDS).flat().sort(),['air','alert','devices','feel','full','heating','horizon','humidity','measures','mini','openings','temperature','tile']);
  assert.equal(cleanConfig({type:'custom:hestia-comfort-card',format:'humidity',piece_style:'compact'}).piece_style,'compact');
  assert.throws(()=>cleanConfig({type:'custom:hestia-comfort-card',piece_style:'grande'}));
  // An older card keeps its format: nothing to change on the dashboard.
  for(const format of ['full','tile','intermediate','mini','measures','alert'])assert.equal(cleanConfig({type:'custom:hestia-comfort-card',format}).format,format);
});
test('the modules: one air shows each room’s humidity, its windows and sun once (30 October)',()=>{
  const room=(title,h,inherited={})=>{const v=fresh();v.title=title;v.inherited=inherited;
    v.observations={...v.observations,indoor_temperature:{value:20.5,quality:'valid',source:'sensor.t_'+title},indoor_humidity:{value:h,quality:'valid',source:'sensor.h_'+title},
      'window:binary_sensor.w':{value:true,quality:'valid',source:'binary_sensor.w'}};return v;};
  const config={type:'custom:hestia-comfort-card',modules:['windows','air','humidity','shutters','coordination','temperature']};
  const list=modules(room('Salon',58),config,[room('Cuisine',66)]);
  const hum=list.find(m=>m.key==='humidity');
  // One air's rooms one after the other (31 October), those out of range first; here neither is: the rooms' order.
  assert.deepEqual(hum.slides.map(r=>r.label),['Salon','Cuisine']);
  const open=list.find(m=>m.key==='openings');
  assert.equal([open.main,...open.stats].filter(x=>(x.label??'')==='Fenêtres').length,1);
  assert.equal(list[0].key,'temperature');
});
test('one air says its windows to open in one line (30 October)',()=>{
  // Salon asks for Fenêtre Ouest, Cuisine for Fenêtre Cuisine, both doors already open: one gesture, one line.
  const room=(title,open)=>{const v=fresh();v.title=title;v.names={ouest:'Fenêtre Ouest',cuisine:'Fenêtre Cuisine',sd:'Porte-fenêtre SD'};
    v.observations={...v.observations,co2:{value:1300,quality:'valid',source:'sensor.co2'}};
    v.assessment={...v.assessment,action:'ouvrir',level:'action',reason:'air_needed',needs:['air'],constraints:[],missing:[],
      features:{...v.assessment.features,airflow:{open:[open],keep:['sd'],path:'two_sides',into:null,faster:null,learned:0,avoid:[]}}};return v;};
  const said=factList(room('Salon','ouest'),[room('Cuisine','cuisine')]).filter(f=>f.title.startsWith('Ouvrez')).map(f=>f.title);
  assert.deepEqual(said,['Ouvrez aussi Fenêtre Ouest et Fenêtre Cuisine']);
});
test('one air never says « refermer » and « laisser ouvert », nor « refroidirait » with a milder outside (27 October)',()=>{
  // Salon 20,3 °C open, Cuisine 19,6 °C open and a little cool, 22,3 °C outside: the open window warms them.
  const room=(title,ti,hi,reason,needs,features)=>{const v=fresh();v.title=title;
    v.observations={...v.observations,indoor_temperature:{value:ti,quality:'valid',source:'sensor.t'},indoor_humidity:{value:hi,quality:'valid',source:'sensor.h'},
      outdoor_temperature:{value:22.3,quality:'valid',source:'sensor.te'},'window:binary_sensor.c':{value:true,quality:'valid',source:'binary_sensor.c'}};
    v.assessment={...v.assessment,action:'ok',level:'calm',reason,needs,missing:[],constraints:[],temperature_delta:22.3-ti,features:{air:{co2_status:'ok',pm25_status:'ok',voc_status:'ok'},...features}};return v;};
  const salon=room('Salon',20.3,61,'open_neutral',['dry'],{open_warms:true,humidity:{status:'high',degree:1,measured:61,trend:'stable'}});
  const kitchen=room('Cuisine',19.6,68,'heat_needed',['heat','dry'],{humidity:{status:'high',degree:2,measured:68,trend:'improving'},
    warmth:{occupied:true,heating:'on',slight:true,outdoor_warms:true,warming:true}});
  const said=factList(salon,[kitchen]).map(f=>`${f.title} · ${f.text}`).join(' | ');
  assert.doesNotMatch(said,/refermer/);assert.doesNotMatch(said,/refroidirait/);
  assert.match(said,/Fenêtre ouverte · elle ne fait presque pas baisser l’humidité/);
  const flat=t=>t==null?'':typeof t!=='object'?String(t):t.strings?t.strings.map((x,i)=>x+(i<t.values.length?flat(t.values[i]):'')).join(''):'';
  assert.match(flat(advice(salon).line),/réchauffe la pièce/);
});
test('the review card is a summary unless « full » is chosen, its title trimmed',()=>{
  assert.deepEqual(cleanReviewConfig({type:'custom:hestia-comfort-review-card'}),{type:'custom:hestia-comfort-review-card',format:'summary'});
  assert.deepEqual(cleanReviewConfig({type:'custom:hestia-comfort-review-card',format:'full',title:'  Maison  '}),{type:'custom:hestia-comfort-review-card',format:'full',title:'Maison'});
  assert.equal(cleanReviewConfig({type:'custom:hestia-comfort-review-card',format:'grand',title:' '}).format,'summary');
  assert.throws(()=>cleanReviewConfig({type:'custom:hestia-comfort-card'}));
});

test('the full home card chooses its sections, what folds away and the period shown first',()=>{
  const c=cleanHomeConfig({type:'custom:hestia-comfort-home-card',sections:['themes','rooms_chart','curve'],folded:['curve'],period:'week',more_open:true});
  assert.deepEqual([c.sections,c.folded,c.period,c.more_open],[['themes','rooms_chart','curve'],['curve'],'week',true]);
  assert.throws(()=>cleanHomeConfig({type:'custom:hestia-comfort-home-card',sections:['graphique']}));
  assert.throws(()=>cleanHomeConfig({type:'custom:hestia-comfort-home-card',period:'année'}));
});
test('a new hass from an unrelated state change does not redraw the cards',()=>{
  const connection={},hass={connection,themes:{darkMode:true},user:{is_admin:true}};
  const changed=old=>new Map([['hass',old]]);
  assert.equal(hassMatters(changed({...hass,states:{}}),{...hass,states:{a:1}}),false);
  assert.equal(hassMatters(changed(hass),{...hass,themes:{darkMode:false}}),true);
  assert.equal(hassMatters(changed(hass),{...hass,connection:{}}),true);
  assert.equal(hassMatters(changed(undefined),hass),true);
  assert.equal(hassMatters(new Map([['hass',hass],['config',{}]]),hass),true);
});
test('the Air module shows each of its measures the same way, one after the other, those out first (30 October, evening)',()=>{
  const v=fresh();
  v.observations={...v.observations,co2:{value:1250,quality:'valid',source:'sensor.co2',unit:'ppm'},voc:{value:420,quality:'valid',source:'sensor.voc',unit:''}};
  v.assessment={...v.assessment,level:'action',reason:'air_needed',action:'ouvrir',needs:['air'],
    features:{...v.assessment.features,air:{co2_status:'high',pm25_status:'not_configured',voc_status:'high',voc_unit:null,purifier:{on:null,speed:null},coverage:'',message:''}}};
  const air=modules(v,{type:'custom:hestia-comfort-card',modules:['air']}).find(m=>m.key==='air');
  assert.deepEqual(air.slides.map(x=>x.label),['CO₂','COV']);
  // The banner keeps one advice: both reasons are on its line.
  assert.equal(slides(v).length,1);
});
test('one air: the banner says the leading room’s advice, with what it learned (31 October)',()=>{
  const flat=t=>t==null?'':Array.isArray(t)?t.map(flat).join(''):typeof t!=='object'?String(t):t.strings?t.strings.map((x,i)=>x+(i<t.values.length?flat(t.values[i]):'')).join(''):'';
  const lead=fresh();lead.title='Cuisine';
  lead.observations={...lead.observations,co2:{value:1250,quality:'valid',source:'sensor.co2',unit:'ppm'}};
  lead.assessment={...lead.assessment,level:'action',reason:'air_needed',action:'ouvrir',needs:['air'],
    features:{...lead.assessment.features,air:{co2_status:'high',pm25_status:'not_configured',voc_status:'ok',voc_unit:null,purifier:{on:null,speed:null},coverage:'',message:''},
      learned:{now:1250,after:700,minutes:10,measure:'co2',openings:6,days:19,precision:{temperature:.4,humidity:1}}}};
  const salon=fresh();salon.title='Salon';
  salon.assessment={...salon.assessment,level:'action',reason:'shared_volume',action:'ouvrir',needs:['dry'],features:{...salon.assessment.features,volume:{lead:'Cuisine',reason:'air_needed',action:'ouvrir'}}};
  const st={why:false,tilesOpen:true,detailsOpen:false,uid:'t',toggle(){}};
  const card=flat(roomCard(salon,{type:'custom:hestia-comfort-card',format:'full',modules:['air']},st,'full',[lead]));
  // The « i » says it: the advice comes from what the leading room learned.
  assert.match(card,/conseil optimisé, d’après 6 aérations/);
});
test('the banner draws each gesture as its scene: the window and which way the air goes, the VMC, the radiator (2 November)',async()=>{
  const {sceneFor,hourOf}=await import(pathToFileURL(join(temp,'ui/scene.mjs')));
  const room=(reason,o={})=>{const v=fresh();v.assessment={...v.assessment,reason,needs:o.needs??[],openings:o.open?[{name:'Fenêtre',open:true,flags:[]}]:[],sun:{elevation:o.sun??30,azimuth:180},temperature_delta:o.delta??null};return v;};
  const s=(title,disk,level='action')=>({title,disk,level});
  assert.deepEqual(sceneFor(s('Refermez','shut'),room('exchange_harmful',{open:true,delta:-6})),{k:'win',m:'open',flow:'in-cold',hour:'day'});
  assert.equal(sceneFor(s('Refermez','shut'),room('exchange_harmful',{open:true,delta:4})).flow,'in-heat');
  assert.equal(sceneFor(s('Refermez','shut'),room('voc_outdoor',{open:true})).flow,'in-dust');
  assert.equal(sceneFor(s('Refermez','shut'),room('rehumidification_risk',{open:true})).flow,'in-humid');
  assert.equal(sceneFor(s('Fermez, il pleut','rain'),room('rain_open_windows',{open:true})).flow,'in-rain');
  assert.equal(sceneFor(s('Refermez avant la pluie','rain'),room('rain_soon',{open:true})).sky,'storm');
  // Airing under way: what leaves is what the room needed to lose.
  assert.equal(sceneFor(s('Aération en cours','open','benefit'),room('short_air_change',{open:true,needs:['air']})).flow,'out-stale');
  assert.equal(sceneFor(s('Encore 4 min d’aération','open','benefit'),room('drying_possible',{open:true,needs:['dry']})).flow,'out-humid');
  assert.equal(sceneFor(s('Laissez ouvert cette nuit','moon','benefit'),room('precool_possible',{open:true})).flow,'out-heat');
  // Asked to open, nothing open yet: the sash nudges, no air drawn.
  assert.deepEqual(sceneFor(s('Aérez 10 min','open','benefit'),room('drying_possible',{needs:['dry']})),{k:'win',m:'invite',hour:'day'});
  assert.equal(sceneFor(s('Aérez vers 15 h','clock','benefit'),room('drying_later')).clock,'15 h');
  assert.equal(sceneFor(s('Lancez la VMC','vmc'),room('drying_slow')).k,'vmc');
  assert.equal(sceneFor(s('Rallumez le chauffage','heat'),room('heat_needed')).k,'rad');
  assert.equal(sceneFor(s('Adaptez les volets','window'),room('shutter_protection')).shutter,true);
  // States that are not gestures keep their pictogram.
  assert.equal(sceneFor(s('Mesures en chargement','clock','neutral'),room('incomplete_data')),null);
  assert.equal(sceneFor(s('Mesures absentes','mute','neutral'),room('incomplete_data')),null);
  assert.equal(hourOf(-10),'night');assert.equal(hourOf(25),'day');assert.equal(hourOf(2,new Date('2026-11-02T08:00:00')),'dawn');assert.equal(hourOf(2,new Date('2026-11-02T17:30:00')),'dusk');
});

test('« Bon à savoir » of the full card: one folded box, the dated lines in « À venir », the heating said once (7 November)',async()=>{
  const {fullBody}=await import(pathToFileURL(join(temp,'views/full.mjs')));
  const flat=t=>t==null?'':Array.isArray(t)?t.map(flat).join(''):typeof t!=='object'?String(t):t.strings?t.strings.map((x,i)=>x+(i<t.values.length?flat(t.values[i]):'')).join(''):'';
  const at=new Date(Date.now()+2*3600e3);at.setSeconds(0,0);const hh=`${at.getHours()} h ${String(at.getMinutes()).padStart(2,'0')}`;
  const v={...fresh(),advisor:{title:'Rien à faire',attributes:{regle:'nothing',geste:'nothing',bon_a_savoir:[
    `Chauffage prévu à ${hh} : 20 °C visés`,"Dehors, l'air est plus sec qu'ici : aérer assèche",
    "Ouverte depuis 9 h 05 : 19,2 → 18,8 °C : elle renouvelle peu l'air","Chauffage éteint : le rallumer donnerait 1,2 °C de plus d'ici 22 h"]}}};
  v.assessment={...v.assessment,features:{...v.assessment.features,planned:{at:at.toISOString(),preset:'comfort',temperature:20}}};
  const config=cleanConfig({type:'custom:hestia-comfort-card',format:'full'});
  const st=open=>({why:false,tilesOpen:true,detailsOpen:false,knowOpen:open,uid:'t',toggle(){}});
  const folded=flat(fullBody(v,config,st(false),[])),opened=flat(fullBody(v,config,st(true),[]));
  // Folded: the box says how many lines, none of them.
  assert.match(folded,/Bon à savoir<\/span><span class="nw-sum">3</);
  assert.doesNotMatch(folded,/plus sec qu/);
  // Unfolded: the three lines without a time to come, the past and the horizon among them.
  for(const x of [/plus sec qu/,/Ouverte depuis 9 h 05/,/d'ici 22 h/])assert.match(opened.split('nc-know')[1]??'',x);
  // The heating's change once in « À venir », in the engine's words.
  assert.equal((opened.match(/Chauffage prévu/g)??[]).length,1);
  assert.doesNotMatch(opened,/confort \(20/);
  // Without the engine's line, the card says the schedule's change itself.
  const alone={...v,advisor:{...v.advisor,attributes:{...v.advisor.attributes,bon_a_savoir:[]}}};
  assert.match(flat(fullBody(alone,config,st(false),[])),/confort \(20/);
});

test('the room asleep: a small moon on the banner, its waking hour said, none by day (8 November)',()=>{
  const wake=new Date(2026,10,9,6,45).toISOString();
  const at=(advice3)=>slides({...fresh(),advisor:{title:'Rien à faire',attributes:{geste:'nothing',regle:'nothing',...advice3}}})[0];
  assert.equal(at({nuit:true,reveil:wake}).night,'6 h 45');
  assert.equal(at({nuit:true,reveil:new Date(2026,10,9,7,0).toISOString()}).night,'7 h');
  assert.equal(at({nuit:false,reveil:null}).night,undefined);
  assert.equal(at({nuit:true}).night,undefined);
});
