import {html,nothing} from 'lit';
import {frame,noteBox,t,fr} from './socle/ui';
import type {Hass} from './model';

/** One state of the banner and what the light does then; a WLED effect's speed too. */
export interface LightLook {colour:string|null;effect:string;brightness:number;speed?:Speed}
export type Speed='slow'|'normal'|'fast';
/** A light that shows the advice: which one, what it follows, when it may act, and its looks. */
export interface LightRule {entity_id:string;follow:string;wake:boolean;night:boolean;presence:boolean;states:Record<string,LightLook>}
/** « Lumières »: one light for the whole home, or one per room (in its Notifications tab). */
export interface Lights {mode:'home'|'rooms';home:LightRule|null;rooms:Record<string,LightRule>}
/** What Home Assistant says of a light (hestia_comfort/light_info): a WLED segment's LEDs, its strip's segments and who drives them. */
export interface LightInfo {wled:boolean;leds:number|null;segments:{entity_id:string;segment:number;leds:number|null;speed:string|null;automations:string[]}[]}

// The banner's states, with the card's colours (hestia-charte.css): blue all is well, green a benefit, orange a gesture.
export const lightStates:{key:string;label:string;colour:string;text:string}[]=[
 {key:'calm',label:fr('Tout va bien'),colour:'#aad6e5',text:'#0c3f52'},
 {key:'benefit',label:fr('À saisir'),colour:'#a5d6ae',text:'#1f4a27'},
 {key:'action',label:fr('Geste conseillé'),colour:'#f1b277',text:'#5a3108'},
 {key:'airing',label:fr('Aération en cours'),colour:'#aad6e5',text:'#0c3f52'},
 {key:'urgent',label:fr('Attention'),colour:'#e8857f',text:'#5c1714'}];
const defaults:Record<string,LightLook>={calm:{colour:'#aad6e5',effect:'keep',brightness:40},benefit:{colour:'#a5d6ae',effect:'solid',brightness:50},
 action:{colour:'#f1b277',effect:'solid',brightness:70},airing:{colour:'#aad6e5',effect:'solid',brightness:60},urgent:{colour:'#e8857f',effect:'flash',brightness:100}};
// A WLED light is a status light: each state has its own motion (as the approved mockup), when the strip has the effect.
const wledDefaults:Record<string,LightLook>={calm:{colour:'#aad6e5',effect:'solid',brightness:40,speed:'normal'},benefit:{colour:'#a5d6ae',effect:'Breathe',brightness:50,speed:'slow'},
 action:{colour:'#f1b277',effect:'Heartbeat',brightness:70,speed:'normal'},airing:{colour:'#aad6e5',effect:'Breathe',brightness:60,speed:'normal'},urgent:{colour:'#e8857f',effect:'Blink',brightness:100,speed:'fast'}};
// Hestia-FB's own effects; then the light's, in Hestia-FB's words when WLED has them.
const ownEffects:[string,string][]=[['keep',fr('Ne rien changer')],['off',fr('Éteindre')],['solid',fr('Fixe')],['flash',fr('Clignoter')]];
// WLED's effects worth a status light: those a single LED shows (WLED's fxdata flag « 0 »), then a chase along a strip.
const wledMain:[string,string][]=[['Breathe',fr('Respire')],['Heartbeat',fr('Battement de cœur')],['Blink',fr('Clignote')],['Fade',fr('Fondu')],['Candle',fr('Bougie')]];
const wledStrip:[string,string][]=[['Chase',fr('Chenillard')]];
const wledOneLed=['Random Colors','Colorloop','Strobe','Strobe Rainbow','Strobe Mega','Blink Rainbow','Fire Flicker','TV Simulator'];
const speeds:[Speed,string][]=[['slow',fr('Lent')],['normal',fr('Normal')],['fast',fr('Rapide')]];

export const noLights=():Lights=>({mode:'home',home:null,rooms:{}});
const effectsOf=(hass:Hass|undefined,id:string)=>(hass?.states?.[id]?.attributes?.effect_list as string[]|undefined)??[];
const isWled=(hass:Hass|undefined,id:string)=>hass?.entities?.[id]?.platform==='wled';
export function newRule(entity_id:string,follow='home',hass?:Hass):LightRule{
 // A WLED light takes moving looks; an effect the strip does not have falls back to Hestia-FB's own.
 const list=effectsOf(hass,entity_id),states=isWled(hass,entity_id)?Object.fromEntries(Object.entries(wledDefaults).map(([k,l])=>[k,list.includes(l.effect)||l.effect==='solid'?{...l}:{...defaults[k],speed:'normal' as Speed}])):structuredClone(defaults);
 // A bulb that can neither flash nor blink shows « Attention » by its colour.
 const a=hass?.states?.[entity_id]?.attributes??{};if(!isWled(hass,entity_id)&&!(Number(a.supported_features??0)&8)&&!named(a.effect_list,'blink'))states.urgent={...states.urgent,effect:'solid'};
 return {entity_id,follow,wake:false,night:true,presence:true,states};}
