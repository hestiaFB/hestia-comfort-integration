import {html,nothing} from 'lit';
import {listSection,listRow,moreRow,toggle,pageHead,t,fr,type NkAction} from './socle/ui';

/** The household's settings (« Réglages du foyer », niak-comfort/docs/REGLAGES-3.md § 4.3): only what the person set
 *  is kept, a missing key takes its default. The same keys as the advisor's `Habits` (advisor/household.py). */
export type Foyer=Partial<{sommeil:{debut:string;fin:string};ouvrir_la_nuit:boolean;tolerance:number;aeration_max_min:number;
 plus_tard_max_min:number;appareils_max_min:number;cette_nuit_avant_h:number;buee_avant_h:number;hors_gel:number;
 pas_maintenant_min:number;poele_tient_h:number;depassement:number;depassement_min:number;isolation:Walls;vitrage:Glazing}>;
/** The house itself, for the room's ressenti (engine/feel.py): how well the walls are insulated, which glazing. */
export type Walls='bien'|'moyenne'|'peu';export type Glazing='simple'|'double'|'triple';
export const FOYER_DEFAULTS={sommeil:{debut:'22:00',fin:'07:00'},ouvrir_la_nuit:false,tolerance:1,aeration_max_min:30,plus_tard_max_min:120,
 appareils_max_min:60,cette_nuit_avant_h:4,buee_avant_h:5,hors_gel:7,pas_maintenant_min:60,poele_tient_h:3,depassement:1,depassement_min:30,
 isolation:'moyenne' as Walls,vitrage:'double' as Glazing};
const WALLS:[Walls,string][]=[['bien',fr('Bien isolés')],['moyenne',fr('Moyennement isolés')],['peu',fr('Peu ou pas isolés')]];
const GLAZING:[Glazing,string][]=[['simple',fr('Simple vitrage')],['double',fr('Double vitrage')],['triple',fr('Triple vitrage')]];
// « Combien de conseils »: five notches, the middle one the default (foyer.py TOLERANCES).
export const TOLERANCES=[0.5,0.75,1,1.5,2];
const toleranceWords=[fr('Même les petits gains sont dits.'),fr('Un peu plus de conseils.'),fr('Les gestes qui changent quelque chose qu’on sent.'),fr('Un peu moins de conseils.'),fr('Seulement les gestes les plus nets.')];
export const toleranceName=(v:number)=>[t('Beaucoup plus'),t('Un peu plus'),t('Normal'),t('Un peu moins'),t('Beaucoup moins')][Math.max(0,TOLERANCES.indexOf(v))];

export function duration(minutes:number){const h=Math.floor(minutes/60),m=minutes%60;return h?(m?t('{h} h {m}',{h,m:String(m).padStart(2,'0')}):t('{h} h',{h})):t('{n} min',{n:minutes});}
const hours=(n:number)=>n===1?t('1 h avant le coucher'):t('{n} h avant le coucher',{n:String(n).replace('.',',')});
const degrees=(n:number)=>String(n).replace('.',',')+' °C';

interface Options {head?:boolean;foyer:Foyer;busy:boolean;stove:boolean;allergy:boolean;weatherLinked:boolean;back:NkAction;
 change:(next:Foyer)=>void;setAllergy:(on:boolean)=>void}

