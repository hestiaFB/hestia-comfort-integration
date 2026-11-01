import {LitElement,html,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {customElement,property,state} from 'lit/decorators.js';
import {live} from 'lit/directives/live.js';
import styles from './styles.css';
// The comfort review is shared with its Lovelace card (card/src/review.ts).
import '../card/src/review';
import {frame,noteBox,hubStyles,modernStyles,helpTip,defaultValue,pageHead,todoFrame,itemsFrame,stepMenu,stepFooter,extensionsFrame,detectedFrame,versionsFrame,extensionCard as nkExtensionCard,removeBlock as nkRemoveBlock,pageStyles,setLanguage,addDictionary,t,fr,currentLocale,currentLanguage,type NkLine,type NkLevel} from './socle/ui';
import {PANEL_EN} from './i18n-en';
import {lightEditor,noLights,type Lights,type LightRule,type LightInfo} from './lights';
import {words,labels,indoor,outdoor,multiple,exposures,kinds,measurement,newRoom,coverage,exteriorSummary,livingArea,defaultOpening,warningText,warningId,stages,intros,outdoorGroups,changedAdvanced,advancedDefaults,airSource,airChoices,exteriorChoices,airReferenceDefaults,vocPreset,thresholdSources,type Choice,type Candidate,type Discovery,type Health,type HealthLine,type Target,type Snapshot,type Hass,type Room,type RoomConfig,type Spec,type Twins,type Twin,type Progress,type Extension,seasonNames} from './model';
// Confort's words beside the hub's (socle 1.13): French in the code, English for any other language.
addDictionary('en',PANEL_EN);
/** An extension's state in one word, and its colour: blue when linked, orange when one step is left. */
const extState:Record<Extension['state'],[string,string]>={linked:[fr('liée'),'ok'],found:[fr('à lier'),'act'],missing:[fr('non installée'),''],off:[fr('désactivée'),'']};
const extIcon:Record<string,string>={wled:'light',hestia_weather:'weather',versatile_thermostat:'heating',adaptive_cover_pro:'openings',cover_automatic:'openings',cover_extender:'openings',alarmo:'presence'};
/** HACS opens the repository from its GitHub address. */
const hacsUrl=(url:string)=>{const [owner,repository]=url.replace('https://github.com/','').split('/');return `https://my.home-assistant.io/redirect/hacs_repository/?owner=${owner}&repository=${repository}&category=integration`;};
/** Plural words: French says « 0 point », English « 0 points ». */
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
const roomSections=[{stage:0,path:'temperature',label:fr('Température'),title:fr('Température et humidité'),icon:'temperature'},{stage:1,path:'ouvertures',label:fr('Ouvertures'),title:fr('Fenêtres et portes'),icon:'openings'},{stage:2,path:'air',label:fr('Air intérieur'),title:fr('Qualité de l’air'),icon:'air'},{stage:6,path:'presence',label:fr('Présence'),title:fr('Présence'),icon:'presence'},{stage:3,path:'chauffage',label:fr('Chauffage'),title:fr('Chauffage'),icon:'heating'},{stage:4,path:'piece',label:fr('La pièce'),title:fr('La pièce et ses réglages'),icon:'room'},{stage:7,path:'notifications',label:fr('Notifications'),title:fr('Notifications'),icon:'light'}];
const roomOrder=[0,1,2,6,3,4,7,5];
// The step menu ends on « Récapitulatif », as in every Hestia brick (socle 1.12).
const menuSections=[...roomSections,{stage:5,path:'recapitulatif',label:fr('Récapitulatif'),title:fr('Récapitulatif'),icon:'review'}];
const repository='https://github.com/hestiaFB/hestia-comfort-integration';
// The third-party integrations by theme on the Extensions page, as in Hestia Weather; one not listed here goes under « Autres ».
const themes:[string,string[]][]=[[fr('Chauffage'),['versatile_thermostat']],[fr('Volets'),['adaptive_cover_pro','cover_automatic','cover_extender']],[fr('Présence'),['alarmo']],[fr('Lumières'),['wled']],[fr('Autres'),[]]];
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
 static styles=[unsafeCSS(styles),hubStyles,modernStyles,pageStyles];
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
 @state() private healthError='';
 private healthGeneration=0;
 // The tab opens on the home's technical state; « Modifier » leads to the rooms.
 @state() private page:'health'|'rooms'|'review'|'settings'='health';
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
 connectedCallback(){super.connectedCallback();if(this.hass&&!this.snapshot){this.connection=this.hass.connection;void this.load();}else if(this.healthLoading&&this.snapshot)void this.loadHealth();window.addEventListener('beforeunload',this.beforeUnload);void loadPicker().then(tag=>this.pickerTag=tag);}
 disconnectedCallback(){super.disconnectedCallback();this.workspaceGeneration++;this.opening=false;if(this.busy)this.routeHandled=undefined;this.generation++;this.healthGeneration++;window.removeEventListener('beforeunload',this.beforeUnload);}
 protected updated(changed:PropertyValues){
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
  try{const value=await this.ws<Snapshot>({type:'hestia_comfort/configuration'});if(generation===this.generation){this.snapshot=value;await this.followRoute();if(!value.rooms.length)await this.loadOverview();}}
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
   ${itemsFrame({title:t('Vos pièces'),items:this.snapshot!.rooms.map(r=>({name:r.title,detail:coverage(r.config)}))})}`;
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
  const known=twins.filter(r=>r.progress?.complete).length,todo=h.todo.length,tips=h.tips.length;
  const kpi=(value:string,label:string,cls='')=>html`<div class=${'ac-kpi '+cls}><b>${value}</b><span>${label}</span></div>`;
  return html`${this.head({level:h.level==='ok'?'ok':'todo',text:h.level==='ok'?t('Tout fonctionne'):h.summary,detail:h.rooms_summary})}
  <div class="ac-kpis">${kpi(`${answering} / ${configured}`,t('capteurs qui répondent'),answering===configured?'ok':'bad')}
   ${kpi(`${known} / ${twins.length||h.rooms.length}`,t('pièces observées à 100 %'),twins.length&&known===twins.length?'ok':'')}
   ${kpi(String(todo),(many(todo)?t('points à régler'):t('point à régler'))+(tips?' · '+t('{n} à améliorer',{n:tips}):''),todo?'bad':'ok')}</div>
  ${todoFrame(h.todo.map(l=>this.nkLine(l)),h.tips.map(l=>this.nkLine(l)))}
  ${this.roomsBox()}
  <div class="ac-cols">${this.learningBox()}<div>${this.extensionsSummary()}</div></div>${this.versionsBox()}`;}
 /** The top of the Accueil: the same as every brick's, with its way to the general settings. */
 private head(state?:{level:NkLevel;text:string;detail?:string}){return pageHead({title:t('Confort'),subtitle:t('Vos pièces, ce que Confort apprend et ses extensions.'),state,actions:[{label:t('Réglages généraux'),onClick:()=>this.path('reglages'),disabled:this.busy}]});}
 private nkLine(l:HealthLine):NkLine{return {level:l.level,text:l.text,why:l.why,go:l.target?{label:l.target.label,onClick:()=>void this.goTo(l.target!),disabled:this.busy}:null};}
 /** Versions and useful links, as on Hestia Weather's home. */
 private versionsBox(){const h=this.health!,version=h.version??'';
  const bricks=(h.extensions??[]).filter(x=>x.official&&x.state==='linked').map(x=>x.name);
  return versionsFrame([[t('Intégration'),version||t('Version non reçue')],[t('Carte'),version||t('Version non reçue')],['API','hestia_comfort_api v1'],[t('Socle commun'),h.socle||t('Version non reçue')],[t('Liaisons'),bricks.length?bricks.join(' · '):t('Aucune brique reliée')]],repository,'hestia_comfort');}
 /** The state of each extension, in one word; linking and installing are in the general settings. */
 private extensionsSummary(){const h=this.health!,level:Record<string,NkLevel>={ok:'ok',act:'todo'};
  return extensionsFrame((h.extensions??[]).map(x=>({name:x.name,group:x.official?t('Briques Hestia'):t('Extensions tierces'),pill:{text:t(extState[x.state][0]),level:level[extState[x.state][1]]??'none'}})),{label:t('Gérer les extensions'),onClick:()=>this.path('extensions'),disabled:this.busy});}
 /** Where the station's sun sensor is shaded, learned from its history: there the sun is estimated. */
 private shadeRow(){
  const shade=(this.twins?.rooms??[]).map(r=>r.sun_shade).find(s=>s)??null;if(!shade)return nothing;
  const morning=shade.shaded.some(a=>a<180),afternoon=shade.shaded.some(a=>a>=180);
  const when=morning&&afternoon?t('le matin et l’après-midi'):morning?t('le matin'):afternoon?t('l’après-midi'):'';
  return html`<p class="hint">${when?t('Ensoleillement : station à l’ombre {when}, soleil estimé.',{when}):t('Ensoleillement : station dégagée.')}</p>`;
 }
 /** Each room once: what measures it, how well it is learned, and a clear way to change it or add another. */
 private roomsBox(){const h=this.health!,twins=new Map((this.twins?.rooms??[]).map(r=>[r.entry_id,r]));
  const observed=(entry_id:string)=>{const r=twins.get(entry_id);if(!r)return html`<span class="muted">—</span>`;const st=learnState(r.twin,r.progress);return html`<span class=${'tw-pill '+st.cls}>${st.label}</span>`;};
  // What is left to see, in words; once everything is seen, how closely the room is forecast.
  const left=(entry_id:string)=>{const r=twins.get(entry_id);if(!r)return html`<span class="muted">—</span>`;
   const st=learnState(r.twin,r.progress),p=r.twin.precision;
   return st.missing.length?html`<span class="ac-prec ac-left">${st.missing.map(m=>html`<span>${m}</span>`)}</span>`
    :html`<span class="ac-prec">${p?t('tout vu · ±{temp} °C · ±{hum} %',{temp:num(p.temperature,p.temperature<1?2:1),hum:num(p.humidity,0)}):t('tout vu')}</span>`;};
  // What the advice can already promise, measure by measure (« Conseil optimisé » on the card), or what holds it back.
  const optimised=(entry_id:string)=>{const r=twins.get(entry_id);if(!r)return html`<span class="muted">—</span>`;
   const ready=r.progress?.ready,p=r.twin.precision,seen=r.progress?.seen;if(!ready)return html`<span class="muted">—</span>`;
   const learnt=[ready.humidity?t('humidité'):'',ready.temperature?t('température'):'',...(ready.air??[]).map(a=>a==='co2'?'CO₂':'COV')].filter(Boolean);
   if(learnt.length)return html`<span class="ac-ready">${learnt.join(' · ')}</span>`;
   const blocked=r.twin.status!=='ready'||(seen?.days??0)<7?t('une semaine de mesures d’abord'):!p?t('prévisions à vérifier')
    :p.temperature>0.5&&p.humidity>3?t('prévisions à affiner (±{temp} °C, ±{hum} %)',{temp:num(p.temperature,2),hum:num(p.humidity,0)})
    :(seen?.airings??0)<5&&(seen?.open??0)<6?t('fenêtres à observer davantage')
    :p.humidity>3?t('humidité à affiner (±{hum} %)',{hum:num(p.humidity,0)}):t('température à affiner (±{temp} °C)',{temp:num(p.temperature,2)});
   return html`<span class="muted">${t('pas encore')}</span><span class="ac-prec">${blocked}</span>`;};
  // What the other room weighs here, as learned by this room's twin: its windows, its air, its heating.
  const byTitle=new Map((this.twins?.rooms??[]).map(x=>[x.title,x]));
  const weights=(r:{entry_id:string;title:string},others:string[])=>{const me=twins.get(r.entry_id)?.twin.room,other=others.length===1?byTitle.get(others[0])?.twin.room:null;
   const heat=me?.heating_degrees!=null&&other?.heating_degrees?Math.round(100*me.heating_degrees/other.heating_degrees):null;
   const parts=[me?.far_window_percent!=null?t('fenêtres {n} %',{n:me.far_window_percent}):'',me?.mixing_percent!=null?t('air {n} % par heure',{n:me.mixing_percent}):'',heat!=null?t('chauffage {n} %',{n:Math.min(heat,100)}):''].filter(Boolean);
   return parts.length?html`<small class="ac-weight">${t('Poids ici : {parts}',{parts:parts.join(' · ')})}</small>`:nothing;};
  const shared=(r:{entry_id:string;title:string})=>{const others=(this.volumeName(r.entry_id)??'').split(' · ').filter(x=>x&&x!==r.title);return others.length?html`<small>${t('Même air que {names}',{names:others.join(t(' et '))})}</small>${weights(r,others)}`:nothing;};
  // Read only: a room opens its sheet in the review; changing it is in the general settings.
  return frame(t('Vos pièces'),html`<div class="ac-bar"><p class="hint">${t('Appuyez sur une pièce pour voir son bilan.')}</p></div>
   <div class="ac-list"><div class="ac-r ac-head" aria-hidden="true"><span>${t('Pièce')}</span><span>${t('Observé')}</span><span>${t('Ce qui reste à apprendre')}</span><span>${t('Conseils optimisés')}</span></div>
   <ul class="ac-rows" aria-label=${t('Vos pièces')}>${h.rooms.map(r=>html`<li class="ac-r"><div class="ac-room"><button class="link ac-open" @click=${()=>this.path('bilan/'+r.entry_id)}>${r.title}</button>${shared(r)}</div>
     <div class="ac-cell ac-c1" data-label=${t('Observé')}>${observed(r.entry_id)}</div><div class="ac-cell ac-c2" data-label=${t('Ce qui reste à apprendre')}>${left(r.entry_id)}</div>
     <div class="ac-cell ac-c3" data-label=${t('Conseils optimisés')}>${optimised(r.entry_id)}</div></li>`)}</ul></div>
   <div class="ac-foot"><p class="hint">${t('Observé : ce que Confort a vu de la pièce ; Optimal quand il a tout vu. Conseils optimisés : ce qu’il prévoit assez juste pour annoncer un résultat.')}</p></div>`,{className:'ac-rooms'});}
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
 /** What learning asks and what it gave this week; the state of each room is in « Vos pièces ». */
 private learningBox(){
  return frame(t('Apprentissage'),html`${this.learningHow()}${this.learningQuestions()}${this.learningWeek()}`);
 }
 /** What learning is, in a few plain lines, and how far the home has got. */
 private learningHow(){
  const rooms=(this.twins?.rooms??[]).filter(r=>r.progress),mean=rooms.length?Math.round(rooms.reduce((n,r)=>n+r.progress!.percent,0)/rooms.length):null;
  const done=rooms.filter(r=>r.progress!.complete).length;
  // Rooms that already give at least one optimised advice, without waiting for 100 %.
  const some=rooms.filter(r=>{const x=r.progress!.ready;return !!x&&(x.humidity||x.temperature||(x.air??[]).length>0);}).length;
  return html`${mean!=null?html`<div class="tw-week">${[[`${mean} %`,t('du logement observé')],[`${some} / ${rooms.length}`,many(some)?t('pièces ont déjà des conseils optimisés'):t('pièce a déjà des conseils optimisés')],[`${done} / ${rooms.length}`,many(done)?t('pièces observées à 100 %'):t('pièce observée à 100 %')]].map(([b,t])=>html`<div><b>${b}</b><span>${t}</span></div>`)}</div>`:nothing}
   <ul class="tw-how">
    <li>${t('Confort observe chaque pièce toutes les 30 minutes : température, humidité, soleil, fenêtres, chauffage.')}</li>
    <li>${t('Il en déduit comment elle réagit, puis vérifie ses prévisions sur la veille.')}</li>
    <li>${t('« Observé » dit ce que Confort a vu. « Conseils optimisés » : dès que ses prévisions sont assez justes pour une mesure (humidité, température, air), le conseil annonce son résultat.')}</li>
    <li>${t('100 % : il a tout vu. Une semaine de mesures, des prévisions justes, cinq aérations, le chauffage en marche.')}</li></ul>`;
 }
 /** Questions on the habits found: a « yes » names a cause; nothing is ever guessed without it. */
 private learningQuestions(){
  const asked=(this.twins?.rooms??[]).flatMap(r=>(r.questions??[]).map(q=>({...q,entry_id:r.entry_id})));
  if(!asked.length)return nothing;
  const answer=async(entry_id:string,key:string,value:string)=>{
   try{await this.ws({type:'hestia_comfort/answer',entry_id,key,answer:value});this.twins=await this.ws<Twins>({type:'hestia_comfort/twins'});}
   catch(e){this.error=this.message(e);}};
  return html`<h3 class="tw-sub">${t('Pour affiner l’apprentissage')}</h3>${asked.map(q=>html`<div class="tw-q"><p>${q.text}<small>${q.hint}</small></p>
   <div class="tw-btns">${[['yes',t('Oui')],['no',t('Non')],['unknown',t('Je ne sais pas')]].map(([v,l])=>html`<button @click=${()=>void answer(q.entry_id,q.key,v)}>${l}</button>`)}</div></div>`)}`;
 }
 /** The week of the feedback loop, over every room: airings followed, what they gave, predictions held. */
 private learningWeek(){
  const weeks=(this.twins?.rooms??[]).map(r=>({title:r.title,w:r.week})).filter(x=>x.w&&(x.w.followed||x.w.ignored));
  if(!weeks.length)return nothing;
  const sum=(k:'followed'|'ignored'|'evaluated'|'held')=>weeks.reduce((n,x)=>n+x.w![k],0);
  const dry=weeks.filter(x=>x.w!.gains.humidity!=null),gain=dry.length?dry.reduce((n,x)=>n+x.w!.gains.humidity,0)/dry.length:null;
  const best=[...dry].sort((a,b)=>a.w!.gains.humidity-b.w!.gains.humidity)[0];
  const tile=(value:string,label:string)=>html`<div><b>${value}</b><span>${label}</span></div>`;
  return html`<h3 class="tw-sub">${t('Cette semaine')}</h3><div class="tw-week">
   ${tile(String(sum('followed')),many(sum('followed'))?t('aérations conseillées et suivies'):t('aération conseillée et suivie'))}
   ${gain!=null?tile(`${num(gain,0)} %`,t('d’humidité en moyenne après une aération')):nothing}
   ${sum('evaluated')?tile(t('{n} sur {total}',{n:sum('held'),total:sum('evaluated')}),t('prévisions tenues')):nothing}
   ${best?tile(best.title,t('la pièce qui gagne le plus à être aérée')):nothing}
   ${sum('ignored')?tile(String(sum('ignored')),many(sum('ignored'))?t('conseils laissés sans suite'):t('conseil laissé sans suite')):nothing}</div>`;
 }
 /** A command of Confort, answered in the panel's language (engine/i18n.py). */
 private ws<T>(msg:Record<string,unknown>){return this.hass!.callWS<T>({...msg,language:this.hass!.language});}
 private message(e:unknown){return typeof e==='object'&&e&&'message' in e?String(e.message):t('La connexion est indisponible. Réessayez sans quitter votre brouillon.');}
 private path(path:string){if(!this.isConnected)return;this.opening=false;const full='/'+path.replace(/^\//,'');this.routeHandled=full==='/'?'':full;const [key,sub]=path.split('/');if(key==='bilan'){this.page='review';this.reviewRoom=sub;}else if(key==='reglages')this.page='settings';else if(key==='pieces'||!key)this.page=key==='pieces'?'rooms':'health';history.pushState(null,'',(this.route?.prefix??'/hestia/confort')+(path?'/'+path:''));window.dispatchEvent(new CustomEvent('location-changed'));}
 private remember(){if(this.workspaceKey&&(this.draft||this.exteriorDraft))this.drafts.set(this.workspaceKey,{draft:this.draft,exteriorDraft:this.exteriorDraft,discovery:this.discovery,entryId:this.entryId,stage:this.stage,revision:this.revision,acknowledged:this.acknowledged,proposed:this.proposed,search:this.search,weatherEntry:this.weatherEntry});}
 private async followRoute(){
  const path=this.route?.path??'';if(this.routeHandled===path)return;
  // A route that is not the browser's address is a late copy of one already left (Home Assistant can send the former
  // page again just after a save): following it reopened that page behind the preview, stuck on « Chargement… ».
  const here=decodeURI(location.pathname).replace(/\/$/,'');if(this.route?.prefix&&here!==(this.route.prefix+path).replace(/\/$/,''))return;this.routeHandled=path;const generation=++this.workspaceGeneration;this.remember();
  const [id,section]=path.split('/').filter(Boolean);const key=id??'';
  // A newer page takes over: the « Chargement… » of the one it replaces must not stay forever.
  this.opening=false;this.workspaceKey=key;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.preview=undefined;this.error='';this.saved='';this.confirmDiscard=false;this.confirmRemove=false;
  // The tab opens on its technical home; « pieces » is the list of rooms to set.
  // « pieces » (the former list of rooms) is now the general settings, like every brick's.
  if(key==='pieces'){this.path('reglages');return;}
  // The general settings only list the rooms; the extensions (and the outside they give) have their own page.
  if(key==='reglages'){this.page='settings';return;}
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
 // Creates every checked room at once with Hestia's unambiguous proposals; each room keeps its assistant.
 private async createAll(){
  const areas=(this.overview??[]).filter(a=>this.picked.includes(a.area_id));if(!areas.length){this.error=t('Cochez au moins une pièce.');return;}
  this.busy=true;this.error='';let created=0;
  try{for(const a of areas){const discovery=await this.discover(a.area_id);const snapshot:Snapshot=await this.ws<Snapshot>({type:'hestia_comfort/save_config',config:newRoom({area_id:a.area_id,name:a.name},'',discovery),revision:this.snapshot!.revision,acknowledged:[]});this.snapshot=snapshot;created++;}
   this.saved=(created>1?t('{n} pièces créées.',{n:created}):t('{n} pièce créée.',{n:created}))+' '+t('Ouvrez chacune pour renseigner l’exposition des ouvrants et compléter si besoin.');this.overview=undefined;}
  catch(e){this.error=(created?(created>1?t('{n} pièces créées, puis : ',{n:created}):t('{n} pièce créée, puis : ',{n:created})):'')+this.message(e);}
  finally{this.busy=false;}
 }
 private menu(){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));}
 private areaName(id:string|null){return id?this.snapshot?.areas.find(a=>a.area_id===id)?.name??id:'';}
 private async discover(area_id?:string|null,entry_id?:string){
  return await this.ws<Discovery>({type:'hestia_comfort/discover',...(area_id?{area_id}:{}),...(entry_id?{entry_id}:{})});
 }
 private begin(){this.confirmRemove=false;this.adding=false;this.busy=true;this.error='';this.saved='';this.preview=undefined;this.search={};this.confirmed=false;}
 private async start(area:{area_id:string;name:string}|null,name=''){
  if(!area&&!name.trim()){this.error=t('Donnez un nom à la pièce libre, par exemple « Étage » ou « Suite parentale ».');return;}
  // From the general settings their draft is kept for the way back, and gives way to the new room's.
  const workspace=this.workspaceGeneration;this.remember();this.begin();
  try{const d=await this.discover(area?.area_id);if(workspace!==this.workspaceGeneration)return;this.exteriorDraft=undefined;this.discovery=d;this.revision=d.revision;this.entryId=undefined;this.draft=newRoom(area,name.trim(),d);this.proposed=[...Object.values(this.draft.sources),...this.draft.windows];this.stage=0;this.acknowledged=[];this.freeName='';this.workspaceKey='nouvelle';this.path('nouvelle/temperature');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editRoom(room:Room,route=true){
  const cached=this.drafts.get(room.entry_id);if(route&&cached){Object.assign(this,cached);this.workspaceKey=room.entry_id;this.path(room.entry_id+'/'+(roomSections.find(x=>x.stage===this.stage)?.path??'recapitulatif'));return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover(room.config.area_id,room.entry_id);if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.entryId=room.entry_id;
   const config=structuredClone(room.config);config.area_id??=null;config.openings??={};for(const id of config.windows)config.openings[id]??={...defaultOpening(),sheltered:config.rain_exposed===false};
   this.draft=config;this.proposed=[];this.stage=0;this.acknowledged=[...(config.acknowledged??[])];this.workspaceKey=room.entry_id;if(route)this.path(room.entry_id+'/temperature');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editExterior(route=true){
  const cached=this.drafts.get('extensions');if(route&&cached){Object.assign(this,cached);this.workspaceKey='extensions';this.path('extensions');return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover();if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.exteriorDraft=structuredClone(this.snapshot!.home.sources);this.weatherEntry=this.snapshot!.home.weather??null;this.acknowledged=[...(this.snapshot!.home.acknowledged??[])];this.proposed=[];this.workspaceKey='extensions';if(this.weatherEntry)await this.useWeather(this.weatherEntry,true);if(route)this.path('extensions');}
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
 // The exterior: its source first; with Hestia Weather everything is read from it, with own sensors each one is chosen.
 private exteriorSource(){const s=this.snapshot!,nw=s.hestia_weather,from=this.weatherEntry?'weather':'own';
  return html`<span id="l-from" class="sr-only">${t('Source des mesures du dehors')}</span>
   ${this.choiceList('from','l-from',exteriorChoices(s),from,v=>v==='weather'?void this.useWeather(nw!.places[0].entry_id):this.ownSensors())}
   ${from==='weather'&&(nw?.places.length??0)>1?this.zone(t('Lieu Hestia Weather'),nw!.places.map(p=>({value:p.entry_id,label:p.title})),this.weatherEntry!,id=>void this.useWeather(id)):nothing}`;}
 /** One line per outdoor measure: its name, then its sensor (a choice only with own sensors), then its value now. */
 private exteriorRows(){const weather=!!this.weatherEntry,all=(key:string)=>this.discovery?.candidates[key]??[];
  const keys=outdoorGroups.flatMap(([,k])=>k),spec=this.exteriorDraft!.pollution,air=all('pollution').find(x=>x.entity_id===spec?.entity_id),wa=this.weatherAir;
  // The air comes from Hestia Weather's own choice (Atmo France or a WAQI station), or from its index entity.
  const airName=spec?.adapter==='hestia_air'&&wa?'Hestia Weather · '+wa.provider:air?air.name:'—';
  const airValue=spec?.adapter==='hestia_air'?(wa?.index?html`<span>${wa.label??t('indice {n}',{n:wa.index})}</span>`:html`<span class="bad">${t('ne répond pas')}</span>`)
   :air?html`<span class=${air.available?'':'bad'}>${air.atmo_label??measurement(air)}</span>`:html`<span class="muted">${spec?'—':t('non fourni par Hestia Weather')}</span>`;
  const title=this.snapshot?.hestia_weather?.places.find(p=>p.entry_id===this.weatherEntry)?.title;
  const value=(key:string)=>{const id=this.selected(key)[0],c=all(key).find(x=>x.entity_id===id);
   // With Hestia Weather, its season comes through its interface, as on its own card.
   if(weather&&key==='season')return this.weatherSeason?html`<span>${seasonNames[this.weatherSeason]??this.weatherSeason}</span>`:html`<span class="muted">${t('non fourni par Hestia Weather')}</span>`;
   if(key==='season'&&c)return html`<span class=${c.available?'':'bad'}>${seasonNames[String(c.value).toLowerCase().trim()]??c.value}</span>`;
   return !id?html`<span class="muted">${weather?t('non fourni par Hestia Weather'):'—'}</span>`:c?html`<span class=${c.available?'':'bad'}>${key==='wind_bearing'&&c.available&&c.value!==''&&Number.isFinite(Number(c.value))?t(exposures[Math.round(Number(c.value)/45)%8][1]):measurement(c)}</span>`:weather?html`<span class="muted">—</span>`:html`<span class="bad">${t('introuvable')}</span>`;};
  const sensor=(key:string)=>{const id=this.selected(key)[0]??'',c=all(key).find(x=>x.entity_id===id);
   if(weather)return html`<span class="ex-name">${key==='season'?t('Hestia Weather'):c?.name??(id||'—')}</span>`;
   const ids=all(key).map(x=>x.entity_id);if(!ids.length)return html`<span class="muted">${t('Aucun capteur compatible')}</span>`;
   const changed=(v:unknown)=>{if(v===''||v==null){if(id)this.clear(key,id);}else this.pick(key,v);};
   return html`${this.pickerTag?this.selector(key,ids,id,labels[key],changed):html`<select aria-label=${labels[key]} @change=${(e:Event)=>changed((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!id}>${t('Aucun')}</option>${all(key).map(x=>html`<option value=${x.entity_id} ?selected=${x.entity_id===id}>${x.name} · ${this.where(x)}</option>`)}</select>`}${c?this.warnings(c,key,true):nothing}`;};
  const rows=html`<div class="ex-rows">${keys.map(k=>html`<div class=${'ex-row'+(weather?'':' own')}><b>${labels[k]}</b><div class="ex-sensor">${sensor(k)}</div><div class="ex-value">${value(k)}</div></div>`)}
    ${weather?html`<div class="ex-row"><b>${labels.pollution}</b><div class="ex-sensor"><span class="ex-name">${airName}</span></div><div class="ex-value">${airValue}</div></div>`:nothing}</div>`;
  // With Hestia Weather the measures are only read: folded, under its choice. Own sensors are chosen one by one.
  if(weather)return html`<details class="ex-fold"><summary>${t('Voir les {n} mesures reprises',{n:keys.length+1})}${title?' · '+title:''}</summary>${noteBox(t('Lu dans Hestia Weather'),t('Reprises telles quelles. Une autre station se choisit dans Hestia Weather.'))}${rows}${this.shadeRow()}</details>${this.exteriorDraft!.pollution?this.airCaution():nothing}`;
  return frame(t('Vos capteurs'),rows);}
 /** The person's caution on a daily air index (Atmo France scale, also used by Hestia Weather). */
 private airCaution(){const spec=this.exteriorDraft!.pollution;
  return spec&&['atmo_daily','hestia_index','hestia_air'].includes(spec.adapter??'')?html`<label class="ex-caution">${t('Prudence à partir du niveau')}<select @change=${(e:Event)=>{this.exteriorDraft={...this.exteriorDraft!,pollution:{...spec!,block_from:Number((e.target as HTMLSelectElement).value)}};}}>${[t('Moyen'),t('Dégradé'),t('Mauvais'),t('Très mauvais'),t('Extrêmement mauvais')].map((label,i)=>html`<option value=${i+2} ?selected=${(spec!.block_from??4)===i+2}>${label}</option>`)}</select></label><p class="hint">${t('Votre préférence de prudence, pas une consigne sanitaire.')}</p>`:nothing;}
 // The outdoor air: with Hestia Weather, its index of the day; otherwise an integration, then its zone or place.
 /** The people the room is for: one for a bedroom, several for a shared room, none for the whole household. */
 private personsBlock(){const d=this.draft;if(!d)return nothing;const states=this.hass?.states??{},all=Object.keys(states).filter(e=>e.startsWith('person.')).sort(),mine=new Set(d.persons??[]);
  const toggle=(e:string,on:boolean)=>{const next=new Set(mine);if(on)next.add(e);else next.delete(e);this.draft={...d,persons:[...next]};};
  return frame(t('Personnes de la pièce'),html`<p class="hint">${t('Cochez les personnes à qui sert la pièce : une pour une chambre, plusieurs pour une pièce commune. La pièce compte alors comme vide quand elles sont toutes absentes, même si d’autres sont à la maison. Sans case cochée, toute la maison compte.')}</p>
   ${all.length?all.map(e=>html`<label class="check"><input type="checkbox" .checked=${mine.has(e)} @change=${(ev:Event)=>toggle(e,(ev.target as HTMLInputElement).checked)}>${String(states[e]?.attributes?.friendly_name??e)} <span class="muted">· ${states[e]?.state==='home'?t('à la maison'):t('absent')}</span></label>`)
    :html`<p class="muted">${t('Aucune personne dans Home Assistant (Paramètres → Personnes).')}</p>`}`);}
 private airBlock(){const all=this.discovery?.candidates.pollution??[],spec=this.exteriorDraft!.pollution,current=airSource(spec);
  const pickSource=(v:string)=>{if(v===current)return;if(v==='none'){this.clear('pollution');return;}
   const first=all.find(c=>c.adapter===(v==='atmo'?'atmo_daily':'hestia_index'));if(first)this.choose('pollution',first);};
  const zones=spec&&current!=='other'?all.filter(c=>c.adapter===spec.adapter):[],c=all.find(x=>x.entity_id===spec?.entity_id);
  if(this.weatherEntry)return nothing;
  return frame(labels.pollution,html`<span id="l-air" class="sr-only">${labels.pollution}</span><p class="hint">${t('Une précaution régionale du jour, pas une mesure à vos fenêtres.')}</p>
   ${this.choiceList('air','l-air',airChoices(this.snapshot!,all,current),current,pickSource)}
   ${spec&&current!=='other'?this.zone(current==='atmo'?t('Zone Atmo France'):t('Lieu Hestia Weather'),zones.map(z=>({value:z.entity_id,label:z.name+' · '+measurement(z)})),spec.entity_id,id=>this.pick('pollution',id)):nothing}
   ${current==='other'?html`<p class="hint">${c?.name??spec!.entity_id}</p>`:nothing}${c?this.warnings(c):nothing}${this.airCaution()}`);}
 // ---- Pieces shared by every step (charte des onglets de réglage) ----
 // What the step is for, in a frame that folds and stays folded.
 private intro(key:string){if(key==='6')return html`<div class="nk-step-help">${helpTip(t('Présence'),help.presence,t('À quoi sert cette étape ?'))}</div>`;return html`<div class="nk-step-help">${helpTip(t('Comprendre cette étape'),html`<ul>${intros[key].map(line=>html`<li>${t(line)}</li>`)}</ul>`,t('À quoi sert cette étape ?'))}</div>`;}

 private choiceList(name:string,label:string,choices:Choice[],value:string,pick:(v:string)=>void){
  return html`<div class="sources" role="radiogroup" aria-labelledby=${label}>${choices.map(c=>html`<label class="source ${c.value===value?'on':''} ${c.available?'':'off'}">
   <input type="radio" name=${name} .checked=${c.value===value} ?disabled=${!c.available||this.busy} @change=${()=>pick(c.value)}>
   <span><strong>${c.label}${c.badge?html` <em class="ex-badge benefit">${c.badge}</em>`:nothing}</strong><span>${c.hint}</span>${c.available?nothing:html`<span>${c.missing}${c.url?html` · <a href=${c.url} target="_blank" rel="noreferrer">${t('installer {name}',{name:c.label})}</a>`:nothing}</span>`}</span></label>`)}</div>`;}
 // The zone, place or device of the chosen source, shown even when there is only one.
 private zone(label:string,options:{value:string;label:string}[],value:string,pick:(v:string)=>void,hint=''){
  const known=options.some(o=>o.value===value);
  return html`<label class="zone">${label}<select ?disabled=${this.busy} @change=${(e:Event)=>pick((e.target as HTMLSelectElement).value)}>
   ${known?nothing:html`<option value="" selected disabled>${t('Introuvable · choisissez-en un autre')}</option>`}
   ${options.map(o=>html`<option value=${o.value} ?selected=${o.value===value}>${o.label}</option>`)}</select></label>${hint?html`<p class="hint">${hint}</p>`:nothing}`;}

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
 private cancel(){if(this.draft||this.exteriorDraft){this.confirmDiscard=true;return;}this.discard();}
 private discard(){const back=this.draft&&!this.exteriorDraft?'reglages':'';this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path(back);this.confirmDiscard=false;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.error='';this.acknowledged=[];this.proposed=[];}
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
 private warnings(c:Candidate,_key?:string,_selected?:boolean){return html`${c.warnings.filter(w=>!(w==='derived'&&c.warnings.includes('alias'))).map(w=>html`<p class="warning hint">${warningText[w]??t('Source à vérifier.')}</p>`)}${c.provenance.length>1?html`<p class="provenance">${t('Origine de la mesure :')} ${c.provenance.map((p,i)=>html`${i?' → ':nothing}${p.name}${p.area_id?` (${this.areaName(p.area_id)})`:nothing}`)}</p>`:nothing}`;}
 // Sensors chosen with a warning that the person has not confirmed yet: one confirmation covers them all.
 private pending(){const keys=this.exteriorDraft?[...outdoor]:[...indoor,'illuminance','co2','pm25','voc','purifier','ventilation','ventilation_boost','presence','heating','windows'];const out:{id:string;name:string}[]=[];
  for(const key of keys)for(const id of this.selected(key)){const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,id)))out.push({id:warningId(key,id),name:c.name});}
  if(this.draft)for(const m of Object.values(this.draft.openings))for(const [field,key] of [['cover_entity','covers'],['auto_entity','shutter_auto'],['override_entity','shutter_override']] as const){const id=m[field],c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,c.entity_id)))out.push({id:warningId(key,c.entity_id),name:c.name});}
  return out;}
 private confirmBlock(){const list=this.pending();if(!list.length)return nothing;
  return html`<div class="notice confirm"><p>${(list.length===1?t('Un capteur est à vérifier (autre pièce, porte d’appareil ou mesure recopiée) : {names}.',{names:list.map(x=>x.name).join(', ')}):t('{n} capteurs sont à vérifier (autre pièce, porte d’appareil ou mesure recopiée) : {names}.',{n:list.length,names:list.map(x=>x.name).join(', ')}))+' '+(this.exteriorDraft?t('Les explications sont plus haut.'):t('Les explications sont aux étapes précédentes.'))}</p><label class="check"><input type="checkbox" .checked=${this.confirmed} @change=${(e:Event)=>{this.confirmed=(e.target as HTMLInputElement).checked;if(this.confirmed)this.error='';}}>${t('J’ai vérifié, je confirme mes choix.')}</label></div>`;}
 private where(c:Candidate){return c.area_id?this.areaName(c.area_id):t('Sans pièce');}
 private candidateRow(c:Candidate,key:string){return html`<div class="candidate"><div><strong>${c.name}</strong><p>${measurement(c)} · ${this.where(c)}${c.reference?' · '+t('référence de la pièce'):nothing}</p>${this.warnings(c,key,false)}</div><button @click=${()=>this.choose(key,c)}>${t('Utiliser')}</button></div>`;}
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
 private picker(key:string,all:Candidate[],selected:string[]){
  const free=all.filter(c=>!selected.includes(c.entity_id));
  if(!free.length)return html`<p class="hint">${t('Aucun autre capteur compatible dans Home Assistant.')}</p>`;
  const label=multiple.has(key)&&selected.length?(key==='presence'?t('Ajouter un autre capteur de présence'):t('Ajouter un autre ouvrant')):t('Choisir un autre capteur');
  if(this.pickerTag)return html`<div class="picker">${this.selector(key,free.map(c=>c.entity_id),'',label,id=>this.pick(key,id))}</div>`;
  const text=(this.search[key]??'').toLowerCase();
  return html`<div class="picker"><label>${label}<input type="search" placeholder=${t('Tapez un nom, une pièce…')} .value=${this.search[key]??''} @input=${(e:Event)=>this.search={...this.search,[key]:(e.target as HTMLInputElement).value}}></label>${text?html`<div class="search-results">${free.filter(c=>(c.name+' '+c.entity_id+' '+this.where(c)).toLowerCase().includes(text)).slice(0,8).map(c=>this.candidateRow(c,key))}</div>`:nothing}</div>`;
 }
 private chosen(key:string,id:string,all:Candidate[],selected:string[]){
  const c=all.find(x=>x.entity_id===id);
  // Each chosen sensor is itself a picker: choosing another one replaces it in place.
  const ids=[id,...all.filter(x=>!selected.includes(x.entity_id)).map(x=>x.entity_id)];
  return html`<div class="choice">${this.pickerTag?html`<div class="chosen">${this.selector(key,ids,id,labels[key]===labels.windows?t('Ouvrant'):labels[key],v=>this.replace(key,id,v))}</div>`:html`<strong>${c?.name??id}</strong>`}
   <span>${c?measurement(c)+' · '+this.where(c):t('Capteur introuvable ou incompatible · choisissez-en un autre')}</span>${this.proposed.includes(id)?html`<span>${t('Proposé par Hestia · gardez-le, changez-le ou retirez-le')}</span>`:nothing}${c?.reference?html`<span>${t('Référence de cette pièce dans Home Assistant')}</span>`:nothing}${c?this.warnings(c,key,true):nothing}${key==='windows'?this.openingDetails(id):nothing}<button class="link" @click=${()=>this.clear(key,id)}>${t('Retirer')}</button></div>`;
 }
 private openingSource(id:string,key:'cover_entity'|'auto_entity'|'override_entity',kind:string,label:string){const m=this.draft!.openings[id]??defaultOpening(),all=this.discovery?.candidates[kind]??[],value=m[key]??'';
  const change=(next:unknown)=>{if(typeof next==='string'){this.acknowledged=this.acknowledged.filter(a=>a!==warningId(kind,value));this.confirmed=false;this.setOpening(id,{[key]:next||undefined});}};
  return html`<label>${this.pickerTag?nothing:label}${this.pickerTag?this.selector(kind,[...new Set([...(value?[value]:[]),...all.map(c=>c.entity_id)])],value,label,change):html`<select @change=${(e:Event)=>change((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!value}>${t('Non renseigné')}</option>${value&&!all.some(c=>c.entity_id===value)?html`<option selected value=${value}>${value} · ${t('introuvable')}</option>`:nothing}${all.map(c=>html`<option value=${c.entity_id} ?selected=${value===c.entity_id}>${c.name} · ${measurement(c)}</option>`)}</select>`}</label>${all.find(c=>c.entity_id===value)?this.warnings(all.find(c=>c.entity_id===value)!):nothing}`;
 }
 private evolutionNumber(key:'glazing_factor'|'presence_delay_minutes'|'voc_delay_minutes'|'voc_pause_minutes',label:string,initial:number,min:number,max:number,step:number){const d=this.draft!;return html`<label>${label}<input type="number" min=${min} max=${max} step=${step} .value=${String(d.evolution?.[key]??initial)} @input=${(e:Event)=>this.draft={...d,evolution:{...d.evolution,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`;}
 /** Chauffage : d'abord si la pièce est chauffée ; éteint, le thermostat et ses réglages s'effacent (gardés pour un retour). */
 private heatingStage(){const d=this.draft!,heated=d.heated!==false;
  return html`<label class="check ex-switch heat-switch"><input type="checkbox" role="switch" .checked=${heated} @change=${(e:Event)=>this.draft={...d,heated:(e.target as HTMLInputElement).checked}}>${t('Pièce chauffée')}</label>
   ${heated?html`${this.field('heating')}${d.sources.heating||d.sources.heating_indicator?this.field('heating_indicator'):nothing}`:noteBox(t('Pièce non chauffée'),t('Hestia ne conseillera jamais de réchauffer cette pièce et ne lit pas son chauffage.'))}`;}
 private airPresence(){return html`${['co2','pm25','voc','purifier','ventilation'].map(key=>this.field(key))}${this.draft?.sources.ventilation?this.field('ventilation_boost'):nothing}`;}
 private sensorSettings(key:string){const d=this.draft!;if(!d)return nothing;const selected=!!this.selected(key).length;if(!selected&&!['pm25','voc'].includes(key))return nothing;
 const voc=this.discovery?.candidates.voc?.find(c=>c.entity_id===d.sources.voc),unit=voc?(voc.unit??''):(d.evolution?.voc_threshold?.unit??''),preset=vocPreset(voc),availableVoc=this.discovery?.candidates.voc?.find(c=>vocPreset(c)),availablePreset=vocPreset(availableVoc);
 if(key==='co2')return html`<div class="sensor-settings"><h4>${t('Repères d’interprétation')}</h4>

  ${this.number('co2_potential',t('CO₂ : aérer ferait du bien (ppm)'),1000)}${this.number('co2_action',t('CO₂ : aérer (ppm)'),1200)}${this.number('co2_urgent',t('CO₂ : attention (ppm)'),1600)}
  ${defaultValue(t('800 / 1 000 / 1 500 ppm'),()=>this.draft={...d,settings:{...d.settings,co2_potential:airReferenceDefaults.co2_potential,co2_action:airReferenceDefaults.co2_action,co2_urgent:airReferenceDefaults.co2_urgent}},html`<p class="hint">${t('Pourquoi : le HCSP retient 800 ppm comme objectif de renouvellement d’air et 1 500 ppm comme valeur d’action rapide dans les établissements recevant du public. Ces repères en sont inspirés pour le logement, avec un palier intermédiaire à 1 000 ppm. Ces valeurs décrivent le confinement, pas la toxicité ni l’ensemble des polluants. Les anciens repères Hestia étaient 1 000 / 1 200 / 1 600 ppm.')} <a href=${thresholdSources.co2} target="_blank" rel="noopener noreferrer">${t('Source : HCSP, avis du 21 janvier 2022')}</a>.</p>`,{applied:['co2_potential','co2_action','co2_urgent'].every(k=>d.settings[k]===airReferenceDefaults[k as keyof typeof airReferenceDefaults])})}</div>`;
 if(key==='pm25')return html`<div class="sensor-settings"><h4>${t('Repère d’interprétation')}</h4>
  ${selected?this.number('pm25_action',t('PM2.5 : seuil de signalement (µg/m³)'),25):nothing}
  ${defaultValue('15 µg/m³',()=>this.draft={...d,settings:{...d.settings,pm25_action:airReferenceDefaults.pm25_action}},html`<p class="hint">${t('Pourquoi 15 : l’OMS recommande 15 µg/m³ en moyenne sur 24 heures (et 5 sur un an). 15 sert ici de repère de vigilance sur la mesure reçue ; ce n’est pas une exposition calculée sur 24 heures. Un pic n’est donc pas un dépassement de la moyenne OMS, et une mesure basse ne garantit pas l’absence de risque. Le seuil Hestia précédent était 25.')} <a href=${thresholdSources.pm25} target="_blank" rel="noopener noreferrer">${t('Source : OMS, lignes directrices 2021')}</a>.</p>`,{applied:d.settings.pm25_action===15,disabled:!selected,note:!selected?t('Choisissez le capteur pour activer le suivi.'):undefined})}</div>`;
 if(key==='voc')return html`<div class="sensor-settings"><h4>${t('Repère d’interprétation')}</h4>
  ${d.sources.voc?html`<p class="hint">${t('Capteur choisi : {name}. Unité : {unit}. Le seuil reste attaché à cette unité ; changer de capteur ou d’unité impose de le vérifier.',{name:voc?.name??d.sources.voc,unit:unit||t('indice sans unité')})}</p>
  <label>${t('Seuil COV ({unit})',{unit:unit||t('indice')})}<input type="number" min="0" step="any" .value=${d.evolution?.voc_threshold?.unit===unit?String(d.evolution.voc_threshold.value):''} @input=${(e:Event)=>{const value=(e.target as HTMLInputElement).value,evolution={...d.evolution};if(value)evolution.voc_threshold={value:Number(value),unit};else delete evolution.voc_threshold;this.draft={...d,evolution};}}></label>
  ${preset?html`${defaultValue(t('Indice 150'),()=>this.draft={...d,evolution:{...d.evolution,voc_threshold:{...preset}}},html`<p class="hint">${t('Pourquoi 150 : pour la VINDSTYRKA IKEA identifiée, c’est l’exemple d’action de Sensirion. L’indice 100 correspond au niveau habituel appris par le capteur ; un indice plus haut signale davantage de COV par rapport à cet historique. Ce n’est ni une concentration, ni une limite sanitaire. L’adaptation du capteur peut ramener une pollution persistante vers 100.')} <a href=${thresholdSources.voc} target="_blank" rel="noopener noreferrer">${t('Source : Sensirion, fonctionnement du VOC Index')}</a>.</p>`,{applied:d.evolution?.voc_threshold?.value===preset.value&&d.evolution?.voc_threshold?.unit===preset.unit})}`:html`<p class="hint">${t('Aucune valeur par défaut pour ce capteur : son unité seule ne suffit pas à justifier un seuil commun. Utilisez un repère documenté par son fabricant dans cette unité ; les indices ne sont pas convertis en ppb ou en µg/m³. À défaut de seuil, la mesure reste visible sans verdict COV.')}</p><p class="hint">${t('L’UBA rappelle que le total des COV ne permet pas à lui seul d’évaluer le risque sanitaire. Un seuil d’une substance ou un repère TVOC ne s’applique pas automatiquement à tous les capteurs grand public.')} <a href=${thresholdSources.tvoc} target="_blank" rel="noopener noreferrer">${t('Source : agence allemande de l’environnement, AIR')}</a>.</p>`}
  <p class="hint">${t('Vous pouvez laisser le seuil vide pour suivre la mesure sans l’interpréter.')}</p>
  ${this.evolutionNumber('voc_delay_minutes',t('Au-dessus du seuil depuis au moins (minutes)'),10,0,120,1)}${this.evolutionNumber('voc_pause_minutes',t('Pause après une aération (minutes)'),45,0,240,5)}
  ${helpTip(t('Comprendre ces délais'),html`<p>${t('Les COV varient beaucoup : cuisine, produit ménager, bougie, quelqu’un qui entre. Pour éviter un conseil qui va et vient, Confort juge la moyenne des 10 dernières minutes. Il conseille d’aérer quand elle reste au-dessus du seuil pendant le délai choisi (10 minutes par défaut), tout de suite si l’indice atteint le double du seuil. Le conseil cesse quand la moyenne repasse sous le seuil moins 20 % (120 pour un seuil de 150).')}</p><p>${t('Après une aération, Confort attend la pause choisie (45 minutes par défaut) avant de redemander : si la source est encore là, rouvrir ne sert à rien. Il redemande plus tôt si l’indice remonte nettement. Ce sont des choix pratiques Hestia, pas des normes.')}</p>`,t('Comprendre ce réglage'))}`:html`<p class="hint">${t('Choisissez votre capteur COV pour activer le suivi.')}</p>${availablePreset?defaultValue(t('Indice {n}',{n:availablePreset.value}),()=>{},html`<p class="hint">${t('Pourquoi 150 : pour la VINDSTYRKA IKEA identifiée, c’est l’exemple d’action de Sensirion. L’indice 100 correspond au niveau habituel appris par le capteur ; un indice plus haut signale davantage de COV par rapport à cet historique. Ce n’est ni une concentration, ni une limite sanitaire. L’adaptation du capteur peut ramener une pollution persistante vers 100.')} <a href=${thresholdSources.voc} target="_blank" rel="noopener noreferrer">${t('Source : Sensirion, fonctionnement du VOC Index')}</a>.</p>`,{applied:false,disabled:true,note:t('Pour le capteur reconnu : {name}',{name:availableVoc!.name})}):html`<p class="hint">${t('Valeur par défaut : selon le modèle et l’unité du capteur.')}</p>`}`}</div>`;
 if(key==='indoor_humidity')return html`<div class="sensor-settings"><h4>${t('Votre plage d’humidité')}</h4>${this.number('humidity_low',t('Humidité minimale (%)'),40)}${this.number('humidity_high',t('Humidité maximale (%)'),62)}${defaultValue(t('40 à 60 %'),()=>this.draft={...d,settings:{...d.settings,humidity_low:airReferenceDefaults.humidity_low,humidity_high:airReferenceDefaults.humidity_high}},html`<p class="hint">${t('L’ADEME conseille 40 à 60 % d’humidité. Vous pouvez adapter cette plage à la pièce.')} <a href=${thresholdSources.humidity} target="_blank" rel="noopener noreferrer">${t('Source : ADEME, Respirer un air sain chez soi')}</a>.</p>`,{applied:(d.settings.humidity_low??40)===40&&d.settings.humidity_high===60})}<p class="hint">${t('Jusqu’à 3 points hors de votre plage : légèrement humide ou sec. Jusqu’à 10 points : air humide ou sec. Au-delà : très humide ou très sec. Ces paliers Hestia graduent l’affichage, ce ne sont pas des seuils sanitaires. La durée et l’amélioration sont indiquées séparément ; aérer n’est conseillé que si cela aide.')}</p></div>`;
 if(key==='presence')return html`<div class="sensor-settings">${this.evolutionNumber('presence_delay_minutes',t('Délai avant de considérer la pièce vide (minutes)'),5,0,120,1)}${helpTip(t('Comprendre le délai de présence'),html`<p>${t('5 minutes est un choix pratique Hestia pour éviter les changements trop rapides. Le délai commence après une absence réellement signalée ; le silence d’un détecteur de mouvement ne suffit pas. Une pièce vide conserve son suivi et ses alertes.')}</p>`,t('Comprendre ce réglage'))}</div>`;
 if(key==='indoor_temperature')return html`<div class="sensor-settings"><h4>${t('Votre plage de confort')}</h4>${this.uses('versatile_thermostat')&&this.discovery?.candidates.heating?.find(c=>c.entity_id===d.sources.heating)?.thermostat&&d.thermostat_reference!==false?noteBox(t('Lu dans Versatile Thermostat'),t('Le minimum suit la consigne de votre Versatile Thermostat (onglet Chauffage). Celui saisi ici sert si le thermostat ne répond pas.')):nothing}${this.number('minimum',t('Minimum (°C)'),20,0.5)}${this.number('maximum',t('Maximum en hiver (°C)'),24,0.5)}${this.number('summer_maximum',t('Maximum en été (°C)'),26,0.5)}${defaultValue(t('20–24 °C l’hiver, 26 °C l’été'),()=>this.draft={...d,settings:{...d.settings,minimum:20,maximum:24,summer_maximum:26}},html`<p class="hint">${t('Les températures où vous vous sentez bien dans cette pièce. En dessous, Hestia parle de chauffage ; au-dessus, de rafraîchir. Le maximum passe doucement de la valeur d’hiver à celle d’été avec la saison. C’est un choix personnel, pas une limite de santé.')}</p>`,{applied:d.settings.minimum===20&&d.settings.maximum===24&&(d.settings.summer_maximum??26)===26})}</div>`;
 if(key==='heating'){const found=this.discovery?.candidates.heating?.find(c=>c.entity_id===d.sources.heating)?.thermostat,vt=this.uses('versatile_thermostat')?found:undefined,deg=(v:number|null|undefined)=>v==null?'—':String(v).replace('.',',')+' °C';
  return html`${found&&!vt?html`<div class="sensor-settings">${noteBox(t('Versatile Thermostat désactivé'),t('Coupé dans Réglages généraux, rubrique Extensions : ce chauffage est lu comme un thermostat ordinaire, sans ses consignes ni la raison d’un arrêt.'))}</div>`:nothing}${vt?html`<div class="sensor-settings">${noteBox(t('Versatile Thermostat reconnu'),t('Hestia lit ses consignes (confort {comfort}, éco {eco}, hors-gel {frost}), la raison d’un arrêt, sa pente de température, la présence et la fenêtre ouverte qu’il détecte. Il ne commande rien.',{comfort:deg(vt.comfort),eco:deg(vt.eco),frost:deg(vt.frost)}))}
   <label class="check"><input type="checkbox" .checked=${d.thermostat_reference!==false} @change=${(e:Event)=>this.draft={...d,thermostat_reference:(e.target as HTMLInputElement).checked}}>${t('Prendre la consigne du thermostat comme minimum de la pièce ({target} en ce moment)',{target:deg((vt.preset??'').includes('frost')?vt.comfort:vt.target??vt.comfort)})}</label>
   <p class="hint">${t('Le minimum suit ce que le thermostat vise : sa consigne confort ou éco selon le moment. Une pièce à 18 °C quand le thermostat vise 17 °C en éco n’est donc pas « trop fraîche ». Le hors-gel protège sans être un confort : c’est alors la température confort qui sert de minimum, sans conseil de rallumer. Arrêté par une fenêtre ou par son propre délestage, le thermostat repart seul : Hestia ne conseille pas de le rallumer.')}</p></div>`:nothing}
  <div class="sensor-settings"><h4>${t('Quand conseiller de rallumer')}</h4>${this.number('heating_tolerance',t('Tolérance sous le minimum (°C)'),1,0.5)}${defaultValue('1 °C',()=>this.draft={...d,settings:{...d.settings,heating_tolerance:1}},html`<p class="hint">${t('Sous le minimum de la pièce, Hestia le dit d’abord dans « À savoir ». « Rallumez le chauffage » n’apparaît que si la pièce reste plus bas que cette tolérance pendant 30 minutes, avec quelqu’un à la maison et le chauffage coupé, et qu’elle ne se réchauffe pas d’elle-même (soleil). 0 : dès le minimum.')}</p>`,{applied:(d.settings.heating_tolerance??1)===1})}</div>`;}
 return nothing;
 }
 /** Who moves the cover. Adaptive Cover Pro, CoverAutomatic and Cover Extender are recognised by themselves and each signal they give is shown;
     any other automation is told by hand. Full width, below the cover's own fields. */
 private coverDriver(id:string,cover?:string|null){
  const m=this.draft!.openings[id]??defaultOpening(),found=cover?this.discovery?.drivers?.[cover]:undefined,driver=found&&this.uses(found.driver??'adaptive_cover_pro')?found:undefined;
  const fields=html`${this.openingSource(id,'auto_entity','shutter_auto',t('Interrupteur qui active le pilotage automatique'))}${this.openingSource(id,'override_entity','shutter_override',t('Capteur « repris à la main »'))}`;
  if(!driver)return html`<div class="wide"><h4>${t('Qui pilote ce volet ?')}</h4>${found?html`<p class="hint">${t('{name} est désactivé dans Réglages généraux, rubrique Extensions : ses signaux ne sont pas lus.',{name:found.name})}</p>`:nothing}<p class="hint">${t('Si une automatisation ouvre et ferme ce volet, indiquez l’interrupteur qui l’active et, s’il existe, le capteur qui signale que vous avez repris la main. Rien n’est commandé : le conseil évite seulement ce que l’automatisme fait déjà.')}</p>${fields}</div>`;
  const sig=driver.signals,row=(label:string,s:{name:string;on:boolean}|null|undefined,on:string,off:string)=>s?html`<li><b>${label}</b> · ${s.on?on:off}<span class="hint"> (${s.name})</span></li>`:nothing;
  const names:Record<string,string>=Object.fromEntries(exposures.map(([k,l])=>[k,t(l)]));
  return html`<div class="wide driver"><h4>${t('Piloté par {name}',{name:driver.name})}</h4>
   <p class="hint">${t('Ces signaux sont lus tout seuls, rien à renseigner :')}</p>
   <ul>${row(t('Intégration'),sig?.enabled,t('activée'),t('désactivée : elle ne pilote rien'))}${row(t('Pilotage automatique'),sig?.auto,t('activé'),t('coupé'))}${row(t('Suivi du soleil'),sig?.tracking,t('activé'),t('coupé'))}${row(t('Mode climat'),sig?.climate,t('activé'),t('coupé : il ne ferme pas contre la chaleur'))}${row(t('Détection de la reprise à la main'),sig?.detection,t('activée'),t('coupée : un volet bougé à la main ne sera pas reconnu'))}${row(t('Repris à la main'),sig?.override,'oui','non')}${row(t('Soleil devant la fenêtre'),sig?.sun,'oui','non')}
    ${driver.azimuth!=null?html`<li><b>${t('Orientation de la fenêtre')}</b> · ${Math.round(driver.azimuth)}°${driver.exposure?` (${names[driver.exposure]})`:''}${driver.exposure&&m.exposure!==driver.exposure?html` <button class="link" @click=${()=>this.setOpening(id,{exposure:driver.exposure})}>${t('Utiliser pour l’exposition')}</button>`:nothing}</li>`:nothing}</ul>
   ${noteBox(t('Bon à savoir'),t('Ainsi, quand {name} pilote le volet, aucun geste ne vous est demandé ; s’il est coupé, vous êtes prévenu avant que le soleil n’arrive sur la fenêtre. Rien n’est commandé.',{name:driver.name}))}
   ${m.auto_entity||m.override_entity?html`<h4>${t('Signaux choisis à la main')}</h4><p class="hint">${t('Ils remplacent ceux de {name}. Retirez-les pour revenir à la détection.',{name:driver.name})}</p>${fields}`:nothing}</div>`;
 }
 private openingDetails(id:string){const m=this.draft!.openings[id]??defaultOpening(),found=m.shutter==='connected'&&m.cover_entity?this.discovery?.drivers?.[m.cover_entity]:undefined,known=found&&this.uses(found.driver??'adaptive_cover_pro')?found:undefined;return html`<div class="opening">
  <label>${t('Exposition')}<select @change=${(e:Event)=>this.setOpening(id,{exposure:(e.target as HTMLSelectElement).value||null})}><option value="" ?selected=${!m.exposure}>${t('Je ne sais pas')}</option>${exposures.map(([v,l])=>html`<option value=${v} ?selected=${m.exposure===v}>${t(l)}</option>`)}</select></label>
  <label>${t('Angle précis (facultatif)')}<input type="number" min="0" max="359" step="1" inputmode="numeric" placeholder=${m.exposure?String(({N:0,NE:45,E:90,SE:135,S:180,SO:225,O:270,NO:315} as Record<string,number>)[m.exposure]??''):t('0 à 359')} .value=${m.azimuth!=null?String(m.azimuth):''}
   @input=${(e:Event)=>{const raw=(e.target as HTMLInputElement).value;this.setOpening(id,{azimuth:raw===''?null:Number(raw)});}}></label>
  <p class="hint wide">${t('En degrés, si vous le connaissez : nord 0, est 90, sud 180, ouest 270. Il affine le calcul du soleil sur cette fenêtre.')}</p>
  <label>${t('Type')}<select @change=${(e:Event)=>this.setOpening(id,{kind:(e.target as HTMLSelectElement).value})}>${kinds.map(([v,l])=>html`<option value=${v} ?selected=${m.kind===v}>${t(l)}</option>`)}</select></label>
  <label class="check"><input type="checkbox" .checked=${m.sheltered} @change=${(e:Event)=>this.setOpening(id,{sheltered:(e.target as HTMLInputElement).checked})}>${t('Abrité par une avancée de toit ou un balcon')}</label>
  <label>${t('Volet')}<select @change=${(e:Event)=>{const shutter=(e.target as HTMLSelectElement).value as 'none'|'manual'|'connected';this.setOpening(id,{shutter,cover_entity:undefined,auto_entity:undefined,override_entity:undefined});}}>${[['none',t('Sans volet')],['manual',t('Volet manuel (bois, battant…)')],['connected',t('Volet connecté')]].map(([v,l])=>html`<option value=${v} ?selected=${(m.shutter??'none')===v}>${l}</option>`)}</select></label>
  ${m.shutter==='manual'?html`<p class="hint">${t('Position non mesurée. Les conseils resteront conditionnels : si votre volet est ouvert, vous pouvez le fermer.')}</p>`:nothing}
  ${m.shutter==='connected'?this.openingSource(id,'cover_entity','covers',t('Volet de cet ouvrant')):nothing}
  ${m.shutter==='connected'?this.coverDriver(id,m.cover_entity):nothing}
  <details class="group"><summary>${t('Dimensions et avancée de toit (pour l’ombre)')}</summary><p class="hint">${t('En mètres. L’ombre et la capacité d’aération seront estimées ; laissez vide ce que vous ne connaissez pas.')}</p>${known?.width!=null||known?.height!=null?html`<p class="hint"><b>${t('Repris de {name} :',{name:known.name})}</b> ${[known.width!=null?t('largeur {n} m',{n:num(known.width,2)}):'',known.height!=null?t('hauteur {n} m',{n:num(known.height,2)}):''].filter(Boolean).join(', ')}. ${t('Une valeur saisie ici le remplace.')}</p>`:nothing}${([['width',t('Largeur de l’ouvrant')],['height',t('Hauteur de l’ouvrant')],['overhang_depth',t('Profondeur de l’avancée')],['overhang_gap',t('Écart entre avancée et haut de l’ouvrant')]] as const).map(([key,label])=>html`<label>${label} (m)<input type="number" min="0" step="0.01" placeholder=${key==='width'&&known?.width!=null?String(known.width):key==='height'&&known?.height!=null?String(known.height):''} .value=${m[key]===undefined?'':String(m[key])} @input=${(e:Event)=>{const value=(e.target as HTMLInputElement).value;this.setOpening(id,{[key]:value===''?undefined:Number(value)});}}></label>`)}</details></div>`;}
 private field(key:string){
  const all=this.discovery?.candidates[key]??[],selected=this.selected(key),room=this.draft;
  const proposals=(this.exteriorDraft?all.filter(c=>c.outside):all.filter(c=>c.local)).filter(c=>!selected.includes(c.entity_id));
  const canAdd=multiple.has(key)||!selected.length;
  const where=this.exteriorDraft?t('dans vos pièces extérieures'):room?.area_id?t('dans la pièce {name}',{name:this.areaName(room.area_id)}):'';
  return frame(labels[key],html`
   ${key==='windows'&&selected.length?html`${helpTip(t('Comprendre l’exposition'),html`<p>${t('L’exposition est le côté vers lequel regarde l’ouvrant. Elle permet de savoir quand le soleil y entre.')}</p>`,t('Comprendre ce réglage'))}`:nothing}
   ${selected.map(id=>this.chosen(key,id,all,selected))}
   ${canAdd&&proposals.length?html`<p class="hint strong">${proposals.length===1?t('Trouvé {where}',{where}):(multiple.has(key)?t('Trouvés {where} : choisissez ceux qui conviennent',{where}):t('Trouvés {where} : choisissez celui qui convient',{where}))}</p><div class="candidates">${proposals.slice(0,5).map(c=>this.candidateRow(c,key))}</div>`:nothing}
   ${canAdd&&!proposals.length&&!selected.length?html`<p class="notice">${where?t('Rien trouvé {where}. Vous pouvez en choisir un ailleurs ci-dessous.',{where}):t('Pièce libre : choisissez le capteur ci-dessous.')}</p>`:nothing}
   ${canAdd?this.picker(key,all,selected):nothing}
   ${this.draft?this.sensorSettings(key):nothing}
   ${key!=='indoor_temperature'&&!selected.length?html`<button class="link" @click=${()=>{this.clear(key);this.saved=t('{name} : laissé vide pour l’instant.',{name:labels[key]});}}>${t('Continuer sans')}</button>`:nothing}
  `,{count:key==='indoor_temperature'?t('Obligatoire'):selected.length?t('Choisi'):t('Facultatif'),help:help[key],className:this.exteriorDraft?'nk-setting-section nk-plain':'nk-field-section nk-plain'});
 }
 private go(stage:number){this.stage=stage;if(this.workspaceKey)this.path(this.workspaceKey+'/'+(roomSections.find(x=>x.stage===stage)?.path??'recapitulatif'));this.error='';this.saved='';this.updateComplete.then(()=>{this.renderRoot.querySelector<HTMLElement>('h1')?.focus();});}
 /** What must be right before going on or saving; '' when it is. */
 private problem(all=false){const d=this.draft!,s=d.settings;
  if((all||this.stage===0)&&!d.sources.indoor_temperature)return t('Choisissez la température de la pièce pour continuer. C’est la seule mesure obligatoire.');
  const tol=s.heating_tolerance;if(tol!==undefined&&!(Number.isFinite(tol)&&tol>=0&&tol<=5))return t('La tolérance du chauffage va de 0 à 5 °C.');
  if(all||this.stage===4){if(!d.name.trim())return t('Donnez un nom à la pièce.');if(!Number.isFinite(s.minimum)||!Number.isFinite(s.maximum)||s.minimum>=s.maximum)return t('La température minimum doit être inférieure au maximum.');if(Number.isFinite(s.summer_maximum)&&s.summer_maximum<s.maximum)return t('Le maximum d’été ne peut pas être inférieur à celui d’hiver.');}
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
   this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path('');this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;
   if(wasRoom){this.preview=edited??this.snapshot.rooms.find(r=>!before.has(r.entry_id))?.entry_id;this.previewEdited=!!edited;if(this.preview)this.path('apercu/'+this.preview);}
   this.saved=wasRoom?'':t('L’extérieur est enregistré. Toutes vos pièces l’utilisent.');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private number(key:string,label:string,initial:number,step=1){const d=this.draft!;return html`<label>${label}<input type="number" step=${step} .value=${String(d.settings[key]??initial)} @input=${(e:Event)=>this.draft={...d,settings:{...d.settings,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`;}
 private floorName(){const d=this.draft!;const id=d.area_id?this.snapshot?.areas.find(a=>a.area_id===d.area_id)?.floor_id:d.floor_id;return this.snapshot?.floors?.find(f=>f.floor_id===id)?.name??t('Non renseigné');}
 private preferences(){const d=this.draft!,used=new Set(this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId).map(r=>r.config.area_id));
  return html`${frame(t('La pièce'),html`<label>${t('Nom')}<input type="text" maxlength="100" .value=${d.name} @input=${(e:Event)=>this.draft={...d,name:(e.target as HTMLInputElement).value}}></label>
   <label>${t('Pièce Home Assistant')}<select @change=${(e:Event)=>this.changeArea((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!d.area_id}>${t('Aucune (pièce libre)')}</option>${this.snapshot!.areas.filter(a=>!a.outdoor&&(!used.has(a.area_id)||a.area_id===d.area_id)).map(a=>html`<option value=${a.area_id} ?selected=${a.area_id===d.area_id}>${a.name}</option>`)}</select></label>
   ${d.area_id?html`<p>${t('Étage :')} <strong>${this.floorName()}</strong></p>${noteBox(t('Repris de Home Assistant'),t('Pour le modifier, changez l’étage de cette pièce dans Home Assistant.'))}`:html`<label>${t('Étage (facultatif)')}<select @change=${(e:Event)=>this.draft={...d,floor_id:(e.target as HTMLSelectElement).value||null}}><option value="" ?selected=${!this.snapshot?.floors?.some(f=>f.floor_id===d.floor_id)}>${t('Non renseigné')}</option>${(this.snapshot?.floors??[]).map(f=>html`<option value=${f.floor_id} ?selected=${d.floor_id===f.floor_id}>${f.name}</option>`)}</select></label>`}
   <p class="hint">${t('Le suivi fonctionne aussi de plain-pied, sans étage à configurer.')}</p>
   <p class="hint">${t('Rattacher la pièce permet de proposer ses capteurs. Vous pouvez toujours en choisir ailleurs.')}</p>`,{className:'nk-field-section nk-plain'})}
   ${this.sharedAir()}
   ${this.equipmentFrame()}
   ${frame(t('Réglages avancés'),html`
    <p class="hint">${t('Choix de fonctionnement Hestia, modifiables selon votre logement ; ces valeurs ne sont pas des normes sanitaires.')}</p>${this.number('gust_max',t('Rafales : ne rien laisser ouvert au-delà de (km/h)'),45)}${this.number('frost',t('Gel : pas d’ouverture prolongée en dessous de (°C)'),1,0.5)}${this.number('sun_facade',t('Soleil compté sur une fenêtre à partir de (W/m²)'),250,10)}${this.evolutionNumber('glazing_factor',t('Facteur estimé du vitrage (0 à 1)'),0.7,0,1,0.05)}${this.number('illuminance_low',t('Luminosité basse (lux)'),100)}${this.number('max_age_seconds',t('Ancienneté maximum des mesures (secondes)'),10800)}<p class="hint">${t('45 km/h de rafales et 1 °C : précautions Hestia pour les ouvrants, à adapter à leur exposition. 250 W/m² : à partir de ce soleil sur une fenêtre (moyenne des 15 dernières minutes), Confort conseille de le garder (pièce fraîche) ou de baisser le volet (pièce chaude) ; plus bas, il le signale plus souvent. 100 lux : repère de faible luminosité, sans déduction de position de volet. Facteur vitrage 0,7 : hypothèse de calcul de buée entre température extérieure (0) et intérieure (1), sans mesure du vitrage. 10 800 secondes : après 3 heures sans nouvelle mesure de l’appareil, une donnée numérique devient trop ancienne. Beaucoup de capteurs n’envoient une valeur que lorsqu’elle change ; une valeur stable reste donc valable. Cette expiration ne s’applique pas aux états de contacts.')}</p>`,{collapsible:true,open:false,count:changedAdvanced(d.settings)?t('{n} sur {total} modifiés',{n:changedAdvanced(d.settings),total:Object.keys(advancedDefaults).length}):t('Par défaut')})}`;}
 /** What the room holds that changes its air: a shower makes its peaks of humidity expected, never a mould risk. */
 private equipmentFrame(){const d=this.draft!,mine=d.equipment??[];
  const item=(key:string,label:string,hint:string)=>html`<label class="check"><input type="checkbox" .checked=${mine.includes(key)}
   @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.draft={...d,equipment:on?[...mine,key]:mine.filter(x=>x!==key)};}}>${label}</label><p class="hint">${hint}</p>`;
  return frame(t('Équipements'),html`<p class="hint">${t('Ce que la pièce contient et qui change son air, même sans capteur à part.')}</p>
   ${item('shower',t('Douche ou baignoire'),t('Dans la pièce ou dans une salle d’eau ouverte sur elle. La hausse d’humidité qui suit une douche est attendue : Hestia propose d’assécher, sans parler de moisissure, et nomme la douche quand l’humidité monte à son heure habituelle.'))}`,{className:'nk-field-section nk-plain'});}
 /** Rooms with no wall or door between them share one air: their windows are common, their advice never opposite. */
 private sharedAir(){const d=this.draft!,others=this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId);if(!others.length)return nothing;
  const mine=d.open_to??[],theirs=(r:{config:RoomConfig})=>!!this.entryId&&(r.config.open_to??[]).includes(this.entryId);
  return frame(t('Même air'),html`<p class="hint">${t('Cochez les pièces ouvertes sur celle-ci, sans mur ni porte entre elles (un salon ouvert sur sa cuisine). Leurs fenêtres comptent pour les deux, et le même air ne reçoit jamais deux gestes contraires.')}</p>
   ${others.map(r=>html`<label class="check"><input type="checkbox" .checked=${mine.includes(r.entry_id)||theirs(r)} ?disabled=${theirs(r)}
    @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.draft={...d,open_to:on?[...mine,r.entry_id]:mine.filter(x=>x!==r.entry_id)};}}>${r.title}${theirs(r)?' '+t('(déclaré depuis cette pièce)'):''}</label>`)}`,{className:'nk-field-section nk-plain'});}
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
 private wizard(){const d=this.draft!,section=roomSections.find(x=>x.stage===this.stage),at=roomOrder.indexOf(this.stage);
  return html`${pageHead({back:{label:t('Réglages généraux'),onClick:()=>this.cancel()},title:d.name?t('Configurer {name}',{name:d.name}):t('Configurer la pièce'),subtitle:`${d.area_id?t('Pièce Home Assistant : {name}',{name:this.areaName(d.area_id)}):t('Pièce libre')} · ${t('Les réglages de cette pièce')}`})}
  ${stepMenu(t('Réglages de la pièce'),menuSections.map(x=>({label:t(x.label),title:t(x.title),icon:x.icon,current:x.stage===this.stage,onClick:()=>this.go(x.stage)})),this.busy)}
  <div class="room-content-head"><h2>${section?t(section.title):t('Récapitulatif')}</h2></div>${this.intro(String(this.stage))}
  ${this.stage===0?[...indoor,'illuminance'].map(key=>this.field(key)):this.stage===1?html`${this.field('windows')}${this.draft&&!this.draft.windows.length?html`<label class="check"><input type="checkbox" .checked=${this.draft.windows_unmeasured===true} @change=${(e:Event)=>this.draft={...this.draft!,windows_unmeasured:(e.target as HTMLInputElement).checked}}>${t('Pas de contact de fenêtre ici, c’est voulu : ne plus le suggérer')}</label>`:nothing}`:this.stage===2?this.airPresence():this.stage===6?html`${this.field('presence')}${this.personsBlock()}`:this.stage===3?this.heatingStage():this.stage===4?this.preferences():this.stage===7?this.notifications():this.summary()}
  ${this.stage!==4&&this.stage!==5&&this.stage!==7&&!(this.stage===3&&d.heated===false)?html`<button class="link" ?disabled=${this.busy} @click=${()=>this.refreshCandidates()}>${t('Rechercher à nouveau les capteurs')}</button>`:nothing}${this.errorBlock()}
  ${stepFooter({previous:at>0?{label:t('Étape précédente'),onClick:()=>this.go(roomOrder[at-1]),disabled:this.busy}:undefined,
   next:this.stage!==5?{label:t('Continuer'),onClick:()=>this.next(),disabled:this.busy}:undefined,
   save:this.entryId?{label:t('Enregistrer'),onClick:()=>this.saveRoom(),disabled:this.busy}:this.stage===5?{label:t('Créer la pièce'),onClick:()=>void this.save(),disabled:this.busy}:undefined})}${this.removeBlock()}`;}
 /** The general settings: the rooms, Hestia's own bricks, then the other integrations Confort reads or could read. */
 private exterior(){const h=this.health,ext=h?.extensions??[],weather=ext.find(x=>x.key==='hestia_weather');
  return html`${pageHead({back:{label:t('Accueil Confort'),onClick:()=>this.cancel()},title:t('Extensions'),subtitle:t('Les autres briques Hestia, le dehors qu’elles donnent, et les intégrations que Confort lit.')})}
  <h2 class="ex-sec">${t('Extensions officielles Hestia')}</h2>
  ${this.extensionCard({...(weather??{key:'hestia_weather',name:t('Hestia Weather'),official:true,level:'none',role:'',use:t('Le dehors pour toutes les pièces : température, humidité, pluie, vent, soleil, saison, pollution, alertes et prévisions.'),without:'',url:'https://github.com/hestiaFB/hestia-weather-integration',text:'',rooms:[]}),
    state:this.weatherEntry?'linked':this.snapshot?.hestia_weather?.installed&&this.snapshot.hestia_weather.places.length?'found':'missing'},
    html`${this.exteriorSource()}${this.weatherEntry?this.exteriorRows():nothing}`)}
  ${this.weatherEntry?nothing:html`${this.exteriorRows()}${this.airBlock()}`}
  <h2 class="ex-sec">${t('Extensions tierces')}</h2><p class="hint">${t('Rangées par thème. Toutes facultatives : chacune affine les conseils là où elle sert.')}</p>
  ${h?themes.map(([label,keys])=>{const items=ext.filter(x=>!x.official&&(keys.length?keys.includes(x.key):!themes.some(([,k])=>k.includes(x.key))));
   return items.length?html`<h3 class="ex-theme">${t(label)}</h3>${items.map(x=>this.extensionCard(x))}`:nothing;}):html`<p class="muted" role="status">${t('Recherche des extensions…')}</p>`}
  ${detectedFrame({brick:t('Confort'),repository:'https://github.com/hestiaFB/hestia-comfort-integration',version:h?.version??'',rows:h?.others??[]})}
  ${this.confirmBlock()}${this.errorBlock()}${stepFooter({previous:{label:t('Annuler'),onClick:()=>this.cancel()},save:{label:t('Enregistrer'),onClick:()=>void this.save(),disabled:this.busy}})}`;}
 /** Réglages généraux: the rooms to change or add, and how to show their cards; nothing here waits for a save. */
 private settingsPage(){return html`${pageHead({back:{label:t('Accueil Confort'),onClick:()=>this.path('')},title:t('Réglages généraux'),subtitle:t('Vos pièces et les cartes.')})}
  ${this.roomsSettings()}
  ${this.householdSettings()}
  ${this.lightsCard()}
  ${frame(t('Les cartes'),html`<p class="hint">${t('Dans un tableau de bord :')} <strong>${t('Ajouter une carte')}</strong>${t(', puis')} <strong>${t('Hestia Confort')}</strong> ${t('pour une pièce (les pièces au même air n’en font qu’une), ou')} <strong>${t('Hestia Confort · logement')}</strong> ${t('pour la synthèse.')}</p>`)}
  ${this.errorBlock()}`;}
 /** The household: an allergy to pollens shortens the airings on days of high pollens. Off by default, saved at once. */
 private householdSettings(){const on=!!this.snapshot?.home.pollen_allergy;
  return frame(t('Le foyer'),html`<label class="check ex-switch"><input type="checkbox" role="switch" .checked=${on} ?disabled=${this.busy} @change=${(e:Event)=>void this.setPollenAllergy((e.target as HTMLInputElement).checked)}>${t('Allergie aux pollens')}</label>
   <p class="hint">${t('Les jours de pollens élevés, les aérations restent courtes, de préférence tôt le matin ou juste après la pluie.')}</p>
   <p class="hint">${t('Une aération utile pour l’humidité ou le CO₂ est toujours conseillée.')}</p>
   ${on&&!this.snapshot?.home.weather?html`<p class="hint">${t('Les pollens viennent de Hestia Weather : reliez-le dans Extensions.')}</p>`:nothing}`);}
 private async setPollenAllergy(allergy:boolean){this.busy=true;
  try{this.snapshot=await this.ws<Snapshot>({type:'hestia_comfort/set_pollen_allergy',allergy});this.revision=this.snapshot.revision;}
  catch(e){this.error=(e as {message?:string}).message??t('Le réglage n’a pas pu être enregistré.');}finally{this.busy=false;}}
 /** Every room, to change or to add; what needs setting is named on its line. */
 private roomsSettings(){const todo=new Map<string,number>();for(const l of this.health?.todo??[])if(l.target?.kind==='room')todo.set(l.target.entry_id,(todo.get(l.target.entry_id)??0)+1);
  return itemsFrame({title:t('Vos pièces'),hint:t('Capteurs, ouvrants, même air et réglages de chaque pièce.'),
   add:{label:this.adding?t('Fermer'):t('Ajouter une pièce'),onClick:()=>{this.adding=!this.adding;}},addContent:this.adding?html`<div class="ac-add">${this.addRoom()}</div>`:nothing,
   items:this.snapshot!.rooms.map(r=>{const n=todo.get(r.entry_id)??0,others=(this.volumeName(r.entry_id)??'').split(' · ').filter(x=>x&&x!==r.title);
    return {name:r.title,note:others.length?t('même air que {names}',{names:others.join(t(' et '))}):undefined,detail:coverage(r.config),pill:n?{text:n>1?t('{n} points à régler',{n}):t('1 point à régler'),level:'todo' as NkLevel}:undefined,
     edit:{label:t('Modifier'),onClick:()=>void this.openRoom(r.entry_id),disabled:this.busy}};})});}
 /** From the general settings to a room: their draft is kept for the way back. */
 private async openRoom(entry_id:string,section=''){const room=this.snapshot?.rooms.find(r=>r.entry_id===entry_id);if(!room)return;
  // They stay on screen while the room loads: no other page shows in between.
  this.remember();this.workspaceKey='';await this.editRoom(room);if(this.draft)this.exteriorDraft=undefined;else this.workspaceKey='reglages';const stage=roomSections.find(x=>x.path===section)?.stage;if(section&&stage!=null&&this.draft)this.go(stage);}
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
 private lightsCard(){const l=this.lights(),rooms=this.snapshot?.rooms??[],wled=this.wledOn();
  const name=(r?:LightRule|null)=>r?String(this.hass?.states?.[r.entity_id]?.attributes?.friendly_name??r.entity_id):t('aucune');
  const mode=(m:Lights['mode'])=>html`<label class="check"><input type="radio" name="li-mode" .checked=${l.mode===m} ?disabled=${this.busy} @change=${()=>void this.saveLights({...l,mode:m})}>${m==='home'?t('Tout le logement'):t('Pièce par pièce')}</label>`;
  return frame(t('Notifications lumineuses'),html`<p class="hint">${t('Une lumière prend la couleur du conseil : bleu tout va bien, vert à saisir, orange un geste.')}</p>
   <p class="hint">${wled?t('WLED est activé dans Extensions : ses bandeaux, leurs segments et leurs effets sont proposés.'):t('Une ampoule couleur suffit. Activez WLED dans Extensions pour ses bandeaux, leurs segments et leurs effets.')}</p>
   <div class="li-when" role="radiogroup" aria-label=${t('Qui pilote la lumière ?')}><p class="hint">${t('Qui pilote la lumière ?')}</p>${mode('home')}${mode('rooms')}</div>
   ${l.mode==='home'?lightEditor({hass:this.hass,wled,rule:l.home,busy:this.busy,info:this.infoOf(l.home),users:this.lightUsers(),follows:[{value:'home',label:t('Tout le logement')},...rooms.map(r=>({value:r.entry_id,label:r.title}))],change:rule=>void this.saveLights({...l,home:rule})})
    :html`<ul class="li-rooms">${rooms.map(r=>html`<li><span><strong>${r.title}</strong> · ${name(l.rooms[r.entry_id])}</span><button class="nk-edit" ?disabled=${this.busy} @click=${()=>void this.openRoom(r.entry_id,'notifications')}>${t('Régler')}</button></li>`)}</ul>
     <p class="hint">${t('Chaque pièce règle sa lumière dans son onglet Notifications.')}</p>`}
   ${noteBox(t('Enregistré tout de suite.'),nothing)}`,{className:'li-settings'});}
 /** To the general settings, the draft open here kept for later, as when opening another room. */
 private goSettings(){this.remember();this.workspaceKey='';this.draft=undefined;this.exteriorDraft=undefined;this.path('reglages');}
 /** WLED used: installed in Home Assistant and not turned off in Extensions. */
 private wledOn(){return this.uses('wled')&&Object.values(this.hass?.entities??{}).some(e=>e.platform==='wled');}
 /** A room's Notifications tab: its own light when the lights go room by room; the phone will come later. */
 private notifications(){const l=this.lights(),id=this.entryId;
  const light=l.mode==='home'?frame(t('Lumière'),html`${noteBox(t('Bon à savoir'),t('La lumière est réglée pour tout le logement, dans Réglages généraux.'))}<button class="nk-edit" ?disabled=${this.busy} @click=${()=>this.goSettings()}>${t('Ouvrir le réglage')}</button>`,{className:'nk-field-section nk-plain'})
   :!id?frame(t('Lumière'),html`<p class="hint">${t('Créez d’abord la pièce : sa lumière se règle ensuite ici.')}</p>`,{className:'nk-field-section nk-plain'})
   :lightEditor({hass:this.hass,wled:this.wledOn(),rule:l.rooms[id]??null,busy:this.busy,info:this.infoOf(l.rooms[id]??null),users:this.lightUsers(),taken:this.snapshot?.rooms.find(r=>r.entry_id!==id&&l.rooms[r.entry_id]&&l.rooms[r.entry_id].entity_id===l.rooms[id]?.entity_id)?.title,change:rule=>{const rooms={...l.rooms};if(rule)rooms[id]={...rule,follow:id};else delete rooms[id];void this.saveLights({...l,rooms});}});
  return html`${light}${frame(t('Sur le téléphone'),noteBox(t('Bientôt'),t('Prévenir sur le téléphone quand un geste est conseillé.')),{className:'nk-field-section nk-plain'})}`;}
 private extensionCard(x:Extension,body:unknown=nothing){const [said,cls]=extState[x.state],word=t(said);
  // Linking a heating or a cover is a room's choice: the first room opens on that step.
  const step=x.key==='versatile_thermostat'?'chauffage':['adaptive_cover_pro','cover_automatic','cover_extender'].includes(x.key)?'ouvertures':'';const first=this.snapshot?.rooms[0];
  // Hestia Weather's own choice already says how to install it.
  const off=x.state==='off',act=x.key==='wled'?(x.state==='missing'?html`<a class="ex-act" href="https://my.home-assistant.io/redirect/config_flow_start/?domain=wled" target="_blank" rel="noreferrer">${t('Ajouter dans Home Assistant')}</a>`:x.state==='found'?html`<button class="nk-edit" ?disabled=${this.busy} @click=${()=>this.goSettings()}>${t('Régler')}</button>`:nothing):x.state==='missing'&&!x.official?html`<a class="ex-act" href=${hacsUrl(x.url)} target="_blank" rel="noreferrer">${t('Installer avec HACS')}</a>`
   :x.state==='found'&&step&&first?html`<button class="nk-edit" ?disabled=${this.busy} @click=${()=>void this.openRoom(first.entry_id,step)}>${t('Lier')}</button>`:nothing;
  const detail=off?t('Confort ne s’en sert pas.')+' '+x.without:x.key==='wled'&&x.state!=='missing'?(x.state==='linked'?t('Notifications lumineuses : {names}',{names:x.rooms.join(', ')}):t('Trouvé dans Home Assistant. Choisissez un bandeau dans Réglages généraux → Notifications lumineuses.')):x.state==='linked'?(x.rooms.length?(x.rooms.length>1?t('{n} pièces : {names}',{n:x.rooms.length,names:x.rooms.join(', ')}):t('1 pièce : {names}',{names:x.rooms.join(', ')})):''):x.state==='found'?(step?t('Trouvé dans Home Assistant. Dans une pièce : Modifier → {step}.',{step:step==='chauffage'?t('Chauffage'):t('Ouvertures')}):t('Trouvée dans Home Assistant.')):x.without;
  return nkExtensionCard({icon:extIcon[x.key]??'settings',name:x.name,use:x.use,pill:{text:word,level:cls==='ok'?'ok':cls==='act'?'todo':'none'},detail:detail&&x.key!=='hestia_weather'?detail:'',action:act,todo:x.state==='found',
   switches:!x.official&&x.state!=='missing'?[{label:t('Utiliser {name} dans les conseils',{name:x.name}),checked:!off,disabled:this.busy,onChange:on=>void this.useExtension(x.key,on)}]:[],body});}
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
  // Inside the shared « Hestia » panel, its header and tabs replace this one.
  const header=this.hasAttribute('embedded')?nothing:html`<header><button aria-label=${t('Ouvrir le menu Home Assistant')} @click=${()=>this.menu()}><span class="menu-icon"></span></button><strong>${t('Hestia Confort')}</strong></header>`;
  return html`${header}<main class=${(this.page==='health'||this.page==='review')&&!editing&&!this.preview&&this.snapshot?.rooms.length?'wide':''}>${this.confirmDiscard?html`<section class="notice" role="alertdialog" aria-label=${t('Abandonner le brouillon')}><h2>${t('Quitter sans enregistrer ?')}</h2><p>${t('Vos choix de cette page seront perdus.')}</p><div class="actions"><button @click=${()=>this.confirmDiscard=false}>${t('Continuer la configuration')}</button><button @click=${()=>this.discard()}>${t('Quitter sans enregistrer')}</button></div></section>`:nothing}
   ${!editing?html`${this.errorBlock()}${this.error&&!this.snapshot?html`<button @click=${()=>this.load()}>${t('Réessayer')}</button>`:nothing}`:nothing}${this.saved?html`<p class="notice success" role="status">${this.saved}</p>`:nothing}${this.busy&&!this.snapshot?html`<p class="loading" role="status">${t('Chargement de votre logement…')}</p>`:nothing}
   ${this.snapshot?(this.exteriorDraft?this.exterior():this.draft?this.wizard():this.preview?this.previewScreen():this.opening?html`<p class="muted" role="status">${t('Chargement…')}</p>`:this.page==='settings'?this.settingsPage():this.page==='review'?html`<hestia-comfort-review .hass=${this.hass} .room=${this.reviewRoom} @review-navigate=${(e:CustomEvent<string>)=>this.path(e.detail)}></hestia-comfort-review>`:this.page==='health'&&this.snapshot.rooms.length?this.healthScreen():this.home()):nothing}${this.busy&&this.snapshot?html`<p class="busy" role="status">${t('Un instant…')}</p>`:nothing}</main>`;
 }
}
