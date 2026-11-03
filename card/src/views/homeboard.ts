import {css,html,nothing,svg,type TemplateResult} from 'lit';
import {number} from '../view';
import {icon} from '../ui/icons';
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

/** The banner: one advice at a time, the room named first, bars to pick one. */
export function band(o:{slides:Slide[];index:number;pick:(i:number)=>void;title:string}):TemplateResult {
  const s=o.slides[o.index%o.slides.length],many=o.slides.length>1,asking=!!KIND[s.level];
  return html`<div class="nh-band" data-level=${s.level}>
    <div class="nh-band-top"><span class="nh-room">${asking?tx(s.pill):o.title}</span>${asking?html`<span class="nh-kind">${t(KIND[s.level]!)}</span>`:html`<span class="nh-kind">${tx(s.pill??pills[s.level])}</span>`}
      ${many?html`<span class="nh-pos">${t('{i} sur {n}',{i:o.index%o.slides.length+1,n:o.slides.length})}</span>`:nothing}</div>
    <div class="nh-band-main"><span class="nh-disk">${icon(s.disk??'check')}</span>
      <div class="nh-band-text"><p class="nh-title">${tx(s.title)}</p>${s.line?html`<p class="nh-line">${tl(s.line)}</p>`:nothing}${s.cap?html`<p class="nh-cap">${tx(s.cap)}</p>`:nothing}</div></div>
    ${many?html`<div class="nh-bars">${o.slides.map((x,k)=>html`<button type="button" aria-label=${t('Conseil {n} : {title}',{n:k+1,title:tx(x.pill)})} aria-current=${k===o.index%o.slides.length?'true':'false'} data-level=${x.level} @click=${()=>o.pick(k)}><span></span></button>`)}</div>`:nothing}
  </div>`;
}

export function tabs(period:Period,pick:(p:Period)=>void):TemplateResult {
  return html`<div class="nh-tabs" role="group" aria-label=${t('Période')}>${PERIODS.map(([p,label])=>html`<button type="button" aria-pressed=${p===period?'true':'false'} @click=${()=>pick(p)}>${t(label)}</button>`)}</div>`;
}

/** A value not known yet. */
const DASH='—';
const goodness=(l:string|null)=>l==='A'||l==='B'?'calm':l==='C'?'neutral':l?'action':'neutral';
const comfortWord=(s:number)=>s>=85?fr('Très bon'):s>=70?fr('Bon dans l’ensemble'):s>=55?fr('Correct'):fr('À améliorer');
const PERIOD_WORD:Record<Period,string>={day:fr('sur 24 h'),week:fr('sur 7 jours'),month:fr('sur 30 jours')};