/** The page (CAHIER-HUB.md § 5.2): one list per subject, one row per setting; each change is saved at once. */
export function foyerPage(o:Options){
 const f={...FOYER_DEFAULTS,...o.foyer},set=(key:keyof Foyer,value:unknown)=>{const next={...o.foyer,[key]:value} as Foyer;if(JSON.stringify(value)===JSON.stringify(FOYER_DEFAULTS[key as keyof typeof FOYER_DEFAULTS]))delete next[key];o.change(next);};
 const choice=(key:keyof Foyer,label:string,values:number[],word:(n:number)=>string)=>html`<select aria-label=${label} ?disabled=${o.busy} @change=${(e:Event)=>set(key,Number((e.target as HTMLSelectElement).value))}>${values.map(v=>html`<option value=${v} ?selected=${(f as Record<string,unknown>)[key]===v}>${word(v)}</option>`)}</select>`;
 const pick=<T extends string>(key:keyof Foyer,label:string,values:[T,string][])=>html`<select aria-label=${label} ?disabled=${o.busy} @change=${(e:Event)=>set(key,(e.target as HTMLSelectElement).value)}>${values.map(([v,w])=>html`<option value=${v} ?selected=${(f as Record<string,unknown>)[key]===v}>${t(w)}</option>`)}</select>`;
 const time=(label:string,value:string,change:(v:string)=>void)=>html`<input type="time" aria-label=${label} .value=${value} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)change(v);}}>`;
 const row=(label:string,value:unknown,sub?:unknown)=>listRow({label,value,sub});
 const tol=Math.max(0,TOLERANCES.indexOf(f.tolerance));
 return html`${o.head===false?nothing:pageHead({back:o.back,title:t('Réglages du foyer'),subtitle:t('Votre façon de vivre, pour toute la maison. Une pièce qui vit autrement se règle dans son onglet « La pièce ».')})}
 ${listSection(t('Sommeil'),[row(t('Coucher'),time(t('Coucher'),f.sommeil.debut,v=>set('sommeil',{debut:v,fin:f.sommeil.fin}))),row(t('Lever'),time(t('Lever'),f.sommeil.fin,v=>set('sommeil',{debut:f.sommeil.debut,fin:v}))),
  row(t('Ouvrir une fenêtre la nuit'),toggle(t('Ouvrir une fenêtre la nuit'),f.ouvrir_la_nuit,on=>set('ouvrir_la_nuit',on),o.busy),f.ouvrir_la_nuit?t('Hestia peut conseiller d’ouvrir pendant le sommeil.'):t('Aucune ouverture conseillée pendant le sommeil.'))],
  {help:html`<p>${t('La nuit, Hestia ne propose que les gestes importants. L’alarme en mode nuit compte aussi.')}</p>`})}
 ${listSection(t('Conseils'),[row(t('Combien de conseils'),html`<input type="range" aria-label=${t('Combien de conseils')} min="0" max="4" step="1" .value=${String(tol)} ?disabled=${o.busy} @change=${(e:Event)=>set('tolerance',TOLERANCES[Number((e.target as HTMLInputElement).value)])}>`,t(toleranceWords[tol])),
  row(t('Aération la plus longue'),choice('aeration_max_min',t('Aération la plus longue'),[10,15,20,30,45,60],duration)),
  row(t('Gestes « plus tard », jusqu’à'),choice('plus_tard_max_min',t('Gestes « plus tard », jusqu’à'),[30,60,120,180,240],duration)),
  row(t('VMC et purificateur, au plus'),choice('appareils_max_min',t('VMC et purificateur, au plus'),[15,30,45,60,90,120],duration)),
  row(t('« Pas maintenant » met de côté'),choice('pas_maintenant_min',t('« Pas maintenant » met de côté'),[15,30,60,120,240],duration))],
  {help:html`<p>${t('Hestia calcule la durée de chaque geste, de 5 en 5 minutes. Vous fixez seulement les limites. La sécurité passe toujours : « Fermez, il pleut » reste.')}</p>`})}
 ${listSection(t('Le soir'),[row(t('« Cette nuit, pensez à… »'),choice('cette_nuit_avant_h',t('« Cette nuit, pensez à… »'),[1,2,3,4,5,6,7,8],hours)),row(t('Buée sur les vitres'),choice('buee_avant_h',t('Buée sur les vitres'),[1,2,3,4,5,6,7,8],hours))])}
 ${listSection(t('Le logement'),[row(t('Murs'),pick('isolation',t('Murs'),WALLS)),row(t('Fenêtres'),pick('vitrage',t('Fenêtres'),GLAZING))],
  {help:html`<p>${t('Pour le ressenti des pièces : des murs et des vitres froids se sentent, même quand l’air est à bonne température.')}</p>`})}
 ${listSection(t('Absence et santé'),[row(t('Hors-gel pendant les vacances'),choice('hors_gel',t('Hors-gel pendant les vacances'),[5,6,7,8,9,10,11,12],degrees)),
  row(t('Allergie aux pollens'),toggle(t('Allergie aux pollens'),o.allergy,on=>o.setAllergy(on),o.busy),o.allergy&&!o.weatherLinked?t('Les pollens viennent de Hestia Weather : reliez-le dans Extensions.'):t('Les jours de pollens élevés, aérations courtes et tôt.'))])}
 ${o.stove?listSection(t('Le poêle'),[row(t('Le couper s’il tient la pièce'),choice('poele_tient_h',t('Le couper s’il tient la pièce'),[1,1.5,2,2.5,3,4,5,6,8,10,12],n=>t('{n} h sans lui',{n:String(n).replace('.',',')}))),
  row(t('« Coupez le poêle » au-dessus de la consigne'),html`${choice('depassement',t('« Coupez le poêle » au-dessus de la consigne'),[0.5,1,1.5,2,2.5,3],n=>'+ '+degrees(n))}${choice('depassement_min',t('Pendant'),[10,15,20,30,45,60,90,120],n=>t('pendant {d}',{d:duration(n)}))}`)],
  {help:html`<p>${t('Pour un chauffage de toute la maison. Rallumer coûte des granulés et de l’usure.')}</p>`}):nothing}`;
}

/** « Différent du foyer pour cette pièce »: a box per setting a room may set apart; ticked, it opens on the house's value. */
export function roomFoyer(o:{house:Foyer;room:Foyer;busy:boolean;change:(next:Foyer)=>void}){
 const house={...FOYER_DEFAULTS,...o.house},room=o.room??{},n=Object.keys(room).length,f={...house,...room};
 const own=(key:keyof Foyer,label:string,control:unknown)=>{const mine=key in room;return listRow({label,sub:mine?t('Propre à cette pièce'):t('Comme la maison'),
  value:html`${control}${mine?html`<button type="button" class="nk-reset-s" ?disabled=${o.busy} @click=${()=>{const next={...room};delete next[key];o.change(next);}}>${t('Comme la maison')}</button>`:nothing}`});};
 return moreRow(t('Différent du foyer'),n?(n>1?t('{n} réglages',{n}):t('1 réglage')):t('rien'),[
  own('sommeil',t('Coucher'),html`<input type="time" aria-label=${t('Coucher')} .value=${f.sommeil.debut} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)o.change({...room,sommeil:{debut:v,fin:f.sommeil.fin}});}}>`),
  own('ouvrir_la_nuit',t('Ouvrir une fenêtre la nuit'),toggle(t('Ouvrir une fenêtre la nuit'),!!f.ouvrir_la_nuit,on=>o.change({...room,ouvrir_la_nuit:on}),o.busy)),
  own('tolerance',t('Combien de conseils'),html`<select aria-label=${t('Combien de conseils')} ?disabled=${o.busy} @change=${(e:Event)=>o.change({...room,tolerance:Number((e.target as HTMLSelectElement).value)})}>${TOLERANCES.map(v=>html`<option value=${v} ?selected=${f.tolerance===v}>${toleranceName(v)}</option>`)}</select>`)]);
}
