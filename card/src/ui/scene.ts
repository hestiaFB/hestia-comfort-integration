import {html,type TemplateResult} from 'lit';
import {unsafeHTML} from 'lit/directives/unsafe-html.js';
import type {Level,View} from '../types';

/** The banner's scene (2 November, maquettes/prototype-carte-piece.html): the window seen a little from the side, its sky
 *  the hour's, the main sash open or about to open, a sheer curtain and what the air carries; or the VMC, or the radiator.
 *  It stands where the round pictogram stood, on the left of the advice. */
export type Hour='dawn'|'day'|'dusk'|'night';
/** Which way the air goes through the open sash, and what it carries. */
export type Flow='in-cold'|'in-rain'|'in-humid'|'in-heat'|'in-dust'|'out-humid'|'out-heat'|'out-stale';
export interface Scene {k:'win'|'vmc'|'rad';m?:'open'|'invite'|'closed';flow?:Flow;sky?:'rain'|'storm';hour:Hour;clock?:string;shutter?:boolean}

/** The hour of the sky from the sun's height: night below -6°, dawn or dusk under 6°, day above. */
export function hourOf(elevation:number|null|undefined,at:Date=new Date()):Hour {
  if(elevation===null||elevation===undefined){const h=at.getHours();return h<6||h>=21?'night':h<9?'dawn':h>=18?'dusk':'day';}
  return elevation< -6?'night':elevation<6?(at.getHours()<12?'dawn':'dusk'):'day';
}

/** The scene of an advice, from its gesture (the pictogram it had) and the room's reason; null keeps the pictogram
 *  (sensors loading or silent, « regardez dehors », the purifier). */
export function sceneFor(s:{title:string;disk:string;level?:Level},v:View):Scene|null {
  const a=v.assessment,hour=hourOf(a.sun?.elevation,new Date(v.computed_at||Date.now()));
  const opened=(a.openings??[]).some(o=>o.open===true);
  const going=/^(Encore |Laissez ouvert|Aération en cours)/.test(s.title);
  // What leaves while the room airs: stale air, damp, or the day's heat.
  const leaving:Flow=a.needs.includes('air')?'out-stale':a.needs.includes('dry')?'out-humid':a.needs.includes('cool')?'out-heat':'out-stale';
  const at=/vers (\d{1,2} h(?: \d{2})?)/.exec(s.title)?.[1];
  // Raining now, whatever the advice: the window's sky shows it (the rain sensor, else the engine's constraint).
  const wet=v.observations?.rain?.value===true||a.constraints?.includes('rain');
  const sc=pick(s,v,hour,opened,going,leaving,at);
  return sc&&wet&&sc.k==='win'&&!sc.sky&&!sc.shutter?{...sc,sky:'rain'}:sc;
}

function pick(s:{title:string;disk:string;level?:Level},v:View,hour:Hour,opened:boolean,going:boolean,leaving:Flow,at:string|undefined):Scene|null {
  const reason=v.assessment.reason,a=v.assessment;
  switch(s.disk){
    case 'rain':return /avant/.test(s.title)?{k:'win',m:'open',flow:'in-cold',sky:'storm',hour}:{k:'win',m:'open',flow:'in-rain',sky:'rain',hour};
    case 'shut':{
      if(/^Vous pouvez refermer/.test(s.title))return {k:'win',m:'open',hour};
      const flow:Flow=reason==='rehumidification_risk'?'in-humid':reason==='voc_outdoor'?'in-dust':reason==='sun_entering'?'in-heat'
        :reason==='exchange_harmful'&&(a.temperature_delta??0)>0?'in-heat':'in-cold';
      return {k:'win',m:'open',flow,hour};}
    case 'open':case 'air':
      if(s.title==='Rien à faire')return {k:'win',m:'open',hour};
      if(going)return {k:'win',m:'open',flow:reason==='warming_possible'?'in-heat':leaving,hour};
      return {k:'win',m:opened?'open':'invite',...(opened?{flow:leaving}:{}),hour};
    case 'moon':
      if(going)return {k:'win',m:'open',flow:'out-heat',hour:'night'};
      return {k:'win',m:at?'closed':'invite',hour:'night',...(at?{clock:at}:{})};
    case 'clock':
      if(s.level==='neutral')return null;
      return {k:'win',m:'closed',hour:at?'day':hour,clock:at??'Plus tard'};
    case 'vmc':return {k:'vmc',hour};
    case 'heat':case 'flame':return {k:'rad',hour};
    case 'window':return s.title==='Adaptez les volets'||/volet/i.test(s.title)?{k:'win',m:'closed',shutter:true,hour:'day'}:{k:'win',m:'closed',hour,clock:'Plus tard'};
    case 'check':case 'drop':return {k:'win',m:opened?'open':'closed',hour};
  }
  return null;
}

