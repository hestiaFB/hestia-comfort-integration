import {html,nothing} from 'lit';
import {listSection,listRow,moreRow,toggle,pageHead,segmented,t,fr,type NkAction} from './socle/ui';
import {habitsSection,houseSection,weekendRow,type HabitsContext,type HouseUses,type Question,type ShutterHabit} from './habitudes';

/** The household's settings (« Réglages du foyer », niak-comfort/docs/REGLAGES-3.md § 4.3): only what the person set
 *  is kept, a missing key takes its default. The same keys as the advisor's `Habits` (advisor/household.py). */
export type Foyer=Partial<{sommeil:{debut:string;fin:string;fin_weekend?:string};
 volets_absence:ShutterHabit;volets_nuit:ShutterHabit;volets_ete:ShutterHabit;journee_vide:{de:string;a:string}|null;linge_pieces:string[];linge_parfois:boolean;repondu:Question[];
 volet:'none'|'manual'|'connected';hauteur:number;murs:'heavy'|'wood';plage:Partial<Record<'minimum'|'maximum'|'summer_maximum',number>>;ouvrir_la_nuit:boolean;tolerance:number;aeration_max_min:number;
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
 change:(next:Foyer)=>void;setAllergy:(on:boolean)=>void;
 /** The home as « Vos habitudes » and « Votre maison » need it (habitudes.ts). */
 home?:Pick<HabitsContext,'manual'|'absences'|'rooms'>&{uses:HouseUses}}

/** The page (CAHIER-HUB.md § 5.2): one list per subject, one row per setting; each change is saved at once. */
export function foyerPage(o:Options){
 const f={...FOYER_DEFAULTS,...o.foyer},set=(key:keyof Foyer,value:unknown)=>{const next={...o.foyer,[key]:value} as Foyer;if(JSON.stringify(value)===JSON.stringify(FOYER_DEFAULTS[key as keyof typeof FOYER_DEFAULTS]))delete next[key];o.change(next);};
 const choice=(key:keyof Foyer,label:string,values:number[],word:(n:number)=>string)=>html`<select aria-label=${label} ?disabled=${o.busy} @change=${(e:Event)=>set(key,Number((e.target as HTMLSelectElement).value))}>${values.map(v=>html`<option value=${v} ?selected=${(f as Record<string,unknown>)[key]===v}>${word(v)}</option>`)}</select>`;
 const pick=<T extends string>(key:keyof Foyer,label:string,values:[T,string][])=>html`<select aria-label=${label} ?disabled=${o.busy} @change=${(e:Event)=>set(key,(e.target as HTMLSelectElement).value)}>${values.map(([v,w])=>html`<option value=${v} ?selected=${(f as Record<string,unknown>)[key]===v}>${t(w)}</option>`)}</select>`;
 const time=(label:string,value:string,change:(v:string)=>void)=>html`<input type="time" aria-label=${label} .value=${value} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)change(v);}}>`;
 const row=(label:string,value:unknown,sub?:unknown)=>listRow({label,value,sub});
 const tol=Math.max(0,TOLERANCES.indexOf(f.tolerance));
 const context:HabitsContext|undefined=o.home?{foyer:o.foyer,busy:o.busy,change:o.change,manual:o.home.manual,absences:o.home.absences,rooms:o.home.rooms}:undefined;
 return html`${o.head===false?nothing:pageHead({back:o.back,title:t('Réglages du foyer'),subtitle:t('Votre façon de vivre, pour toute la maison. Une pièce qui vit autrement se règle dans son onglet « La pièce ».')})}
 ${listSection(t('Sommeil'),[row(t('Coucher'),time(t('Coucher'),f.sommeil.debut,v=>set('sommeil',{debut:v,fin:f.sommeil.fin}))),row(t('Lever'),time(t('Lever'),f.sommeil.fin,v=>set('sommeil',{debut:f.sommeil.debut,fin:v}))),
  ...(context?[weekendRow(context)]:[]),
  row(t('Ouvrir une fenêtre la nuit'),toggle(t('Ouvrir une fenêtre la nuit'),f.ouvrir_la_nuit,on=>set('ouvrir_la_nuit',on),o.busy),f.ouvrir_la_nuit?t('Hestia-FB peut conseiller d’ouvrir pendant le sommeil.'):t('Aucune ouverture conseillée pendant le sommeil.'))],
  {help:html`<p>${t('La nuit, Hestia-FB ne propose que les gestes importants. L’alarme en mode nuit compte aussi.')}</p>`})}
 ${context&&o.home?html`${houseSection({...context,uses:o.home.uses})}${habitsSection(context)}`:nothing}
 ${listSection(t('Conseils'),[row(t('Combien de conseils'),// To the right, more advice; its two ends said (Frank, 5 November: « la barre n'indique rien »).
  html`<span class="hb-scale"><input type="range" aria-label=${t('Combien de conseils')} min="0" max="4" step="1" .value=${String(4-tol)} ?disabled=${o.busy} @change=${(e:Event)=>set('tolerance',TOLERANCES[4-Number((e.target as HTMLInputElement).value)])}><span class="hb-ends" aria-hidden="true"><span>${t('Moins')}</span><span>${t('Plus')}</span></span></span>`,t(toleranceWords[tol])),
  row(t('Aération la plus longue'),choice('aeration_max_min',t('Aération la plus longue'),[10,15,20,30,45,60],duration)),
  row(t('Gestes « plus tard », jusqu’à'),choice('plus_tard_max_min',t('Gestes « plus tard », jusqu’à'),[30,60,120,180,240],duration)),
  row(t('VMC et purificateur conseillés, au plus'),choice('appareils_max_min',t('VMC et purificateur conseillés, au plus'),[15,30,45,60,90,120],duration)),
  row(t('« Pas maintenant » met de côté'),choice('pas_maintenant_min',t('« Pas maintenant » met de côté'),[15,30,60,120,240],duration))],
  {help:html`<p>${t('Hestia-FB ne commande rien : il conseille, vous faites le geste.')}</p><p>${t('Hestia-FB calcule la durée de chaque geste, de 5 en 5 minutes. Vous fixez seulement les limites. La sécurité passe toujours : « Fermez, il pleut » reste.')}</p>`})}
 ${listSection(t('Le soir'),[row(t('« Cette nuit, pensez à… »'),choice('cette_nuit_avant_h',t('« Cette nuit, pensez à… »'),[1,2,3,4,5,6,7,8],hours)),row(t('Buée sur les vitres'),choice('buee_avant_h',t('Buée sur les vitres'),[1,2,3,4,5,6,7,8],hours))])}
 ${context?nothing:listSection(t('Le logement'),[row(t('Murs'),pick('isolation',t('Murs'),WALLS)),row(t('Fenêtres'),pick('vitrage',t('Fenêtres'),GLAZING))],
  {help:html`<p>${t('Pour le ressenti des pièces : des murs et des vitres froids se sentent, même quand l’air est à bonne température.')}</p>`})}
 ${listSection(t('Absence et santé'),[row(t('En vacances, conseiller de chauffer sous'),choice('hors_gel',t('En vacances, conseiller de chauffer sous'),[5,6,7,8,9,10,11,12],degrees),t('Le minimum de la maison pendant vos absences de plusieurs jours.')),
  row(t('Allergie aux pollens'),toggle(t('Allergie aux pollens'),o.allergy,on=>o.setAllergy(on),o.busy),o.allergy&&!o.weatherLinked?t('Les pollens viennent de Hestia Weather : reliez-le dans Extensions.'):t('Les jours de pollens élevés, aérations courtes et tôt.'))])}
 ${o.stove?listSection(t('Chauffage'),[
  // Advice only, never a command (Frank, 5 November: « on sous-entend que Confort coupe de lui-même »).
  listRow({label:t('Conseiller de le couper quand la maison tient sans lui'),sub:t('Hestia-FB vous le dit, il ne touche pas au chauffage.'),
   value:choice('poele_tient_h',t('Conseiller de le couper quand la maison tient sans lui'),[1,1.5,2,2.5,3,4,5,6,8,10,12],n=>t('{n} h sans lui',{n:String(n).replace('.',',')}))}),
  listRow({label:t('Conseiller de le couper quand il chauffe trop'),sub:t('Au-dessus de la consigne, depuis un moment.'),
   value:html`${choice('depassement',t('Conseiller de le couper quand il chauffe trop'),[0.5,1,1.5,2,2.5,3],n=>'+ '+degrees(n))}${choice('depassement_min',t('Pendant'),[10,15,20,30,45,60,90,120],n=>t('pendant {d}',{d:duration(n)}))}`})],
  {help:html`<p>${t('Pour le chauffage de toute la maison : poêle, chaudière, pompe à chaleur. Pas les radiateurs d’une seule pièce.')}</p><p>${t('Hestia-FB ne le commande pas : il vous conseille de le couper, vous décidez. Rallumer coûte de l’énergie et de l’usure : le conseil ne vient que si la maison tient assez longtemps.')}</p>`}):nothing}`;
}

