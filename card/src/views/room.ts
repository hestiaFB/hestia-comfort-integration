import {factBox3,slides3,why3} from './advisor3';
import {html,svg,nothing,LitElement,type TemplateResult} from 'lit';
import {property,state} from 'lit/decorators.js';
import {SCALE_MARKS,CHIPS,TILE_BLOCKS,DETAIL_ROWS,INSIGHT_TOPICS,PIECES,type Piece,type Config,type View,type Level,type Format,type BannerBlock,type Chip,type HorizonSubject,type Horizon} from '../types';
import {numeric,number,heatingLabels,coverageText,windFrom,sourceLabel,needs as needLabels,constraintLabels,shortWhy} from '../view';
import {icon} from '../ui/icons';
import {echelle,echellePos} from '../ui/hestia-echelle';
import {lecture} from '../ui/hestia-lecture';
import {scene,sceneFor,type Scene} from '../ui/scene';
import {feelPanel} from './feel';
import {horizonBox,horizonChart,horizonHead,horizonResult,horizonLegend,horizonShown} from './horizon';
import {t,t as tr,tx,tl} from '../i18n';

/** The level, said in two or three words: the colour is never the only signal. */
// Versatile Thermostat's presets and the reasons it stops by itself, in the person's words.
const presetWord=(p:string|null)=>!p?'mode réduit':p.includes('frost')?'hors-gel':p.includes('away')?'absence':p.includes('eco')?'éco':p;
const offWords:Record<string,string>={window:'fenêtre ouverte',auto_start_stop:'arrêt automatique',sleep:'veille',safety:'sécurité',central_mode:'mode central',inhibition:'délestage'};

/** The banner's mood, which sets the ring and the light: « Au mieux » is calm, but not « Tout va bien ». */
export const mood=(s:{level:Level;pill?:string}|undefined,level:Level)=>s?.pill==='Au mieux'?'best':s?.level??level;
/** Each pill carries its mark, so states read apart without relying on colour alone. */
const PILL_MARKS:Record<string,string>={'Tout va bien':'check','Au mieux':'best','Conseil optimisé':'flask','Trop frais':'temp','Démarrage':'clock','Capteurs muets':'mute','Un capteur muet':'mute','Plus tard':'clock'};
const LEVEL_MARKS:Record<string,string>={calm:'check',benefit:'spark',action:'hand',urgent:'alert',neutral:'help'};
export const pillMark=(pill:string,level:Level,learned=false)=>html`<span class="nc-mark">${icon(learned?'flask':PILL_MARKS[pill]??LEVEL_MARKS[level]??'info')}${tx(pill)}</span>`;
export const pills:Record<Level,string>={calm:'Tout va bien',benefit:'À saisir',action:'Geste conseillé',urgent:'Attention',neutral:'À vérifier'};
/** The banner's pill, the room's state alone (30 October, evening): what the advice learned or what is out goes elsewhere. */
const STATE_PILLS=new Set(['Tout va bien','Au mieux','À saisir','Geste conseillé','Attention','À vérifier','Démarrage','Capteurs muets','Un capteur muet']);
export const statePill=(s:{level:Level;pill?:string}|undefined,level:Level)=>s?.pill&&STATE_PILLS.has(s.pill)?s.pill:pills[s?.level??level];
const hour=(iso:string)=>{const h=new Date(iso).getHours();return h===0?'minuit':h===12?'midi':h+' h';};
/** « 15 h 20 », to the five minutes: when to shut before a coming rain. */
const rainClock=(d:Date)=>{const m=Math.floor(d.getMinutes()/5)*5;return d.getHours()+' h'+(m?' '+String(m).padStart(2,'0'):'');};
const b=(text:string)=>html`<b>${text}</b>`;
const deg=(v:number|null)=>v===null?'—':number(v)+' °C';

export interface Advice {title:string;line:TemplateResult|string;disk:string;cap?:string;
  /** Learned on this room by its twin: the basis, said under the gesture (« d'après 31 aérations »). */ learned?:string;
  /** A state that is not advice (sensors loading or silent) brings its own words and colour. */ pill?:string;level?:Level;
  /** The banner's scene (window, VMC, radiator) in place of the pictogram; none keeps the pictogram. */ scene?:Scene|null}
/** Reasons that only say « keep closed »: the engine lowers them to calm when nothing is open and no reflex is at stake. */
const QUIET=['drying_unavailable','drying_slow','drying_night','drying_alone','opening_blocked','cooling_unavailable','precool_later'];
/** The banner: the gesture in a few words, then why in one line. The full explanation stays behind « i ». */
/** The room cannot be read: its temperature or three sensors silent. The banner then says so, and nothing that
 * supposes an advice (a result, an airing) is said under it. One or two late secondary sensors leave the advice. */
const unreadable=(v:View)=>{const failed=v.assessment.missing.filter(k=>!!v.observations[k]&&k!=='pollution');return failed.includes('indoor_temperature')||failed.length>=3;};
/** A pill names what is out; « votre plage » is kept for the temperature's range. */
const NEED_PILLS:Record<string,string>={dry:'Trop humide',heat:'Trop frais',cool:'Trop chaud',air:'Air à renouveler'};
/** …and its disk shows the measure's own pictogram: the tick is kept for « nothing to report ». */
const NEED_DISKS:Record<string,string>={dry:'drop',heat:'temp',cool:'temp',air:'air'};
/** A cool room that asks no gesture is no problem to the person: the heating takes care of it, nobody is home, the
 * outdoor air or the room itself warms it, or it is within the tolerance. Only a room clearly cold with no heating
 * known keeps its « Trop frais »: Hestia cannot say who warms it, and « Tout va bien » would be wrong. */
export const coldSettled=(a:View['assessment'])=>{const w=a.features?.warmth;
  return !w||w.slight||w.heating!=null||!!w.thermostat||w.occupied===false||!!w.outdoor_warms||!!w.warming;};
const SEASON_NAMES:Record<string,string>={spring:'printemps',summer:'été',autumn:'automne',winter:'hiver'};
export function humidityLabel(v:View):string|null {
  if(numeric(v.observations.indoor_humidity)===null)return null;
  const humidity=v.assessment.features?.humidity;
  if(!humidity?.status)return v.assessment.needs.includes('dry')?'Trop humide':null;
  if(humidity.status==='unknown')return null;
  if(humidity.status==='normal')return 'Dans votre plage';
  const wet=humidity.status==='high';
  return humidity.degree===1?(wet?'Légèrement humide':'Légèrement sec'):humidity.degree===3?(wet?'Très humide':'Très sec'):(wet?'Air humide':'Air sec');
}
// Mirrored word for word by custom_components/hestia_comfort/engine/verdict.py for the entities: tests/test_verdict_parity.py.
export function advice(v:View):Advice {
  const out=withLearning(v,gesture(v));
  // The gesture made, the window open while it still helps: nothing better to do, in blue. « Vous pouvez refermer » is orange again.
  if((/^(Encore |Laissez ouvert)/.test(out.title)||out.title==='Aération en cours')&&['action','benefit'].includes(v.assessment.level))
    return {...out,pill:'Au mieux',level:'calm'};
  const humidity=v.assessment.features?.humidity,label=humidityLabel(v);
  if(label&&humidity?.status&&v.assessment.reason!=='shared_volume'&&['calm','neutral'].includes(v.assessment.level)&&!unreadable(v)
      &&v.assessment.action!=='fermer'&&!v.assessment.needs.some(need=>need!=='dry'&&need!=='precool'&&(need!=='heat'||!coldSettled(v.assessment)))){
    if(humidity.status==='normal'&&out.pill==='Trop humide')return {...out,pill:undefined,disk:'check',level:v.assessment.level};
    // Out of range with nothing better to do: « Au mieux », in blue; « À savoir » says what and why.
    if(humidity.status==='low'||humidity.status==='high')return {...out,pill:'Au mieux',disk:'drop',level:'calm'};
  }
  // To close, say which window: in a shared air it may be in the other room.
  if(v.assessment.action==='fermer'&&!out.cap){
    const open=(v.assessment.openings??[]).filter(o=>o.open).map(o=>v.names?.[o.entity_id]??o.entity_id);
    if(open.length)return {...out,cap:open.length>2?`${open.length} ouvertures`:open.join(' et ')};
  }
  return out;
}
function gesture(v:View):Advice {
  // One verdict per shared air: the room shows the leading room's advice, with that room's measures.
  const vol=v.assessment.features?.volume;
  if(v.assessment.reason==='shared_volume'&&vol?.assessment){
    const lead=advice({...v,observations:vol.observations??v.observations,assessment:{...v.assessment,...vol.assessment,features:{...v.assessment.features,...vol.assessment.features,volume:undefined}} as View['assessment']});
    // « Même air » is said in « À savoir », under the banner.
    return lead;
  }
  const a=v.assessment,o=v.observations,ti=numeric(o.indoor_temperature);
  const opened=Object.entries(o).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true);
  const first=(a.open_first??[]).map(id=>v.names?.[id]??id)[0];
  const slot=a.slot;
  const duration=a.features?.ventilation?.duration_minutes;
  // The banner compares instead of asserting: the reader sees the two values the advice is based on.
  const te=numeric(o.outdoor_temperature),hi=numeric(o.indoor_humidity),incoming=a.features?.humidity?.incoming_relative??null;
  const temps=html`${deg(ti)} dedans, ${b(deg(te)+' dehors')}`;
  // Humidity in plain words: where the outdoor air would bring the room once warmed inside.
  // Once learned, the room's own past airings say where the humidity would really go.
  const drying=a.features?.drying??null;
  const water=(()=>{
    // The room's own measure, as on its tile; the drop is the one learned for its air.
    if(drying){const now=Math.round(hi??drying.now),after=Math.round((hi??drying.now)-drying.gain),outside=numeric(o.outdoor_humidity);
      return outside!==null&&Math.round(outside)>=now
        ?html`Dehors ${Math.round(outside)} %, mais l’air froid contient peu d’eau : ${b('environ '+after+' %')} après l’aération`
        :html`${now} % d’humidité, ${b('environ '+after+' %')} après l’aération`;}
    if(incoming==null||hi===null)return html`L’air du dehors est ${b('plus sec')}`;
    const target=Math.round(incoming),now=Math.round(hi),outside=numeric(o.outdoor_humidity);
    // The trap: a cold outdoor air at 79 % holds little water. Say it, or the advice looks wrong.
    if(target<now&&outside!==null&&Math.round(outside)>=now)
      return html`Dehors ${Math.round(outside)} %, mais l’air froid contient peu d’eau : réchauffé chez vous, il ferait ${b(target+' %')}`;
    return target<now?html`${now} % d’humidité, l’air du dehors la ferait ${b('descendre à '+target+' %')}`
      :target>now?html`${now} % d’humidité, l’air du dehors la ferait ${b('monter à '+target+' %')}`
      :html`${now} % d’humidité, l’air du dehors ${b('ne la changerait pas')}`;
  })();
  // How long, under the disk: the duration first, then where to open.
  const span=duration?`${duration.min} à ${duration.max} min`:undefined;
  // The airing time is part of the gesture: in the title, before opening and while the window is open.
  const opened_for=a.features?.ventilation?.opened_minutes??null;
  const airing=(verb:string,fallback:string,line:TemplateResult|string):Advice=>{
    if(a.action==='ok'){
      if(duration&&opened_for!=null){const left=Math.round(duration.max-opened_for);
        return left>0?{title:`Encore ${left} min d’aération`,line,disk:'open',cap:`ouvert depuis ${Math.round(opened_for)} min`}
          :{title:'Vous pouvez refermer',line,disk:'shut',cap:`ouvert depuis ${Math.round(opened_for)} min`};}
      return {title:'Aération en cours',line,disk:'open',cap:span?`${span} au total`:undefined};
    }
    // A later rain bounds the airing: the window is shut five minutes before it.
    const rain=a.features?.rain_ahead,shut=rain&&rain.minutes<=(duration?.max??15)+15?rainClock(new Date(new Date(v.computed_at).getTime()+(rain.minutes-5)*60000)):null;
    return {title:span?`${verb} ${span}`:fallback,line,disk:'open',cap:shut?`Refermez avant ${shut}`:first};
  };
  const constraint=a.constraints.find(c=>c!=='heating_running'&&c!=='frost')??a.constraints[0];
  // A silent sensor is not advice: the banner says what Hestia cannot see, the tiles show which ones.
  const failed=a.missing.filter(k=>!!o[k]&&k!=='pollution'),count=failed.length;
  const blind=unreadable(v);
  if(blind&&v.starting)return {title:'Mesures en chargement',line:html`Home Assistant ${b('vient de démarrer')}`,disk:'clock',pill:'Démarrage',level:'neutral'};
  if(blind){const one=count===1;
    return {title:'Mesures absentes',line:html`${b(`${count} capteur${one?'':'s'} ne répond${one?'':'ent'} pas`)} · détail dans Mesures`,disk:'mute',pill:'Capteurs muets',level:'neutral'};}
  // « Do not open » to someone who was not opening brings nothing: the banner stays calm, the measure on its tile.
  // The banner only ever carries a gesture; what is merely worth knowing goes to « À savoir » below.
  const quiet=(QUIET.includes(a.reason)&&(a.level==='calm'||a.level==='neutral'))||['humid_outdoor','open_neutral','drying_unavailable'].includes(a.reason)
    ||(a.reason==='drying_slow'&&a.features?.air?.ventilation?.on!==false)||(a.reason==='heat_needed'&&a.action!=='fermer'&&a.level!=='action');
  if(quiet&&a.action!=='fermer'){
    // Already open, « opening would bring nothing » reads as a contradiction: open or shut makes no difference.
    // A measure out of range with nothing to do about it: not « Tout va bien », only nothing better to do.
    // Opening is held back (rain, gusts, outdoor air): not that it would bring nothing; « À savoir » says why.
    // A warm room in winter: opening would cool it, but too fast; the season, not the physics, says no.
    const winterWarm=a.features?.season?.group==='winter'&&a.needs.includes('cool');
    // A measure named beside « Rien à faire » reads as « do something »: with nothing better to do the pill says
    // « Au mieux », in blue, and « À savoir » says what is out and why. Only a room clearly cold with no heating
    // known keeps « Trop frais »: someone could warm it, Hestia cannot tell who.
    const unsettled=a.needs.includes('heat')&&!coldSettled(a),first=unsettled?'heat':a.needs.includes('dry')?'dry':a.needs[0];
    return {title:'Rien à faire',line:opened&&a.features?.open_warms?html`L’air du dehors, plus doux, ${b('réchauffe la pièce')}`:opened?html`Ouverte ou fermée, ${b('cela ne change rien')}`:a.reason==='opening_blocked'?html`Aérer ${b('n’est pas possible')} pour l’instant`
      :a.reason==='drying_night'?html`La nuit, ${b('aérez plutôt au réveil')}`
      :a.reason==='drying_alone'?html`Elle ${b('sèche d’elle-même')}, fenêtres fermées`
      :winterWarm?html`Ouvrir la ${b('refroidirait trop vite')} en hiver`:html`Ouvrir ${b('n’apporterait rien')} pour l’instant`,disk:opened?'open':'check',cap:opened?'Fenêtre ouverte':undefined,
      // The pill names what is out, never « plage »: that word is the temperature's range alone.
      ...(a.needs.length?{pill:unsettled?NEED_PILLS.heat:'Au mieux',level:(unsettled?'neutral':'calm') as Level,...(opened?{}:{disk:NEED_DISKS[first]??'info'})}:{})};}
  switch(a.reason){
    case 'within_comfort': return {title:'Rien à faire',line:html`${deg(ti)}, ${b('dans votre plage')}`,disk:opened?'open':'check',cap:opened?'Fenêtre ouverte':undefined};
    case 'rain_open_windows': return {title:'Fermez, il pleut',line:html`La pluie ${b('entre par les ouvrants exposés')}`,disk:'rain'};
    case 'gust_open_windows': return {title:'Fermez, vent fort',line:html`Les rafales ${b('dépassent votre seuil')}`,disk:'shut'};
    case 'alarm_open': return {title:'Refermez',line:html`L’alarme est armée ${b(a.features?.household?.alarm?.state==='armed_night'?'pour la nuit':'en absence')}`,disk:'shut'};
    case 'rain_soon': return {title:'Refermez avant la pluie',line:html`Pluie ${b(rainWhen(a))}`,disk:'rain'};
    case 'opening_blocked': {
      const why=constraint==='rain_soon'?`Pluie ${rainWhen(a)}`:constraint?constraintLabels[constraint]??constraint:'Contrainte extérieure';
      return {title:a.action==='fermer'?'Refermez':'Gardez fermé',line:html`${b(why)}${a.needs.length?' : le besoin attendra':''}`,disk:a.action==='fermer'?'shut':'window'};
    }
    case 'short_air_change': return {title:a.action==='ok'?'Aération en cours':'Aérez 5 minutes',line:html`${a.needs.includes('air')?'Air à renouveler':'Humidité à évacuer'}, ${b(shortWhy(a.constraints))}`,disk:'open',cap:a.action==='ok'?undefined:'Puis refermez'};
    case 'air_needed': return airing('Aérez','Renouvelez l’air',airWhy(v));
    case 'cooling_possible': return airing('Ouvrez','Ouvrez pour rafraîchir',temps);
    // Warming has no airing time: an open window is kept open while the outside stays milder.
    case 'warming_possible': return a.action==='ok'?{title:'Laissez ouvert',line:html`L’air du dehors, plus doux, ${b('réchauffe la pièce')}`,disk:'open',cap:first}:{title:'Ouvrez pour réchauffer',line:temps,disk:'open',cap:first};
    case 'precool_possible': return {title:a.action==='ok'?'Laissez ouvert cette nuit':'Ouvrez pour la nuit',line:html`Demain sera chaud : ${b('stockez le frais')}`,disk:'moon',cap:first};
    case 'precool_later':
    case 'cooling_unavailable':
      return slot&&slot.kind==='open'?{title:`Ouvrez vers ${hour(slot.time)}`,line:html`Il fera ${b(number(slot.temperature)+' °C')} dehors`,disk:'moon',cap:slot.wind_bearing!=null?windFrom(slot.wind_bearing):undefined}
        :{title:'Gardez fermé',line:html`Il ne fait ${b('pas plus frais dehors')} pour l’instant`,disk:'clock'};
    case 'shared_volume': {
      // Rooms open onto each other share one air: this one follows the room whose reason weighs more.
      const vol=a.features?.volume,lead=vol?.lead??'La pièce voisine',why=vol?SHARED[vol.reason]??'le demande':'le demande';
      const line=html`${b(lead)} ${why}`;
      return a.action==='fermer'?{title:'Refermez',line,disk:'shut',cap:'Même air'}
        :a.action==='ok'?{title:'Laissez ouvert',line,disk:'open',cap:'Même air'}
        :{title:'Aérez',line,disk:'open',cap:first??'Même air'};
    }
    case 'drying_possible': {const out=airing('Aérez','Aérez pour assécher',water);
      // « Environ 66 % après l’aération » from this room's own airings: its flask, even before « Conseil optimisé ».
      return (drying?.openings??0)>=5&&!out.learned?{...out,learned:`d’après ${drying!.openings} aérations`}:out;}
    case 'drying_later': {const later=drying?.later;
      // The figure comes from this room's own airings once five are learned: the pill says it with its flask.
      return later?{title:`Aérez vers ${hour(later.time)}`,line:html`L’air sera plus sec : ${b('environ '+Math.round(later.after)+' %')} après ${later.minutes} min`,disk:'clock',...((drying?.openings??0)>=5?{learned:`d’après ${drying!.openings} aérations`}:{})}
        :{title:'Aérez plus tard',line:water,disk:'clock'};}
    case 'drying_slow': {
      const line=drying?slowWindow(drying):water;
      return {title:'Lancez la VMC',line,disk:'vmc',cap:'Aérer assèche peu ici'};
    }
    case 'ventilation_possible': return {title:'Lancez la VMC',line:html`${b(number(hi)+' %')} d’humidité, la fenêtre la baisse à peine`,disk:'vmc',cap:'Elle assèchera mieux'};
    case 'exchange_harmful': return {title:'Refermez',line:html`L’air du dehors ${b(a.temperature_delta!==null&&a.temperature_delta>0?'réchauffe la pièce':'refroidit la pièce')}`,disk:'shut'};
    case 'rehumidification_risk': return {title:'Refermez',line:incoming!=null?water:html`L’air du dehors ${b('est plus humide')}`,disk:'shut'};
    case 'voc_outdoor': return {title:'Refermez',line:html`L’air du dehors ${b('fait monter le COV')}`,disk:'shut'};
    // A cold room asks for a gesture only when someone is home and the heating is off.
    case 'warm_walls': {const w=a.features?.warm_walls;
      return {title:'Chauffez un peu plus',line:w?html`Visez ${b(deg(w.target))} : des murs plus chauds ne moisissent pas`:html`Des murs plus chauds ${b('ne moisissent pas')}`,disk:'heat',cap:'Risque de moisissure'};}
    case 'heat_needed': return a.action==='fermer'?{title:'Refermez',line:html`Pièce fraîche : ${b(deg(ti))}`,disk:'shut'}
      :{title:'Rallumez le chauffage',line:html`${b(deg(ti))}, sous votre plage`,disk:'heat',cap:'Le chauffage est coupé'};
    case 'sun_entering': return {title:'Fermez côté soleil',line:html`Le soleil ${b('chauffe la pièce')}`,disk:'shut'};
    case 'shutter_protection': return {title:'Adaptez les volets',line:html`Le soleil ${b('tape sur une façade')}`,disk:'window'};
    case 'optional_air_change': return {title:'Aérez si possible',line:html`CO₂ ${b(number(numeric(o.co2))+' ppm')}`,disk:'open'};
    case 'verify_exterior': {
      const gesture=a.needs.includes('air')?'Renouvelez l’air':a.needs.includes('cool')?'Ouvrez pour rafraîchir':a.needs.includes('dry')?'Aérez pour assécher':'Vérifiez dehors';
      return {title:gesture,line:html`${outsideGaps(v)} : ${b('regardez dehors avant')}`,disk:'ask',cap:'Si le temps le permet'};
    }
    case 'incomplete_data': {
      // One or two secondary sensors silent, nothing else to say: a calm banner, the silent tile shows it.
      return failed.length?{title:'Rien à faire',line:html`${b(coverageText(v).replace(/^Mesures à vérifier : /,''))} ne répond pas`,disk:'check',pill:failed.length>1?'Capteurs muets':'Un capteur muet',level:'neutral'}
        :{title:'Bilan partiel',line:html`${b('Rien à signaler')} dans les mesures connues`,disk:'check'};
    }
  }
  // Any other combination still names a gesture, from the action, never the level's word.
  return a.action==='fermer'?{title:'Refermez',line:'',disk:'shut'}:a.action==='ouvrir'?{title:'Aérez',line:'',disk:'open'}:{title:'Rien à faire',line:'',disk:'check'};
}
/** A window that renews little air: what it would really gain, never « 85 → 85 % ». */
const slowWindow=(d:{gain:number}):TemplateResult=>{const g=Math.round(d.gain);
  return g<1?html`Aérer ${b('ne la baisserait presque pas')}`:html`Aérer ne la baisserait ${b(`que de ${g} point${g>1?'s':''}`)}`;};
