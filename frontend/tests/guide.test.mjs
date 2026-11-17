// The installation guide (guide.ts): its screens follow the drafts, each topic says whether it is complete.
import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const temp=await mkdtemp(join(tmpdir(),'hestia-comfort-guide-'));
await build({entryPoints:['guide.ts'],bundle:true,platform:'node',format:'esm',outfile:join(temp,'guide.mjs'),logLevel:'silent'});
const {guideScreens,topicDone,guideTopics,nextScreen,ready,left}=await import(pathToFileURL(join(temp,'guide.mjs')));
after(()=>rm(temp,{recursive:true,force:true}));

const house=(change={})=>({kind:'house',foyer:{},lights:{mode:'home',home:null,rooms:{}},outside:false,habits:['journee_vide','linge_pieces'],lightsFound:true,...change});
const candidate=id=>({entity_id:id,name:id});
const room=(change={},candidates={})=>({kind:'room',ownLight:false,lightSet:false,candidates,
 room:{name:'Salon',area_id:'salon',sources:{},windows:[],openings:{},settings:{minimum:20,maximum:24},...change}});
const keys=s=>guideScreens(s).map(x=>x.key);

test('the house: the welcome first, one screen a habit, the summary last',()=>{
 assert.deepEqual(keys(house()),['welcome','outside','house','sleep','habits:journee_vide','habits:linge_pieces','advice','lights','recap']);
 // A manual shutter adds its questions: the screens follow the answers.
 assert.deepEqual(keys(house({habits:['volets_absence','linge_pieces']})).filter(k=>k.startsWith('habits:')),['habits:volets_absence','habits:linge_pieces']);
});
test('the house’s topics are complete once answered, the lights when there is none to choose',()=>{
 const s=house();
 assert.deepEqual(guideTopics(s).filter(x=>!x.done).map(x=>x.topic),['outside','house','sleep','habits','lights']);
 const done=house({outside:true,foyer:{repondu:['vitrage','journee_vide','linge_pieces'],sommeil:{debut:'22:00',fin:'07:00'}},lights:{mode:'rooms',home:null,rooms:{}}});
 assert.equal(left(done),0);
 assert.equal(topicDone('lights',house({lightsFound:false})),true);
 // « Combien de conseils » has a default: never « à voir ».
 assert.equal(topicDone('advice',house()),true);
});
test('a room: one screen an opening, its light only when the lights go room by room',()=>{
 const s=room({windows:['binary_sensor.a','binary_sensor.b']});
 assert.deepEqual(keys(s),['welcome','measures','air','presence','openings','opening:binary_sensor.a','opening:binary_sensor.b','heating','equipment','room','recap']);
 assert.ok(keys({...s,ownLight:true}).includes('notifications'));
});
test('a room cannot go past its temperature, nor be saved without it',()=>{
 const s=room({},{indoor_temperature:[candidate('sensor.t')]}),screen=guideScreens(s).find(x=>x.topic==='measures');
 assert.equal(ready(screen,s),false);
 assert.equal(ready(screen,room({sources:{indoor_temperature:'sensor.t'}})),true);
 // The house has no screen that cannot be left.
 assert.ok(guideScreens(house()).every(x=>ready(x,house())));
});
test('a room’s optional topics are complete when nothing is there to choose',()=>{
 const none=room({sources:{indoor_temperature:'sensor.t'}});
 for(const topic of ['air','presence','openings','opening','heating','equipment'])assert.equal(topicDone(topic,none),true,topic);
 const found=room({sources:{indoor_temperature:'sensor.t'}},{co2:[candidate('sensor.co2')],windows:[candidate('binary_sensor.a')],heating:[candidate('climate.r')]});
 assert.deepEqual(guideTopics(found).filter(x=>!x.done).map(x=>x.topic),['air','openings','heating']);
 // « Pas de contact ici, c’est voulu », or a room not heated, is an answer.
 assert.equal(topicDone('openings',room({windows_unmeasured:true},{windows:[candidate('binary_sensor.a')]})),true);
 assert.equal(topicDone('heating',room({heated:false},{heating:[candidate('climate.r')]})),true);
 // An opening is described once its exposure is said.
 assert.equal(topicDone('opening',room({windows:['binary_sensor.a'],openings:{'binary_sensor.a':{exposure:null}}})),false);
 assert.equal(topicDone('opening',room({windows:['binary_sensor.a'],openings:{'binary_sensor.a':{exposure:'S'}}})),true);
});
test('moving on: the next and previous screens, an opening removed starts again from the welcome',()=>{
 const s=room({windows:['binary_sensor.a']});
 assert.equal(nextScreen(s,'openings',1),'opening:binary_sensor.a');
 assert.equal(nextScreen(s,'opening:binary_sensor.a',-1),'openings');
 assert.equal(nextScreen(s,'recap',1),'recap');
 assert.equal(nextScreen(s,'opening:binary_sensor.gone',1),'measures');
});
