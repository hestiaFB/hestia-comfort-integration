import {LitElement,html,css,nothing} from 'lit';
import {property,state} from 'lit/decorators.js';
import {SECTIONS,SECTION_LABELS,SHOWN_SECTIONS,FOLDED_SECTIONS} from './views/homeboard';
import {t,th,fr,setLanguage} from './i18n';
import {cleanConfig,cleanHomeConfig,KINDS,kindOf,nowBlocks,type Kind,type Format,MODULES,SCALE_MARKS,CHIPS,TILE_BLOCKS,NOW_BLOCKS,HORIZON_SUBJECTS,INSIGHT_GROUPS,DETAIL_ROWS,homeAction,type Config,type HomeConfig,type HomeAssistant,type Entry} from './types';

/* The editors are built like Hestia Weather's: the room (or title) and the format on top, then folding groups that
   change with the format. The theme follows Home Assistant: it is no longer offered. */
type Item={name:string;title?:string};
const toggle=(name:string)=>({name,selector:{boolean:{}}});
const group=(title:string,icon:string,schema:unknown[],expanded=false)=>({type:'expandable',name:'',title:t(title),icon,flatten:true,expanded,schema});
const choices=(name:string,options:[string,string][],reorder=true)=>({name,selector:{select:{multiple:true,reorder,mode:'list',options:options.map(([value,label])=>({value,label:t(label)}))}}});
const dropdown=(name:string,options:[string,string][])=>({name,required:true,selector:{select:{mode:'dropdown',options:options.map(([value,label])=>({value,label:t(label)}))}}});
const look=(expanded=true)=>group(fr('Visuel et performance'),'mdi:palette-outline',[toggle('animations'),toggle('glass_effect')],expanded);
/** On a full card, the full card in a window would show itself again: only a page, or nothing. */
const hold=(action:string,full=false)=>group(fr('Fonctionnalités'),'mdi:tune-variant',[
  dropdown('hold_action',full?[['none',fr('Rien')],['page',fr('Ouvrir une page')]]:[['popup',fr('Ouvrir la carte complète en fenêtre')],['page',fr('Ouvrir une page')],['none',fr('Rien')]]),
  ...(action==='page'?[{name:'hold_path',selector:{text:{}}}]:[])]);
const chipOptions:[string,string][]=[['temperature',fr('Température')],['humidity',fr('Humidité')],['co2','CO₂']];
const detailOptions:[string,string][]=[['range',fr('Plage de confort')],['slot',fr('Créneau conseillé')],['windows',fr('Fenêtres')],['shutters',fr('Volets')],['people',fr('Présence, personnes, alarme')],
  ['drying',fr('Séchage et buée')],['trend',fr('Tendance')],['sensors',fr('Capteurs et sources')]];
/* The room card's settings (6 November), laid out as Hestia Weather's: the room and the format on top, then « Visuel et
   performance », the card's own sections in their order (Bandeau intelligent, En ce moment, À venir, Détails), and
   « Fonctionnalités » (the tap and the long press). Only what changes the card is offered; the advice itself is never switched off. */
const nowList=choices('now_blocks',[['warmth',fr('Ressenti : la chaleur')],['humidity',fr('Ressenti : l’humidité')],['air',fr('Air : CO₂, particules, COV')],
  ['devices',fr('Appareils : fenêtres, volet, chauffage, VMC, purificateur')]],false);
/** One choice per air: rooms open onto each other are offered once, as « Salon · Cuisine ». A card already set on one of
    them keeps its room as the value, so that nothing moves. */
