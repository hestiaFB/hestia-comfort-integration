import {html,nothing,type TemplateResult} from 'lit';
import {listSection,listRow,segmented,noteBox,pageHead,t,fr,type NkAction} from './socle/ui';
import type {Foyer,Glazing} from './foyer';

/** What the sensors do not see (niak-comfort/docs/HABITUDES-FOYER.md, validated by Frank on 5 November): the manual
 *  shutters, the empty weekdays, the laundry, the weekend's waking up; and « Votre maison », what each window and each
 *  room takes when it does not set its own. Every answer is a household setting with its default (foyer.py). */
export type ShutterHabit='fermes'|'ouverts'|'variable';
export type Question='vitrage'|'volets_absence'|'volets_nuit'|'volets_ete'|'journee_vide'|'linge_pieces'|'fin_weekend';

export interface HabitsContext {
 foyer:Foyer;busy:boolean;
 /** The rooms with a manual shutter: the shutters' questions are asked only when there is one. */
 manual:string[];
 /** What says the absences (the alarm's name), or null: the weekday question is asked only without it. */
 absences:string|null;
 rooms:{entry_id:string;title:string}[];
 change:(next:Foyer)=>void;
 /** Opens the questionnaire: « Vos habitudes » shows only it while nothing is answered. */
 quiz?:()=>void;
}

const GLAZING_WORDS:[Glazing,string][]=[['simple',fr('Simple')],['double',fr('Double')],['triple',fr('Triple')]];
const hm=(s:string)=>{const [h,m]=s.split(':');return m==='00'?t('{h} h',{h:Number(h)}):t('{h} h {m}',{h:Number(h),m});};
const VOLETS=fr('Les volets à la main');

interface Asked {key:Question;group:string;title:string;short:string;why:string;choices:[string,string][];
 /** The answer shown: what is set, else the default once the question was answered. */
 value:(f:Foyer,seen:boolean)=>string|undefined;answer:(f:Foyer,v:string)=>Foyer}

/** The questions, in order; only those that mean something for this home. */
export function questions(o:HabitsContext):Asked[]{
 const shutters=(key:'volets_absence'|'volets_nuit'|'volets_ete',title:string,short:string,why:string,last:string):Asked=>({key,group:t(VOLETS),title,short,why,
  choices:[['fermes',t('Fermés')],['ouverts',t('Ouverts')],['variable',last]],value:(f,seen)=>f[key]??(seen?'variable':undefined),
  answer:(f,v)=>{const n={...f};if(v==='variable')delete n[key];else n[key]=v as ShutterHabit;return n;}});
 const list:Asked[]=[
  {key:'vitrage',group:t('Les fenêtres'),title:t('Vos fenêtres sont en…'),short:t('Vitrage'),why:t('Hestia-FB saura quand vos vitres s’embuent, et ce que le soleil apporte.'),
   choices:[['simple',t('Simple vitrage')],['double',t('Double vitrage')],['triple',t('Triple vitrage')],['variable',t('Ça dépend des fenêtres')]],
   value:(f,seen)=>f.vitrage??(seen?'variable':undefined),answer:(f,v)=>{const n={...f};if(v==='variable')delete n.vitrage;else n.vitrage=v as Glazing;return n;}}];
 if(o.manual.length)list.push(
  shutters('volets_absence',t('Quand vous partez, les volets restent…'),t('Quand vous partez'),t('Hestia-FB saura que le soleil n’entre pas pendant vos absences.'),t('Ça dépend')),
  shutters('volets_nuit',t('La nuit, les volets sont…'),t('La nuit'),t('Hestia-FB comptera la chaleur qu’ils gardent jusqu’au matin.'),t('Ça dépend des pièces')),
  shutters('volets_ete',t('L’été, aux heures chaudes, les volets côté soleil sont…'),t('L’été, aux heures chaudes'),t('Hestia-FB ne vous rappellera de les fermer que si besoin.'),t('Ça dépend')));
 if(!o.absences)list.push({key:'journee_vide',group:t('La maison'),title:t('En semaine, dans la journée, la maison est…'),short:t('En semaine, dans la journée'),
  why:t('Pas de conseil quand personne n’est là pour le suivre.'),choices:[['vide',t('Souvent vide')],['occupee',t('Souvent occupée')],['variable',t('Ça change')]],
  value:(f,seen)=>f.journee_vide?'vide':seen?'variable':undefined,
  answer:(f,v)=>{const n={...f};if(v==='vide')n.journee_vide=f.journee_vide??{de:'08:30',a:'17:30'};else delete n.journee_vide;return n;}});
 list.push({key:'linge_pieces',group:t('La maison'),title:t('L’hiver, le linge sèche…'),short:t('L’hiver, le linge sèche'),why:t('Hestia-FB reconnaîtra l’humidité du linge, et dira quand aérer.'),
  choices:[['dehors',t('Dehors ou au sèche-linge')],['dedans',t('Dans la maison')],['deux',t('Les deux, selon le temps')]],
  value:(f,seen)=>f.linge_pieces?.length?(f.linge_parfois?'deux':'dedans'):f.linge_pieces||seen?'dehors':undefined,
  // « Dans la maison » or « Les deux » (Frank, 5 November: outside when it is fine, inside otherwise): the rooms are then
  // chosen just under it.
  answer:(f,v)=>{const n:Foyer={...f};delete n.linge_parfois;
   if(v==='dehors')return {...n,linge_pieces:[]};
   return {...n,linge_pieces:f.linge_pieces?.length?f.linge_pieces:o.rooms.slice(0,1).map(r=>r.entry_id),...(v==='deux'?{linge_parfois:true}:{})};}},
  {key:'fin_weekend',group:t('La maison'),title:t('Le week-end, vous vous levez…'),short:t('Le week-end, le lever'),why:t('Ni conseil ni lumière avant votre lever.'),
   choices:[['pareil',t('Comme en semaine')],['tard',t('Plus tard')]],value:(f,seen)=>f.sommeil?.fin_weekend?'tard':seen||f.sommeil?'pareil':undefined,
   answer:(f,v)=>{const s={debut:f.sommeil?.debut??'22:00',fin:f.sommeil?.fin??'07:00'} as NonNullable<Foyer['sommeil']>;if(v==='tard')s.fin_weekend=f.sommeil?.fin_weekend??'09:00';return {...f,sommeil:s};}});
 return list;
}

