import {css,html,nothing,svg,type TemplateResult} from 'lit';
import {number} from '../view';
import {icon} from '../ui/icons';
import {scene} from '../ui/scene';
import {pills,type Slide} from './room';
import type {Level} from '../types';
import {t,t as tr,tx,tl,fr,currentLocale} from '../i18n';

/** The home card as a light review: the rotating advice of the rooms, then the last day, week or month. */
export type Period='day'|'week'|'month';
export const PERIODS:[Period,string][]=[['day',fr('Jour')],['week',fr('Semaine')],['month',fr('Mois')]];
type Grade={score:number|null;letter:string|null;share?:number|null};
export interface PeriodRoom {entry_id:string;title:string;heated:boolean;score:number|null;min:number|null;max:number|null;mean:number|null;themes:Record<string,Grade>}
export interface PeriodData {period:Period;start:string;step_hours:number;themes:{comfort:Grade;warmth:Grade;humidity:Grade;air:Grade};rooms:PeriodRoom[];
  outdoor:{min:number;max:number;mean:number}|null;curve:{inside:(number|null)[];outside:(number|null)[]}}
export type Periods={version:number;computed_at:string}&Record<Period,PeriodData>;

export const SECTIONS=['themes','rooms_chart','curve','rooms','details'] as const;
export type Section=typeof SECTIONS[number];
export const SECTION_LABELS:Record<Section,string>={themes:fr('Les 4 thèmes du bilan'),rooms_chart:fr('Températures des pièces'),curve:fr('Courbe dedans et dehors'),
  rooms:fr('Pièces (tuiles)'),details:fr('Détails')};
export const SHOWN_SECTIONS:Section[]=[...SECTIONS];
export const FOLDED_SECTIONS:Section[]=['curve','rooms','details'];

const KIND:Partial<Record<Level,string>>={action:fr('Geste conseillé'),urgent:fr('Attention'),benefit:fr('À saisir')};

/** The banner, the charter's (.nw-band): a glass frame, the gesture's scene (the room's window, VMC or radiator; the pictogram
 *  in a tinted box only when there is none, sensors loading or silent), the room named above the
 *  gesture, the line and how sure the effect is under it; bars to pick another room's advice. */
export function band(o:{slides:Slide[];index:number;pick:(i:number)=>void}):TemplateResult {
  const n=o.slides.length,k=o.index%n,s=o.slides[k],many=n>1,asking=!!KIND[s.level];
  return html`<div class="nw-band nw-glass" data-level=${s.level}>
    <div class="nw-band-row">
      ${s.scene?html`<span class="nw-band-pic" aria-hidden="true">${scene(s.scene)}</span>`:html`<span class="nw-band-pic box">${icon(s.disk??'check')}</span>`}
      <div class="nw-band-text">
        ${asking||many?html`<span class="nw-band-kicker">${asking?tx(s.pill):tx(s.pill??pills[s.level])}${many?html`<i>${t('{i} sur {n}',{i:k+1,n})}</i>`:nothing}</span>`:nothing}
        <p class="nw-band-title">${tx(s.title)}</p>${s.line?html`<p class="nw-band-line">${tl(s.line)}</p>`:nothing}${s.cap?html`<p class="nw-band-note">${tx(s.cap)}</p>`:nothing}
        ${s.learned?html`<p class="nw-band-note">${icon('flask')}<span>${tx(s.learned)}</span></p>`:nothing}
      </div>
    </div>
    ${many?html`<div class="nw-band-bars">${o.slides.map((x,j)=>html`<button type="button" aria-label=${t('Conseil {n} : {title}',{n:j+1,title:tx(x.pill)})} aria-current=${j===k?'true':'false'} @click=${()=>o.pick(j)}><span></span></button>`)}</div>`:nothing}
  </div>`;
}

export function tabs(period:Period,pick:(p:Period)=>void):TemplateResult {
  return html`<div class="nh-tabs" role="group" aria-label=${t('Période')}>${PERIODS.map(([p,label])=>html`<button type="button" aria-pressed=${p===period?'true':'false'} @click=${()=>pick(p)}>${t(label)}</button>`)}</div>`;
}

