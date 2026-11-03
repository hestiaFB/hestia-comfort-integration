import {html,LitElement,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import charte from './ui/hestia-charte.css';
import roomStyle from './ui/room.css';
import sceneStyle from './ui/scene.css';
import traitStyle from './ui/trait.css';
import {watchOffscreen} from './ui/offscreen';
import {html as h2} from 'lit';
import {isView,number,numeric} from './view';
import {advice,needs,coldSettled,scale,fold,hero,tileSummary,pills,moreInfo,type CardState,type Advice,type Slide} from './views/room';
import {cleanHomeConfig,homeAction,type Connection,type HomeAssistant,type HomeConfig,type HomeFormat,type Unsubscribe,type View,type Level} from './types';
import {icon} from './ui/icons';
import {hassMatters} from './hass-change';
import {setLanguage,guessLanguage,t as tt,tx,fr} from './i18n';
/** A part of a line in bold, translated where the line is shown. */
const B=(text:string)=>h2`<b>${text}</b>`;
import {band,tabs,themes,roomsChart,curve,homeboardStyles,SHOWN_SECTIONS,FOLDED_SECTIONS,type Period,type Periods,type Section,type ChartFloor} from './views/homeboard';

interface FloorRef {floor_id:string|null;name:string;level:number|null}
interface Floor extends FloorRef {room_ids:string[];mean:number|null;measured:number;total:number;hottest:{title:string;temperature:number}|null}
interface Ventilation {kind:'stack'|'cross'|'combined';engaged:boolean;wind_favorable:boolean;openings:{title:string;name:string;floor:FloorRef|null}[]}
interface Home {
  floors?:Floor[];floor_contrast?:{warmer:string;cooler:string;difference:number;partial:boolean}|null;
  ventilation?:Ventilation|null; start_floor?:FloorRef|null;
  level:string; focus:string|null; partial:boolean; outdoor_temperature:number|null; spread:number|null;
  hottest:{title:string;temperature:number}|null; coolest:{title:string;temperature:number}|null;
  open_rooms:{title:string;open:string[]}[]; crossing:'strong'|'partial'|'none'|null; start_with:string|null;
  sun_entering:{title:string;openings:string[]}[];
}

/** The home card: a synthesis of every room. It never replaces the room cards' advice. */
export class HestiaComfortHomeCard extends LitElement {
  static styles=[unsafeCSS(style),unsafeCSS(charte),unsafeCSS(roomStyle),unsafeCSS(sceneStyle),unsafeCSS(traitStyle),homeboardStyles];
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  @state() private rooms:View[]=[];
  @state() private home?:Home;
  @state() private problem?:string;
  @state() private folds:Record<string,boolean>={};
  @state() private dialogOpen=false;
  /** The last day, week and month of the home (hestia_comfort/home_periods), read every quarter of an hour. */
  @state() private periods?:Periods;
  @state() private period?:Period;
  @state() private slide=0;
  private paused=false;
  private ticker?:ReturnType<typeof setInterval>;
  private reader?:ReturnType<typeof setInterval>;
  @property({type:Boolean}) preview=false;
  @property({type:Boolean}) editMode=false;
  private uid=`nch-${Math.random().toString(36).slice(2,8)}`;
  private connection?:Connection;
  private unsubscribe?:Unsubscribe;
  private retry?:ReturnType<typeof setTimeout>;
  private generation=0;
  setConfig(input:HomeConfig){this.config=cleanHomeConfig(input);}
  static getConfigElement(){return document.createElement('hestia-comfort-home-card-editor');}
  static getStubConfig():HomeConfig{return {type:'custom:hestia-comfort-home-card'};}
  getCardSize(){const f=this.config?.format;return f==='mini'?1:f==='alert'?2:f==='list'?1+this.rooms.length:f==='tile'?4:4+this.rooms.length;}
  connectedCallback(){super.connectedCallback();this.connect();this.unwatch=watchOffscreen(this);}
  disconnectedCallback(){super.disconnectedCallback();this.stop();this.unwatch?.();}
  /** Stops watching whether the card is in view (its animations pause out of view). */
  private unwatch?:()=>void;
  protected shouldUpdate(changed:PropertyValues){return hassMatters(changed,this.hass);}
  // The words follow Home Assistant's language, set before each drawing.
  protected willUpdate(){setLanguage(this.hass?.language);}
  protected updated(changed:PropertyValues){
    if(changed.has('hass'))this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);this.toggleAttribute('still',this.config?.animations===false);this.toggleAttribute('flat',this.config?.glass_effect===false);
    this.toggleAttribute('empty',this.config?.format==='alert'&&!!this.home&&!this.asking().length&&!this.preview&&!this.editMode);
    const dialog=this.renderRoot.querySelector<HTMLDialogElement>('dialog');if(this.dialogOpen&&dialog&&!dialog.open)dialog.showModal();
    if(this.config?.theme==='light'||this.config?.theme==='dark')this.setAttribute('forced',this.config.theme);else this.removeAttribute('forced');
  }
  private stop(){this.generation++;if(this.retry)clearTimeout(this.retry);this.retry=undefined;clearInterval(this.ticker);clearInterval(this.reader);this.ticker=this.reader=undefined;const remove=this.unsubscribe;this.unsubscribe=undefined;this.connection=undefined;if(remove)void Promise.resolve().then(()=>remove()).catch(()=>{});}
  private connect(){
    const connection=this.hass?.connection;if(!this.isConnected||!connection||!this.config||connection===this.connection)return;
    this.stop();this.connection=connection;const generation=this.generation;
    connection.subscribeMessage<{version:number;rooms?:unknown[];home?:Home;reload?:boolean}>(event=>{
      if(generation!==this.generation)return;
      if(event.reload){this.rooms=[];this.home=undefined;this.problem='reload';this.later();return;}
      if(event.version!==1||!event.home||!Array.isArray(event.rooms)){this.problem='version';return;}
      this.rooms=event.rooms.filter(isView);this.home=event.home;this.problem=undefined;
    },{type:'hestia_comfort/home_subscribe'}).then(remove=>{if(generation!==this.generation)void remove();else this.unsubscribe=remove;})
      .catch((e:{code?:string})=>{if(generation===this.generation){this.problem=e?.code??'connection';this.later();}});
    if((this.config.format??'full')==='full'){
      const read=()=>{this.hass?.callWS<Periods>({type:'hestia_comfort/home_periods'}).then(p=>{if(generation===this.generation&&p?.version===1)this.periods=p;},()=>{});};
      read();this.reader=setInterval(read,15*60000);
      this.ticker=setInterval(()=>{if(!this.paused&&this.config?.rotate!==false&&this.config?.animations!==false)this.slide++;},6000);
    }
  }
  private later(){if(this.retry)return;this.retry=setTimeout(()=>{this.retry=undefined;this.connection=undefined;this.connect();},4000);}
  private open(view:View){history.pushState(null,'','/hestia/confort/'+encodeURIComponent(view.entry_id));window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));}
  private state():CardState{
    const o=this.folds,c=this.config,start:Record<string,boolean>={tilesOpen:c?.rooms_open??false,detailsOpen:c?.details_open??false},get=(k:string)=>o[k]??start[k]??false;
    return {why:get('why'),tilesOpen:get('tilesOpen'),detailsOpen:get('detailsOpen'),uid:this.uid,toggle:k=>{const cur=this.folds;this.folds={...cur,[k]:!(cur[k]??start[k]??false)};}};
  }
  /** Short names for the scale: « Chambre AL » → AL, « Salle de bain » → SB, « Salon » → S; never twice the same. */
  private shorts(rooms:View[]):Map<string,string>{
    const out=new Map<string,string>(),used=new Set<string>();
    for(const r of rooms){const words=r.title.trim().split(/\s+/).filter(w=>!/^(de|du|des|la|le|les|d’|d')$/i.test(w));
      let s=words.length>1&&words[words.length-1].length<=3?words[words.length-1].toUpperCase():words.length>1?words.map(w=>w[0]).join('').toUpperCase():r.title.slice(0,1).toUpperCase();
      if(used.has(s))s=r.title.slice(0,2);used.add(s);out.set(r.entry_id,s);}
    return out;
  }
  /** Rooms sharing one air are one tile, under the volume's name, from the room that leads it. */
  private collapse(rooms:View[]):View[]{
    const hidden=new Set<string>(),out:View[]=[];
    for(const r of rooms){
      if(hidden.has(r.entry_id))continue;
      const group=this.rooms.filter(x=>x.entry_id===r.entry_id||(r.volume??[]).some(p=>p.entry_id===x.entry_id));
      const lead=group.find(x=>x.title===r.volume_name?.split(' · ')[0])??r;
      group.forEach(x=>hidden.add(x.entry_id));
      if(group.length>1)this.groups.set(lead.entry_id,group);
      out.push(group.length>1?{...lead,title:lead.volume_name??lead.title}:r);
    }
    return out;
  }
  /** Rooms sharing one air, by the room that leads their tile. */
  private groups=new Map<string,View[]>();
  /** What a tile says is out, for one room or for rooms sharing one air: like « À savoir », the humidity of the most
   * humid room first, once, and a cold the heating takes care of last. */
  private tileNeeds(r:View):string[]{
    const group=this.groups.get(r.entry_id);
    if(!group)return needs(r);
    const deg=(x:View)=>x.assessment.features?.humidity?.degree??0,humid=/ (légèrement |très )?(humide|sec)$|trop humide$/;
    const all=[...group].sort((x,y)=>deg(y)-deg(x)).flatMap(x=>needs(x)),cold=/^(un peu|trop) frais$/;
    const settled=group.every(x=>coldSettled(x.assessment));
    const one=all.filter((n,i)=>all.indexOf(n)===i).filter((n,i,list)=>!humid.test(n)||list.findIndex(m=>humid.test(m))===i);
    return settled?[...one.filter(n=>!cold.test(n)),...one.filter(n=>cold.test(n))]:one;
  }
  private roomTile(r:View){
    const t=numeric(r.observations.indoor_temperature),a=r.assessment,lvl=a.level as Level,unheated=a.features?.season?.heated===false;
    const note=tx(t===null?'mesure indisponible':['action','urgent'].includes(lvl)?advice(r).title.toLowerCase():unheated?'non chauffée':'dans votre plage');
    // Like the room card: what is out of range is always said; the orange frame only with a gesture to make.
    const out=['action','urgent'].includes(lvl),need=t===null?[]:this.tileNeeds(r);
    return h2`<button class=${'nc-tile'+(out?' out':need.length?' out soft':'')} data-level=${unheated&&!out?'neutral':lvl} @click=${(e:Event)=>{const id=r.observations.indoor_temperature?.source;if(id)moreInfo(e,id);else this.open(r);}} title=${tt('Détails : {label}',{label:r.title})}><div class="nc-tile-h"><span class="nw-label">${r.title}</span></div><b>${number(t)}<small>°C</small></b><em>${need.length?h2`<hestia-note-ticker .notes=${need} .still=${this.config?.animations===false||this.config?.rotate===false}></hestia-note-ticker>`:note}</em></button>`;
  }
  private details(h:Home){
    const row=(label:string,x:string)=>h2`<li><b>${tx(label)}</b><span> · ${tx(x)}</span></li>`,out=[];
    if(h.start_with)out.push(row('Commencez par',h.start_with+(h.start_floor?` (${h.start_floor.name})`:'')));
    if(h.floor_contrast){const c=h.floor_contrast;out.push(row(c.warmer,`${number(c.difference)} °C de plus que ${c.cooler}`));}
    if(h.hottest&&h.coolest)out.push(row('Écart entre pièces',`${number(h.spread)} °C (${h.hottest.title} la plus chaude, ${h.coolest.title} la plus fraîche)`));
    if(h.ventilation){const v=h.ventilation;out.push(row(v.kind==='cross'?'Air traversant':'Effet cheminée',`${v.openings.map(o=>`${o.title} — ${o.name}`).join(' + ')}${v.engaged?' · déjà ouverts':''}`));}
    if(h.open_rooms.length)out.push(row('Ouvert',h.open_rooms.map(r=>`${r.title} (${r.open.length})`).join(', ')));
    for(const s of h.sun_entering)out.push(row('Soleil qui entre',s.title));
    return out;
  }
  /** One slide per room that asks for something, the most urgent first, then what the home can do as a whole. */
  /** Rooms that ask for something, the most urgent first. */
  private asking(levels=['urgent','action']):View[]{
    const rank:Record<string,number>={urgent:0,action:1,benefit:2};
    // A room that only follows its shared air comes after the one it follows.
    const follows=(r:View)=>r.assessment.reason==='shared_volume'?1:0;
    // A room airing as advised asks nothing more: its banner is blue.
    return this.rooms.filter(r=>levels.includes(advice(r).level??r.assessment.level)).sort((a,b)=>rank[a.assessment.level]-rank[b.assessment.level]||follows(a)-follows(b));
  }
  private slides(h:Home,calmAdvice:Advice):Slide[]{
    const blocks=this.config?.banner_blocks??['rooms','house'];
    const asking=blocks.includes('rooms')?this.asking(['urgent','action','benefit']):[];
    // Rooms open onto each other share one air: one slide for them, named after all of them.
    const out:Slide[]=[],shared=new Map<string,{slide:Slide;action:string}>();
    for(const r of asking){
      const key=r.volume?.length?[r.entry_id,...r.volume.map(p=>p.entry_id)].sort().join('|'):null,a=r.assessment;
      const known=key?shared.get(key):undefined;
      if(known&&(a.reason==='shared_volume'||a.action===known.action)){known.slide.pill+=' · '+r.title;continue;}
      const ad=advice(r),cool=a.needs.includes('cool')&&h.start_with===r.title;
      const slide:Slide={...ad,level:a.level as Level,pill:r.title,line:cool&&h.start_floor?h2`${ad.line} · ${B(h.start_floor.name)} d’abord`:ad.line};
      out.push(slide);
      if(key&&!known)shared.set(key,{slide,action:a.action});
    }
    if(blocks.includes('house')&&h.ventilation&&!h.ventilation.engaged)out.push({level:'benefit',pill:'Logement',title:h.ventilation.kind==='cross'?'Faites traverser l’air':'Ouvrez en bas et en haut',
      line:h2`${h.ventilation.openings.map(o=>o.name).join(' + ')}`,disk:'open'});
    // A sensor that stops answering is a matter for the Hestia panel, not an advice for the home.
    const calm=(h.level==='neutral'?'calm':h.level) as Level;
    return out.length?out:[{level:calm,pill:pills[calm],...calmAdvice}];
  }
  protected render(){
    if(!this.config)return nothing;
    const h=this.home;
    if(!h){const text=this.problem==='not_configured'?[fr('Aucune pièce'),fr('Ouvrez Hestia Confort dans la barre latérale pour configurer vos pièces.')]:this.problem?[fr('Connexion indisponible'),fr('La carte réessaie automatiquement.')]:[fr('Chargement du logement'),fr('En attente des pièces.')];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${tt(text[0])}</h2><p>${tt(text[1])}</p></ha-card>`;}
    // Every room without its indoor temperature: Home Assistant is starting or no longer passes measures on. Not advice.
    const muted=this.rooms.filter(r=>r.assessment.missing.includes('indoor_temperature')&&!!r.observations.indoor_temperature).length;
    if(this.rooms.length&&muted===this.rooms.length){const starting=this.rooms.some(r=>r.starting);
      return this.renderCard(h,starting?{title:'Mesures en chargement',line:h2`Home Assistant ${B('vient de démarrer')}`,disk:'clock',pill:'Démarrage',level:'neutral'}
        :{title:'Mesures absentes',line:h2`Aucune pièce ne transmet sa température`,disk:'mute',pill:'Capteurs muets',level:'neutral'});}
    return this.renderCard(h,undefined);
  }
  private act=(e:Event)=>{
    const c=this.config!,action=homeAction(c);
    if(action==='none')return;
    if(action==='page'&&c.hold_path){history.pushState(null,'',c.hold_path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));return;}
    this.dialogOpen=true;void e;
  };
  private pressTimer?:ReturnType<typeof setTimeout>;
  private held=false;
  private press=(e:PointerEvent)=>{if(e.button!==0)return;this.held=false;clearTimeout(this.pressTimer);this.pressTimer=setTimeout(()=>{this.held=true;this.act(e);},500);};
  private release=()=>{clearTimeout(this.pressTimer);};
  private swallow={handleEvent:(e:Event)=>{if(this.held){e.stopPropagation();e.preventDefault();this.held=false;}},capture:true};
  private closeFull(){this.renderRoot?.querySelector<HTMLDialogElement>('dialog')?.close();this.dialogOpen=false;}
  private renderCard(h:Home,muteAdvice?:Advice&{pill:string;level:Level}){
    if(!this.config)return nothing;
    const format=this.config.format??'full';
    // The full card answers a long press only when a page is set (a window would show itself again).
    if(format==='full'&&homeAction(this.config)!=='page')return this.homeCard(h,muteAdvice,'full');
    const card=this.homeCard(h,muteAdvice,format);
    if(card===null)return this.preview||this.editMode?html`<ha-card class="nc-c nc-alert-note" data-level="calm"><p>${tt('Alerte · {room} : rien à signaler. La carte n’apparaît que lorsqu’une pièce demande un geste.',{room:this.config.title||tt('Mon logement')})}</p></ha-card>`:nothing;
    const tap=format==='mini'||format==='alert';
    return html`<div class="nc-hold" role=${tap?'button':'group'} tabindex=${tap?0:-1} aria-label=${tap?tt('Ouvrir la carte complète'):this.config.title||tt('Mon logement')}
      @click=${tap?this.act:this.swallow} @pointerdown=${tap?undefined:this.press} @pointerup=${this.release} @pointerleave=${this.release} @pointercancel=${this.release}
      @keydown=${(e:KeyboardEvent)=>{if(tap&&(e.key==='Enter'||e.key===' ')){e.preventDefault();this.act(e);}}}>${card}</div>
      <dialog aria-label=${tt('Logement complet')} @cancel=${()=>{this.dialogOpen=false;}} @close=${()=>{this.dialogOpen=false;}}>
        <div class="dialog-top"><span>${this.config.title||tt('Mon logement')}</span><button class="icon-button" aria-label=${tt('Fermer')} @click=${()=>this.closeFull()}>${icon('close')}</button></div>
        <div>${this.dialogOpen?this.homeCard(h,muteAdvice,'full'):nothing}</div></dialog>`;
  }
  /** The home card in each format; null when the alert format has nothing to say. */
  private homeCard(h:Home,muteAdvice:(Advice&{pill:string;level:Level})|undefined,format:HomeFormat){
    if(!this.config)return nothing;
    const focus=this.rooms.find(r=>r.entry_id===h.focus);
    // No gesture, but rooms out of range: never a tick and « Tout va bien »; the rooms section says how many.
    const watched=this.rooms.filter(r=>needs(r,false).length>0);
    const calmAdvice={title:'Rien à faire',line:h2`Aucune pièce ${B('ne demande de geste')}`,disk:h.open_rooms.length?'open':watched.length?'info':'check',cap:h.open_rooms.length?undefined:'Tout est fermé',
      // Out of range with nothing to do: « Au mieux », like each room card; « À savoir » of the rooms says what.
      ...(watched.length?{pill:'Au mieux',level:'calm' as Level}:{})};
    const homeSlides=muteAdvice?[{...muteAdvice}]:this.slides(h,calmAdvice);
    const shorts=this.shorts(this.rooms),season=(focus??this.rooms[0])?.assessment.features?.season;
    const rooms=this.rooms.flatMap(r=>{const t=numeric(r.observations.indoor_temperature);return t===null?[]:[{name:r.title,entity:r.observations.indoor_temperature?.source??undefined,short:shorts.get(r.entry_id)!,value:t,level:(r.assessment.features?.season?.heated===false&&!['action','urgent'].includes(r.assessment.level)?'neutral':r.assessment.level) as Level}];});
    const st=this.state(),floors=h.floors?.length?h.floors:[{floor_id:null,name:tt('Mon logement'),level:null,room_ids:this.rooms.map(r=>r.entry_id),mean:null,measured:0,total:0,hottest:null}];
    // « À surveiller » counts what the room cards call so: a gesture to make, or a measure out of range.
    const all=this.rooms.map(r=>this.roomTile(r)),outside=this.rooms.filter(r=>['action','urgent'].includes(r.assessment.level)||needs(r,false).length>0);
    const body=h2`<div class="nc-tiles">${floors.map(f=>h2`${floors.length>1?h2`<div class="nc-floor"><span class="nw-label">${f.name}</span><b>${number(f.mean)} °C</b></div>`:nothing}${this.collapse(this.rooms.filter(r=>f.room_ids.includes(r.entry_id))).map(r=>this.roomTile(r))}`)}</div>`;
    const c=this.config,name=c.title||tt('Mon logement'),still=c.animations===false||c.rotate===false;
    const top=homeSlides[0]?.level??h.level as Level;
    const temps=this.rooms.map(r=>numeric(r.observations.indoor_temperature)).filter((t):t is number=>t!==null);
    const mean=temps.length?temps.reduce((x,y)=>x+y,0)/temps.length:null;
    if(format==='alert'&&!this.asking().length)return null;
    if(format==='mini'){const n=this.asking().length,first=homeSlides[0];
      return html`<ha-card class="nc-c nc-line-card" data-level=${muteAdvice?'neutral':n?top:'calm'}><div class="nc-disk">${icon(muteAdvice?first.disk:n?first.disk:'home')}</div>
        <div class="nc-line-text"><span>${name}</span><b>${muteAdvice?tx(first.title):n?(n>1?tt('{n} pièces demandent un geste',{n}):tt('{n} pièce demande un geste',{n})):tt('Rien à faire')}</b></div>
        ${mean!==null?html`<span class="nc-line-value">${number(Math.round(mean*10)/10)}<small> °C</small></span>`:nothing}</ha-card>`;}
    if(format==='list'){
      const order=c.list_order==='floor'?floors.flatMap(f=>this.rooms.filter(r=>f.room_ids.includes(r.entry_id))):[...this.asking(['urgent','action','benefit']),...this.rooms.filter(r=>!['urgent','action','benefit'].includes(r.assessment.level))];
      return html`<ha-card class="nc-c nc-list-card" data-level="neutral"><div class="nc-mhead"><h2>${name}</h2>${mean!==null?html`<span class="nw-sum">${tt('{value} en moyenne',{value:number(Math.round(mean*10)/10)+' °C'})}</span>`:nothing}</div>
        <div class="nc-rows">${order.map(r=>{const t=numeric(r.observations.indoor_temperature),a=advice(r),id=r.observations.indoor_temperature?.source;
          return html`<button type="button" class="nc-row" data-level=${r.assessment.level} title=${tt('Détails : {label}',{label:r.title})} @click=${(e:Event)=>{if(id)moreInfo(e,id);}}><i></i><b>${r.title}</b><span>${tx(a.title)}</span><em>${number(t)}<small> °C</small></em></button>`;})}</div></ha-card>`;
    }
    if(format==='full')return this.board(h,homeSlides,body,all,outside,floors,season);
    const small=format==='tile'||format==='alert';
    return html`<ha-card class="nc-c" data-level=${top} ?data-starting=${this.rooms.some(r=>r.starting)}>
      ${hero({name,level:top,slides:homeSlides,small,compact:c.show_scale===false||format==='alert',still,scaleLabel:tt('Les pièces'),scale:scale({band:season?[season.minimum,season.maximum]:null,out:h.outdoor_temperature,rooms,outEntity:this.rooms[0]?.observations.outdoor_temperature?.source??undefined}),st,why:h2`<p><b>${tt('Pièce suivie de près')}</b> · ${focus?focus.title:tt('aucune')}</p>`})}
      ${format==='alert'?nothing:html`<div class="nc-body" ?hidden=${c.show_rooms===false&&(c.show_details===false||format==='tile')}>
        ${c.show_rooms===false?nothing:fold({label:tt('Pièces'),summary:tileSummary(all.length,outside.length,'pièce'),open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:this.uid+'-rooms',body,keep:outside.map(r=>this.roomTile(r))})}
        ${c.show_details===false||format==='tile'?nothing:fold({label:tt('Détails'),summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:this.uid+'-details',body:h2`<ul class="nc-list">${this.details(h)}</ul>`})}
      </div>`}
    </ha-card>`;
  }
  /** The full card: the rooms' advice in turn, then the last day, week or month like a light review. */
  private board(h:Home,slides:Slide[],tiles:ReturnType<typeof h2>,all:unknown[],outside:View[],floors:{name:string;mean:number|null;room_ids:string[]}[],
      season:{minimum:number;maximum:number}|undefined){
    const c=this.config!,st=this.state(),name=c.title||tt('Mon logement'),period=this.period??c.period??'day',data=this.periods?.[period];
    const legacy:Record<string,boolean|undefined>={rooms_chart:c.show_scale,rooms:c.show_rooms,details:c.show_details};
    // The old switches still hide a section until sections are chosen in the editor.
    const shown=c.sections??SHOWN_SECTIONS.filter(s=>legacy[s]!==false),folded=c.folded??FOLDED_SECTIONS;
    // The comfort range: the season's when the engine knows it, else the rooms' own settings.
    const own=this.rooms.find(r=>r.comfort_minimum!=null&&r.comfort_maximum!=null);
    const bandRange:[number,number]|null=season?[season.minimum,season.maximum]:own?[own.comfort_minimum!,own.comfort_maximum!]:null;
    const chartFloors:ChartFloor[]=floors.map(f=>({name:f.name,mean:f.mean,rooms:this.rooms.filter(r=>f.room_ids.includes(r.entry_id)).map(r=>{
      const lvl=(advice(r).level??r.assessment.level) as Level;
      const own=r.assessment.features?.season,unheated=own?.heated===false;
      const range:[number,number]|null=unheated?null:own?[own.minimum,own.maximum]:r.comfort_minimum!=null&&r.comfort_maximum!=null?[r.comfort_minimum,r.comfort_maximum]:null;
      return {entry_id:r.entry_id,title:r.title,now:numeric(r.observations.indoor_temperature),band:range,level:unheated&&!['action','urgent'].includes(lvl)?'neutral':lvl};})}));
    const render=(s:Section,inside:boolean)=>{switch(s){
      case 'themes':return themes(data,period);
      case 'rooms_chart':return roomsChart({floors:chartFloors,data,period,outNow:h.outdoor_temperature});
      case 'curve':return curve(data,period,bandRange);
      case 'rooms':return inside?h2`<div><span class="nw-label">${tt('Pièces')}</span>${tiles}</div>`
        :fold({label:tt('Pièces'),summary:tileSummary(all.length,outside.length,'pièce'),open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:this.uid+'-rooms',body:tiles,keep:outside.map(r=>this.roomTile(r))});
      case 'details':{const list=h2`<ul class="nc-list">${this.details(h)}</ul>`;
        return inside?h2`<div><span class="nw-label">${tt('Détails')}</span>${list}</div>`:fold({label:tt('Détails'),summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:this.uid+'-details',body:list});}
    }};
    const open=shown.filter(s=>!folded.includes(s)),more=shown.filter(s=>folded.includes(s));
    const pick=(i:number)=>{this.paused=true;this.slide=i;};
    return html`<ha-card class="nc-c" data-level=${slides[0]?.level??h.level} ?data-starting=${this.rooms.some(r=>r.starting)}>
      ${band({slides,index:this.slide,pick,title:name})}
      <div class="nh-body">
        <div class="nh-head"><h2>${name}</h2>${tabs(period,p=>{this.period=p;})}</div>
        ${open.map(s=>render(s,false))}
        ${more.length?fold({label:tt('Plus de détails'),summary:more.length>1?tt('{n} sections',{n:more.length}):tt('{n} section',{n:more.length}),open:this.folds.moreOpen??c.more_open??false,onToggle:()=>{this.folds={...this.folds,moreOpen:!(this.folds.moreOpen??c.more_open??false)};},id:this.uid+'-more',
          body:h2`<div class="nh-more">${more.map(s=>render(s,true))}</div>`}):nothing}
      </div>
    </ha-card>`;
  }
}
if(!customElements.get('hestia-comfort-home-card'))customElements.define('hestia-comfort-home-card',HestiaComfortHomeCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
guessLanguage();
if(!window.customCards.some(c=>c.type==='hestia-comfort-home-card'))window.customCards.push({type:'hestia-comfort-home-card',name:tt('Hestia Confort · logement'),description:tt('La synthèse de toutes vos pièces : celle qui demande le plus d’attention, la plus chaude, les ouvrants ouverts.')});