export function look(rule:LightRule,key:string):LightLook{return rule.states[key]??defaults[key];}
const named=(effects:unknown,name:string)=>(Array.isArray(effects)?effects as string[]:[]).find(e=>String(e).toLowerCase()===name);
const moves=(effect:string)=>!['keep','off','solid','flash'].includes(effect);

/** The lights that can show a colour; a plain on/off or dimmable bulb cannot. */
export function colourLights(hass?:Hass,wled=true){const states=hass?.states??{};
 return Object.keys(states).filter(id=>id.startsWith('light.')&&((states[id].attributes?.supported_color_modes as string[]|undefined)??[]).some(m=>!['onoff','brightness','white'].includes(m)))
  .filter(id=>wled||hass?.entities?.[id]?.platform!=='wled').map(id=>{const e=hass?.entities?.[id],device=e?.device_id?hass?.devices?.[e.device_id]:undefined;
   return {id,name:String(states[id].attributes?.friendly_name??id),wled:e?.platform==='wled',strip:e?.platform==='wled'?String(device?.name_by_user??device?.name??'WLED'):''};}).sort((a,b)=>a.name.localeCompare(b.name));}
/** A WLED strip cut into segments: each segment is a light of its own, able to show another room. */
export function segmentsOf(hass:Hass|undefined,strip:string){return colourLights(hass,true).filter(l=>l.wled&&l.strip===strip);}

/** What the light is, for its settings: a WLED segment of one LED, a WLED strip, or a bulb. */
type Kind='wled1'|'strip'|'bulb';
function kindOf(hass:Hass|undefined,id:string,info?:LightInfo):Kind{return info?.wled||isWled(hass,id)?(info?.leds===1?'wled1':'strip'):'bulb';}
/** The effects offered: the ones the light can show, in Hestia-FB's words first; the others under « Plus d'effets ». */
function menuOf(kind:Kind,list:string[],canFlash:boolean,current:string[]){
 const has=(v:string)=>list.includes(v);
 const main:[string,string][]=kind==='bulb'?ownEffects.filter(([v])=>v!=='flash'||canFlash):[...ownEffects.filter(([v])=>v!=='flash'),...[...wledMain,...(kind==='strip'?wledStrip:[])].filter(([v])=>has(v))];
 const shown=new Set(main.map(([v])=>v));
 const more=kind==='wled1'?wledOneLed.filter(has):list.filter(v=>!shown.has(v)&&v!=='Solid');
 // A look saved before (a flash on WLED, an effect since removed) stays readable.
 const kept=current.filter(v=>!shown.has(v)&&!more.includes(v));
 return {main,more:[...kept,...more]};}
export function effectName(effect:string){const found=[...ownEffects,...wledMain,...wledStrip].find(([v])=>v===effect);return found?t(found[1]):effect;}

function rgb(hex:string){return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));}
const speedValue:Record<Speed,number>={slow:60,normal:128,fast:220};
/** Shows a state's look on the light at once, from the hub: the « Essayer » button. Fitted as the driver does
 * (engine/light_plan.py fit and speed): no flash → its « Blink » effect; « Fixe » stops an effect already running; a WLED
 * effect takes its speed on the segment's own « Vitesse ». */
export function tryLook(hass:Hass|undefined,rule:LightRule,key:string,info?:LightInfo){const l=look(rule,key);if(!hass?.callService||l.effect==='keep')return;
 if(l.effect==='off'){void hass.callService('light','turn_off',{entity_id:rule.entity_id});return;}
 const data:Record<string,unknown>={entity_id:rule.entity_id,brightness_pct:l.brightness,...(l.colour?{rgb_color:rgb(l.colour)}:{})};
 const a=hass.states?.[rule.entity_id]?.attributes??{},canFlash=(Number(a.supported_features??0)&8)!==0;
 if(l.effect==='flash'){const blink=named(a.effect_list,'blink');if(canFlash)data.flash='long';else if(blink)data.effect=blink;}
 else if(l.effect!=='solid')data.effect=l.effect;else{const solid=named(a.effect_list,'solid');if(solid)data.effect=solid;}
 const speed=info?.segments.find(s=>s.entity_id===rule.entity_id)?.speed;
 if(speed&&moves(l.effect))void hass.callService('number','set_value',{entity_id:speed,value:speedValue[l.speed??'normal']});
 void hass.callService('light','turn_on',data);}

