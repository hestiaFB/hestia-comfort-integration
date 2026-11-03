import {html,nothing,type TemplateResult} from 'lit';
import type {Feel,View} from '../types';
import {numeric} from '../view';
import {icon} from '../ui/icons';
import {echelle} from '../ui/hestia-echelle';
import {currentLocale,fr,t} from '../i18n';

/** The room's « Ressenti » (3 November, maquettes/maquette-ressenti-piece.html), drawn as Hestia Weather's: the value
 *  and its word, the scale of the room's range, then what plays on it in tiles, each with its effect in one word.
 *  The figures come from the engine (engine/feel.py); the big temperature above stays the thermometer's. */

const nf=(v:number,digits=1)=>new Intl.NumberFormat(currentLocale(),{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v).replace('-','−');
const signed=(v:number)=>`${v>=0?'+':'−'}${nf(Math.abs(v))}`;
// The walls, as the card's other pictograms are drawn (ui/icons.ts).
const WALL=html`<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="1.5"/><path d="M3 9.3h18M3 14.7h18M9 4v5.3M15 9.3v5.4M9 14.7V20"/></svg>`;
const HEATERS:Record<string,string>={stove:fr('Poêle'),radiator:fr('Radiateur'),floor:fr('Plancher chauffant'),ac:fr('Climatisation')};

interface Factor {ic:TemplateResult;title:string;value:string;effect:string;theme:string;note:string}
const NONE={effect:fr('sans effet'),theme:'calm'};
/** An effect in one word and its share of the ressenti; under a twentieth of a degree, it has none. */
const effect=(delta:number,quiet:string)=>Math.abs(delta)<.05?{...NONE,note:quiet}
  :{effect:delta>0?fr('réchauffe'):fr('refroidit'),theme:delta>0?'heat':'cold',note:t('{delta} °C au ressenti',{delta:signed(delta)})};

/** What plays on the ressenti: the walls and panes, the sun, the heating, a draught, the humidity, the air's CO₂. */
function factors(f:Feel,co2:number|null):Factor[] {
  const w=f.factors.walls,s=f.factors.sun,h=f.factors.heating,d=f.factors.draught,u=f.factors.humidity;
  const out:Factor[]=[];
  if(w.gap!==null)out.push({ic:WALL,title:t('Murs et vitres'),value:t('{gap} °C d’écart',{gap:nf(Math.abs(w.gap),0)}),...effect(w.delta,t('dehors comme dedans')),
    ...(Math.abs(w.delta)>=.05&&w.shutters?{note:t('{delta} °C · volets fermés',{delta:signed(w.delta)})}:{})});
  out.push({ic:icon(s.night?'moon':'sun'),title:t('Soleil'),value:s.night||s.hidden||s.wm2===null?'—':`${s.wm2} W/m²`,
    ...(s.night?{...NONE,note:t('la nuit, il ne réchauffe pas')}:s.hidden?{...NONE,note:t('volets fermés, il n’entre pas')}:effect(s.delta,t('fenêtres à l’ombre')))});
  if(h)out.push({ic:icon('flame'),title:t((h.kind&&HEATERS[h.kind])||fr('Chauffage')),value:h.on?t('en marche'):t('à l’arrêt'),...effect(h.delta,h.kind==='ac'?t('ne rayonne pas'):h.on?t('rayonne peu'):t('ne rayonne pas'))});
  out.push({ic:icon('air'),title:t('Courant d’air'),value:d.open?(d.gust!==null?`${d.gust} km/h`:t('fenêtre ouverte')):t('aucun'),
    ...effect(d.delta,d.open?t('dehors aussi doux'):t('fenêtres fermées')),...(d.open&&Math.abs(d.delta)>=.05?{note:t('{delta} °C · fenêtre ouverte',{delta:signed(d.delta)})}:{})});
  if(u)out.push({ic:icon('drop'),title:t('Humidité'),value:`${u.value} %`,
    ...(u.delta>=.05?{effect:fr('réchauffe'),theme:'heat',note:t('{delta} °C · air lourd',{delta:signed(u.delta)})}
      :u.value<35?{effect:fr('attention'),theme:'level1',note:t('air sec')}:u.dew>=18?{effect:fr('attention'),theme:'level1',note:t('air lourd')}:{...NONE,note:t('sans gêne')})});
  // The CO₂ changes nothing to the warmth: it says whether the air feels stale.
  if(co2!==null)out.push({ic:icon('fan'),title:t('Air'),value:`${Math.round(co2)} ppm`,
    ...(co2>=1400?{effect:fr('attention'),theme:'level2',note:t('renfermé')}:co2>=1000?{effect:fr('attention'),theme:'level1',note:t('un peu renfermé')}:{...NONE,note:t('air frais')})});
  return out;
}

/** The range the room keeps now: the season's when known, else its own settings. */
const range=(v:View):[number,number]|null=>{const s=v.assessment.features?.season;
  return s?.minimum!=null&&s?.maximum!=null?[s.minimum,s.maximum]:v.comfort_minimum!=null&&v.comfort_maximum!=null?[v.comfort_minimum,v.comfort_maximum]:null;};

/** The panel, or null when the engine sends no ressenti (an older integration, no temperature). `gauge`: the scale shown. */
export function feelPanel(v:View,partners:View[]=[],o:{gauge?:boolean;src?:string}={}):TemplateResult|null {
  const f=v.feel;
  if(!f)return null;
  const band=range(v),[mn,mx]=band??[19,24],lo=Math.floor(Math.min(mn-3,f.feels-1)),hi=Math.ceil(Math.max(mx+3,f.feels+1));
  const parts=[{from:lo,to:mn,word:t('Frais'),tone:'color-mix(in oklab,var(--nw-cold) 45%,var(--nw-calm))'},
    {from:mn,to:mx,word:t('Agréable'),tone:'var(--nw-calm)'},{from:mx,to:hi,word:t('Chaud'),tone:'var(--nw-level2)'}];
  const word=f.feels<mn?t('Frais'):f.feels<mx?t('Agréable'):t('Chaud'),gap=f.feels-f.air;
  const say=Math.abs(gap)<.1?t('comme le thermomètre'):t('{gap} °C par rapport au thermomètre',{gap:signed(gap)});
  const co2=numeric(v.observations.co2)??partners.map(p=>numeric(p.observations.co2)).find(x=>x!==null)??null;
  const tiles=factors(f,co2);
  // Under the scale, what « Agréable » is: the room's range, the season's when the range follows the seasons.
  const group=v.assessment.features?.season?.group,low=nf(mn,mn%1?1:0),high=nf(mx,mx%1?1:0);
  const plage=!band?t('Agréable = la plage par défaut, de {low} à {high} °C',{low,high})
    :group==='winter'?t('Agréable = votre plage d’hiver, de {low} à {high} °C',{low,high})
    :group==='summer'?t('Agréable = votre plage d’été, de {low} à {high} °C',{low,high})
    :group==='between'?t('Agréable = votre plage d’entre-saison, de {low} à {high} °C',{low,high})
    :t('Agréable = votre plage, de {low} à {high} °C',{low,high});
  const walls={bien:t('bien isolés'),moyenne:t('moyennement isolés'),peu:t('peu isolés')}[f.walls]??f.walls;
  const others=partners.filter(p=>p.feel).map(p=>({label:t('{room} · ressenti',{room:p.title}),value:`${nf(p.feel!.feels)} °C`}));
  const stats=[...others,...(f.outdoor!==null?[{label:t('Dehors'),value:`${nf(f.outdoor)} °C`}]:[])];
  const toggle=(e:Event)=>{const b=e.currentTarget as HTMLElement,why=b.closest('section')?.querySelector<HTMLElement>('.nw-feel-why');
    if(why){why.hidden=!why.hidden;b.setAttribute('aria-expanded',String(!why.hidden));}};
  return html`<section class="nc-mod nw-panel nc-feel" data-piece="temperature" aria-label=${t('Ressenti')}>
    <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon('temp')}</span><h3>${t('Ressenti')}</h3>
      <button type="button" class="nw-info" aria-label=${t('Qu’est-ce que le ressenti ?')} aria-expanded="false" @click=${toggle}></button>
      <span class="aside">${o.src??t('maintenant')}</span></div>
    <div class="nw-feel-why" hidden><p>${t('C’est la température que le corps perçoit dans la pièce. Le thermomètre ne mesure que l’air : des murs et des vitres froids, un courant d’air la font baisser, le soleil et le chauffage qui rayonne la font monter.')}</p>
      <p>${t('C’est une estimation : les murs sont calculés depuis l’écart avec dehors et votre réglage (murs {walls}).',{walls})}</p>
      <p class="ex">${t('En ce moment : {air} °C d’air se ressentent comme {feels} °C.',{air:nf(f.air),feels:nf(f.feels)})}</p></div>
    <div class="nw-feel-row"><div class="nw-value"><b>${nf(f.feels)}</b><span>°C</span></div><span class="nw-feel-word">${word}</span><span class="nw-feel-say">${say}</span></div>
    ${o.gauge===false?nothing:html`${echelle({lo,hi,parts,value:f.feels,valueText:`${nf(f.feels)} °C`,label:t('Ressenti {t} °C',{t:nf(f.feels)}),degree:v=>`${v<0?'−':''}${Math.abs(v)}°`})}
      <div class="nw-feel-ends" style="justify-content:center">${plage}</div>`}
    <div class="nw-feel-factors" style="--nw-ff-cols:3">${tiles.map(x=>html`<div>
      <span class="nw-ff-head"><span class="nw-ff-t">${x.ic}${x.title}</span><span class="nw-ff-eff" style=${`--c:var(--nw-${x.theme})`}>${t(x.effect)}</span></span>
      <b>${x.value}</b>${x.note?html`<small>${x.note}</small>`:nothing}</div>`)}</div>
    ${stats.length?html`<div class="nc-mod-stats nw-stats" style=${`--n:${Math.min(stats.length,4)}`}>${stats.map(x=>html`<div><span>${x.label}</span><b>${x.value}</b></div>`)}</div>`:nothing}
  </section>`;
}