// ---------- The drawing ----------
const SKY:Record<string,{a:string;b:string;sun?:string;x?:number;y?:number}>={
  dawn:{a:'#f7d3b9',b:'#cbd3ee',sun:'#ffe0b0',x:24,y:62},day:{a:'#9ccff4',b:'#e6f3ff',sun:'#fff1bf',x:68,y:28},
  dusk:{a:'#f2a982',b:'#7a7db7',sun:'#ffcf9c',x:74,y:62},night:{a:'#15213e',b:'#33456d',sun:'#eef1ff',x:66,y:26},
  rain:{a:'#66768c',b:'#aab6c6'},rainNight:{a:'#141c2e',b:'#2c3850'},storm:{a:'#8d98a8',b:'#d7e6f5',sun:'#fff1bf',x:76,y:30}};
// The colour of what the air carries, its outline, and which way it goes.
const AIR:Record<Flow,[string,string,string]>={'in-cold':['#eaf6ff','rgba(30,80,140,.55)','in'],'in-rain':['#dcecfb','rgba(30,70,120,.75)','in rainy'],
  'in-humid':['#ffffff','rgba(70,80,92,.5)','in'],'in-heat':['var(--nw-heat)','rgba(110,50,15,.45)','in'],'in-dust':['#a8968a','rgba(60,40,25,.35)','in dust'],
  'out-humid':['#ffffff','rgba(70,80,92,.5)','out'],'out-heat':['var(--nw-heat)','rgba(110,50,15,.45)','out'],'out-stale':['#9d9ba8','rgba(40,40,52,.3)','out stale']};
let uid=0;

function sky(sc:Scene):string {
  const kind=sc.sky??sc.hour,k=SKY[kind==='rain'&&sc.hour==='night'?'rainNight':kind],night=kind==='night'||sc.hour==='night';let body='';
  if(kind==='rain')body=Array.from({length:11},(_,i)=>`<i class="nsc-drop" style="left:${(i*37+7)%96}%;animation-delay:-${(i*0.27).toFixed(2)}s;animation-duration:${(.6+(i%4)*.12).toFixed(2)}s"></i>`).join('');
  else if(kind==='storm')body=`<i class="nsc-sun" style="left:${k.x}%;top:${k.y}%"></i><i class="nsc-cloud dark" style="left:4%;top:24%"></i>`;
  else if(night)body=`<i class="nsc-moon" style="left:${k.x}%;top:${k.y}%"></i>`+[[18,20],[40,12],[30,46],[84,48],[56,40]].map(([x,y],i)=>`<i class="nsc-star" style="left:${x}%;top:${y}%;animation-delay:-${i*.7}s"></i>`).join('');
  else body=`<i class="nsc-sun${sc.shutter?' big':''}" style="left:${sc.shutter?62:k.x}%;top:${sc.shutter?70:k.y}%"></i>`+(kind==='day'&&!sc.shutter?'<i class="nsc-cloud" style="left:14%;top:40%"></i>':'');
  const hill=night?'#0d1730':kind==='rain'?'color-mix(in srgb,#5f7a74 80%,transparent)':'color-mix(in srgb,#7fa99a 75%,transparent)';
  return `<div class="nsc-sky" style="--sa:${k.a};--sb:${k.b};--sun:${k.sun??'#fff'};--hill:${hill}">${body}<i class="nsc-hill"></i></div>`;
}
// The sheer curtain, hung in front of the fixed pane: still, blown into the room, or drawn toward the opening.
const voile=()=>{const id='nscv'+(++uid);return `<div class="nsc-voile"><svg viewBox="0 0 40 90" preserveAspectRatio="none" aria-hidden="true">
  <defs><linearGradient id="${id}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".78"/><stop offset=".2" stop-color="#fff" stop-opacity=".5"/><stop offset=".4" stop-color="#fff" stop-opacity=".74"/><stop offset=".62" stop-color="#fff" stop-opacity=".46"/><stop offset=".82" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity=".42"/></linearGradient></defs>
  <path d="M0 0H40V84Q34 90 27 86T13 87 0 85Z" fill="url(#${id})" stroke="color-mix(in srgb,var(--nw-fg) 22%,transparent)" stroke-width=".6"/>
  <path d="M8 0V86M17 0V87M26 0V86M34 0V87" stroke="color-mix(in srgb,var(--nw-fg) 10%,transparent)" stroke-width=".7"/></svg></div>`;};
