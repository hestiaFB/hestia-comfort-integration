import {html,nothing,type TemplateResult} from 'lit';
import type {Level} from '../types';
import {icon} from '../ui/icons';

/** The 3.0 advisor's decision for the room, as the HA de test publishes it (`sensor.conseil_3_<pièce>`), read by the card
 *  in place of the 2.1 advice: the banner, « À savoir » and « Pourquoi ? » (PASSAGE-CONFORT-3.md, the bridge of 1 November).
 *  The measures, tiles and modules stay the 2.1 view's. */
export interface Advisor3 {
  title:string;
  attributes:Record<string,unknown>;
  /** « Ce conseil ne va pas »: sends the household's opinion. */
  send?:(kind:string)=>void;
  /** What the last opinion sent answered, shown in place of the buttons. */
  said?:string;
}
interface Slide3 {title:string;line:string;disk:string;level:Level;pill:string;learned?:string}

const str=(x:unknown)=>typeof x==='string'?x:'';
const list=(x:unknown)=>Array.isArray(x)?x.filter((i):i is string=>typeof i==='string'):[];
/** The icon of each gesture, as the 2.1 banner draws its disk. */
const DISKS:Record<string,string>={nothing:'check',open:'open',open_more:'air',close:'shut',boost:'vmc',boost_off:'vmc',purify:'fan',
  purify_off:'fan',shutter_close:'window',shutter_open:'window',heat_on:'flame',heat_to:'flame',heat_stop:'flame'};
/** How sure the effect the gesture rests on is (advisor/proof.py), said under the gesture. */
const PROOF:Record<string,string>={proven:'effet avéré dans cette pièce',reinforced:'effet probable',supposed:'effet supposé'};
/** Why the banner says what it says: the rule, in a plain sentence. */
const RULES:Record<string,string>={nothing:'Aucun geste ne ferait mieux : la pièce va bien comme elle est.',
  insignificant:'Un geste changerait trop peu pour valoir la peine.',kept:'Le conseil précédent reste le meilleur.',
  unproven:'Un geste aiderait peut-être, mais son effet n’est pas encore prouvé dans cette pièce : il est à essayer.',
  best:'C’est le geste qui aide le plus, comparé à ne rien faire.',safety:'Une règle de sécurité impose ce geste.',
  overheat:'La pièce dépasse sa consigne depuis un moment : c’est une mesure, pas une prévision.',
  doubtful:'Une mesure semble fausse : pas de conseil tant qu’elle l’est.'};
const LIMITS:Record<string,string>={rain:'il pleut',rain_soon:'la pluie arrive',gusts:'rafales de vent',vigilance:'vigilance météo',
  away:'la maison est en mode absence',frost:'le gel est annoncé'};
const SOURCES:Record<string,string>={co2:'CO₂',voc:'COV',particles:'particules',humidity:'humidité'};

/** The minutes left before shutting, from the time the engine gave: the card counts down between two of its steps. */
export function countdown(a:Record<string,unknown>,now=Date.now()):string|null{
  const at=str(a.refermer_a);if(!at)return null;
  const left=Math.ceil((Date.parse(at)-now)/60000);
  return left>0?`Laissez ouvert encore ${left} min`:'Refermez';
}

/** The colour and the pill: orange for a gesture, red for safety, green for one to try, blue otherwise (the charter). */
export function level3(x:Advisor3):{level:Level;pill:string}{
  const a=x.attributes,rule=str(a.regle),gesture=str(a.geste)||'nothing';
  if(rule==='doubtful')return {level:'neutral',pill:'À vérifier'};
  if(rule==='safety')return {level:'urgent',pill:'Attention'};
  if(gesture!=='nothing')return {level:'action',pill:'Geste conseillé'};
  if(str(a.a_essayer))return {level:'benefit',pill:'À saisir'};
  return {level:'calm',pill:['insignificant','unproven'].includes(rule)||beyond(a)?'Au mieux':'Tout va bien'};
}
/** « Rien à faire » while a measure stays out of its range or mark: the engine's line says so (advisor/words.py). */
const beyond=(a:Record<string,unknown>)=>/aucun geste ne ferait vraiment mieux|^(Ouverte ou fermée|Ouverte|Fermée) :/i.test(str(a.phrase));