/** A gesture the twin has learned in this room: the predicted result replaces the general explanation. */
function withLearning(v:View,out:Advice):Advice {
  const l=v.assessment.features?.learned;
  // « Refermez », learned: what the open window takes from the room in half an hour.
  if(l?.closing&&v.assessment.action==='fermer')
    return {...out,line:html`Ouverte, de ${b(number(l.now))} à ${b(number(l.after)+' °C')} en ${l.minutes} min`,learned:'appris dans cette pièce',pill:'Conseil optimisé'};
  if(!l||!['ouvrir','ok'].includes(v.assessment.action))return out;
  const unit=l.measure==='temperature'?' °C':l.measure==='co2'?' ppm':l.measure==='voc'?'':' %',fmt=(x:number)=>l.measure==='temperature'?number(x):number(Math.round(x));
  const label=l.measure==='co2'?'CO₂ ':l.measure==='voc'?'COV ':'';
  // The learned duration replaces the general span: the title and the promise say the same minutes.
  const title=v.assessment.action==='ouvrir'&&/^(Aérez|Ouvrez) /.test(out.title)?`${out.title.split(' ')[0]} ${l.minutes} min`:out.title;
  return {...out,title,line:html`${label}de ${b(fmt(l.now))} à ${b(fmt(l.after)+unit)} en ${l.minutes} min`,learned:`d’après ${l.openings} aérations`,pill:'Conseil optimisé'};
}
/** Where the twin stands, when the advice is only estimated: said in « À savoir », never in the banner. */
function learning(v:View):Fact|null {
  const t=v.twin,gestureNow=['action','urgent','benefit'].includes(v.assessment.level);
  // Only a gesture that announces a result (open, keep open) can have it estimated: « Refermez » promises none.
  if(!t||!gestureNow||v.assessment.features?.learned||!['ouvrir','ok'].includes(v.assessment.action)||unreadable(v))return null;
  // What the gesture is about, and what that measure still lacks: its result is then estimated.
  const g=t.progress,a=v.assessment,ready=g?.ready;
  if(g&&ready){
    const kind=a.reason==='drying_possible'||a.reason==='ventilation_possible'?'humidity':['air_needed','short_air_change','optional_air_change'].includes(a.reason)?'air'
      :['cooling_possible','precool_possible','warming_possible'].includes(a.reason)?'temperature':null;
    if(!kind)return null;
    const n=g.seen.airings,p=t.precision,week=t.status==='ready'&&t.days>=7;
    const why=!week?`${Math.max(1,Math.floor(t.days))} jour${Math.floor(t.days)>1?'s':''} de mesures sur 7`
      :kind==='humidity'?(n<5?`humidité : ${n} aération${n>1?'s':''} sur 5`:!p||p.humidity>3?'humidité : prévisions pas encore assez justes':null)
      :kind==='temperature'?((g.seen.open??6)<6?'température : fenêtre pas assez ouverte ce mois-ci':!p||p.temperature>0.5?'température : prévisions pas encore assez justes':null)
      :'air : pas encore vu fenêtre ouverte';
    return why?{ic:'clock',title:'Apprentissage',text:`${why}, résultat estimé`}:null;}
  // A room is learned after a week of measures at least, then only if its twin replays the last day well.
  if(t.status!=='ready'||t.days<7)return {ic:'clock',title:'Apprentissage',text:`en cours : ${Math.max(1,Math.floor(t.days))} jour${Math.floor(t.days)>1?'s':''} sur 7`};
  if(!t.precision)return {ic:'clock',title:'Apprentissage',text:'vérification en attente : il manque une journée de mesures complète'};
  if(t.precision.temperature>0.5||t.precision.humidity>3)return {ic:'clock',title:'Apprentissage',text:'en cours : prévisions pas encore assez justes, conseil estimé'};
  return null;
}
const PATHS:Record<string,string>={wind:'le vent entre par l’une et sort par l’autre',opposite:'l’air traverse de part en part',two_sides:'l’air passe en angle'};
const AVOID:Record<string,string>={rain:'la pluie y entrerait',gust:'face aux rafales',sun:'le soleil y entre'};
/** Which openings, while airing is asked or going on: the banner says to air, this line says where. */
function airflowFacts(v:View):Fact[] {
  const p=v.assessment.features?.airflow,g=advice(v);
  if(!p||g.disk!=='open'||['Rien à faire','Vous pouvez refermer'].includes(g.title))return [];
  const name=(id:string)=>v.names?.[id]??id,out:Fact[]=[];
  if(p.open.length){
    const faster=p.faster&&p.faster>=1.3?` · ${number(p.faster)} fois plus rapide`:'',why=p.open.length+p.keep.length>1?PATHS[p.path]:null;
    out.push({ic:'open',topic:'windows',opens:p.open.map(name),also:p.keep.length>0,title:p.keep.length?`Ouvrez aussi ${p.open.map(name).join(' et ')}`:`Ouvrez ${p.open.map(name).join(' et ')}`,
      text:`${why??'la meilleure ouverture maintenant'}${faster}${p.learned?` (d’après ${p.learned} aérations)`:''}`});}
  // Said only when the plan had to leave it out: one line for the first one.
  const left=p.avoid[0];
  if(left)out.push({ic:'shut',topic:'windows',title:`Pas ${name(left.entity_id)}`,text:AVOID[left.why]??'à garder fermée'});
  return out;
}
/** « À savoir »: what is worth knowing about the room, under the advice. Never a gesture, one idea per line. */
export interface Fact {ic:string;title:string;text:TemplateResult|string;topic?:string;rank?:number;
  /** Lines of one kind said by rooms sharing one air: only the strongest is kept (weight), named after its room. */ key?:string;weight?:number;room?:string;
  /** The windows to open for the gesture: rooms sharing one air say them in one line. */ opens?:string[];also?:boolean}
/** What counts most comes first: where to open for the gesture, a risk, what is out of range, then why nothing
 * better is done, the equipment at work, and last what was learned. */
const RANK:Record<string,number>={'Fenêtres':0,'Autres fenêtres':0,'Cette nuit':0,'Humidité élevée':1,'Fenêtre ouverte':1,
  'Air humide':2,'Légèrement humide':2,'Très humide':2,'Air sec':2,'Légèrement sec':2,'Très sec':2,'Un peu frais':2,'Pièce fraîche':2,'Pièce chaude':2,
  'Purificateur':4,'VMC':4,'Dernière aération':5};
