import {html,nothing} from 'lit';
import {frame,defaultValue,noteBox,pageHead,t,fr,type NkAction} from './socle/ui';

/** The household's settings (« Réglages du foyer », niak-comfort/docs/REGLAGES-3.md § 4.3): only what the person set
 *  is kept, a missing key takes its default. The same keys as the advisor's `Habits` (advisor/household.py). */
export type Foyer=Partial<{sommeil:{debut:string;fin:string};ouvrir_la_nuit:boolean;tolerance:number;aeration_max_min:number;
 plus_tard_max_min:number;appareils_max_min:number;cette_nuit_avant_h:number;buee_avant_h:number;hors_gel:number;
 pas_maintenant_min:number;poele_tient_h:number;depassement:number;depassement_min:number}>;
export const FOYER_DEFAULTS={sommeil:{debut:'22:00',fin:'07:00'},ouvrir_la_nuit:false,tolerance:1,aeration_max_min:30,plus_tard_max_min:120,
 appareils_max_min:60,cette_nuit_avant_h:4,buee_avant_h:5,hors_gel:7,pas_maintenant_min:60,poele_tient_h:3,depassement:1,depassement_min:30};
// « Combien de conseils »: five notches, the middle one the default (foyer.py TOLERANCES).
export const TOLERANCES=[0.5,0.75,1,1.5,2];
const toleranceWords=[fr('Beaucoup plus : même les petits gains sont dits.'),fr('Un peu plus de conseils.'),fr('Normal : les gestes qui changent quelque chose qu’on sent.'),fr('Un peu moins de conseils.'),fr('Beaucoup moins : seulement les gestes les plus nets.')];
export const toleranceName=(v:number)=>[t('Beaucoup plus'),t('Un peu plus'),t('Normal'),t('Un peu moins'),t('Beaucoup moins')][Math.max(0,TOLERANCES.indexOf(v))];

export function duration(minutes:number){const h=Math.floor(minutes/60),m=minutes%60;return h?(m?t('{h} h {m}',{h,m:String(m).padStart(2,'0')}):t('{h} h',{h})):t('{n} min',{n:minutes});}
const hours=(n:number)=>n===1?t('1 h avant le coucher'):t('{n} h avant le coucher',{n:String(n).replace('.',',')});
const degrees=(n:number)=>String(n).replace('.',',')+' °C';

interface Options {foyer:Foyer;busy:boolean;stove:boolean;allergy:boolean;weatherLinked:boolean;back:NkAction;
 change:(next:Foyer)=>void;setAllergy:(on:boolean)=>void}

