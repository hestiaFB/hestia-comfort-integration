// The installation guide: every setting worth knowing, one question a screen, saved once at the end.
// Two guides with the same frame, as in Hestia Weather's (its guide.ts): the house (the outside, how it is built, how it lives,
// the lights) and each room (its sensors, its openings one by one, its heating, its equipment).
// They work on the same drafts as the settings: a room's draft is the one of its tabs, saved by the same command; the house's
// settings, saved at each change in Réglages, are kept in a draft here and sent at the end with the same commands.
// For now they live beside the settings; they are built to replace them one day: each topic says whether it is complete.
import {html,nothing,type TemplateResult} from 'lit';
import {t,fr} from './socle/ui';
import type {Foyer} from './foyer';
import type {Lights} from './lights';
import type {Question} from './habitudes';
import type {RoomConfig,Candidate} from './model';

export type GuideKind='house'|'room';
export type GuideTopic='welcome'|'outside'|'house'|'sleep'|'habits'|'advice'|'lights'
 |'measures'|'air'|'presence'|'openings'|'opening'|'heating'|'equipment'|'room'|'notifications'|'recap';
/** One screen of a guide; a habit takes one screen per question, an opening one per window or door. */
export interface GuideScreen {key:string;topic:GuideTopic;item?:string}

/** What the house's guide needs to know: its draft, and what the home offers. */
export interface HouseState {kind:'house';foyer:Foyer;lights:Lights;
 /** The outside is given: Hestia Weather chosen, or at least an outdoor temperature. */
 outside:boolean;
 /** The habits' questions asked for this home, in order (habitudes.ts), without the ones another screen asks. */
 habits:Question[];
 /** A light able to show the advice exists in Home Assistant. */
 lightsFound:boolean}
/** What a room's guide needs to know: its draft, the sensors found, whether its light is set here. */
export interface RoomState {kind:'room';room:RoomConfig;candidates:Record<string,Candidate[]|undefined>;
 /** The lights go room by room and the room exists: its light is chosen on its own screen. */
 ownLight:boolean;lightSet:boolean}
export type GuideState=HouseState|RoomState;

/** The name of each topic, on top of its screens and in the guide's summary. */
export const TOPICS:Record<GuideTopic,string>={welcome:fr('Bienvenue'),outside:fr('Le dehors'),house:fr('Votre maison'),sleep:fr('Le sommeil'),
 habits:fr('Vos habitudes'),advice:fr('Les conseils'),lights:fr('La lumière du conseil'),measures:fr('Température et humidité'),air:fr('L’air de la pièce'),
 presence:fr('La présence'),openings:fr('Fenêtres et portes'),opening:fr('Chaque ouvrant'),heating:fr('Le chauffage'),equipment:fr('VMC et équipements'),
 room:fr('La pièce'),notifications:fr('Sa lumière'),recap:fr('Récapitulatif')};
// The question each topic asks, and why, in one or two lines (a habit and an opening have their own).
const ASK:Partial<Record<GuideTopic,[string,string]>>={
 outside:[fr('D’où vient le dehors ?'),fr('Confort compare chaque pièce au dehors : plus frais, plus sec, pluie, vent, soleil. Hestia Weather donne tout ; sinon, un capteur par mesure.')],
 house:[fr('Comment est votre maison ?'),fr('Chaque pièce et chaque fenêtre reprend ces valeurs : vous n’aurez à changer que celles qui diffèrent.')],
 sleep:[fr('Quand dormez-vous ?'),fr('Ni conseil ni lumière pendant votre sommeil, sauf les gestes importants.')],
 advice:[fr('Combien de conseils ?'),fr('Des petits gains aux seuls gestes les plus nets. Hestia-FB ne commande rien : il conseille, vous faites le geste.')],
 lights:[fr('Une lumière pour montrer le conseil ?'),fr('Elle prend la couleur du conseil : bleu tout va bien, vert à saisir, orange un geste. Facultatif.')],
 measures:[fr('Quelle température suivre ?'),fr('La mesure de l’air de cette pièce, la seule obligatoire. L’humidité permet de conseiller contre l’air trop humide ou trop sec.')],
 air:[fr('Mesurez-vous l’air de la pièce ?'),fr('Le CO₂ dit quand aérer, les particules et les COV quand l’air se charge, la luminosité quand le soleil entre. Tout est facultatif.')],
 presence:[fr('Qui vit dans cette pièce ?'),fr('Pas de conseil quand personne n’est là pour le suivre. Facultatif.')],
 openings:[fr('Quelles fenêtres et portes ?'),fr('Leur contact dit quand elles sont ouvertes : Confort apprend ce qu’une aération change dans la pièce.')],
 heating:[fr('Comment la pièce est-elle chauffée ?'),fr('Confort apprend ce que le chauffage apporte à la pièce, et en tient compte dans ses conseils.')],
 equipment:[fr('Une VMC, un purificateur, une douche ?'),fr('Ce qui change l’air de la pièce. Relié à une entité, Hestia-FB sait quand il marche. Facultatif.')],
 room:[fr('Où est cette pièce ?'),fr('Son nom, son étage, et les pièces qui partagent son air, comme un salon ouvert sur sa cuisine.')],
 notifications:[fr('Une lumière pour cette pièce ?'),fr('Elle prend la couleur du conseil de la pièce. Elle s’enregistre tout de suite, sans attendre la fin du guide.')],
};
export const askOf=(topic:GuideTopic):[string,string]=>{const a=ASK[topic];return a?[t(a[0]),t(a[1])]:['',''];};

