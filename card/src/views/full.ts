import {html,svg,nothing,type TemplateResult} from 'lit';
import {trial3} from './advisor3';
import {nowBlocks,type Config,type View,type Horizon} from '../types';
import {numeric,number} from '../view';
import {icon} from '../ui/icons';
import {echelle} from '../ui/hestia-echelle';
import {t,tx,currentLocale} from '../i18n';
import {tiles,trendOf,humidityLabel,moreInfo,fold,details,asking,nextChange,type Tile,type Trend,type CardState} from './room';
import {horizonShown,horizonChart,horizonHead,horizonResult} from './horizon';

/** The full card below its banner (4 November, maquettes/maquette-carte-complete.html): five questions, one place each.
 *  « En ce moment »: the Ressenti (warmth and humidity, each on the charter's compact scale) and the Air (rings);
 *  « À venir »: what will change, dated; « Appareils »: one line; « Détails »: folded. A section without a source is left out:
 *  the card shows what the room's sensors allow, never a guess. The banner above is not this file's. */

const nf=(v:number,digits=1)=>new Intl.NumberFormat(currentLocale(),{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v).replace('-','−');
const signed=(v:number,digits=1)=>`${v>=0?'+':'−'}${nf(Math.abs(v),digits)}`;
/** The charter's state colours: blue all is well, amber out of the range without a gesture, orange a gesture, green a benefit. */
const C={ok:'var(--nw-ok)',watch:'var(--nw-watch)',act:'var(--nw-act)',benefit:'var(--nw-benefit)',none:'var(--nw-fg2)'};
type Tone=keyof typeof C;
const str=(x:unknown)=>typeof x==='string'?x:'';
const list=(x:unknown)=>Array.isArray(x)?x.filter((i):i is string=>typeof i==='string'):[];

/** The range the room keeps now: the season's when known, else its own settings. */
const range=(v:View):[number,number]|null=>{const s=v.assessment.features?.season;
  return s?.minimum!=null&&s?.maximum!=null?[s.minimum,s.maximum]:v.comfort_minimum!=null&&v.comfort_maximum!=null?[v.comfort_minimum,v.comfort_maximum]:null;};

/** The arrow on the word's line (planche-tendance.html, choice E, 5 November): the charter's arrow leans with the speed,
 *  → steady, ↗ ↘ slowly, ↑ ↓ fast, the words in front and the speed under them. No curve: the sensor's tenth no longer shakes it. */
const LEANS={temperature:[.3,1],humidity:[3,10]} as const;
function trendLine(tr:Trend|undefined,slope:number|null|undefined,unit:string,digits:number):TemplateResult|typeof nothing {
  if(!tr)return nothing;
  const [slow,fast]=LEANS[unit==='%'?'humidity':'temperature'],a=slope==null?0:Math.abs(slope);
  // Without a speed, the engine's way alone leans it slowly.
  const up=slope!=null?slope>0:tr.way==='up',moving=slope!=null?a>=slow&&tr.way!=='stable':tr.way!=='stable',quick=moving&&a>=fast;
  const turn=!moving?90:quick?(up?0:180):(up?45:135);
  const word=!moving?t('stable'):quick?(up?t('monte vite'):t('baisse vite')):(up?t('monte doucement'):t('baisse doucement'));
  return html`<span class="nc-fx-trend" data-tone=${moving?tr.tone:'steady'}><span class="nc-fx-say"><span>${word}</span>${moving&&slope!=null?html`<small>${signed(slope,digits)} ${unit}/h</small>`:nothing}</span>
    <span class="nw-trend nc-fx-arrow" data-way="lean" data-tone=${moving?tr.tone:'steady'} style=${`--r:${turn}deg`} aria-hidden="true"></span></span>`;
}

// ---------- « À savoir » of the engine: what has a time to come goes to « À venir », the rest to « Bon à savoir ». ----------
// One place for each line, the same every time (Frank, 7 November: « je me demande surtout où sont affichés les bon à
// savoir »): the lines were spread over the Ressenti, the Air and the Détails, and lost in a room without an air sensor.
interface Said {know:string[];coming:Coming[];doubts:string[];tryIt:string}
interface Coming {when:number;at:string;ic:string;text:string;note?:string|TemplateResult;tone:Tone;chart?:TemplateResult}
const TIME=/(jusqu[’']à |vers |à |dès |avant )?(demain )?(\d{1,2}) h(?: (\d{2}))?/;
/** « 23 h », « demain 6 h 30 »: the moment it says, today unless said tomorrow or already past by an hour. */
function when(m:RegExpMatchArray):number {const d=new Date();d.setHours(+m[3],m[4]?+m[4]:0,0,0);
  if(m[2]||d.getTime()<Date.now()-3600e3)d.setDate(d.getDate()+1);return d.getTime();}
const clockAt=(ms:number)=>{const d=new Date(ms),h=d.getHours(),m=d.getMinutes(),time=m?`${h} h ${String(m).padStart(2,'0')}`:`${h} h`;
  return d.toDateString()===new Date().toDateString()?time:t('demain {time}',{time});};
/** A line of the engine as an event: « Le poêle tourne au minimum » in bold, the rest under it, the time in its column. */
function event(line:string,m:RegExpMatchArray,ic:string,tone:Tone):Coming {
  // « de 11 h à 15 h »: the span in the time column, both hours out of the words.
  const span=line.match(/\bde (\d{1,2} h(?: \d{2})?) à ((\d{1,2}) h(?: (\d{2}))?)/),end=span?span[3]&&clockAt(when(['',undefined,undefined,span[3],span[4]] as unknown as RegExpMatchArray)):'';
  const until=/^jusqu/.test(m[1]??''),rest=line.replace(span?span[0]:m[0],'').replace(/\s+(au moins|environ)\s*$/,'').replace(/[\s,]+$/,'').replace(/\s{2,}/g,' ').replace(/\s+:/g,' :');
  const [title,...more]=rest.split(' : ');
  const at=span?`${clockAt(when(m))} → ${end}`:until?t('jusqu’à {time}',{time:clockAt(when(m))}):clockAt(when(m));
  return {when:when(m),at,ic,text:title.trim(),note:more.join(' : ').trim()||undefined,tone};
}
/** A time that is not to come: « ouverte depuis 14 h 05 », « 1,2 °C de plus d'ici 22 h » (a horizon, not an event). */
const notComing=(line:string,m:RegExpMatchArray)=>/(depuis|d[’']ici)\s*$/.test(line.slice(0,m.index));
function spread(v:View):Said {
  const out:Said={know:[],coming:[],doubts:[],tryIt:''};
  const a=v.advisor?.attributes;
  if(!a)return out;
  // The engine writes « À essayer — … »: the heading is the card's. With no other gesture the trial is the banner's advice
  // (advisor3.ts trial3): said there, not twice.
  out.tryIt=trial3(a)?'':str(a.a_essayer).replace(/^À essayer\s*[—:–-]\s*/,'');
  const night=str(a.cette_nuit);
  if(night){const d=new Date();d.setHours(22,30,0,0);out.coming.push({when:d.getTime(),at:t('Cette nuit'),ic:'moon',text:night,tone:'act'});}
  const aside=a.pas_maintenant&&typeof a.pas_maintenant==='object'?Object.entries(a.pas_maintenant as Record<string,string>):[];
  for(const [what,until] of aside){const m=String(until).match(TIME);
    out.coming.push({when:m?when(m):Date.now(),at:t('jusqu’à {time}',{time:m?clockAt(when(m)):String(until)}),ic:'clock',text:t('{what} mis de côté',{what}),note:t('vous avez dit « Pas maintenant »'),tone:'none'});}
  out.doubts=typeof a.douteuses==='string'?[a.douteuses]:list(a.douteuses);
  for(const line of list(a.bon_a_savoir).filter(l=>l!==night)){
    const m=line.match(TIME);
    if(m&&!notComing(line,m))out.coming.push(event(line,m,/chauff|poêle/i.test(line)?'heat':/soleil/i.test(line)?'sun':'clock','none'));
    else out.know.push(line);
  }
  return out;
}

// ---------- Ressenti : the warmth, then the humidity, each its word, its trend, the compact scale, what plays on it. ----------
const HEATERS:Record<string,string>={stove:'Poêle',pellet:'Poêle à granulés',radiator:'Radiateur',radiant:'Panneau rayonnant',inertia:'Radiateur à inertie',floor:'Plancher chauffant',ac:'Climatisation'};
const tap=(id:string|undefined,title:string)=>id?{onValue:(e:Event)=>moreInfo(e,id),valueTitle:title}:{};
const fxTop=(body:TemplateResult,id:string|undefined,title:string)=>id
  ?html`<button type="button" class="nc-fx-top nc-hit" title=${title} @click=${(e:Event)=>moreInfo(e,id)}>${body}</button>`
  :html`<div class="nc-fx-top">${body}</div>`;
/** `only` keeps one half: the warmth or the humidity alone, for the cards « Température » and « Humidité » (6 November). */
function feelPanel(v:View,partners:View[],said:Said,uid:string,only?:'warmth'|'humidity',src?:string):TemplateResult|typeof nothing {
  const f=v.feel,a=v.assessment,band=range(v),ti=numeric(v.observations.indoor_temperature),value=only==='humidity'?null:f?.feels??ti;
  const h=only==='warmth'?null:numeric(v.observations.indoor_humidity),hum=a.features?.humidity,curves=a.features?.trends?.curves;
  if(value===null&&h===null)return nothing;
  const ask=asking(v),needs=a.needs;
  // A tap on the word or on the bubble opens the sensor's details in Home Assistant.
  const tempId=v.observations.indoor_temperature?.source??undefined,humId=v.observations.indoor_humidity?.source??undefined;
  let warmth:TemplateResult|typeof nothing=nothing;
  if(value!==null){
    const [mn,mx]=band??[19,24],lo=Math.floor(Math.min(mn-3,value-1)),hi=Math.ceil(Math.max(mx+3,value+1));
    const word=value<mn?t('Frais'):value<mx?t('Agréable'):t('Chaud'),out=value<mn?'low':value>=mx?'high':null;
    const tone:Tone=!out?'ok':ask&&needs.some(n=>n==='heat'||n==='cool')?'act':'watch';
    const causes=f?[
      ...(Math.abs(f.factors.walls.delta)>=.05?[[t('Murs et vitres'),f.factors.walls.delta]]:[]),
      ...(Math.abs(f.factors.sun.delta)>=.05?[[t('Soleil'),f.factors.sun.delta]]:[]),
      ...(f.factors.heating&&Math.abs(f.factors.heating.delta)>=.05?[[t((f.factors.heating.kind&&HEATERS[f.factors.heating.kind])||'Chauffage'),f.factors.heating.delta]]:[]),
      ...(Math.abs(f.factors.draught.delta)>=.05?[[t('Courant d’air'),f.factors.draught.delta]]:[]),
      ...(f.factors.humidity&&f.factors.humidity.delta>=.05?[[t('Air lourd'),f.factors.humidity.delta]]:[])] as [string,number][]:[];
    const line=causes.map(([k,d])=>html`<span>${k} <b>${signed(d)} °C</b></span>`);
    warmth=html`<div class="nc-fx-row"><span class="nw-label">${t('Chaleur')}</span>
      ${fxTop(html`<b class="nc-fx-word" style=${`--c:${C[tone]}`}>${word}</b>${trendLine(trendOf(v,'temperature',out,band),curves?.temperature?.slope,'°C',1)}`,tempId,t('Détails de la température'))}
      ${echelle({lo,hi,value,valueText:`${nf(value)} °C`,label:t('Ressenti {t} °C',{t:nf(value)}),degree:()=>'',compact:true,...tap(tempId,t('Détails de la température')),
        parts:[{from:lo,to:mn,word:t('Frais'),tone:'color-mix(in oklab,var(--nw-cold) 45%,var(--nw-calm))'},{from:mn,to:mx,word:t('Agréable'),tone:'var(--nw-calm)'},{from:mx,to:hi,word:t('Chaud'),tone:'var(--nw-level2)'}]})}
      ${line.length?html`<p class="nc-fx-line">${line.map((x,i)=>html`${i?' · ':''}${x}`)}</p>`:nothing}</div>`;
  }
  let humidity:TemplateResult|typeof nothing=nothing;
  if(h!==null){
    const hmin=hum?.minimum??40,hmax=hum?.maximum??60,very=Math.max(hmax+10,70);
    const label=humidityLabel(v),word=!label||label==='Dans votre plage'?t('Correcte'):tx(label);
    const out=hum?.status==='high'?'high':hum?.status==='low'?'low':null;
    const tone:Tone=!out?'ok':ask&&needs.includes('dry')?'act':'watch';
    const others=partners.map(p=>({room:p.title,h:numeric(p.observations.indoor_humidity)})).filter(x=>x.h!==null);
    const note=others.map(x=>t('{room} {value} %',{room:x.room,value:Math.round(x.h!)}));
    humidity=html`<div class="nc-fx-row"><span class="nw-label">${partners.length?t('Humidité · {room}',{room:v.title}):t('Humidité')}</span>
      ${fxTop(html`<b class="nc-fx-word" style=${`--c:${C[tone]}`}>${word}</b>${trendLine(trendOf(v,'humidity',out,[hmin,hmax]),curves?.humidity?.slope,'%',0)}`,humId,t('Détails de l’humidité'))}
      ${echelle({lo:20,hi:90,value:h,valueText:`${Math.round(h)} %`,label:t('Humidité {n} %',{n:Math.round(h)}),degree:()=>'',compact:true,...tap(humId,t('Détails de l’humidité')),
        parts:[{from:20,to:hmin,word:t('Sec'),tone:'color-mix(in oklab,var(--nw-level1) 60%,var(--nw-calm))'},{from:hmin,to:hmax,word:t('Agréable'),tone:'var(--nw-calm)'},
          {from:hmax,to:very,word:t('Humide'),tone:'color-mix(in oklab,var(--nw-rain) 55%,var(--nw-calm))'},{from:very,to:90,word:t('Très'),tone:'var(--nw-rain)'}]})}
      ${note.length?html`<p class="nc-fx-line">${note.join(' · ')}</p>`:nothing}</div>`;
  }
  // At the foot, the rooms of the same air and outside: said once.
  const te=f?.outdoor??numeric(v.observations.outdoor_temperature);
  const foot=value===null?[]:[...partners.filter(p=>p.feel).map(p=>html`${t('{room} · ressenti',{room:p.title})} <b>${nf(p.feel!.feels)} °C</b>`),...(te!==null?[html`${t('Dehors')} <b>${nf(te)} °C</b>`]:[])];
  const toggle=(e:Event)=>{const b=e.currentTarget as HTMLElement,why=b.closest('section')?.querySelector<HTMLElement>('.nw-feel-why');
    if(why){why.hidden=!why.hidden;b.setAttribute('aria-expanded',String(!why.hidden));}};
  const gap=f?f.feels-f.air:0;
  return html`<section class="nc-mod nw-panel nc-fx" data-piece="temperature" aria-label=${value!==null?t('Ressenti'):t('Humidité')}>
    <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(value!==null?'temp':'drop')}</span><h3>${value!==null?t('Ressenti'):t('Humidité')}</h3>
      ${f&&value!==null?html`<button type="button" class="nw-info" aria-label=${t('Qu’est-ce que le ressenti ?')} aria-controls=${uid+'-why'} aria-expanded="false" @click=${toggle}></button>`:nothing}${src?html`<span class="aside nc-src">${src}</span>`:nothing}</div>
    ${f&&value!==null?html`<div class="nw-feel-why" id=${uid+'-why'} hidden><p>${t('C’est la température que le corps perçoit dans la pièce. Le thermomètre ne mesure que l’air : des murs et des vitres froids, un courant d’air la font baisser, le soleil et le chauffage qui rayonne la font monter.')}</p>
      <p class="ex">${t('En ce moment : {air} °C d’air se ressentent comme {feels} °C.',{air:nf(f.air),feels:nf(f.feels)})} ${Math.abs(gap)<.1?'':t('{gap} °C par rapport au thermomètre.',{gap:signed(gap)})}</p>
      ${band?html`<p>${t('Votre plage : {low} à {high} °C · humidité {hlow} à {hhigh} %.',{low:nf(band[0],band[0]%1?1:0),high:nf(band[1],band[1]%1?1:0),hlow:Math.round(hum?.minimum??40),hhigh:Math.round(hum?.maximum??60)})}</p>`:nothing}</div>`:nothing}
    ${warmth}${humidity}
    ${foot.length?html`<p class="nc-fx-foot">${foot.map((x,i)=>html`${i?' · ':''}${x}`)}</p>`:nothing}
  </section>`;
}

// ---------- Air : a ring per measure around the verdict of the one most at stake; one measure is a gauge. ----------
interface AirRow {key:'co2'|'pm25'|'voc';label:string;room?:string;value:number|null;unit:string;tile:Tile;slope?:number|null}
const RANK:Record<Tone,number>={act:3,watch:2,none:1,ok:0,benefit:0};
/** Each measure's parts, from the marks set for the room (engine/assessment.py Settings), words and tones of the charter. */
function parts(v:View,r:AirRow):{lo:number;hi:number;steps:[number,number,string,string][]} {
  const ok='var(--nw-calm)',mid='color-mix(in oklab,var(--nw-calm) 50%,var(--nw-level1))',l1='var(--nw-level1)',l2='var(--nw-level2)';
  if(r.key==='co2'){const [p,a,u]=v.air_marks?.co2??[1000,1200,1600];
    return {lo:400,hi:u+400,steps:[[400,p,t('Frais'),ok],[p,a,t('Correct'),mid],[a,u,t('Renfermé'),l1],[u,u+400,t('Très renfermé'),l2]]};}
  if(r.key==='pm25'){const a=v.air_marks?.pm25??25;
    return {lo:0,hi:a*2+10,steps:[[0,10,t('Propre'),ok],[10,a,t('Moyen'),mid],[a,a*2,t('Chargé'),l1],[a*2,a*2+10,t('Très chargé'),l2]]};}
  // The VOC: an index (100 = the usual air).
  return {lo:0,hi:400,steps:[[0,150,t('Normal'),ok],[150,250,t('Élevé'),l1],[250,400,t('Très élevé'),l2]]};
}
const MUTE=['indisponible','pas de nouvelle mesure','en attente'];
function airRows(v:View,partners:View[],config:Config):AirRow[] {
  const many=partners.length>0,keys:Record<string,AirRow['key']>={'CO₂':'co2',Particules:'pm25',COV:'voc'};
  return [v,...partners].flatMap(r=>tiles(r,config).filter(x=>keys[x.label]&&!(many&&r.inherited?.[keys[x.label]]))
    .map(x=>({key:keys[x.label],label:x.label,room:many?r.title:r.inherited?.[keys[x.label]]??undefined,value:numeric(r.observations[keys[x.label]]),unit:x.unit??'',tile:x,
      slope:r.assessment.features?.trends?.curves?.[keys[x.label]]?.slope})))
    // Always the same order: CO₂, particles, VOC.
    .sort((a,b)=>['co2','pm25','voc'].indexOf(a.key)-['co2','pm25','voc'].indexOf(b.key));
}
const arc=(r:number,f:number)=>{const L=270,a0=135*Math.PI/180,a1=(135+L*f)*Math.PI/180;
  return `M${(60+r*Math.cos(a0)).toFixed(1)} ${(60+r*Math.sin(a0)).toFixed(1)} A${r} ${r} 0 ${L*f>180?1:0} 1 ${(60+r*Math.cos(a1)).toFixed(1)} ${(60+r*Math.sin(a1)).toFixed(1)}`;};
function airPanel(v:View,partners:View[],config:Config,said:Said,src?:string):TemplateResult|typeof nothing {
  const rows=airRows(v,partners,config);
  // Without an air sensor, no panel: a ventilation or a purifier stays in « Appareils ».
  if(!rows.length)return nothing;
  const ask=asking(v)&&v.assessment.needs.includes('air');
  const look=(r:AirRow)=>{const p=parts(v,r),x=r.value??p.lo,i=Math.max(0,p.steps.findIndex(([a,b])=>x>=a&&x<b)),step=x>=p.hi?p.steps[p.steps.length-1]:p.steps[i];
    const muted=r.value===null||MUTE.includes(r.tile.note),tone:Tone=muted?'none':r.tile.out?(ask?'act':'watch'):'ok';
    return {p,x,tier:x>=p.hi?p.steps.length-1:i,word:step[2],color:step[3],tone,muted};};
  const live=rows.filter(r=>!look(r).muted),lead=[...live].sort((a,b)=>RANK[look(b).tone]-RANK[look(a).tone]||look(b).tier-look(a).tier)[0];
  const center=!lead?'—':look(lead).tier===0&&look(lead).tone==='ok'?t('Air frais'):look(lead).word;
  const fill=(r:AirRow,R:number,w:number)=>{const l=look(r),f=Math.max(.04,Math.min(.999,(l.x-l.p.lo)/(l.p.hi-l.p.lo)));
    return svg`<path d=${arc(R,.999)} class="nc-ring-track" style=${`stroke-width:${w}`}></path><path d=${arc(R,f)} class="nc-ring-fill" style=${`stroke:${l.color};stroke-width:${w};--len:${(2*Math.PI*R*270/360*f).toFixed(1)}`}></path>`;};
  const rate=(r:AirRow)=>{const tr=r.tile.trend,moving=!!tr&&tr.way!=='stable'&&r.slope!=null&&Math.abs(r.slope)>=1;
    return html`<span class="nc-fx-trend" data-tone=${tr?.tone??'steady'}><span class="nw-trend nc-way" data-way=${moving?tr!.way:'stable'} data-tone=${tr?.tone??'steady'}></span>${moving?`${signed(r.slope!,0)} ${r.unit?r.unit+'/h':'/h'}`:t('stable')}</span>`;};
  const name=(r:AirRow)=>html`<span class="nc-ring-n">${tx(r.label)}${r.room?html` <small>${r.room}</small>`:nothing}</span>`;
  const open=(r:AirRow)=>(e:Event)=>{if(r.tile.entity)moreInfo(e,r.tile.entity);};
  const head=html`<div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon('air')}</span><h3>${t('Air')}</h3>${src?html`<span class="aside nc-src">${src}</span>`:nothing}</div>`;
  // One measure: its value in the ring, its word, way and note beside it.
  if(rows.length===1&&live.length===1){const r=live[0],l=look(r);
    return html`<section class="nc-mod nw-panel nc-air" data-piece="air">${head}<div class="nc-rings one">
      <button type="button" class="nc-ring" @click=${open(r)} title=${t('Détails : {label}',{label:tx(r.label)})}><svg viewBox="0 0 120 120" aria-hidden="true">${fill(r,50,10)}</svg>
        <span class="nc-ring-c"><b class="nc-ring-v">${number(r.value!)}</b><small>${r.unit}</small></span></button>
      <div class="nc-ring-side">${name(r)}<b class="nc-fx-word" style=${`--c:${C[l.tone]}`}>${l.word}</b>${rate(r)}</div></div></section>`;}
  // One ring per kind of measure (CO₂, particles, VOC), drawn for the room where it is most at stake; every room in the list.
  // A wider hole in the middle (6 November): the verdict fits inside the innermost ring.
  const R=[50,39,28],W=8,kinds=(['co2','pm25','voc'] as const).map(k=>live.filter(r=>r.key===k).sort((a,b)=>RANK[look(b).tone]-RANK[look(a).tone]||look(b).x-look(a).x)[0]).filter((r):r is AirRow=>!!r);
  // The legend (6 November): each line's mark is the rings in small, its own ring in its colour, the others faint.
  const key=(r:AirRow,color:string)=>{const at=kinds.findIndex(k=>k.key===r.key);
    return at<0?html`<i class="nc-ring-dot"></i>`:html`<svg class="nc-ring-g" viewBox="0 0 120 120" aria-hidden="true">${kinds.map((_,i)=>svg`<path d=${arc([52,36,20][i],.999)} style=${i===at&&color?`stroke:${color}`:''} class=${i===at?'on':''}></path>`)}</svg>`;};
  return html`<section class="nc-mod nw-panel nc-air" data-piece="air">${head}<div class="nc-rings">
    <div class="nc-ring"><svg viewBox="0 0 120 120" role="img" aria-label=${t('Air : {word}',{word:center})}>${kinds.map((r,i)=>fill(r,R[i],W))}</svg>
      <span class="nc-ring-c"><b style=${`--c:${C[lead?look(lead).tone:'none']}`}>${center}</b></span></div>
    <div class=${'nc-ring-list'+(rows.length>=3?' cols2':'')}>${rows.map(r=>{const l=look(r);
      return html`<button type="button" class=${'nc-ring-row'+(l.muted?' mute':'')} @click=${open(r)} title=${t('Détails : {label}',{label:tx(r.label)})}>
        ${key(r,l.muted?'':l.color)}${name(r)}<b>${l.muted?'—':html`${number(r.value!)}${r.unit?html`<small> ${r.unit}</small>`:nothing}`}</b>
        ${l.muted?html`<span class="nc-ring-w mute">${t('à vérifier · {why}',{why:tx(r.tile.note)})}</span>`:html`<span class="nc-ring-w" style=${`--c:${C[l.tone]}`}>${l.word}</span>${rate(r)}`}</button>`;})}</div>
  </div></section>`;
}

// ---------- À venir : what will change, dated, each with its source; nothing to say, no section. ----------
function coming(v:View,said:Said,plage:(s:'temperature'|'humidity')=>[number,number]|null):Coming[] {
  const a=v.assessment,f=a.features,out:Coming[]=[...said.coming],ms=(iso:unknown)=>{const d=new Date(String(iso));return isNaN(+d)?null:d.getTime();};
  // The heating's own schedule (ha-chauffage, Scheduler): its next change, cold or not.
  // Said once: when the engine already says this change (« Chauffage prévu à 20 h 30 : 20 °C visés »), its line is kept.
  const plan=f?.planned??f?.warmth?.next,next=nextChange(plan),nextAt=ms(plan?.at);
  if(next&&nextAt&&!said.coming.some(e=>e.ic==='heat'&&Math.abs(e.when-nextAt)<=5*60e3))out.push({when:nextAt,at:clockAt(nextAt),ic:'heat',text:t('Chauffage'),note:next.replace(/\s*(?:demain )?à \d{1,2} h \d{2}/,''),tone:'none'});
  if(a.rain_soon_minutes!=null){const at=Date.now()+a.rain_soon_minutes*60e3;
    out.push({when:at,at:clockAt(at),ic:'rain',text:t('Pluie'),note:t('dans {n} min · les ouvrants exposés se ferment',{n:Math.round(a.rain_soon_minutes)}),tone:'none'});}
  // The engine's next hours (engine/horizon.py): a gesture later compared with doing nothing, summer nights drawn.
  for(const h of horizonShown(f?.horizon??[],'needed')){const r=h.result;
    if(h.kind==='cool'){const at=ms(r.open_from)??Date.now();
      out.push({when:at,at:`${clockAt(at)} → ${clockAt(ms(r.open_until)??at)}`,ic:'open',text:t('Ouvrez la nuit'),note:horizonResult(h),tone:'act',chart:horizonChart(h,plage('temperature'))});continue;}
    const at=ms(r.at)??ms(h.bands[0]?.[0])??Date.now();
    // The airing of now is the banner's: « À venir » says only what follows.
    if((h.kind==='air'||h.kind==='dry')&&Math.abs(at-Date.now())<20*60e3)continue;
    if(h.kind==='air')out.push({when:at,at:clockAt(at),ic:'air',text:t('Aérez {n} min',{n:Number(r.minutes)}),
      note:r.back?t('la pièce perd {drop} °C, retrouvés vers {time}',{drop:nf(Number(r.drop)),time:clockAt(ms(r.back)!)}):t('la pièce perd {drop} °C',{drop:nf(Number(r.drop))}),tone:'act'});
    else if(h.kind==='dry')out.push({when:at,at:clockAt(at),ic:'drop',text:t('Aérez {n} min',{n:Number(r.minutes)}),note:t('{with} % d’humidité au lieu de {without} %',{with:Number(r.with),without:Number(r.without)}),tone:'act'});
    else out.push({when:at,at:clockAt(at),ic:'sun',text:t('Le soleil réchauffe la pièce'),note:r.gain!=null?t('{gain} °C vers {time}',{gain:signed(Number(r.gain)),time:clockAt(ms(r.gain_time)??at)}):undefined,tone:'benefit'});
  }
  // Without a gesture, the room doing nothing: only when it crosses its range, and when.
  const trend=(f?.horizon??[]).find(x=>x.kind==='trend'),band=plage('temperature');
  if(trend&&band&&!out.some(x=>x.chart)){const cross=crossing(trend,band);if(cross)out.push(cross);}
  return out.sort((x,y)=>x.when-y.when);
}
/** The first half hour the forecast leaves the range by half a degree, or comes back into it. */
function crossing(h:Horizon,[mn,mx]:[number,number]):Coming|null {
  const t0=new Date(h.start).getTime(),step=h.step_minutes*60e3,s=h.base,inside=(x:number)=>x>=mn&&x<=mx;
  if(!s.length)return null;
  const i=!inside(s[0])?s.findIndex(inside):s.findIndex(x=>x<mn-.5||x>mx+.5);
  if(i<=0)return null;
  const at=t0+i*step;
  return {when:at,at:clockAt(at),ic:'temp',text:!inside(s[0])?t('Revient dans votre plage'):s[i]<mn?t('Passe sous {n} °C',{n:nf(mn,mn%1?1:0)}):t('Dépasse {n} °C',{n:nf(mx,mx%1?1:0)}),note:t('sans rien faire'),tone:'none'};
}

// ---------- Appareils : one line, each device as it stands, a tap opens it. ----------
function devices(v:View,partners:View[],config:Config,src?:string):TemplateResult|typeof nothing {
  const seen=new Set<string>(),chips:{ic:string;text:string;tone:Tone;entity?:string}[]=[];
  for(const r of [v,...partners])for(const x of tiles(r,config)){
    if(!['Fenêtres','Volet','Chauffage','Purificateur','Ventilation'].includes(x.label))continue;
    const key=x.label==='Fenêtres'?x.label:x.label+(x.entity??r.title);
    if(seen.has(key))continue;seen.add(key);
    if(x.label==='Fenêtres'){const [open,all]=x.value.split('/').map(Number),flagged=x.note==='à refermer';
      chips.push({ic:x.ic,text:!open?(all>1?t('{n} fenêtres fermées',{n:all}):t('Fenêtre fermée')):flagged?t('{n} à refermer',{n:open}):tx(x.note),tone:flagged?'act':open?'benefit':'none',entity:x.entity});}
    else if(x.label==='Volet')chips.push({ic:x.ic,text:t('Volet {state}',{state:tx(x.value).toLowerCase()})+(x.out?` · ${tx(x.note)}`:''),tone:x.out?'act':'none',entity:x.entity});
    else if(x.label==='Chauffage')chips.push({ic:x.ic,text:[t('Chauffage'),tx(x.value).toLowerCase()+(x.unit?` ${x.unit}`:''),x.note?tx(x.note):''].filter(Boolean).join(' · '),tone:'none',entity:x.entity});
    else chips.push({ic:x.ic,text:`${x.label==='Ventilation'?t('VMC'):t('Purificateur')} ${tx(x.value).toLowerCase()}`,tone:x.out?'benefit':'none',entity:x.entity});
  }
  return chips.length?html`<section class="nc-fx-devices"><div class="nc-dev-h"><span class="nw-label">${t('Appareils')}</span>${src?html`<span class="nc-src">${src}</span>`:nothing}</div><div class="nw-chips">${chips.map(c=>{
    const body=html`${icon(c.ic)}${c.text}`,cls='nw-chip'+(c.tone==='none'?' nc-plain':'');
    return c.entity?html`<button type="button" class=${cls} style=${`--c:${C[c.tone]}`} @click=${(e:Event)=>moreInfo(e,c.entity!)}>${body}</button>`:html`<span class=${cls} style=${`--c:${C[c.tone]}`}>${body}</span>`;})}</div></section>`:nothing;
}

/** « À venir » in its panel: what will change, dated, each with its source; nothing to say, nothing. */
function comingList(next:Coming[]):TemplateResult {
  return html`<ol class="nc-mod nw-panel nc-coming">${next.map(e=>html`<li class="nc-ev" style=${`--c:${C[e.tone]}`}><span class="nc-ev-at">${e.at}</span><span class="nc-ev-dot" aria-hidden="true"></span>
    <div class="nc-ev-body"><b><span class="nc-ev-ic">${icon(e.ic)}</span>${e.text}</b>${e.note?html`<small>${e.note}</small>`:nothing}${e.chart?html`<div class="nc-ev-chart nc-horizon">${e.chart}</div>`:nothing}</div></li>`)}</ol>`;
}
const plageOf=(v:View)=>(s:'temperature'|'humidity'):[number,number]|null=>{const hum=v.assessment.features?.humidity,season=v.assessment.features?.season;
  return s==='humidity'?(hum?.minimum!=null&&hum?.maximum!=null?[hum.minimum,hum.maximum]:null):(season?[season.minimum,season.maximum]:null);};

/** The full card's pieces, one card each (6 November): every format draws the full card's own pieces, never older ones.
 *  « temperature » and « humidity » are the Ressenti's two halves, « air » the rings, « devices » the line of devices,
 *  « horizon » the dated « À venir », « measures » the whole « En ce moment » with the devices. Nothing to show: nothing. */
export function fullPiece(kind:'feel'|'temperature'|'humidity'|'air'|'devices'|'horizon'|'measures',v:View,config:Config,st:CardState,partners:View[],name=v.title):TemplateResult|typeof nothing {
  const said=spread(v);
  if(kind==='feel')return feelPanel(v,partners,said,st.uid,undefined,name);
  if(kind==='temperature'||kind==='humidity')return feelPanel(v,partners,said,st.uid,kind==='temperature'?'warmth':'humidity',name);
  if(kind==='air')return airPanel(v,partners,config,said,name);
  if(kind==='devices'){const d=devices(v,partners,config,name);return d===nothing?nothing:html`<div class="nc-mod nw-panel nc-devices-card">${d}</div>`;}
  if(kind==='horizon'){const next=coming(v,said,plageOf(v));
    return next.length?html`<section class="nc-part"><header class="nc-part-h nw-section-head"><h2>${t('À venir')}</h2><span class="nw-sum">${name}</span></header>${comingList(next)}</section>`:nothing;}
  const {feel,air,devs}=now(v,config,said,st.uid,partners);
  return feel===nothing&&air===nothing&&devs===nothing?nothing:html`<div class="nc-body nc-sections nc-full">${feel!==nothing||air!==nothing?html`<div class="nc-mods">${feel}${air}</div>`:nothing}${devs}</div>`;
}
/** « En ce moment » as the card's settings choose it: the Ressenti's halves, the air, the devices. */
function now(v:View,config:Config,said:Said,uid:string,partners:View[]){
  const b=nowBlocks(config),warm=b.includes('warmth'),hum=b.includes('humidity');
  return {feel:warm||hum?feelPanel(v,partners,said,uid,warm&&hum?undefined:warm?'warmth':'humidity'):nothing,
    air:b.includes('air')?airPanel(v,partners,config,said):nothing,devs:b.includes('devices')?devices(v,partners,config):nothing};
}

/** Everything below the banner of the full card; the unfolded tile shows the same, its blocks chosen in its settings. */
export function fullBody(v:View,config:Config,st:CardState,partners:View[],blocks?:readonly string[]):TemplateResult {
  const said=spread(v),plage=plageOf(v),show=(b:string)=>!blocks||blocks.includes(b);
  const parts=show('measures')?now(v,config,said,st.uid,partners):{feel:nothing,air:nothing,devs:nothing},{feel,air}=parts;
  const next=config.show_horizon===false||!show('horizon')?[]:coming(v,said,plage);
  const sensors=new Set([v,...partners].flatMap(r=>Object.values(r.observations).map(o=>o?.source).filter((x):x is string=>!!x))).size;
  const rows=[...details(v,config),...said.doubts.map(x=>html`<li><b>${t('À vérifier')}</b><span> · ${x}</span></li>`)];
  return html`<div class="nc-body nc-sections nc-full">
    ${said.tryIt?html`<p class="nc-try"><b>${t('À essayer')}</b> · ${said.tryIt}</p>`:nothing}
    ${feel!==nothing||air!==nothing?html`<section class="nc-part"><header class="nc-part-h nw-section-head"><h2>${t('En ce moment')}</h2></header><div class="nc-mods">${feel}${air}</div></section>`:nothing}
    ${next.length?html`<section class="nc-part"><header class="nc-part-h nw-section-head"><h2>${t('À venir')}</h2><span class="nw-sum">${t('ce qui va changer')}</span></header>${comingList(next)}</section>`:nothing}
    ${parts.devs}
    ${said.know.length&&(show('measures')||show('details'))?fold({label:t('Bon à savoir'),summary:String(said.know.length),open:!!st.knowOpen,onToggle:()=>st.toggle('knowOpen'),id:st.uid+'-know',
      body:html`<ul class="nc-list nc-know">${said.know.map(x=>html`<li>${x}</li>`)}</ul>`}):nothing}
    ${config.show_details===false||!show('details')?nothing:fold({label:t('Détails'),summary:html`${t('{n} capteurs',{n:sensors})}${said.doubts.length?html` · <b>${t('{n} à vérifier',{n:said.doubts.length})}</b>`:nothing}`,open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:st.uid+'-details',
      body:html`<ul class="nc-list">${rows}</ul>${st.configure?html`<button class="nw-badge nc-configure" @click=${st.configure}>${icon('settings')}${t('Configurer cette pièce')}</button>`:nothing}`})}
  </div>`;
}