const seen=(f:Foyer,key:Question)=>(f.repondu??[]).includes(key);
/** The questions not answered yet (« Ça dépend » or « Je ne sais pas » count: a question is never asked twice). */
export function unanswered(o:HabitsContext):number{return questions(o).filter(q=>!seen(o.foyer,q.key)).length;}
/** Where the questionnaire opens: its first question not answered yet (the first one when all are). */
export function firstUnanswered(o:HabitsContext):number{const i=questions(o).findIndex(q=>!seen(o.foyer,q.key));return i<0?0:i;}
const noted=(f:Foyer,key:Question):Foyer=>({...f,repondu:[...new Set([...(f.repondu??[]),key])]});

/** What a choice opens: the empty hours, the laundry's rooms, the weekend's waking hour. */
function extra(o:HabitsContext,key:Question):TemplateResult|typeof nothing{
 const f=o.foyer,change=o.change;
 const time=(label:string,value:string,set:(v:string)=>void)=>html`<input type="time" aria-label=${label} .value=${value} ?disabled=${o.busy} @change=${(e:Event)=>{const v=(e.target as HTMLInputElement).value;if(v)set(v);}}>`;
 if(key==='journee_vide'&&f.journee_vide){const d=f.journee_vide;
  return html`<span class="nk-unit">${t('De')}</span>${time(t('De'),d.de,v=>change({...f,journee_vide:{...d,de:v}}))}<span class="nk-unit">${t('à')}</span>${time(t('À'),d.a,v=>change({...f,journee_vide:{...d,a:v}}))}`;}
 if(key==='linge_pieces'&&f.linge_pieces?.length){const chosen=f.linge_pieces;
  return html`<span class="nk-chips">${o.rooms.map(r=>html`<button type="button" class="nk-chip" aria-pressed=${String(chosen.includes(r.entry_id))} ?disabled=${o.busy}
   @click=${()=>change({...f,linge_pieces:chosen.includes(r.entry_id)?chosen.filter(x=>x!==r.entry_id):[...chosen,r.entry_id]})}>${r.title}</button>`)}</span>`;}
 if(key==='fin_weekend'&&f.sommeil?.fin_weekend){const s=f.sommeil;return html`<span class="nk-unit">${t('Vers')}</span>${time(t('Lever du week-end'),s.fin_weekend!,v=>change({...f,sommeil:{...s,fin_weekend:v}}))}`;}
 return nothing;
}