/** A value not known yet. */
const DASH='—';
const comfortWord=(s:number)=>s>=85?fr('Très bon'):s>=70?fr('Bon dans l’ensemble'):s>=55?fr('Correct'):fr('À améliorer');
const PERIOD_WORD:Record<Period,string>={day:fr('sur 24 h'),week:fr('sur 7 jours'),month:fr('sur 30 jours')};
export const periodWord=(p:Period)=>t(PERIOD_WORD[p]);

/** The review's four themes over the period, in four small cases: the figure said the right way round (time in range),
 *  the engine's letter A to E in grey at the corner, and a gauge carrying the colour: blue when the letter is A or B,
 *  amber below (out of range too often, no gesture asked). The letters keep no colour of their own: the brown and grey
 *  of the old card mixed with the state colours (5 November, card E of maquette-carte-logement.html). */
export function themes(d:PeriodData|undefined,period:Period):TemplateResult {
  const th=d?.themes,none=fr('pas assez de mesures');
  const share=(g:Grade|undefined,flip=false)=>g?.share==null?null:flip?100-g.share:g.share;
  const tiles:[string,Grade|undefined,number|null,string,string,string][]=[
    [fr('Confort'),th?.comfort,th?.comfort.score??null,'/ 100',th?.comfort.score!=null?comfortWord(th.comfort.score):none,none],
    [fr('Chaleur'),th?.warmth,share(th?.warmth),'%',fr('du temps confortable'),fr('aucune pièce chauffée mesurée')],
    // The engine counts the hours too humid: the card says the others, like the three other cases.
    [fr('Humidité'),th?.humidity,share(th?.humidity,true),'%',fr('du temps pas trop humide'),fr('pas de capteur d’humidité')],
    [fr('Air'),th?.air,share(th?.air),'%',fr('du temps air correct'),fr('pas de capteur de CO₂')]];
  return html`<div class="nh-themes" aria-label=${t('Bilan {period}',{period:periodWord(period)})}>${tiles.map(([label,g,value,unit,note,missing])=>{
    const tone=!g?.letter?'none':g.letter==='A'||g.letter==='B'?'ok':'watch';
    return html`<div class="nh-theme" data-tone=${tone}>
    <span class="nw-label">${t(label)}</span>${g?.letter?html`<span class="nh-letter" aria-label=${t('Note {letter}',{letter:g.letter})}>${g.letter}</span>`:nothing}
    <div class="nw-value"><b>${d?value??DASH:'…'}</b>${d&&value!=null?html`<span>${unit}</span>`:nothing}</div>
    <span class="nh-note">${d?t(value!=null?note:missing):t('chargement')}</span>
    <span class="nh-meter" aria-hidden="true"><i style=${`width:${value==null?0:Math.max(0,Math.min(100,value))}%`}></i></span></div>`;})}</div>`;
}

export interface ChartRoom {entry_id:string;title:string;level:Level|'neutral';now:number|null;
 /** This room's comfort range for the season; none for a room left unheated. */ band:[number,number]|null}
export interface ChartFloor {name:string;mean:number|null;rooms:ChartRoom[]}