// How an effect moves in the preview; a light's own effect is drawn by its name (WLED: Breathe, Blink, Rainbow…).
function motion(effect:string){const e=effect.toLowerCase();
 return e==='keep'||e==='off'?e:e==='flash'||/blink|strobe/.test(e)?'blink':/heart/.test(e)?'heart':/breath/.test(e)?'breathe':/fade/.test(e)?'fade':/candle|fire|flicker|tv/.test(e)?'candle'
  :/rainbow|colorloop|palette|random/.test(e)?'rainbow':/chase|running|scan|theater|wave|twinkle/.test(e)?'chase':'';}
/** The look as the light will show it: one LED for a segment of one, the strip's LEDs, or a bulb. */
function lookPreview(kind:Kind,leds:number|null,l:LightLook,colour:string){
 const m=motion(l.effect),n=kind==='bulb'?1:kind==='wled1'?1:Math.max(3,Math.min(leds??7,12)),d={slow:2.6,normal:1.5,fast:.7}[l.speed??'normal'];
 const light=(i:number)=>html`<i class=${'li-px '+m} style=${`--li-c:${colour};--li-b:${.55+l.brightness/220};--li-d:${d}s;--li-i:${i/n}`}></i>`;
 return html`<span class=${'li-pv '+(kind==='bulb'?'bulb':kind==='wled1'?'one':'many')} role="img" aria-label=${effectName(l.effect)}>${Array.from({length:n},(_,i)=>light(i))}</span>`;}
/** The strip's segments as a board: who shows on each (a room, an automation) and the warning before taking one. */
function ledBoard(o:{hass?:Hass;info:LightInfo;rule:LightRule;users:Record<string,string>;busy:boolean;pick:(id:string)=>void}){
 const own=o.info.segments.find(s=>s.entity_id===o.rule.entity_id);
 return html`<div class="li-board"><h4>${t('Votre bandeau WLED')}</h4><div class="li-slots" role="radiogroup" aria-label=${t('Segment')}>${o.info.segments.map(s=>{
   const st=o.hass?.states?.[s.entity_id],c=st?.state==='on'&&Array.isArray(st.attributes?.rgb_color)?`rgb(${(st.attributes.rgb_color as number[]).join(',')})`:'';
   const who=o.users[s.entity_id]??(s.automations.length?s.automations.join(', '):t('Libre'));
   return html`<button class=${'li-slot'+(s.entity_id===o.rule.entity_id?' sel':'')} role="radio" aria-checked=${s.entity_id===o.rule.entity_id} ?disabled=${o.busy} @click=${()=>s.entity_id!==o.rule.entity_id&&o.pick(s.entity_id)}>
    <span class="n">${t('Segment {n}',{n:s.segment})}${s.leds?html` · ${s.leds===1?t('1 LED'):t('{n} LED',{n:s.leds})}`:nothing}</span><span class=${'li-led'+(c?'':' free')} style=${c?`background:${c}`:''}></span><span class="who">${who}</span></button>`;})}</div>
  ${own?.automations.length?html`<p class="warning hint">${t('Votre automatisation « {name} » pilote déjà ce segment. Choisissez un segment libre, ou laissez Hestia-FB le prendre seulement pour un geste ou une alerte.',{name:own.automations.join(' », « ')})}</p>`:nothing}</div>`;}
/** What the chosen light can do, said once above its settings. */
function kindHint(kind:Kind,leds:number|null,own:boolean){
 return kind==='wled1'?t('Une seule LED : seuls les effets visibles sur une LED sont proposés. Vitesse réglable.')
  :kind==='strip'?(leds?t('Bandeau de {n} LED : les effets qui bougent le long du bandeau s’ajoutent (chenillard…). Vitesse réglable.',{n:leds}):t('Bandeau WLED : ses effets sont proposés pour chaque état. Vitesse réglable.'))
  :own?t('Ampoule couleur avec ses propres effets : ils sont proposés tels quels.'):t('Ampoule couleur : une couleur et une luminosité. Elle ne sait ni clignoter ni faire d’effet : Hestia-FB ne propose que ce qu’elle sait faire.');}
