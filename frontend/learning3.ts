import {html,nothing,type TemplateResult} from 'lit';
import {listRow,listSection,t,fr,currentLocale} from './socle/ui';

/** What the 3.0 advisor knows of a room (room/advice.py `knowing`), for the hub's « Apprentissage » (CAHIER-HUB.md § 5.3). */
export interface Effect3 {effet:string;niveau:'proven'|'reinforced'|'supposed';gestes:number;prevu:number|null;mesure:number|null;
 manque:{gestes?:number;ecart?:boolean;nuit?:boolean}|null}
export interface Advisor3Room {piece:string|null;effets:Effect3[];pourcent:number;ecart_1h:number|null;appris_le:string|null;jours:number|null}
/** How reliable the outside is (advisor_home.py `outside`). */
export interface Outside3 {source:string;station:number|null;prevision:number|null;ecart:number|null;
 soleil:{ecart?:number|null}|null;ombre_cases:number;nuages_manques:number|null}

const num=(v:number,d=1)=>v.toLocaleString(currentLocale(),{maximumFractionDigits:d,minimumFractionDigits:0});
const signed=(v:number,d=1)=>(v>0?'+':v<0?'−':'')+num(Math.abs(v),d);
/** Avéré, Renforcé, Supposé: the level of proof, as the card says it (CAHIER-MOTEUR.md § 4.1). */
const LEVELS:Record<Effect3['niveau'],[string,string,string]>={
 proven:[fr('Avéré'),'ok',fr('Vu et mesuré assez souvent pour annoncer un résultat.')],
 reinforced:[fr('Renforcé'),'',fr('Vu quelques fois, ou appuyé par les mesures du moment : le conseil reste prudent.')],
 supposed:[fr('Supposé'),'',fr('Pas encore vu : Hestia part d’une pièce ordinaire.')]};
/** Each effect in the household's words: what does it, on what. */
const EFFECTS:Record<string,string>={heat:fr('Fenêtres · chaleur'),humidity:fr('Fenêtres · humidité'),co2:fr('Fenêtres · CO₂'),
 particles:fr('Fenêtres · particules'),voc:fr('Fenêtres · COV'),'heating:heat':fr('Chauffage'),'boost:humidity':fr('VMC rapide · humidité'),
 'boost:heat':fr('VMC rapide · chaleur'),'boost:co2':fr('VMC rapide · CO₂'),'purify:particles':fr('Purificateur · particules'),
 'purify:voc':fr('Purificateur · COV'),'purify:humidity':fr('Purificateur · humidité'),'purify:co2':fr('Purificateur · CO₂'),'purify:heat':fr('Purificateur · chaleur')};
const UNITS:Record<string,[string,number]>={heat:['°C',1],humidity:['pts',0],co2:['ppm',0],particles:['µg/m³',0],voc:['',0]};

const label=(e:Effect3)=>t(EFFECTS[e.effet]??e.effet);
function seen(e:Effect3):string{
 const [unit,d]=UNITS[e.effet.split(':').pop()!]??['',1];
 if(e.effet==='heating:heat')return e.niveau==='proven'?t('Appris chaque nuit sur ses mises en marche.'):t('Appris à la première nuit qui a assez de jours.');
 if(!e.gestes)return t('Pas encore vu.');
 const times=e.gestes>1?t('vu {n} fois',{n:e.gestes}):t('vu 1 fois');
 return e.prevu!=null&&e.mesure!=null?t('{times} · prévu {f} {u}, mesuré {m} {u}',{times,f:signed(e.prevu,d),m:signed(e.mesure,d),u:unit}).replace(/ ,/g,',').trim():times;
}
/** What is still missing for an effect, in one short line; null once proven. */
function missing(e:Effect3):string|null{
 const m=e.manque;if(!m)return null;
 if(m.nuit)return t('{what} : la première nuit avec assez de mesures',{what:label(e)});
 if(m.gestes)return m.gestes>1?t('{what} : encore {n} fois à voir',{what:label(e),n:m.gestes}):t('{what} : encore 1 fois à voir',{what:label(e)});
 return t('{what} : vu assez, mais la prévision ne colle pas encore',{what:label(e)});
}
export const firstMissing=(a:Advisor3Room)=>a.effets.map(missing).find(Boolean)??null;

/** « Apprentissage » of one room, from the 3.0 advisor: what it knows, what is missing, how its forecasts hold. */
export function roomLearning3(a:Advisor3Room):TemplateResult{
 const left=a.effets.map(missing).filter((m):m is string=>!!m);
 const day=a.appris_le?new Date(a.appris_le).toLocaleString(currentLocale(),{weekday:'long',hour:'2-digit',minute:'2-digit'}):null;
 return html`${listSection(t('Ce que Hestia sait de la pièce'),a.effets.map(e=>{const [word,cls,why]=LEVELS[e.niveau];
   return listRow({label:label(e),sub:seen(e),value:html`<span class=${'nk-pill '+cls} title=${t(why)}>${t(word)}</span>`});}),
  {help:html`<p>${t('Avéré : vu et mesuré assez souvent pour annoncer un résultat. Renforcé : vu quelques fois, le conseil reste prudent. Supposé : pas encore vu, Hestia part d’une pièce ordinaire.')}</p>`})}
 ${listSection(t('Ce qui manque encore'),left.length?left.map(l=>listRow({label:l})):[listRow({label:t('Rien : tout ce que la pièce possède a été vu.')})])}
 ${listSection(t('Ses prévisions'),[
  listRow({label:t('Écart sur la dernière heure'),value:a.ecart_1h!=null?t('{v} °C',{v:signed(a.ecart_1h,1)}):t('pas encore mesuré')}),
  listRow({label:t('Dernier apprentissage'),value:day??t('pas encore')}),
  ...(a.jours!=null?[listRow({label:t('Mesures relues'),value:a.jours>=2?t('{n} jours',{n:num(a.jours,0)}):t('{n} jour',{n:num(a.jours,0)})})]:[])])}`;
}

/** « Le dehors », on the « Apprentissage » page: can the outside the advisor reads be trusted. */
export function outside3(o:Outside3|null|undefined):TemplateResult|typeof nothing{
 if(!o)return nothing;
 const sun=o.soleil?.ecart;
 return listSection(t('Le dehors'),[
  listRow({label:t('Prévision'),sub:o.ecart!=null?t('Écart avec la station maintenant : {v} °C',{v:signed(o.ecart,1)}):undefined,value:o.source}),
  listRow({label:t('Position du soleil'),value:sun==null?t('pas vérifiée'):sun<=1?t('juste'):t('écart de {v}° : vérifiez la position de la maison',{v:num(sun,1)})}),
  ...(o.ombre_cases?[listRow({label:t('Ombre de la station'),sub:o.nuages_manques!=null?t('Nuages manqués par la prévision : {v} %',{v:num(o.nuages_manques*100,0)}):undefined,value:t('apprise')})]:[])],
  {help:html`<p>${t('Le moteur compare la prévision à la station, et sa propre position du soleil à celle de Home Assistant : un écart dit qu’une source est à vérifier.')}</p>`});
}