/** One line per room on a shared scale: the period's range, a dot for now (day) or the mean (week, month). */
export function roomsChart(o:{floors:ChartFloor[];data:PeriodData|undefined;period:Period;outNow:number|null}):TemplateResult {
  const byId=new Map((o.data?.rooms??[]).map(r=>[r.entry_id,r]));
  const lines=o.floors.flatMap(f=>f.rooms.map(r=>{const p=byId.get(r.entry_id),dot=o.period==='day'?r.now??p?.mean??null:p?.mean??r.now;
    const lo=[p?.min,o.period==='day'?r.now:null].filter((x):x is number=>x!=null),hi=[p?.max,o.period==='day'?r.now:null].filter((x):x is number=>x!=null);
    return {...r,dot,min:lo.length?Math.min(...lo):null,max:hi.length?Math.max(...hi):null};}));
  const values=lines.flatMap(l=>[l.min,l.max,l.dot,...(l.band??[])]).filter((x):x is number=>x!=null);
  // The scale's degrees stand out within the range only when every room has the same one.
  const bands=lines.map(l=>l.band).filter((b):b is [number,number]=>!!b),same=bands.length&&bands.every(b=>b[0]===bands[0][0]&&b[1]===bands[0][1])?bands[0]:null;
  const from=Math.floor((values.length?Math.min(...values):18)-0.5),to=Math.ceil((values.length?Math.max(...values):24)+0.5);
  const at=(t:number)=>`${((Math.min(Math.max(t,from),to)-from)/(to-from)*100).toFixed(1)}%`;
  const ticks=[];for(let t=Math.ceil(from/2)*2;t<=to;t+=2)if(t>from)ticks.push(t);
  const bandStyle=(b:[number,number]|null)=>b?`left:${at(b[0])};width:calc(${at(b[1])} - ${at(b[0])})`:'display:none';
  const out=o.data?.outdoor,outValue=o.period==='day'?o.outNow??out?.mean??null:out?.mean??o.outNow;
  const row=(l:typeof lines[number])=>html`<div class="nh-row" data-level=${l.level}>
    <span class="nh-name">${l.title}</span>
    <span class="nh-track"><i class="nh-band-zone" style=${bandStyle(l.band)}></i>
      ${l.min!=null&&l.max!=null?html`<i class="nh-range" style=${`left:${at(l.min)};width:max(4px,calc(${at(l.max)} - ${at(l.min)}))`}></i>`:nothing}
      ${l.dot!=null?html`<i class="nh-dot" style=${`left:${at(l.dot)}`}></i>`:nothing}</span>
    <span class="nh-val">${l.dot!=null?number(Math.round(l.dot*10)/10)+'°':'—'}</span></div>`;
  let i=0;
  return html`<section class="nh-part"><div class="nw-section-head"><h2>${t('Températures')}</h2><span class="nw-sum">${periodWord(o.period)}</span></div>
    <div class="nw-panel nh-chart">
    <div class="nh-row nh-axis"><span></span><span class="nh-track">${ticks.map(t=>html`<em class=${same&&t>=same[0]&&t<=same[1]?'in':''} style=${`left:${at(t)}`}>${t}°</em>`)}</span><span></span></div>
    ${o.floors.map(f=>{const rows=lines.slice(i,i+=f.rooms.length);
      return html`${o.floors.length>1?html`<div class="nh-floor"><span class="nw-label">${f.name}</span><span>${f.mean!=null?number(f.mean)+'°':''}</span></div>`:nothing}${rows.map(row)}`;})}
    ${outValue!=null?html`<div class="nh-row nh-out"><span class="nh-name">${t('Dehors')}</span><span class="nh-out-text">${out?html`${number(out.min)} – ${number(out.max)} °C`:nothing}</span><span class="nh-val">${number(Math.round(outValue*10)/10)}°</span></div>`:nothing}
    <div class="nw-legend nh-legend">${bands.length?html`<span><i class="nh-key-band"></i>${t('votre plage')}</span>`:nothing}<span><i class="nh-key-range"></i>${t('mini–maxi')}</span><span><i class="nh-key-dot"></i>${o.period==='day'?t('maintenant'):t('moyenne')}</span></div>
    </div></section>
  </div>`;
}