/** The review's four themes over the period: a letter each, and the figure behind it. */
export function themes(d:PeriodData|undefined,period:Period):TemplateResult {
  const th=d?.themes,none=fr('pas assez de mesures');
  const tiles:[string,Grade|undefined,string,string,string][]=[
    [fr('Confort'),th?.comfort,th?.comfort.score!=null?String(th.comfort.score):'—',' / 100',th?.comfort.score!=null?comfortWord(th.comfort.score):none],
    [fr('Chaleur'),th?.warmth,th?.warmth.share!=null?String(th.warmth.share):'—',' %',th?.warmth.share!=null?fr('du temps confortable'):fr('aucune pièce chauffée mesurée')],
    [fr('Humidité'),th?.humidity,th?.humidity.share!=null?String(th.humidity.share):'—',' %',th?.humidity.share!=null?fr('du temps trop humide'):fr('pas de capteur d’humidité')],
    [fr('Air'),th?.air,th?.air.share!=null?String(th.air.share):'—',' %',th?.air.share!=null?fr('du temps air correct'):fr('pas de capteur de CO₂')]];
  return html`<div class="nh-themes" aria-label=${t('Bilan {period}',{period:t(PERIOD_WORD[period])})}>${tiles.map(([label,g,value,unit,note])=>html`<div class="nh-theme">
    <span class="nw-label">${t(label)}</span><span class="nh-letter" data-level=${goodness(g?.letter??null)}>${g?.letter??'–'}</span>
    <b>${d?value:'…'}${d&&value!=='—'?html`<small>${unit}</small>`:nothing}</b><span class="nh-note">${d?t(g?.letter||value!==DASH?note:none):t('chargement')}</span></div>`)}</div>`;
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
  return html`<div class="nh-chart">
    <div class="nh-chart-head"><span class="nw-label">${t('Températures {period}',{period:t(PERIOD_WORD[o.period])})}</span>
      <span class="nh-legend">${bands.length?html`<span><i class="nh-key-band"></i>${t('votre plage')}</span>`:nothing}<span><i class="nh-key-range"></i>${t('mini–maxi')}</span><span><i class="nh-key-dot"></i>${o.period==='day'?t('maintenant'):t('moyenne')}</span></span></div>
    <div class="nh-row nh-axis"><span></span><span class="nh-track">${ticks.map(t=>html`<em class=${same&&t>=same[0]&&t<=same[1]?'in':''} style=${`left:${at(t)}`}>${t}°</em>`)}</span><span></span></div>
    ${o.floors.map(f=>{const rows=lines.slice(i,i+=f.rooms.length);
      return html`${o.floors.length>1?html`<div class="nh-floor"><span class="nw-label">${f.name}</span><span>${f.mean!=null?number(f.mean)+'°':''}</span></div>`:nothing}${rows.map(row)}`;})}
    ${outValue!=null?html`<div class="nh-row nh-out"><span class="nh-name">${t('Dehors')}</span><span class="nh-out-text">${out?html`${number(out.min)} – ${number(out.max)} °C`:nothing}</span><span class="nh-val">${number(Math.round(outValue*10)/10)}°</span></div>`:nothing}
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
  .nh-band { --c:var(--nw-ok); padding:16px 20px 12px; display:flex; flex-direction:column; gap:10px;
    background:linear-gradient(180deg, color-mix(in oklab, var(--c) 24%, transparent), color-mix(in oklab, var(--c) 7%, transparent)); }
  .nh-band[data-level="action"] { --c:var(--nw-act); } .nh-band[data-level="urgent"] { --c:var(--nw-alert); } .nh-band[data-level="benefit"] { --c:var(--nw-benefit); }
  .nh-band[data-level="neutral"] { --c:color-mix(in srgb, var(--nw-fg) 45%, transparent); }
  .nh-band-top { display:flex; align-items:center; gap:8px; min-width:0; }
  .nh-room { padding:3px 10px; border-radius:var(--nw-radius-pill); background:var(--c); color:#1f232b; font-size:var(--nw-fs-small); font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nh-kind { font-size:var(--nw-fs-label); font-weight:600; letter-spacing:var(--nw-label-spacing); text-transform:uppercase; color:color-mix(in oklab, var(--c) 70%, var(--nw-fg)); white-space:nowrap; }
  .nh-pos { margin-left:auto; font-size:var(--nw-fs-small); opacity:.75; white-space:nowrap; }
  .nh-band-main { display:flex; align-items:center; gap:14px; min-width:0; }
  .nh-disk { flex:none; display:grid; place-items:center; width:46px; height:46px; border-radius:50%; border:2px solid var(--c); color:var(--c); }
  .nh-disk svg { width:22px; height:22px; }
  .nh-band-text { min-width:0; } .nh-band-text p { margin:0; }
  .nh-title { font-size:21px; font-weight:700; line-height:1.2; }
  .nh-line, .nh-cap { font-size:var(--nw-fs-small); opacity:.85; margin-top:3px !important; }
  .nh-cap { opacity:.7; }
  .nh-bars { display:flex; gap:6px; }
  .nh-bars button { flex:1; height:16px; padding:6px 0; border:0; background:none; cursor:pointer; }
  .nh-bars span { display:block; height:4px; border-radius:2px; background:color-mix(in srgb, var(--nw-fg) 18%, transparent); }
  .nh-bars button[aria-current="true"] span { background:var(--c); }
  .nh-body { padding:16px 20px 18px; display:flex; flex-direction:column; gap:18px; }
  .nh-head { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .nh-head h2 { margin:0; font-size:var(--nw-fs-title); font-weight:600; }
  .nh-tabs { display:flex; padding:3px; border-radius:var(--nw-radius-pill); background:color-mix(in srgb, var(--nw-fg) 7%, transparent); }
  .nh-tabs button { min-height:32px; padding:0 14px; border:0; border-radius:var(--nw-radius-pill); background:none; color:inherit; font:inherit; font-size:var(--nw-fs-small); font-weight:600; opacity:.8; cursor:pointer; }
  .nh-tabs button[aria-pressed="true"] { background:var(--nw-fg); color:var(--nw-bg); opacity:1; }
  .nh-themes { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:8px; }
  .nh-theme { display:grid; grid-template-columns:1fr auto; align-items:center; gap:2px 10px; padding:12px 14px; border-radius:14px; background:color-mix(in srgb, var(--nw-fg) 5%, transparent); }
  .nh-theme b { font-size:20px; } .nh-theme b small { font-size:12px; font-weight:500; opacity:.7; }
  .nh-note { font-size:var(--nw-fs-small); opacity:.8; }
  .nh-letter { grid-column:2; grid-row:1 / span 3; display:grid; place-items:center; width:40px; height:40px; border-radius:12px; font-size:20px; font-weight:700;
    --c:color-mix(in srgb, var(--nw-fg) 45%, transparent); background:color-mix(in oklab, var(--c) 35%, transparent); color:color-mix(in oklab, var(--c) 45%, var(--nw-fg)); }
  .nh-letter[data-level="calm"] { --c:var(--nw-ok); } .nh-letter[data-level="action"] { --c:var(--nw-act); }
  .nh-chart, .nh-curve { display:flex; flex-direction:column; gap:2px; }
  .nh-chart-head { display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap; padding-bottom:6px; }
  .nh-legend { display:flex; gap:12px; font-size:11px; opacity:.8; }
  .nh-legend span { display:flex; align-items:center; gap:5px; }
  .nh-key-range { width:18px; height:6px; border-radius:3px; background:color-mix(in oklab, var(--nw-ok) 45%, transparent); }
  .nh-key-dot { width:9px; height:9px; border-radius:50%; background:var(--nw-ok); }
  .nh-key-in, .nh-key-out { width:14px; height:3px; border-radius:2px; background:var(--nw-ok); } .nh-key-out { background:color-mix(in srgb, var(--nw-fg) 45%, transparent); }
  .nh-row { --c:var(--nw-ok); display:grid; grid-template-columns:minmax(90px, 30%) 1fr 46px; gap:10px; align-items:center; min-height:32px; }
  .nh-row[data-level="action"], .nh-row[data-level="urgent"] { --c:var(--nw-act); }
  .nh-row[data-level="neutral"] { --c:color-mix(in srgb, var(--nw-fg) 45%, transparent); }
  .nh-row[data-level="action"] .nh-name, .nh-row[data-level="action"] .nh-val { color:color-mix(in oklab, var(--nw-act) 60%, var(--nw-fg)); font-weight:600; }
  .nh-name { font-size:var(--nw-fs-small); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nh-val { font-size:var(--nw-fs-small); font-weight:600; text-align:right; white-space:nowrap; }
  .nh-track { position:relative; height:32px; }
  .nh-track i { position:absolute; }
  .nh-track::before { content:''; position:absolute; left:0; right:0; top:15px; height:2px; background:var(--nw-line-soft); }
  .nh-band-zone { top:0; bottom:0; background:color-mix(in oklab, var(--nw-calm) 14%, transparent); }
  .nh-key-band { width:12px; height:10px; border-radius:2px; background:color-mix(in oklab, var(--nw-calm) 35%, transparent); }
  .nh-range { top:12px; height:8px; border-radius:4px; background:color-mix(in oklab, var(--c) 45%, transparent); }
  .nh-dot { top:9px; width:14px; height:14px; margin-left:-7px; border-radius:50%; box-sizing:border-box; border:2px solid var(--nw-bg); background:var(--c); }
  .nh-axis { min-height:16px; } .nh-axis .nh-track { height:16px; } .nh-axis .nh-track::before { display:none; }
  .nh-axis em { position:absolute; transform:translateX(-50%); font-style:normal; font-size:11px; opacity:.7; }
  .nh-axis em.in { color:var(--nw-calm); opacity:1; }
  .nh-floor { display:flex; justify-content:space-between; padding:10px 0 2px; font-size:11px; opacity:.85; }
  .nh-out { margin-top:6px; border-top:1px dashed var(--nw-line); }
  .nh-out .nh-name, .nh-out-text { font-size:var(--nw-fs-small); opacity:.8; }
  .nh-curve { position:relative; }
  .nh-curve svg { width:100%; height:120px; display:block; overflow:visible; }
  .nh-yaxis { position:absolute; right:0; top:28px; height:120px; display:flex; flex-direction:column; justify-content:space-between; font-size:11px; opacity:.6; pointer-events:none; }
  .nh-c-band { fill:color-mix(in oklab, var(--nw-calm) 14%, transparent); }
  .nh-c-in, .nh-c-out { fill:none; stroke-linejoin:round; vector-effect:non-scaling-stroke; }
  .nh-c-in { stroke:var(--nw-ok); stroke-width:2.5; } .nh-c-out { stroke:color-mix(in srgb, var(--nw-fg) 45%, transparent); stroke-width:2; }
  .nh-ticks { display:flex; justify-content:space-between; font-size:11px; opacity:.7; }
  .nh-empty { margin:0; font-size:var(--nw-fs-small); opacity:.75; }
  .nh-more { display:flex; flex-direction:column; gap:18px; padding-top:6px; }
  @media (prefers-reduced-motion: no-preference) { .nh-band { transition:background .4s ease; } }
`;