const offered=(s:RoomState,keys:string[])=>keys.some(k=>!!s.candidates[k]?.length);
const has=(r:RoomConfig,key:string)=>!!r.sources?.[key];

/** The screens of a guide for this draft, in order. Worked out at every change: an opening added, a light mode changed. */
export function guideScreens(s:GuideState):GuideScreen[]{
 const one=(topic:GuideTopic):GuideScreen=>({key:topic,topic});
 if(s.kind==='house')return [one('welcome'),one('outside'),one('house'),one('sleep'),
  ...s.habits.map(q=>({key:'habits:'+q,topic:'habits' as const,item:q})),one('advice'),one('lights'),one('recap')];
 const r=s.room;
 return [one('welcome'),one('measures'),one('air'),one('presence'),one('openings'),
  ...r.windows.map(id=>({key:'opening:'+id,topic:'opening' as const,item:id})),one('heating'),one('equipment'),one('room'),
  ...(s.ownLight?[one('notifications')]:[]),one('recap')];
}
/** Whether a topic is complete for this draft: nothing left that Hestia-FB could use. « Facultatif » stays complete when
 *  nothing is there to choose. */
export function topicDone(topic:GuideTopic,s:GuideState):boolean{
 if(s.kind==='house'){const f=s.foyer,seen=f.repondu??[];
  switch(topic){
   case 'outside':return s.outside;
   case 'house':return seen.includes('vitrage');
   case 'sleep':return !!f.sommeil;
   case 'habits':return s.habits.every(q=>seen.includes(q));
   case 'lights':return !s.lightsFound||s.lights.mode==='rooms'||!!s.lights.home;
   default:return true;
  }
 }
 const r=s.room;
 switch(topic){
  case 'measures':return has(r,'indoor_temperature')&&(has(r,'indoor_humidity')||!offered(s,['indoor_humidity']));
  case 'air':return ['co2','pm25','voc','illuminance'].some(k=>has(r,k))||!offered(s,['co2','pm25','voc','illuminance']);
  case 'presence':return !!r.presence?.length||!!r.persons?.length||!offered(s,['presence']);
  case 'openings':return !!r.windows.length||r.windows_unmeasured===true||!offered(s,['windows']);
  case 'opening':return r.windows.every(id=>!!r.openings?.[id]?.exposure);
  case 'heating':return r.heated===false||!!r.heaters?.length||has(r,'heating')||!offered(s,['heating']);
  case 'equipment':return has(r,'ventilation')||has(r,'purifier')||!!r.equipment?.length||!offered(s,['ventilation','purifier']);
  case 'room':return !!r.name.trim();
  case 'notifications':return s.lightSet;
  default:return true;
 }
}
/** The screen that cannot be left empty: a room's temperature. */
export function ready(screen:GuideScreen,s:GuideState):boolean{return s.kind!=='room'||screen.topic!=='measures'||has(s.room,'indoor_temperature');}
/** The topics of a guide, once each, in order, with their state: the summary of the welcome screen. */
export function guideTopics(s:GuideState):{topic:GuideTopic;done:boolean;first:string}[]{
 const seen=new Map<GuideTopic,string>();
 for(const x of guideScreens(s))if(!seen.has(x.topic))seen.set(x.topic,x.key);
 return [...seen].filter(([topic])=>topic!=='welcome'&&topic!=='recap').map(([topic,first])=>({topic,first,done:topicDone(topic,s)}));
}
/** The topics still worth a look: the line of a room or of the house in the overview. */
export const left=(s:GuideState)=>guideTopics(s).filter(x=>!x.done).length;
/** The screen after or before this one; an unknown key (an opening removed) starts again from the welcome. */
export function nextScreen(s:GuideState,key:string,step:1|-1):string{
 const list=guideScreens(s),at=list.findIndex(x=>x.key===key);
 return list[Math.max(0,Math.min(list.length-1,(at<0?0:at)+step))].key;
}