export function roomChoices(entries:Entry[],current?:string):{value:string;label:string}[] {
  const out:{value:string;label:string}[]=[],done=new Set<string>();
  for(const e of entries){
    if(done.has(e.entry_id))continue;
    const group=[e.entry_id,...(e.volume??[])];group.forEach(id=>done.add(id));
    // The best equipped room leads, as in the volume's name (« Salon · Cuisine »).
    const lead=entries.find(x=>group.includes(x.entry_id)&&x.title===e.volume_name?.split(' · ')[0])?.entry_id??e.entry_id;
    const value=current&&group.includes(current)?current:lead;
    out.push({value,label:e.volume?.length&&e.volume_name?e.volume_name:e.title});
  }
  return out.sort((a,b)=>a.label.localeCompare(b.label));
}
const labels:Record<string,string>={entry_id:fr('Pièce'),piece_style:fr('Version'),title:fr('Titre facultatif'),format:fr('Format'),animations:fr('Animations'),glass_effect:fr('Effet verre dépoli'),
  rotate:fr('Faire défiler les conseils'),banner_blocks:fr('Contenu du bandeau'),scale_marks:fr('Repères de l’échelle'),modules:fr('Cases'),measures_open:fr('Mesures dépliées au départ'),
  show_details:fr('Afficher la section'),details_open:fr('Dépliés au départ'),show_measures:fr('Afficher la section'),show_insights:fr('Afficher la section'),
  show_horizon:fr('Afficher la section'),horizon_mode:fr('Quand l’afficher'),horizon_subjects:fr('Sujets'),insight_groups:fr('Rubriques'),insight_max:fr('Lignes au plus'),detail_rows:fr('Lignes'),tile_chips:fr('Pastilles de la tuile repliée'),tile_blocks:fr('Contenu de la tuile dépliée'),
  mini_values:fr('Valeurs de la ligne'),hold_action:fr('Appui long'),hold_path:fr('Page à ouvrir'),show_scale:fr('Échelle dans la case Température'),show_rooms:fr('Section Pièces'),sections:fr('Sections affichées'),folded:fr('Dans « Plus de détails »'),more_open:fr('« Plus de détails » déplié au départ'),period:fr('Période au départ'),hero_temperature:fr('Grande température'),rooms_open:fr('Pièces dépliées au départ'),
  list_order:fr('Ordre des pièces'),now_blocks:fr('Ce qui est affiché'),tap_action:fr('Appui court')};
const helpers:Record<string,string>={
  animations:fr('Coupées, la lumière et l’anneau restent fixes et les conseils ne défilent plus seuls.'),
  glass_effect:fr('Le flou demande beaucoup de ressources : à couper sur un appareil lent. Coupé, le verre devient plus opaque.'),
  rotate:fr('Toutes les 4,5 s ; décoché, ils changent d’un appui.'),
  title:fr('En tête de la carte ; vide, le nom de la pièce.'),
  show_horizon:fr('Ce qui va changer, heure par heure : un geste plus tard, le chauffage, la pluie, la pièce qui sort de votre plage. Rien à dire, rien d’affiché.'),
  horizon_mode:fr('« Seulement quand il aide » : la carte change de taille en douceur. « Toujours » : sans geste à montrer, la température prévue sans rien faire.'),
  horizon_subjects:fr('Ceux à prévoir dans les prochaines 24 h.'),
  insight_groups:fr('Pour le geste : à essayer, cette nuit, mis de côté. À surveiller : une mesure qui semble fausse. Bon à savoir : le reste.'),
  insight_max:fr('Dans l’ordre des rubriques ; 8 les montre toutes.'),
  show_scale:fr('Trop frais, votre plage, trop chaud, sous le ressenti.'),
  detail_rows:fr('Pour comprendre et vérifier. Tout décocher vide la section.'),
  banner_blocks:fr('Le conseil du moment reste toujours. Cochez ce qui défile après lui, dans l’ordre.'),
  scale_marks:fr('Tout décocher retire l’échelle.'),modules:fr('La température reste toujours ; tout décocher ne garde qu’elle.'),
  measures_open:fr('Repliées, les mesures à surveiller restent visibles.'),
  tile_chips:fr('Sous le conseil ; une mesure à surveiller passe en ambre. La température est déjà à droite du bandeau.'),tile_blocks:fr('Ce qui s’ouvre d’un appui, sous le bandeau.'),
  mini_values:fr('À droite du conseil.'),hold_action:fr('La carte complète par-dessus la page, une page de votre tableau de bord, ou rien.'),
  hold_path:fr('Le chemin de la page, par exemple /confort ou /lovelace/confort.'),rooms_open:fr('Repliées, les pièces qui demandent un geste restent visibles.'),
  folded:fr('Les sections cochées ici passent dans la partie dépliable, sous les autres.'),
  hero_temperature:fr('En haut à droite : la température dehors, ou la moyenne de toutes vos pièces avec la plus fraîche et la plus chaude.'),
  now_blocks:fr('Tout décocher retire la section.'),tap_action:fr('Sur la tuile : la déplier, la carte complète par-dessus la page, une page, ou rien.')};