/** « Différent du foyer pour cette pièce »: a box per setting a room may set apart; ticked, it opens on the house's value. */
export function roomFoyer(o:{house:Foyer;room:Foyer;busy:boolean;change:(next:Foyer)=>void;manual?:boolean}){
 const house={...FOYER_DEFAULTS,...o.house},room=o.room??{},n=Object.keys(room).length,f={...house,...room};
 const own=(key:keyof Foyer,label:string,control:unknown)=>{const mine=key in room;return listRow({label,sub:mine?t('Propre à cette pièce'):t('Comme la maison'),
  value:html`${control}${mine?html`<button type="button" class="nk-reset-s" ?disabled=${o.busy} @click=${()=>{const next={...room};delete next[key];o.change(next);}}>${t('Comme la maison')}</button>`:nothing}`});};
 return moreRow(t('Différent du foyer'),n?(n>1?t('{n} réglages',{n}):t('1 réglage')):t('rien'),[
  own('sommeil',t('Coucher'),html`<input type="time" aria-label=${t('Coucher')} .value=${f.sommeil.debut} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)o.change({...room,sommeil:{debut:v,fin:f.sommeil.fin}});}}>`),
  own('ouvrir_la_nuit',t('Ouvrir une fenêtre la nuit'),toggle(t('Ouvrir une fenêtre la nuit'),!!f.ouvrir_la_nuit,on=>o.change({...room,ouvrir_la_nuit:on}),o.busy)),
  own('tolerance',t('Combien de conseils'),html`<select aria-label=${t('Combien de conseils')} ?disabled=${o.busy} @change=${(e:Event)=>o.change({...room,tolerance:Number((e.target as HTMLSelectElement).value)})}>${TOLERANCES.map(v=>html`<option value=${v} ?selected=${f.tolerance===v}>${toleranceName(v)}</option>`)}</select>`),
  // A room with a manual shutter may shut it otherwise (HABITUDES-FOYER.md: the chambre M's is almost never shut).
  ...(o.manual?([['volets_absence',t('Volet quand vous partez')],['volets_nuit',t('Volet la nuit')],['volets_ete',t('Volet l’été, aux heures chaudes')]] as const).map(([key,label])=>
   own(key,label,segmented(label,[['fermes',t('Fermés')],['ouverts',t('Ouverts')],['variable',t('Ça dépend')]],(f[key]??'variable') as ShutterHabit,v=>o.change({...room,[key]:v}),o.busy))):[])]);
}