/** The page: one frame per subject; each change is saved at once. */
export function foyerPage(o:Options){
 const f={...FOYER_DEFAULTS,...o.foyer},set=(key:keyof Foyer,value:unknown)=>{const next={...o.foyer,[key]:value} as Foyer;if(JSON.stringify(value)===JSON.stringify(FOYER_DEFAULTS[key as keyof typeof FOYER_DEFAULTS]))delete next[key];o.change(next);};
 const reset=(key:keyof Foyer)=>()=>{const next={...o.foyer};delete next[key];o.change(next);};
 const choice=(key:keyof Foyer,label:string,values:number[],word:(n:number)=>string)=>html`<label>${label}<select ?disabled=${o.busy} @change=${(e:Event)=>set(key,Number((e.target as HTMLSelectElement).value))}>${values.map(v=>html`<option value=${v} ?selected=${(f as Record<string,unknown>)[key]===v}>${word(v)}</option>`)}</select></label>`;
 const why=(text:unknown)=>html`<p class="why">${text}</p>`;
 const dflt=(key:keyof Foyer,shown:string,explanation:string)=>defaultValue(shown,reset(key),html`<p>${explanation}</p>`,{applied:!(key in o.foyer),disabled:o.busy});
 const tol=Math.max(0,TOLERANCES.indexOf(f.tolerance));
 return html`${pageHead({back:o.back,title:t('Réglages du foyer'),subtitle:t('Votre façon de vivre, pour toute la maison. Une pièce qui vit autrement se règle dans son onglet « La pièce ».')})}
 ${noteBox(t('Enregistré tout de suite.'),nothing)}
 ${frame(t('Sommeil'),html`<div class="sensor-settings">
   <label>${t('Coucher')}<input type="time" .value=${f.sommeil.debut} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)set('sommeil',{debut:v,fin:f.sommeil.fin});}}></label>
   <label>${t('Lever')}<input type="time" .value=${f.sommeil.fin} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)set('sommeil',{debut:f.sommeil.debut,fin:v});}}></label>
   ${why(t('La nuit, Hestia ne propose que les gestes importants. L’alarme en mode nuit compte aussi comme la nuit.'))}
   ${dflt('sommeil','22:00 – 07:00',t('Des heures ordinaires : changez-les si votre foyer se couche ou se lève autrement.'))}</div>
  <label class="check ex-switch"><input type="checkbox" role="switch" .checked=${f.ouvrir_la_nuit} ?disabled=${o.busy} @change=${(e:Event)=>set('ouvrir_la_nuit',(e.target as HTMLInputElement).checked)}>${t('Ouvrir une fenêtre la nuit')}</label>
  ${why(f.ouvrir_la_nuit?t('Oui : Hestia peut conseiller d’ouvrir pendant le sommeil, quand ça vaut la peine de se lever.'):t('Non : aucune ouverture conseillée pendant le sommeil. « Refermez », la VMC et le purificateur restent.'))}`,{className:'nk-field-section nk-plain'})}
 ${frame(t('Combien de conseils'),html`<label class="fy-slider">${t('Plus de conseils, ou moins')}<input type="range" min="0" max="4" step="1" .value=${String(tol)} ?disabled=${o.busy} @change=${(e:Event)=>set('tolerance',TOLERANCES[Number((e.target as HTMLInputElement).value)])}></label>
  <div class="fy-ticks"><span>${t('Plus')}</span><span>${t('Normal')}</span><span>${t('Moins')}</span></div>
  <p><strong>${t(toleranceWords[tol])}</strong></p>
  ${why(t('L’écart qu’un geste doit apporter pour être conseillé. La sécurité passe toujours : « Fermez, il pleut » reste.'))}
  ${dflt('tolerance',t('Normal'),t('Au milieu : un geste est conseillé quand il change quelque chose qu’on sent, par exemple 1,5 °C pendant deux heures.'))}`,{className:'nk-field-section nk-plain'})}
 ${frame(t('Gestes proposés'),html`<p class="hint">${t('Hestia calcule la durée de chaque geste, de 5 en 5 minutes, avec ce qu’il a appris de la pièce. Vous fixez seulement les limites.')}</p>
  <div class="sensor-settings">${choice('aeration_max_min',t('Aération la plus longue'),[10,15,20,30,45,60],duration)}
   ${why(t('« Aérez 15 min », juste ce qu’il faut. Si ça ne suffit pas : « Laissez ouvert encore 5 min ». Jamais plus que cette limite d’un coup.'))}
   ${dflt('aeration_max_min','30 min',t('Assez pour renouveler l’air d’une pièce ordinaire, même par temps doux.'))}</div>
  <div class="sensor-settings">${choice('plus_tard_max_min',t('Gestes « plus tard », jusqu’à'),[30,60,120,180,240],duration)}
   ${why(t('Hestia peut attendre un meilleur moment : « Aérez vers 16 h », « Refermez vers 16 h ». Jamais plus loin que cette limite.'))}
   ${dflt('plus_tard_max_min','2 h',t('Au-delà de deux heures, la prévision devient moins sûre.'))}</div>
  <div class="sensor-settings">${choice('appareils_max_min',t('VMC rapide et purificateur, durée la plus longue'),[15,30,45,60,90,120],duration)}
   ${why(t('« Lancez le purificateur 25 min », juste ce qu’il faut.'))}
   ${dflt('appareils_max_min','1 h',t('Une heure suffit à la plupart des pièces ; une VMC rapide fait du bruit.'))}</div>
  <div class="sensor-settings">${choice('pas_maintenant_min',t('« Pas maintenant » met le geste de côté pendant'),[15,30,60,120,240],duration)}
   ${why(t('Après « Pas maintenant » sur la carte, Hestia ne redemande pas avant ce délai.'))}
   ${dflt('pas_maintenant_min','1 h',t('Le temps de finir ce qu’on faisait.'))}</div>`,{className:'nk-field-section nk-plain'})}
 ${frame(t('Le soir'),html`<div class="sensor-settings">${choice('cette_nuit_avant_h',t('« Cette nuit, pensez à… »'),[1,2,3,4,5,6,7,8],hours)}${choice('buee_avant_h',t('Buée sur les vitres cette nuit'),[1,2,3,4,5,6,7,8],hours)}
  ${why(t('Quand ces phrases apparaissent sur la carte.'))}</div>`,{className:'nk-field-section nk-plain'})}
 ${frame(t('Absence'),html`<div class="sensor-settings">${choice('hors_gel',t('Hors-gel pendant les vacances'),[5,6,7,8,9,10,11,12],degrees)}
  ${why(t('Quand l’alarme est en mode vacances, la maison est seulement gardée au-dessus de cette température.'))}
  ${dflt('hors_gel','7 °C',t('Assez pour protéger les canalisations, sans chauffer une maison vide.'))}</div>`,{className:'nk-field-section nk-plain'})}
 ${o.stove?frame(t('Le poêle'),html`<p class="hint">${t('Pour le chauffage de toute la maison : un poêle ou un insert, qu’on n’arrête pas d’un geste.')}</p>
  <div class="sensor-settings">${choice('poele_tient_h',t('Le couper s’il tient la pièce au moins'),[1,1.5,2,2.5,3,4,5,6,8,10,12],n=>t('{n} h sans lui',{n:String(n).replace('.',',')}))}
   ${why(t('Rallumer coûte des granulés et de l’usure : Hestia propose de le couper seulement si la pièce reste dans sa plage assez longtemps sans lui.'))}
   ${dflt('poele_tient_h','3 h',t('Trois heures : une soirée sans rallumer.'))}</div>
  <div class="sensor-settings">${choice('depassement',t('« Coupez le poêle » quand la pièce dépasse sa consigne de'),[0.5,1,1.5,2,2.5,3],degrees)}${choice('depassement_min',t('Pendant'),[10,15,20,30,45,60,90,120],duration)}
   ${why(t('Une pièce plus chaude que voulu, assez longtemps pour que ce ne soit pas un à-coup.'))}</div>`,{className:'nk-field-section nk-plain'}):nothing}
 ${frame(t('Santé'),html`<label class="check ex-switch"><input type="checkbox" role="switch" .checked=${o.allergy} ?disabled=${o.busy} @change=${(e:Event)=>o.setAllergy((e.target as HTMLInputElement).checked)}>${t('Allergie aux pollens')}</label>
  ${why(t('Les jours de pollens élevés, les aérations restent courtes, de préférence tôt le matin ou juste après la pluie. Une aération utile pour l’humidité ou le CO₂ est toujours conseillée.'))}
  ${o.allergy&&!o.weatherLinked?html`<p class="hint">${t('Les pollens viennent de Hestia Weather : reliez-le dans Extensions.')}</p>`:nothing}`,{className:'nk-field-section nk-plain'})}`;
}

