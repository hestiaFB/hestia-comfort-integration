import {t,currentLocale} from './i18n';
import {LitElement,html,svg,css,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {hassMatters} from './hass-change';
import {property,state} from 'lit/decorators.js';
import charte from './ui/hestia-charte.css';
import {icon} from './ui/icons';

/** The comfort review (review_source.py): the home's review, then one room's sheet. Graded on EN 16798-1.
    Drawn with the common charter (maquettes/maquette-bilan.html, chosen on 6 November 2026): the letters A to E in grey,
    the colour on the gauge — blue within your range, amber outside —, the advice in the charter's banner. */
type Month={month:string};
type Grade={score:number|null;letter:string|null;comfortable:number|null;hours:number};
type Warmth=Grade&{monthly:(Month&{min:number;mean:number;max:number;cold:number;hot:number;comfortable:number;low:number;high:number})[];
 chilly?:number|null;chilly_below?:number;
 coldest:{value:number;month:string}|null;hottest:{value:number;month:string}|null;day:{winter:(number|null)[];summer:(number|null)[];outdoor_winter:(number|null)[];outdoor_summer:(number|null)[]}};
type Humidity=Grade&{dry:number;humid:number;damp?:number;monthly:(Month&{mean:number;humid:number})[]};
type Air=Grade&{split:number[];day:(number|null)[];monthly:(Month&{median:number})[]};
type Advice={key:string;theme:'warmth'|'humidity'|'air';level:'action'|'benefit'|'neutral';share:number|null;below?:number;hour?:number;gap?:number;rooms?:number;room?:string;entry_id?:string};
type RoomReview={entry_id:string;title:string;score:number|null;letter:string|null;themes:{warmth?:Warmth;humidity?:Humidity;air?:Air};advice?:Advice[]};
type ThemeGrade={score:number|null;letter:string|null;rooms?:number};
type ThemeKey='warmth'|'humidity'|'air';
export type Review={version:number;computed_at:string;start:string;outdoor:boolean;home:{score:number|null;letter:string|null;themes:Record<ThemeKey,ThemeGrade>;advice?:Advice[]};rooms:RoomReview[]};
type Hass={callWS:<T>(m:object)=>Promise<T>};

// « 2026-03 » as « mars » (« March »), short or long, in the user's language.
const month=(m:string,style:'short'|'long')=>{const n=Number(m.slice(5,7));return n>=1&&n<=12?new Date(2026,n-1,15).toLocaleDateString(currentLocale(),{month:style}):m;};
const shortMonth=(m:string)=>month(m,'short').replace('.','');
const longMonth=(m:string)=>month(m,'long');
const num=(v:number,d=1)=>v.toLocaleString(currentLocale(),{maximumFractionDigits:d});
const good=(l:string|null|undefined)=>l==='A'||l==='B';
const HEATING=[11,12,1,2,3,4],SUMMER=[6,7,8];
const inMonths=(m:string,months:number[])=>months.includes(Number(m.slice(5,7)));
const avg=(v:number[])=>v.length?v.reduce((a,b)=>a+b,0)/v.length:0;
const THEMES:ThemeKey[]=['warmth','humidity','air'];
const names=()=>({warmth:t('Chaleur'),humidity:t('Humidité'),air:t('Air')});
const ORDER={action:0,benefit:1,neutral:2};
const byLevel=(list:Advice[]|undefined)=>[...(list??[])].sort((a,b)=>ORDER[a.level]-ORDER[b.level]);
const word=(s:number)=>s>=85?t('Très bon'):s>=70?t('Bon dans l’ensemble'):s>=55?t('Correct'):t('À améliorer');

/** One gesture and the measured fact behind it (engine/review.py advice): never a cause the sensors cannot prove. */
function adviceText(a:Advice):[string,string,string]{
 const share=a.share==null?'':num(a.share,0)+' %';
 switch(a.key){
  case 'heat_more':return [t('Chauffez-la davantage l’hiver'),t('Sous {below} °C {share} du temps, de novembre à avril',{share,below:num(a.below??18,0)}),'flame'];
  case 'run_ventilation':return [t('Faites tourner la VMC plus longtemps'),t('Au-dessus de 70 % d’humidité {share} du temps',{share}),'fan'];
  case 'air_daily':return [t('Aérez 10 minutes chaque jour'),t('Au-dessus de 70 % d’humidité {share} du temps',{share}),'window'];
  case 'air_at':return [t('Aérez 10 minutes vers {h} h',{h:a.hour??''}),t('Air à renouveler {share} du temps, surtout vers {h} h',{share,h:a.hour??''}),'window'];
  case 'open_at_night':return [t('L’été, ouvrez en grand la nuit'),t('À l’aube, dehors est {gap} °C plus frais que la maison',{gap:num(a.gap??0)}),'window'];
  case 'add_co2':return [t('Ajoutez un capteur de CO₂ dans une chambre'),!a.rooms?t('L’air n’est mesuré dans aucune pièce'):a.rooms>1?t('L’air n’est mesuré que dans {n} pièces',{n:a.rooms}):t('L’air n’est mesuré que dans {n} pièce',{n:a.rooms}),'air'];
  default:return [a.key,'','info'];
 }
}

export class ComfortReview extends LitElement {
 @property({attribute:false}) hass?:Hass;
 /** The room whose sheet is shown; none for the home's review. */
 @property({attribute:false}) room?:string;
 /** « summary »: the note, the three themes and the advice, for a dashboard card; « page »: the whole review. */
 @property({reflect:true}) mode:'page'|'summary'='page';
 /** The title of the home's review (« Votre maison » in the hub, the card's title on a dashboard). */
 @property() heading?:string;
 /** A card set on one room: no way back to the home's review. */
 @property({type:Boolean}) pinned=false;
 @state() private data?:Review;
 @state() private error='';
 @state() private season:'winter'|'summer'='winter';
 @state() private slide=0;
 @state() private how=false;
 private asked=false;
 static styles=[unsafeCSS(charte),css`
  :host{display:block;container-type:inline-size;font-family:Manrope,var(--ha-font-family-body,Roboto),system-ui,sans-serif;line-height:1.5;color:var(--nw-fg);
   --nw-surface:color-mix(in srgb,var(--nw-fg) 3.5%,var(--nw-bg))}
  .rv{display:grid;gap:16px;min-width:0}
  :host([mode="page"]) .rv{max-width:760px}
  .muted{color:var(--nw-fg2);font-size:var(--nw-fs-text)}
  .notice{margin:0;padding:12px 14px;border-radius:14px;background:var(--nw-surface)}
  .notice button{margin-left:6px}
  /* The title line: the title and one sentence, the note large on the right with its grey letter. */
  .top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
  .top .l{display:grid;gap:6px;justify-items:start;min-width:0}.top h1{display:flex;align-items:center;gap:8px}
  .sub{font-size:var(--nw-fs-small);color:var(--nw-fg2)}
  .grade{display:grid;justify-items:end;flex:none}
  .g-row{display:flex;align-items:center;gap:8px}.grade .nw-temp{line-height:1}
  .g-side{display:grid;justify-items:center;gap:4px}.g-side small{font-size:var(--nw-fs-small);color:var(--nw-fg2);font-weight:500;white-space:nowrap}
  .grade .nw-range{font-size:var(--nw-fs-small);color:var(--nw-fg2);margin-top:4px}
  .lt{display:grid;place-items:center;flex:none;width:28px;height:28px;border-radius:9px;background:color-mix(in srgb,var(--nw-fg) 7%,transparent);
   color:color-mix(in srgb,var(--nw-fg) 78%,transparent);font-size:var(--nw-fs-text);font-weight:700;line-height:1}
  .lt.none{color:var(--nw-fg2);font-weight:500}
  .howto{margin:0;font-size:var(--nw-fs-small);color:var(--nw-fg2);line-height:1.6}
  /* The three themes in small cases; the letter beside the gauge, which carries the colour. */
  .cases{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
  .case{display:grid;gap:2px;align-content:start;padding:12px;border-radius:14px;background:var(--nw-surface);min-width:0}
  .case .nw-value{flex-wrap:wrap;column-gap:4px}
  .cw{font-size:var(--nw-fs-small);color:var(--nw-fg2);line-height:1.35;min-height:2.7em}
  .cm{display:flex;align-items:center;gap:8px;margin-top:6px}.cm .meter{flex:1}
  .cm .lt{width:22px;height:22px;border-radius:7px;font-size:var(--nw-fs-small)}
  .meter{display:block;height:4px;border-radius:2px;background:color-mix(in srgb,var(--nw-fg) 8%,transparent);overflow:hidden}
  .meter i{display:block;height:100%;border-radius:2px;background:color-mix(in oklab,var(--c) 85%,transparent);transform-origin:left;animation:nw-grow .6s var(--nw-ease) both}
  .open{cursor:pointer;display:grid;gap:16px}
  .more{display:flex;align-items:center;justify-content:center;gap:4px;border:0;background:none;padding:2px;font-size:var(--nw-fs-small);font-weight:650;color:var(--nw-fg2);cursor:pointer}
  .more:hover{color:var(--nw-fg)}
  /* Side by side when the review has the room (the hub's page); one column on a card. */
  .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px 20px;align-items:start}
  .nw-band-pic.box svg{width:34px;height:34px}
  /* Sections */
  .part{display:grid;gap:10px;min-width:0}
  .nw-panel{display:grid;gap:12px}.nw-panel .nw-stats{margin-top:0}
  .nw-panel-head h3{margin-right:auto}
  .nw-legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:var(--nw-fs-small);color:var(--nw-fg2)}.nw-legend span{display:inline-flex;align-items:center;gap:6px}
  .nw-legend.col{flex-direction:column;gap:6px}.nw-legend small{font-size:var(--nw-fs-small);color:var(--nw-fg2);margin-top:2px}
  .nw-legend i{display:inline-block;flex:none}
  .k-ok{width:12px;height:10px;border-radius:3px;background:color-mix(in oklab,var(--nw-ok) 80%,transparent)}
  .k-cold{width:12px;height:10px;border-radius:3px;background:color-mix(in oklab,var(--nw-watch) 85%,transparent)}
  .k-hot{width:12px;height:10px;border-radius:3px;background:repeating-linear-gradient(45deg,var(--nw-watch) 0 2px,color-mix(in oklab,var(--nw-watch) 30%,transparent) 2px 4px)}
  .k-mean{width:16px;border-top:2px solid var(--nw-fg)}.k-out{width:16px;border-top:2px dashed var(--nw-fg2)}
  .k-area{width:14px;height:8px;border-radius:2px;background:color-mix(in srgb,var(--nw-fg) 14%,transparent)}
  .k-lim{width:16px;border-top:2px dotted color-mix(in oklab,var(--nw-ok) 80%,var(--nw-fg))}.k-colddot{width:8px;height:8px;border-radius:50%;background:var(--nw-watch)}
  .k-rok{width:10px;height:10px;border-radius:50%;background:color-mix(in oklab,var(--nw-ok) 85%,transparent)}
  .k-rmid{width:10px;height:10px;border-radius:50%;background:color-mix(in oklab,var(--nw-watch) 45%,transparent)}.k-rbad{width:10px;height:10px;border-radius:50%;background:var(--nw-watch)}
  /* Charts */
  svg.chart{width:100%;height:auto;display:block;overflow:visible}
  .tk{font-size:10px;fill:var(--nw-fg2);font-family:Manrope,system-ui,sans-serif}.grid{stroke:color-mix(in srgb,var(--nw-fg) 7%,transparent);stroke-width:1}
  .b-track{fill:color-mix(in srgb,var(--nw-fg) 6%,transparent)}
  .b-ok{fill:color-mix(in oklab,var(--nw-ok) 80%,transparent)}.b-cold,.b-wet{fill:color-mix(in oklab,var(--nw-watch) 85%,transparent)}.b-hot{fill:url(#rv-hatch)}
  .h-bg{fill:color-mix(in oklab,var(--nw-watch) 30%,transparent)}.h-ln{stroke:var(--nw-watch);stroke-width:2.4}
  .bars rect{transform-box:fill-box;transform-origin:bottom;animation:rv-grow-y .7s var(--nw-ease) both}
  @keyframes rv-grow-y{from{transform:scaleY(0)}}
  .c-area{fill:color-mix(in srgb,var(--nw-fg) 9%,transparent)}.c-mean{fill:none;stroke:var(--nw-fg);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
  .c-lim{fill:none;stroke:color-mix(in oklab,var(--nw-ok) 80%,var(--nw-fg));stroke-width:1.3;stroke-dasharray:3 4}
  .c-out{fill:none;stroke:var(--nw-fg2);stroke-width:1.5;stroke-dasharray:4 4}
  .c-dot{fill:var(--nw-fg);stroke:var(--nw-surface);stroke-width:2}.c-dot.cold{fill:var(--nw-watch)}
  .g-top{stop-color:var(--nw-fg);stop-opacity:.16}.g-bot{stop-color:var(--nw-fg);stop-opacity:0}
  .say{margin:0;font-size:var(--nw-fs-small);color:var(--nw-fg2)}
  /* Humidity room by room, the rooms list */
  .hl{display:grid;gap:8px}.hrow{display:grid;grid-template-columns:96px minmax(0,1fr) 30px;column-gap:10px;align-items:center}
  .hrow small{grid-column:2/-1;font-size:var(--nw-fs-small);color:var(--nw-fg2);margin-top:-2px}
  .fn{font-size:var(--nw-fs-small);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .rl{display:grid;padding-top:4px;padding-bottom:4px}
  .rrow{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(40px,1fr) 30px 28px 16px;gap:10px;align-items:center;padding:9px 0;border:0;
   border-bottom:1px solid var(--nw-line-soft);background:none;text-align:left;width:100%;cursor:pointer;color:inherit;font:inherit}
  .rrow:last-child{border-bottom:0}.rrow:hover .rm b{text-decoration:underline}
  .go-c{color:var(--nw-fg2);display:grid}
  .rm{display:grid;min-width:0}.rm b{font-size:var(--nw-fs-text);font-weight:650;line-height:1.3}.rm small{font-size:var(--nw-fs-small);color:var(--nw-fg2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .rs{font-size:var(--nw-fs-text);font-weight:650;text-align:right;font-variant-numeric:tabular-nums}
  /* The air in a ring */
  .airw{display:flex;align-items:center;gap:18px}
  .ring{width:108px;flex:none}.ring circle{fill:none;stroke-width:12}.r-track{stroke:color-mix(in srgb,var(--nw-fg) 6%,transparent)}
  .r-ok{stroke:color-mix(in oklab,var(--nw-ok) 85%,transparent)}.r-mid{stroke:color-mix(in oklab,var(--nw-watch) 45%,transparent)}.r-bad{stroke:var(--nw-watch)}
  .r-v{font-size:16px;font-weight:600;fill:var(--nw-fg);font-family:Manrope,system-ui,sans-serif}
  /* A room's advice, as « À venir » on the room card */
  .tip{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;align-items:start;padding:12px 14px;border-radius:14px;background:color-mix(in oklab,var(--c) 10%,var(--nw-surface))}
  .tip b{display:block;font-size:var(--nw-fs-text);font-weight:650;color:color-mix(in oklab,var(--c) 45%,var(--nw-fg))}.tip small{font-size:var(--nw-fs-small);color:var(--nw-fg2)}
  .ev-ic{display:grid;place-items:center;width:26px;height:26px;border-radius:50%;background:color-mix(in oklab,var(--c) 26%,transparent);color:color-mix(in oklab,var(--c) 40%,var(--nw-fg))}
  .ev-ic svg{width:15px;height:15px}
  .fine{display:flex;align-items:center;gap:8px;margin:0;font-size:var(--nw-fs-small);color:color-mix(in oklab,var(--nw-ok) 50%,var(--nw-fg))}.fine svg{width:14px;height:14px}
  .back{display:inline-flex;align-items:center;gap:6px;justify-self:start;border:0;background:none;padding:0;font-size:var(--nw-fs-small);font-weight:650;color:var(--nw-fg2);cursor:pointer;margin-bottom:-6px}
  .seg2{display:inline-flex;gap:2px;padding:3px;border-radius:999px;background:color-mix(in srgb,var(--nw-fg) 5%,transparent)}
  .seg2 button{border:0;background:none;border-radius:999px;padding:3px 10px;font-size:var(--nw-fs-small);color:var(--nw-fg2);cursor:pointer}
  .seg2 button[aria-pressed="true"]{background:color-mix(in srgb,var(--nw-fg) 12%,transparent);color:var(--nw-fg);font-weight:650}
  @container (max-width:380px){.grade .nw-temp{font-size:44px}.case{padding:10px}}
  @media (prefers-reduced-motion:reduce){.meter i,.bars rect{animation:none}}
 `];
 connectedCallback(){super.connectedCallback();if(this.hass&&!this.asked)void this.load();}
 protected shouldUpdate(changed:PropertyValues){return hassMatters(changed,this.hass);}
 protected updated(){if(this.hass&&!this.asked)void this.load();}
 private async load(){this.asked=true;this.error='';
  try{this.data=await this.hass!.callWS<Review>({type:'hestia_comfort/review'});}
  catch(e){this.error=typeof e==='object'&&e&&'message' in e?String((e as {message:string}).message):t('connexion indisponible');}
 }
 private go(room?:string){this.room=room;this.dispatchEvent(new CustomEvent('review-navigate',{detail:room?'bilan/'+room:'bilan',bubbles:true,composed:true}));}
 private open(){this.dispatchEvent(new CustomEvent('review-open',{bubbles:true,composed:true}));}
 render(){
  if(this.error)return html`<p class="notice" role="alert">${t('Le bilan n’a pas pu être chargé : {error}.',{error:this.error})} <button @click=${()=>this.load()}>${t('Réessayer')}</button></p>`;
  if(!this.data)return html`<p class="muted" role="status">${t('Calcul du bilan sur les douze derniers mois…')}</p>`;
  if(this.mode==='summary')return this.summary();
  if(!this.data.rooms.length)return html`<p class="notice">${t('Aucune pièce Hestia Confort chargée.')}</p>`;
  const room=this.room?this.data.rooms.find(r=>r.entry_id===this.room):undefined;
  return room?this.sheet(room):this.dashboard();
 }

 // ---------- Common pieces ----------
 private lt(l:string|null|undefined){return l?html`<span class="lt" aria-label=${t('Note {letter}',{letter:l})}>${l}</span>`:html`<span class="lt none" aria-label=${t('Pas encore de note')}>–</span>`;}
 private meter(v:number|null|undefined,l:string|null|undefined){return html`<span class="meter" style=${`--c:${l==null?'color-mix(in srgb,var(--nw-fg) 30%,transparent)':good(l)?'var(--nw-ok)':'var(--nw-watch)'}`}><i style=${`width:${v??0}%`}></i></span>`;}
 private grade(score:number|null,letter:string|null,sub:string){
  return html`<div class="grade"><div class="g-row"><span class="nw-temp">${score??'–'}</span><span class="g-side">${this.lt(letter)}<small>/ 100</small></span></div><div class="nw-range">${sub}</div></div>`;
 }
 private top(title:string,sub:string,score:number|null,letter:string|null,under:string){
  return html`<div class="top"><div class="l"><h1 class="nw-title">${title} <button class="nw-info" aria-label=${t('Comment est calculée la note ?')} aria-expanded=${this.how}
    @click=${(e:Event)=>{e.stopPropagation();this.how=!this.how;}}></button></h1><span class="sub">${sub}</span></div>${this.grade(score,letter,under)}</div>
   ${this.how?html`<p class="howto">${this.howText()}</p>`:nothing}`;
 }
 private howText(){return t('Chaque heure est classée selon la norme européenne EN 16798-1 et reçoit des points : 100 en confort élevé, 75 en confort normal, 50 en confort modéré, 0 en dehors. La note est la moyenne, de 0 à 100 : A dès 85, B dès 70, C dès 55, D dès 40, E en dessous. Une pièce est notée sur ce qu’elle mesure, le logement sur la moyenne de ses pièces. Il faut deux semaines de mesures pour noter un thème.');}
 /** The three themes in small cases: the score, one line, the gauge and its letter. */
 private cases(themes:Partial<Record<ThemeKey,{score:number|null;letter:string|null}>>,say:Partial<Record<ThemeKey,string>>){
  const n=names();
  return html`<div class="nw-cases cases">${THEMES.filter(k=>themes[k]).map(k=>{const g=themes[k]!;
   return html`<div class="case"><span class="nw-label">${n[k]}</span><div class="nw-value"><b>${g.score??'–'}</b><span>/ 100</span></div>
    <span class="cw">${g.score==null?t('pas encore de note'):say[k]??''}</span><div class="cm">${this.meter(g.score,g.letter)}${this.lt(g.letter)}</div></div>`;})}</div>`;
 }
 /** The charter's banner: the most pressing piece of advice, the others behind its bars. */
 private band(list:Advice[]){
  if(!list.length)return html`<div class="nw-band nw-glass" data-level="ok"><div class="nw-band-row"><span class="nw-band-pic box">${icon('check')}</span>
   <div class="nw-band-text"><p class="nw-band-kicker">${t('Toute la maison')}</p><p class="nw-band-title">${t('Rien à changer')}</p><p class="nw-band-line">${t('Aucun problème qui dure dans vos pièces.')}</p></div></div></div>`;
  const n=list.length,i=this.slide%n,a=list[i],[title,why,pic]=adviceText(a);
  return html`<div class="nw-band nw-glass" data-level=${a.level}><div class="nw-band-row"><span class="nw-band-pic box">${icon(pic)}</span>
   <div class="nw-band-text"><p class="nw-band-kicker">${a.room??t('Toute la maison')}${n>1?html`<i>${t('{i} sur {n}',{i:i+1,n})}</i>`:nothing}</p>
    <p class="nw-band-title">${title}</p><p class="nw-band-line">${why}</p></div></div>
   ${n>1?html`<div class="nw-band-bars">${list.map((_,k)=>html`<button aria-label=${t('Conseil {n}',{n:k+1})} aria-current=${k===i} @click=${(e:Event)=>{e.stopPropagation();this.slide=k;}}><span></span></button>`)}</div>`:nothing}</div>`;
 }
 private section(title:string,sum:string,body:unknown){return html`<section class="part"><div class="nw-section-head"><h2>${title}</h2><span class="nw-sum">${sum}</span></div>${body}</section>`;}
 private homeLine(){
  const d=this.data!,h=d.home;if(h.score==null)return t('Pas encore de note : il faut deux semaines de mesures');
  const warm=d.rooms.map(r=>r.themes.warmth).filter((w):w is Warmth=>!!w&&w.score!=null);
  const weak=THEMES.filter(k=>h.themes[k].score!=null).sort((a,b)=>h.themes[a].score!-h.themes[b].score!)[0];
  const winterCold=avg(warm.flatMap(w=>w.monthly.filter(m=>inMonths(m.month,HEATING)).map(m=>m.cold)));
  const point=weak==='warmth'?(winterCold>=30?t('l’hiver est le point faible'):t('la chaleur est le point faible')):weak==='humidity'?t('l’humidité est le point faible'):t('l’air est le point faible');
  return `${word(h.score)} · ${point}`;
 }
 private period(){const d=this.data!;return `${longMonth(d.start.slice(0,7))} ${d.start.slice(0,4)} – ${longMonth(d.computed_at.slice(0,7))} ${d.computed_at.slice(0,4)}`;}
 private graded(n:number|undefined){return n==null?'':n>1?t('{n} pièces notées',{n}):t('{n} pièce notée',{n});}

 // ---------- The dashboard card's summary (« Bulletin ») ----------
 private summary(){
  const room=this.room?this.data!.rooms.find(r=>r.entry_id===this.room):undefined;
  if(room)return this.roomSummary(room);
  const h=this.data!.home,say=Object.fromEntries(THEMES.map(k=>[k,this.graded(h.themes[k].rooms)]));
  return html`<div class="rv"><div class="open" @click=${()=>this.open()}>${this.top(this.heading??t('Bilan du logement'),this.homeLine(),h.score,h.letter,t('sur douze mois'))}
   ${this.cases(h.themes,say)}</div>${this.band(byLevel(h.advice))}
   <button class="more" @click=${()=>this.open()}>${t('Voir le bilan complet')} <i class="nw-chev"></i></button></div>`;
 }

 /** One room's summary (6 November): its note, its themes, its own advice; a tap opens its sheet. */
 private roomSummary(r:RoomReview){
  const th=r.themes,share=(v:number|null|undefined,air=false)=>v==null?'':air?t('{n} % air frais',{n:v}):t('{n} % dans votre plage',{n:v});
  const own=byLevel(r.advice);
  return html`<div class="rv"><div class="open" @click=${()=>this.open()}>${this.top(this.heading??r.title,r.score==null?t('Pas encore assez de mesures pour une note'):word(r.score),r.score,r.letter,t('sur douze mois'))}
   ${this.cases(th,{warmth:share(th.warmth?.comfortable),humidity:share(th.humidity?.comfortable),air:share(th.air?.comfortable,true)})}</div>
   ${own.length?this.band(own.map(a=>({...a,room:a.room??r.title}))):html`<p class="fine">${icon('check')}${t('Rien à changer dans cette pièce.')}</p>`}
   <button class="more" @click=${()=>this.open()}>${t('Voir la fiche de la pièce')} <i class="nw-chev"></i></button></div>`;
 }

 // ---------- The home's review ----------
 private dashboard(){
  const d=this.data!,h=d.home,w=this.warmth(),hu=this.humidity(),air=this.air();
  const say={warmth:w.say,humidity:hu.say,air:good(h.themes.air.letter)?t('air sain'):t('à renouveler plus souvent')};
  const rooms=[...d.rooms].sort((a,b)=>(b.score??-1)-(a.score??-1)),n=names();
  const list=html`<div class="nw-panel rl">${rooms.map(r=>html`<button class="rrow" @click=${()=>this.go(r.entry_id)}><div class="rm"><b>${r.title}</b>
   <small>${THEMES.filter(k=>r.themes[k]).map(k=>n[k]).join(' · ')}</small></div>${this.meter(r.score,r.letter)}<b class="rs">${r.score??'–'}</b>${this.lt(r.letter)}<span class="go-c"><i class="nw-chev"></i></span></button>`)}</div>`;
  return html`<div class="rv">${this.top(this.heading??t('Votre maison'),this.period(),h.score,h.letter,h.score==null?t('pas encore de note'):word(h.score).toLowerCase())}
   ${this.band(byLevel(h.advice))}${this.cases(h.themes,say)}
   <div class="grid2">${w.body?this.section(n.warmth,w.say,html`<div class="nw-panel">${w.body}</div>`):nothing}
   ${hu.body?this.section(n.humidity,hu.say,html`<div class="nw-panel">${hu.body}</div>`):nothing}
   ${air?this.section(n.air,say.air,html`<div class="nw-panel">${air}</div>`):nothing}
   ${this.section(t('Vos pièces'),t('{n} pièces · de la meilleure note à la moins bonne',{n:d.rooms.length}),list)}</div>
   <section class="part"><button class="nw-fold-head" aria-expanded=${this.how} @click=${()=>{this.how=!this.how;}}><span class="nw-label">${t('Comment est calculée la note ?')}</span><span class="nw-sum"></span><span class="nw-chevron"><i class="nw-chev"></i></span></button></section></div>`;
 }
 /** Month by month, the mean over the graded rooms of the time too cold, within the range and too hot. */
 private warmth(){
  const warm=this.data!.rooms.map(r=>r.themes.warmth).filter((w):w is Warmth=>!!w&&w.score!=null);
  const months=[...new Set(warm.flatMap(w=>w.monthly.map(m=>m.month)))].sort().slice(-12);
  if(!months.length)return {say:t('pas encore de note'),body:null};
  const at=(m:string,k:'cold'|'comfortable'|'hot')=>avg(warm.flatMap(w=>w.monthly.filter(x=>x.month===m).map(x=>x[k])));
  const winter=avg(months.filter(m=>inMonths(m,HEATING)).map(m=>at(m,'cold'))),summer=avg(months.filter(m=>inMonths(m,SUMMER)).map(m=>at(m,'hot')));
  const say=winter>=30&&summer>=30?t('frais l’hiver, chaud l’été'):winter>=30?t('un peu frais l’hiver'):summer>=30?t('chaud l’été'):t('confortable toute l’année');
  const W=340,H=120,slot=W/months.length,bw=slot*.58,y=(v:number)=>H*(1-v/100);
  const body=html`<svg class="chart" viewBox="0 0 ${W} ${H+20}" role="img" aria-label=${t('Part du temps trop frais, confortable et trop chaud, mois par mois')}>
   <defs><pattern id="rv-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" class="h-bg"/><line x1="0" y1="0" x2="0" y2="5" class="h-ln"/></pattern></defs>
   ${months.map((m,i)=>{const c=at(m,'cold'),o=at(m,'comfortable'),h=at(m,'hot'),x=i*slot+(slot-bw)/2;
    return svg`<g class="bars"><rect class="b-track" x=${x} width=${bw} y="0" height=${H} rx="2"/><rect class="b-cold" x=${x} width=${bw} y=${y(c)} height=${H*c/100} rx="2"/>
     <rect class="b-ok" x=${x} width=${bw} y=${y(c+o)} height=${H*o/100} rx="2"/><rect class="b-hot" x=${x} width=${bw} y=${y(c+o+h)} height=${H*h/100} rx="2"/></g>
     <text class="tk" x=${i*slot+slot/2} y=${H+15} text-anchor="middle">${shortMonth(m)}</text>`;})}</svg>
   <div class="nw-legend"><span><i class="k-ok"></i>${t('dans votre plage')}</span><span><i class="k-cold"></i>${t('trop frais')}</span><span><i class="k-hot"></i>${t('trop chaud')}</span></div>`;
  return {say,body};
 }
 private humidity(){
  const rows=this.data!.rooms.filter(r=>r.themes.humidity?.score!=null).sort((a,b)=>a.themes.humidity!.score!-b.themes.humidity!.score!);
  if(!rows.length)return {say:t('pas encore de note'),body:null};
  const worst=[...rows].sort((a,b)=>b.themes.humidity!.humid-a.themes.humidity!.humid)[0];
  return {say:worst.themes.humidity!.humid>=25?t('{room} souvent trop humide',{room:worst.title}):t('bonne dans les pièces'),
   body:html`<div class="hl">${rows.map(r=>{const h=r.themes.humidity!;return html`<div class="hrow"><span class="fn">${r.title}</span>${this.meter(h.score,h.letter)}<b class="rs">${h.score}</b>
    <small>${t('{n} % trop humide',{n:num(h.humid,0)})}</small></div>`;})}</div>`};
 }
 private ring(split:number[]){
  const r=40,c=2*Math.PI*r,cls=['r-ok','r-mid','r-bad'];let at=0;
  return html`<svg class="ring" viewBox="0 0 100 100" role="img" aria-label=${t('Répartition du temps selon la qualité de l’air')}><circle cx="50" cy="50" r=${r} class="r-track"/>
   ${split.map((p,i)=>{const s=svg`<circle cx="50" cy="50" r=${r} class=${cls[i]} stroke-dasharray=${`${c*p/100} ${c}`} stroke-dashoffset=${c/4-c*at/100}/>`;at+=p;return s;})}
   <text x="50" y="54" text-anchor="middle" class="r-v">${num(split[0],0)} %</text></svg>`;
 }
 private ringLegend(split:number[]){
  return html`<span><i class="k-rok"></i>${t('{n} % très bon',{n:num(split[0],0)})}</span><span><i class="k-rmid"></i>${t('{n} % correct',{n:num(split[1],0)})}</span><span><i class="k-rbad"></i>${t('{n} % à renouveler',{n:num(split[2],0)})}</span>`;
 }
 private air(){
  const rooms=this.data!.rooms.filter(r=>r.themes.air?.score!=null);if(!rooms.length)return null;
  const split=[0,1,2].map(i=>avg(rooms.map(r=>r.themes.air!.split[i]??0))),where=rooms.map(r=>r.title).join(', ');
  return html`<div class="airw">${this.ring(split)}<div class="nw-legend col">${this.ringLegend(split)}
   <small>${rooms.length<this.data!.rooms.length?t('Mesuré dans {rooms} seulement',{rooms:where}):t('Mesuré dans {rooms}',{rooms:where})}</small></div></div>`;
 }

 // ---------- One room's sheet ----------
 private sheet(r:RoomReview){
  const th=r.themes,n=names(),best=this.data!.rooms.filter(x=>x.score!=null).sort((a,b)=>b.score!-a.score!)[0];
  const sub=best?.entry_id===r.entry_id&&this.data!.rooms.length>1?t('la plus confortable de la maison'):r.score==null?t('Pas encore assez de mesures pour une note'):word(r.score);
  const share=(v:number|null|undefined,air=false)=>v==null?'':air?t('{n} % air frais',{n:v}):t('{n} % dans votre plage',{n:v});
  const sum=(g:Grade)=>g.score==null?t('pas encore de note'):`${g.score} / 100`;
  return html`<div class="rv">${this.pinned?nothing:html`<button class="back" @click=${()=>this.go()}><i class="nw-chev" style="--r:180deg"></i>${t('Votre maison')}</button>`}
   ${this.top(this.pinned&&this.heading?this.heading:r.title,sub,r.score,r.letter,t('sur douze mois'))}
   ${this.cases(th,{warmth:share(th.warmth?.comfortable),humidity:share(th.humidity?.comfortable),air:share(th.air?.comfortable,true)})}
   <div class="grid2">${th.warmth?this.section(n.warmth,sum(th.warmth),html`${this.tips(r,'warmth')}${this.warmthSheet(th.warmth)}`):nothing}
   ${th.humidity?this.section(n.humidity,sum(th.humidity),html`${this.tips(r,'humidity')}${this.humiditySheet(th.humidity)}`):nothing}
   ${th.air?this.section(n.air,sum(th.air),html`${this.tips(r,'air')}<div class="nw-panel"><div class="airw">${this.ring(th.air.split)}<div class="nw-legend col">${this.ringLegend(th.air.split)}</div></div></div>`):nothing}</div></div>`;
 }
 /** A theme's advice first; « Rien à changer » in blue when its grade is good and nothing is advised. */
 private tips(r:RoomReview,theme:ThemeKey){
  const list=(r.advice??[]).filter(a=>a.theme===theme);
  if(list.length)return list.map(a=>{const [title,why,pic]=adviceText(a);return html`<div class="tip" style=${`--c:${a.level==='action'?'var(--nw-act)':a.level==='benefit'?'var(--nw-benefit)':'color-mix(in srgb,var(--nw-fg) 30%,transparent)'}`}>
   <span class="ev-ic">${icon(pic)}</span><div><b>${title}</b><small>${why}</small></div></div>`;});
  return good(r.themes[theme]?.letter)?html`<p class="fine">${icon('check')}${theme==='warmth'?t('Rien à changer : la chaleur est bonne'):theme==='humidity'?t('Rien à changer : l’humidité est bonne'):t('Rien à changer : l’air est sain')}</p>`:nothing;
 }
 private warmthSheet(w:Warmth){
  const m=w.monthly.slice(-12);if(!m.length)return nothing;
  const W=340,H=130,n=m.length;
  const lo=Math.floor(Math.min(...m.map(x=>Math.min(x.min,x.low))))-1,hi=Math.ceil(Math.max(...m.map(x=>Math.max(x.max,x.high))))+1;
  const x=(i:number)=>n>1?8+i*(W-16)/(n-1):W/2,y=(v:number)=>H*(hi-v)/(hi-lo);
  const path=(k:'mean'|'low'|'high')=>m.map((p,i)=>`${i?'L':'M'}${x(i)} ${y(p[k])}`).join(' ');
  const area=[...m.map((p,i)=>`${x(i)},${y(p.max)}`),...m.map((p,i)=>`${x(i)},${y(p.min)}`).reverse()].join(' ');
  const ticks:number[]=[];for(let v=Math.ceil(lo/5)*5;v<=hi;v+=5)ticks.push(v);
  const s=this.season,seg=html`<span class="seg2" role="group" aria-label=${t('Saison')}><button aria-pressed=${s==='winter'} @click=${()=>{this.season='winter';}}>${t('Hiver')}</button><button aria-pressed=${s==='summer'} @click=${()=>{this.season='summer';}}>${t('Été')}</button></span>`;
  return html`<div class="nw-panel"><svg class="chart" viewBox="0 0 ${W} ${H+20}" role="img" aria-label=${t('Température mois par mois : mini, moyenne, maxi et votre plage')}>
    ${ticks.map(v=>svg`<line class="grid" x1="0" x2=${W} y1=${y(v)} y2=${y(v)}/><text class="tk" x=${W} y=${y(v)-3} text-anchor="end">${v}°</text>`)}
    <polygon class="c-area" points=${area}/><path class="c-lim" d=${path('low')}/><path class="c-lim" d=${path('high')}/><path class="c-mean" d=${path('mean')}/>
    ${m.map((p,i)=>svg`<circle class=${'c-dot'+(p.cold>=30?' cold':'')} cx=${x(i)} cy=${y(p.mean)} r="3"/><text class="tk" x=${x(i)} y=${H+15} text-anchor="middle">${shortMonth(p.month)}</text>`)}</svg>
   <div class="nw-legend"><span><i class="k-mean"></i>${t('moyenne')}</span><span><i class="k-area"></i>${t('mini–maxi')}</span><span><i class="k-lim"></i>${t('votre plage')}</span><span><i class="k-colddot"></i>${t('trop frais ≥ 30 % du mois')}</span></div>
   <div class="nw-stats" style="--n:3">${w.coldest?html`<div><span>${t('Le plus froid')}</span><b>${num(w.coldest.value)} °C · ${longMonth(w.coldest.month)}</b></div>`:nothing}
    ${w.hottest?html`<div><span>${t('Le plus chaud')}</span><b>${num(w.hottest.value)} °C · ${longMonth(w.hottest.month)}</b></div>`:nothing}
    ${w.chilly!=null?html`<div><span>${t('Sous {n} °C l’hiver',{n:num(w.chilly_below??18,0)})}</span><b>${t('{n} % du temps',{n:num(w.chilly,0)})}</b></div>`:nothing}</div></div>
   <div class="nw-panel"><div class="nw-panel-head"><h3>${t('Une journée type')}</h3>${seg}</div>${this.day(w)}</div>`;
 }
 private day(w:Warmth){
  const s=this.season,ins=s==='winter'?w.day.winter:w.day.summer,outs=s==='winter'?w.day.outdoor_winter:w.day.outdoor_summer;
  const known=ins.filter((v):v is number=>v!=null),out=outs.filter((v):v is number=>v!=null);
  if(!known.length)return html`<p class="say">${s==='winter'?t('Pas encore de mesures cet hiver.'):t('Pas encore de mesures cet été.')}</p>`;
  const lo=Math.floor(Math.min(...known,...out))-1,hi=Math.ceil(Math.max(...known,...out))+1,W=340,H=110;
  const x=(i:number)=>i*W/23,y=(v:number)=>H*(hi-v)/(hi-lo);
  const path=(a:(number|null)[])=>a.map((v,i)=>v==null?'':`${i&&a[i-1]!=null?'L':'M'}${x(i)} ${y(v)}`).join(' ');
  const min=Math.min(...known),max=Math.max(...known);
  return html`<svg class="chart" viewBox="0 0 ${W} ${H+20}" role="img" aria-label=${t('Une journée type, dedans et dehors')}>
    <defs><linearGradient id="rv-day" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="g-top"/><stop offset="1" class="g-bot"/></linearGradient></defs>
    ${ins.every(v=>v!=null)?svg`<path d=${`${path(ins)} L${W} ${H} L0 ${H} Z`} fill="url(#rv-day)"/>`:nothing}<path class="c-out" d=${path(outs)}/><path class="c-mean" d=${path(ins)}/>
    ${[0,6,12,18,23].map(h=>svg`<text class="tk" x=${x(h)} y=${H+15} text-anchor=${h===0?'start':h===23?'end':'middle'}>${t('{n} h',{n:h})}</text>`)}</svg>
   <div class="nw-stats" style="--n:3"><div><span>${t('Dedans')}</span><b>${num(min)} – ${num(max)} °C</b></div><div><span>${t('Le plus frais')}</span><b>${t('vers {n} h',{n:ins.indexOf(min)})}</b></div>
    ${out.length?html`<div><span>${t('Dehors')}</span><b>${num(Math.min(...out))} – ${num(Math.max(...out))} °C</b></div>`:nothing}</div>
   <div class="nw-legend"><span><i class="k-mean"></i>${t('dedans')}</span><span><i class="k-out"></i>${t('dehors')}</span></div>`;
 }
 private humiditySheet(h:Humidity){
  const m=h.monthly.slice(-12);if(!m.length)return nothing;
  const W=340,H=90,slot=W/m.length,bw=slot*.5;
  return html`<div class="nw-panel"><svg class="chart" viewBox="0 0 ${W} ${H+20}" role="img" aria-label=${t('Part du temps trop humide, mois par mois')}>
    ${m.map((p,i)=>{const x=i*slot+(slot-bw)/2,hh=H*p.humid/100;return svg`<g class="bars"><rect class="b-track" x=${x} width=${bw} y="0" height=${H} rx="3"/><rect class=${p.humid>=30?'b-wet':'b-ok'} x=${x} width=${bw} y=${H-hh} height=${hh} rx="3"/></g>
     <text class="tk" x=${i*slot+slot/2} y=${H+15} text-anchor="middle">${shortMonth(p.month)}</text>`;})}</svg>
   <div class="nw-stats" style="--n:3"><div><span>${t('Trop humide')}</span><b>${t('{n} % du temps',{n:num(h.humid,0)})}</b></div><div><span>${t('Très humide')}</span><b>${num(h.damp??0,0)} %</b></div><div><span>${t('Trop sec')}</span><b>${num(h.dry,0)} %</b></div></div></div>`;
 }
}

// The hub's panel and the dashboard card may both load it: defined once.
if(!customElements.get('hestia-comfort-review'))customElements.define('hestia-comfort-review',ComfortReview);
declare global{interface HTMLElementTagNameMap{'hestia-comfort-review':ComfortReview}}