export function slides3(x:Advisor3):Slide3[]{
  const a=x.attributes,gesture=str(a.geste)||'nothing',{level,pill}=level3(x);
  const proof=gesture!=='nothing'&&!['safety','overheat'].includes(str(a.regle))?PROOF[str(a.preuve)]:undefined;
  return [{title:countdown(a)??x.title,line:str(a.phrase),disk:str(a.regle)==='safety'?'rain':DISKS[gesture]??'check',level,pill,learned:proof}];
}

/** « À savoir » from the 3.0 decision: what to try and the night first, then what is worth watching, then the passive advice. */
export function factBox3(x:Advisor3):TemplateResult|typeof nothing{
  const a=x.attributes,doubts=typeof a.douteuses==='string'?[a.douteuses]:[];
  const aside=a.pas_maintenant&&typeof a.pas_maintenant==='object'?Object.entries(a.pas_maintenant as Record<string,string>):[];
  const groups=[
    {id:'gesture',ic:'hand',title:'Pour le geste',lines:[str(a.a_essayer),str(a.cette_nuit),...aside.map(([what,until])=>`Mis de côté jusqu’à ${until} : ${what}`)].filter(Boolean)},
    {id:'watch',ic:'eye',title:'À surveiller',lines:doubts},
    {id:'know',ic:'info',title:'Bon à savoir',lines:list(a.bon_a_savoir)},
  ].filter(g=>g.lines.length);
  return groups.length?html`<div class="nc-facts"><div class="nw-label">À savoir</div><div class="nc-facts-box nw-glass">${groups.map(g=>html`<section class="nc-facts-g" data-group=${g.id}>
    <h4>${icon(g.ic)}${g.title}</h4><ul>${g.lines.map(l=>html`<li>${icon(g.ic)}<span>${l}</span></li>`)}</ul></section>`)}</div></div>`:nothing;
}

const OPINIONS:[string,string][]=[['faux','Faux'],['inutile','Inutile'],['pas_maintenant','Pas maintenant']];

/** « Pourquoi ? » from the 3.0 decision: the rule, the scenarios compared, what holds back, the source seen, the proof. */
export function why3(x:Advisor3):TemplateResult{
  const a=x.attributes,{pill}=level3(x),rule=str(a.regle),limit=LIMITS[str(a.interdit)];
  const sources=a.sources&&typeof a.sources==='object'?Object.keys(a.sources as object).map(k=>SOURCES[k]??k):[];
  const row=(ic:string,label:string,text:string)=>html`<div class="nc-why-row">${icon(ic)}<span>${label}</span><b>${text}</b></div>`;
  const asked=str(a.geste)!=='nothing'||!!str(a.a_essayer);
  const said=pill==='Au mieux'&&rule==='nothing'?'Une mesure sort de votre plage ou de son repère, mais aucun geste ne ferait mieux pour l’instant.':RULES[rule]??'';
  return html`<p class="nc-why-head"><b>Pourquoi « ${pill} » ?</b> ${said}</p>
    ${list(a.pourquoi).map(l=>row('clock','Scénario',l))}
    ${limit?row('alert','Ce qui limite',limit):nothing}
    ${sources.length?row('spark','Source en cours',sources.join(', ')+' : plus que d’habitude'):nothing}
    ${str(a.preuve)&&str(a.geste)!=='nothing'?row('flask','Preuve',PROOF[str(a.preuve)]??str(a.preuve)):nothing}
    ${x.send?html`<div class="nc-why-row nc-opinion">${icon('ask')}<span>Ce conseil ne va pas</span>${x.said?html`<b>${x.said}</b>`
      :html`<b>${OPINIONS.filter(([k])=>k!=='pas_maintenant'||(asked&&rule!=='safety')).map(([k,label])=>html`<button type="button" class="nw-badge" @click=${(e:Event)=>{e.stopPropagation();x.send!(k);}}>${label}</button>`)}</b>`}</div>`:nothing}`;
}