export interface GuideFrame {state:GuideState;at:string;busy:boolean;body:unknown;saveLabel:string;
 go:(key:string)=>void;save:()=>void;skip?:()=>void}
/** A screen of a guide: where one is, the question and why, its body, then « Précédent », « Passer » and « Suivant »
 *  (« Enregistrer » at the end). */
export function guideFrame(o:GuideFrame):TemplateResult{
 const list=guideScreens(o.state),at=Math.max(0,list.findIndex(x=>x.key===o.at)),screen=list[at],last=at===list.length-1,ok=ready(screen,o.state);
 const progress=html`<p class="hb-step">${t('Guide · {topic} · {n} sur {total}',{topic:t(TOPICS[screen.topic]),n:at+1,total:list.length})}</p>
  <div class="hb-progress" role="progressbar" aria-label=${t('Avancement du guide')} aria-valuemin="0" aria-valuemax=${list.length-1} aria-valuenow=${at}><i style=${`width:${at/(list.length-1)*100}%`}></i></div>`;
 const back=at?html`<button type="button" class="link" ?disabled=${o.busy} @click=${()=>o.go(list[at-1].key)}>‹ ${t('Précédent')}</button>`:nothing;
 const skip=o.skip&&!last&&screen.topic!=='welcome'&&ok?html`<button type="button" class="link" ?disabled=${o.busy} @click=${o.skip}>${screen.topic==='habits'?t('Je ne sais pas'):t('Passer')}</button>`:nothing;
 const next=last?html`<button type="button" class="primary" ?disabled=${o.busy||!list.every(x=>ready(x,o.state))} @click=${o.save}>${o.saveLabel}</button>`
  :html`<button type="button" class="primary" ?disabled=${o.busy||!ok} @click=${()=>o.go(list[at+1].key)}>${at?t('Suivant'):t('Commencer')}</button>`;
 return html`<div class="hb-quiz gd-guide">${progress}${o.body}<p class="hb-foot gd-foot">${back}<span class="hb-sp"></span>${skip}${next}</p></div>`;
}
/** The welcome screen: what the guide does, then its topics, each a line to jump to, a mark when complete. */
export function welcome(o:{state:GuideState;title:string;intro:string;busy:boolean;go:(key:string)=>void}):TemplateResult{
 const topics=guideTopics(o.state),n=topics.filter(x=>!x.done).length;
 return html`<h2 class="hb-title">${o.title}</h2>
  <p class="muted">${t('Une question à la fois, avec la raison de chacune. Rien n’est enregistré avant la dernière étape.')}</p>
  <p class="muted">${o.intro} ${n?(n>1?t('{n} étapes peuvent encore servir.',{n}):t('{n} étape peut encore servir.',{n})):t('Tout est déjà réglé : le guide permet de tout revoir.')}</p>
  <ol class="gd-topics">${topics.map(x=>html`<li><button type="button" class=${x.done?'gd-done':'gd-left'} ?disabled=${o.busy} @click=${()=>o.go(x.first)}>
   <span class="gd-mark" aria-hidden="true">${x.done?'✓':''}</span><span>${t(TOPICS[x.topic])}</span><small>${x.done?t('fait'):t('à voir')}</small></button></li>`)}</ol>`;
}
/** The guide's own styles, beside the questionnaire's (habitudes.ts): a little wider for the lists of settings. */
export const guideStyles=`
.gd-guide{max-width:640px}
.gd-topics{list-style:none;margin:18px 0 0;padding:0;display:flex;flex-direction:column;gap:8px}
.gd-topics button{display:flex;align-items:center;gap:12px;width:100%;min-height:48px;margin:0;padding:10px 16px;border:1px solid var(--divider-color);border-radius:14px;background:var(--card-background-color);color:inherit;font:inherit;text-align:left;cursor:pointer}
.gd-topics button>span:nth-child(2){flex:1;font-weight:500}
.gd-topics small{color:var(--secondary-text-color);font-size:var(--nw-fs-small,12px)}
.gd-mark{display:inline-grid;place-items:center;flex:none;width:22px;height:22px;box-sizing:border-box;border-radius:50%;border:1.5px dashed var(--secondary-text-color);color:var(--primary-color);font-size:12px;font-weight:700}
.gd-done .gd-mark{border:1.5px solid var(--primary-color)}
.gd-foot{flex-wrap:wrap;gap:8px 14px}
`;