// What the air carries: born small in the opening, far away, it grows as it comes to us; leaving, the other way.
const MOTES=[[74,30,-26,20,2.4,0],[84,46,-22,26,2.8,-.7],[70,58,-30,18,2.2,-1.4],[80,70,-18,22,2.6,-.35],[76,40,-34,30,3,-1.9],[86,62,-24,16,2.3,-1.1]];
const motes=()=>`<div class="nsc-motes">${MOTES.map(([x,y,dx,dy,d,l])=>`<i class="nsc-mote" style="--x0:${x}px;--y0:${y}px;--x1:${x+dx}px;--y1:${y+dy}px;--d:${d}s;--l:${l}s"></i>`).join('')}</div>`;
// The rain that comes in is never drawn over the panes: drops bounce off the sill, a puddle spreads below.
const rainIn=()=>`<div class="nsc-rain-in"><i class="nsc-puddle"></i>${[[18,-4,0],[40,3,-.25],[62,-3,-.5],[84,4,-.15],[30,5,-.6],[72,-5,-.38]].map(([x,dx,l])=>`<i class="nsc-hop" style="left:${x}%;--dx:${dx}px;animation-delay:${l}s"></i>`).join('')}
  ${[25,55,80].map((x,i)=>`<i class="nsc-splash" style="left:${x}%;animation-delay:-${(i*.3).toFixed(1)}s"></i>`).join('')}</div>`;
// « 15 h » or « Plus tard », facing us, out of the perspective.
const clock=(label:string)=>`<div class="nsc-clk"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="var(--c)" stroke-width="2.4"/><path d="M12 12h4" stroke="var(--nw-fg)" stroke-width="2.2" stroke-linecap="round"/><path class="nsc-mn" d="M12 12V6" stroke="var(--nw-fg)" stroke-width="1.8" stroke-linecap="round"/></svg>${label.replace(/[<>&]/g,'')}</div>`;
// The VMC breathes the room's damp in: big near us, it shrinks into the mouth.
const VMC=[[10,18,2.6,0],[100,26,2.9,-.8],[6,86,2.4,-1.5],[102,94,2.7,-.4],[34,110,2.5,-1.9],[80,4,2.8,-1.1]];

function draw(sc:Scene):string {
  if(sc.k==='win'){
    const st=sc.m==='open'?'open':sc.m==='invite'?'invite':'',air=sc.flow?AIR[sc.flow]:null;
    return `<div class="nsc ${st} ${air?air[2]:''}" style="${air?`--wc:${air[0]};--wh:${air[1]}`:''}"><div class="nsc-obj nsc-fr">${sky(sc)}${sc.shutter?'<i class="nsc-coffre"></i><i class="nsc-tablier"></i>':''}<div class="nsc-pane nsc-pl"></div><div class="nsc-pane nsc-pr"><i class="nsc-handle"></i></div></div><i class="nsc-rod"></i>${voile()}${sc.clock?clock(sc.clock):''}
      ${air?(sc.flow==='in-rain'?rainIn():motes()):''}</div>`;
  }
  if(sc.k==='vmc'){
    const blades=[0,120,240].map(r=>`<path d="M27 27 C27 14 36 9 41 13 C44 17 38 24 27 27Z" fill="color-mix(in srgb,var(--nw-fg) 55%,var(--nw-bg))" transform="rotate(${r} 27 27)"/>`).join('');
    const rings=[29,22,15].map(r=>`<circle cx="33" cy="33" r="${r}" fill="none" stroke="var(--nsc-frame)" stroke-width="1.4"/>`).join('');
    return `<div class="nsc out" style="--wc:#ffffff;--wh:rgba(70,80,92,.5)"><div class="nsc-obj"><i class="nsc-plate"></i><div class="nsc-mouth"><svg class="nsc-blades" viewBox="0 0 54 54" aria-hidden="true">${blades}<circle cx="27" cy="27" r="4" fill="var(--nw-fg)"/></svg>
      <svg class="nsc-grille" viewBox="0 0 66 66" aria-hidden="true">${rings}</svg></div></div>
      <div class="nsc-motes">${VMC.map(([x,y,d,l])=>`<i class="nsc-mote" style="--x0:54px;--y0:58px;--x1:${x}px;--y1:${y}px;--d:${d}s;--l:${l}s"></i>`).join('')}</div></div>`;
  }
  const waves=`<svg class="nsc-heat" viewBox="0 0 96 46" preserveAspectRatio="none" aria-hidden="true">${[24,48,72].map(x=>`<path d="M${x} 42 c-6 -7 6 -12 0 -19 c-6 -7 6 -12 0 -19"/>`).join('')}</svg>`;
  return `<div class="nsc"><div class="nsc-obj">${waves}<i class="nsc-rad"></i><i class="nsc-feet" style="left:14px"></i><i class="nsc-feet" style="right:14px"></i></div></div>`;
}
/** The scene, drawn once from fixed pieces (no text from the house but the hour, stripped of markup). */
export const scene=(sc:Scene):TemplateResult=>html`${unsafeHTML(draw(sc))}`;