function row(o:HabitsContext,q:Asked):TemplateResult{
 const more=extra(o,q.key);
 return listRow({label:q.short,sub:q.why,value:html`${segmented(q.title,q.choices,q.value(o.foyer,seen(o.foyer,q.key)),v=>o.change(noted(q.answer(o.foyer,v),q.key)),o.busy)}${more===nothing?nothing:html`<span class="nk-row-more">${more}</span>`}`});
}

/** Réglages › « Vos habitudes »: the same questions, in rows, to change one's mind later. */
export function habitsSection(o:HabitsContext):TemplateResult{
 const asked=questions(o),rows:unknown[]=[],shutters=asked.filter(q=>q.group===t(VOLETS));
 // One or the other (Frank, 5 November, as in Weather's Station › Emplacement): nothing answered yet, only the card that
 // opens the questionnaire; once one answer is given, the rows.
 const left=unanswered(o);
 if(o.quiz&&left===asked.length)return listSection(t('Vos habitudes'),[listRow({name:t('Vos habitudes'),label:html`<strong>${t('Vos habitudes')}</strong>`,
  sub:left>1?t('{n} questions, une minute : ce que les capteurs ne voient pas.',{n:left}):t('Une question : ce que les capteurs ne voient pas.'),go:o.quiz})]);
 if(shutters.length)rows.push(listRow({label:html`<b>${t(VOLETS)}</b>`,sub:o.manual.join(', ')}),...shutters.map(q=>row(o,q)));
 rows.push(listRow({label:html`<b>${t('La maison')}</b>`}));
 if(o.absences)rows.push(listRow({label:t('En semaine, dans la journée'),value:noteBox(t('Lu sur {name}.',{name:o.absences}),t('Hestia-FB sait quand la maison est vide : rien à répondre.'))}));
 rows.push(...asked.filter(q=>q.key==='journee_vide'||q.key==='linge_pieces').map(q=>row(o,q)));
 return listSection(t('Vos habitudes'),rows,{help:html`<p>${t('Ce que les capteurs ne voient pas. Hestia-FB s’en sert pour apprendre chaque pièce et pour choisir ses conseils.')}</p><p>${t('« Ça dépend » laisse Hestia-FB faire la moyenne de ce qu’il observe. Un volet motorisé est lu tout seul : ces questions ne le concernent pas.')}</p>`});
}

/** The week-end's waking up, in « Sommeil ». */
export function weekendRow(o:HabitsContext):TemplateResult{return row(o,questions(o).find(x=>x.key==='fin_weekend')!);}