/** The home inside (heated rooms' mean) and the outdoor air over the period, the comfort range behind. */
export function curve(d:PeriodData|undefined,period:Period,band:[number,number]|null):TemplateResult {
  if(!d)return html`<p class="nh-empty">${t('Chargement de l’historique…')}</p>`;
  const ins=d.curve.inside,outs=d.curve.outside,all=[...ins,...outs].filter((x):x is number=>x!=null).concat(band??[]);
  if(!ins.some(x=>x!=null))return html`<p class="nh-empty">${t('Pas encore d’historique pour cette période.')}</p>`;
  const W=320,H=120,lo=Math.floor(Math.min(...all))-1,hi=Math.ceil(Math.max(...all))+1,n=Math.max(ins.length-1,1);
  const x=(k:number)=>(k/n*W).toFixed(1),y=(t:number)=>((hi-t)/(hi-lo)*H).toFixed(1);
  const path=(s:(number|null)[])=>s.map((v,k)=>v==null?'':`${k&&s[k-1]!=null?'L':'M'}${x(k)} ${y(v)}`).join(' ');
  const start=new Date(d.start),labels=[0,.25,.5,.75,1].map(f=>{const at=new Date(start.getTime()+f*(ins.length*d.step_hours)*3600000);
    return f===1?tr('maint.'):period==='day'?tr('{n} h',{n:at.getHours()}):period==='week'?at.toLocaleDateString(currentLocale(),{weekday:'short'}):at.toLocaleDateString(currentLocale(),{day:'numeric',month:'short'});});
  return html`<div class="nh-curve">
    <div class="nh-chart-head"><span class="nw-label">${tr('Dedans et dehors')}</span><span class="nh-legend"><span><i class="nh-key-in"></i>${tr('dedans')}</span><span><i class="nh-key-out"></i>${tr('dehors')}</span></span></div>
    <svg viewBox=${`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label=${tr('Température moyenne des pièces et dehors {period}',{period:tr(PERIOD_WORD[period])})}>
      ${band?svg`<rect class="nh-c-band" x="0" width=${W} y=${y(band[1])} height=${Number(y(band[0]))-Number(y(band[1]))}></rect>`:nothing}
      <path class="nh-c-out" d=${path(outs)}></path><path class="nh-c-in" d=${path(ins)}></path></svg>
    <div class="nh-yaxis" aria-hidden="true"><span>${hi}°</span><span>${lo}°</span></div>
    <div class="nh-ticks">${labels.map(l=>html`<span>${l}</span>`)}</div></div>`;
}

export const homeboardStyles=css`
  /* The small formats as card E (6 November): the list's rows, the mini line, the alert's banner, the tile's handle. */
  .nh-rows { display:grid; padding-top:4px; padding-bottom:4px; }
  .nh-line { all:unset; box-sizing:border-box; width:100%; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; align-items:center; padding:9px 0; border-bottom:1px solid var(--nw-line-soft); cursor:pointer; }
  .nh-line:last-child { border-bottom:0; } .nh-line:focus-visible { outline:2px solid var(--nw-accent); outline-offset:2px; border-radius:8px; }
  .nh-row-n { display:grid; min-width:0; } .nh-row-n b { font-size:var(--nw-fs-text); font-weight:650; line-height:1.3; }
  .nh-row-n small { font-size:var(--nw-fs-small); color:var(--nw-fg2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nh-line:is([data-level="action"],[data-level="urgent"]) .nh-row-n small { font-weight:600; color:color-mix(in oklab, var(--nw-act) 45%, var(--nw-fg)); }
  .nh-row-t { font-size:var(--nw-fs-text); font-weight:650; font-variant-numeric:tabular-nums; } .nh-row-t small { font-weight:500; color:var(--nw-fg2); }
  .nh-mini { display:flex; align-items:center; gap:12px; padding:10px 14px; }
  .nh-mini-pic { padding:0; background:none; border:0; } .nh-mini-pic .nw-band-pic.box { width:36px; height:36px; border-radius:9px; }
  .nh-mini-pic .nw-band-pic.box svg { width:20px; height:20px; }
  .nh-mini-text { display:grid; flex:1; min-width:0; } .nh-mini-text b { font-size:var(--nw-fs-text); font-weight:650; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nh-mini-t { font-size:var(--nw-fs-case); font-weight:300; font-variant-numeric:tabular-nums; } .nh-mini-t small { font-size:var(--nw-fs-text); color:var(--nw-fg2); }
  .nh-alert { padding:12px; } .nh-alert .nw-band-title { font-size:var(--nw-fs-case); }
  .nh-body > .nc-handle { align-self:center; }
  /* The card: the title line (title, pill, outside temperature), the banner, then the review — card E, 5 November. */
  .nh-body { padding:18px; display:flex; flex-direction:column; gap:16px; }
  .nh-top { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
  .nh-top-l { display:grid; gap:8px; justify-items:start; min-width:0; }
  .nh-top-l .nw-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:100%; }
  .nh-top .nc-level { margin:0; }
  .nh-part { display:grid; gap:10px; min-width:0; }
  .nh-part .nw-section-head .nh-tabs { margin-left:auto; }
  /* The banner is the charter's (.nw-band, hestia-charte.css, 5 November). */
  /* The room card's halo: the advice's colour, soft from the top right, behind the title line and the banner only. */
  .nh-hero { position:relative; isolation:isolate; z-index:0; display:flex; flex-direction:column; gap:16px; }
  /* The light reaches the card's edges, past the body's padding. */
  .nh-hero > .nc-b-light { left:-18px; right:-18px; top:-18px; }
  /* Day, week, month: the charter's small switch. */
  .nh-tabs { display:inline-flex; gap:2px; padding:3px; border-radius:var(--nw-radius-pill); background:var(--nw-surface); }
  .nh-tabs button { min-height:0; padding:4px 11px; border:0; border-radius:var(--nw-radius-pill); background:none; color:var(--nw-fg2); font:inherit; font-size:var(--nw-fs-small); cursor:pointer; }
  .nh-tabs button[aria-pressed="true"] { background:color-mix(in srgb, var(--nw-fg) 12%, transparent); color:var(--nw-fg); font-weight:650; }
  /* The four themes: small cases, the letter neutral at the corner, the colour on the gauge. */
  .nh-themes { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:8px; }
  @container (min-width:560px) { .nh-themes { grid-template-columns:repeat(4, minmax(0, 1fr)); } }
  .nh-theme { --c:var(--nw-fg2); position:relative; display:grid; gap:2px; align-content:start; min-width:0; padding:12px 14px; border-radius:14px; background:var(--nw-surface); }
  .nh-theme[data-tone="ok"] { --c:var(--nw-ok); } .nh-theme[data-tone="watch"] { --c:var(--nw-watch); }
  .nh-theme .nw-value b { font-size:var(--nw-fs-case); font-weight:600; letter-spacing:-.015em; line-height:1.2; }
  .nh-note { font-size:var(--nw-fs-small); color:var(--nw-fg2); }
  .nh-letter { position:absolute; top:10px; right:10px; display:grid; place-items:center; width:30px; height:30px; border-radius:9px;
    background:color-mix(in srgb, var(--nw-fg) 7%, transparent); color:color-mix(in srgb, var(--nw-fg) 78%, transparent); font-size:var(--nw-fs-text); font-weight:700; line-height:1; }
  .nh-meter { display:block; height:4px; margin-top:8px; border-radius:2px; overflow:hidden; background:color-mix(in srgb, var(--nw-fg) 8%, transparent); }
  .nh-meter i { display:block; height:100%; border-radius:2px; background:color-mix(in oklab, var(--c) 85%, transparent); transform-origin:left; animation:nw-grow .6s var(--nw-ease) both; }
  @media (prefers-reduced-motion:reduce) { .nh-meter i { animation:none; } }
  .nh-chart, .nh-curve { display:flex; flex-direction:column; gap:2px; }
  .nh-chart-head { display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap; padding-bottom:6px; }
  .nh-chart-head .nh-legend { margin-top:0; display:flex; gap:12px; font-size:var(--nw-fs-label); color:var(--nw-fg2); }
  .nh-chart-head .nh-legend span { display:flex; align-items:center; gap:5px; }
  .nh-chart { display:flex; flex-direction:column; gap:2px; }
  .nh-legend { margin-top:8px; }
  .nh-legend i { display:inline-block; }
  .nh-key-range { width:14px; height:4px; border-radius:2px; background:color-mix(in srgb, var(--nw-fg) 40%, transparent); }
  .nh-key-dot { width:8px; height:8px; border-radius:50%; background:var(--nw-fg); }
  .nh-key-band { width:14px; height:8px; border-radius:4px; background:color-mix(in oklab, var(--nw-ok) 40%, transparent); }
  .nh-key-in, .nh-key-out { width:14px; height:3px; border-radius:2px; background:var(--nw-fg); } .nh-key-out { background:color-mix(in srgb, var(--nw-fg) 45%, transparent); }
  .nh-row { --c:var(--nw-ok); display:grid; grid-template-columns:minmax(86px, 30%) 1fr 44px; gap:10px; align-items:center; min-height:24px; }
  .nh-row[data-level="action"], .nh-row[data-level="urgent"] { --c:var(--nw-act); } .nh-row[data-level="benefit"] { --c:var(--nw-benefit); }
  .nh-row[data-level="neutral"] { --c:var(--nw-fg2); }
  .nh-name { font-size:var(--nw-fs-small); font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nh-val { font-size:var(--nw-fs-small); font-weight:650; text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
  .nh-track { position:relative; height:16px; }
  .nh-track i { position:absolute; }
  .nh-track::before { content:''; position:absolute; left:0; right:0; top:7px; height:2px; border-radius:1px; background:color-mix(in srgb, var(--nw-fg) 9%, transparent); }
  .nh-band-zone { top:2px; height:12px; border-radius:6px; background:color-mix(in oklab, var(--nw-ok) 34%, transparent); }
  .nh-range { top:6px; height:4px; border-radius:2px; background:color-mix(in srgb, var(--nw-fg) 40%, transparent); }
  .nh-dot { top:3px; width:10px; height:10px; margin-left:-5px; border-radius:50%; background:color-mix(in oklab, var(--c) 75%, var(--nw-fg)); box-shadow:0 0 0 2px var(--nw-surface); }
  .nh-axis { min-height:16px; } .nh-axis .nh-track::before { display:none; }
  .nh-axis em { position:absolute; transform:translateX(-50%); font-style:normal; font-size:var(--nw-fs-label); color:var(--nw-fg2); }
  .nh-axis em.in { color:var(--nw-fg); }
  .nh-floor { display:flex; justify-content:space-between; padding:8px 0 2px; font-size:var(--nw-fs-label); color:var(--nw-fg2); }
  .nh-out { margin-top:6px; padding-top:6px; border-top:1px dashed var(--nw-line); }
  /* Outside in words: the scale is the rooms', a winter outside would sit flat against its edge (labo, 5 November). */
  .nh-out-text { font-size:var(--nw-fs-small); color:var(--nw-fg2); font-variant-numeric:tabular-nums; }
  .nh-curve { position:relative; }
  .nh-curve svg { width:100%; height:120px; display:block; overflow:visible; }
  .nh-yaxis { position:absolute; right:0; top:28px; height:120px; display:flex; flex-direction:column; justify-content:space-between; font-size:var(--nw-fs-label); opacity:.6; pointer-events:none; }
  .nh-c-band { fill:color-mix(in oklab, var(--nw-ok) 24%, transparent); }
  .nh-c-in, .nh-c-out { fill:none; stroke-linejoin:round; vector-effect:non-scaling-stroke; }
  .nh-c-in { stroke:var(--nw-ok); stroke-width:2.5; } .nh-c-out { stroke:color-mix(in srgb, var(--nw-fg) 45%, transparent); stroke-width:2; }
  .nh-ticks { display:flex; justify-content:space-between; font-size:var(--nw-fs-label); opacity:.7; }
  .nh-empty { margin:0; font-size:var(--nw-fs-small); opacity:.75; }
  .nh-more { display:flex; flex-direction:column; gap:18px; padding-top:6px; }
`;
