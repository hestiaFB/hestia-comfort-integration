import {LitElement,html,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {customElement,property,state} from 'lit/decorators.js';
import {live} from 'lit/directives/live.js';
import styles from './styles.css';
// The comfort review is shared with its Lovelace card (card/src/review.ts).
import {kpis,todoLists,listSection,listRow,saveBar,tabBar,numberField,segmented,toggle,moreRow,frame,noteBox,hubStyles,modernStyles,helpTip,defaultValue,pageHead,todoFrame,itemsFrame,stepMenu,stepFooter,extensionsFrame,detectedFrame,versionsFrame,extensionCard as nkExtensionCard,aboutPage,removeBlock as nkRemoveBlock,pageStyles,hassChanged,setLanguage,addDictionary,wordsReady,t,fr,currentLocale,currentLanguage,type NkLine,type NkLevel} from './socle/ui';
import {lightEditor,noLights,type Lights,type LightRule,type LightInfo} from './lights';
import {foyerPage,roomFoyer,toleranceName,FOYER_DEFAULTS,duration,type Foyer} from './foyer';
import {quizScreen,unanswered,firstUnanswered,habitsStyles,type HabitsContext,type HouseUses} from './habitudes';
import {overhangSketch} from './sketch';
import {roomLearning3,outside3,firstMissing} from './learning3';
import {words,labels,indoor,outdoor,multiple,exposures,kinds,measurement,newRoom,coverage,exteriorSummary,livingArea,defaultOpening,warningText,warningId,stages,intros,outdoorGroups,airSource,airChoices,exteriorChoices,airReferenceDefaults,vocPreset,thresholdSources,type Choice,type Candidate,type Discovery,type Health,type HealthLine,type Target,type Snapshot,type Hass,type Room,type RoomConfig,type Spec,type Twins,type Twin,type Progress,type Extension,seasonNames,ordinarySize,type Heater,type OpeningMeta,type RoomBuilt,type CustomEquipment} from './model';
// Confort's words beside the hub's (socle 1.13): French in the code, English for any other language.
// Loaded only for a Home Assistant in another language than French (socle 1.23, PLAN-OPTIMISATION-HUB.md point 10).
addDictionary('en',()=>import('./i18n-en').then(m=>m.PANEL_EN));
// The comfort review (« Bilan », shared with the card) only when it is opened.
let reviewLoad:Promise<unknown>|undefined;
const loadReview=()=>reviewLoad??=import('../card/src/review');
/** An extension's state in one word, and its colour: blue when linked, orange when one step is left. */
const extState:Record<Extension['state'],[string,string]>={linked:[fr('liée'),'ok'],found:[fr('à lier'),'act'],missing:[fr('non installée'),''],off:[fr('désactivée'),'']};
const extIcon:Record<string,string>={wled:'light',hestia_weather:'weather',versatile_thermostat:'heating',adaptive_cover_pro:'openings',cover_automatic:'openings',cover_extender:'openings',alarmo:'presence'};
/** HACS opens the repository from its GitHub address. */
const hacsUrl=(url:string)=>{const [owner,repository]=url.replace('https://github.com/','').split('/');return `https://my.home-assistant.io/redirect/hacs_repository/?owner=${owner}&repository=${repository}&category=integration`;};
/** Plural words: French says « 0 point », English « 0 points ». */
/** A saved room as the editor holds it: every window with its details, the area said even when there is none. */
const editable=(saved:RoomConfig):RoomConfig=>{const config=structuredClone(saved);config.area_id??=null;config.openings??={};for(const id of config.windows)config.openings[id]??={...defaultOpening(),sheltered:config.rain_exposed===false};return config;};
const many=(n:number)=>n>1||n===0&&currentLanguage()!=='fr';
const num=(v:number,d=1)=>v.toLocaleString(currentLocale(),{maximumFractionDigits:d,minimumFractionDigits:0});
const days=(d:number)=>{const n=Math.max(1,Math.floor(d));return n>1?t('{n} jours',{n}):t('{n} jour',{n});};
/** Where a room's learning stands: 100 % once it has seen everything it has (engine/twin.py progress). */
function learnState(tw:Twin,g?:Progress|null):{label:string;cls:string;missing:string[]}{
  if(!g)return {label:tw.status==='ready'?'—':t('En cours'),cls:'',missing:[]};
  const p=g.parts,s=g.seen,missing:string[]=[];
  if((p.days??1)<1)missing.push(t('mesures : {days} sur 7',{days:days(s.days)}));
  if((p.precision??1)<1)missing.push(tw.precision?t('prévisions à affiner'):t('prévisions à vérifier'));
  if((p.sun??1)<1)missing.push(t('soleil pas encore vu'));
  // Airings are kept three months, the twin's open half hours one: old airings alone are not enough.
  if((p.windows??1)<1)missing.push(s.airings<5?(many(s.airings)?t('fenêtres : {n} aérations sur 5',{n:s.airings}):t('fenêtres : {n} aération sur 5',{n:s.airings})):t('fenêtres pas assez ouvertes ce mois-ci'));
  if((p.heating??1)<1)missing.push(t('chauffage pas encore vu en marche'));
  if((p.air??1)<1)missing.push(t('air pas encore vu fenêtre ouverte'));
  return {label:g.complete?t('Optimal'):`${g.percent} %`,cls:g.complete?'ok':'',missing};
}
// A sensor's name in a row of the room's page: the page already says which room.
const rowLabels:Record<string,string>=words({indoor_temperature:fr('Température'),indoor_humidity:fr('Humidité'),co2:fr('CO₂'),pm25:fr('Particules fines'),voc:fr('COV'),illuminance:fr('Luminosité'),presence:fr('Présence'),purifier:fr('Purificateur'),ventilation:fr('VMC'),ventilation_boost:fr('Vitesse rapide'),heating_indicator:fr('Indicateur de chauffe')});
const roomSections=[{stage:0,path:'mesures',label:fr('Mesures'),title:fr('Mesures'),icon:'temperature'},{stage:1,path:'ouvertures',label:fr('Ouvertures'),title:fr('Fenêtres et portes'),icon:'openings'},{stage:3,path:'chauffage',label:fr('Chauffage'),title:fr('Chauffage'),icon:'heating'},{stage:2,path:'equipements',label:fr('Équipements'),title:fr('Équipements'),icon:'air'},{stage:4,path:'piece',label:fr('La pièce'),title:fr('La pièce'),icon:'room'},{stage:8,path:'apprentissage',label:fr('Apprentissage'),title:fr('Apprentissage'),icon:'learning'},{stage:7,path:'notifications',label:fr('Notifications'),title:fr('Notifications'),icon:'light'}];
// A new room goes through the tabs as steps, then its summary; a room that exists opens on its tabs, with the save bar.
const roomOrder=[0,1,3,2,4,5];
// The step menu ends on « Récapitulatif », as in every Hestia-FB brick (socle 1.12).
const createSections=[...roomSections.filter(x=>x.stage<7),{stage:5,path:'recapitulatif',label:fr('Récapitulatif'),title:fr('Récapitulatif'),icon:'review'}];
const repository='https://github.com/hestiaFB/hestia-comfort-integration';
// The third-party integrations by theme on the Extensions page, as in Hestia Weather; one not listed here goes under « Autres ».
const themes:[string,string[]][]=[[fr('Chauffage'),['versatile_thermostat','chauffage','scheduler']],[fr('Volets'),['adaptive_cover_pro','cover_automatic','cover_extender']],[fr('Présence'),['alarmo']],[fr('Lumières'),['wled']],[fr('Autres'),[]]];
const help:Record<string,string>=words({season:fr('La saison règle les heures où une aération peut être proposée : jusqu’au coucher en été, en journée au printemps et en automne, aux heures les moins froides en hiver. Le capteur de l’intégration Saison convient.'),indoor_temperature:fr('La mesure de l’air de cette pièce. Seule information obligatoire. La température d’un appareil ou du sol d’une plante peut être différente.'),indoor_humidity:fr('Permet de repérer un air trop humide et de savoir si aérer l’assèche vraiment.'),illuminance:fr('La lumière mesurée en lux aide à interpréter le soleil. Elle ne mesure pas la position d’un volet.'),pm25:fr('Mesure les particules fines. Le seuil d’action est votre réglage de confort.'),voc:fr('Les repères ci-dessous dépendent du capteur et de son unité ; un indice n’est pas une concentration.'),purifier:fr('Observe son fonctionnement sans le commander. Un purificateur filtre les particules ; il ne retire pas le CO₂.'),ventilation:fr('Une VMC ou une ventilation renouvelle l’air et aide à assécher. Seul son état (en marche ou non) est lu, sans la commander ni présumer son débit.'),ventilation_boost:fr('Seulement si votre VMC a deux vitesses : choisissez ici sa position rapide (Turbo). La VMC compte comme en marche si l’une des deux tourne.'),presence:fr('Plusieurs capteurs peuvent suivre la pièce. L’absence adapte les conseils sans couper le suivi ni les alertes.'),co2:fr('Permet de savoir quand renouveler l’air. Ce capteur ne mesure pas tous les polluants.'),windows:fr('Les contacts des fenêtres et portes qui donnent sur l’extérieur. Pas les portes de meubles ou d’appareils.'),heating:fr('Permet de savoir si le chauffage tourne vraiment, pour ne pas conseiller d’ouvrir à ce moment-là. Rien n’est commandé.'),heating_indicator:fr('Pour un thermostat qui ne dit pas s’il chauffe : une vanne, un relais ou un état de marche qui le dit. Il passe avant ce que dit le thermostat ; arrêté, le thermostat reste lu « Arrêté ».'),outdoor_temperature:fr('Permet de savoir si ouvrir rafraîchit ou réchauffe, et s’il gèle.'),outdoor_humidity:fr('Avec les températures, permet de comparer l’eau contenue dans l’air dedans et dehors.'),rain:fr('Une intensité en mm/h dit s’il pleut maintenant. Un cumul de la journée ne le dit pas.'),wind_gust:fr('Au-delà de vos réglages (45 km/h par défaut), le conseil est de ne rien laisser ouvert.'),wind_bearing:fr('D’où vient le vent, en degrés. Avec l’exposition des ouvrants, elle dit lesquels sont au vent, aide à faire traverser l’air et repère la pluie poussée sous un avant-toit.'),solar:fr('Un capteur d’ensoleillement en W/m² permet de calculer le soleil reçu par chaque façade.'),pollution:fr('L’indice ATMO du jour (intégration Atmo France) sert de précaution régionale. Ce n’est pas une mesure à vos fenêtres.')});
let pickerLoad:Promise<string|null>|undefined;
// Home Assistant loads its entity picker lazily; a card editor makes it available to this page.
function loadPicker():Promise<string|null>{
 pickerLoad??=(async()=>{
  const tag=()=>customElements.get('ha-selector')?'ha-selector':customElements.get('ha-entity-picker')?'ha-entity-picker':null;
  if(tag())return tag();
  try{const helpers=await (window as unknown as {loadCardHelpers?:()=>Promise<{createCardElement:(c:object)=>Promise<HTMLElement>}>}).loadCardHelpers?.();
   if(helpers)for(const config of [{type:'tile',entity:'sun.sun'},{type:'entities',entities:['sun.sun']}]){const card=await helpers.createCardElement(config);await (card.constructor as unknown as {getConfigElement?:()=>Promise<unknown>}).getConfigElement?.();if(tag())break;}}
  catch{/* the simple search list remains available */}
  for(let i=0;i<30&&!tag();i++)await new Promise(r=>setTimeout(r,100));
  return tag();
 })();
 return pickerLoad;
}
@customElement('hestia-comfort-setup')
export class ComfortSetup extends LitElement {
 static styles=[unsafeCSS(styles),hubStyles,modernStyles,pageStyles,unsafeCSS(habitsStyles)];
 @property({attribute:false}) hass?:Hass;
 @property({attribute:false}) route?:{prefix?:string;path:string};
 @property({type:Boolean}) narrow=false;
 @state() private snapshot?:Snapshot;
 @state() private discovery?:Discovery;
 @state() private draft?:RoomConfig;
 @state() private exteriorDraft?:Record<string,Spec>;
 @state() private entryId?:string;
 @state() private stage=0;
 @state() private busy=false;
 @state() private lightInfo:Record<string,LightInfo|null>={};
 @state() private error='';
 @state() private saved='';
 @state() private search:Record<string,string>={};
 @state() private acknowledged:string[]=[];
 @state() private confirmed=false;
 @state() private health?:Health;
 @state() private healthLoading=true;
 @state() private twins?:Twins;
 // The integration whose page is open under Extensions.
 @state() private extKey?:string;
 // « Réglages → Lumière »: the light of the whole home, on its own page.
 @state() private lightPage=false;
 /** « Vos habitudes », the questionnaire (HABITUDES-FOYER.md), and the question it shows. */
 @state() private quizPage=false;
 @state() private quizStep=0;
 private originalExterior='';
 // The room's settings as saved, to show the save bar only once something changed (CAHIER-HUB.md § 6).
 private original='';
 @state() private healthError='';
 private healthGeneration=0;
 // The tab opens on the home's technical state; « Modifier » leads to the rooms.
 @state() private page:'health'|'rooms'|'review'|'settings'|'foyer'|'pieces'|'learning'|'about'='health';
 /** A room or the general settings being read: nothing else is shown meanwhile, not even the home for an instant. */
 @state() private opening=false;
 @state() private cardLoad:'idle'|'loading'|'done'|'failed'='idle';
 // The comfort review (review.ts): the home's dashboard, or one room's sheet.
 @state() private reviewRoom?:string;
 @state() private adding=false;
 @state() private weatherAir:{provider:string;index:number|null;label:string|null}|null=null;
 @state() private weatherSeason:string|null=null;
 @state() private overview?:{area_id:string;name:string;suggestions:Record<string,string|string[]>;temperatures:number}[];
 @state() private picked:string[]=[];
 @state() private weatherEntry:string|null=null;
 @state() private proposed:string[]=[];
 @state() private confirmDiscard=false;
 @state() private confirmRemove=false;
 @state() private freeName='';
 @state() private preview?:string;
 @state() private previewEdited=false;
 @state() private pickerTag:string|null=null;
 private generation=0;
 private connection?:unknown;
 private routeHandled:string|undefined;
 private workspaceGeneration=0;
 private workspaceKey='';
 private drafts=new Map<string,{draft?:RoomConfig;exteriorDraft?:Record<string,Spec>;discovery?:Discovery;entryId?:string;stage:number;revision:string;acknowledged:string[];proposed:string[];search:Record<string,string>;weatherEntry:string|null}>();
 private revision='';
 private previewCard?:{id:string;el:HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void}};
 private beforeUnload=(e:BeforeUnloadEvent)=>{if(this.draft||this.exteriorDraft||this.drafts.size){e.preventDefault();e.returnValue='';}};
 // The words of a language arrive after the page (socle 1.23): drawn again with them.
 private words=()=>this.requestUpdate();
 connectedCallback(){super.connectedCallback();window.addEventListener('hestia-words',this.words);if(this.hass&&!this.snapshot){this.connection=this.hass.connection;void this.load();}else if(this.healthLoading&&this.snapshot)void this.loadHealth();window.addEventListener('beforeunload',this.beforeUnload);void loadPicker().then(tag=>this.pickerTag=tag);}
 disconnectedCallback(){super.disconnectedCallback();this.workspaceGeneration++;this.opening=false;if(this.busy)this.routeHandled=undefined;this.generation++;this.healthGeneration++;window.removeEventListener('beforeunload',this.beforeUnload);window.removeEventListener('hestia-words',this.words);}
 // Home Assistant hands a new `hass` at every change of state in the home (8 a second on the lab): this tab redraws only when
 // one of the entities it shows changes, or its language, theme or connection (socle 1.23, PLAN-OPTIMISATION-HUB.md point 7).
 // The card's preview follows every change.
 protected shouldUpdate(changed:PropertyValues){
  if(changed.has('hass')&&this.previewCard)this.previewCard.el.hass=this.hass;
  return !(changed.size===1&&changed.has('hass'))||hassChanged(changed.get('hass') as Hass|undefined,this.hass,this.shown(),this.hassSeen);}
 private hassSeen={};
 /** Every entity this tab may show: the rooms' and the outside's sensors, the alarm, the lights, and the room being set. */
 private shown():string[]{const ids:string[]=[];
  const add=(v:unknown):void=>{if(typeof v==='string'){if(v.includes('.'))ids.push(v);}else if(Array.isArray(v))v.forEach(add);else if(v&&typeof v==='object')Object.values(v).forEach(add);};
  add(this.snapshot?.rooms.map(r=>r.config));add(this.snapshot?.home);add(this.draft);add(this.exteriorDraft);return ids;}
 protected updated(changed:PropertyValues){
  if(this.page==='review')void loadReview();
  // The hub's words (socle 1.13) follow Home Assistant's language.
  // Its words come back from Confort in the new language too: the report is asked again.
  if(setLanguage(this.hass?.language)){this.requestUpdate();if(this.snapshot)void this.loadHealth();}
  this.setAttribute('data-theme',this.hass?.themes?.darkMode===false?'light':'dark');
  if(changed.has('hass')&&this.hass&&(this.hass.connection!==this.connection||!this.snapshot&&!this.busy&&!this.error)){this.connection=this.hass?.connection;void this.load();}
  if(changed.has('hass')&&this.previewCard)this.previewCard.el.hass=this.hass;
  if(changed.has('route')&&this.snapshot)void this.followRoute();
  // Fresh state after every change of the home (a room saved, the exterior changed…).
  if(changed.has('snapshot')&&this.snapshot)void this.loadHealth();
  // An error appears next to what the person was doing, never only at the top of a long page.
  if(changed.has('error')&&this.error)this.renderRoot.querySelector('.error')?.scrollIntoView({block:'center',behavior:'smooth'});
 }
 private async load(){
  if(!this.hass)return;const generation=++this.generation;this.busy=true;this.error='';
  try{const [value]=await Promise.all([this.ws<Snapshot>({type:'hestia_comfort/configuration'}),wordsReady()]);if(generation===this.generation){this.snapshot=value;await this.followRoute();if(!value.rooms.length)await this.loadOverview();}}
  catch(e){if(generation===this.generation)this.error=this.message(e);}
  finally{if(generation===this.generation)this.busy=false;}
 }
 private async loadHealth(){
  const generation=++this.healthGeneration;this.healthLoading=true;this.healthError='';
  // What the twins learned is a bonus: the health page never waits for it nor fails with it.
  void this.ws<Twins>({type:'hestia_comfort/twins'}).then(t=>{if(generation===this.healthGeneration)this.twins=t;},()=>{});
  try{const value=await this.ws<Health>({type:'hestia_comfort/health'});if(generation===this.healthGeneration)this.health=value;}
  catch(e){if(generation===this.healthGeneration)this.healthError=this.message(e);}
  finally{if(generation===this.healthGeneration)this.healthLoading=false;}
 }
 private healthScreen(){
  if(this.health)return html`${this.healthError?html`<p class="notice error" role="alert">${t('Le bilan n’a pas pu être actualisé.')} <button @click=${()=>void this.loadHealth()}>${t('Réessayer')}</button></p>`:nothing}${this.healthPage()}`;
  // The rooms are known before the report: they stay one click away while it loads.
  return html`${this.head()}${this.healthError?html`<p class="notice error" role="alert">${t('Le bilan technique n’a pas pu être chargé.')} ${this.healthError}</p>
   <div class="actions"><button @click=${()=>void this.loadHealth()}>${t('Réessayer')}</button></div>`
   :html`<p class="muted" role="status">${t('Chargement du bilan technique…')}</p>`}
   ${this.roomList()}`;
 }
 private async goTo(t:Target){
  if(t.kind==='exterior')return this.editExterior();
  if(t.kind==='area')return this.start({area_id:t.area_id,name:this.areaName(t.area_id)});
  const room=this.snapshot?.rooms.find(r=>r.entry_id===t.entry_id);if(room)return this.editRoom(room);
 }
 private hline(l:HealthLine){
  return html`<li class=${l.level}><span class="hl-dot"></span><div><strong>${l.text}</strong>${l.why?html`<span class="hl-why">${l.why}</span>`:nothing}</div>
   ${l.target?html`<button class="link hl-go" ?disabled=${this.busy} @click=${()=>void this.goTo(l.target!)}>${l.target.label}</button>`:nothing}</li>`;
 }
 /** The technical home of Confort: is everything working, then each room once (sensors and learning together), then the links. */
 private healthPage(){const h=this.health!,twins=this.twins?.rooms??[];
  // A sensor read from the room sharing the air is counted once, in the room that has it.
  const cells=h.rooms.flatMap(r=>r.cells).filter(c=>c.level!=='shared'),configured=h.sensors?.total??cells.filter(c=>c.level!=='none').length,answering=h.sensors?.answering??cells.filter(c=>c.level==='ok').length;
  const avg=twins.length?Math.round(twins.reduce((a,r)=>a+(r.advisor?.pourcent??r.progress?.percent??0),0)/twins.length):0,followed=twins.reduce((n,r)=>n+(r.week?.followed??0),0);
  return html`${this.head({level:h.level==='ok'?'ok':'todo',text:h.level==='ok'?t('Tout fonctionne'):h.summary,detail:h.rooms_summary})}
  ${kpis([{value:`${answering} / ${configured}`,label:t('capteurs qui répondent'),level:answering===configured?'ok':'todo'},
   {value:`${avg} %`,label:t('du logement appris'),go:()=>this.path('apprentissage')},
   {value:String(followed),label:many(followed)?t('conseils suivis cette semaine'):t('conseil suivi cette semaine')}])}
  ${todoLists(h.todo.map(l=>this.nkLine(l)),[...this.habitsLine(),...h.tips.map(l=>this.nkLine(l))])}
  ${this.roomList()}`;}
 /** « À améliorer »: the questions on the household's habits not answered yet (HABITUDES-FOYER.md § 4); never orange. */
 private habitsLine():NkLine[]{const n=this.snapshot?unanswered(this.habitsContext()):0;
  return n?[{level:'tip',text:t('Vos habitudes'),why:n>1?t('{n} questions, une minute : ce que les capteurs ne voient pas.',{n}):t('Une question : ce que les capteurs ne voient pas.'),
   go:{label:t('Répondre'),onClick:()=>{this.quizStep=firstUnanswered(this.habitsContext());this.path('reglages/habitudes');},disabled:this.busy}}]:[];}
 /** The home as « Vos habitudes » and « Votre maison » need it: the rooms with a manual shutter, what says the absences. */
 private habitsContext():HabitsContext{const s=this.snapshot!,house=this.foyer(),rooms=s.rooms.map(r=>({entry_id:r.entry_id,title:r.title}));
  const shutter=(r:Room,w:string)=>r.config.openings?.[w]?.shutter??house.volet??'none';
  const manual=s.rooms.filter(r=>r.config.windows.some(w=>shutter(r,w)==='manual')).map(r=>r.title);
  // The alarm as the advisor reads it (room/presence.py `_alarm_entity`): the one chosen, else Alarmo found by itself.
  const registry=(this.hass as unknown as {entities?:Record<string,{platform?:string;disabled_by?:string|null}>})?.entities??{};
  const alarm=typeof s.home.alarm==='string'?s.home.alarm||null:Object.entries(registry).find(([id,e])=>id.startsWith('alarm_control_panel.')&&e.platform==='alarmo'&&!e.disabled_by)?.[0]??null;
  const absences=alarm?(this.hass?.states?.[alarm]?.attributes?.friendly_name as string|undefined)??alarm:null;
  return {foyer:house,busy:this.busy,manual,absences,rooms,change:next=>void this.saveFoyer(next),quiz:()=>{this.quizStep=firstUnanswered(this.habitsContext());this.path('reglages/habitudes');}};}
 /** How many windows and rooms take each value of « Votre maison ». */
 private houseUses():HouseUses{const rooms=this.snapshot?.rooms??[],windows=rooms.flatMap(r=>r.config.windows.map(w=>r.config.openings?.[w]??{}));
  const said=(n:number,own:number)=>own?t('Repris par {n} ouvrants · {own} différents',{n,own}):t('Repris par {n} ouvrants',{n});
  // A window « Comme la maison »: no value of its own, or the house's.
  const house=this.foyer(),glazing=windows.filter(m=>!('glazing' in m&&m.glazing&&m.glazing!==(house.vitrage??'double'))).length,
   shutter=windows.filter(m=>!('shutter' in m&&m.shutter&&m.shutter!==(house.volet??'none'))).length;
  const built=rooms.filter(r=>r.config.room?.height==null&&!r.config.room?.wall_material).length;
  const stats=rooms.filter(r=>r.config.thermostat_plage||(r.config.heaters??[]).some(h=>h.entity_id)).map(r=>r.title);
  return {glazing:said(glazing,windows.length-glazing),shutter:said(shutter,windows.length-shutter),
   rooms:t('Repris par {n} pièces',{n:built}),thermostat:stats.length?t('Suivent leur thermostat : {rooms}.',{rooms:stats.join(', ')}):''};}
 /** The top of the Accueil: the same as every brick's, with its way to the general settings. */
 private head(state?:{level:NkLevel;text:string;detail?:string}){return pageHead({title:t('Confort'),state});}
 /** The rooms, one line each: what it measures, how much is learned; a tap opens the room. */
 private roomList(title=t('Pièces')){const twins=new Map((this.twins?.rooms??[]).map(r=>[r.entry_id,r])),todo=new Map<string,number>();
  for(const l of this.health?.todo??[])if(l.target?.kind==='room')todo.set(l.target.entry_id,(todo.get(l.target.entry_id)??0)+1);
  // The overview says how each room is now; the list of rooms, what each one measures.
  const now=(r:Room)=>{const v=(id?:string|string[])=>{const e=Array.isArray(id)?id[0]:id,x=e?this.hass?.states?.[e]?.state:undefined;return x!=null&&x!==''&&Number.isFinite(Number(x))?Number(x):undefined;};
   const temp=v(r.config.sources.indoor_temperature),hum=v(r.config.sources.indoor_humidity);
   return [temp!=null?num(temp,1)+' °C':'',hum!=null?num(hum,0)+' %':''].filter(Boolean).join(' · ')||undefined;};
  const overview=!!title;
  return listSection(title,this.snapshot!.rooms.map(r=>{const others=(this.volumeName(r.entry_id)??'').split(' · ').filter(x=>x&&x!==r.title),same=others.length?t('même air que {names}',{names:others.join(t(' et '))}):'',bad=todo.get(r.entry_id);
   return listRow({name:r.title,label:overview?(bad?html`<strong>${r.title}</strong>`:r.title):html`${r.title}${bad?html` <span class="nk-pill todo">${t('À régler')}</span>`:nothing}`,level:bad?'todo':undefined,
    sub:overview?same||undefined:[coverage(r.config),same].filter(Boolean).join(' · '),value:overview?now(r):undefined,go:()=>void this.openRoom(r.entry_id)});}),
   overview?{help:html`<p>${t('Appris : ce que Confort a vu de chaque pièce. À 100 %, une semaine de mesures, des prévisions justes, cinq aérations et le chauffage en marche.')}</p>`}:{});}
 /** « Pièces »: every room, to open or to add. */
 private roomsPage(){return html`${pageHead({title:t('Pièces'),actions:[{label:this.adding?t('Fermer'):t('Ajouter une pièce'),onClick:()=>{this.adding=!this.adding;}}]})}
  ${this.adding?html`<div class="ac-add">${this.addRoom()}</div>`:nothing}${this.roomList('')}`;}
 /** « Apprentissage »: what Confort has learned of each room, and what it still has to see. */
 private learningPage(){const rooms=this.twins?.rooms??[];
  const avg=rooms.length?Math.round(rooms.reduce((a,r)=>a+(r.advisor?.pourcent??r.progress?.percent??0),0)/rooms.length):0;
  // The questions Confort asks to learn faster (habits, use of a room): answered here in one tap.
  const asked=rooms.flatMap(r=>(r.questions??[]).map(q=>({...q,entry_id:r.entry_id})));
  const answer=async(entry_id:string,key:string,value:string)=>{
   try{await this.ws({type:'hestia_comfort/answer',entry_id,key,answer:value});this.twins=await this.ws<Twins>({type:'hestia_comfort/twins'});}
   catch(e){this.error=this.message(e);}};
  const weeks=rooms.map(r=>r.week).filter(w=>w&&(w.followed||w.ignored)),sum=(k:'followed'|'ignored'|'evaluated'|'held')=>weeks.reduce((n,w)=>n+w![k],0);
  const shade=rooms.map(r=>r.sun_shade).find(s=>s)??null,morning=!!shade?.shaded.some(a=>a<180),afternoon=!!shade?.shaded.some(a=>a>=180);
  const when=morning&&afternoon?t('le matin et l’après-midi'):morning?t('le matin'):afternoon?t('l’après-midi'):'';
  return html`${pageHead({title:t('Apprentissage'),subtitle:rooms.length?t('{n} % du logement appris',{n:avg}):t('Chargement…')})}
  ${asked.length?listSection(t('Pour affiner l’apprentissage'),asked.map(q=>listRow({label:q.text,sub:q.hint,value:segmented(q.text,[['yes',t('Oui')],['no',t('Non')],['unknown',t('Je ne sais pas')]],undefined,v=>void answer(q.entry_id,q.key,v))}))):nothing}
  ${listSection(t('Pièces'),rooms.map(r=>{const st=learnState(r.twin,r.progress),p=r.twin.precision,a=r.advisor;
   // The 3.0 advisor, when it reads the room: the share of its effects proven, and the first thing still to see.
   if(a){const left=firstMissing(a);return listRow({label:r.title,sub:left?t('Encore : {what}',{what:left}):t('tout vu'),
    value:html`<span class="nk-bar" aria-hidden="true"><i style=${'width:'+a.pourcent+'%'}></i></span>${t('{n} %',{n:a.pourcent})}`,go:()=>void this.openRoom(r.entry_id,'apprentissage')});}
   const pc=r.progress?.percent;
   return listRow({label:r.title,sub:st.missing.length?t('Encore : {what}',{what:st.missing.join(', ')}):p?t('tout vu · ±{temp} °C · ±{hum} %',{temp:num(p.temperature,p.temperature<1?2:1),hum:num(p.humidity,0)}):t('tout vu'),
    value:pc!=null?html`<span class="nk-bar" aria-hidden="true"><i style=${'width:'+pc+'%'}></i></span>${t('{n} %',{n:pc})}`:st.label,go:()=>void this.openRoom(r.entry_id,'apprentissage')});}),{help:html`<p>${t('Chaque nuit, Confort relit les derniers jours de chaque pièce : comment elle se refroidit, ce que font ses fenêtres, son chauffage, le soleil. Il vérifie ses prévisions de la veille. À 100 %, tout ce que la pièce possède a été vu et ses prévisions sont justes.')}</p>`})}
  ${weeks.length?listSection(t('Cette semaine'),[listRow({label:t('Conseils suivis'),value:t('{a} sur {b}',{a:sum('followed'),b:sum('followed')+sum('ignored')})}),
   ...(sum('evaluated')?[listRow({label:t('Prévisions tenues'),value:t('{a} sur {b}',{a:sum('held'),b:sum('evaluated')})})]:[])]):nothing}
  ${this.twins?.outside?outside3(this.twins.outside):shade?listSection(t('Le dehors'),[listRow({label:t('Soleil de la station'),sub:when?t('À l’ombre {when} : le soleil y est estimé.',{when}):undefined,value:when?t('estimé'):t('mesuré')})]):nothing}`;}
 private nkLine(l:HealthLine):NkLine{return {level:l.level,text:l.text,why:l.why,go:l.target?{label:l.target.label,onClick:()=>void this.goTo(l.target!),disabled:this.busy}:null};}
 /** Versions and useful links, as on Hestia Weather's home. */
 private versionsBox(){const h=this.health!,version=h.version??'';
  const bricks=(h.extensions??[]).filter(x=>x.official&&x.state==='linked').map(x=>x.name);
  return versionsFrame([[t('Intégration'),version||t('Version non reçue')],[t('Carte'),version||t('Version non reçue')],[t('Moteur de conseil'),h.advisor||t('Version non reçue')],['API','hestia_comfort_api v1'],[t('Socle commun'),h.socle||t('Version non reçue')],[t('Liaisons'),bricks.length?bricks.join(' · '):t('Aucune brique reliée')]],repository,'hestia_comfort');}
 /** A new room: one of the Home Assistant areas not yet followed, or a free room. */
 private addRoom(){const s=this.snapshot!,used=new Set(s.rooms.map(r=>r.config.area_id).filter((a):a is string=>!!a));const living=livingArea(s.areas,used);
  const areas=s.areas.filter(a=>!a.outdoor&&!used.has(a.area_id)&&(s.rooms.length||a!==living));
  return html`${areas.length&&!(this.overview&&!s.rooms.length)?html`<p class="hint">${t('Vos pièces Home Assistant : leurs capteurs vous seront proposés.')}</p><div class="area-buttons">${areas.map(a=>html`<button @click=${()=>this.start(a)}>${a.name}</button>`)}</div>`:nothing}
   <form class="free" @submit=${(e:Event)=>{e.preventDefault();void this.start(null,this.freeName);}}><label>${t('Pièce libre, sans pièce Home Assistant')}<input type="text" maxlength="100" placeholder=${t('Par exemple : Étage')} .value=${this.freeName} @input=${(e:Event)=>this.freeName=(e.target as HTMLInputElement).value}></label><button type="submit">${t('Créer')}</button></form>`;}
 /** « Salon · Cuisine » for a room open onto others, from the rooms' « Même air » settings. */
 private volumeName(entry_id:string):string|null{
  const rooms=this.snapshot?.rooms??[],links=new Map(rooms.map(r=>[r.entry_id,new Set(r.config.open_to??[])]));
  const group=new Set([entry_id]),todo=[entry_id];
  while(todo.length){const id=todo.pop()!;for(const r of rooms)if(!group.has(r.entry_id)&&(links.get(id)?.has(r.entry_id)||links.get(r.entry_id)?.has(id))){group.add(r.entry_id);todo.push(r.entry_id);}}
  if(group.size<2)return null;
  return rooms.filter(r=>group.has(r.entry_id)).sort((a,b)=>Object.keys(b.config.sources??{}).length-Object.keys(a.config.sources??{}).length||a.title.localeCompare(b.title,'fr')).map(r=>r.title).join(' · ');
 }
 /** A command of Confort, answered in the panel's language (engine/i18n.py). */
 private ws<T>(msg:Record<string,unknown>){return this.hass!.callWS<T>({...msg,language:this.hass!.language});}
 private message(e:unknown){return typeof e==='object'&&e&&'message' in e?String(e.message):t('La connexion est indisponible. Réessayez sans quitter votre brouillon.');}
 private path(path:string){if(!this.isConnected)return;this.opening=false;const full='/'+path.replace(/^\//,'');this.routeHandled=full==='/'?'':full;const [key,sub]=path.split('/');if(key==='bilan'){this.page='review';this.reviewRoom=sub;}else if(key==='reglages'){this.page='settings';this.lightPage=sub==='lumiere';this.quizPage=sub==='habitudes';}else if(key==='pieces'&&!sub)this.page='pieces';else if(key==='apprentissage')this.page='learning';else if(key==='a-propos')this.page='about';else if(!key)this.page='health';this.extKey=key==='extensions'?sub:undefined;history.pushState(null,'',(this.route?.prefix??'/hestia/confort')+(path?'/'+path:''));window.dispatchEvent(new CustomEvent('location-changed'));}
 private remember(){if(this.workspaceKey&&(this.draft||this.exteriorDraft))this.drafts.set(this.workspaceKey,{draft:this.draft,exteriorDraft:this.exteriorDraft,discovery:this.discovery,entryId:this.entryId,stage:this.stage,revision:this.revision,acknowledged:this.acknowledged,proposed:this.proposed,search:this.search,weatherEntry:this.weatherEntry});}
 private async followRoute(){
  const path=this.route?.path??'';if(this.routeHandled===path)return;
  // A route that is not the browser's address is a late copy of one already left (Home Assistant can send the former
  // page again just after a save): following it reopened that page behind the preview, stuck on « Chargement… ».
  const here=decodeURI(location.pathname).replace(/\/$/,'');if(this.route?.prefix&&here!==(this.route.prefix+path).replace(/\/$/,''))return;this.routeHandled=path;const generation=++this.workspaceGeneration;this.remember();
  const [id,section]=path.split('/').filter(Boolean);const key=id??'';this.extKey=key==='extensions'?section:undefined;
  // A newer page takes over: the « Chargement… » of the one it replaces must not stay forever.
  this.opening=false;this.workspaceKey=key;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.preview=undefined;this.error='';this.saved='';this.confirmDiscard=false;this.confirmRemove=false;
  // The tab opens on its technical home; « pieces » is the list of rooms to set.
  // « pieces » (the former list of rooms) is now the general settings, like every brick's.
  // The menu's pages (CAHIER-HUB.md § 5.1): the rooms, and what each has learned.
  if(key==='pieces'&&!section){this.page='pieces';if(!this.health)void this.loadHealth();return;}
  if(key==='apprentissage'){this.page='learning';if(!this.twins)void this.loadHealth();return;}
  // « À propos », a page of every brick's menu (socle 1.22): versions and the project's links.
  if(key==='a-propos'){this.page='about';if(!this.health)void this.loadHealth();return;}
  // The general settings only list the rooms; the extensions (and the outside they give) have their own page.
  if(key==='reglages'){this.page='settings';this.lightPage=section==='lumiere';this.quizPage=section==='habitudes';return;}
  this.page=key==='bilan'?'review':'health';this.reviewRoom=key==='bilan'?section:undefined;if(key==='bilan')return;
  const cached=this.drafts.get(key);
  if(cached){Object.assign(this,cached);this.stage=roomSections.find(x=>x.path===section)?.stage??(section==='recapitulatif'?5:cached.stage);return;}
  if(id==='apercu'&&this.snapshot?.rooms.some(r=>r.entry_id===section)){this.preview=section;this.previewEdited=true;return;}
  const room=this.snapshot?.rooms.find(r=>r.entry_id===id);this.opening=id==='extensions'||!!room;
  try{if(id==='extensions'){await this.editExterior(false);return;}
   if(room){await this.editRoom(room,false);if(generation===this.workspaceGeneration)this.stage=roomSections.find(x=>x.path===section)?.stage??(section==='recapitulatif'?5:0);}else if(id){this.error=t('Cette pièce n’est plus disponible. Choisissez une pièce ci-dessous.');}}
  finally{if(generation===this.workspaceGeneration)this.opening=false;}
 }
 private async loadOverview(){
  try{const o=await this.ws<{areas:NonNullable<ComfortSetup['overview']>}>({type:'hestia_comfort/overview'});const living=livingArea(o.areas.map(a=>({...a,outdoor:false})),new Set());this.overview=living?[...o.areas.filter(a=>a.area_id===living.area_id),...o.areas.filter(a=>a.area_id!==living.area_id)]:o.areas;this.picked=o.areas.filter(a=>typeof a.suggestions.indoor_temperature==='string').map(a=>a.area_id);}
  catch{this.overview=[];}
 }
 private detected(s:Record<string,string|string[]>){const parts=[s.indoor_temperature&&t('température'),s.indoor_humidity&&t('humidité'),s.co2&&'CO₂',s.heating&&t('chauffage')].filter(Boolean) as string[];const n=Array.isArray(s.windows)?s.windows.length:0;if(n)parts.push(n>1?t('{n} ouvrants',{n}):t('{n} ouvrant',{n}));return parts.join(', ');}
 // Creates every checked room at once with Hestia-FB's unambiguous proposals; each room keeps its assistant.
 private async createAll(){
  const areas=(this.overview??[]).filter(a=>this.picked.includes(a.area_id));if(!areas.length){this.error=t('Cochez au moins une pièce.');return;}
  this.busy=true;this.error='';let created=0;
  try{for(const a of areas){const discovery=await this.discover(a.area_id);const snapshot:Snapshot=await this.ws<Snapshot>({type:'hestia_comfort/save_config',config:this.withHouse(newRoom({area_id:a.area_id,name:a.name},'',discovery)),revision:this.snapshot!.revision,acknowledged:[]});this.snapshot=snapshot;created++;}
   this.saved=(created>1?t('{n} pièces créées.',{n:created}):t('{n} pièce créée.',{n:created}))+' '+t('Ouvrez chacune pour renseigner l’exposition des ouvrants et compléter si besoin.');this.overview=undefined;}
  catch(e){this.error=(created?(created>1?t('{n} pièces créées, puis : ',{n:created}):t('{n} pièce créée, puis : ',{n:created})):'')+this.message(e);}
  finally{this.busy=false;}
 }
 private menu(){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));}
 private areaName(id:string|null){return id?this.snapshot?.areas.find(a=>a.area_id===id)?.name??id:'';}
 private async discover(area_id?:string|null,entry_id?:string){
  const d=await this.ws<Discovery>({type:'hestia_comfort/discover',...(area_id?{area_id}:{}),...(entry_id?{entry_id}:{})});
  // The cover's override switches are sent once when they are its automation's (configuration.py discover).
  if(!d.candidates.shutter_override&&d.candidates.shutter_auto)d.candidates.shutter_override=d.candidates.shutter_auto;
  return d;
 }
 private begin(){this.confirmRemove=false;this.adding=false;this.busy=true;this.error='';this.saved='';this.preview=undefined;this.search={};this.confirmed=false;}
 private async start(area:{area_id:string;name:string}|null,name=''){
  if(!area&&!name.trim()){this.error=t('Donnez un nom à la pièce libre, par exemple « Étage » ou « Suite parentale ».');return;}
  // From the general settings their draft is kept for the way back, and gives way to the new room's.
  const workspace=this.workspaceGeneration;this.remember();this.begin();
  try{const d=await this.discover(area?.area_id);if(workspace!==this.workspaceGeneration)return;this.exteriorDraft=undefined;this.discovery=d;this.revision=d.revision;this.entryId=undefined;this.draft=this.withHouse(newRoom(area,name.trim(),d));this.proposed=[...Object.values(this.draft.sources),...this.draft.windows];this.stage=0;this.acknowledged=[];this.freeName='';this.workspaceKey='nouvelle';this.path('nouvelle/temperature');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editRoom(room:Room,route=true){
  const cached=this.drafts.get(room.entry_id);if(route&&cached){Object.assign(this,cached);this.workspaceKey=room.entry_id;this.path(room.entry_id+'/'+(roomSections.find(x=>x.stage===this.stage)?.path??'mesures'));return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover(room.config.area_id,room.entry_id);if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.entryId=room.entry_id;
   const config=editable(room.config);
   this.draft=config;this.original=JSON.stringify(config);this.proposed=[];this.stage=0;this.acknowledged=[...(config.acknowledged??[])];this.workspaceKey=room.entry_id;if(route)this.path(room.entry_id+'/mesures');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editExterior(route=true){
  const cached=this.drafts.get('extensions');if(route&&cached){Object.assign(this,cached);this.workspaceKey='extensions';this.path('extensions');return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover();if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.exteriorDraft=structuredClone(this.snapshot!.home.sources);this.weatherEntry=this.snapshot!.home.weather??null;this.acknowledged=[...(this.snapshot!.home.acknowledged??[])];this.proposed=[];this.workspaceKey='extensions';if(this.weatherEntry)await this.useWeather(this.weatherEntry,true);this.originalExterior=JSON.stringify([this.exteriorDraft,this.weatherEntry]);if(route)this.path('extensions');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 // Takes Hestia Weather's station and signals as the whole exterior; only the caution on the air stays the person's.
 private async useWeather(entry_id:string,quiet=false){
  if(!quiet)this.busy=true;this.error='';
  try{const p=await this.ws<{entry_id:string;title:string;sources:Record<string,Spec>;air?:{provider:string;index:number|null;label:string|null}|null;season?:string|null}>({type:'hestia_comfort/weather_proposal',entry_id});
   const caution=this.exteriorDraft?.pollution?.block_from,next={...p.sources};if(next.pollution&&caution)next.pollution={...next.pollution,block_from:caution};
   this.exteriorDraft=next;this.weatherEntry=p.entry_id;this.weatherAir=p.air??null;this.weatherSeason=p.season??null;if(!quiet)this.saved=t('Les mesures de Hestia Weather ({place}) sont reprises : enregistrez pour les garder.',{place:p.title});}
  catch(e){if(quiet)this.weatherEntry=entry_id;this.error=this.message(e);}finally{if(!quiet)this.busy=false;}
 }
 private ownSensors(){if(this.exteriorDraft?.pollution?.adapter==='hestia_air')this.clear('pollution');this.weatherEntry=null;this.weatherAir=null;this.weatherSeason=null;this.saved='';}
 private async changeArea(area_id:string){
  if(!this.draft)return;this.busy=true;this.error='';
  try{const d=await this.discover(area_id||null,this.entryId);this.discovery=d;this.revision=d.revision;this.draft={...this.draft,area_id:area_id||null,floor_id:null};}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async refreshCandidates(){
  this.busy=true;this.error='';
  try{const d=await this.discover(this.draft?.area_id,this.entryId);if(d.revision!==this.revision){this.error=t('La configuration a changé ailleurs. Votre brouillon est conservé ; revenez à Mon logement et rechargez avant d’enregistrer.');return;}this.discovery=d;this.saved=t('La liste des capteurs a été actualisée. Vos choix restent inchangés.');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 // Deleting a room leaves the person's devices untouched; an area room is proposed again on the home page.
 private async removeRoom(){const id=this.entryId,d=this.draft;if(!id||!d)return;this.busy=true;this.error='';
  try{const snapshot=await this.ws<Snapshot>({type:'hestia_comfort/remove_room',entry_id:id,revision:this.revision});this.snapshot=snapshot;this.discard();this.confirmRemove=false;
   this.saved=t('« {name} » est supprimée. Vos capteurs n’ont pas été touchés.',{name:d.name})+(d.area_id?' '+t('La pièce vous est de nouveau proposée ci-dessous.'):'');if(!snapshot.rooms.length)await this.loadOverview();}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private removeBlock(){const d=this.draft!;if(!this.entryId)return nothing;
  return nkRemoveBlock({link:t('Supprimer cette pièce'),title:t('Supprimer « {name} » ?',{name:d.name}),lines:[t('Cette pièce ne sera plus suivie et sa carte n’affichera plus rien. Vos appareils et capteurs Home Assistant ne sont pas touchés.'),
   d.area_id?t('La pièce Home Assistant vous sera de nouveau proposée.'):t('Vous pourrez la recréer comme pièce libre.')],keep:t('Garder la pièce'),confirm:t('Supprimer la pièce'),asking:this.confirmRemove,busy:this.busy,
   onAsk:()=>{this.confirmRemove=true;},onCancel:()=>{this.confirmRemove=false;},onConfirm:()=>void this.removeRoom()});}
 /** Leaving asks only when something is really unsaved: a new room not created yet, or choices that differ from the saved ones (after « Enregistrer », nothing is pending). */
 private cancel(){const pending=this.exteriorDraft?this.exteriorChanges()>0:this.draft?(!this.entryId||this.changes()>0):false;
  if(pending){this.confirmDiscard=true;return;}this.discard();}
 private discard(){const back=this.draft&&!this.exteriorDraft?'pieces':'';this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path(back);this.confirmDiscard=false;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.error='';this.acknowledged=[];this.proposed=[];}
 private selected(key:string):string[]{if(this.exteriorDraft)return this.exteriorDraft[key]?[this.exteriorDraft[key].entity_id]:[];if(!this.draft)return [];return key==='presence'?(this.draft.presence??[]):key==='windows'?this.draft.windows:this.draft.sources[key]?[this.draft.sources[key]]:[];}
 private choose(key:string,c:Candidate){
  const previous=this.selected(key);
  if(this.exteriorDraft){this.exteriorDraft={...this.exteriorDraft,[key]:{entity_id:c.entity_id,adapter:c.adapter,...(c.adapter==='atmo_daily'?{block_from:this.exteriorDraft[key]?.block_from??4}:{})}};}
  else if(this.draft){if(key==='presence'){this.draft={...this.draft,presence:[...new Set([...(this.draft.presence??[]),c.entity_id])]};}else if(key==='windows'){this.draft={...this.draft,windows:[...new Set([...this.draft.windows,c.entity_id])],openings:{...this.draft.openings,[c.entity_id]:this.draft.openings[c.entity_id]??defaultOpening()}};}else {const evolution={...this.draft.evolution};if(key==='voc'&&this.draft.sources.voc!==c.entity_id){const preset=vocPreset(c);if(preset)evolution.voc_threshold=preset;else delete evolution.voc_threshold;}this.draft={...this.draft,evolution,sources:{...this.draft.sources,[key]:c.entity_id}};}}
  if(!multiple.has(key))this.acknowledged=this.acknowledged.filter(id=>!previous.some(p=>id===warningId(key,p)));
  this.proposed=this.proposed.filter(id=>id!==c.entity_id);this.search={...this.search,[key]:''};this.error='';
 }
 private pick(key:string,id:unknown){if(typeof id!=='string'||!id)return;const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c)this.choose(key,c);}
 private clear(key:string,id?:string){
  const removed=id??this.selected(key)[0]??'';
  if(this.exteriorDraft){const next={...this.exteriorDraft};delete next[key];this.exteriorDraft=next;}
  else if(this.draft){if(key==='presence'){this.draft={...this.draft,presence:(this.draft.presence??[]).filter(e=>e!==id)};}else if(key==='windows'){const openings={...this.draft.openings};delete openings[id!];this.draft={...this.draft,windows:this.draft.windows.filter(e=>e!==id),openings};}else{const next={...this.draft.sources};delete next[key];const evolution={...this.draft.evolution};if(key==='voc')delete evolution.voc_threshold;this.draft={...this.draft,evolution,sources:next};}}
  this.acknowledged=this.acknowledged.filter(v=>v!==warningId(key,removed));
 }
 private setOpening(id:string,change:Partial<RoomConfig['openings'][string]>){const d=this.draft!;this.draft={...d,openings:{...d.openings,[id]:{...(d.openings[id]??defaultOpening()),...change}}};}
 // Sensors chosen with a warning that the person has not confirmed yet: one confirmation covers them all.
 private pending(){const keys=this.exteriorDraft?[...outdoor]:[...indoor,'illuminance','co2','pm25','voc','purifier','ventilation','ventilation_boost','presence','heating','windows'];const out:{id:string;name:string}[]=[];
  for(const key of keys)for(const id of this.selected(key)){const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,id)))out.push({id:warningId(key,id),name:c.name});}
  if(this.draft)for(const m of Object.values(this.draft.openings))for(const [field,key] of [['cover_entity','covers'],['auto_entity','shutter_auto'],['override_entity','shutter_override']] as const){const id=m[field],c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,c.entity_id)))out.push({id:warningId(key,c.entity_id),name:c.name});}
  return out;}
 private confirmBlock(){const list=this.pending();if(!list.length)return nothing;
  return html`<div class="notice confirm"><p>${(list.length===1?t('Un capteur est à vérifier (autre pièce, porte d’appareil ou mesure recopiée) : {names}.',{names:list.map(x=>x.name).join(', ')}):t('{n} capteurs sont à vérifier (autre pièce, porte d’appareil ou mesure recopiée) : {names}.',{n:list.length,names:list.map(x=>x.name).join(', ')}))+' '+(this.exteriorDraft?t('Les explications sont plus haut.'):t('Les explications sont aux étapes précédentes.'))}</p><label class="check"><input type="checkbox" .checked=${this.confirmed} @change=${(e:Event)=>{this.confirmed=(e.target as HTMLInputElement).checked;if(this.confirmed)this.error='';}}>${t('J’ai vérifié, je confirme mes choix.')}</label></div>`;}
 private replace(key:string,old:string,id:unknown){
  if(id===''||id===undefined||id===null){this.clear(key,old);return;}  // the picker's cross removes the sensor
  if(typeof id!=='string'||id===old)return;
  const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(!c)return;
  if(key==='windows'&&this.draft){
   // The replacement keeps the exposure, type and shelter already described for this opening.
   const d=this.draft,openings={...d.openings,[id]:d.openings[old]??defaultOpening()};delete openings[old];
   this.draft={...d,windows:d.windows.map(w=>w===old?id:w),openings};
   this.acknowledged=this.acknowledged.filter(a=>a!==warningId(key,old));this.proposed=this.proposed.filter(p=>p!==old);
  }else if(key==='presence'&&this.draft){this.draft={...this.draft,presence:[...new Set((this.draft.presence??[]).map(e=>e===old?id:e))]};this.acknowledged=this.acknowledged.filter(a=>a!==warningId(key,old));}else this.choose(key,c);
 }
 private selector(key:string,ids:string[],value:string,label:string,changed:(id:unknown)=>void){
  if(this.pickerTag==='ha-selector')return html`<ha-selector .hass=${this.hass} .selector=${{entity:{include_entities:ids}}} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-selector>`;
  return html`<ha-entity-picker .hass=${this.hass} .includeEntities=${ids} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-entity-picker>`;
 }
 /** Chauffage : d'abord si la pièce est chauffée ; éteint, le thermostat et ses réglages s'effacent (gardés pour un retour). */
 private heatingStage(){const d=this.draft!,heated=d.heated!==false,head=listRow({label:t('Pièce chauffée'),value:toggle(t('Pièce chauffée'),heated,on=>this.draft={...this.draft!,heated:on},this.busy)});
  if(!heated)return html`${listSection(t('Chauffage'),[head])}${noteBox(t('Pièce non chauffée'),t('Hestia-FB ne conseillera jamais de la réchauffer.'))}`;
  const list=this.heaters(),all=this.discovery?.candidates.heating??[],free=all.filter(c=>!list.some(h=>h.entity_id===c.entity_id)).map(c=>c.entity_id),found=(id:string)=>all.find(c=>c.entity_id===id),vt=this.uses('versatile_thermostat');
  const add=(id:string)=>({entity_id:id,scope:this.looksLikeStove(id)?'house':'room'} as Heater);
  const rows=[head,...list.flatMap((h,i)=>{const c=found(h.entity_id);return [
   listRow({label:t('Chauffage'),sub:c?(c.thermostat&&vt?t('Versatile Thermostat'):measurement(c)):t('Capteur introuvable ou incompatible · choisissez-en un autre'),
    value:this.selector('heating',[h.entity_id,...free],h.entity_id,'',v=>this.setHeaters(typeof v==='string'&&v?list.map((x,j)=>j===i?add(v):x):list.filter((_,j)=>j!==i)))}),
   listRow({label:html`<span class="nk-indent">${t('Il chauffe')}</span>`,value:segmented(t('Il chauffe'),[['room',t('Cette pièce')],['house',t('Toute la maison')]],h.scope,scope=>this.setHeaters(list.map((x,j)=>j===i?{...x,scope}:x)),this.busy)})];}),
   free.length?listRow({label:t('Ajouter un chauffage'),value:this.selector('heating',free,'','',v=>{if(typeof v==='string'&&v)this.setHeaters([...list,add(v)]);})}):nothing,
   ...(d.sources.heating||d.sources.heating_indicator?this.sensorRows('heating_indicator'):[])];
  const p=this.plage(),now=(id:string)=>{const th=found(id)?.thermostat;const v=th&&vt?((th.preset??'').includes('frost')?th.comfort:th.target??th.comfort):undefined;return v==null?undefined:t('{t} en ce moment',{t:String(v).replace('.',',')+' °C'});};
  const radio=(id:string|null,label:string,sub?:string)=>html`<label class="nk-row nk-row-go"><span class="nk-row-lab">${label}${sub?html`<small>${sub}</small>`:nothing}</span><input type="radio" name="plage" .checked=${p===id} ?disabled=${this.busy} @change=${()=>this.setHeaters(list,id)}></label>`;
  const set=(i:number,change:Partial<Heater>)=>this.setHeaters(list.map((x,j)=>{if(j!==i)return x;const n={...x,...change};if(!n.kind)delete n.kind;if(n.power==null||Number.isNaN(n.power))delete n.power;return n;}));
  const known=list.filter(h=>h.kind||h.power).length;
  return html`${listSection(t('Chauffages'),rows,{help:html`<p>${t('Un poêle, un insert ou une cheminée chauffent toute la maison : chaque pièce apprend la part qui lui arrive.')}</p>`})}
  ${list.some(h=>found(h.entity_id)?.thermostat)&&!vt?noteBox(t('Versatile Thermostat désactivé'),t('Coupé dans Extensions : ce chauffage est lu comme un thermostat ordinaire.')):nothing}
  ${list.length?listSection(t('La plage suit'),[...list.map(h=>radio(h.entity_id,found(h.entity_id)?.name??h.entity_id,now(h.entity_id))),radio(null,t('Aucun'),t('La plage reste celle des Mesures.'))],
   {help:html`<p>${t('La consigne du thermostat devient le minimum de la pièce. En éco, la pièce est attendue plus fraîche ; en hors-gel, c’est la consigne confort qui compte.')}</p>`}):nothing}
  ${list.length?listSection('',[moreRow(t('Pour aller plus loin'),t('{n} sur {total}',{n:known,total:list.length}),list.map((h,i)=>{const c=found(h.entity_id),fromVt=!!c?.thermostat&&vt;
   return listRow({label:c?.name??h.entity_id,sub:fromVt?t('Puissance lue dans Versatile Thermostat.'):undefined,value:html`<select aria-label=${t('Type')} @change=${(e:Event)=>set(i,{kind:(e.target as HTMLSelectElement).value||undefined})}><option value="" ?selected=${!h.kind}>${t('Type…')}</option>${[['radiator',t('Convecteur ou soufflant')],['radiant',t('Panneau rayonnant')],['inertia',t('Radiateur à inertie ou à eau')],['floor',t('Plancher chauffant')],['stove',t('Poêle à bois ou insert')],['pellet',t('Poêle à granulés')],['ac',t('Climatisation réversible')]].map(([v,l])=>html`<option value=${v} ?selected=${h.kind===v}>${l}</option>`)}</select>
    ${fromVt?nothing:html`<input type="number" aria-label=${t('Puissance (W)')} min="100" max="20000" step="50" placeholder="W" .value=${h.power==null?'':String(h.power)} @input=${(e:Event)=>{const raw=(e.target as HTMLInputElement).value;set(i,{power:raw===''?undefined:Number(raw)});}}><span class="nk-unit">W</span>`}`});}))]):nothing}`;}
 /** The room's heatings: the one saved by Confort 2.1 when none is listed yet, a stove proposed for the whole house. */
 private heaters():Heater[]{const d=this.draft!;if(d.heaters?.length)return d.heaters;const id=d.sources.heating;return id?[{entity_id:id,scope:this.looksLikeStove(id)?'house':'room'}]:[];}
 private looksLikeStove(id:string){const c=this.discovery?.candidates.heating?.find(x=>x.entity_id===id);return /po[eê]le|stove|insert|chemin[ée]e|granul/i.test(`${c?.name??''} ${id}`);}
 /** The heating the range follows: null for « Aucun ». */
 private plage():string|null{const d=this.draft!;if(d.thermostat_reference===false)return null;const ids=this.heaters().map(h=>h.entity_id);return d.thermostat_plage&&ids.includes(d.thermostat_plage)?d.thermostat_plage:ids[0]??null;}
 /** Confort 2.1 reads one heating: the one the range follows, or the first. */
 private setHeaters(list:Heater[],follow?:string|null){const d=this.draft!,ids=list.map(h=>h.entity_id);
  let plage=follow===undefined?this.plage():follow;if(plage&&!ids.includes(plage))plage=ids[0]??null;
  const sources={...d.sources},main=plage??ids[0];if(main)sources.heating=main;else delete sources.heating;
  this.draft={...d,heaters:list,sources,thermostat_plage:plage,thermostat_reference:plage!==null||!list.length};}
 /** Who moves the cover. Adaptive Cover Pro, CoverAutomatic and Cover Extender are recognised by themselves and each signal they give is shown;
     any other automation is told by hand. Full width, below the cover's own fields. */
 private sensorRows(key:string){const all=this.discovery?.candidates[key]??[],sel=this.selected(key),free=all.filter(c=>!sel.includes(c.entity_id));
  const order=(xs:Candidate[])=>[...xs.filter(c=>c.local),...xs.filter(c=>!c.local)].map(c=>c.entity_id);
  const rows=sel.map(id=>{const c=all.find(x=>x.entity_id===id);
   return listRow({label:rowLabels[key]??t(labels[key]),sub:c?html`${measurement(c)}${c.warnings.length?html` · <span class="warning" title=${warningText[c.warnings[0]]??t('Source à vérifier.')}>${t('source à vérifier')}</span>`:nothing}`:t('Capteur introuvable ou incompatible · choisissez-en un autre'),
    value:this.selector(key,[id,...order(free)],id,'',v=>this.replace(key,id,v))});});
  if(multiple.has(key)||!sel.length){const mine=free.find(c=>c.local);
   rows.push(listRow({label:sel.length?t('Ajouter'):html`${rowLabels[key]??t(labels[key])}${key==='indoor_temperature'?html` <span class="nk-pill">${t('Obligatoire')}</span>`:nothing}`,name:rowLabels[key]??t(labels[key]),
    value:html`${mine&&!sel.length?html`<button class="link" ?disabled=${this.busy} @click=${()=>this.choose(key,mine)}>${t('Utiliser {name}',{name:mine.name})}</button>`:nothing}${this.selector(key,order(free),'','',v=>this.pick(key,v))}`}));}
  return rows;}
 /** The openings: each its contact (changed in place), then what it is; « Ajouter un ouvrant » from a contact. */
 private windowsTab(){const d=this.draft!,all=this.discovery?.candidates.windows??[],free=all.filter(c=>!d.windows.includes(c.entity_id)).map(c=>c.entity_id);
  return html`${d.windows.map(id=>{const c=all.find(x=>x.entity_id===id);
   return listSection(c?.name??id,[listRow({label:t('Contact'),sub:c?measurement(c):undefined,value:this.selector('windows',[id,...free],id,'',v=>this.replace('windows',id,v))}),...this.openingRows(id),
    html`<button type="button" class="nk-row nk-row-go danger-row" ?disabled=${this.busy} @click=${()=>this.clear('windows',id)}><span class="nk-row-lab">${t('Retirer cet ouvrant')}</span></button>`],
    {help:html`<p>${t('La taille règle l’air qui entre et le soleil reçu. L’exposition dit quand le soleil arrive sur la fenêtre.')}</p>`});})}
  ${listSection(d.windows.length?'':t('Fenêtres et portes'),[listRow({label:t('Ajouter un ouvrant'),sub:t('Le contact de la porte ou de la fenêtre.'),value:this.selector('windows',free,'','',v=>this.pick('windows',v))}),
   d.windows.length?nothing:listRow({label:t('Pas de contact ici, c’est voulu'),sub:t('Hestia-FB ne le proposera plus.'),value:toggle(t('Pas de contact ici, c’est voulu'),d.windows_unmeasured===true,on=>this.draft={...this.draft!,windows_unmeasured:on})})])}`;}
 /** One opening in rows (CAHIER-HUB.md § 5.3): where it faces, what it is, its size, its shutter; the rest in « Pour aller plus loin ». */
 private openingRows(id:string){const m=this.draft!.openings[id]??defaultOpening(),found=m.shutter==='connected'&&m.cover_entity?this.discovery?.drivers?.[m.cover_entity]:undefined,driver=found&&this.uses(found.driver??'adaptive_cover_pro')?found:undefined;
  const select=(label:string,value:string|undefined,options:[string,string][],set:(v:string)=>void)=>html`<select aria-label=${label} @change=${(e:Event)=>set((e.target as HTMLSelectElement).value)}>${options.map(([v,l])=>html`<option value=${v} ?selected=${(value??'')===v}>${l}</option>`)}</select>`;
  const metres=(key:'width'|'height'|'overhang_depth'|'overhang_gap',label:string,placeholder:string)=>html`<input type="number" aria-label=${label} min="0" max="20" step="0.05" placeholder=${placeholder} .value=${m[key]===undefined?'':String(m[key])} @input=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;this.setOpening(id,{[key]:v===''?undefined:Number(v)});}}>`;
  const pick=(key:'cover_entity'|'auto_entity'|'override_entity',kind:string)=>{const all=this.discovery?.candidates[kind]??[],value=m[key]??'';
   return this.selector(kind,[...new Set([...(value?[value]:[]),...all.map(c=>c.entity_id)])],value,'',next=>{if(typeof next==='string'){this.acknowledged=this.acknowledged.filter(a=>a!==warningId(kind,value));this.confirmed=false;this.setOpening(id,{...(m.shutter?{}:{shutter:'connected' as const}),[key]:next||undefined});}});};
  const [w,h]=ordinarySize(m.kind),size=(n:number)=>String(n).replace('.',','),sig=driver?.signals;
  const signal=(label:string,x:{name:string;on:boolean}|null|undefined,on:string,off:string)=>x?html`<li><b>${label}</b> · ${x.on?on:off}</li>`:nothing;
  const known=(m.overhang_depth!=null?1:0)+(m.azimuth!=null?1:0);
  // « Votre maison » (HABITUDES-FOYER.md § 3 bis): the window takes the house's glazing and shutter until it sets its own.
  const house=this.foyer(),houseShutter=house.volet??'none',houseGlazing=house.vitrage??'double',shutter=m.shutter??houseShutter;
  const like=(own:boolean,reset:()=>void)=>own?html`${t('Propre à cet ouvrant')} · <button type="button" class="nk-reset-s" @click=${reset}>${t('Comme la maison')}</button>`:t('Comme la maison');
  return [listRow({label:t('Exposition'),value:select(t('Exposition'),m.exposure??'',[['',t('Je ne sais pas')],...exposures.map(([v,l])=>[v,t(l)] as [string,string])],v=>this.setOpening(id,{exposure:v||null}))}),
   listRow({label:t('Type'),value:select(t('Type'),m.kind,kinds.map(([v,l])=>[v,t(l)] as [string,string]),v=>this.setOpening(id,{kind:v}))}),
   listRow({label:t('Taille'),sub:m.width!=null||m.height!=null?undefined:driver?.width!=null?t('Reprise de {name}.',{name:driver.name}):t('Vide : environ {w} × {h} m.',{w:size(w),h:size(h)}),
    value:html`${metres('width',t('Largeur (m)'),size(driver?.width??w))}<span class="nk-unit">×</span>${metres('height',t('Hauteur (m)'),size(driver?.height??h))}<span class="nk-unit">m</span>`}),
   listRow({label:t('Abritée par une avancée ou un balcon'),value:toggle(t('Abritée par une avancée ou un balcon'),m.sheltered,on=>this.setOpening(id,{sheltered:on}))}),
   listRow({label:t('Vitrage'),sub:like(!!m.glazing&&m.glazing!==houseGlazing,()=>this.setOpening(id,{glazing:undefined})),value:segmented(t('Vitrage'),[['simple',t('Simple')],['double',t('Double')],['triple',t('Triple')]],m.glazing??houseGlazing,v=>this.setOpening(id,{glazing:v===houseGlazing?undefined:v}))}),
   listRow({label:t('Volet'),sub:like(m.shutter!==undefined&&m.shutter!==houseShutter,()=>this.setOpening(id,{shutter:undefined,cover_entity:undefined,auto_entity:undefined,override_entity:undefined,shutter_habit:undefined})),
    value:segmented(t('Volet'),[['none',t('Aucun')],['manual',t('À la main')],['connected',t('Motorisé')]],shutter,v=>this.setOpening(id,{shutter:v===houseShutter&&v!=='connected'?undefined:v,cover_entity:undefined,auto_entity:undefined,override_entity:undefined,shutter_habit:undefined}))}),
   shutter==='connected'?listRow({label:driver?html`${t('Volet motorisé')} ${helpTip(t('Piloté par {name}',{name:driver.name}),html`<p>${t('Ces signaux sont lus tout seuls, rien à renseigner :')}</p><ul>${signal(t('Intégration'),sig?.enabled,t('activée'),t('désactivée : elle ne pilote rien'))}${signal(t('Pilotage automatique'),sig?.auto,t('activé'),t('coupé'))}${signal(t('Suivi du soleil'),sig?.tracking,t('activé'),t('coupé'))}${signal(t('Mode climat'),sig?.climate,t('activé'),t('coupé : il ne ferme pas contre la chaleur'))}${signal(t('Détection de la reprise à la main'),sig?.detection,t('activée'),t('coupée : un volet bougé à la main ne sera pas reconnu'))}</ul>`)}`:t('Volet motorisé'),
    sub:driver?t('Piloté par {name} : aucun geste demandé.',{name:driver.name}):t('Sa position est lue dans Home Assistant.'),value:pick('cover_entity','covers')}):nothing,
   moreRow(t('Pour aller plus loin'),t('{n} sur {total}',{n:known,total:2}),[
    listRow({label:html`${t('Avancée au-dessus')} ${helpTip(t('Avancée au-dessus'),html`${overhangSketch()}<p>${t('Un débord de toit, un balcon de l’étage, une casquette en béton. A : du mur jusqu’au bord, à l’horizontale. B : du dessous de l’avancée jusqu’au haut de la fenêtre. À 10 cm près suffit.')}</p>`)}`,sub:t('A : du mur au bord. B : du dessous au haut de la fenêtre.'),
     value:html`<span class="nk-unit">A</span>${metres('overhang_depth',t('Profondeur (m)'),'0,60')}<span class="nk-unit">B</span>${metres('overhang_gap',t('Écart (m)'),'0,30')}<span class="nk-unit">m</span>`}),
    listRow({label:t('Angle précis'),sub:t('Nord 0, est 90, sud 180, ouest 270.'),value:html`<input type="number" aria-label=${t('Angle précis')} min="0" max="359" step="1" .value=${m.azimuth!=null?String(m.azimuth):''} @input=${(e:Event)=>{const raw=(e.target as HTMLInputElement).value;this.setOpening(id,{azimuth:raw===''?null:Number(raw)});}}><span class="nk-unit">°</span>`}),
    ...(m.shutter==='connected'&&!driver?[listRow({label:t('Interrupteur du pilotage automatique'),sub:t('Si une automatisation ouvre et ferme ce volet.'),value:pick('auto_entity','shutter_auto')}),listRow({label:t('Capteur « repris à la main »'),value:pick('override_entity','shutter_override')})]:[])])];}
 private go(stage:number){this.stage=stage;if(this.workspaceKey)this.path(this.workspaceKey+'/'+(roomSections.find(x=>x.stage===stage)?.path??'recapitulatif'));this.error='';this.saved='';this.updateComplete.then(()=>{this.renderRoot.querySelector<HTMLElement>('h1')?.focus();});}
 /** What must be right before going on or saving; '' when it is. */
 private problem(all=false){const d=this.draft!,s=d.settings;
  if((all||this.stage===0)&&!d.sources.indoor_temperature)return t('Choisissez la température de la pièce pour continuer. C’est la seule mesure obligatoire.');
  const tol=s.heating_tolerance;if(tol!==undefined&&!(Number.isFinite(tol)&&tol>=0&&tol<=5))return t('La tolérance du chauffage va de 0 à 5 °C.');
  if(all||this.stage===4){if(!d.name.trim())return t('Donnez un nom à la pièce.');if((d.custom_equipment??[]).some(c=>!c.name.trim()))return t('Donnez un nom à chaque équipement ajouté.');if(!Number.isFinite(s.minimum)||!Number.isFinite(s.maximum)||s.minimum>=s.maximum)return t('La température minimum doit être inférieure au maximum.');if(Number.isFinite(s.summer_maximum)&&s.summer_maximum<s.maximum)return t('Le maximum d’été ne peut pas être inférieur à celui d’hiver.');}
  return '';}
 private next(){const problem=this.problem();if(problem){this.error=problem;return;}this.go(roomOrder[roomOrder.indexOf(this.stage)+1]??5);}
 /** « Enregistrer » from any step of a room that exists: a sensor still to confirm leads to the summary, where it is. */
 private saveRoom(){const problem=this.problem(true);if(problem){this.error=problem;return;}
  if(this.pending().length&&!this.confirmed){this.go(5);this.error=t('Vérifiez les capteurs signalés, puis cochez « J’ai vérifié, je confirme mes choix » pour enregistrer.');return;}
  void this.save();}
 private async save(){
  const config=this.exteriorDraft?{sources:this.exteriorDraft,weather:this.weatherEntry}:this.draft;if(!config)return;
  const workspace=this.workspaceGeneration,entryId=this.entryId,isHome=!!this.exteriorDraft,revision=this.revision;this.busy=true;this.error='';
  try{const validated=await this.ws<{warnings:{key:string;entity_id:string}[]}>({type:'hestia_comfort/validate_config',config,home:isHome});if(workspace!==this.workspaceGeneration)return;const missing=validated.warnings.map(w=>warningId(w.key,w.entity_id)).filter(id=>!this.acknowledged.includes(id));
   if(missing.length&&!this.confirmed){this.error=t('Cochez « J’ai vérifié, je confirme mes choix » juste au-dessus pour enregistrer.');return;}
   this.acknowledged=[...new Set([...this.acknowledged,...missing])];
   const before=new Set(this.snapshot?.rooms.map(r=>r.entry_id));const wasRoom=!isHome;const edited=entryId;
   this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/save_config',config,home:isHome,revision,...(entryId?{entry_id:entryId}:{}),acknowledged:this.acknowledged});
   if(workspace!==this.workspaceGeneration)return;
   // A room saved stays on screen, on the same tab and at the same place: no other page in between, nothing reloaded.
   const kept=wasRoom&&edited?this.snapshot.rooms.find(r=>r.entry_id===edited):undefined;
   if(kept){const config=editable(kept.config);this.drafts.delete(this.workspaceKey);this.draft=config;this.original=JSON.stringify(config);this.acknowledged=[...(config.acknowledged??[])];this.revision=this.snapshot.revision;this.saved=t('Enregistré');return;}
   this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path('');this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;
   if(wasRoom&&edited){const tab=roomSections.find(x=>x.stage===this.stage)?.path??'mesures';await this.openRoom(edited,tab);this.saved=t('Enregistré');return;}
   if(wasRoom){this.preview=this.snapshot.rooms.find(r=>!before.has(r.entry_id))?.entry_id;this.previewEdited=false;if(this.preview)this.path('apercu/'+this.preview);}
   if(isHome){await this.editExterior();this.saved=t('Enregistré');}}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private floorName(){const d=this.draft!;const id=d.area_id?this.snapshot?.areas.find(a=>a.area_id===d.area_id)?.floor_id:d.floor_id;return this.snapshot?.floors?.find(f=>f.floor_id===id)?.name??t('Non renseigné');}
 /** « La pièce » (CAHIER-HUB.md § 5.3): its name and place, the rooms it shares its air with, what differs from the house, how it is built. */
 private preferences(){const d=this.draft!,used=new Set(this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId).map(r=>r.config.area_id));
  const others=this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId),open=d.open_to??[],theirs=(r:{config:RoomConfig})=>!!this.entryId&&(r.config.open_to??[]).includes(this.entryId);
  return html`${listSection(t('La pièce'),[listRow({label:t('Nom'),value:html`<input type="text" aria-label=${t('Nom')} maxlength="100" .value=${d.name} @input=${(e:Event)=>this.draft={...this.draft!,name:(e.target as HTMLInputElement).value}}>`}),
   listRow({label:t('Pièce Home Assistant'),sub:d.area_id?undefined:t('Rattachée, ses capteurs sont proposés en premier.'),value:html`<select aria-label=${t('Pièce Home Assistant')} @change=${(e:Event)=>this.changeArea((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!d.area_id}>${t('Aucune (pièce libre)')}</option>${this.snapshot!.areas.filter(a=>!a.outdoor&&(!used.has(a.area_id)||a.area_id===d.area_id)).map(a=>html`<option value=${a.area_id} ?selected=${a.area_id===d.area_id}>${a.name}</option>`)}</select>`}),
   d.area_id?listRow({label:t('Étage'),sub:t('Repris de Home Assistant.'),value:this.floorName()})
    :listRow({label:t('Étage'),value:html`<select aria-label=${t('Étage')} @change=${(e:Event)=>this.draft={...this.draft!,floor_id:(e.target as HTMLSelectElement).value||null}}><option value="" ?selected=${!this.snapshot?.floors?.some(f=>f.floor_id===d.floor_id)}>${t('Non renseigné')}</option>${(this.snapshot?.floors??[]).map(f=>html`<option value=${f.floor_id} ?selected=${d.floor_id===f.floor_id}>${f.name}</option>`)}</select>`})])}
  ${others.length?listSection(t('Même air'),others.map(r=>listRow({label:r.title,sub:theirs(r)?t('Déclaré depuis cette pièce'):undefined,value:toggle(r.title,open.includes(r.entry_id)||theirs(r),on=>this.draft={...this.draft!,open_to:on?[...open,r.entry_id]:open.filter(x=>x!==r.entry_id)},theirs(r))})),
   {help:html`<p>${t('Les pièces sans mur ni porte entre elles, comme un salon ouvert sur sa cuisine : leurs fenêtres comptent pour les deux, et le même air ne reçoit jamais deux gestes contraires.')}</p>`}):nothing}
  ${listSection('',[roomFoyer({house:this.foyer(),room:d.foyer??{},busy:this.busy,manual:d.windows.some(w=>(d.openings[w]?.shutter??this.foyer().volet)==='manual'),change:next=>{this.draft={...this.draft!,foyer:next};}}),this.roomMore()])}
  ${this.entryId?listSection('',[html`<button type="button" class="nk-row nk-row-go" ?disabled=${this.busy} @click=${()=>this.refreshCandidates()}><span class="nk-row-lab">${t('Rechercher à nouveau les capteurs')}</span></button>`]):nothing}
  ${this.removeBlock()}`;}
 /** « Pour aller plus loin »: how the room is built, every answer optional (REGLAGES-3.md § 4.4). */
 private roomMore(){const d=this.draft!,r=d.room??{};
  const set=(change:Partial<RoomBuilt>)=>{const n:Record<string,unknown>={...this.draft!.room,...change};for(const k of Object.keys(n))if(n[k]===undefined||n[k]===''||Number.isNaN(n[k])||(Array.isArray(n[k])&&!(n[k] as unknown[]).length))delete n[k];this.draft={...this.draft!,room:n as RoomBuilt};};
  const count=(['uses','surface','height','outside','wall_material','insulation','partitions'] as const).filter(k=>r[k]!==undefined).length;
  const select=(key:'uses'|'wall_material'|'insulation'|'partitions',label:string,options:[string,string][])=>listRow({label,value:html`<select aria-label=${label} @change=${(e:Event)=>set({[key]:(e.target as HTMLSelectElement).value||undefined})}><option value="" ?selected=${!r[key]}>${t('Je ne sais pas')}</option>${options.map(([v,l])=>html`<option value=${v} ?selected=${r[key]===v}>${l}</option>`)}</select>`});
  const number=(key:'surface'|'height',label:string,unit:string,step:number,hint:string,sub?:string)=>listRow({label,sub,value:html`<input type="number" aria-label=${label} min="0" step=${step} placeholder=${hint} .value=${r[key]==null?'':String(r[key])} @input=${(e:Event)=>{const raw=(e.target as HTMLInputElement).value;set({[key]:raw===''?undefined:Number(raw)});}}><span class="nk-unit">${unit}</span>`});
  const sides=r.outside??[],sideName:Record<string,string>={N:t('Nord'),E:t('Est'),S:t('Sud'),O:t('Ouest')};
  return moreRow(t('Pour aller plus loin'),t('{n} sur {total}',{n:count,total:7}),[
   select('uses',t('Usage'),[['bedroom',t('Chambre')],['living',t('Séjour')],['kitchen',t('Cuisine')],['bathroom',t('Salle de bain')],['office',t('Bureau')],['other',t('Autre')]]),
   number('surface',t('Surface'),'m²',0.5,'16',r.surface==null?t('Vide : une pièce ordinaire de 16 m².'):undefined),number('height',t('Hauteur sous plafond'),'m',0.05,'2,50'),
   listRow({label:t('Murs qui donnent dehors'),value:html`<span class="nk-chips">${['N','E','S','O'].map(side=>html`<button type="button" class="nk-chip" aria-pressed=${String(sides.includes(side))} @click=${()=>set({outside:sides.includes(side)?sides.filter(x=>x!==side):[...sides,side]})}>${sideName[side]}</button>`)}</span>`}),
   select('wall_material',t('Murs du dehors'),[['heavy',t('Pierre, béton, brique')],['wood',t('Bois')]]),
   select('insulation',t('Isolés'),[['inside',t('Par l’intérieur')],['outside',t('Par l’extérieur')],['none',t('Pas isolés')]]),
   select('partitions',t('Murs entre les pièces'),[['light',t('Cloisons légères')],['heavy',t('Murs lourds')]])]);}
 /** What the room holds that warms, wets or loads its air (REGLAGES-3.md § 4.4): each may say when it runs. */
 /** « Équipements » (CAHIER-HUB.md § 5.3): the VMC, the purifier, and what warms, wets or loads the air; each may say when it runs. */
 private equipmentTab(){const d=this.draft!,mine=d.equipment??[],links=d.equipment_links??{},custom=d.custom_equipment??[],ids=this.runEntities();
  const flow=(k:'purifier'|'ventilation_boost',label:string,sub?:string)=>listRow({label,sub,value:numberField({label,value:d.flows?.[k],unit:'m³/h',step:5,min:10,max:1000,set:v=>{const flows={...this.draft!.flows};if(v===undefined)delete flows[k];else flows[k]=v;this.draft={...this.draft!,flows};}})});
  const run=(value:string,changed:(id:string)=>void)=>this.selector('equipment',[...new Set([...(value?[value]:[]),...ids])],value,'',v=>changed(typeof v==='string'?v:''));
  const sub=(label:string)=>html`<span class="nk-indent">${label}</span>`;
  const setOn=(key:string,on:boolean)=>{const l={...links};if(!on)delete l[key];this.draft={...this.draft!,equipment:on?[...mine,key]:mine.filter(x=>x!==key),equipment_links:l};};
  const item=(key:string,label:string,effect:string)=>[listRow({label,sub:effect,value:toggle(label,mine.includes(key),on=>setOn(key,on))}),
   mine.includes(key)?listRow({label:sub(t('Pour savoir quand il marche')),sub:links[key]?undefined:t('Facultatif : une prise, un interrupteur, une puissance.'),value:run(links[key]??'',v=>{const l={...this.draft!.equipment_links??{}};if(v)l[key]=v;else delete l[key];this.draft={...this.draft!,equipment_links:l};})}):nothing];
  const setCustom=(i:number,change:Partial<CustomEquipment>|null)=>{const list=[...(this.draft!.custom_equipment??[])];if(change)list[i]={...list[i],...change};else list.splice(i,1);this.draft={...this.draft!,custom_equipment:list};};
  const effects:[string,string][]=[['heat',t('Chauffe')],['cool',t('Rafraîchit')],['humid',t('Mouille l’air')],['dry',t('Assèche l’air')],['voc',t('COV, odeurs')],['particles',t('Particules, fumée')],['purify',t('Purifie')]];
  return html`${listSection(t('VMC'),[...this.sensorRows('ventilation'),...(d.sources.ventilation?[...this.sensorRows('ventilation_boost'),flow('ventilation_boost',t('Débit en vitesse rapide'))]:[])],
   {help:html`<p>${t('Le débit, sur la notice, donne une durée juste dès le premier jour. Vide, Hestia-FB suppose une VMC ordinaire et se corrige au fil des utilisations.')}</p>`})}
  ${listSection(t('Purificateur'),[...this.sensorRows('purifier'),...(d.sources.purifier?[flow('purifier',t('Débit d’air propre'),t('« CADR » sur la notice ou la boîte.'))]:[])])}
  ${listSection(t('Ce qui change l’air de la pièce'),[...item('shower',t('Douche ou baignoire'),t('Humidité')),...item('hob',t('Plaque de cuisson'),t('Humidité, COV, particules')),...item('oven',t('Four'),t('COV, chaleur')),
   ...item('hood',t('Hotte'),t('Enlève l’humidité et le COV')),...item('drying',t('Linge qui sèche'),t('Humidité')),...item('fan',t('Ventilateur'),t('Rafraîchit la peau, pas l’air')),
   ...custom.flatMap((c,i)=>[listRow({label:html`<input type="text" maxlength="40" aria-label=${t('Nom de l’équipement')} placeholder=${t('Nom de l’équipement')} .value=${c.name} @input=${(e:Event)=>setCustom(i,{name:(e.target as HTMLInputElement).value})}>`,value:html`<button type="button" class="nk-reset-s" @click=${()=>setCustom(i,null)}>${t('Retirer')}</button>`}),
    listRow({label:sub(t('Ce qu’il change')),value:html`<span class="nk-chips">${effects.map(([v,l])=>html`<button type="button" class="nk-chip" aria-pressed=${String(c.effects.includes(v))} @click=${()=>setCustom(i,{effects:c.effects.includes(v)?c.effects.filter(x=>x!==v):[...c.effects,v]})}>${l}</button>`)}</span>`}),
    listRow({label:sub(t('Pour savoir quand il marche')),value:run(c.entity_id??'',v=>setCustom(i,{entity_id:v||null}))})]),
   custom.length<10?html`<button type="button" class="nk-row nk-row-go" ?disabled=${this.busy} @click=${()=>this.draft={...this.draft!,custom_equipment:[...custom,{name:'',effects:[],entity_id:null}]}}><span class="nk-row-lab">${t('Ajouter un autre équipement')}</span><span class="nk-chev" aria-hidden="true">+</span></button>`:nothing],
   {help:html`<p>${t('Relié à une entité, Hestia-FB sait quand il marche : « C’est le four, le COV retombera quand il s’arrête ».')}</p>`})}`;}
 /** What can say an equipment runs: a switch, a plug, a fan, a contact, or a power sensor. */
 private runEntities(){const s=this.hass?.states??{};return Object.keys(s).filter(id=>/^(switch|binary_sensor|fan|input_boolean)\./.test(id)||id.startsWith('sensor.')&&(s[id].attributes?.device_class==='power'||s[id].attributes?.unit_of_measurement==='W')).sort();}
 private summary(){const d=this.draft!,home=this.snapshot!.home;const name=(key:string,id?:string)=>id?this.discovery?.candidates[key]?.find(v=>v.entity_id===id)?.name??id:'';
  const metas=d.windows.map(id=>d.openings[id]??defaultOpening());const counts=new Map<string,number>();for(const m of metas)if(m.exposure)counts.set(m.exposure,(counts.get(m.exposure)??0)+1);
  const expo=[...counts].map(([e,n])=>n+' '+t(exposures.find(x=>x[0]===e)![1]).toLowerCase()).join(', ');const unknown=metas.filter(m=>!m.exposure).length,sheltered=metas.filter(m=>m.sheltered).length;
  const measures=[name('indoor_temperature',d.sources.indoor_temperature),name('indoor_humidity',d.sources.indoor_humidity)].filter(Boolean).join(' · ');
  return html`${frame(t('Récapitulatif'),html`<dl class="summary compact"><dt>${t(stages[0])}</dt><dd>${measures||'—'}</dd>
   <dt>${t(stages[1])}</dt><dd>${d.windows.length?html`${d.windows.length>1?t('{n} ouvrants',{n:d.windows.length}):t('{n} ouvrant',{n:d.windows.length})}${sheltered?' · '+(sheltered>1?t('{n} abrités',{n:sheltered}):t('{n} abrité',{n:sheltered})):''}${expo?' · '+expo:''}${unknown?' · '+t('{n} sans exposition',{n:unknown}):''}<details><summary>${t('Voir la liste')}</summary>${d.windows.map(id=>html`<div>${name('windows',id)}</div>`)}</details>`:t('Aucun')}</dd>
   <dt>${t(stages[2])}</dt><dd>${['co2','pm25','voc','purifier','ventilation','ventilation_boost'].map(k=>name(k,d.sources[k])).filter(Boolean).join(' · ')||t('Air non mesuré')}${d.presence?.length?' · '+(d.presence.length>1?t('{n} capteurs de présence',{n:d.presence.length}):t('{n} capteur de présence',{n:d.presence.length})):''}</dd><dt>${t(stages[3])}</dt><dd>${name('heating',d.sources.heating)||t('Non suivi')}</dd>
   <dt>${t(stages[4])}</dt><dd>${d.name} · ${d.area_id?t('rattachée à « {name} »',{name:this.areaName(d.area_id)}):t('pièce libre')} · ${t('étage : {floor}',{floor:this.floorName()})} · ${d.settings.minimum}–${d.settings.maximum} °C${(d.settings.summer_maximum??26)>d.settings.maximum?' '+t('(été {n} °C)',{n:d.settings.summer_maximum??26}):''}${d.heated===false?' · '+t('non chauffée'):''}${d.equipment?.includes('shower')?' · '+t('douche'):''}</dd>
   <dt>${t('Extérieur')}</dt><dd>${home.configured?exteriorSummary(home.sources):t('À configurer depuis Mon logement')}</dd></dl>`)}
   ${this.confirmBlock()}`;}
 private errorBlock(){return this.error?html`<p class="notice error" role="alert">${this.error}</p>`:nothing;}
 /** What changed in the room since it was opened: one per setting changed, for the save bar. */
 private changes(){if(!this.draft||!this.original)return 0;const before=JSON.parse(this.original) as Record<string,unknown>,now=this.draft as unknown as Record<string,unknown>;
  return [...new Set([...Object.keys(before),...Object.keys(now)])].filter(k=>JSON.stringify(before[k])!==JSON.stringify(now[k])).length;}
 /** Under the room's name: what it measures now, whether something is to set, how much is learned. */
 private roomChips(){const d=this.draft!,all=this.discovery?.candidates??{},todo=(this.health?.todo??[]).some(l=>l.target?.kind==='room'&&l.target.entry_id===this.entryId);
  const now=['indoor_temperature','indoor_humidity','co2','voc'].flatMap(k=>{const c=all[k]?.find(x=>x.entity_id===this.selected(k)[0]);return c?.available?[measurement(c)]:[];});
  const room=this.twins?.rooms.find(x=>x.entry_id===this.entryId),learned=room?.advisor?.pourcent??room?.progress?.percent;
  return html`<div class="room-chips">${now.map(m=>html`<span class="room-m">${m}</span>`)}${this.health?html`<span class=${'nk-pill '+(todo?'todo':'ok')}>${todo?t('À régler'):t('Rien à faire')}</span>`:nothing}${learned!=null?html`<span class="nk-pill">${t('{n} % appris',{n:learned})}</span>`:nothing}</div>`;}
 /** « Mesures » (CAHIER-HUB.md § 5.3): the sensors, the comfort range, the marks of what is measured, who the room is for. */
 private measuresTab(){const d=this.draft!,st=d.settings,has=(k:string)=>!!this.selected(k).length;
  const setting=(key:string,dflt:number)=>(v:number|undefined)=>this.draft={...this.draft!,settings:{...this.draft!.settings,[key]:v??dflt}};
  const num=(label:string,key:string,unit:string,dflt:number,step=1)=>listRow({label,value:numberField({label,value:st[key],unit,dflt,step,set:setting(key,dflt)})});
  // The range's defaults are the house's (« Votre maison »): « Rétablir » brings the room back to them.
  const plage={minimum:20,maximum:24,summer_maximum:26,...(this.foyer().plage??{})};
  // The minimum read from the thermostat the range follows: shown, never a field that says the opposite (CAHIER-HUB.md § 5.3).
  const c=this.discovery?.candidates.heating?.find(x=>x.entity_id===d.sources.heating),th=this.uses('versatile_thermostat')&&d.thermostat_reference!==false?c?.thermostat:undefined;
  const set=th?((th.preset??'').includes('frost')?th.comfort:th.target??th.comfort):undefined;
  const minimum=th?listRow({label:t('Minimum'),sub:t('La consigne de {name}, en ce moment.',{name:c!.name}),value:html`${set==null?'—':String(set).replace('.',',')+' °C'} <button class="link" ?disabled=${this.busy} @click=${()=>this.go(3)}>${t('Changer')}</button>`}):num(t('Minimum'),'minimum','°C',plage.minimum,0.5);
  const voc=this.discovery?.candidates.voc?.find(x=>x.entity_id===d.sources.voc),unit=voc?(voc.unit??''):(d.evolution?.voc_threshold?.unit??''),preset=vocPreset(voc),vt=d.evolution?.voc_threshold;
  const setVoc=(v:number|undefined)=>{const evolution={...this.draft!.evolution},value=v??preset?.value;if(value===undefined)delete evolution.voc_threshold;else evolution.voc_threshold={value,unit};this.draft={...this.draft!,evolution};};
  const marks=[has('indoor_humidity')?num(t('Humidité au-dessus de'),'humidity_high','%',60):null,has('co2')?num(t('Aérer à partir de'),'co2_action','ppm',1000,50):null,
   has('pm25')?num(t('Particules fines au-dessus de'),'pm25_action','µg/m³',15):null,
   has('voc')?listRow({label:t('COV au-dessus de'),sub:preset||vt?.unit===unit?undefined:t('Vide : la mesure est suivie sans verdict.'),value:numberField({label:t('COV au-dessus de'),value:vt?.unit===unit?vt.value:undefined,unit:unit||t('indice'),dflt:preset?.value,set:setVoc})}):null].filter(x=>x);
  const persons=Object.keys(this.hass?.states??{}).filter(e=>e.startsWith('person.')).sort(),mine=new Set(d.persons??[]);
  const person=(e:string)=>{const on=mine.has(e);return html`<button type="button" class="nk-chip" aria-pressed=${String(on)} @click=${()=>{const next=new Set(mine);if(on)next.delete(e);else next.add(e);this.draft={...this.draft!,persons:[...next]};}}>${String(this.hass?.states?.[e]?.attributes?.friendly_name??e)}</button>`;};
  const presence=[persons.length?listRow({label:t('Personnes de la pièce'),sub:t('Sans personne cochée, toute la maison compte.'),value:html`<span class="nk-chips">${persons.map(person)}</span>`}):null,
   has('presence')?listRow({label:t('Pièce vide après'),value:numberField({label:t('Pièce vide après'),value:d.evolution?.presence_delay_minutes,unit:'min',dflt:5,min:0,max:120,set:v=>this.draft={...this.draft!,evolution:{...this.draft!.evolution,presence_delay_minutes:v??5}}})}):null].filter(x=>x);
  return html`${listSection(t('Capteurs'),['indoor_temperature','indoor_humidity','co2','pm25','voc','illuminance','presence'].flatMap(key=>this.sensorRows(key)))}
  ${listSection(t('Plage de confort'),[minimum,num(t('Maximum en hiver'),'maximum','°C',plage.maximum,0.5),num(t('Maximum en été'),'summer_maximum','°C',plage.summer_maximum,0.5)],{help:html`<p>${t('Les températures où vous vous sentez bien. Le maximum passe de l’hiver à l’été avec la saison. C’est un choix personnel, pas une limite de santé.')}</p>`})}
  ${marks.length?listSection(t('Repères'),marks,{help:html`<p>${t('Humidité : l’ADEME conseille 40 à 60 %. Jusqu’à 3 points au-dessus, l’air est dit légèrement humide ; jusqu’à 10, humide ; au-delà, très humide. Ces paliers graduent l’affichage, ce ne sont pas des seuils sanitaires.')}</p>
   <p>${t('CO₂ : repères du HCSP ; à 1 500 ppm, aérer vite (fixe). Particules fines : 15 µg/m³, la moyenne sur 24 h recommandée par l’OMS. COV : l’indice 100 est le niveau habituel appris par le capteur ; 150 est l’exemple d’action de Sensirion.')}</p>
   <p><a href=${thresholdSources.humidity} target="_blank" rel="noopener noreferrer">ADEME</a> · <a href=${thresholdSources.co2} target="_blank" rel="noopener noreferrer">HCSP</a> · <a href=${thresholdSources.pm25} target="_blank" rel="noopener noreferrer">OMS</a> · <a href=${thresholdSources.voc} target="_blank" rel="noopener noreferrer">Sensirion</a></p>`}):nothing}
  ${presence.length?listSection(t('Présence'),presence):nothing}`;}
 private wizard(){const d=this.draft!,creating=!this.entryId,section=roomSections.find(x=>x.stage===this.stage),at=roomOrder.indexOf(this.stage);
  const tabs=creating?createSections:roomSections.filter(x=>x.stage!==7||this.lights().mode==='rooms');
  const content=this.stage===0?this.measuresTab()
   :this.stage===1?this.windowsTab()
   :this.stage===2?this.equipmentTab()
   :this.stage===3?this.heatingStage():this.stage===4?this.preferences()
   :this.stage===8?this.roomLearning():this.stage===7?this.notifications():this.summary();
  return html`${pageHead({back:{label:t('Pièces'),onClick:()=>this.cancel()},title:d.name?d.name:t('Nouvelle pièce')})}
  ${creating?html`<p class="room-step">${t('Nouvelle pièce · étape {n} sur {total}',{n:at+1,total:roomOrder.length})}</p>`:this.roomChips()}
  ${tabBar(t('Réglages de la pièce'),tabs.map(x=>({label:t(x.label),current:x.stage===this.stage,onClick:()=>this.go(x.stage)})),this.busy)}
  ${content}${this.errorBlock()}
  ${creating?stepFooter({previous:at>0?{label:t('Étape précédente'),onClick:()=>this.go(roomOrder[at-1]),disabled:this.busy}:undefined,
   next:this.stage!==5?{label:t('Continuer'),onClick:()=>this.next(),disabled:this.busy}:undefined,save:this.stage===5?{label:t('Créer la pièce'),onClick:()=>void this.save(),disabled:this.busy}:undefined})
   :saveBar({count:this.changes(),busy:this.busy,cancel:()=>{this.draft=JSON.parse(this.original);this.error='';},save:()=>this.saveRoom(),done:this.saved===t('Enregistré')?this.saved:undefined})}`;}
 /** « Apprentissage » of one room: how far its learning is, what it still has to see, how closely it is forecast. */
 private roomLearning(){const r=this.twins?.rooms.find(x=>x.entry_id===this.entryId);
  if(!r)return html`<p class="muted" role="status">${t('Chargement…')}</p>`;
  if(r.advisor)return roomLearning3(r.advisor);
  const st=learnState(r.twin,r.progress),p=r.twin.precision,g=r.progress,w=r.week;
  const part=(key:'days'|'precision'|'sun'|'windows'|'heating'|'air',label:string)=>g&&g.parts[key]!==undefined?listRow({label,value:g.parts[key]!>=1?t('vu'):`${Math.round(g.parts[key]!*100)} %`}):nothing;
  return html`${listSection(t('Où en est la pièce'),[listRow({label:t('Appris'),value:g?`${g.percent} %`:st.label}),part('days',t('Mesures')),part('precision',t('Prévisions')),part('sun',t('Soleil')),part('windows',t('Fenêtres')),part('heating',t('Chauffage')),part('air',t('Air'))])}
  ${listSection(t('Ce qui manque encore'),st.missing.length?st.missing.map(m=>listRow({label:m})):[listRow({label:t('Rien : tout ce que la pièce possède a été vu.')})])}
  ${listSection(t('Ses prévisions'),[listRow({label:t('Justesse'),value:p?t('±{temp} °C · ±{hum} %',{temp:num(p.temperature,p.temperature<1?2:1),hum:num(p.humidity,0)}):t('pas encore vérifiées')}),
   ...(w?[listRow({label:t('Cette semaine'),value:t('{a} conseils suivis, {b} laissés',{a:w.followed,b:w.ignored})})]:[])])}`;}
 /** The general settings: the rooms, Hestia-FB's own bricks, then the other integrations Confort reads or could read. */
 /** What changed in the outside since the page opened, for the save bar. */
 private exteriorChanges(){if(!this.exteriorDraft||!this.originalExterior)return 0;const [sources,weather]=JSON.parse(this.originalExterior) as [Record<string,unknown>,string|null],now=this.exteriorDraft as unknown as Record<string,unknown>;
  return [...new Set([...Object.keys(sources),...Object.keys(now)])].filter(k=>JSON.stringify(sources[k])!==JSON.stringify(now[k])).length+((weather??null)!==(this.weatherEntry??null)?1:0);}
 /** « Extensions » (CAHIER-HUB.md § 5.4): where the outside comes from, in one choice, then the integrations Confort reads. */
 private exterior(){const h=this.health,ext=h?.extensions??[];if(this.extKey)return this.extensionPage(ext.find(x=>x.key===this.extKey));
  const row=(x:Extension)=>{const off=x.state==='off',missing=x.state==='missing';
   return listRow({label:x.beta?html`${x.name} <span class="nk-pill">${t('bêta')}</span>`:x.name,name:x.name,control:true,sub:missing?t('Pas installée'):off?t('Pas utilisée'):x.rooms.length?x.rooms.slice(0,3).join(', ')+(x.rooms.length>3?'…':''):x.state==='found'?t('Trouvée, pas encore liée'):x.use,
    value:missing?undefined:toggle(t('Utiliser {name}',{name:x.name}),!off,on=>void this.useExtension(x.key,on),this.busy),go:()=>this.path('extensions/'+x.key)});};
  return html`${pageHead({title:t('Extensions'),subtitle:t('D’où vient le dehors, et les intégrations que Confort lit.')})}
  ${this.outdoorSection()}
  ${h?themes.map(([label,keys])=>{const items=ext.filter(x=>!x.official&&(keys.length?keys.includes(x.key):!themes.some(([,k])=>k.includes(x.key))));return items.length?listSection(t(label),items.map(row)):nothing;}):html`<p class="muted" role="status">${t('Recherche des extensions…')}</p>`}
  ${this.confirmBlock()}${this.errorBlock()}
  ${saveBar({count:this.exteriorChanges(),busy:this.busy,cancel:()=>{const [sources,weather]=JSON.parse(this.originalExterior);this.exteriorDraft=sources;this.weatherEntry=weather;if(weather)void this.useWeather(weather,true);this.error='';},save:()=>void this.save(),done:this.saved===t('Enregistré')?this.saved:undefined})}`;}
 /** « Le dehors »: Hestia Weather gives it all; otherwise one sensor per measure, and the air of the day. Set once, for every room. */
 private outdoorSection(){const s=this.snapshot!,nw=s.hestia_weather,weather=!!this.weatherEntry,can=!!nw?.installed&&!!nw.places.length,spec=this.exteriorDraft!.pollution;
  const all=(key:string)=>this.discovery?.candidates[key]??[];
  const rows:unknown[]=[listRow({label:t('D’où vient le dehors'),sub:weather?t('Hestia Weather donne tout le dehors : mesures, prévisions, alertes et air.'):t('Une mesure par capteur, sans prévisions ni alertes.'),
   value:can?segmented(t('D’où vient le dehors'),[['weather','Hestia Weather'],['own',t('Vos capteurs')]],weather?'weather':'own',v=>v==='weather'?void this.useWeather(nw!.places[0].entry_id):this.ownSensors(),this.busy)
    :html`<a href=${hacsUrl('https://github.com/hestiaFB/hestia-weather-integration')} target="_blank" rel="noreferrer">${t('Installer Hestia Weather')}</a>`})];
  if(weather&&(nw?.places.length??0)>1)rows.push(listRow({label:t('Lieu Hestia Weather'),value:html`<select aria-label=${t('Lieu Hestia Weather')} @change=${(e:Event)=>void this.useWeather((e.target as HTMLSelectElement).value)}>${nw!.places.map(p=>html`<option value=${p.entry_id} ?selected=${p.entry_id===this.weatherEntry}>${p.title}</option>`)}</select>`}));
  if(!weather){
   for(const key of outdoorGroups.flatMap(([,k])=>k)){const id=this.selected(key)[0]??'',c=all(key).find(x=>x.entity_id===id),ids=all(key).map(x=>x.entity_id);if(!ids.length&&!id)continue;
    rows.push(listRow({label:t(labels[key]),sub:c?measurement(c):undefined,value:this.selector(key,ids,id,'',v=>{if(v===''||v==null){if(id)this.clear(key,id);}else this.pick(key,v);})}));}
   const air=this.discovery?.candidates.pollution??[],current=airSource(spec),choices=airChoices(s,air,current).filter(c=>c.available);
   rows.push(listRow({label:t('Air du dehors'),sub:t('Une précaution régionale du jour, pas une mesure à vos fenêtres.'),value:segmented(t('Air du dehors'),choices.map(c=>[c.value,c.label] as [string,string]),current,v=>{if(v===current)return;if(v==='none'){this.clear('pollution');return;}const first=air.find(c=>c.adapter===(v==='atmo'?'atmo_daily':'hestia_index'));if(first)this.choose('pollution',first);},this.busy)}));
   if(spec&&current!=='other'){const zones=air.filter(c=>c.adapter===spec.adapter);if(zones.length>1)rows.push(listRow({label:current==='atmo'?t('Zone Atmo France'):t('Lieu Hestia Weather'),value:html`<select aria-label=${t('Zone')} @change=${(e:Event)=>this.pick('pollution',(e.target as HTMLSelectElement).value)}>${zones.map(z=>html`<option value=${z.entity_id} ?selected=${z.entity_id===spec.entity_id}>${z.name}</option>`)}</select>`}));}}
  if(spec&&['atmo_daily','hestia_index','hestia_air'].includes(spec.adapter??''))rows.push(listRow({label:t('Ne pas aérer dès l’indice'),sub:t('Votre prudence, pas une consigne sanitaire.'),
   value:html`<select aria-label=${t('Ne pas aérer dès l’indice')} @change=${(e:Event)=>{this.exteriorDraft={...this.exteriorDraft!,pollution:{...spec,block_from:Number((e.target as HTMLSelectElement).value)}};}}>${[t('Moyen'),t('Dégradé'),t('Mauvais'),t('Très mauvais'),t('Extrêmement mauvais')].map((label,i)=>html`<option value=${i+2} ?selected=${(spec.block_from??4)===i+2}>${label}</option>`)}</select>`}));
  return listSection(t('Le dehors'),rows,{help:html`<p>${t('Une seule source pour toutes les pièces.')}</p>`});}
 /** One integration: used or not in Confort, where it serves, what Confort does without it. */
 private extensionPage(x?:Extension){if(!x)return html`<p class="muted" role="status">${t('Chargement…')}</p>`;const off=x.state==='off',missing=x.state==='missing';
  const step=x.key==='versatile_thermostat'?'chauffage':['adaptive_cover_pro','cover_automatic','cover_extender'].includes(x.key)?'ouvertures':'',first=this.snapshot?.rooms[0];
  return html`${pageHead({back:{label:t('Extensions'),onClick:()=>this.path('extensions')},title:x.name,subtitle:x.use})}
  ${listSection('',[...(x.beta?[listRow({label:html`<span class="nk-pill">${t('bêta')}</span>`,sub:t('Lecture nouvelle : vos retours sur GitHub la font progresser.')})]:[]),missing?listRow({label:t('Pas installée dans Home Assistant'),value:x.key==='wled'?html`<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=wled" target="_blank" rel="noreferrer">${t('Ajouter dans Home Assistant')}</a>`:html`<a href=${hacsUrl(x.url)} target="_blank" rel="noreferrer">${t('Installer avec HACS')}</a>`})
   :listRow({label:t('Utiliser dans Confort'),sub:off?t('Confort l’ignore, sans rien désinstaller.'):undefined,value:toggle(t('Utiliser dans Confort'),!off,on=>void this.useExtension(x.key,on),this.busy)})])}
  ${!missing&&!off?listSection(t('Où elle sert'),x.rooms.length?x.rooms.map(n=>listRow({label:n})):[listRow({label:t('Nulle part pour l’instant.'),value:step&&first?html`<button type="button" class="nk-reset-s" @click=${()=>void this.openRoom(first.entry_id,step)}>${t('Lier dans une pièce')}</button>`:x.key==='wled'?html`<button type="button" class="nk-reset-s" @click=${()=>this.goSettings()}>${t('Régler')}</button>`:undefined})]):nothing}
  ${x.without?listSection(t('Sans elle'),[listRow({label:x.without})]):nothing}`;}
 /** Réglages généraux: the rooms to change or add, and how to show their cards; nothing here waits for a save. */
 private settingsPage(){if(this.lightPage)return this.lightScreen();
  if(this.quizPage)return quizScreen({...this.habitsContext(),step:this.quizStep,go:step=>{this.quizStep=step;},back:{label:t('Vue d’ensemble'),onClick:()=>this.path('')},settings:()=>this.path('reglages')});
  const h=this.health,version=h?.version??'';
  return html`${pageHead({title:t('Réglages'),subtitle:t('Ce qui vaut pour toute la maison.')})}
  ${foyerPage({head:false,foyer:this.foyer(),busy:this.busy,stove:this.hasStove(),allergy:!!this.snapshot?.home.pollen_allergy,weatherLinked:!!this.snapshot?.home.weather,back:{label:'',onClick:()=>{}},change:next=>void this.saveFoyer(next),setAllergy:on=>void this.setPollenAllergy(on),
   home:this.snapshot?{...this.habitsContext(),uses:this.houseUses()}:undefined})}
  ${this.lightsCard()}
  ${this.errorBlock()}`;}
 /** « À propos » (socle 1.22): Confort's versions, its advice engine's, how to add a card, the project's links. */
 private aboutScreen(){const h=this.health,version=h?.version??'';
  const bricks=(h?.extensions??[]).filter(x=>x.official&&x.state==='linked').map(x=>x.name);
  return aboutPage({name:'Hestia Confort',repository,card:t('Tableau de bord → Ajouter une carte → Hestia Confort, ou Hestia Confort · logement.'),
   versions:[[t('Hestia Confort'),version||'—'],...(h?.advisor?[[t('Moteur de conseil'),h.advisor] as [string,string]]:[]),['API','hestia_comfort_api v1'],
    ...(h?.socle?[[t('Socle commun'),h.socle] as [string,string]]:[]),[t('Liaisons'),bricks.length?bricks.join(' · '):t('Aucune brique reliée')]]});}
 private foyer():Foyer{return this.snapshot?.home.foyer??{};}
 /** A new room starts from the house's range (« Votre maison »); its windows take the rest as they read it. */
 private withHouse(room:RoomConfig):RoomConfig{const p=this.foyer().plage??{};return {...room,settings:{...room.settings,...p}};}
 /** A heating for the whole house in some room: the stove's settings are shown. */
 private hasStove(){return !!this.snapshot?.rooms.some(r=>(r.config.heaters??[]).some(h=>h.scope==='house'||h.kind==='stove'||h.kind==='pellet'));}
 private async saveFoyer(foyer:Foyer){this.busy=true;this.error='';
  try{this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/set_foyer',foyer});this.revision=this.snapshot.revision;}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}}
 private async setPollenAllergy(allergy:boolean){this.busy=true;
  try{this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/set_pollen_allergy',allergy});this.revision=this.snapshot.revision;}
  catch(e){this.error=(e as {message?:string}).message??t('Le réglage n’a pas pu être enregistré.');}finally{this.busy=false;}}
 /** From the general settings to a room: their draft is kept for the way back. */
 private async openRoom(entry_id:string,section=''){const room=this.snapshot?.rooms.find(r=>r.entry_id===entry_id);if(!room)return;
  // They stay on screen while the room loads: no other page shows in between.
  this.remember();this.workspaceKey='';await this.editRoom(room);if(this.draft)this.exteriorDraft=undefined;else this.workspaceKey='pieces';const stage=roomSections.find(x=>x.path===section)?.stage;if(section&&stage!=null&&this.draft)this.go(stage);}
 /** One extension: what it is for, its state, and the one thing to do (link it, install it) when it is not used. */
 /** The lights that show the advice, saved at once: the whole home here, or room by room in each room's Notifications tab. */
 private lights():Lights{return this.snapshot?.home.lights??noLights();}
 private async saveLights(lights:Lights){this.busy=true;this.error='';
  try{this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/set_lights',lights});}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}}
 /** A light's segments and LEDs, asked once per light; the editor draws without them until they come. */
 private infoOf(rule:LightRule|null){const id=rule?.entity_id;if(!id)return undefined;
  if(!(id in this.lightInfo)){this.lightInfo={...this.lightInfo,[id]:null};
   void this.ws<LightInfo>({type:'hestia_comfort/light_info',entity_id:id}).then(info=>{this.lightInfo={...this.lightInfo,[id]:info};},()=>undefined);}
  return this.lightInfo[id]??undefined;}
 /** Which segment shows which room, for the strip's board. */
 private lightUsers(){const l=this.lights(),users:Record<string,string>={};
  if(l.mode==='home'&&l.home)users[l.home.entity_id]=t('Confort · {room}',{room:t('Tout le logement')});
  if(l.mode==='rooms')for(const r of this.snapshot?.rooms??[])if(l.rooms[r.entry_id])users[l.rooms[r.entry_id].entity_id]=t('Confort · {room}',{room:r.title});
  return users;}
 /** « Lumières »: who drives the light, then the light itself on its own page (or in each room's Notifications). */
 private lightsCard(){const l=this.lights(),rooms=this.snapshot?.rooms??[];
  const name=(r?:LightRule|null)=>r?String(this.hass?.states?.[r.entity_id]?.attributes?.friendly_name??r.entity_id):t('aucune');
  return listSection(t('Lumières'),[listRow({label:t('Qui pilote la lumière'),value:segmented(t('Qui pilote la lumière'),[['home',t('Tout le logement')],['rooms',t('Pièce par pièce')]],l.mode,m=>void this.saveLights({...l,mode:m}),this.busy)}),
   ...(l.mode==='home'?[listRow({label:t('Lumière'),value:name(l.home),go:()=>this.path('reglages/lumiere')})]:rooms.map(r=>listRow({label:r.title,value:name(l.rooms[r.entry_id]),go:()=>void this.openRoom(r.entry_id,'notifications')})))],
   {help:html`<p>${t('Une lumière prend la couleur du conseil : bleu tout va bien, vert à saisir, orange un geste.')}</p>`});}
 /** The light of the whole home, with its rule, its colours and its effects. */
 private lightScreen(){const l=this.lights(),rooms=this.snapshot?.rooms??[];
  return html`${pageHead({back:{label:t('Réglages'),onClick:()=>this.path('reglages')},title:t('Lumière')})}
  ${lightEditor({hass:this.hass,wled:this.wledOn(),rule:l.home,busy:this.busy,info:this.infoOf(l.home),users:this.lightUsers(),follows:[{value:'home',label:t('Tout le logement')},...rooms.map(r=>({value:r.entry_id,label:r.title}))],change:rule=>void this.saveLights({...l,home:rule})})}
  ${this.errorBlock()}`;}
 /** To the general settings, the draft open here kept for later, as when opening another room. */
 private goSettings(){this.remember();this.workspaceKey='';this.draft=undefined;this.exteriorDraft=undefined;this.path('reglages');}
 /** WLED used: installed in Home Assistant and not turned off in Extensions. */
 private wledOn(){return this.uses('wled')&&Object.values(this.hass?.entities??{}).some(e=>e.platform==='wled');}
 /** A room's Notifications tab: its own light when the lights go room by room; the phone will come later. */
 private notifications(){const l=this.lights(),id=this.entryId;
  const light=l.mode==='home'?frame(t('Lumière'),html`${noteBox(t('Bon à savoir'),t('La lumière est réglée pour tout le logement, dans Réglages généraux.'))}<button class="nk-edit" ?disabled=${this.busy} @click=${()=>this.goSettings()}>${t('Ouvrir le réglage')}</button>`,{className:'nk-field-section nk-plain'})
   :!id?frame(t('Lumière'),html`<p class="hint">${t('Créez d’abord la pièce : sa lumière se règle ensuite ici.')}</p>`,{className:'nk-field-section nk-plain'})
   :lightEditor({hass:this.hass,wled:this.wledOn(),rule:l.rooms[id]??null,busy:this.busy,info:this.infoOf(l.rooms[id]??null),users:this.lightUsers(),taken:this.snapshot?.rooms.find(r=>r.entry_id!==id&&l.rooms[r.entry_id]&&l.rooms[r.entry_id].entity_id===l.rooms[id]?.entity_id)?.title,change:rule=>{const rooms={...l.rooms};if(rule)rooms[id]={...rule,follow:id};else delete rooms[id];void this.saveLights({...l,rooms});}});
  return light;}
 /** A third-party integration used or not, for every room; saved at once, without touching the other settings. */
 private async useExtension(key:string,enabled:boolean){this.busy=true;
  try{this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/set_extension',key,enabled});this.revision=this.snapshot.revision;await this.loadHealth();}
  catch(e){this.error=(e as {message?:string}).message??t('Le réglage n’a pas pu être enregistré.');}finally{this.busy=false;}}
 /** False when the person turned this integration off in the general settings. */
 private uses(key:string){return !(this.snapshot?.home.disabled??[]).includes(key);}
 private card(id:string){
  // The card is a dashboard resource, absent from a page opened straight on the panel: it comes with the panel's own version.
  if(!customElements.get('hestia-comfort-card')){
   if(this.cardLoad==='idle'){this.cardLoad='loading';import(/* @vite-ignore */ new URL('hestia-comfort-card.js'+new URL(import.meta.url).search,import.meta.url).href).then(()=>this.cardLoad='done',()=>this.cardLoad='failed');}
   return html`<p class="notice">${this.cardLoad==='failed'?t('L’aperçu de la carte apparaîtra après un rechargement de la page.'):t('Chargement de l’aperçu…')}</p>`;}
  if(this.previewCard?.id!==id){const el=document.createElement('hestia-comfort-card') as HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void};el.setConfig?.({type:'custom:hestia-comfort-card',entry_id:id,format:'full'});el.hass=this.hass;this.previewCard={id,el};}
  return this.previewCard!.el;
 }
 private previewScreen(){const s=this.snapshot!,room=s.rooms.find(r=>r.entry_id===this.preview);if(!room)return this.home();
  return html`<h1 tabindex="-1">${this.previewEdited?t('{name} : modifications enregistrées',{name:room.title}):t('{name} est prêt',{name:room.title})}</h1><p>${t('Voici sa carte confort, telle qu’elle apparaîtra sur votre tableau de bord. Les conseils se mettent à jour en quelques secondes.')}</p><div class="preview">${this.card(room.entry_id)}</div>
   <h2>${t('Ajouter la carte à un tableau de bord')}</h2><ol class="howto"><li>${t('Ouvrez votre tableau de bord, puis le crayon')} <strong>${t('Modifier')}</strong>.</li><li><strong>${t('Ajouter une carte')}</strong>${t(', puis cherchez')} <strong>${t('Hestia Confort')}</strong>${t('. Pour toutes les pièces d’un coup :')} <strong>${t('Hestia Confort · logement')}</strong>.</li><li>${t('Choisissez la pièce')} <strong>${room.title}</strong> ${t('et enregistrez.')}</li></ol>
   ${!s.home.configured?html`<p class="notice">${t('Pour comparer avec le dehors (fraîcheur, pluie, vent, soleil), configurez maintenant l’extérieur du logement.')}</p>`:nothing}
   <div class="actions">${!s.home.configured?html`<button class="primary" @click=${()=>this.editExterior()}>${t('Configurer l’extérieur')}</button>`:nothing}<button class=${s.home.configured?'primary':''} @click=${()=>{this.preview=undefined;this.path('');}}>${t('Retour à Mon logement')}</button></div>`;}
 private foundRooms(){const list=this.overview!;const n=this.picked.length;
  return html`<section class="start"><h2>${t('Vos pièces trouvées')}</h2><p>${t('Voici les pièces trouvées dans Home Assistant. Décochez celles à ne pas suivre : vous pourrez tout retoucher ensuite, pièce par pièce.')}</p>
   <div class="found">${list.map(a=>{const ok=typeof a.suggestions.indoor_temperature==='string';return html`<div class="found-row"><label class="check"><input type="checkbox" ?disabled=${!ok} .checked=${this.picked.includes(a.area_id)} @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.picked=on?[...this.picked,a.area_id]:this.picked.filter(x=>x!==a.area_id);}}><span><strong>${a.name}</strong><span class="hint">${ok?this.detected(a.suggestions):a.temperatures>1?t('Plusieurs températures : à choisir'):t('Aucune température trouvée')}</span></span></label>${ok?nothing:html`<button @click=${()=>this.start(a)}>${t('Configurer')}</button>`}</div>`;})}</div>
   ${this.errorBlock()}<button class="primary" ?disabled=${this.busy||!n} @click=${()=>this.createAll()}>${n?(n>1?t('Créer les {n} pièces',{n}):t('Créer la pièce')):t('Cochez une pièce')}</button></section>`;}
 private home(){const s=this.snapshot!;const living=livingArea(s.areas,new Set(s.rooms.map(r=>r.config.area_id).filter((a):a is string=>!!a)));
  return html`
  ${this.head()}
  ${!s.rooms.length&&this.overview?.some(a=>typeof a.suggestions.indoor_temperature==='string')?this.foundRooms():!s.rooms.length?html`<section class="start"><h2>${t('Commençons par le Salon')}</h2>${living?html`<p>${t('La pièce « {name} » existe dans Home Assistant. Il vous proposera ses capteurs ; vous gardez, retirez ou complétez.',{name:living.name})}</p><button class="primary" @click=${()=>this.start(living)}>${t('Configurer le Salon')}</button>`:html`<p>${t('Aucune pièce « Salon » dans Home Assistant : une pièce libre est créée et vous choisissez ses capteurs.')}</p><button class="primary" @click=${()=>this.start(null,t('Salon'))}>${t('Créer le Salon')}</button>`}</section>`:html`<div class="room-list">${s.rooms.map(room=>html`<section class="room"><div><h3>${room.title}</h3><p class="hint">${coverage(room.config)}${room.config.area_id?'':' · '+t('pièce libre')}</p>${!room.loaded?html`<p class="warning hint">${t('Le calcul de cette pièce n’est pas chargé. Vérifiez ses capteurs et les journaux de l’intégration.')}</p>`:nothing}</div><button ?disabled=${this.busy} @click=${()=>this.editRoom(room)}>${t('Configurer')}</button></section>`)}</div>`}
  ${frame(s.rooms.length?t('Ajouter une pièce'):this.overview?t('Une pièce sans pièce Home Assistant ?'):t('Ou commencer par une autre pièce'),this.addRoom())}
  ${s.rooms.length?html`${frame(t('Les cartes'),html`<p>${t('Dans un tableau de bord :')} <strong>${t('Ajouter une carte')}</strong>${t(', puis')} <strong>${t('Hestia Confort')}</strong> ${t('pour une pièce, ou')} <strong>${t('Hestia Confort · logement')}</strong> ${t('pour la synthèse de toutes les pièces.')}</p>`)}`:nothing}${this.health?html`${this.health.todo.length?frame(t('À régler'),html`<ul class="hl-lines">${this.health.todo.map(l=>this.hline(l))}</ul>`,{className:'todo'}):nothing}${this.health.tips.length?frame(t('À améliorer'),html`<ul class="hl-lines">${this.health.tips.map(l=>this.hline(l))}</ul>`):nothing}<p><button @click=${()=>this.path('')}>${t('Retour à l’accueil Confort')}</button></p>`:this.healthError?html`<p class="notice" role="alert">${t('Le bilan technique n’a pas pu être chargé.')} <button @click=${()=>void this.loadHealth()}>${t('Réessayer')}</button></p>`:html`<p class="muted" role="status">${t('Actualisation du bilan…')}</p>`}`;}
 protected render(){if(this.hass?.user?.is_admin===false)return html`<main><h1>${t('Hestia Confort')}</h1><p>${t('La configuration du logement est réservée aux administrateurs Home Assistant.')}</p></main>`;
  const editing=!!(this.draft||this.exteriorDraft);
  // Inside the shared « Hestia-FB » panel, its header and tabs replace this one.
  const header=this.hasAttribute('embedded')?nothing:html`<header><button aria-label=${t('Ouvrir le menu Home Assistant')} @click=${()=>this.menu()}><span class="menu-icon"></span></button><strong>${t('Hestia Confort')}</strong></header>`;
  return html`${header}<main class=${(this.page==='health'||this.page==='review')&&!editing&&!this.preview&&this.snapshot?.rooms.length?'wide':''}>${this.confirmDiscard?html`<section class="notice" role="alertdialog" aria-label=${t('Abandonner le brouillon')}><h2>${t('Quitter sans enregistrer ?')}</h2><p>${t('Vos choix de cette page seront perdus.')}</p><div class="actions"><button @click=${()=>this.confirmDiscard=false}>${t('Continuer la configuration')}</button><button @click=${()=>this.discard()}>${t('Quitter sans enregistrer')}</button></div></section>`:nothing}
   ${!editing?html`${this.errorBlock()}${this.error&&!this.snapshot?html`<button @click=${()=>this.load()}>${t('Réessayer')}</button>`:nothing}`:nothing}${this.saved&&this.saved!==t('Enregistré')?html`<p class="notice success" role="status">${this.saved}</p>`:nothing}${this.busy&&!this.snapshot?html`<p class="loading" role="status">${t('Chargement de votre logement…')}</p>`:nothing}
   ${this.snapshot?(this.exteriorDraft?this.exterior():this.draft?this.wizard():this.preview?this.previewScreen():this.opening?html`<p class="muted" role="status">${t('Chargement…')}</p>`:this.page==='settings'||this.page==='foyer'?this.settingsPage():this.page==='pieces'?this.roomsPage():this.page==='learning'?this.learningPage():this.page==='about'?this.aboutScreen():this.page==='review'?html`<hestia-comfort-review .hass=${this.hass} .room=${this.reviewRoom} @review-navigate=${(e:CustomEvent<string>)=>this.path(e.detail)}></hestia-comfort-review>`:this.page==='health'&&this.snapshot.rooms.length?this.healthScreen():this.home()):nothing}${this.busy&&this.snapshot?html`<p class="busy" role="status">${t('Un instant…')}</p>`:nothing}</main>`;
 }
}