export interface HouseUses {glazing:string;shutter:string;rooms:string;thermostat:string}
/** Réglages › « Votre maison »: what each window and each room takes when it does not set its own (« Comme la maison »). */
export function houseSection(o:HabitsContext&{uses:HouseUses}):TemplateResult{
 const f=o.foyer,set=(next:Foyer)=>o.change(next);
 const pick=(label:string,value:string|undefined,options:[string,string][],change:(v:string)=>void)=>html`<select aria-label=${label} ?disabled=${o.busy} @change=${(e:Event)=>change((e.target as HTMLSelectElement).value)}>${options.map(([v,l])=>html`<option value=${v} ?selected=${(value??'')===v}>${l}</option>`)}</select>`;
 const without=(key:keyof Foyer,v:unknown)=>{const n={...f} as Record<string,unknown>;if(v===undefined||v==='')delete n[key];else n[key]=v;return n as Foyer;};
 const plage={minimum:20,maximum:24,summer_maximum:26,...(f.plage??{})};
 const degree=(key:'minimum'|'maximum'|'summer_maximum',label:string,values:number[])=>pick(label,String(plage[key]),values.map(v=>[String(v),String(v).replace('.',',')+' °C']),v=>set({...f,plage:{...(f.plage??{}),[key]:Number(v)}}));
 return listSection(t('Votre maison'),[
  listRow({label:t('Vitrage'),sub:o.uses.glazing,value:segmented(t('Vitrage'),GLAZING_WORDS.map(([v,l])=>[v,t(l)] as [Glazing,string]),f.vitrage??'double',v=>set(noted({...f,vitrage:v},'vitrage')),o.busy)}),
  listRow({label:t('Volets'),sub:o.uses.shutter,value:segmented(t('Volets'),[['none',t('Aucun')],['manual',t('À la main')],['connected',t('Motorisé')]],f.volet??'none',v=>set(without('volet',v==='none'?undefined:v)),o.busy)}),
  listRow({label:t('Hauteur sous plafond'),sub:o.uses.rooms,value:pick(t('Hauteur sous plafond'),f.hauteur!=null?String(f.hauteur):'',[['',t('Je ne sais pas')],...[2.4,2.5,2.6,2.7,2.8,3].map(v=>[String(v),v.toFixed(2).replace('.',',')+' m'] as [string,string])],v=>set(without('hauteur',v===''?undefined:Number(v))))}),
  listRow({label:t('Murs du dehors'),sub:o.uses.rooms,value:pick(t('Murs du dehors'),f.murs,[['',t('Je ne sais pas')],['heavy',t('Pierre, béton, brique')],['wood',t('Bois')]],v=>set(without('murs',v||undefined)))}),
  listRow({label:t('Isolation des murs'),value:pick(t('Isolation des murs'),f.isolation??'moyenne',[['bien',t('Bien isolés')],['moyenne',t('Moyennement isolés')],['peu',t('Peu ou pas isolés')]],v=>set(without('isolation',v==='moyenne'?undefined:v)))}),
  // Each value named above its list (Frank, 5 November: « on ne sait pas à quoi correspondent les plages »).
  listRow({label:t('Plage de confort'),sub:html`${t('La température visée dans chaque pièce.')}<br>${t('Le thermostat de la pièce la remplace, s’il est renseigné.')}${o.uses.thermostat?html`<br>${o.uses.thermostat}`:nothing}`,
   value:html`<span class="hb-ranges">${([['minimum',t('Minimum'),[16,17,18,19,19.5,20,20.5,21,22]],['maximum',t('Maximum en hiver'),[21,22,23,24,25,26]],['summer_maximum',t('Maximum en été'),[24,25,26,27,28]]] as const)
    .map(([key,label,values])=>html`<label class="hb-range"><span>${label}</span>${degree(key,label,[...values])}</label>`)}</span>`})],
  {help:html`<p>${t('Chaque pièce et chaque fenêtre reprend ces valeurs, et les montre déjà choisies : « Comme la maison ». Une pièce ou une fenêtre qui diffère se change sur place, dans sa page.')}</p><p>${t('Changer une valeur ici change toutes celles qui sont « Comme la maison ».')}</p>`});
}

