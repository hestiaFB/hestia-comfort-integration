import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const temp=await mkdtemp(join(tmpdir(),'hestia-setup-'));
await build({entryPoints:['model.ts'],bundle:true,platform:'node',format:'esm',outfile:join(temp,'model.mjs')});
const {confirmable,newRoom,measurement,coverage,livingArea,exteriorSummary,stages,intros,airSource,airChoices,exteriorChoices,changedAdvanced,vocPreset,airReferenceDefaults}=await import(pathToFileURL(join(temp,'model.mjs')));
after(()=>rm(temp,{recursive:true,force:true}));
test('every room source the server may ask to confirm shows the « J’ai vérifié » box (issue #78)',async()=>{
  const {readFile}=await import('node:fs/promises');
  const discovery=await readFile(new URL('../../custom_components/hestia_comfort/discovery.py',import.meta.url),'utf8');
  const indoor=[...discovery.match(/^INDOOR = \(([^)]*)\)/m)[1].matchAll(/"([a-z_0-9]+)"/g)].map(m=>m[1]);
  assert.ok(indoor.includes('heating_indicator'));
  assert.deepEqual(indoor.filter(k=>!confirmable.includes(k)),[]);
});
test('new room copies proposals, describes each opening and freezes no data',()=>{
 const d={suggestions:{indoor_temperature:'sensor.room',windows:['binary_sensor.window']}};
 const room=newRoom({area_id:'salon',name:'Salon'},'',d);
 assert.deepEqual(room.sources,{indoor_temperature:'sensor.room'});
 assert.deepEqual(room.openings['binary_sensor.window'],{exposure:null,kind:'window',sheltered:false});
 room.windows.push('binary_sensor.second');assert.equal(d.suggestions.windows.length,1);
 assert.equal(room.sources.co2,undefined);
 assert.equal(room.settings.humidity_low,40);assert.equal(room.settings.humidity_high,60);
});
test('a free room has a name and no Home Assistant area',()=>{
 const room=newRoom(null,'Étage',{suggestions:{}});
 assert.equal(room.area_id,null);assert.equal(room.name,'Étage');assert.deepEqual(room.windows,[]);
});
test('the living room is found by its usual names but never outside or twice',()=>{
 const areas=[{area_id:'ext',name:'Extérieur',outdoor:true},{area_id:'sejour',name:'Séjour',outdoor:false}];
 assert.equal(livingArea(areas,new Set()).area_id,'sejour');
 assert.equal(livingArea(areas,new Set(['sejour'])),undefined);
});
test('exterior summary names what is configured',()=>{
 assert.equal(exteriorSummary({outdoor_temperature:{},rain:{}}),'Température, pluie');
 assert.equal(exteriorSummary({}),'Rien de configuré');
});
test('binary contact and ATMO daily values are readable and never 1 or off',()=>{
 assert.equal(measurement({available:true,value:'off',device_class:'window'}),'Fermé');
 assert.equal(measurement({available:true,value:'2',atmo_label:'Moyen'}),'Moyen · indice du jour');
 assert.equal(measurement({available:false}),'Ne répond pas en ce moment');
});
test('coverage describes absent windows rather than implying a fault',()=>{
 assert.match(coverage({sources:{indoor_temperature:'sensor.room'},windows:[]}),/fenêtres non mesurées/);
 assert.match(coverage({sources:{indoor_temperature:'sensor.room'},windows:['a','b']}),/2 ouvrants/);
});
test('steps are named by what they set, each with its explanation',()=>{
 assert.equal(stages.length,6);assert.equal(stages.at(-1),'Récapitulatif');
 assert.ok(!stages.includes('Capteurs'));
 stages.forEach((_,i)=>assert.ok(intros[i].length>=1&&intros[i].length<=3));
 assert.ok(intros.exterior.length<=3);
});
test('air quality is chosen by integration, missing ones greyed with a link, « Pas de » last',()=>{
 const none={hestia_weather:{installed:false,places:[]},integrations:{atmofrance:false}};
 let list=airChoices(none,[],'none');
 assert.deepEqual(list.map(c=>c.value),['atmo','hestia','none']);
 assert.equal(list[0].available,false);assert.equal(list[0].missing,'Pas encore installée');assert.match(list[0].url,/atmofrance/);
 assert.equal(list.at(-1).label,'Pas de qualité de l’air');assert.equal(list.at(-1).available,true);
 list=airChoices({...none,integrations:{atmofrance:true}},[],'none');
 assert.equal(list[0].available,false);assert.equal(list[0].url,undefined);
 list=airChoices(none,[{adapter:'atmo_daily'}],'atmo');assert.equal(list[0].available,true);
 assert.deepEqual(airChoices(none,[],'other').map(c=>c.value),['atmo','hestia','other','none']);
 assert.equal(airSource(undefined),'none');assert.equal(airSource({adapter:'atmo_daily'}),'atmo');assert.equal(airSource({adapter:'hestia_index'}),'hestia');assert.equal(airSource({adapter:'binary'}),'other');
});
test('the exterior comes from Hestia Weather only when it has a place',()=>{
 assert.equal(exteriorChoices({}).at(0).missing,'Pas encore installée');
 assert.equal(exteriorChoices({hestia_weather:{installed:true,places:[]}}).at(0).available,false);
 assert.equal(exteriorChoices({hestia_weather:{installed:true,places:[{entry_id:'a',title:'Maison'}]}}).at(0).available,true);
});
test('advanced settings count only what differs from the defaults',()=>{
 assert.equal(changedAdvanced({minimum:20}),0);assert.equal(changedAdvanced({humidity_high:62,frost:2}),1);
 assert.equal(changedAdvanced({co2_action:1000,pm25_action:15,humidity_high:60}),0);
});
test('new room copies optional presence independently and discovers extra measurements',()=>{
 const d={suggestions:{presence:['binary_sensor.motion'],pm25:'sensor.pm',illuminance:'sensor.lux'}};
 const room=newRoom(null,'Bureau',d);assert.deepEqual(room.presence,['binary_sensor.motion']);
 assert.equal(room.sources.pm25,'sensor.pm');assert.equal(room.sources.illuminance,'sensor.lux');
 room.presence.push('binary_sensor.other');assert.equal(d.suggestions.presence.length,1);
 assert.equal(stages[2],'Qualité de l’air');
});
test('new rooms start with explained air references and only identified VOC presets',()=>{
 const voc={entity_id:'sensor.ikea',unit:null,voc_reference:{id:'sensirion_index',value:150,unit:''}};
 const d={suggestions:{voc:'sensor.ikea'},candidates:{voc:[voc]}};
 const room=newRoom(null,'Salon',d);
 for(const [key,value] of Object.entries(airReferenceDefaults))assert.equal(room.settings[key],value);
 assert.deepEqual(room.evolution.voc_threshold,{value:150,unit:''});
 room.evolution.voc_threshold.value=200;assert.equal(voc.voc_reference.value,150);
 assert.equal(vocPreset({...voc,unit:'ppb'}),undefined);
 assert.equal(vocPreset({unit:null}),undefined);
 assert.equal(newRoom(null,'Autre',{suggestions:{voc:'sensor.other'},candidates:{voc:[{entity_id:'sensor.other',unit:'ppb'}]}}).evolution,undefined);
 assert.equal(stages[4],'La pièce et ses réglages');
});