/** The light's settings, as in the approved mockup; every change is handed back to be saved at once. */
export function lightEditor(o:{hass?:Hass;wled:boolean;rule:LightRule|null;taken?:string;follows?:{value:string;label:string}[];busy:boolean;info?:LightInfo;users?:Record<string,string>;change:(rule:LightRule|null)=>void}){
 const lights=colourLights(o.hass,o.wled),rule=o.rule,current=rule?lights.find(l=>l.id===rule.entity_id):undefined;
 const list=rule?effectsOf(o.hass,rule.entity_id):[],a=rule?o.hass?.states?.[rule.entity_id]?.attributes??{}:{},canFlash=(Number(a.supported_features??0)&8)!==0;
 const kind=rule?kindOf(o.hass,rule.entity_id,o.info):'bulb',leds=o.info?.leds??null,wled=kind!=='bulb';
 const set=(change:Partial<LightRule>)=>rule&&o.change({...rule,...change});
 const setLook=(key:string,change:Partial<LightLook>)=>rule&&o.change({...rule,states:{...rule.states,[key]:{...look(rule,key),...change}}});
 const pickLight=(id:string)=>o.change(id?(rule?{...rule,entity_id:id}:newRule(id,o.follows?.[0]?.value??'home',o.hass)):null);
 const pick=html`<label class="zone">${t('Lumière à piloter')}<select ?disabled=${o.busy} @change=${(e:Event)=>pickLight((e.target as HTMLSelectElement).value)}>
  <option value="" ?selected=${!rule}>${t('Aucune')}</option>${lights.filter(l=>!l.wled).map(l=>html`<option value=${l.id} ?selected=${l.id===rule?.entity_id}>${l.name}</option>`)}
  ${[...new Set(lights.filter(l=>l.wled).map(l=>l.strip))].map(strip=>html`<optgroup label=${'WLED · '+strip}>${lights.filter(l=>l.wled&&l.strip===strip).map(l=>html`<option value=${l.id} ?selected=${l.id===rule?.entity_id}>${l.name}</option>`)}</optgroup>`)}
  ${rule&&!current?html`<option value=${rule.entity_id} selected>${t('Introuvable · choisissez-en une autre')}</option>`:nothing}</select></label>`;
 if(!lights.length&&!rule)return frame(t('Lumière'),html`<p class="hint">${t('Aucune lumière couleur trouvée dans Home Assistant. Un bandeau WLED ou une ampoule couleur conviennent.')}</p>`,{className:'nk-field-section nk-plain'});
 const menu=menuOf(kind,list,canFlash,rule?lightStates.map(s=>look(rule,s.key).effect):[]);
 return frame(t('Lumière'),html`<div class="li-host">${noteBox(t('Bon à savoir'),t('Hestia-FB ne la commande que dans les conditions choisies ici.'))}
  <div class="li-grid">${pick}${rule&&o.follows?.length?html`<label class="zone">${t('Suit le conseil de')}<select ?disabled=${o.busy} @change=${(e:Event)=>set({follow:(e.target as HTMLSelectElement).value})}>
   ${o.follows.map(f=>html`<option value=${f.value} ?selected=${f.value===rule.follow}>${f.label}</option>`)}</select></label>`:nothing}</div>
  ${rule?html`<p class="hint">${wled?html`<em class="ex-badge benefit">WLED</em> `:nothing}${kindHint(kind,leds,canFlash||list.length>0)}</p>`:nothing}
  ${rule&&o.info&&o.info.segments.length>1?ledBoard({hass:o.hass,info:o.info,rule,users:o.users??{},busy:o.busy,pick:pickLight}):nothing}
  ${o.taken?html`<p class="warning hint">${t('Cette lumière montre déjà {room}. Choisissez un autre segment ou une autre lumière.',{room:o.taken})}</p>`:nothing}
  ${rule?html`<div class="li-when" role="radiogroup" aria-label=${t('Quand agir')}>
    <label class="check"><input type="radio" name="li-wake" .checked=${!rule.wake} ?disabled=${o.busy} @change=${()=>set({wake:false})}>${t('Seulement quand elle est déjà allumée')}</label>
    <label class="check"><input type="radio" name="li-wake" .checked=${rule.wake} ?disabled=${o.busy} @change=${()=>set({wake:true})}>${t('L’allumer pour un geste ou une alerte, puis la rendre comme avant')}</label>
    <label class="check"><input type="checkbox" .checked=${rule.night} ?disabled=${o.busy} @change=${(e:Event)=>set({night:(e.target as HTMLInputElement).checked})}>${t('Jamais la nuit (de 22 h à 7 h)')}</label>
    <label class="check"><input type="checkbox" .checked=${rule.presence} ?disabled=${o.busy} @change=${(e:Event)=>set({presence:(e.target as HTMLInputElement).checked})}>${t('Seulement si quelqu’un est à la maison')}</label></div>
   <div class="li-box"><div class="li-head"><h4>${wled?t('Pour chaque état · effet, vitesse et aperçu'):t('Pour chaque état · couleur et luminosité')}</h4><button class="nk-edit" ?disabled=${o.busy} @click=${()=>set({states:newRule(rule.entity_id,rule.follow,o.hass).states})}>${t('Couleurs Hestia-FB')}</button></div>
   <div class=${'li-table'+(wled?' wled':'')}><div class="li-row li-cols" aria-hidden="true"><span>${t('État')}</span><span>${t('Couleur')}</span><span>${t('Effet')}</span>${wled?html`<span>${t('Vitesse')}</span>`:nothing}<span>${t('Luminosité')}</span><span>${t('Aperçu')}</span><span></span></div>
   ${lightStates.map(s=>{const l=look(rule,s.key),plain=l.effect==='keep'||l.effect==='off',colour=l.colour??s.colour;
    return html`<div class="li-row"><span class="li-pill" style="background:${s.colour};color:${s.text}">${t(s.label)}</span>
     <label class="li-swatch ${plain?'plain':''}" style="--li-c:${colour}"><input type="color" aria-label=${t('Couleur : {state}',{state:t(s.label)})} .value=${colour} ?disabled=${o.busy||plain} @change=${(e:Event)=>setLook(s.key,{colour:(e.target as HTMLInputElement).value})}></label>
     <select aria-label=${t('Effet : {state}',{state:t(s.label)})} ?disabled=${o.busy} @change=${(e:Event)=>setLook(s.key,{effect:(e.target as HTMLSelectElement).value})}>
      ${menu.main.map(([v,label])=>html`<option value=${v} ?selected=${v===l.effect}>${t(label)}</option>`)}
      ${menu.more.length?html`<optgroup label=${wled?t('Plus d’effets'):t('Effets de la lumière')}>${menu.more.map(v=>html`<option value=${v} ?selected=${v===l.effect}>${effectName(v)}</option>`)}</optgroup>`:nothing}</select>
     ${wled?html`<span class="li-speed" role="radiogroup" aria-label=${t('Vitesse : {state}',{state:t(s.label)})}>${moves(l.effect)?speeds.map(([v,label])=>html`<button role="radio" aria-checked=${(l.speed??'normal')===v} class=${(l.speed??'normal')===v?'on':''} ?disabled=${o.busy} @click=${()=>setLook(s.key,{speed:v})}>${t(label)}</button>`):html`<span class="li-none">—</span>`}</span>`:nothing}
     <label class="li-bright"><input type="range" min="5" max="100" step="5" .value=${String(l.brightness)} aria-label=${t('Luminosité : {state}',{state:t(s.label)})} ?disabled=${o.busy||plain}
      @input=${(e:Event)=>{const b=Number((e.target as HTMLInputElement).value);((e.target as HTMLElement).nextElementSibling as HTMLElement).textContent=b+' %';}}
      @change=${(e:Event)=>setLook(s.key,{brightness:Number((e.target as HTMLInputElement).value)})}><span>${plain?'—':l.brightness+' %'}</span></label>
     ${lookPreview(kind,leds,l,colour)}
     <button class="li-try" ?disabled=${o.busy||l.effect==='keep'} aria-label=${t('Essayer sur la lumière')} title=${t('Essayer sur la lumière')} @click=${()=>tryLook(o.hass,rule,s.key,o.info)}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M8 5v14l11-7Z"></path></svg></button></div>`;})}</div></div>
   <p class="hint">${kind==='wled1'?t('L’aperçu est une seule LED, comme la vraie. « Plus d’effets » garde les autres effets visibles sur une LED.')+' ':kind==='bulb'?t('Une ampoule montre l’état par sa couleur.')+' ':''}${t('« Essayer » montre l’état sur la lumière tout de suite. Ensuite, Hestia-FB la change quand le conseil change, et la rend comme avant quand tout va bien.')}</p>`:nothing}</div>`,{className:'nk-field-section nk-plain'});}
