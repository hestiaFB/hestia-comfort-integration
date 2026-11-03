import {t,t as tr,fr,currentLocale} from './i18n';
import {LitElement,html,svg,css,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {hassMatters} from './hass-change';
import {property,state} from 'lit/decorators.js';

/** The comfort review (review_source.py): the home's dashboard, then one room's sheet. Graded on EN 16798-1. */
type Month={month:string};
type Grade={score:number|null;letter:string|null;comfortable:number|null;hours:number};
type Warmth=Grade&{monthly:(Month&{min:number;mean:number;max:number;cold:number;hot:number;comfortable:number;low:number;high:number})[];
 coldest:{value:number;month:string}|null;hottest:{value:number;month:string}|null;day:{winter:(number|null)[];summer:(number|null)[];outdoor_winter:(number|null)[];outdoor_summer:(number|null)[]}};
type Humidity=Grade&{dry:number;humid:number;monthly:(Month&{mean:number;humid:number})[]};
type Air=Grade&{split:number[];day:(number|null)[];monthly:(Month&{median:number})[]};
type Advice={key:string;theme:'warmth'|'humidity'|'air';level:'action'|'benefit'|'neutral';share:number|null;below?:number;hour?:number;gap?:number;rooms?:number;room?:string;entry_id?:string};
type RoomReview={entry_id:string;title:string;score:number|null;letter:string|null;themes:{warmth?:Warmth;humidity?:Humidity;air?:Air};advice?:Advice[]};
type ThemeGrade={score:number|null;letter:string|null;rooms:number};
export type Review={version:number;computed_at:string;start:string;outdoor:boolean;home:{score:number|null;letter:string|null;themes:Record<'warmth'|'humidity'|'air',ThemeGrade>;advice?:Advice[]};rooms:RoomReview[]};
type Hass={callWS:<T>(m:object)=>Promise<T>};

// « 2026-03 » as « mars » (« March »), short or long, in the user's language.
const month=(m:string,style:'short'|'long')=>{const n=Number(m.slice(5,7));return n>=1&&n<=12?new Date(2026,n-1,15).toLocaleDateString(currentLocale(),{month:style}):m;};
const monthName=(m:string)=>month(m,'short');
const longMonth=(m:string)=>month(m,'long');
const num=(v:number,d=1)=>v.toLocaleString(currentLocale(),{maximumFractionDigits:d});
const good=(l:string|null)=>l==='A'||l==='B';
const BLUE='#378ADD',BLUE_LIGHT='#85B7EB',AMBER='#EF9F27',AMBER_LIGHT='#FAC775',GREY='#888780';
const CSS_BLUE=unsafeCSS(BLUE),CSS_AMBER=unsafeCSS(AMBER);
const HEATING=[11,12,1,2,3,4],WINTER=[12,1,2],SUMMER=[6,7,8];
const inMonths=(m:string,months:number[])=>months.includes(Number(m.slice(5,7)));
const avg=(v:number[])=>v.length?v.reduce((a,b)=>a+b,0)/v.length:0;

/** One gesture and the measured fact behind it (engine/review.py advice): never a cause the sensors cannot prove. */
function adviceText(a:Advice):[string,string]{
 const share=a.share==null?'':num(a.share,0)+' %';
 switch(a.key){
  case 'heat_more':return [t('Chauffez-la davantage l’hiver'),t('Sous {below} °C {share} du temps, de novembre à avril',{share,below:num(a.below??18,0)})];
  case 'run_ventilation':return [t('Faites tourner la VMC plus longtemps'),t('Au-dessus de 70 % d’humidité {share} du temps',{share})];
  case 'air_daily':return [t('Aérez 10 minutes chaque jour'),t('Au-dessus de 70 % d’humidité {share} du temps',{share})];
  case 'air_at':return [t('Aérez 10 minutes vers {h} h',{h:a.hour??''}),t('Air à renouveler {share} du temps, surtout vers {h} h',{share,h:a.hour??''})];
  case 'open_at_night':return [t('L’été, ouvrez en grand la nuit'),t('À l’aube, dehors est {gap} °C plus frais que la maison',{gap:num(a.gap??0)})];
  case 'add_co2':return [t('Ajoutez un capteur de CO₂ dans une chambre'),(a.rooms??0)>1?t('L’air n’est mesuré que dans {n} pièces',{n:a.rooms??0}):t('L’air n’est mesuré que dans {n} pièce',{n:a.rooms??0})];
  default:return [a.key,''];
 }
}

/** A small SVG chart: `n` slots across, values scaled between `lo` and `hi`. */
function frame(n:number,lo:number,hi:number,w=320,h=140){
 const pad={l:34,r:6,t:8,b:20},slot=(w-pad.l-pad.r)/n;
 return {w,h,pad,slot,x:(i:number)=>pad.l+(i+.5)*slot,y:(v:number)=>pad.t+(1-(v-lo)/(hi-lo))*(h-pad.t-pad.b)};
}
type Frame=ReturnType<typeof frame>;
// A room's sheet spreads its charts across the page: wider, not taller.
const WIDE=720,TALL=190;
function axes(f:Frame,ticks:number[],unit:string,labels:string[],every=1){
 return svg`${ticks.map(t=>svg`<line x1=${f.pad.l} x2=${f.w-f.pad.r} y1=${f.y(t)} y2=${f.y(t)} class="grid"/><text x=${f.pad.l-4} y=${f.y(t)+3} text-anchor="end" class="tick">${num(t,0)}${unit}</text>`)}
  ${labels.map((l,i)=>i%every?nothing:svg`<text x=${f.x(i)} y=${f.h-6} text-anchor="middle" class="tick">${l}</text>`)}`;
}
const line=(f:Frame,values:(number|null)[])=>values.map((v,i)=>v==null?null:`${f.x(i)},${f.y(v)}`).filter(Boolean).join(' ');
const band=(f:Frame,low:number[],high:number[])=>[...high.map((v,i)=>`${f.x(i)},${f.y(v)}`),...low.map((v,i)=>`${f.x(i)},${f.y(v)}`).reverse()].join(' ');

export class ComfortReview extends LitElement {
 @property({attribute:false}) hass?:Hass;
 /** The room whose sheet is shown; none for the home's dashboard. */
 @property({attribute:false}) room?:string;
 /** « summary »: the note, the four themes and the most pressing piece of advice, for a dashboard card. */
 @property() mode:'page'|'summary'='page';
 @state() private data?:Review;
 @state() private error='';
 @state() private season:'winter'|'summer'='winter';
 private asked=false;
 static styles=css`
  :host{display:block;--rv-surface:var(--nc-surface,var(--card-background-color,#222932));--rv-muted:var(--nc-muted,var(--secondary-text-color,#bdc5d1));--rv-border:var(--nc-border,var(--divider-color,#657386))}
  h1{margin:0;font-size:24px;font-weight:600}h2{margin:0;font-size:17px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px}
  .muted{color:var(--rv-muted);font-size:14px}.small{font-size:12px}
  .top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:16px}
  .note{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:16px;border-radius:14px;background:var(--rv-surface)}
  .scale{display:flex;align-items:center;gap:4px}.scale span{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:600;background:color-mix(in srgb,var(--rv-muted) 14%,transparent);color:var(--rv-muted)}
  .scale span.on{width:46px;height:46px;font-size:22px}
  .scale span.on.good{background:color-mix(in srgb,${CSS_BLUE} 30%,transparent);color:var(--nc-accent,#a1c9e8)}.scale span.on.bad{background:color-mix(in srgb,${CSS_AMBER} 30%,transparent);color:var(--nc-todo,#f2a65a)}
  .letter{display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:28px;border-radius:8px;font-weight:600}
  .letter.big{min-width:46px;height:46px;font-size:22px;border-radius:12px}
  .good{background:color-mix(in srgb,${CSS_BLUE} 24%,transparent);color:var(--nc-accent,#a1c9e8)}.bad{background:color-mix(in srgb,${CSS_AMBER} 26%,transparent);color:var(--nc-todo,#f2a65a)}
  .none{background:color-mix(in srgb,var(--rv-muted) 14%,transparent);color:var(--rv-muted);font-size:12px;padding:0 8px;font-weight:500}
  .panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px;margin-top:16px}
  .panel{background:var(--rv-surface);border-radius:14px;padding:14px 16px}
  .headline{font-size:16px;font-weight:600;margin:6px 0 2px}
  .rooms{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-top:8px}
  .room{display:flex;justify-content:space-between;align-items:center;gap:8px;background:var(--rv-surface);border:1px solid transparent;border-radius:12px;padding:10px 12px;cursor:pointer;color:inherit;font:inherit;text-align:left}
  .room:hover,.room:focus-visible{border-color:var(--rv-border)}
  section.theme{border-top:1px solid color-mix(in srgb,var(--rv-border) 50%,transparent);padding:18px 0 6px;margin-top:12px}
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:10px 0}
  .stat{background:var(--rv-surface);border-radius:10px;padding:8px 10px}.stat b{display:block;font-size:19px;font-weight:600}
  .chips{display:flex;gap:6px;flex-wrap:wrap}.chip{font-size:12px;padding:3px 10px;border-radius:999px}
  .back{background:none;border:none;color:var(--nc-accent,#a1c9e8);font:inherit;font-size:14px;cursor:pointer;padding:0;margin-bottom:10px}
  .seg{display:flex;gap:4px}.seg button{font:inherit;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--rv-border);background:none;color:inherit;cursor:pointer}.seg button.on{background:color-mix(in srgb,${CSS_BLUE} 25%,transparent)}
  svg{width:100%;height:auto;display:block;margin-top:6px}svg .grid{stroke:color-mix(in srgb,var(--rv-muted) 22%,transparent);stroke-width:.5}svg .tick{fill:var(--rv-muted);font-size:9px}
  .legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--rv-muted);margin-top:4px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
  details{margin-top:10px;font-size:14px}summary{cursor:pointer;color:var(--rv-muted)}details p{color:var(--rv-muted);line-height:1.6}
  .notice{padding:12px 14px;border-radius:12px;background:var(--rv-surface)}
  .advice{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin-top:8px}
  .tip{display:block;text-align:left;font:inherit;color:inherit;background:var(--rv-surface);border:1px solid transparent;border-radius:12px;padding:10px 12px}
  .tip.action{border-color:color-mix(in srgb,${CSS_AMBER} 55%,transparent)}.tip.benefit{border-color:color-mix(in srgb,#639922 60%,transparent)}
  button.tip{cursor:pointer}button.tip:hover{background:color-mix(in srgb,var(--rv-surface) 80%,var(--rv-border))}
  .tip b{display:block;font-size:15px;font-weight:600;margin:2px 0}
  .sheet{max-width:900px}
  /* Animations on arrival: bars grow, lines draw, the grade and the panels rise; none when the system asks for less motion. */
  @keyframes rv-rise{from{opacity:0;transform:translateY(8px)}}@keyframes rv-grow-y{from{transform:scaleY(0)}}@keyframes rv-grow-x{from{transform:scaleX(0)}}
  @keyframes rv-draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}@keyframes rv-fade{from{opacity:0}}@keyframes rv-pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.08)}}
  @keyframes rv-turn{from{opacity:0;transform:rotate(-90deg)}}
  @media (prefers-reduced-motion:no-preference){
   .note,.panel,.room,.tip,section.theme,.stat{animation:rv-rise .45s ease-out both}
   .panel:nth-child(2),.room:nth-child(2),.tip:nth-child(2),.stat:nth-child(2){animation-delay:.06s}.panel:nth-child(3),.room:nth-child(3),.tip:nth-child(3),.stat:nth-child(3){animation-delay:.12s}
   .panel:nth-child(4),.room:nth-child(4),.tip:nth-child(4),.stat:nth-child(4){animation-delay:.18s}.panel:nth-child(n+5),.room:nth-child(n+5),.tip:nth-child(n+5),.stat:nth-child(n+5){animation-delay:.24s}
   .scale span.on,.letter.big{animation:rv-pop .5s .15s ease-out both}
   svg .bar{transform-box:fill-box;transform-origin:bottom;animation:rv-grow-y .7s .1s cubic-bezier(.2,.8,.2,1) both}
   svg .hbar{transform-box:fill-box;transform-origin:left;animation:rv-grow-x .7s .1s cubic-bezier(.2,.8,.2,1) both}
   svg .draw{stroke-dasharray:1;animation:rv-draw 1.1s .15s ease-out both}
   svg .fade,svg .dot{animation:rv-fade .5s .7s both}
   svg .ring{transform-box:view-box;transform-origin:50% 50%;animation:rv-turn .8s ease-out both}
  }
  button.summary{display:block;width:100%;text-align:left;font:inherit;color:inherit;background:none;border:none;padding:0;cursor:pointer}
 `;
 connectedCallback(){super.connectedCallback();if(this.hass&&!this.asked)void this.load();}
 protected shouldUpdate(changed:PropertyValues){return hassMatters(changed,this.hass);}
 protected updated(){if(this.hass&&!this.asked)void this.load();}
 private async load(){this.asked=true;this.error='';
  try{this.data=await this.hass!.callWS<Review>({type:'hestia_comfort/review'});}
  catch(e){this.error=typeof e==='object'&&e&&'message' in e?String((e as {message:string}).message):t('connexion indisponible');}
 }
 private go(room?:string){this.room=room;this.dispatchEvent(new CustomEvent('review-navigate',{detail:room?'bilan/'+room:'bilan',bubbles:true,composed:true}));}
 private letter(l:string|null,big=false){return l?html`<span class=${'letter '+(big?'big ':'')+(good(l)?'good':'bad')}>${l}</span>`:html`<span class="letter none">${t('sans note')}</span>`;}
 private period(){const d=this.data!;return t('De {from} à {to}',{from:`${longMonth(d.start.slice(0,7))} ${d.start.slice(0,4)}`,to:`${longMonth(d.computed_at.slice(0,7))} ${d.computed_at.slice(0,4)}`});}
 private how(){return html`<details><summary>${t('Comment est calculée la note ?')}</summary><p>${t('Chaque heure est classée selon la norme européenne EN 16798-1 et reçoit des points : 100 en confort élevé, 75 en confort normal, 50 en confort modéré, 0 en dehors. La note est la moyenne, de 0 à 100 : A dès 85, B dès 70, C dès 55, D dès 40, E en dessous. Une pièce est notée sur ce qu’elle mesure, le logement sur la moyenne de ses pièces. Il faut deux semaines de mesures pour noter un thème.')}</p></details>`;}

 render(){
  if(this.error)return html`<p class="notice" role="alert">${t('Le bilan n’a pas pu être chargé : {error}.',{error:this.error})} <button @click=${()=>this.load()}>${t('Réessayer')}</button></p>`;
  if(!this.data)return html`<p class="muted" role="status">${t('Calcul du bilan sur les douze derniers mois…')}</p>`;
  if(this.mode==='summary')return this.summary();
  const room=this.room?this.data.rooms.find(r=>r.entry_id===this.room):undefined;
  return room?this.sheet(room):this.dashboard();
 }

 /** The dashboard card's summary: the note, a letter per theme, the most pressing advice; « review-open » asks for the rest. */
 private summary(){
  const h=this.data!.home,names={warmth:t('Chaleur'),humidity:t('Humidité'),air:t('Air')},order={action:0,benefit:1,neutral:2};
  const first=[...(h.advice??[])].sort((a,b)=>order[a.level]-order[b.level])[0],[title,why]=first?adviceText(first):['',''];
  const open=()=>this.dispatchEvent(new CustomEvent('review-open',{bubbles:true,composed:true}));
  return html`<button class="summary" @click=${open} aria-label=${t('Ouvrir le bilan du logement')}>
   <div class="note"><div class="scale">${['A','B','C','D','E'].map(l=>html`<span class=${l===h.letter?'on '+(good(l)?'good':'bad'):''}>${l}</span>`)}</div>
    <div><div class="headline">${h.score==null?t('Pas encore de note'):t('Confort : {score} / 100',{score:h.score})}</div><div class="muted small">${t('Sur les douze derniers mois')}</div></div></div>
   <div class="chips" style="margin-top:10px">${(['warmth','humidity','air'] as const).map(k=>h.themes[k].letter?html`<span class=${'chip '+(good(h.themes[k].letter)?'good':'bad')}>${names[k]} ${h.themes[k].letter}</span>`:html`<span class="chip none">${names[k]} · ${t('sans note')}</span>`)}</div>
   ${first?html`<div class=${'tip '+first.level} style="margin-top:10px"><span class="muted small">${first.room??t('Toute la maison')}</span><b>${title}</b><span class="muted small">${why}</span></div>`:html`<p class="muted">${t('Rien à signaler : aucun problème qui dure.')}</p>`}
  </button>`;
 }

 // The home: its note, one panel per theme, its rooms.
 private dashboard(){
  const d=this.data!,h=d.home;
  if(!d.rooms.length)return html`<p class="notice">${t('Aucune pièce Hestia Confort chargée.')}</p>`;
  const warm=d.rooms.map(r=>r.themes.warmth).filter((w):w is Warmth=>!!w&&w.score!=null);
  return html`<div class="top"><div><h1>${t('Votre maison')}</h1><p class="muted">${this.period()}</p></div></div>
   <div class="note"><div class="scale">${['A','B','C','D','E'].map(l=>html`<span class=${l===h.letter?'on '+(good(l)?'good':'bad'):''}>${l}</span>`)}</div>
    <div><div class="headline">${h.score==null?t('Pas encore de note'):t('Confort : {score} / 100',{score:h.score})}</div><div class="muted">${this.homeLine(warm)}</div><div class="muted small">${t('Selon la norme européenne EN 16798-1')}</div></div></div>
   ${this.how()}
   <div class="panels">${this.warmthPanel(warm)}${this.humidityPanel()}${this.airPanel()}${this.energyPanel()}</div>
   ${this.adviceList(h.advice??[],true)}
   <h2 style="margin-top:20px">${t('Vos pièces')}</h2>
   <div class="rooms">${[...d.rooms].sort((a,b)=>(b.score??-1)-(a.score??-1)).map(r=>html`<button class="room" @click=${()=>this.go(r.entry_id)}><span>${r.title}<br><span class="muted small">${r.score==null?t('pas encore assez de mesures'):r.score+' / 100'}</span></span>${this.letter(r.letter)}</button>`)}</div>`;
 }
 /** The pieces of advice, as cards: on the home's page each names its room and opens its sheet. */
 private adviceList(list:Advice[],home=false){
  if(!list.length)return home?html`<h2 style="margin-top:20px">${t('Nos conseils')}</h2><p class="muted">${t('Rien à signaler : aucun problème qui dure dans vos pièces.')}</p>`:nothing;
  const order={action:0,benefit:1,neutral:2};
  return html`${home?html`<h2 style="margin-top:20px">${t('Nos conseils')}</h2>`:nothing}<div class="advice">${[...list].sort((a,b)=>order[a.level]-order[b.level]).map(a=>{const [title,why]=adviceText(a);
   const body=html`<span class="muted small">${a.room??t('Toute la maison')}</span><b>${title}</b><span class="muted small">${why}</span>`;
   return home&&a.entry_id?html`<button class=${'tip '+a.level} @click=${()=>this.go(a.entry_id)}>${body}</button>`:html`<div class=${'tip '+a.level}>${home?body:html`<b>${title}</b><span class="muted small">${why}</span>`}</div>`;})}</div>`;
 }
 private homeLine(warm:Warmth[]){
  const h=this.data!.home;if(h.score==null)return '';
  const weak=(['warmth','humidity','air'] as const).filter(k=>h.themes[k].score!=null).sort((a,b)=>h.themes[a].score!-h.themes[b].score!)[0];
  const winterCold=avg(warm.flatMap(w=>w.monthly.filter(m=>inMonths(m.month,HEATING)).map(m=>m.cold)));
  const label=h.score>=85?t('Très bon'):h.score>=70?t('Bon dans l’ensemble'):h.score>=55?t('Correct'):t('À améliorer');
  const point=weak==='warmth'?(winterCold>=30?t('l’hiver est le point faible'):t('la chaleur est le point faible')):weak==='humidity'?t('l’humidité est le point faible'):t('l’air est le point faible');
  return `${label} · ${point}`;
 }
 /** Month by month, the mean over the graded rooms of the time too cold, comfortable and too hot. */
 private warmthPanel(warm:Warmth[]){
  const t=this.data!.home.themes.warmth;
  const months=[...new Set(warm.flatMap(w=>w.monthly.map(m=>m.month)))].sort().slice(-12);
  const at=(m:string,k:'cold'|'comfortable'|'hot')=>avg(warm.flatMap(w=>w.monthly.filter(x=>x.month===m).map(x=>x[k])));
  const winter=avg(months.filter(m=>inMonths(m,HEATING)).map(m=>at(m,'cold'))),summer=avg(months.filter(m=>inMonths(m,SUMMER)).map(m=>at(m,'hot')));
  const headline=winter>=30&&summer>=30?tr('frais l’hiver, chaud l’été'):winter>=30?tr('un peu frais l’hiver'):summer>=30?tr('chaud l’été'):tr('confortable toute l’année');
  const f=frame(months.length||1,0,100);
  return html`<div class="panel"><h2><span>${tr('Chaleur')}</span>${this.letter(t.letter)}</h2>
   <div class="headline">${t.score==null?tr('Pas encore de note'):`${t.score} / 100 · ${headline}`}</div><div class="muted small">${tr('Part du temps, pièces chauffées, mois par mois')}</div>
   <svg viewBox="0 0 ${f.w} ${f.h}" role="img" aria-label=${tr('Part du temps trop frais, confortable et trop chaud, mois par mois')}>${axes(f,[0,50,100],' %',months.map(monthName))}
    ${months.map((m,i)=>{const c=at(m,'cold'),o=at(m,'comfortable'),hot=at(m,'hot'),x=f.x(i)-f.slot*.32,w=f.slot*.64;
     return svg`<rect class="bar" x=${x} width=${w} y=${f.y(c)} height=${f.y(0)-f.y(c)} fill=${BLUE_LIGHT}/><rect class="bar" x=${x} width=${w} y=${f.y(c+o)} height=${f.y(c)-f.y(c+o)} fill=${BLUE}/><rect class="bar" x=${x} width=${w} y=${f.y(c+o+hot)} height=${f.y(c+o)-f.y(c+o+hot)} fill=${AMBER}/>`;})}</svg>
   <div class="legend"><span><i style="background:${BLUE_LIGHT}"></i>${tr('trop frais')}</span><span><i style="background:${BLUE}"></i>${tr('confortable')}</span><span><i style="background:${AMBER}"></i>${tr('trop chaud')}</span></div></div>`;
 }
 private humidityPanel(){
  const t=this.data!.home.themes.humidity,rows=this.data!.rooms.filter(r=>r.themes.humidity?.score!=null).sort((a,b)=>b.themes.humidity!.score!-a.themes.humidity!.score!);
  const worst=[...rows].sort((a,b)=>b.themes.humidity!.humid-a.themes.humidity!.humid)[0];
  const headline=worst&&worst.themes.humidity!.humid>=30?tr('{room} trop humide',{room:worst.title}):tr('bonne dans les pièces');
  const h=Math.max(40,rows.length*22+8);
  return html`<div class="panel"><h2><span>${tr('Humidité')}</span>${this.letter(t.letter)}</h2>
   <div class="headline">${t.score==null?tr('Pas encore de note'):`${t.score} / 100 · ${headline}`}</div><div class="muted small">${tr('Note de chaque pièce sur 100')}</div>
   <svg viewBox="0 0 320 ${h}" role="img" aria-label=${tr('Note d’humidité de chaque pièce')}>${rows.map((r,i)=>{const s=r.themes.humidity!.score!,y=6+i*22;
    return svg`<text x="0" y=${y+11} class="tick" style="font-size:10px">${r.title}</text><rect x="96" y=${y} width="200" height="14" rx="4" fill=${GREY} fill-opacity=".18"/><rect class="hbar" x="96" y=${y} width=${2*s} height="14" rx="4" fill=${s>=70?BLUE:AMBER_LIGHT}/><text x="302" y=${y+11} class="tick" style="font-size:10px">${s}</text>`;})}</svg></div>`;
 }
 private airPanel(){
  const t=this.data!.home.themes.air,rooms=this.data!.rooms.filter(r=>r.themes.air?.score!=null);
  if(!rooms.length)return html`<div class="panel"><h2><span>${tr('Air')}</span>${this.letter(null)}</h2><div class="headline">${tr('Pas de capteur de CO₂')}</div><div class="muted small">${tr('Un capteur de CO₂ dans une pièce suffit à noter son air.')}</div></div>`;
  const split=[0,1,2].map(i=>avg(rooms.map(r=>r.themes.air!.split[i])));
  return html`<div class="panel"><h2><span>${tr('Air')}</span>${this.letter(t.letter)}</h2>
   <div class="headline">${t.score} / 100 · ${good(t.letter)?tr('air sain'):tr('à renouveler plus souvent')}</div><div class="muted small">${tr('CO₂, part du temps')} · ${rooms.map(r=>r.title).join(', ')}${rooms.length<this.data!.rooms.length?(rooms.length>1?tr(', seules pièces équipées'):tr(', seule pièce équipée')):''}</div>
   <div style="display:flex;align-items:center;gap:16px">${this.donut(split)}<div class="legend" style="flex-direction:column;gap:4px;font-size:13px">
    <span><i style="background:${BLUE}"></i>${tr('{n} % très bon',{n:num(split[0],0)})}</span><span><i style="background:${AMBER_LIGHT}"></i>${tr('{n} % correct',{n:num(split[1],0)})}</span><span><i style="background:${AMBER}"></i>${tr('{n} % à renouveler',{n:num(split[2],0)})}</span></div></div></div>`;
 }
 private donut(parts:number[]){
  let at=0;const r=40,c=2*Math.PI*r,colors=[BLUE,AMBER_LIGHT,AMBER];
    // Each part starts at the top by its offset (a quarter turn back), not by a rotate attribute: the animation turns the
  // whole group, and a CSS rotation would replace the attribute and swing the parts around another centre.
  return svg`<svg viewBox="0 0 100 100" style="width:110px;flex:none" role="img" aria-label=${t('Répartition du temps selon la qualité de l’air')}><g class="ring">${parts.map((p,i)=>{const seg=svg`<circle cx="50" cy="50" r=${r} fill="none" stroke=${colors[i]} stroke-width="14" stroke-dasharray=${`${c*p/100} ${c}`} stroke-dashoffset=${c/4-c*at/100}/>`;at+=p;return seg;})}</g></svg>`;
 }
 private energyPanel(){
  return html`<div class="panel"><h2><span>${t('Énergie')}</span><span class="letter none">${t('sans note')}</span></h2><div class="headline">${t('Bientôt')}</div><div class="muted small">${t('La consommation du chauffage, comparée à la météo de chaque mois.')}</div></div>`;
 }

 // One room: its note, then each theme it measures.
 private sheet(r:RoomReview){
  const th=r.themes,names={warmth:t('Chaleur'),humidity:t('Humidité'),air:t('Air')};
  const chips=(['warmth','humidity','air'] as const).map(k=>th[k]?.score!=null?html`<span class=${'chip '+(good(th[k]!.letter)?'good':'bad')}>${names[k]} ${th[k]!.letter} · ${th[k]!.score}</span>`
   :html`<span class="chip none">${names[k]} · ${th[k]?t('pas encore assez de mesures'):k==='warmth'?t('non notée'):t('pas de capteur')}</span>`);
  const best=this.data!.rooms.filter(x=>x.score!=null).sort((a,b)=>b.score!-a.score!)[0];
  return html`<div class="sheet"><button class="back" @click=${()=>this.go()}><i class="nw-chev" style="--r:180deg"></i> ${t('Votre maison')}</button>
   <div class="top"><div><h1>${r.title}</h1><p class="muted">${r.score==null?t('Pas encore assez de mesures pour une note'):t('Confort : {score} / 100',{score:r.score})+(best?.entry_id===r.entry_id&&this.data!.rooms.length>1?' · '+t('la plus confortable de la maison'):'')}</p></div>${this.letter(r.letter,true)}</div>
   <div class="chips">${chips}</div>
   ${th.warmth?this.warmthSection(th.warmth,this.tips(r,'warmth')):nothing}${th.humidity?this.humiditySection(th.humidity,this.tips(r,'humidity')):nothing}${th.air?this.airSection(th.air,this.tips(r,'air')):nothing}</div>`;
 }
 /** A theme's advice in a room's sheet; « Rien à faire » in blue when its grade is good and nothing is advised. */
 private tips(r:RoomReview,theme:Advice['theme']){
  const list=(r.advice??[]).filter(a=>a.theme===theme);
  if(list.length)return this.adviceList(list);
  return good(r.themes[theme]?.letter??null)?html`<p class="tip" style="background:color-mix(in srgb,${BLUE} 18%,transparent);color:var(--nc-accent,#a1c9e8)">${theme==='warmth'?t('Rien à faire, la chaleur est bonne'):theme==='humidity'?t('Rien à faire, l’humidité est bonne'):t('Rien à faire, l’air est sain')}</p>`:nothing;
 }
 private stat(label:string,value:string,note:string){return html`<div class="stat"><span class="muted small">${t(label)}</span><b>${value}</b><span class="muted small">${note}</span></div>`;}
 private warmthSection(w:Warmth,tips:unknown=nothing){
  const m=w.monthly.slice(-12);if(!m.length)return nothing;
  const lo=Math.floor(Math.min(...m.map(x=>Math.min(x.min,x.low))))-1,hi=Math.ceil(Math.max(...m.map(x=>Math.max(x.max,x.high))))+1,f=frame(m.length,lo,hi,WIDE,TALL);
  return html`<section class="theme"><h2><span>${t('Chaleur')}</span>${this.letter(w.letter)}</h2>
   <div class="stats">${this.stat(fr('Confortable'),w.comfortable==null?'—':w.comfortable+' %',t('du temps, selon la norme'))}
    ${w.coldest?this.stat(fr('Au plus froid'),num(w.coldest.value)+' °C',t('en {month}',{month:longMonth(w.coldest.month)})):nothing}${w.hottest?this.stat(fr('Au plus chaud'),num(w.hottest.value)+' °C',t('en {month}',{month:longMonth(w.hottest.month)})):nothing}</div>
   <div class="muted small">${t('Mois par mois · le plus bas, la moyenne et le plus haut · bande bleue = zone de la norme')}</div>
   <svg viewBox="0 0 ${f.w} ${f.h}" role="img" aria-label=${t('Température mois par mois et zone de confort de la norme')}>${axes(f,[lo+1,Math.round((lo+hi)/2),hi-1],'°',m.map(x=>monthName(x.month)))}
    <polygon points=${band(f,m.map(x=>x.low),m.map(x=>x.high))} fill=${BLUE} fill-opacity=".14"/>
    ${m.map((x,i)=>svg`<rect class="bar" x=${f.x(i)-f.slot*.18} width=${f.slot*.36} y=${f.y(x.max)} height=${f.y(x.min)-f.y(x.max)} rx="3" fill=${GREY} fill-opacity=".35"/>`)}
    <polyline class="draw" pathLength="1" points=${line(f,m.map(x=>x.mean))} fill="none" stroke=${BLUE} stroke-width="2.5"/>${m.map((x,i)=>svg`<circle class="dot" cx=${f.x(i)} cy=${f.y(x.mean)} r="2.5" fill=${BLUE}/>`)}</svg>
   <p class="muted small">${t('La zone s’élargit l’été : sans climatisation, la norme accepte plus de chaleur après des jours chauds.')}</p>
   ${this.day(w)}${tips}</section>`;
 }
 private day(w:Warmth){
  const s=this.season,room=s==='winter'?w.day.winter:w.day.summer,out=s==='winter'?w.day.outdoor_winter:w.day.outdoor_summer;
  const known=room.filter((v):v is number=>v!=null);
  const months=w.monthly.filter(x=>inMonths(x.month,s==='winter'?WINTER:SUMMER)),low=months.length?avg(months.map(x=>x.low)):20,high=months.length?avg(months.map(x=>x.high)):25;
  const values=[...known,...out.filter((v):v is number=>v!=null)],lo=Math.floor(Math.min(low,...values))-1,hi=Math.ceil(Math.max(high,...values))+1,f=frame(24,lo,hi,WIDE,TALL);
  const min=Math.min(...known),max=Math.max(...known);
  return html`<div style="display:flex;justify-content:space-between;align-items:center;margin-top:14px;gap:8px;flex-wrap:wrap"><span class="muted small">${t('Une journée type · la pièce et dehors')}</span>
    <span class="seg"><button class=${s==='winter'?'on':''} @click=${()=>this.season='winter'}>${t('Hiver')}</button><button class=${s==='summer'?'on':''} @click=${()=>this.season='summer'}>${t('Été')}</button></span></div>
   ${known.length?html`<svg viewBox="0 0 ${f.w} ${f.h}" role="img" aria-label=${t('Température heure par heure, une journée type')}>${axes(f,[lo+1,Math.round((lo+hi)/2),hi-1],'°',Array.from({length:24},(_,i)=>t('{n} h',{n:i})),4)}
    <rect x=${f.pad.l} width=${f.w-f.pad.l-f.pad.r} y=${f.y(high)} height=${f.y(low)-f.y(high)} fill=${BLUE} fill-opacity=".14"/>
    <polyline class="fade" points=${line(f,out)} fill="none" stroke=${GREY} stroke-width="1.5" stroke-dasharray="4 3"/><polyline class="draw" pathLength="1" points=${line(f,room)} fill="none" stroke=${BLUE} stroke-width="2.5"/></svg>
   <div class="legend"><span><i style="background:${BLUE}"></i>${t('la pièce')}</span><span><i style="background:${GREY}"></i>${t('dehors')}</span></div>
   <p class="muted small">${s==='winter'?t('L’hiver, la pièce descend vers {min} °C à {at} h et monte vers {max} °C à {top} h.',{min:num(min),at:room.indexOf(min),max:num(max),top:room.indexOf(max)}):t('L’été, la pièce reste entre {min} et {max} °C au fil de la journée.',{min:num(min),max:num(max)})}</p>`
   :html`<p class="muted small">${s==='winter'?t('Pas encore de mesures cet hiver.'):t('Pas encore de mesures cet été.')}</p>`}`;
 }
 private humiditySection(h:Humidity,tips:unknown=nothing){
  const m=h.monthly.slice(-12);if(!m.length)return nothing;
  const f=frame(m.length,20,90,WIDE,TALL),inside=Math.round(100-h.dry-h.humid);
  return html`<section class="theme"><h2><span>${t('Humidité')}</span>${this.letter(h.letter)}</h2>
   <div class="stats">${this.stat(fr('Bonne'),inside+' %',t('entre 25 et 60 %'))}${this.stat(fr('Trop sec'),num(h.dry,0)+' %',t('sous 25 %'))}${this.stat(fr('Trop humide'),num(h.humid,0)+' %',t('au-dessus de 60 %'))}</div>
   <div class="muted small">${t('Humidité moyenne, mois par mois · bande bleue = zone de la norme')}</div>
   <svg viewBox="0 0 ${f.w} ${f.h}" role="img" aria-label=${t('Humidité moyenne mois par mois')}>${axes(f,[30,60,90],' %',m.map(x=>monthName(x.month)))}
    <rect x=${f.pad.l} width=${f.w-f.pad.l-f.pad.r} y=${f.y(60)} height=${f.y(25)-f.y(60)} fill=${BLUE} fill-opacity=".14"/>
    <polyline class="draw" pathLength="1" points=${line(f,m.map(x=>x.mean))} fill="none" stroke=${BLUE} stroke-width="2.5"/>${m.map((x,i)=>svg`<circle class="dot" cx=${f.x(i)} cy=${f.y(x.mean)} r="2.5" fill=${x.mean>60?AMBER:BLUE}/>`)}</svg>${tips}</section>`;
 }
 private airSection(a:Air,tips:unknown=nothing){
  const known=a.day.filter((v):v is number=>v!=null);if(!known.length)return nothing;
  const peak=Math.max(...known),worst=a.day.indexOf(peak),hi=Math.max(900,Math.ceil(peak/100)*100+100),f=frame(24,400,hi,WIDE,TALL);
  return html`<section class="theme"><h2><span>${t('Air')}</span>${this.letter(a.letter)}</h2>
   <div class="stats">${this.stat(fr('Très bon'),num(a.split[0],0)+' %',t('du temps'))}${this.stat(fr('Le moins bon'),t('{n} h',{n:worst}),t('en moyenne'))}${this.stat(fr('À renouveler'),num(a.split[2],0)+' %',t('du temps'))}</div>
   <div class="muted small">${t('CO₂ moyen selon l’heure de la journée')}</div>
   <svg viewBox="0 0 ${f.w} ${f.h}" role="img" aria-label=${t('CO₂ moyen heure par heure')}>${axes(f,[400,Math.round((400+hi)/200)*100,hi],'',Array.from({length:24},(_,i)=>t('{n} h',{n:i})),4)}
    ${a.day.map((v,i)=>v==null?nothing:svg`<rect class="bar" x=${f.x(i)-f.slot*.35} width=${f.slot*.7} y=${f.y(v)} height=${f.y(400)-f.y(v)} rx="2" fill=${v>=950?AMBER:v>=700?AMBER_LIGHT:BLUE_LIGHT}/>`)}</svg>${tips}</section>`;
 }
}

// The hub's panel and the dashboard card may both load it: defined once.
if(!customElements.get('hestia-comfort-review'))customElements.define('hestia-comfort-review',ComfortReview);
declare global{interface HTMLElementTagNameMap{'hestia-comfort-review':ComfortReview}}