/** « Différent du foyer pour cette pièce »: a box per setting a room may set apart; ticked, it opens on the house's value. */
export function roomFoyer(o:{house:Foyer;room:Foyer;busy:boolean;change:(next:Foyer)=>void}){
 const house={...FOYER_DEFAULTS,...o.house},room=o.room??{},n=Object.keys(room).length;
 const toggle=(key:keyof Foyer,on:boolean)=>{const next={...room} as Foyer;if(on)(next as Record<string,unknown>)[key]=(house as Record<string,unknown>)[key];else delete next[key];o.change(next);};
 const line=(key:keyof Foyer,label:string,same:string,editor:unknown)=>html`<label class="check"><input type="checkbox" .checked=${key in room} ?disabled=${o.busy} @change=${(e:Event)=>toggle(key,(e.target as HTMLInputElement).checked)}>${label}</label>
  ${key in room?html`<div class="fy-open">${editor}</div>`:html`<p class="hint fy-same">${t('Comme la maison : {value}',{value:same})}</p>`}`;
 const s={...house.sommeil,...room.sommeil};
 return frame(t('Différent du foyer pour cette pièce'),html`<p class="hint">${t('Une chambre d’enfant, un travail de nuit : cochez ce qui change ici. Le reste suit les réglages du foyer.')}</p>
  ${line('sommeil',t('Heures de sommeil'),`${house.sommeil.debut} – ${house.sommeil.fin}`,html`<div class="sensor-settings">
   <label>${t('Coucher')}<input type="time" .value=${s.debut} @change=${(e:Event)=>o.change({...room,sommeil:{...s,debut:(e.target as HTMLInputElement).value}})}></label>
   <label>${t('Lever')}<input type="time" .value=${s.fin} @change=${(e:Event)=>o.change({...room,sommeil:{...s,fin:(e.target as HTMLInputElement).value}})}></label></div>`)}
  ${line('ouvrir_la_nuit',t('Ouvrir une fenêtre la nuit'),house.ouvrir_la_nuit?t('oui'):t('non'),html`<label class="check ex-switch"><input type="checkbox" role="switch" .checked=${!!room.ouvrir_la_nuit} @change=${(e:Event)=>o.change({...room,ouvrir_la_nuit:(e.target as HTMLInputElement).checked})}>${t('Ouvrir une fenêtre la nuit, ici')}</label>`)}
  ${line('tolerance',t('Combien de conseils'),toleranceName(house.tolerance),html`<label>${t('Combien de conseils, ici')}<select @change=${(e:Event)=>o.change({...room,tolerance:Number((e.target as HTMLSelectElement).value)})}>${TOLERANCES.map(v=>html`<option value=${v} ?selected=${room.tolerance===v}>${toleranceName(v)}</option>`)}</select></label>`)}`,
  {collapsible:true,open:n>0,count:n?(n>1?t('{n} réglages différents',{n}):t('1 réglage différent')):t('rien de différent'),className:'nk-field-section nk-plain'});
}