/** The questionnaire (Vue d'ensemble › À améliorer › « Vos habitudes »): one question a screen, then « C'est noté ». */
export function quizScreen(o:HabitsContext&{step:number;go:(step:number)=>void;back:NkAction;settings:()=>void}):TemplateResult{
 const list=questions(o),f=o.foyer;
 if(o.step>=list.length)return html`${pageHead({back:o.back,title:t('Vos habitudes')})}
  <div class="hb-quiz"><div class="hb-done"><span class="hb-mark" aria-hidden="true">✓</span><h2>${t('C’est noté.')}</h2><p class="muted">${t('Hestia-FB s’en sert dès cette nuit.')}<br>${t('Tout se change dans Réglages.')}</p></div>
  ${listSection('',list.map(q=>listRow({label:q.short,value:answerText(o,q)})))}
  <p class="hb-foot"><span class="hb-sp"></span><button type="button" @click=${o.settings}>${t('Voir dans Réglages')}</button><button type="button" class="primary" @click=${o.back.onClick}>${t('Terminer')}</button></p></div>`;
 const q=list[o.step],value=q.value(f,seen(f,q.key)),more=extra(o,q.key);
 return html`${pageHead({back:o.back,title:t('Vos habitudes')})}
 <div class="hb-quiz"><p class="hb-step">${q.group} · ${t('{n} sur {total}',{n:o.step+1,total:list.length})}</p>
 <div class="hb-progress" role="progressbar" aria-valuemin="0" aria-valuemax=${list.length} aria-valuenow=${o.step}><i style=${`width:${o.step/list.length*100}%`}></i></div>
 <h2 class="hb-title">${q.title}</h2><p class="muted">${q.why}</p>${q.group===t(VOLETS)?html`<p class="hb-rooms">${o.manual.join(', ')}</p>`:nothing}
 <div class="hb-choices" role="group" aria-label=${q.title}>${q.choices.map(([v,l])=>html`<button type="button" class="hb-choice" aria-pressed=${String(value===v)} ?disabled=${o.busy} @click=${()=>o.change(noted(q.answer(f,v),q.key))}>${l}</button>`)}</div>
 ${more===nothing?nothing:html`<div class="hb-more">${q.key==='linge_pieces'?html`<span>${t('Dans quelle pièce ?')}</span>`:nothing}${more}</div>`}
 <p class="hb-foot">${o.step?html`<button type="button" class="link" @click=${()=>o.go(o.step-1)}>‹ ${t('Précédent')}</button>`:nothing}<span class="hb-sp"></span>
  <button type="button" class="link" ?disabled=${o.busy} @click=${()=>{if(!seen(f,q.key))o.change(noted(f,q.key));o.go(o.step+1);}}>${t('Je ne sais pas')}</button>
  <button type="button" class="primary" ?disabled=${o.busy||value===undefined} @click=${()=>o.go(o.step+1)}>${o.step===list.length-1?t('Terminer'):t('Suivant')}</button></p></div>`;
}
function answerText(o:HabitsContext,q:Asked):string{const f=o.foyer,v=q.value(f,seen(f,q.key));
 if(q.key==='journee_vide'&&f.journee_vide)return t('Souvent vide · de {de} à {a}',{de:hm(f.journee_vide.de),a:hm(f.journee_vide.a)});
 if(q.key==='linge_pieces'&&f.linge_pieces?.length){const pieces=f.linge_pieces.map(id=>o.rooms.find(r=>r.entry_id===id)?.title??id).join(', ');
  return f.linge_parfois?t('Les deux · {pieces}',{pieces}):pieces;}
 if(q.key==='fin_weekend'&&f.sommeil?.fin_weekend)return t('Plus tard · vers {h}',{h:hm(f.sommeil.fin_weekend)});
 return q.choices.find(c=>c[0]===v)?.[1]??'—';}

export const habitsStyles=`
.hb-quiz{max-width:520px;margin:8px auto 0}
.hb-step{margin:0;font-size:var(--nw-fs-label,11px);font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--secondary-text-color)}
.hb-progress{height:4px;border-radius:99px;background:var(--divider-color);overflow:hidden;margin:10px 0 24px}
.hb-progress i{display:block;height:100%;background:var(--primary-color);transition:width .3s cubic-bezier(.2,.8,.2,1)}
.hb-title{font-size:var(--nw-fs-case,21px);font-weight:650;letter-spacing:-.02em;line-height:1.3;margin:0 0 6px}
.hb-rooms{margin:-6px 0 14px;font-size:var(--nw-fs-small,12px);color:var(--secondary-text-color)}
.hb-choices{display:flex;flex-direction:column;gap:10px;margin-top:16px}
.hb-choice{display:flex;align-items:center;justify-content:space-between;min-height:56px;padding:12px 18px;border:1px solid var(--divider-color);border-radius:16px;background:var(--card-background-color);color:inherit;cursor:pointer;text-align:left;font:inherit;font-weight:500}
.hb-choice[aria-pressed="true"]{border-color:var(--primary-color);font-weight:650}
.hb-choice[aria-pressed="true"]::after{content:"✓";color:var(--primary-color);font-weight:700}
.hb-more{margin-top:14px;padding:12px 16px;border:1px solid var(--divider-color);border-radius:16px;display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.hb-foot{display:flex;align-items:center;gap:14px;margin-top:24px}.hb-sp{flex:1}
.hb-scale{display:inline-flex;flex-direction:column;gap:2px;min-width:180px}.hb-scale input{width:100%}
.hb-ends{display:flex;justify-content:space-between;font-size:var(--nw-fs-small,12px);color:var(--secondary-text-color)}
.hb-ranges{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:10px}
.hb-range{display:inline-flex;flex-direction:column;gap:4px;font-size:var(--nw-fs-small,12px);color:var(--secondary-text-color)}
.hb-done{text-align:center;padding:24px 0}.hb-done h2{margin:6px 0}
.hb-mark{display:inline-grid;place-items:center;width:56px;height:56px;border-radius:50%;border:1.5px solid var(--primary-color);color:var(--primary-color);font-size:var(--nw-fs-case,21px)}
.nk-row-more{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:6px;justify-content:flex-end}
`;