/** Each format: its icon, its name and what it shows. */
const FORMAT_INFO:Record<Format,[string,string,string]>={
  full:['mdi:page-layout-body',fr('Complète'),fr('toute la pièce, ouverte : bandeau, à savoir, maintenant, à venir, détails')],
  intermediate:['mdi:dock-bottom',fr('Intermédiaire'),fr('la tuile, dépliée au départ')],
  tile:['mdi:dock-window',fr('Tuile dépliable'),fr('le conseil et quelques valeurs ; un appui la déplie')],
  feel:['mdi:home-thermometer-outline',fr('Ressenti'),fr('chaleur et humidité, comme la complète')],
  temperature:['mdi:thermometer',fr('Température'),fr('le ressenti : chaleur, tendance et plage')],
  humidity:['mdi:water-percent',fr('Humidité'),fr('le mot, la tendance et la plage')],
  air:['mdi:weather-windy',fr('Air'),fr('CO₂, particules, COV en anneaux')],
  openings:['mdi:window-open-variant',fr('Ouvertures'),fr('fenêtres, soleil, volets')],
  heating:['mdi:fire',fr('Chauffage'),fr('état et mode du thermostat')],
  devices:['mdi:devices',fr('Appareils'),fr('fenêtres, volet, chauffage, VMC, purificateur : une ligne')],
  measures:['mdi:view-grid-outline',fr('Toutes les mesures'),fr('le ressenti, l’air et les appareils, comme la complète')],
  horizon:['mdi:chart-line',fr('Prochaines heures'),fr('ce qui va changer, heure par heure')],
  mini:['mdi:minus',fr('Mini'),fr('une ligne : conseil et température')],
  alert:['mdi:alert-outline',fr('Alerte'),fr('n’apparaît que s’il y a un geste ou une alerte')]};
const KIND_NOTE:Record<Kind,string>={large:fr('Un appui déplie la tuile ; un appui long ouvre la complète par-dessus la page.'),
  piece:fr('Chaque carte reprend un module de la complète, tel quel. Une pièce au même air montre ses deux pièces dans le module.'),
  small:fr('Une ligne discrète, ou une alerte qui ne se montre que si besoin.')};
const styles=css`.note{color:var(--secondary-text-color);font-size:var(--nw-fs-small,12px);line-height:1.6;margin:0 0 16px}.note.warn{color:var(--primary-text-color)}a{color:var(--primary-color)}
  .formats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:4px 0 6px}
  .formats button{all:unset;box-sizing:border-box;display:flex;flex-direction:column;gap:4px;padding:10px 12px;border:1px solid var(--divider-color);border-radius:12px;cursor:pointer;color:var(--primary-text-color);font-size:var(--nw-fs-small,12px);line-height:1.45}
  .formats button:hover{border-color:var(--secondary-text-color)}
  .formats button:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
  .formats button.on{border:2px solid var(--primary-color);padding:9px 11px}
  .formats ha-icon{--mdc-icon-size:20px;color:var(--secondary-text-color)}.formats button.on ha-icon{color:var(--primary-color)}
  .formats b{font-size:var(--nw-fs-text,14px);font-weight:500}.formats span{color:var(--secondary-text-color)}
  .note.hint{font-size:var(--nw-fs-small,12px);margin:0 0 16px}`;
/** A link inside Home Assistant opens there, without reloading the page. */
const follow=(e:MouseEvent)=>{e.preventDefault();history.pushState(null,'',(e.currentTarget as HTMLAnchorElement).getAttribute('href')??'/hestia/confort');
  window.dispatchEvent(new CustomEvent('location-changed',{bubbles:true,composed:true}));};
/** Mini and alert act on a simple tap; the other formats on a long press. */
const labelFor=(format:string|undefined)=>(item:Item)=>{const tap=item.name==='hold_action'&&['mini','alert'].includes(format??'');return t(item.title??(tap?fr('Appui'):labels[item.name]??item.name));};
const helperFor=(item:Item)=>helpers[item.name]?t(helpers[item.name]):'';
/** Drop empty values, a page path that no longer applies, and defaults the card did not hold: the YAML stays short. */
function tidy(next:Record<string,unknown>,before:Record<string,unknown>,defaults:Record<string,unknown>){
  if(next.hold_action!=='page')delete next.hold_path;
  for(const k of Object.keys(next)){
    if(next[k]===''||next[k]===undefined){delete next[k];continue;}
    if(!(k in before)&&k in defaults&&JSON.stringify(next[k])===JSON.stringify(defaults[k]))delete next[k];
  }
  return next;
}