export const rank=(f:Fact)=>f.rank??RANK[f.title]??(f.topic==='windows'?0:f.topic==='learning'?5:3);
/** Gestures that carry the humidity themselves: the banner already says it is out of range. */
const DRY_GESTURES=['drying_possible','drying_later','ventilation_possible','short_air_change'];
export function facts(v:View):Fact[] {
  const a=v.assessment,o=v.observations,f=a.features,ti=numeric(o.indoor_temperature),out:Fact[]=[];
  // A room that cannot be read has no advice to explain: the banner sends to « Mesures ».
  if(unreadable(v))return out;
  const hum=f?.humidity,w=f?.warmth,air=f?.air,vol=f?.volume;
  // Where to open comes first: it is the precise side of the gesture.
  out.push(...airflowFacts(v));
  // The humidity out of range, named as the measure tile names it, when no gesture is about it: the pill says
  // « Au mieux », this line says what. Rooms sharing one air keep the most humid one's.
  const humLabel=humidityLabel(v),humOut=hum?.status==='high'&&!!hum.degree&&!!humLabel&&!DRY_GESTURES.includes(a.reason);
  if(humOut)out.push({ic:hum.lasting?'clock':'drop',title:humLabel!,key:'humidity',weight:hum.degree,
    text:hum.trend==='improving'?'revient vers votre plage':hum.lasting?'au-dessus de votre plage depuis plusieurs heures':'au-dessus de votre plage'});
  if(hum?.status==='low')out.push({ic:'drop',title:humLabel&&hum.degree?humLabel:'Air sec',key:'humidity',weight:hum.degree??0,text:hum.reachable!=null&&hum.measured!=null
    ?hum.reachable<hum.measured?'aérer assécherait davantage la pièce':hum.reachable>hum.measured?'l’air extérieur pourrait augmenter l’humidité ; le conseil tient aussi compte de la température':'aérer ne changerait pas l’humidité'
    :'effet de l’aération inconnu sans mesure extérieure'});
  // Under a drying gesture the line keeps the degree too: « Très humide » at 78 %, as the measure tile says.
  const humTitle=hum?.status==='high'&&humLabel?humLabel:'Humidité';
  if(!humOut&&hum?.trend==='improving'&&hum.degree)out.push({ic:'drop',title:humTitle,text:'revient vers votre plage'});
  else if(!humOut&&hum?.lasting&&hum.degree)out.push({ic:'clock',title:humTitle,text:hum.status==='low'?'sous votre plage depuis plusieurs heures':'au-dessus de votre plage depuis plusieurs heures'});
  if(a.reason==='shared_volume'&&vol)out.push({ic:'home',title:'Même air',text:`conseil commun avec : ${vol.lead}`});
  // An open window that warms the room is no window to close: the banner says it warms, this line only the humidity.
  if(a.reason==='open_neutral'&&!(f?.open_warms&&!a.needs.includes('dry')))out.push({ic:'open',title:'Fenêtre ouverte',
    text:a.needs.includes('dry')?`elle ne fait presque pas baisser l’humidité${f?.open_warms?'':', vous pouvez refermer'}`:'sans effet sur le confort, vous pouvez refermer'});
  // Opening held back: what holds it, in words.
  // Only under « Rien à faire »: a « Gardez fermé » banner already names it. An open sheltered window may stay open.
  if(a.reason==='opening_blocked'&&a.action!=='fermer'&&['calm','neutral'].includes(a.level)){const c=a.constraints[0],open=Object.entries(o).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true);
    out.push({ic:'shut',title:open?'Autres fenêtres':'Fenêtres',text:`à garder fermées : ${c==='rain_soon'?'pluie imminente':c?(constraintLabels[c]??c).toLowerCase():'contrainte extérieure'}`});}
  // « Refermez » in a damp room: why the airing is not kept for the humidity.
  const gain=f?.drying?.gain;
  if(a.reason==='exchange_harmful'&&a.needs.includes('dry'))
    out.push({ic:'drop',title:'Humidité',text:gain!=null&&gain<4?`l’aération ne la baisserait que ${gain<1.5?'d’un point à peine':`de ${Math.round(gain)} points`}`:'l’aération ne la ferait pas assez baisser'});
  if(a.reason==='heat_needed'&&a.action!=='fermer'&&a.level!=='action')
    out.push({ic:'temp',title:w?.slight?'Un peu frais':'Pièce fraîche',key:'cold',weight:w?.slight?1:2,
      // A cold the heating, an empty home or a chosen preset takes care of counts less than a problem left alone.
      rank:coldSettled(a)?3:2,text:w?.outdoor_warms?'l’air du dehors, plus chaud, la réchauffe : vous pouvez laisser ouvert'
      :w?.occupied===false?(f?.people?.away?.length?`${f.people.away.join(' et ')} ${f.people.away.length>1?'absents':'absent'} : pas besoin de chauffer`:'maison vide : pas besoin de chauffer')
      :w?.thermostat?.lowered?`thermostat en ${presetWord(w.thermostat.preset)}${w.thermostat.target!=null?` : ${deg(w.thermostat.target)} visés`:''}`
      :w?.thermostat?.off_reason&&w.thermostat.off_reason!=='manual'?`chauffage arrêté par le thermostat (${offWords[w.thermostat.off_reason]??'automatique'}), il repartira seul`
      :w?.heating==='on'?'le chauffage s’en charge':w?.warming?`${deg(ti)}, elle se réchauffe d’elle-même`
      :w?.heating==='off'?`${deg(ti)}, ${w.slight?'un peu ':''}sous votre plage · chauffage coupé`:`${deg(ti)}, sous votre plage`});
  // Tonight, simulated on the room's twin (after NADIR): the hours to open and what it leaves for tomorrow's peak.
  const plan=f?.night,warm=a.needs.includes('cool')||a.needs.includes('precool')||['cooling_possible','precool_possible','precool_later','cooling_unavailable'].includes(a.reason);
  if(plan?.worth&&warm&&plan.windows.length){const w0=plan.windows[0];
    out.push({ic:'clock',title:'Cette nuit',text:`ouvrez de ${hour(w0.start)} à ${hour(w0.end)} · ${number(plan.gain)} °C de mieux demain au plus chaud${plan.humid?' · air humide':''}`});}
  // Who the room is for, and the alarm (engine/people.py).
  const hh=f?.household,ppl=f?.people;
  if(hh?.away_open)out.push({ic:'window',title:'Fenêtre ouverte',text:ppl?.away?.length?`${ppl.away.join(' et ')} ${ppl.away.length>1?'sont absents':'est absent'}`:'personne à la maison'});
  // High pollens, for a household that said it is allergic: an empty room is no reason for a long airing then.
  if(hh?.empty_room&&!f?.pollen)out.push({ic:'open',title:'Pièce vide',text:'le bon moment pour aérer longuement'});
  if(f?.pollen)out.push({ic:'open',title:'Pollens élevés',text:f.pollen.after_rain?'aérez court, juste après la pluie':'aérez court, tôt le matin'});
  if(hh?.sleeping&&a.action==='ouvrir'&&!['air_needed','short_air_change'].includes(a.reason))out.push({ic:'clock',title:'Nuit',text:'si vous dormez, aérez plutôt au réveil'});
  // A window no contact of the room watches, seen open by the thermostat (its temperature drop).
  if(f?.thermostat?.window)out.push({ic:'window',title:'Fenêtre ouverte',text:`vue par ${f.thermostat.name}`});
  // Words for everyone: the risk and where it comes from, never a percentage against a wall.
  // The cause is not guessed: after days of rain, walls and fabrics give back water without a shower or a meal.
  if(hum?.mould)out.push({ic:'drop',title:'Humidité élevée',text:'risque de moisissure'});
  // The mould line already says it comes from the weather: one line, not two.
  // Asked to open for the air, « airing would not lower the humidity » would read as a contradiction.
  if(hum?.source==='outside'&&!hum.mould)out.push({ic:'drop',title:'Air humide dehors',text:['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level)?'l’humidité restera la même':'aérer ne ferait pas baisser l’humidité'});
  else if(a.reason==='drying_unavailable')out.push({ic:'open',title:'Aération',text:'n’aiderait pas, l’air du dehors n’est pas plus sec'});
  else if(a.reason==='drying_slow')out.push({ic:'open',title:'Aération',text:'ferait à peine baisser l’humidité'});
  else if(a.reason==='drying_alone'&&f?.drying?.alone!=null)out.push({ic:'drop',title:'Humidité',text:`redescend seule : environ ${Math.round(f.drying.alone)} % dans ${f.drying.minutes} min`});
  else if(a.reason==='drying_night')out.push({ic:'clock',title:'Aération',text:f?.drying?.morning!=null?`dès ${f.drying.morning} h, si l’humidité reste haute`:'au réveil, si l’humidité reste haute'});
  if(hum?.local)out.push({ic:'drop',title:'Vapeur',text:'plus humide ici qu’à côté : cuisson ou douche'});
  // A shower in a room that has one (« Équipements »): the peak is expected, not a risk. A confirmed habit already says it.
  if(hum?.shower&&!v.habit)out.push({ic:'drop',title:'Humidité',text:`après la douche, il y a ${hum.shower.minutes} min`});
  // A high VOC that calls for nothing says why: it falls by itself, or opening makes it climb (engine/voc.py).
  if(air?.voc_falling)out.push({ic:'flask',title:'COV',text:'en baisse, il retombe seul : pas besoin d’aérer'});
  else if(air?.voc_outdoor)out.push({ic:'flask',title:'COV',text:'élevé, mais à cette heure l’air du dehors le fait monter : aérer n’aide pas'});
  if(air?.purifier?.on===true)out.push({ic:'fan',title:'Purificateur',text:'en marche, il filtre l’air'});
  if(air?.ventilation?.on===true)out.push({ic:'vmc',title:'VMC',text:a.needs.includes('dry')?'en marche, elle aide à assécher':'en marche'});
  // The season's rules, said where they change the advice.
  const winter=f?.season?.group==='winter';
  if(winter&&a.needs.includes('cool')&&!['ouvrir','ok'].includes(a.action)&&o.heating)
    out.push({ic:'temp',title:'Pièce chaude',text:'baissez le chauffage plutôt que d’ouvrir'});
  if(winter&&a.reason==='drying_possible'&&a.action==='ouvrir')
    out.push({ic:'open',title:'Aération d’hiver',text:'courte et franche, à refaire dans la journée : les murs restent chauds'});
  // What the sun does for the room now. Asked to open, « keep the window shut » would contradict the gesture.
  const opening=['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level);
  for(const x of f?.benefits??[]){
    if(x.kind==='sun_warms')out.push({ic:'sun',title:'Soleil',text:x.keep_shut&&!opening?'il réchauffe la pièce : volets et rideaux ouverts, fenêtre fermée':'il réchauffe la pièce : volets et rideaux ouverts'});
    if(x.kind==='sun_heats')out.push({ic:'sun',title:'Soleil',text:'il chauffe la pièce : baissez le volet ou le store'});}
  // A confirmed habit names the cause of the humidity, only while it is going on.
  if(v.habit&&(a.needs.includes('dry')||hum?.mould))out.unshift({ic:'drop',title:'Humidité',text:v.habit});
  // A damp room with no gesture for it always says why the humidity stays.
  const said=out.some(x=>/umidit|Aération|Vapeur|VMC|Même air/.test(x.title+x.text));
  // « Gardez fermé … le besoin attendra » already says it.
  const waiting=a.reason==='opening_blocked'&&!['calm','neutral'].includes(a.level);
  if(a.needs.includes('dry')&&!said&&!waiting&&!['drying_possible','drying_later','ventilation_possible','short_air_change'].includes(a.reason))
    // « Would cool » only when the outside is not warmer: a warmer outside would warm the room, not cool it.
    // Asked to open for the air: the same words as the gesture, not a denial of it.
    out.push({ic:'drop',title:'Humidité',text:['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level)?'l’aération la baissera peu'
      :(a.reason==='heat_needed'||a.needs.includes('heat'))&&!(a.temperature_delta!=null&&a.temperature_delta>0.5)?'aérer refroidirait une pièce déjà fraîche'
      :a.reason==='opening_blocked'?'elle attendra que l’on puisse aérer'
      :gain!=null&&gain<4?`l’aération ne la baisserait que ${gain<1.5?'d’un point à peine':`de ${Math.round(gain)} points`}`:'l’aération ne la ferait pas assez baisser'});
  // The last airing followed: what it gave, against what was predicted.
  const last=v.feedback?.last;
  if(last){const f=(x:number)=>last.measure==='temperature'?number(x):number(Math.round(x)),u=last.measure==='temperature'?' °C':last.measure==='co2'?' ppm':last.measure==='voc'?'':' %';
    const what=last.measure==='humidity'?'humidité ':last.measure==='temperature'?'température ':last.measure==='co2'?'CO₂ ':'COV ';
    out.push({ic:'open',title:'Dernière aération',text:`${what}de ${f(last.before)} à ${f(last.after)}${u}${last.predicted!=null?` (prévu ${f(last.predicted)}${u})`:''}`});}
  const l=learning(v);if(l)out.push({...l,topic:l.topic??'learning'});
  // By priority: the sort is stable, lines of one rank keep the order they are said in.
    // Damp walls under « Rien à faire », nothing at work: a tip rather than a fatality.
  const tip=!!hum?.mould&&['calm','neutral'].includes(a.level)&&air?.ventilation?.on!==true;
  return oneHumidity(out,hum?.mould?9:hum?.degree??0,tip).sort((x,y)=>rank(x)-rank(y)).slice(0,4);
}
/** The ventilation drying the room, and how long the humidity has stood: words the humidity line keeps. */
const REMEDY='la VMC l’assèche',LASTING='depuis plusieurs heures';
/** Why airing does not help the humidity, in a few words that follow its state: « Air humide · depuis plusieurs
 * heures, aérer ne gagnerait presque rien ». */
const HUMID_WHY:[RegExp,string|((m:RegExpMatchArray)=>string)][]=[
  [/^ferait à peine baisser/,'aérer ne gagnerait presque rien'],
  [/^n’aiderait pas, (.*)$/,m=>`aérer n’aiderait pas, ${m[1]}`],
  [/^aérer ne ferait pas baisser|^l’humidité restera la même/,'l’air du dehors est humide aussi'],
  [/^l’aération ne la baisserait que d’un point/,'aérer ne gagnerait qu’un point à peine'],
  [/^l’aération ne la baisserait que de (\d+) points/,m=>`aérer ne gagnerait que ${m[1]} points`],
  [/^l’aération ne la ferait pas assez baisser/,'aérer ne suffirait pas'],
  [/^elle attendra que l’on puisse aérer/,'aérer n’est pas possible pour l’instant'],
  [/^l’aération la baissera peu/,'aérer la baissera peu'],
  [/^plus humide ici qu’à côté : (.*)$/,m=>`plus humide qu’à côté : ${m[1]}`],
  [/^(au-dessus|sous) de votre plage depuis plusieurs heures/,'depuis plusieurs heures'],
  [/^(au-dessus|sous) de votre plage$/,''],
  [/^en marche, elle aide à assécher/,REMEDY],
];
/** A reason about the humidity in its few words: the same wording whichever room of one air says it. */
const humidWhy=(t:string)=>{for(const [re,to] of HUMID_WHY){const m=t.match(re);if(m)return typeof to==='string'?to:to(m);}return t;};
/** A line about the humidity: its state, its risk, why airing does not help, or the ventilation drying it. */
const humidLine=(f:Fact)=>TOPICS[f.title]==='humidity'||(typeof f.text==='string'&&((f.title==='Aération'&&/humidit|plus sec/.test(f.text))||(f.title==='VMC'&&/assécher/.test(f.text))));
/** Damp walls with no gesture nor remedy: what the person can still do, instead of a fatality. */
const MOULD_TIP='ne séchez pas de linge ici, écartez les meubles du mur';
/** One line for the humidity: its risk or its state first, then why airing does not help, never two lines
 * about the same thing. A running ventilation is the answer and says so; damp walls with nothing to do get a tip.
 * The line is keyed so rooms sharing one air say it once, from the most humid. */
function oneHumidity(out:Fact[],weight:number,tip:boolean):Fact[] {
  const lines=out.filter(humidLine);
  if(!lines.length)return out;
  const head=lines.find(f=>f.title==='Humidité élevée')??lines.find(f=>f.key==='humidity')??lines[0];
  const short=(f:Fact)=>humidWhy(typeof f.text==='string'?f.text:'');
  // The head's own state words step aside for the reason when there is one: « Air humide » already says it is out.
  const own=head.title==='Humidité élevée'?String(head.text):short(head);
  let rest=lines.filter(f=>f!==head).map(short).filter(Boolean);
  // Said alone, the line keeps its own words.
  if(!rest.length&&!tip)return out.map(f=>f===head?{...f,key:'humidity',weight}:f);
  // The ventilation at work is the answer: why airing would not help is no longer worth saying.
  if(rest.includes(REMEDY))rest=rest.filter(t=>t===LASTING||t===REMEDY);
  const parts=[own,...rest].filter(Boolean).filter((t,i,all)=>all.indexOf(t)===i);
  const text=tip&&head.title==='Humidité élevée'&&!rest.includes(REMEDY)
    ?`${parts.filter(t=>t==='risque de moisissure'||t===LASTING).join(', ')} : ${MOULD_TIP}`
    :parts.join(', ')||String(head.text);
  return out.filter(f=>!humidLine(f)||f===head).map(f=>f===head?{...head,text,key:'humidity',weight}:f);
}
/** The « À savoir » box, under the advice; nothing when there is nothing to know. */
/** The topic of an « À savoir » line, from its title: what the card's settings keep or leave out. */
const TOPICS:Record<string,string>={'Humidité':'humidity','Air sec':'humidity','Légèrement sec':'humidity','Très sec':'humidity',
  'Air humide':'humidity','Légèrement humide':'humidity','Très humide':'humidity','Humidité élevée':'humidity','Air humide dehors':'humidity','Vapeur':'humidity',
  'Pièce fraîche':'heating','Un peu frais':'heating','Pièce chaude':'heating','Soleil':'sun','Fenêtres':'windows','Autres fenêtres':'windows','Fenêtre ouverte':'windows',
  'Aération':'windows','Aération d’hiver':'windows','Pièce vide':'household','Nuit':'household','Pollens élevés':'household','Purificateur':'equipment','VMC':'equipment',
  'Cette nuit':'forecast','Dernière aération':'learning','COV':'windows'};
/** The « À savoir » lines of a card, rooms sharing one air merged, by priority. */
export function factList(v:View,partners:View[]=[],config:Config={type:'custom:hestia-comfort-card'}):Fact[] {
  if(config.show_insights===false)return [];
  const kept=new Set<string>(config.insight_topics??INSIGHT_TOPICS);
  // One card for one air: « Même air » goes without saying, and a line said by two rooms is said once.
  // The card's room cannot be read: its banner sends to « Mesures », the other rooms' lines would explain no advice.
  if(unreadable(v))return [];
  // A line without a known topic (learning, the same air) follows « learning ».
  // A line of one kind (the humidity, the cold) is said once, by the room where it is strongest, named after it.
  const all=[v,...partners].flatMap(r=>facts(r).map(f=>({...f,room:r.title}))).filter(f=>kept.has(TOPICS[f.title]??f.topic??'learning'));
  const strongest=new Map<string,Fact>();
  for(const f of all)if(f.key&&(!strongest.has(f.key)||(f.weight??0)>(strongest.get(f.key)!.weight??0)))strongest.set(f.key,f);
  // The humidity line of the most humid room takes the reasons the other rooms gave: it is one air.
  const hum=strongest.get('humidity'),joined=new Map<Fact,Fact>();
  if(hum&&typeof hum.text==='string'){const parts=hum.text.split(', ');
    for(const f of all)if(f.key==='humidity'&&f!==hum&&typeof f.text==='string')for(const p of f.text.split(', ').map(humidWhy))
      if(p&&!parts.includes(p)&&!/^(au-dessus|sous) de votre plage|^risque de moisissure|^revient vers/.test(p))parts.push(p);
    joined.set(hum,{...hum,text:(parts.length>1?parts.filter(p=>!/^(au-dessus|sous) de votre plage$/.test(p)):parts).join(', ')});}
  // One air, one answer about its windows: a room the open window warms keeps it open, the others do not ask to close it.
  const keep=all.some(f=>typeof f.text==='string'&&f.text.includes('laisser ouvert'))||[v,...partners].some(r=>r.assessment.features?.open_warms);
  // One air, one gesture: the windows each room asks to open are said in one line, the first room's reason kept.
  const opening=all.filter(f=>f.opens?.length);
  if(opening.length>1){const names=[...new Set(opening.flatMap(f=>f.opens!))],first=opening[0];
    const one={...first,title:`${first.also?'Ouvrez aussi':'Ouvrez'} ${names.join(' et ')}`};
    for(const f of opening)joined.set(f,one);}
  const seen=new Set<string>(),list=all.filter(f=>!f.key||strongest.get(f.key)===f).map(f=>joined.get(f)??f)
    .map(f=>keep&&typeof f.text==='string'&&f.text.endsWith(', vous pouvez refermer')?{...f,text:f.text.slice(0,-', vous pouvez refermer'.length)}:f)
    .filter(f=>!(keep&&f.title==='Fenêtre ouverte'&&f.text==='sans effet sur le confort'))
    .filter(f=>!ELSEWHERE.has(f.title)&&f.title!=='Même air'&&!seen.has(f.title)&&!!seen.add(f.title))
    .sort((x,y)=>rank(x)-rank(y)).slice(0,config.insight_max??4);
  return list;
}
/** The headings of « À savoir », by rank: the gesture's side first, then what is worth watching, then what was learned. */
const FACT_GROUPS=[{id:'gesture',ic:'hand',title:'Pour le geste',ranks:[0]},{id:'watch',ic:'eye',title:'À surveiller',ranks:[1,2,3,4]}];
/** Said elsewhere (30 October, evening): the devices at work in the Air module, what was learned in the « i ». */
const ELSEWHERE=new Set(['Purificateur','VMC','Dernière aération','Apprentissage']);
export function factBox(v:View,partners:View[]=[],config:Config={type:'custom:hestia-comfort-card'},list=factList(v,partners,config)):TemplateResult|typeof nothing {
  if(v.advisor)return factBox3(v.advisor);
  // The first line is what counts most: set apart, and a risk in the « to watch » colour.
  // Three headings, each said only when it has lines: where to act for the gesture, what to keep an eye on, what was learned.
  const line=(f:Fact)=>html`<li class=${rank(f)===1?'risk':''}>${icon(f.ic)}<span><b>${tx(f.title)}</b> · ${partners.length&&f.key==='humidity'&&f.room?`${f.room}, `:''}${tl(f.text)}</span></li>`;
  // Under « Rien à faire » there is no gesture: its lines join what is worth watching, never on orange.
  const calm=advice(v).title==='Rien à faire',of=(f:Fact)=>calm&&rank(f)===0?1:rank(f);
  const groups=FACT_GROUPS.map(g=>({...g,lines:list.filter(f=>g.ranks.includes(of(f)))})).filter(g=>g.lines.length);
  return list.length?html`<div class="nc-facts"><div class="nw-label">${t('À savoir')}</div><div class="nc-facts-box nw-glass">${groups.map(g=>html`<section class="nc-facts-g" data-group=${g.id}>
    <h4>${icon(g.ic)}${tx(g.title)}</h4><ul>${g.lines.map(line)}</ul></section>`)}</div></div>`:nothing;
}
/** Why the room that leads a shared air asks for its gesture, after its name. */
const SHARED:Record<string,string>={air_needed:'a besoin d’air',short_air_change:'a besoin d’air',cooling_possible:'se rafraîchit',warming_possible:'se réchauffe',
  drying_possible:'s’assèche',precool_possible:'stocke le frais',rain_soon:'attend la pluie',rain_open_windows:'prend la pluie',
  gust_open_windows:'prend le vent',alarm_open:'est ouverte, alarme armée',opening_blocked:'doit rester fermé',exchange_harmful:'se dérègle',rehumidification_risk:'reprend l’humidité',voc_outdoor:'prend le COV du dehors',
  heat_needed:'est trop fraîche',sun_entering:'prend le soleil'};
/** When the rain starts: to the minute from the radar, only « within the hour » from the hourly forecast. */
function rainWhen(a:View['assessment']):string {
  const m=a.rain_soon_minutes,precise=a.features?.rain_ahead?.precise;
  if(m==null||!precise)return 'annoncée dans l’heure';
  return m<=2?'imminente':`dans ${m} min`;
}
/** Outdoor sources the advice could not check: never configured (« non suivi ») or configured but silent (« indisponible »). */
const OUTSIDE:Record<string,[string,boolean]>={rain:['pluie',true],pollution:['air extérieur',false],outdoor_temperature:['température dehors',true],outdoor_humidity:['humidité dehors',true],wind_gust:['rafales',true]};
export function outsideGaps(v:View):string {
  const a=v.assessment,pick=(keys:string[])=>keys.filter(k=>k in OUTSIDE).map(k=>OUTSIDE[k]);
  const absent=pick(a.unverified??[]),silent=pick(a.missing.filter(k=>!!v.observations[k]));
  // French agreement: feminine only when every name is feminine; « rafales » is already plural.
  const part=(names:[string,boolean][],word:(fem:boolean,plural:boolean)=>string)=>names.length?`${names.map(n=>n[0]).join(' et ')} ${word(names.every(n=>n[1]),names.length>1||names.some(n=>n[0].endsWith('s')))}`:'';
  const text=[part(silent,(_f,pl)=>'indisponible'+(pl?'s':'')),part(absent,(f,pl)=>'non suivi'+(f?'e':'')+(pl?'s':''))].filter(Boolean).join(', ');
  return text?text[0].toUpperCase()+text.slice(1):'Extérieur à vérifier';
}
/** « COV au-dessus de l'habituel depuis 12 min »: an index without unit is relative to the home's own mean. */
export function vocText(air:{voc_unit?:string|null;voc_minutes?:number|null}|undefined):string {
  const base=air?.voc_unit?'COV au-dessus du seuil':'COV au-dessus de l’habituel',m=air?.voc_minutes;
  return typeof m==='number'&&m>0?`${base} depuis ${m} min`:base;
}
function airWhy(v:View):TemplateResult {
  const o=v.observations,air=v.assessment.features?.air,parts:string[]=[];
  if(air?.co2_status==='high')parts.push(`CO₂ ${number(numeric(o.co2))} ppm`);
  if(air?.pm25_status==='high')parts.push('particules élevées');
  if(air?.voc_status==='high')parts.push(vocText(air));
  return html`${b(parts.join(', ')||'Air à renouveler')}`;
}

export interface Slide extends Advice {level:Level;pill:string}
/** Every advice of the moment, the main one first: what to do, then the remedies already at work and what Hestia cannot check. */
export function slides(v:View,blocks:readonly BannerBlock[]=['remedies','later']):Slide[] {
  if(v.advisor)return slides3(v.advisor);
  const a=v.assessment,main=advice(v),out:Slide[]=[{...main,level:main.level??a.level,pill:main.pill??pills[a.level]}];
  // Remedies at work (purifier, ventilation) are information: they are in « À savoir », not in the banner.
  // What Hestia cannot check is information, not advice: it stays in « Détails ».
  const later=a.features?.drying?.later;
  if(blocks.includes('later')&&later&&a.reason==='drying_possible')out.push({level:'benefit',pill:'Plus tard',title:`Encore mieux vers ${hour(later.time)}`,line:html`L’air sera plus sec : ${b('environ '+Math.round(later.after)+' %')}`,disk:'clock'});
  if(blocks.includes('later')&&a.slot&&a.slot.kind==='open'&&!['cooling_unavailable','precool_later'].includes(a.reason))out.push({level:'benefit',pill:'Plus tard',title:`Ouvrez vers ${hour(a.slot.time)}`,line:html`Il fera ${b(number(a.slot.temperature)+' °C')} dehors`,disk:'moon'});
  return out;
}

export interface ScaleInput {band?:[number,number]|null;day?:{min:number;max:number}|null;now?:number|null;out?:number|null;
  rooms?:{name:string;short:string;value:number;level:Level;entity?:string}[];unit?:string;nowEntity?:string;outEntity?:string}
/** The scale is built by the charter (hestia-echelle, the same as Hestia Weather's « Ressenti »): « trop frais », « votre plage »,
 *  « trop chaud » around the range, the last 24 hours, outside, the rooms. Only the room's data here. */
export function scale(s:ScaleInput):TemplateResult {
  const finite=(x:unknown):x is number=>typeof x==='number'&&Number.isFinite(x);
  const core=[s.band?.[0],s.band?.[1],s.day?.min,s.day?.max,s.now,...(s.rooms??[]).map(r=>r.value)].filter(finite);
  const values=core.length?core:[s.out].filter(finite);
  if(!values.length)return html``;
  let lo=Math.floor(Math.min(...values)-1.5),hi=Math.ceil(Math.max(...values)+1.5);
  if(hi-lo<8){const pad=(8-(hi-lo))/2;lo=Math.floor(lo-pad);hi=Math.ceil(hi+pad);}
  const fmt=(x:number)=>number(Math.round(x*10)/10),unit=s.unit??'°C';
  // Temperature: too cool and too warm around the range; another measure: only the range, the rest grey.
  const zones=unit==='°C',grey='color-mix(in srgb,var(--nw-fg) 22%,var(--nw-bg))',pos=(v:number)=>echellePos({lo,hi},v);
  const parts=s.band?[{from:lo,to:s.band[0],word:zones?t('trop frais'):'',tone:zones?'var(--nw-cold)':grey},{from:s.band[0],to:s.band[1],word:t('votre plage'),tone:'var(--nw-calm)'},
    {from:s.band[1],to:hi,word:zones?t('trop chaud'):'',tone:zones?'var(--nw-level2)':grey}].filter(p=>pos(p.to)-pos(p.from)>.5):[{from:lo,to:hi,tone:grey}];
  // Rooms a few tenths apart share one label (« S·C »): every room stays named.
  const sorted=[...(s.rooms??[])].sort((p,q)=>p.value-q.value),groups:typeof sorted[]=[];
  for(const r of sorted){const g=groups[groups.length-1];if(g&&pos(r.value)-pos(g[g.length-1].value)<4.5)g.push(r);else groups.push([r]);}
  const marks=groups.map(g=>{const w=g.map(r=>r.short).join('·');return {value:g.reduce((sum,r)=>sum+r.value,0)/g.length,text:html`<b>${w}</b>`,row:'up' as const,strong:true,chars:w.length};});
  const dots=(s.rooms??[]).map(r=>r.entity?html`<button type="button" class="nc-mk room nc-hit" data-level=${r.level} style=${`left:${pos(r.value).toFixed(2)}%`} title=${r.name+' '+fmt(r.value)+' '+unit} aria-label=${t('Détails : {label}',{label:r.name})} @click=${(e:Event)=>moreInfo(e,r.entity!)}></button>`
    :html`<span class="nc-mk room" data-level=${r.level} style=${`left:${pos(r.value).toFixed(2)}%`} title=${r.name+' '+fmt(r.value)+' '+unit}></span>`);
  const said=[s.now!=null?t('Maintenant {value}',{value:`${fmt(s.now)} ${unit}`}):'',s.band?t('plage {low} à {high}',{low:fmt(s.band[0]),high:`${fmt(s.band[1])} ${unit}`}):'',s.out!=null?t('dehors {value}',{value:`${fmt(s.out)} ${unit}`}):''].filter(Boolean).join(', ');
  return html`${echelle({lo,hi,parts,label:said,degree:v=>fmt(v)+'°',marks,dots,span:s.day?[s.day.min,s.day.max]:undefined,
    value:s.now??undefined,valueText:s.now!=null?`${fmt(s.now)} ${unit}`:undefined,valueTitle:t('Détails de la température'),onValue:s.nowEntity?(e:Event)=>moreInfo(e,s.nowEntity!):undefined,
    outside:s.out!=null?{value:s.out,label:`${t('dehors')} ${fmt(s.out)}°`,title:t('Détails de la température dehors'),onTap:s.outEntity?(e:Event)=>moreInfo(e,s.outEntity!):undefined}:undefined})}
  ${s.day||s.rooms||s.out!=null?html`<div class="nw-legend nc-legend">${s.day?html`<span><i class="k-day"></i>${t('min–max 24 h')}</span>`:nothing}${s.rooms?html`<span><i class="k-room"></i>${t('pièces')}</span>`:nothing}${s.out!=null?html`<span><i class="k-out"></i>${t('dehors')}</span>`:nothing}</div>`:nothing}`;
}

/** `watch` (soft yellow): the measure leaves your range, without a gesture asked; orange stays for gestures. */
/** The range the room keeps now: the season's when known, as the scale draws it, else its own settings. */
const seasonRange=(v:View):[number,number]|null=>{const s=v.assessment.features?.season;
  return s?.minimum!=null&&s?.maximum!=null?[s.minimum,s.maximum]:v.comfort_minimum!=null&&v.comfort_maximum!=null?[v.comfort_minimum,v.comfort_maximum]:null;};
/** A partner room's temperature, as a tile: the scale above shows only the chosen room. */
function roomTemperature(p:View):Tile[] {
  const t=numeric(p.observations.indoor_temperature),n=p.assessment.needs,out=n.includes('cool')||n.includes('heat');
  return t===null?[]:[{ic:'temp',label:'Température',value:number(t),unit:'°C',note:n.includes('cool')?'trop chaud':n.includes('heat')?(p.assessment.features?.warmth?.slight?'un peu frais':'trop frais'):'dans votre plage',level:out?'watch':'calm',out,entity:p.observations.indoor_temperature?.source??undefined,
    trend:trendOf(p,'temperature',n.includes('cool')?'high':n.includes('heat')?'low':null,seasonRange(p))}];
}
export interface Tile {
  /** A curve without an arrow beside the value (the heating's power); the heating's plain mode as a flame. */ curve?:Trend;flame?:boolean;ic:string;label:string;value:string;unit?:string;note:string;level:Level|'watch';out:boolean;entity?:string;
  /** A device at work (purifier, ventilation): framed like a measure, never counted out of your range. */
  remedy?:boolean;
  /** The last half hour: which way it goes, whether that is good for the room, and your range to draw behind. */
  trend?:Trend}
/** `better` heads back to your range, `worse` leaves it further; anything else is said in grey, never in green. */
export interface Trend {way:'up'|'down'|'stable';tone:'better'|'worse'|'steady';points:[number,number][];band?:[number,number]|null;key:string}
/** The curve of a measure, toned by where it stands: `out` is the side of your range it is on, if any. */
export function trendOf(v:View,key:'temperature'|'humidity'|'co2'|'voc'|'pm25'|'solar'|'heating',out:'high'|'low'|null,band:[number,number]|null=null):Trend|undefined {
  const c=v.assessment.features?.trends?.curves?.[key];
  if(!c||c.points.length<2)return undefined;
  const tone=c.way==='stable'||!out?'steady':(out==='high')===(c.way==='down')?'better':'worse';
  return {way:c.way,tone,points:c.points,band,key};
}
/** Below these spans the curve is not stretched: a few tenths would otherwise look like a climb. */
const SPAN:Record<string,number>={temperature:.8,humidity:5,co2:150,voc:60,pm25:6,solar:120,heating:30};
/** A smooth line through the points that never overshoots them (monotone cubic), in a 100 × 24 box. */
function curvePath(pts:[number,number][]):string {
  const n=pts.length,d=pts.slice(1).map((p,i)=>(p[1]-pts[i][1])/((p[0]-pts[i][0])||1));
  const m=pts.map((_,i)=>i===0?d[0]:i===n-1?d[n-2]:d[i-1]*d[i]<=0?0:(d[i-1]+d[i])/2);
  let path=`M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for(let i=0;i<n-1;i++){const h=(pts[i+1][0]-pts[i][0])/3;
    path+=` C${(pts[i][0]+h).toFixed(1)} ${(pts[i][1]+m[i]*h).toFixed(1)} ${(pts[i+1][0]-h).toFixed(1)} ${(pts[i+1][1]-m[i+1]*h).toFixed(1)} ${pts[i+1][0].toFixed(1)} ${pts[i+1][1].toFixed(1)}`;}
  return path;
}
const WAYS={up:'en hausse',down:'en baisse',stable:'stable'} as const;
/** The arrow beside the value: it moves the way the measure goes. */
/** The charter's arrow (.nw-trend): only when the measure really moves; « stable » keeps its place and shows nothing (3 November). */
const trendArrow=(r:Trend)=>html`<span class="nw-trend nc-way" data-way=${r.way} data-tone=${r.tone} title=${r.way==='stable'?nothing:tx(WAYS[r.way])} aria-label=${r.way==='stable'?nothing:tx(WAYS[r.way])} aria-hidden=${r.way==='stable'?'true':nothing}></span>`;
/** The last half hour, drawn smooth with a soft fill under it, over your range as a pale band when it is in view
 *  (the « Trait » rules for every curve: rounded line, soft fill, the dot of now, the range behind). */
let sparkIds=0;
function sparkline(r:Trend):TemplateResult {
  // Your range's nearest edge stays in view; too far, it is left out.
  const vals=r.points.map(p=>p[1]),span=SPAN[r.key]??0;let a=Math.min(...vals),b=Math.max(...vals);
  const band=r.band&&Math.max(r.band[0]-b,a-r.band[1])<=span*3?r.band:null;
  if(band){a=Math.min(a,band[1]);b=Math.max(b,band[0]);}
  const mid=(a+b)/2,half=Math.max(b-a,span)/2*1.35;
  // Shorter than half an hour (just after a start), the curve covers the width all the same.
  const span0=Math.max(...r.points.map(p=>p[0]),1),win=Math.min(30,span0);
  const lo=mid-half,hi=mid+half,y=(x:number)=>22-(x-lo)/(hi-lo)*20,pts=r.points.map(([ago,x]):[number,number]=>[Math.max(0,Math.min(100,(win-ago)/win*100)),y(x)]);
  const last=pts[pts.length-1];
  const line=curvePath(pts),id='nc-sp'+(++sparkIds);
  return html`<div class="nc-spark" data-tone=${r.tone} data-key=${r.key} aria-hidden="true"><svg viewBox="0 0 100 24" preserveAspectRatio="none">
    <defs><linearGradient id=${id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="nc-spark-fill0"></stop><stop offset="1" class="nc-spark-fill1"></stop></linearGradient></defs>
    ${band?svg`<rect class="nc-spark-band" x="0" width="100" y=${Math.max(0,y(band[1])).toFixed(1)} height=${Math.max(0,Math.min(24,y(band[0]))-Math.max(0,y(band[1]))).toFixed(1)} rx="2"></rect>`:nothing}
    <path class="nc-spark-area" d=${`${line} L${last[0].toFixed(1)} 24 L${pts[0][0].toFixed(1)} 24 Z`} fill=${`url(#${id})`}></path>
    <path class="nc-spark-line" d=${line}></path></svg>
    <span class="nc-spark-dot" style=${`left:${last[0]}%;top:${last[1]/24*100}%`}></span></div>${SPARK_CAPTION[r.key]?html`<span class="nc-spark-cap">${t(SPARK_CAPTION[r.key])}</span>`:nothing}`;
}
/** A curve that is not the value shown above it says what it is. */
const SPARK_CAPTION:Record<string,string>={heating:'Puissance de chauffe, dernière demi-heure',solar:'Soleil dehors, dernière demi-heure'};
/** Opens Home Assistant's own details window (history, attributes) for an entity, as any dashboard card does. */
export const moreInfo=(e:Event,entityId:string)=>{e.stopPropagation();(e.currentTarget as HTMLElement).dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId},bubbles:true,composed:true}));};
/** The entity behind each tile: the one a tap opens. */
function tileEntity(v:View,label:string):string|undefined {
  const o=v.observations,src=(k:string)=>o[k]?.source??undefined;
  if(label==='Fenêtres'){const contacts=Object.entries(o).filter(([k])=>k.startsWith('window:'));const open=contacts.find(([,r])=>r.value===true);return (open??contacts[0])?.[1].source??undefined;}
  return ({'Humidité':src('indoor_humidity'),'CO₂':src('co2'),'Particules':src('pm25'),'COV':src('voc'),'Soleil':src('solar'),'Purificateur':src('purifier'),
    'Ventilation':o.ventilation_boost?.value===true?src('ventilation_boost'):src('ventilation')??src('ventilation_boost'),'Chauffage':src('heating')} as Record<string,string|undefined>)[label];
}
/** One compact frame per measure; it takes the level's outline when the measure leaves your range. */
/** Thermostat modes in plain French (presets first, then the plain heating mode). */
const modeLabels:Record<string,string>={frost:'hors gel',eco:'éco',comfort:'confort',boost:'boost',away:'absence',sleep:'nuit',home:'présence',activity:'activité',off:'éteint',heat:'chauffage',auto:'programmé',heat_cool:'automatique'};
/** Why a measure has no value: silent for too long is not the same as gone. */
const gone=(r?:{quality:string})=>r?.quality==='stale'?'pas de nouvelle mesure':'indisponible';
/** « 13 h 50 », in the person's own clock. */
const clock=(x?:string|null)=>{const d=x?new Date(x):null;return d&&!isNaN(+d)?d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}).replace(':',' h '):null;};
/** The source behind a tile, to know whether it is read from the room sharing this air. */
const tileKeys:Record<string,string>={'CO₂':'co2',Particules:'pm25',COV:'voc',Purificateur:'purifier',Ventilation:'ventilation',Chauffage:'heating'};
/** A room's tiles without those it reads from another room: on a card shared by both, each measure shows once. */
const ownTiles=(v:View,list:Tile[])=>list.filter(t=>!v.inherited?.[tileKeys[t.label]??'']);
export function tiles(v:View,config:Config):Tile[] {
  const o=v.observations,a=v.assessment,mods=new Set(config.modules??[]),list:Tile[]=[],air=a.features?.air;
  if(mods.has('humidity')&&o.indoor_humidity){const h=numeric(o.indoor_humidity),hum=a.features?.humidity,wet=a.needs.includes('dry'),outside=hum?.source==='outside',out=h!==null&&(hum?.degree!==undefined?hum.degree>=2:wet);
    list.push({ic:'drop',label:'Humidité',value:h===null?'—':number(Math.round(h)),unit:'%',note:h===null?gone(o.indoor_humidity):(humidityLabel(v)?.toLowerCase()??(outside?'humide dehors aussi':'normale')),level:out?'watch':'calm',out,
      trend:h===null?undefined:trendOf(v,'humidity',hum?.status==='high'||hum?.status==='low'?hum.status:null,hum?.minimum!=null&&hum?.maximum!=null?[hum.minimum,hum.maximum]:null)});}
  if(mods.has('air')&&o.co2){const c=numeric(o.co2),high=air?.co2_status==='high';
    list.push({ic:'air',label:'CO₂',value:number(c),unit:'ppm',note:c===null?gone(o.co2):high?'à renouveler':'normal',level:high?(a.level==='urgent'?'urgent':'watch'):'calm',out:high,trend:c===null?undefined:trendOf(v,'co2',high?'high':null)});}
  if(mods.has('air'))for(const [key,ic,label,status] of [['pm25','pm','Particules',air?.pm25_status],['voc','flask','COV',air?.voc_status]] as const){
    if(!o[key])continue;const x=numeric(o[key]),high=status==='high',treated=key==='pm25'&&high&&air?.pm25_treated===true;
    list.push({ic,label,value:number(x),unit:o[key].unit??'',note:x===null?gone(o[key]):treated?'filtrées':key==='voc'&&air?.voc_falling?'en baisse':key==='voc'&&(air?.voc_outdoor||air?.voc_rising_open)?'élevés':high?(key==='voc'&&typeof air?.voc_minutes==='number'&&air.voc_minutes>0?`depuis ${air.voc_minutes} min`:'élevés'):status==='uninterpreted'?'sans seuil':key==='pm25'?'normales':'normaux',level:treated?'calm':high?'watch':status==='ok'?'calm':'neutral',out:high,trend:x===null?undefined:trendOf(v,key,high?'high':null)});}
  if(mods.has('windows')){const contacts=Object.entries(o).filter(([k])=>k.startsWith('window:')).map(([,r])=>r);
    if(contacts.length){const open=contacts.filter(r=>r.quality==='valid'&&r.value===true).length,flagged=(a.openings??[]).some(x=>x.flags.length>0&&x.open===true);
      list.push({ic:open?'open':'window',label:'Fenêtres',value:`${open}/${contacts.length}`,note:flagged?'à refermer':open?(open===1&&a.features?.ventilation?.opened_minutes!=null?`ouverte depuis ${Math.round(a.features.ventilation.opened_minutes)} min`:open>1?`${open} ouvertes`:'1 ouverte'):'toutes fermées',level:flagged?'action':'neutral',out:flagged});}}
  if(mods.has('shutters')){const s=a.sun,solar=numeric(o.solar),entering=(a.openings??[]).some(x=>x.flags.includes('sun_entering'));
    if(s||solar!==null){const night=!!s&&s.elevation<=0,value=night?'Nuit':solar===null?'non mesuré':solar<150?'Faible':solar<500?'Moyen':'Fort';
      list.push({ic:night?'moon':'sun',label:'Soleil',value,note:entering?'entre dans la pièce':night?'pas d’apport':solar===null?'non mesuré':`${number(Math.round(solar))} W/m²${o.solar?.detail==='shaded_estimate'?' · estimé, station à l’ombre':''}`,level:entering?'action':'neutral',out:entering,trend:solar===null||night?undefined:trendOf(v,'solar',null)});}}
  // A connected cover: where it stands, and who moves it (Adaptive Cover Pro, the person, or nobody yet).
  if(mods.has('shutters'))for(const s of a.features?.shutters??[]){if(s.mode!=='connected')continue;
    const p=s.position,shut=p===0||(p==null&&s.state==='closed'),open=p===100||(p==null&&s.state==='open'),act=s.manual_override!==true&&!!s.advice;
    const auto=!!s.driver&&(s.driving??s.automatic===true)&&s.manual_override!==true;
    const until=clock(s.override_end),soon=s.soon?clock(s.sun_start):null;
    const note=s.manual_override===true?(until?`à la main jusqu’à ${until}`:'repris à la main'):act?(s.advice==='close'?(soon?`à fermer avant ${soon}`:'à fermer'):'à ouvrir'):auto?(s.sun_front?'automatique · soleil devant':'automatique'):s.driver&&(s.off||s.automatic===false)?({disabled:'ACP désactivé',tracking:'suivi du soleil coupé'} as Record<string,string>)[s.off??'']??'automatisme coupé':s.state==null&&p==null?'indisponible':'rien à faire';
    list.push({ic:shut?'shut':'window',label:'Volet',value:shut?'Fermé':open?'Ouvert':p!=null?number(p):'—',unit:!shut&&!open&&p!=null?'%':undefined,note,level:act?'action':auto?'calm':'neutral',out:act,entity:s.cover??undefined});}
  if(mods.has('air')&&o.purifier){const on=o.purifier.quality==='valid'?o.purifier.value===true:null,speed=numeric(o.purifier_speed);
    // Running, it is a remedy at work: framed in green, like the measure it treats.
    list.push({ic:'fan',label:'Purificateur',value:on===null?'—':on?'En marche':'Arrêté',note:on?(speed!==null?`filtre à ${number(speed)} %`:'filtre l’air'):on===false?'à l’arrêt':'indisponible',level:on?'calm':'neutral',out:on===true,remedy:true});}
  const vent=air?.ventilation;
  if(mods.has('air')&&vent){const on=vent.on,fast=vent.boost===true;
    list.push({ic:'vmc',label:'Ventilation',value:on===null?'—':fast?'Rapide':on?'En marche':'Arrêtée',note:on?(fast?'grande vitesse':'renouvelle l’air'):on===false?'à l’arrêt':'indisponible',level:on?'calm':'neutral',out:on===true,remedy:true});}
  if(mods.has('coordination')&&o.heating){const label=heatingLabels[a.heating_action]??'Inconnu',running=a.heating_action==='heating';
    const raw=o.heating_mode?.quality==='valid'&&typeof o.heating_mode.value==='string'?o.heating_mode.value:null,mode=raw?modeLabels[raw]??raw:null;
    const power=o.heating_power?.quality==='valid'&&typeof o.heating_power.value==='number'?o.heating_power.value:null,percent=power!==null&&power>0&&power<100;
    list.push({ic:'heat',label:'Chauffage',value:running?'Chauffe':label,unit:running&&percent?`${number(Math.round(power!))} %`:undefined,note:raw==='heat'?'':mode?`mode ${mode}`:running?'chauffe la pièce':'observé, jamais commandé',level:'neutral',out:false,
      curve:power===null||!(a.features?.trends?.curves?.heating?.points??[]).some(p=>p[1]>0)?undefined:trendOf(v,'heating',null),flame:raw==='heat'});}
  for(const t of list)t.entity??=tileEntity(v,t.label);
  // A measure read from the room sharing this air says where it is measured.
  for(const t of list){const from=v.inherited?.[tileKeys[t.label]??''];if(from)t.note=`${t.note} · ${from}`;}
  // Right after a start, a silent sensor is still on its way, not broken.
  return v.starting?list.map(t=>t.note==='indisponible'||t.note==='pas de nouvelle mesure'?{...t,note:'en attente'}:t):list;
}
// Only a sensor that stopped answering is drawn muted, not a measure that was never configured (« non mesuré »).
// Out of range with a gesture to make: the orange frame; without one, a discreet mark (« soft »).
const tileClass=(t:Tile,soft=false)=>'nc-tile'+(t.out?(soft?' out soft':' out'):'')+(['indisponible','pas de nouvelle mesure','en attente'].includes(t.note)?' mute':'');
export const tile=(t:Tile,soft=false)=>t.entity?html`<button type="button" class=${tileClass(t,soft)} data-level=${t.level} title=${tr('Détails : {label}',{label:tx(t.label)})} @click=${(e:Event)=>moreInfo(e,t.entity!)}>${tileBody(t)}</button>`:html`<div class=${tileClass(t,soft)} data-level=${t.level}>${tileBody(t)}</div>`;
const tileBody=(t:Tile)=>html`<div class="nc-tile-h"><span class="nc-ic">${icon(t.ic)}</span><span class="nw-label">${tx(t.label)}</span></div><b><span>${tx(t.value)}${t.unit&&t.value!=='—'?html`<small>${t.unit}</small>`:nothing}</span>${t.trend?trendArrow(t.trend):nothing}</b>${t.trend?sparkline(t.trend):nothing}<em>${tx(t.note)}</em>`;

const row=(label:string,x:string)=>html`<li><b>${tx(label)}</b><span> · ${tx(x)}</span></li>`;
/** One short line per fact: the long explanations of 0.9 become « title · fact ». */
export function details(v:View,config:Config):TemplateResult[] {
  // Each line has its key: the « Détails techniques » section shows those the card keeps (config.detail_rows).
  const rows=new Set<string>(config.detail_rows??DETAIL_ROWS),add=(key:string,t:string,x:string)=>{if(rows.has(key))out.push(row(t,x));};
  const a=v.assessment,f=a.features,mods=new Set(config.modules??[]),out:TemplateResult[]=[];
  const season=f?.season;
  if(season)add('range','Votre plage de confort',`${number(season.minimum)} à ${number(season.maximum)} °C${!season.heated?' · pièce non chauffée':''}${season.name?' · '+(SEASON_NAMES[season.name]??season.name):season.known?(season.weight===0?' · hiver':season.weight===1?' · été':' · entre-saisons'):' · saison non calculée'}`);
  if(a.action==='ouvrir'&&a.open_first?.length)add('windows','Ouvrez d’abord',a.open_first.map(id=>v.names?.[id]??id).join(' et '));
  // Only a complete slot is said: an hour and a temperature, never « NaN h ».
  const slotOk=!!a.slot&&typeof a.slot.temperature==='number'&&!Number.isNaN(new Date(a.slot.time).getTime());
  if(slotOk)add('slot',a.slot!.kind==='open'?'Ouverture possible':'Fermeture conseillée',`${hour(a.slot!.time)} · ${number(a.slot!.temperature)} °C${a.slot!.wind_bearing!=null?' · '+windFrom(a.slot!.wind_bearing):''}`);
  const silent=a.missing.filter(k=>!!v.observations[k]);
  if(silent.length)add('sensors','Ne répond pas',silent.map(k=>sourceLabel(v,k)).join(', '));
  if(a.unverified?.length&&a.action!=='fermer')add('sensors','Sans capteur',a.unverified.map(k=>k==='rain'?'pluie':'qualité de l’air dehors').join(', '));
  const vent=f?.ventilation;
  if(mods.has('windows')&&vent){if(vent.opened_minutes!=null)add('windows','Ouvert depuis',`${number(vent.opened_minutes)} min`);}
  if(mods.has('shutters'))for(const s of f?.shutters??[]){if(s.mode==='none'||(!s.advice&&!s.manual_override&&s.position==null))continue;
    const from=clock(s.sun_start),to=clock(s.sun_end);
    // In plain words: who sets it, where it stands, when the sun comes. Adaptive Cover Pro's own wording is left out.
    add('shutters',v.names?.[s.entity_id]??'Volet',[s.manual_override?'réglé à la main':s.advice==='close'?'à fermer':s.advice==='open'?'à ouvrir':s.driver&&(s.driving??s.automatic===true)?'piloté par Adaptive Cover Pro':'rien à faire',s.driver&&s.detection===false?'reprise à la main non détectée':'',s.driver&&s.climate===false?'mode climat coupé':'',
      s.position!=null?`ouvert à ${number(s.position)} %`:'',s.driver&&s.target!=null&&s.target!==s.position?`visé ${number(s.target)} %`:'',from&&to?`soleil de ${from} à ${to}`:''].filter(Boolean).join(' · '));}
  if(f?.people&&(f.people.home.length||f.people.away.length))add('people','Personnes',[f.people.home.length?`${f.people.home.join(', ')} à la maison`:'',f.people.away.length?`${f.people.away.join(', ')} ${f.people.away.length>1?'absents':'absent'}`:''].filter(Boolean).join(' · '));
  if(f?.household?.alarm)add('people','Alarme',`${f.household.alarm.name} · ${({disarmed:'désarmée',armed_away:'absence',armed_home:'à la maison',armed_night:'nuit',armed_vacation:'vacances'} as Record<string,string>)[f.household.alarm.state]??f.household.alarm.state}`);
  if(mods.has('air')&&f?.presence&&f.presence.state!=='not_configured')add('people','Présence',{occupied:'quelqu’un est là',empty:'pièce vide',leaving:`personne depuis ${f.presence.minutes??0} min (vide après ${f.presence.delay??5} min)`,unknown:'inconnue'}[f.presence.state]??'');
  // Where the drying promise comes from: this room's own airings, or an ordinary room until one is seen.
  if(mods.has('humidity')&&f?.drying)add('drying','Séchage',f.drying.openings?`appris sur ${f.drying.openings} aération${f.drying.openings>1?'s':''}`:'estimé, aucune aération observée');
  if(mods.has('humidity')&&f?.humidity&&f.humidity.condensation_risk!==null)add('drying','Buée',f.humidity.condensation_risk?'risque estimé':'aucun risque estimé');
  const tr=f?.trends;
  if(mods.has('temperature')&&tr&&(tr.indoor!=null||tr.outdoor!=null))add('trend','Tendance',[tr.indoor!=null?`dedans ${tr.indoor>0?'+':''}${number(tr.indoor)} °C/h`:'',tr.outdoor!=null?`dehors ${tr.outdoor>0?'+':''}${number(tr.outdoor)} °C/h`:''].filter(Boolean).join(', '));
  if(!silent.length)add('sensors','Sources',coverageText(v));
  return out;
}

export interface CardState {why:boolean;tilesOpen:boolean;detailsOpen:boolean;horizonAlt?:boolean;
  /** The tile unfolded by a tap; « Prochaines heures » folded or not on the full card. */ unfolded?:boolean;horizonOpen?:boolean;
  toggle:(k:'why'|'tilesOpen'|'detailsOpen'|'horizonAlt'|'unfolded'|'horizonOpen')=>void;uid:string;configure?:()=>void}
/** The « i » panel: needs, constraints and how complete the picture is, one line each. */
export function whyLines(v:View):TemplateResult {
  const a=v.assessment;
  return html`<p><b>${t('Besoins')}</b> · ${a.needs.length?a.needs.map(n=>tx(needLabels[n]??n)).join(', '):t('aucun parmi les mesures connues')}</p><p><b>${t('Contraintes')}</b> · ${a.constraints.length?a.constraints.map(c=>tx(constraintLabels[c]??c)).join(', '):t('aucune confirmée')}</p><p><b>${t('Bilan')}</b> · ${tx(coverageText(v))}</p>`;
}
/** The banner's « i » answers its pill: « Pourquoi « Au mieux » ? », in one plain sentence, then what to correct (as measured),
 * what holds the gesture back and whether the measures answer. */
export function whyRoom(v:View,slide?:Slide):TemplateResult {
  if(v.advisor)return why3(v.advisor);
  const want=needs(v).map(x=>tx(x)),limits=v.assessment.constraints.map(c=>tx(constraintLabels[c]??c));
  const pill=statePill(slide,v.assessment.level),list=want.join(', ');
  const airing=!!slide&&/^(Encore |Laissez ouvert)|^Aération en cours$/.test(slide.title);
  const why=pill==='Au mieux'?(airing?(list?t('Le geste est fait : l’aération en cours corrige {what}. Rien de mieux à faire d’ici là.',{what:list}):t('Le geste est fait : l’aération en cours fait son effet. Rien de mieux à faire d’ici là.'))
      :list?t('{what} : hors de votre plage, mais aucun geste ne ferait mieux pour l’instant.',{what:list.charAt(0).toUpperCase()+list.slice(1)}):t('Aucun geste ne ferait mieux pour l’instant.'))
    :pill==='Tout va bien'?t('Toutes les mesures sont dans votre plage : rien à corriger.')
    :pill==='Geste conseillé'?(slide?t('« {gesture} » : c’est le geste qui aide le plus maintenant.',{gesture:tx(slide.title)}):t('Un geste améliorerait la pièce maintenant.'))
    :pill==='À saisir'?t('Une occasion d’améliorer la pièce, sans urgence.')
    :pill==='Attention'?(slide?t('« {gesture} » : à faire vite.',{gesture:tx(slide.title)}):t('Une mesure demande d’agir vite.'))
    :pill==='Plus tard'?t('Le meilleur moment pour agir viendra plus tard.')
    :pill==='Conseil optimisé'?t('Ce conseil tient compte de ce que la pièce a appris.')
    :['À vérifier','Capteurs muets','Un capteur muet','Démarrage'].includes(pill)?t('Hestia ne peut pas encore juger toute la pièce : {cover}.',{cover:tx(coverageText(v)).toLowerCase()})
    :list?t('{what}.',{what:list.charAt(0).toUpperCase()+list.slice(1)}):'';
  const row=(ic:string,label:string,text:string)=>html`<div class="nc-why-row">${icon(ic)}<span>${label}</span><b>${text}</b></div>`;
  // Whether to trust it: what holds the gesture back, the measures, what the room learned and its last airing.
  const known=facts(v),said=(title:string)=>known.find(f=>f.title===title);
  const learning=slide?.learned?t('conseil optimisé, {how}',{how:tx(slide.learned)}):said('Apprentissage')?.text,last=said('Dernière aération')?.text;
  const shared=v.assessment.reason==='shared_volume'&&v.assessment.features?.volume?.lead;
  return html`<p class="nc-why-head"><b>${t('Pourquoi « {pill} » ?',{pill:tx(pill)})}</b> ${why}</p>
    ${limits.length?row('alert',t('Ce qui limite'),limits.join(' · ')):nothing}
    ${shared?row('home',t('Même air'),t('conseil commun avec : {room}',{room:shared})):nothing}
    ${row('source',t('Mesures'),coverageText(v)==='Sources configurées disponibles'?t('toutes répondent'):tx(coverageText(v)))}
    ${learning?html`<div class="nc-why-row">${icon('flask')}<span>${t('Apprentissage')}</span><b>${typeof learning==='string'?tx(learning):tl(learning)}</b></div>`:nothing}
    ${last?html`<div class="nc-why-row">${icon('open')}<span>${t('Dernière aération')}</span><b>${typeof last==='string'?tx(last):tl(last)}</b></div>`:nothing}`;
}
/** Hero shared by the room and home cards: name, « i », level pill, the gesture, the disk, then the scale. */
export function hero(o:{name:string;level:Level;slides:Slide[];scaleLabel:string;scale:TemplateResult;st:CardState;why:TemplateResult;compact?:boolean;still?:boolean;small?:boolean;after?:TemplateResult|typeof nothing;graph?:TemplateResult|typeof nothing;
  /** As Hestia Weather: « En ce moment » on the right (the pill, the temperature, its day), a line after the name, the advice in a bubble on a folded tile. */
  now?:TemplateResult|typeof nothing;sub?:string;bubble?:boolean}):TemplateResult {
  const many=o.slides.length>1;
  const pill=html`<span class="nw-chip nc-level">${many?t('{n} conseils',{n:o.slides.length}):pillMark(o.slides[0]?.pill??pills[o.level],o.slides[0]?.level??o.level,!!o.slides[0]?.learned)}</span>`;
  return html`<div class=${'nc-hero'+(o.small?' nc-compact':'')+(o.now!==undefined?' nc-weatherlike':'')+(o.bubble?' nc-folded':'')} data-mood=${mood(o.slides[0],o.level)}>
    <div class="nc-top"><div class="nc-name"><h2>${o.name}</h2><button class="nw-info" aria-label=${t('Pourquoi ce conseil ?')} aria-expanded=${o.st.why} aria-controls=${o.st.uid+'-why'} @click=${()=>o.st.toggle('why')}></button>${o.sub?html`<span class="nc-sub">${o.sub}</span>`:nothing}</div>
      ${o.now!==undefined?html`<div class="nc-moment">${pill}${o.now}</div>`:pill}</div>
    <div class=${o.bubble?'nc-bubble':''}><hestia-advice-ticker .slides=${o.slides} .still=${!!o.still}></hestia-advice-ticker></div>
    <div class="nc-why" id=${o.st.uid+'-why'} ?hidden=${!o.st.why}>${o.why}</div>
    ${o.compact?nothing:html`<div class="nc-sec nw-glass"><div class="nw-label">${o.scaleLabel}</div>${o.scale}</div>`}
    ${o.graph??nothing}
    ${o.after??nothing}
  </div>`;
}
/** The room card's banner (30 October, evening): the room and its day, the state's pill, then the advice beside its tinted
 * square and « En ce moment » on the right. A still light of the advice's colour starts here and runs on behind « À savoir ». */
export function banner(o:{name:string;sub?:string;level:Level;slides:Slide[];st:CardState;why:TemplateResult;still?:boolean;now?:TemplateResult|typeof nothing;compact?:boolean;after?:TemplateResult|typeof nothing}):TemplateResult {
  const first=o.slides[0];
  const pill=html`<span class="nw-chip nc-level">${pillMark(statePill(first,o.level),first?.level??o.level)}</span>`;
  return html`<div class=${'nc-b'+(o.compact?' compact':'')} data-mood=${mood(o.slides[0],o.level)}>
    <div class="nc-b-light" aria-hidden="true"></div>
    <div class="nc-b-top"><div class="nc-b-id"><div class="nc-b-name"><h2 class="nw-title">${o.name}</h2><button class="nw-info" aria-label=${t('Pourquoi ce conseil ?')} aria-expanded=${o.st.why} aria-controls=${o.st.uid+'-why'} @click=${(e:Event)=>{e.stopPropagation();o.st.toggle('why');}}></button>${pill}</div>${o.sub?html`<span class="nc-b-sub">${o.sub}</span>`:nothing}</div>
      ${o.now&&o.now!==nothing?html`<div class="nc-b-now">${o.now}</div>`:nothing}</div>
    <div class="nc-why nc-b-why nw-glass" id=${o.st.uid+'-why'} ?hidden=${!o.st.why}>${o.why}</div>
    <div class="nc-b-main nw-glass"><hestia-advice-ticker layout="banner" .slides=${o.slides.slice(0,1)} .still=${!!o.still}></hestia-advice-ticker></div>
    ${o.after??nothing}
  </div>`;
}
/** A section of the full card, always open: its title and what it counts, then its content. */
const part=(label:string,summary:TemplateResult|string,body:TemplateResult)=>html`<section class="nc-part"><header class="nc-part-h nw-section-head"><h2>${label}</h2>${summary?html`<span class="nw-sum">${summary}</span>`:nothing}</header>${body}</section>`;
/** A folding section with the charter's round chevron; out-of-range tiles stay visible when folded. */
export function fold(o:{label:string;summary:TemplateResult|string;open:boolean;onToggle:()=>void;id:string;body:TemplateResult;keep?:TemplateResult[]}):TemplateResult {
  return html`<div class=${'nc-fold'+(o.open?' open':'')}><button class="nw-fold-head" aria-expanded=${o.open} aria-controls=${o.id} @click=${o.onToggle}><span class="nw-label">${o.label}</span><span class="nw-sum">${o.summary}</span><span class="nw-chevron"><i class="nw-chev"></i></span></button>
    <div id=${o.id}>${o.open?o.body:o.keep?.length?html`<div class="nc-tiles">${o.keep}</div>`:nothing}</div></div>`;
}
/** « 4 mesures · 1 à surveiller · 2 muettes »: a silent measure is never counted as fine. */
/** « 4 mesures », « 3 pièces »: the summary counts measures or rooms. */
const counted=(unit:string,n:number)=>unit==='pièce'?(n>1?t('{n} pièces',{n}):n?t('{n} pièce',{n}):t('Aucune pièce')):(n>1?t('{n} mesures',{n}):n?t('{n} mesure',{n}):t('Aucune mesure'));
export const tileSummary=(n:number,k:number,unit:string,mute=0,waiting=false)=>n?html`${counted(unit,n)}${k?html` · <b>${t('{n} à surveiller',{n:k})}</b>`:''}${mute?(waiting?` · ${t('{n} en attente',{n:mute})}`:` · ${mute>1?t('{n} muettes',{n:mute}):t('{n} muette',{n:mute})}`):''}${!k&&!mute?` · ${t('rien à signaler')}`:''}`:html`${counted(unit,0)}`;
/** The few values a tile or a mini line shows, out of range in amber. */
function chipValues(v:View,which:readonly Chip[]):{ic:string;text:string;out:boolean;entity?:string}[]{
  const o=v.observations,a=v.assessment,out=[];
  for(const c of which){
    if(c==='temperature'){const t=numeric(o.indoor_temperature);if(t!==null)out.push({ic:'temp',text:number(t)+' °C',out:a.needs.includes('cool')||a.needs.includes('heat'),entity:o.indoor_temperature?.source??undefined});}
    if(c==='humidity'){const h=numeric(o.indoor_humidity),degree=a.features?.humidity?.degree;if(h!==null)out.push({ic:'drop',text:number(Math.round(h))+' %',out:degree!==undefined?degree>=2:a.needs.includes('dry'),entity:o.indoor_humidity?.source??undefined});}
    if(c==='co2'){const x=numeric(o.co2);if(x!==null)out.push({ic:'air',text:number(x)+' ppm',out:a.features?.air?.co2_status==='high',entity:o.co2?.source??undefined});}
  }
  return out;
}
const chipRow=(list:ReturnType<typeof chipValues>)=>list.length?html`<div class="nc-chips">${list.map(c=>c.entity
  ?html`<button type="button" class=${'nc-chip nc-hit'+(c.out?' out':'')} title=${t('Détails')} @click=${(e:Event)=>moreInfo(e,c.entity!)}>${icon(c.ic)}${c.text}</button>`
  :html`<span class=${'nc-chip'+(c.out?' out':'')}>${icon(c.ic)}${c.text}</span>`)}</div>`:nothing;
/** Is something asked of the person? The alert format shows only then. */
export const asking=(v:View)=>['action','urgent'].includes(slides(v)[0]?.level??v.assessment.level);
/** A figure at the foot of a module: its label, its value, the sensor behind it. */
interface Stat {label:string;value:string;entity?:string;note?:string}
/** One module of « Maintenant », as Hestia Weather's Pluie or Vent: a title and its room, the measure with its way and its
 * half hour, then a few figures. A shared air shows each room in it (rows). */
interface Module {key:Piece;ic:string;title:string;src?:string;main?:Tile;/** The temperature as its « Ressenti » (views/feel.ts), drawn instead. */ feel?:TemplateResult|null;rows?:{room:string;tile:Tile}[];sub?:string;extra?:TemplateResult|typeof nothing;stats:Stat[];level:string;
  /** A curve other than the main measure's (the heating's power). */
  curve?:Trend;
  /** The windows open now, one line each: its name, what it is doing, its sensor a tap away. */
  list?:{label:string;value:string;entity:string;bad:boolean}[];
  /** Several measures shown one after the other, each the same way (the air: CO₂, VOC, particles; one air's rooms'
   * humidity): its name, the room it is measured in, the measure. */
  slides?:{label:string;room?:string;tile:Tile}[]}
const stat=(t:Tile,label=tx(t.label)):Stat=>({label,value:`${tx(t.value)}${t.unit&&t.value!=='—'?' '+t.unit:''}`,entity:t.entity,note:t.note});
const PIECE_LOOK:Record<Piece,[string,string]>={temperature:['temp','Température'],humidity:['drop','Humidité'],air:['air','Air'],openings:['window','Ouvertures'],heating:['heat','Chauffage']};
/** The modules of a room (and of the rooms sharing its air), each only when it has something to show. */
export function modules(v:View,config:Config,partners:View[]=[],o:{scale?:TemplateResult|null}={}):Module[] {
  const mods=new Set(config.modules??[]),rooms=[v,...partners],f=v.assessment.features,many=partners.length>0;
  // Each room's own tiles: a measure read from the room sharing this air shows once, where it is measured.
  const own=rooms.map(r=>({room:r.title,tiles:many?ownTiles(r,tiles(r,config)):tiles(r,config)}));
  const find=(labels:string[])=>own.flatMap(r=>r.tiles.filter(t=>labels.includes(t.label)).map(t=>({room:r.room,tile:t})));
  const out:Module[]=[],level=(t?:Tile)=>t?.out&&!t.remedy?String(t.level):'calm';
  if(mods.has('temperature')){const main=roomTemperature(v)[0];
    if(main){const d=f?.day_range,te=numeric(v.observations.outdoor_temperature),slope=f?.trends?.curves?.temperature?.slope;
      const stats:Stat[]=[...partners.flatMap(p=>roomTemperature(p).map(t=>stat(t,p.title))),
        ...(te!==null?[{label:t('Dehors'),value:number(te)+' °C',entity:v.observations.outdoor_temperature?.source??undefined}]:[]),
        ...(slope!=null&&!d?[{label:t('Tendance'),value:(slope>0?'+':'')+number(slope)+' °C/h'}]:[])];
      out.push({key:'temperature',ic:'temp',title:PIECE_LOOK.temperature[1],src:many?v.title:undefined,main,sub:tx(main.note),extra:o.scale??nothing,stats:stats.slice(0,4),level:level(main),
        feel:feelPanel(v,partners,{gauge:!!o.scale,src:many?v.title:undefined})});}}
  const hum=find(['Humidité']);
  if(hum.length){const h=f?.humidity,lead=hum.find(x=>x.tile.out)??hum[0],ho=numeric(v.observations.outdoor_humidity);
    // One air's rooms one after the other, the most humid first, each drawn the same way as the air's measures.
    const order=[...hum.filter(x=>x.tile.out),...hum.filter(x=>!x.tile.out)];
    out.push({key:'humidity',ic:'drop',title:PIECE_LOOK.humidity[1],src:hum.length===1&&many?hum[0].room:undefined,main:lead.tile,
      slides:hum.length>1?order.map(x=>({label:x.room,tile:x.tile})):undefined,
      sub:hum.length>1?hum.filter(x=>x.tile.out).map(x=>`${x.room} : ${tx(x.tile.note)}`).join(' · '):tx(lead.tile.note),
      stats:[...(h?.minimum!=null&&h?.maximum!=null?[{label:t('Plage'),value:`${number(h.minimum)}–${number(h.maximum)} %`}]:[]),
        ...(ho!==null?[{label:t('Dehors'),value:number(ho)+' %',entity:v.observations.outdoor_humidity?.source??undefined}]:[]),
        ...(h?.dew_point!=null?[{label:t('Rosée'),value:number(h.dew_point)+' °C',note:'Point de rosée'}]:[])],level:level(lead.tile)});}
  const air=find(['CO₂','COV','Particules','Purificateur','Ventilation']);
  if(air.length){const measures=air.filter(x=>['CO₂','COV','Particules'].includes(x.tile.label)),lead=measures.find(x=>x.tile.out)??measures[0]??air[0];
    const name=(x:typeof lead)=>many&&x.room!==lead.room?`${tx(x.tile.label)} · ${x.room}`:tx(x.tile.label);
    // A list (31 October): every measure and device a line, grouped by room when the air has two; those out first.
    // A room shown alone puts a measure borrowed from the next room under that room's name.
    const at=(x:typeof lead)=>many?x.room:v.inherited?.[tileKeys[x.tile.label]??'']??x.room;
    const rooms=[...new Set(air.map(at))],byRoom=rooms.flatMap(r=>{const of=air.filter(x=>at(x)===r);return [...of.filter(x=>x.tile.out&&!x.tile.remedy),...of.filter(x=>!(x.tile.out&&!x.tile.remedy))];});
    const outs=measures.filter(x=>x.tile.out&&!x.tile.remedy);
    out.push({key:'air',ic:'air',title:PIECE_LOOK.air[1],src:many&&rooms.length<2?lead.room:undefined,main:lead.tile,
      slides:air.length>1?byRoom.map(x=>({label:tx(x.tile.label),room:rooms.length>1?at(x):undefined,tile:x.tile})):undefined,
      sub:air.length>1?outs.map(x=>`${tx(x.tile.label)} ${tx(x.tile.note)}`).join(' · '):`${tx(lead.tile.label)} · ${tx(lead.tile.note)}`,
      stats:air.length>1?[]:air.filter(x=>x!==lead).map(x=>stat(x.tile,name(x))),level:level(lead.tile)});}
  // The windows and the sun are the shared air's: said once, by the first room (as the tiles did).
  const open=find(['Fenêtres','Soleil','Volet']).filter((x,i,all)=>x.tile.label==='Volet'||all.findIndex(y=>y.tile.label===x.tile.label)===i);
  if(open.length){const lead=open.find(x=>x.tile.label==='Fenêtres')??open[0];
    // The sun's curve said little (3 November): the windows open now say more, one line each, those to close first.
    const seen=new Set<string>(),list=rooms.flatMap(r=>Object.entries(r.observations).filter(([k,x])=>k.startsWith('window:')&&x.quality==='valid'&&x.value===true).map(([k])=>k.slice(7))
      .filter(id=>!seen.has(id)&&!!seen.add(id)).map(id=>{const bad=rooms.some(q=>(q.assessment.openings??[]).some(x=>x.entity_id===id&&x.flags.length>0));
        return {label:r.names?.[id]??v.names?.[id]??id,value:bad?'à refermer':'ouverte',entity:id,bad};}));
    out.push({key:'openings',ic:lead.tile.ic,title:PIECE_LOOK.openings[1],main:lead.tile,sub:tx(lead.tile.note),list:mods.has('windows')?[...list.filter(x=>x.bad),...list.filter(x=>!x.bad)]:undefined,
      stats:open.filter(x=>x!==lead).map(x=>x.tile.label==='Soleil'&&x.tile.note&&/W\/m²/.test(x.tile.note)?{...stat(x.tile),value:`${tx(x.tile.value)} · ${x.tile.note.split(' · ')[0]}`}:stat(x.tile)),
      level:level(lead.tile)});}
  const heat=find(['Chauffage']);
  if(heat.length){const lead=heat[0];
    // The set point, how far the room is from it, and how long it heated over the last day.
    const target=numeric(v.observations.heating_target),ti=numeric(v.observations.indoor_temperature),day=f?.heating_day?.minutes;
    const hm=(m:number)=>m<60?`${m} min`:`${Math.floor(m/60)} h${m%60?' '+String(m%60).padStart(2,'0'):''}`;
    const stats:Stat[]=[...(target!==null?[{label:t('Consigne'),value:number(target)+' °C',entity:v.observations.heating_target?.source??undefined}]:[]),
      ...(target!==null&&ti!==null&&!['frost','eco','away','off','sleep'].includes(String(v.observations.heating_mode?.value??''))?[{label:t('Écart'),value:`${ti-target>0?'+':ti-target<0?'−':''}${number(Math.abs(Math.round((ti-target)*10)/10))} °C`}]:[]),
      ...(day!=null?[{label:t('Chauffe 24 h'),value:day?hm(day):t('aucune')}]:[])];
    out.push({key:'heating',ic:'heat',title:PIECE_LOOK.heating[1],src:many?lead.room:undefined,main:lead.tile,rows:heat.length>1?heat:undefined,sub:lead.tile.note?tx(lead.tile.note):undefined,stats,curve:lead.tile.curve,level:'calm'});}
  return out;
}
const statBody=(x:Stat)=>html`<span>${x.label}</span><b>${x.value}</b>`;
/** A module, drawn as Hestia Weather's: header, the measure, its half hour, its figures; each value opens its sensor. */
export function moduleCard(m:Module,soft=true):TemplateResult {
  if(m.feel)return m.feel;
  const value=(t:Tile)=>html`${tx(t.value)}${t.unit&&t.value!=='—'?html`<small>${t.unit}</small>`:nothing}${t.trend?trendArrow(t.trend):nothing}`;
  const hit=(t:Tile,body:TemplateResult,cls:string)=>t.entity?html`<button type="button" class=${cls+' nc-hit'} title=${tr('Détails : {label}',{label:tx(t.label)})} @click=${(e:Event)=>moreInfo(e,t.entity!)}>${body}</button>`:html`<div class=${cls}>${body}</div>`;
  const main=m.rows?html`<div class="nc-mod-rows">${m.rows.map(r=>hit(r.tile,html`<span>${r.room}</span><b>${value(r.tile)}</b>`,'nc-mod-row'+(r.tile.out?' out':'')))}</div>`
    :m.main?hit(m.main,html`<b>${value(m.main)}</b>`,'nc-mod-v nw-value'):nothing;
  // The temperature moves by tenths in half an hour: its scale, its day and its arrow say it better than a flat curve.
  const curve=m.curve??(m.key==='temperature'||m.key==='openings'?undefined:m.rows?(m.rows.find(r=>r.tile.out)??m.rows[0]).tile.trend:m.main?.trend);
  const turning=m.slides&&m.slides.length>1?modSlides(m.slides,value,hit):null;
  return html`<div class=${'nc-mod nw-panel'+(m.level!=='calm'?' out'+(soft?' soft':''):'')} data-piece=${m.key} data-level=${m.level}>
    <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(m.ic)}</span><h3>${tx(m.title)}</h3>${m.main?.flame?html`<span class="nc-flame" title=${t('mode chauffage')}>${icon('flame')}</span>`:nothing}${m.src?html`<span class="aside nc-src">${m.src}</span>`:nothing}</div>
    ${turning?html`${turning}${m.sub?html`<p class="nc-mod-sub nc-mrows-sub">${m.sub}</p>`:nothing}`:html`<div class="nc-mod-line">${main}${m.sub?html`<p class="nc-mod-sub">${m.sub}</p>`:nothing}</div>${m.extra??nothing}${curve?sparkline(curve):nothing}`}
    ${m.list?.length?html`<div class="nc-mrows nc-open-list">${m.list.map(x=>html`<button type="button" class=${'nc-mrow'+(x.bad?' bad':'')} title=${tr('Détails : {label}',{label:x.label})} @click=${(e:Event)=>moreInfo(e,x.entity)}><i class="nc-mrow-dot" aria-hidden="true"></i><span class="nc-mrow-n">${x.label}</span><b class="nc-mrow-v">${tx(x.value)}</b></button>`)}</div>`:nothing}
    ${m.stats.length?html`<div class="nc-mod-stats nw-stats" style=${`--n:${Math.min(m.stats.length,4)}`}>${m.stats.map(x=>x.entity?html`<button type="button" class="nc-hit" title=${x.note?tx(x.note):tr('Détails : {label}',{label:x.label})} @click=${(e:Event)=>moreInfo(e,x.entity!)}>${statBody(x)}</button>`:html`<div title=${x.note?tx(x.note):nothing}>${statBody(x)}</div>`)}</div>`:nothing}
  </div>`;
}
/** The air's measures one after the other: each its name, its value and way, its note, its half hour. */
function modSlides(list:{label:string;room?:string;tile:Tile}[],_value:(t:Tile)=>TemplateResult,hit:(t:Tile,body:TemplateResult,cls:string)=>TemplateResult):TemplateResult {
  // A2 (31 October): a small heading per room when there are two, then a line per measure: its state's dot, its name,
  // its value, its way and its half hour with the dot at its end. A measure treated (filtered) is fine.
  let room:string|undefined;
  const rows=list.map(x=>{const head=x.room&&x.room!==room?html`<div class="nc-mrow-room">${x.room}</div>`:nothing;room=x.room;
    const bad=!!x.tile.out&&!x.tile.remedy,num=x.tile.value!=='—'&&/^[\d\s,.−-]+$/.test(tx(x.tile.value));
    return html`${head}${hit(x.tile,html`<i class="nc-mrow-dot" aria-hidden="true"></i><span class="nc-mrow-n">${x.label}</span>
      <b class="nc-mrow-v">${tx(x.tile.value)}${num&&x.tile.unit?html`<small>${x.tile.unit}</small>`:nothing}</b>
      <span class="nc-mrow-w">${x.tile.trend?trendArrow(x.tile.trend):nothing}</span><span class="nc-mrow-c">${x.tile.trend?sparkline(x.tile.trend):nothing}</span>`,'nc-mrow'+(bad?' bad':''))}`;});
  return html`<div class="nc-mrows">${rows}</div>`;
}
/** « À la carte », compact: the measure, its way and its half hour, nothing else. */
export function moduleCompact(m:Module):TemplateResult {
  const t0=m.rows?(m.rows.find(r=>r.tile.out)??m.rows[0]).tile:m.main;
  const value=(t:Tile)=>html`${tx(t.value)}${t.unit&&t.value!=='—'?html`<small>${t.unit}</small>`:nothing}${t.trend?trendArrow(t.trend):nothing}`;
  const main=m.rows?html`<div class="nc-mod-rows">${m.rows.map(r=>html`<div class=${'nc-mod-row'+(r.tile.out?' out':'')}><span>${r.room}</span><b>${value(r.tile)}</b></div>`)}</div>`
    :m.main?html`<div class="nc-mod-v nw-value"><b>${value(m.main)}</b></div>`:nothing;
  if(m.slides&&m.slides.length>1)return html`<div class=${'nc-mod nw-panel nc-mod-compact'+(m.level!=='calm'?' out soft':'')} data-piece=${m.key} data-level=${m.level}>
    <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(m.ic)}</span><h3>${tx(m.title)}</h3>${m.src?html`<span class="aside nc-src">${m.src}</span>`:nothing}</div>
    ${modSlides(m.slides,value,(_t,body,cls)=>html`<div class=${cls}>${body}</div>`)}</div>`;
  return html`<div class=${'nc-mod nw-panel nc-mod-compact'+(m.level!=='calm'?' out soft':'')} data-piece=${m.key} data-level=${m.level}>
    <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(m.ic)}</span><h3>${tx(m.title)}</h3>${m.main?.flame?html`<span class="nc-flame" title=${t('mode chauffage')}>${icon('flame')}</span>`:nothing}${m.src?html`<span class="aside nc-src">${m.src}</span>`:nothing}</div>
    ${main}${m.sub?html`<p class="nc-mod-sub">${m.sub}</p>`:nothing}${(m.curve??t0?.trend)?sparkline((m.curve??t0?.trend)!):nothing}
  </div>`;
}
/** « Maintenant »: the temperature across, the others two by two, as Hestia Weather's « Aujourd’hui ». */
const moduleGrid=(list:Module[],soft:boolean)=>{const wide=list.filter(m=>m.key==='temperature'),rest=list.filter(m=>m.key!=='temperature');
  return html`<div class="nc-mods">${wide.map(m=>moduleCard(m,soft))}${rest.length?html`<div class="nc-mod-grid">${rest.map(m=>moduleCard(m,soft))}</div>`:nothing}</div>`;};
/** « À venir », as Hestia Weather's forecasts beside « Aujourd'hui »: each subject's next hours in its own module (what to do as
 * its title, the graph, what it changes), the next gesture, and outside. Modules of the same make as « Maintenant ». */
function upcoming(v:View,config:Config,plage:(s:HorizonSubject)=>[number,number]|null):TemplateResult|typeof nothing {
  const a=v.assessment,f=a.features;
  // Only what says something: a gesture compared with doing nothing, or a forecast that leaves your range.
  const leaves=(h:Horizon)=>{const p=plage(h.subject),all=[...h.base,...(h.gesture??[])];return !!p&&all.length>0&&(Math.min(...all)<p[0]||Math.max(...all)>p[1]);};
  const shown=horizonShown(f?.horizon??[],'always',config.horizon_subjects).filter(h=>h.kind!=='trend'||leaves(h));
  const mods:TemplateResult[]=shown.map(h=>html`<div class="nc-mod nw-panel nc-mod-h24 nc-mod-wide" data-piece=${h.subject}>
      <div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(h.subject==='humidity'?'drop':'temp')}</span><h3>${h.subject==='humidity'?t('Humidité'):t('Température')}</h3><span class="nc-mod-h24-what">${horizonHead(h)}</span></div>
      <p class="nc-mod-sub nc-mod-h24-result">${horizonResult(h)}</p>
      <div class="nc-horizon">${horizonChart(h,plage(h.subject))}</div>${horizonLegend(h)}</div>`);
  // The next gesture, when there is one: what « plus tard » would have said in the banner.
  const later=slides(v,['later']).slice(1)[0];
  if(later)mods.push(html`<div class="nc-mod nw-panel" data-piece="next"><div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon(later.disk??'clock')}</span><h3>${t('Prochain geste')}</h3></div>
    <div class="nc-mod-v nw-value"><b class="nc-mod-text">${tx(later.title)}</b></div>${later.line?html`<p class="nc-mod-sub">${tl(later.line)}</p>`:nothing}</div>`);
  // Outside, only when rain is on its way.
  if(a.constraints.includes('rain_soon')||a.rain_soon_minutes!=null)mods.push(html`<div class="nc-mod nw-panel" data-piece="outside"><div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon('rain')}</span><h3>${t('Dehors')}</h3></div>
    <div class="nc-mod-v nw-value"><b class="nc-mod-text">${t('Pluie {when}',{when:tx(rainWhen(a))})}</b></div></div>`);
  return mods.length?html`<div class="nc-mods nc-upcoming"><div class="nc-mod-grid">${mods}</div></div>`:nothing;
}
/** « En ce moment », on the right of the banner as in Hestia Weather: the temperature, then its day (or the room beside it). */
function nowBlock(v:View,partners:View[]):TemplateResult|typeof nothing {
  const ti=numeric(v.observations.indoor_temperature),d=v.assessment.features?.day_range;
  if(ti===null)return nothing;
  const other=partners.map(p=>({p,t:numeric(p.observations.indoor_temperature)})).find(x=>x.t!==null);
  const src=v.observations.indoor_temperature?.source;
  // The charter's reading (hestia-lecture), the same as Hestia Weather's « En ce moment »; without its day, the room beside it.
  return html`${lecture({value:number(ti),unit:'°C',low:d?number(d.min):undefined,high:d?number(d.max):undefined,rangeTitle:d?t('min–max 24 h'):undefined,
      tapTitle:t('Détails de la température'),onTap:src?(e:Event)=>moreInfo(e,src):undefined})}
    ${!d&&other?html`<span class="nw-range">${other.p.title} ${number(other.t!)}°</span>`:nothing}`;
}
/** The room card in each format; null when the alert format has nothing to say. */
export function roomCard(v:View,config:Config,st:CardState,format:Format='full',partners:View[]=[]):TemplateResult|null {
  const a=v.assessment,f=a.features,ti=numeric(v.observations.indoor_temperature),te=numeric(v.observations.outdoor_temperature);
  // Rooms sharing one air are one card: the other rooms' own measures, without the windows and the sun they share.
  const shared=new Set(['Fenêtres','Soleil']),others=partners.map(p=>({title:p.title,list:[...roomTemperature(p),...ownTiles(p,tiles(p,config)).filter(t=>!shared.has(t.label)&&t.label!=='Température')]}));
  // On a card shared by several rooms, the scale shows the first room's temperature: its own tile says so too.
  const own=partners.length?[...roomTemperature(v),...ownTiles(v,tiles(v,config))]:tiles(v,config),list=[...own,...others.flatMap(o=>o.list)],outside=list.filter(t=>t.out&&!t.remedy),muted=list.filter(t=>tileClass(t).includes(' mute'));
  const marks=config.scale_marks??(config.show_scale===false?[]:SCALE_MARKS);
  const band:[number,number]|null=f?.season&&marks.includes('band')?[f.season.minimum,f.season.maximum]:null;
  const sc=(config.modules??[]).includes('temperature')&&marks.length&&ti!==null
    ?scale({band,day:marks.includes('day')?f?.day_range??null:null,now:ti,out:marks.includes('out')?te:null,nowEntity:v.observations.indoor_temperature?.source??undefined,outEntity:v.observations.outdoor_temperature?.source??undefined}):null;
  // One air whose gesture comes from the other room: the banner says that room's advice, its reason and what it learned.
  const leader=a.reason==='shared_volume'?partners.find(p=>p.title===a.features?.volume?.lead&&p.assessment.reason!=='shared_volume'):undefined;
  const said=v.advisor?v:leader??v,all=slides(said,config.banner_blocks).map(s=>({...s,scene:sceneFor(s,said)})),top=all[0]?.level??a.level,name=config.title||(partners.length?v.volume_name:null)||v.title;
  const still=config.animations===false||config.rotate===false;
  // A measure out of range is framed in orange only when the room asks for a gesture.
  const soft=!['action','urgent'].includes(top);
  // What is worth a look only: how many measures the room has is no news (30 October, evening).
  const summary=html`${outside.length?html`<b>${t('{n} à surveiller',{n:outside.length})}</b>`:''}${muted.length?`${outside.length?' · ':''}${v.starting?t('{n} en attente',{n:muted.length}):muted.length>1?t('{n} muettes',{n:muted.length}):t('{n} muette',{n:muted.length})}`:''}`;
  // Folded, a card shared by several rooms names each room on the measures it keeps: « Salon », « Cuisine », not twice « Température ».
  const named=(t:Tile,room:string)=>others.length?{...t,label:t.label==='Température'?room:`${t.label} · ${room}`}:t;
  const watched=[...own.map(t=>named(t,v.title)),...others.flatMap(o=>o.list.map(t=>named(t,o.title)))].filter(t=>(t.out&&!t.remedy)||tileClass(t).includes(' mute'));
  const grid=others.length?html`<div class="nw-label nc-room-label">${v.title}</div><div class="nc-tiles">${own.map(t=>tile(t,soft))}</div>${others.map(o=>o.list.length?html`<div class="nw-label nc-room-label">${o.title}</div><div class="nc-tiles">${o.list.map(t=>tile(t,soft))}</div>`:nothing)}`
    :html`<div class="nc-tiles">${list.map(t=>tile(t,soft))}</div>`;
  const known=factList(v,partners,config),box=factBox(v,partners,config,known);
  // « Au mieux »: the disk shows what « À savoir » names first, whichever room of the shared air it comes from.
  if(!v.advisor&&all.length===1&&all[0].pill==='Au mieux'&&known[0])all[0]={...all[0],disk:known[0].key==='humidity'?'drop':known[0].key==='cold'?'temp':all[0].disk};
  const detailList=html`<ul class="nc-list">${details(v,config)}</ul>${st.configure?html`<button class="nw-badge nc-configure" @click=${st.configure}>${icon('settings')}${t('Configurer cette pièce')}</button>`:nothing}`;
  const scaleBox=sc?html`<div class="nc-sec nw-glass"><div class="nw-label">${t('Température')}</div>${sc}</div>`:nothing;
  // « Prochaines heures » (engine/horizon.py): under the scale, the banner's subject first, the other one behind a tab.
  const hum=f?.humidity,season=f?.season;
  const plage=(s:HorizonSubject):[number,number]|null=>s==='humidity'?(hum?.minimum!=null&&hum?.maximum!=null?[hum.minimum,hum.maximum]:null):(season?[season.minimum,season.maximum]:null);
  const graph=config.show_horizon===false?nothing:horizonBox(f?.horizon??[],{subjects:config.horizon_subjects,mode:config.horizon_mode,uid:st.uid,second:!!st.horizonAlt,onTab:()=>st.toggle('horizonAlt'),plage});
  if(format==='mini'){
    // One thin line: the advice's tinted square, the room and its advice, a value or two, the temperature.
    const values=chipValues(v,config.mini_values??['temperature']),temp=values.find(c=>c.ic==='temp'),first=all[0];
    return html`<ha-card class="nc-c nc-mini-card" data-level=${top}><span class="nc-orb small" data-level=${first?.level??top} data-mood=${mood(first,top)}><span class="nc-orb-ring"></span>${icon(first?.disk??'check')}</span>
      <span class="nc-mi-text"><span>${name}</span><b>${tx(first?.title)}</b></span>${values.filter(c=>c!==temp).map(c=>html`<span class=${'nc-mi-val'+(c.out?' out':'')}>${icon(c.ic)}${c.text}</span>`)}${temp?html`<span class="nc-mi-t">${temp.text.replace(' °C','')}<small>°</small></span>`:nothing}</ha-card>`;
  }
  // The modules of « Maintenant », the scale inside the temperature's (switched off, the module keeps its figures).
  const scaleIn=config.show_scale===false||(config.show_scale===undefined&&config.scale_marks?.length===0)?null:sc;
  const mods=modules(v,config,partners,{scale:scaleIn});
  if(format==='measures')
    return html`<ha-card class="nc-c nc-measures-card" data-level="neutral"><div class="nc-mhead"><h2>${name}</h2><span class="nw-sum">${summary}</span></div><div class="nc-mbody">${moduleGrid(modules(v,config,partners,{scale:config.show_scale===true||config.scale_marks?.length?sc:null}),true)}</div></ha-card>`;
  // One card per piece of the room: the full card's module alone, or its « Prochaines heures ».
  if(format==='horizon')
    return html`<ha-card class="nc-c nc-piece-card" data-level="neutral"><div class="nc-mod nw-panel" data-piece="horizon"><div class="nc-mod-h nw-panel-head"><span class="nc-ic nw-panel-icon">${icon('clock')}</span><h3>${t('Prochaines heures')}</h3><span class="aside nc-src">${name}</span></div>${horizonBox(f?.horizon??[],{subjects:config.horizon_subjects,mode:config.horizon_mode??'always',uid:st.uid,second:!!st.horizonAlt,onTab:()=>st.toggle('horizonAlt'),
      plage:x=>x==='humidity'?(hum?.minimum!=null&&hum?.maximum!=null?[hum.minimum,hum.maximum]:null):(season?[season.minimum,season.maximum]:null)})}</div></ha-card>`;
  if((PIECES as readonly string[]).includes(format)){
    const m=mods.find(x=>x.key===format);
    return html`<ha-card class=${'nc-c nc-piece-card'+(config.piece_style==='compact'?' compact':'')} data-level="neutral">${m?(config.piece_style==='compact'?moduleCompact({...m,src:m.src??name}):moduleCard({...m,src:m.src??name},true)):html`<p class="nc-mod-none">${t('{room} : rien à montrer ici. Vérifiez les capteurs et les rubriques de la carte.',{room:name})}</p>`}</ha-card>`;
  }
  if(format==='alert'){
    if(!asking(v))return null;
    // A low strip on the advice's colour: its square, the room and « Action à faire », the advice and what to touch; never a card's size.
    const first=all[0],tnow=numeric(v.observations.indoor_temperature);
    return html`<ha-card class="nc-c nc-alert-card" data-level=${first?.level??top}><span class="nc-orb small" data-level=${first?.level??top} data-mood=${mood(first,top)}><span class="nc-orb-ring"></span>${icon(first?.disk??'alert')}</span>
      <span class="nc-al-text"><span>${name} · ${t('Action à faire')}${all.length>1?html` · <b>${t('{n} conseils',{n:all.length})}</b>`:nothing}</span><b>${tx(first?.title)}</b>${first?.line?html`<em>${tl(first.line)}</em>`:nothing}</span>
      ${tnow!==null?html`<span class="nc-al-t">${number(tnow)}<small>°</small></span>`:nothing}</ha-card>`;
  }
  const now=nowBlock(v,partners);
  // « Maintenant », « Prochaines heures », « Détails »: the full card's sections, as Hestia Weather's « Aujourd’hui » and « Prévisions ».
  const measures=mods.length>0&&config.show_measures!==false,hasGraph=graph!==nothing;
  // « À venir » says only what is worth it; with nothing to say, it is left out.
  const coming=config.show_horizon===false?nothing:upcoming(v,config,plage);
  // Always « Maintenant », then « À venir », then « Détails », whatever order the settings list them in.
  const sections=(blocks:readonly string[])=>{const parts=['measures','horizon','details'].filter(b=>blocks.includes(b)).map(b=>
      // « Maintenant » is titled only when « À venir » follows it: alone, the title says nothing (3 November).
      b==='measures'&&measures?(blocks.includes('horizon')&&config.show_horizon!==false&&coming!==nothing?part(t('Maintenant'),summary,moduleGrid(mods,soft)):html`<section class="nc-part">${moduleGrid(mods,soft)}</section>`)
      :b==='horizon'&&config.show_horizon!==false&&coming!==nothing?part(t('À venir'),t('Prochaines 24 h'),coming as TemplateResult)
      :b==='details'&&config.show_details!==false?fold({label:t('Détails'),summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:st.uid+'-details',body:detailList}):null).filter(x=>x!==null);
    return parts.length?html`<div class="nc-body nc-sections">${parts}</div>`:nothing;};
  if(format==='tile'||format==='intermediate'){
    // The one foldable card: folded, the banner and a few values; a tap unfolds « À savoir » and the sections in place.
    const open=format==='intermediate'||!!st.unfolded;
    const blocks=(config.tile_blocks??TILE_BLOCKS).filter(b=>b!=='scale');
    const chips=open?nothing:chipRow([...chipValues(v,(config.tile_chips??CHIPS).filter(c=>c!=='temperature')),...partners.flatMap(p=>chipValues(p,['humidity']).map(c=>({...c,text:p.title+' '+c.text})))]);
    return html`<ha-card class=${'nc-c nc-tile-card'+(open?' open':' folded')} data-level=${top} ?data-starting=${!!v.starting}>
      ${banner({name,level:top,slides:all,st,why:whyRoom(v,all[0]),still,now,compact:true,after:html`${chips}${format==='tile'?html`<span class="nc-handle" aria-hidden="true"></span>`:nothing}`})}
      ${open?html`${box}${sections(blocks)}<div class="nc-foot"><span>${partners.length?t('Capteurs de {rooms}',{rooms:[v,...partners].map(r=>r.title).join(' et ')}):t('Capteurs de la pièce')}</span><span>${format==='tile'?t('Appui : replier · '):''}${t('Appui long : carte complète')}</span></div>`:nothing}
    </ha-card>`;
  }
  return html`<ha-card class="nc-c nc-full-card" data-level=${top} ?data-starting=${!!v.starting}>
    ${banner({name,level:top,slides:all,st,why:whyRoom(v,all[0]),still,now})}
    ${box}
    ${sections(['measures','horizon','details'])}
  </ha-card>`;
}

/** The advices, one at a time every 4.5 s (as Hestia Weather's ticker). Every slide sits in the same place,
    so the card keeps the height of the longest one. Pauses on hover or focus; a tap shows the next one. */
export class HestiaAdviceTicker extends LitElement {
  @property({attribute:false}) slides:Slide[]=[];
  @property({type:Boolean}) still=false;
  /** « banner »: the room card's banner (30 October, evening): the icon in its tinted square on the left, the advice beside it. */
  @property({type:String}) layout='';
  @state() private index=0;
  @state() private paused=false;
  private timer?:ReturnType<typeof setTimeout>;
  createRenderRoot(){return this;}
  connectedCallback(){super.connectedCallback();this.schedule();}
  disconnectedCallback(){super.disconnectedCallback();clearTimeout(this.timer);this.timer=undefined;}
  /** The advice that just left: it fades upward, whichever way the list turns. */
  private previous=-1;
  protected willUpdate(changed:Map<string,unknown>){if(changed.has('index'))this.previous=(changed.get('index') as number|undefined)??-1;if(changed.has('slides')&&this.index>=this.slides.length)this.index=0;}
  // The view is refreshed whenever a sensor moves (every few seconds for CO₂): a new list of slides
  // must not restart the countdown, or the first advice would never leave. Only a new slide, a pause
  // or a missing countdown starts one.
  protected updated(changed:Map<string,unknown>){
    if(changed.has('index')||changed.has('paused')||changed.has('still')||!this.timer)this.schedule();
  }
  private get calm(){return this.still||matchMedia('(prefers-reduced-motion: reduce)').matches;}
  private schedule(){
    clearTimeout(this.timer);this.timer=undefined;
    if(this.slides.length>1&&!this.paused&&!this.calm)this.timer=setTimeout(()=>{this.timer=undefined;this.index=(this.index+1)%this.slides.length;},4500);
  }
  private go(i:number){this.index=(i+this.slides.length)%this.slides.length;}
  private hold(on:boolean){this.paused=on;}
  protected render(){
    const list=this.slides,many=list.length>1,i=Math.min(this.index,list.length-1);
    if(!list.length)return nothing;
    if(this.layout==='banner')return this.banner(list,many,i);
    return html`<div class="nc-grid" @mouseenter=${()=>this.hold(true)} @mouseleave=${()=>this.hold(false)} @focusin=${()=>this.hold(true)} @focusout=${()=>this.hold(false)}
        @click=${(e:Event)=>{if(many&&!(e.target as HTMLElement).closest('.nc-bars'))this.go(i+1);}} style=${many?'cursor:pointer':''}>
      <div class="nc-copy">
        <div class="nc-tk-head"><span class="nw-label">${many?t('Conseils'):list[0]?.pill&&list[0].level==='neutral'?t('État'):['action','urgent'].includes(list[0]?.level)?t('Action à faire'):t('Conseil')}</span>${many?html`<span class="nc-tk-count">${t('{i} sur {n}',{i:i+1,n:list.length})}</span>
          <span class="nc-bars">${list.map((s,k)=>html`<button type="button" aria-label=${t('Conseil {n} : {title}',{n:k+1,title:tx(s.title)})} aria-current=${k===i?'true':'false'} data-level=${s.level} class=${k<i?'done':k===i?(this.paused||this.calm?'done':'on'):''} @click=${()=>this.go(k)}><i></i></button>`)}</span>`:nothing}</div>
        <div class="nc-stack" aria-live=${this.paused?'polite':'off'}>${list.map((s,k)=>html`<div class=${'nc-slide'+(k===i?' on':k===this.previous?' out':'')} aria-hidden=${k===i?'false':'true'}>
          ${many?html`<span class="nw-chip nc-slide-pill" data-level=${s.level}>${pillMark(s.pill,s.level,!!s.learned)}</span>`:nothing}<p class="nc-advice">${tx(s.title)}</p>${s.line?html`<p class="nc-line">${tl(s.line)}</p>`:nothing}</div>`)}</div>
      </div>
      <div class="nc-diskwrap nc-stack" aria-hidden="true">${list.map((s,k)=>html`<div class=${'nc-slide nc-diskslide'+(k===i?' on':k===this.previous?' out':'')} data-level=${s.level} data-mood=${mood(s,s.level)} ?data-learned=${!!s.learned}><div class="nc-disk" data-disk=${s.disk}>${icon(s.disk)}</div>${s.cap?html`<div class="nc-cap">${tx(s.cap)}</div>`:nothing}</div>`)}</div>
    </div>`;
  }
  /** The banner's layout: its tinted square with the pictogram, then « Action à faire », the advice, why, and what to touch. */
  private banner(list:Slide[],many:boolean,i:number){
    // The kicker says when: now, or under way; nothing when there is nothing to do.
    const when=(s:Slide)=>/^(Encore |Laissez ouvert)|^Aération en cours$/.test(s.title)?t('En cours'):s.title==='Rien à faire'||s.level==='neutral'||s.level==='calm'?'':t('Maintenant');
    // « Puis refermez » is the gesture's second half: in the title. The other tags were said elsewhere (À savoir, the « i »).
    const title=(s:Slide)=>s.cap==='Puis refermez'?`${tx(s.title)}, ${tx('puis refermez')}`:tx(s.title);
    return html`<div class="nc-bt" @mouseenter=${()=>this.hold(true)} @mouseleave=${()=>this.hold(false)} @focusin=${()=>this.hold(true)} @focusout=${()=>this.hold(false)}>
      <div class="nc-bt-copy">
        <div class="nc-stack" aria-live=${this.paused?'polite':'off'}>${list.map((s,k)=>html`<div class=${'nc-slide'+(k===i?' on':k===this.previous?' out':'')} aria-hidden=${k===i?'false':'true'}>
          ${when(s)||s.learned?html`<div class="nc-tk-head">${when(s)?html`<span class="nc-bt-kicker">${when(s)}</span>`:nothing}${s.learned?html`<span class="nc-bt-learned" title=${tx(s.learned)}>${icon('flask')}${t('Optimisé par l’apprentissage')}</span>`:nothing}</div>`:nothing}
          <p class="nc-advice">${title(s)}</p>${s.line?html`<p class="nc-line">${tl(s.line)}</p>`:nothing}</div>`)}</div>
      </div>
      <div class="nc-bt-icons nc-stack" aria-hidden="true">${list.map((s,k)=>s.scene?html`<div class=${'nc-slide nc-scene'+(k===i?' on':k===this.previous?' out':'')} data-level=${s.level}>${scene(s.scene)}</div>`
        :html`<div class=${'nc-slide nc-orb'+(k===i?' on':k===this.previous?' out':'')} data-level=${s.level} data-mood=${mood(s,s.level)}><span class="nc-orb-ring"></span>${icon(s.disk)}${s.learned?html`<span class="nc-orb-learned">${icon('flask')}</span>`:nothing}</div>`)}</div>
    </div>`;
  }
}
if(!customElements.get('hestia-advice-ticker'))customElements.define('hestia-advice-ticker',HestiaAdviceTicker);

/** What a room needs, as measured: « 68 % trop humide », « 282 COV élevés ». The home card shows it under
    the room, since the advice itself is already in its banner. A device at work is not a need. */
export function needs(v:View,includeSlight=true):string[] {
  const o=v.observations,a=v.assessment,air=a.features?.air,out:string[]=[],val=(k:string)=>numeric(o[k]);
  const h=val('indoor_humidity'),c=val('co2'),pm=val('pm25'),voc=val('voc');
  // The temperature is the tile's own figure, just above: the words alone.
  if(a.needs.includes('cool'))out.push('trop chaud');
  // A little cool, like slightly humid, is no room to watch on the home card.
  const slight=!!a.features?.warmth?.slight,cold=a.needs.includes('heat')&&(includeSlight||!slight)?(slight?'un peu frais':'trop frais'):null;
  // A cold the heating or a chosen preset takes care of is said after what nothing takes care of.
  const settled=coldSettled(a);
  if(cold&&!settled)out.push(cold);
  const humidity=humidityLabel(v),degree=a.features?.humidity?.degree;
  if(humidity&&(degree!==undefined?degree>=(includeSlight?1:2):a.needs.includes('dry')))out.push(h!==null?`${number(h)} % ${humidity.toLowerCase()}`:humidity.toLowerCase());
  if(air?.co2_status==='high')out.push(c!==null?`${number(c)} ppm de CO₂`:'CO₂ élevé');
  if(air?.pm25_status==='high'&&air?.pm25_treated!==true)out.push(pm!==null?`${number(pm)} particules élevées`:'particules élevées');
  if(air?.voc_status==='high')out.push(voc!==null?`${number(voc)} COV élevés`:'COV élevés');
  if((a.openings??[]).some(x=>x.flags.length>0&&x.open===true))out.push('fenêtre à refermer');
  if(cold&&settled)out.push(cold);
  return out;
}

/** A module's measures one at a time, every 5 s, all in the same place (the module keeps the tallest's height); a dot
 * per measure chooses one, a tap shows the next, hovering holds it; still when motion is reduced. */
export class HestiaModSlides extends LitElement {
  @property({attribute:false}) tabs:{label:string;value:string;bad:boolean}[]=[];
  @property({attribute:false}) items:TemplateResult[]=[];
  @state() private index=0;
  private startX:number|null=null;
  createRenderRoot(){return this;}
  protected render(){
    const n=this.items.length,i=this.index%Math.max(1,n);
    // A swipe (finger or mouse) goes to the next or the previous tab; nothing turns by itself.
    const down=(e:PointerEvent)=>{this.startX=e.clientX;};
    const up=(e:PointerEvent)=>{if(this.startX===null)return;const dx=e.clientX-this.startX;this.startX=null;if(Math.abs(dx)>30)this.index=(i+(dx<0?1:n-1))%n;};
    return html`<div class="nc-mtabs" role="tablist">${this.tabs.map((x,k)=>html`<button type="button" role="tab" aria-selected=${k===i} class=${'nc-mtab'+(k===i?' on':'')+(x.bad?' bad':'')} @click=${()=>{this.index=k;}}>
        <i aria-hidden="true"></i><span>${x.label}</span><b>${x.value}</b></button>`)}</div>
      <div class="nc-mslides" @pointerdown=${down} @pointerup=${up} @pointercancel=${()=>{this.startX=null;}}>
        <div class="nc-mslides-stack">${this.items.map((x,k)=>html`<div class=${'nc-mslide'+(k===i?' on':'')} role="tabpanel" aria-hidden=${k===i?'false':'true'}>${x}</div>`)}</div>
      </div>`;
  }
}
if(!customElements.get('hestia-mod-slides'))customElements.define('hestia-mod-slides',HestiaModSlides);

/** Short texts one at a time, every 3 s, in the same place; still when animations are off. */
export class HestiaNoteTicker extends LitElement {
  @property({attribute:false}) notes:string[]=[];
  @property({type:Boolean}) still=false;
  @state() private index=0;
  private timer?:ReturnType<typeof setInterval>;
  createRenderRoot(){return this;}
  connectedCallback(){super.connectedCallback();this.timer=setInterval(()=>{
    if(this.notes.length>1&&!this.still&&!matchMedia('(prefers-reduced-motion: reduce)').matches)this.index=(this.index+1)%this.notes.length;},3000);}
  disconnectedCallback(){super.disconnectedCallback();clearInterval(this.timer);this.timer=undefined;}
  protected render(){
    const list=this.notes,i=this.index%Math.max(1,list.length);
    return html`<span class="nc-notes" title=${list.map(tx).join(' · ')}>${list.map((n,k)=>html`<span class=${k===i?'on':''} aria-hidden=${k===i?'false':'true'}>${tx(n)}</span>`)}</span>`;
  }
}
if(!customElements.get('hestia-note-ticker'))customElements.define('hestia-note-ticker',HestiaNoteTicker);