/** Is the temperature scale shown: the switch, else the list of marks a card kept from before. */
export const scaleShown=(c:Config)=>c.show_scale??!(c.scale_marks?.length===0||(c.scale_marks===undefined&&c.format==='measures'));
/** The card after one change in the form. Home Assistant's form sends back every field it holds, the hidden ones too:
    only what really changed may replace a setting (the scale switch was undone by the list of marks it carries). */
export function nextConfig(config:Config,v:Record<string,unknown>):Record<string,unknown>{
  const next:Record<string,unknown>={...config,...v};
  // The scale needs the temperature module.
  if(Array.isArray(v.modules))next.modules=[...(v.modules as string[]),...((config.modules??MODULES).includes('temperature')?['temperature']:[])];
  if(typeof v.show_scale==='boolean'&&v.show_scale!==scaleShown(config)){next.show_scale=v.show_scale;delete next.scale_marks;}
  else{next.scale_marks=config.scale_marks;next.show_scale=config.show_scale;}
  if('modules' in v&&!('show_measures' in v))delete next.show_measures;
  return next;
}
export class ComfortEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  /** The integration's rooms; null when it does not answer. */
  @state() private entries?:Entry[]|null;
  private asked=false;
  static styles=styles;
  protected willUpdate(){setLanguage(this.hass?.language);}
  setConfig(config:Config){const next=cleanConfig(config);if(this.config&&JSON.stringify(next)===JSON.stringify(this.config))return;this.config=next;}
  protected shouldUpdate(changed:Map<PropertyKey,unknown>){
    // Home Assistant pushes every state change to editors: nothing here depends on them.
    if(changed.has('hass')&&!this.asked&&this.hass){this.asked=true;
      this.hass.callWS<Entry[]>({type:'hestia_comfort/entries'}).then(e=>{this.entries=e;},()=>{this.entries=null;});}
    return !(changed.size===1&&changed.has('hass'));
  }
  private schema(){
    const c=this.config!,f=c.format??'tile',action=c.hold_action??(c.hold_path?'page':'popup');
    const rooms=this.entries&&this.entries.length>1?[{name:'entry_id',selector:{select:{mode:'dropdown',options:roomChoices(this.entries,c.entry_id)}}}]:[];
    // As Hestia Weather's editor: the kind of card first, then the formats of that kind only.
    const kinds={name:'kind',title:t('Type de carte'),required:true,selector:{select:{mode:'list',options:[
      {value:'large',label:t('Grandes cartes : la complète et la tuile dépliable')},
      {value:'piece',label:t('À la carte : ressenti, température, humidité, air, appareils, ouvertures, chauffage, prochaines heures')},
      {value:'small',label:t('Petites cartes : une ligne ou une alerte')}]}}};
    // The big cards name themselves in their banner's section; the others right here.
    const head=[...rooms,...(kindOf(f)==='large'?[]:[{name:'title',selector:{text:{}}}]),kinds];
    const pieceStyle={name:'piece_style',selector:{select:{mode:'list',options:[{value:'detailed',label:t('Détaillée : le module, avec ses chiffres')},{value:'compact',label:t('Compacte : la mesure, sa tendance et sa courbe')}]}}};
    const foldable=f==='tile'||f==='intermediate',small=f==='mini'||f==='alert',tap=c.tap_action??'toggle';
    const presses=[['popup',fr('Ouvrir la carte complète en fenêtre')],['page',fr('Ouvrir une page')],['none',fr('Rien')]] as [string,string][];
    const features=group(fr('Fonctionnalités'),'mdi:tune-variant',[
      ...(foldable?[dropdown('tap_action',[['toggle',fr('Déplier ou replier la tuile')],...presses])]:[]),
      dropdown('hold_action',f==='full'?[['none',fr('Rien')],['page',fr('Ouvrir une page')]]:presses),
      ...(action==='page'||(foldable&&tap==='page')?[{name:'hold_path',selector:{text:{}}}]:[])],small);
    const visual=group(fr('Visuel et performance'),'mdi:palette-outline',[toggle('animations'),toggle('glass_effect')],true);
    const content=(...items:unknown[])=>group(fr('Contenu'),'mdi:view-list-outline',items,true);
    if(f==='mini')return [...head,visual,content(choices('mini_values',chipOptions)),features];
    if(f==='alert')return [...head,visual,features];
    if(f==='measures')return [...head,visual,content(nowList),features];
    if(f==='openings'||f==='heating')return [...head,visual,content(pieceStyle),features];
    if(kindOf(f)==='piece')return [...head,visual,features];
    const banner=group(fr('Bandeau intelligent'),'mdi:view-day-outline',[{name:'title',selector:{text:{}}},
      choices('banner_blocks',[['remedies',fr('Ce qui agit déjà (purificateur, VMC)')],['later',fr('Un meilleur moment plus tard')]]),toggle('rotate')],true);
    const now=group(fr('En ce moment'),'mdi:clock-outline',[nowList]);
    const details=(withSwitch:boolean)=>group(fr('Détails'),'mdi:text-box-search-outline',[...(withSwitch?[toggle('show_details')]:[]),choices('detail_rows',detailOptions),toggle('details_open')]);
    // The tile: folded, the banner and its chips; a tap unfolds the sections ticked here.
    if(foldable)return [...head,visual,banner,group(fr('Tuile'),'mdi:view-day-outline',[choices('tile_chips',chipOptions.filter(([k])=>k!=='temperature'),false),
      choices('tile_blocks',[['measures',fr('En ce moment')],['horizon',fr('À venir')],['details',fr('Détails')]],false)],true),now,details(false),features];
    return [...head,visual,banner,now,group(fr('À venir'),'mdi:calendar-clock',[toggle('show_horizon')]),details(true),features];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    const value={...e.detail.value};
    // Another kind of card: its first format. The kind itself is not a setting of the card.
    if(typeof value.kind==='string'&&value.kind!==kindOf(this.config.format))value.format=KINDS[value.kind as Kind][0];
    delete value.kind;
    this.config=cleanConfig(tidy(nextConfig(this.config,value),this.config as unknown as Record<string,unknown>,this.defaults(this.config)) as unknown as Config);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private defaults(c:Config):Record<string,unknown>{
    return {piece_style:'detailed',animations:true,glass_effect:true,rotate:true,show_details:true,details_open:false,measures_open:false,show_measures:true,
      show_horizon:true,horizon_mode:'needed',horizon_subjects:[...HORIZON_SUBJECTS],show_insights:true,insight_groups:[...INSIGHT_GROUPS],insight_max:8,detail_rows:[...DETAIL_ROWS],
      banner_blocks:['remedies','later'],tile_chips:[...CHIPS],tile_blocks:[...TILE_BLOCKS],mini_values:['temperature'],hold_action:c.hold_path?'page':'popup',now_blocks:[...NOW_BLOCKS],tap_action:'toggle',
      scale_marks:c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]};
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...this.defaults(c),hold_action:c.hold_action??(c.hold_path?'page':'popup'),
      ...c,kind:kindOf(c.format),show_scale:scaleShown(c),now_blocks:nowBlocks(c),modules:(c.modules??MODULES).filter(m=>m!=='temperature'),
      // The tile draws neither the temperature chip (« En ce moment » says it) nor the scale block (inside its case).
      tile_chips:(c.tile_chips??CHIPS).filter(x=>x!=='temperature'),tile_blocks:(c.tile_blocks??TILE_BLOCKS).filter(x=>x!=='scale')};
    const s=this.schema(),cut=s.findIndex(x=>x.name==='kind')+1;
    const form=(schema:typeof s)=>html`<ha-form .hass=${this.hass} .data=${data} .schema=${schema} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
    const one=this.entries?.length===1?this.entries[0]:this.entries?.find(e=>e.entry_id===c.entry_id);
    return html`${this.entries===null?html`<p class="note warn">${t('L’intégration Hestia Confort ne répond pas : vérifiez qu’elle est installée et chargée.')}</p>`
      :this.entries?.length===0?html`<p class="note warn">${th('Aucune pièce : ouvrez {link} dans la barre latérale pour en ajouter une.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>`
      :html`<p class="note">${one?html`${th('Pièce : {room}.',{room:html`<b>${one.volume?.length&&one.volume_name?one.volume_name:one.title}</b>`})} `:nothing}${th('Les capteurs et préférences se règlent dans {link}.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>`}
      ${form(s.slice(0,cut))}${this.formats()}${form(s.slice(cut))}`;
  }
  /** The formats of the chosen kind as tiles, as in the editor's mockup: an icon, a name, what it shows. */
  private formats(){
    const f=this.config!.format??'tile',kind=kindOf(f);
    const pick=(value:Format)=>{if(value!==f)this.changed(new CustomEvent('value-changed',{detail:{value:{format:value}}}));};
    return html`<div class="formats" role="radiogroup" aria-label=${t('Format')}>${KINDS[kind].map(k=>{const [icon,name,text]=FORMAT_INFO[k];
      return html`<button type="button" role="radio" aria-checked=${k===f} class=${k===f?'on':''} @click=${()=>pick(k)}><ha-icon icon=${icon}></ha-icon><b>${t(name)}</b><span>${t(text)}</span></button>`;})}</div>
      <p class="note hint">${t(KIND_NOTE[kind])}</p>`;
  }
}
if(!customElements.get('hestia-comfort-card-editor'))customElements.define('hestia-comfort-card-editor',ComfortEditor);

const HOME_DEFAULTS:Record<string,unknown>={format:'full',sections:[...SHOWN_SECTIONS],folded:[...FOLDED_SECTIONS],more_open:false,period:'day',hero_temperature:'outdoor',animations:true,glass_effect:true,rotate:true,show_scale:true,show_rooms:true,rooms_open:false,show_details:true,details_open:false,
  banner_blocks:['rooms','house'],list_order:'urgent',hold_action:'popup'};
/** The home card's editor, built the same way. */
export class ComfortHomeEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  static styles=styles;
  protected willUpdate(){setLanguage(this.hass?.language);}
  setConfig(config:HomeConfig){this.config=cleanHomeConfig(config);}
  protected shouldUpdate(changed:Map<PropertyKey,unknown>){return !(changed.size===1&&changed.has('hass')&&!!this.config);}
  private schema(){
    const c=this.config!,f=c.format??'full',action=homeAction(c);
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:t('Complète : les conseils des pièces, puis le bilan du jour, de la semaine ou du mois')},{value:'tile',label:t('Tuile : le titre et le bandeau ; un appui déplie le bilan')},
      {value:'list',label:t('Liste des pièces : une ligne par pièce')},{value:'mini',label:t('Mini : une ligne pour toute la maison')},
      {value:'alert',label:t('Alerte : visible seulement si une pièce demande un geste')}]}}};
    const head=[{name:'title',selector:{text:{}}},format];
    // The big temperature of the title line (7 November): outside, or the mean of the rooms. Mini and alert do not show it.
    const temperature=dropdown('hero_temperature',[['outdoor',fr('Dehors')],['home',fr('Moyenne des pièces')]]);
    const banner=group(fr('Bandeau intelligent'),'mdi:view-day-outline',[choices('banner_blocks',[['rooms',fr('Conseils des pièces')],['house',fr('Gestes pour toute la maison (air traversant)')]]),toggle('rotate')],true);
    if(f==='mini')return [...head,look(),hold(action)];
    if(f==='alert')return [...head,look(),banner,hold(action)];
    if(f==='list')return [...head,temperature,look(),group(fr('Contenu'),'mdi:format-list-bulleted',[dropdown('list_order',[['urgent',fr('Celles qui demandent un geste d’abord')],['floor',fr('Par étage')]])],true),hold(action)];
    const sections=SECTIONS.map(k=>[k,SECTION_LABELS[k]] as [string,string]);
    // The tile unfolds into the full card's review (6 November): the same settings.
    return [...head,temperature,look(),banner,
      group(fr('Bilan'),'mdi:chart-box-outline',[dropdown('period',[['day',fr('Jour')],['week',fr('Semaine')],['month',fr('Mois')]]),choices('sections',sections),choices('folded',sections),toggle('more_open'),toggle('rooms_open'),toggle('details_open')],f==='full'),
      hold(action,f==='full')];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    const next={...this.config,...e.detail.value} as HomeConfig;
    // Changing format resets an action the new format does not offer (a window on the full card).
    if((next.format??'full')==='full'&&next.hold_action==='popup')delete next.hold_action;
    this.config=cleanHomeConfig(tidy(next as unknown as Record<string,unknown>,this.config as unknown as Record<string,unknown>,{...HOME_DEFAULTS,hold_action:homeAction({...next,hold_action:undefined,hold_path:undefined})}) as unknown as HomeConfig);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...HOME_DEFAULTS,...c,hold_action:homeAction(c)};
    return html`<p class="note">${th('Toutes les pièces de Hestia Confort. Elles se règlent dans {link}.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('hestia-comfort-home-card-editor'))customElements.define('hestia-comfort-home-card-editor',ComfortHomeEditor);
