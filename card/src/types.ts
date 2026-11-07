import type {Advisor3} from './views/advisor3';
import {t,fr} from './i18n';
export const LEVELS = ['calm','benefit','action','urgent','neutral'] as const;
export const ACTIONS = ['ok','ouvrir','fermer','attendre','unknown'] as const;
export const MODULES = ['windows','air','temperature','humidity','shutters','coordination'] as const;
export type Level = typeof LEVELS[number];
export type Module = typeof MODULES[number];
/** Like Hestia Weather: full, tile (folds), intermediate (the tile unfolded), mini (one line), measures (the tiles alone),
 *  alert (only while a gesture is asked, hidden otherwise), and one card per measure (the full card's modules). */
export const FORMATS = ['full','tile','intermediate','mini','measures','alert','temperature','humidity','air','openings','heating','devices','horizon','feel'] as const;
export type Format = typeof FORMATS[number];
/** The formats in three kinds, as Hestia Weather's editor: large cards, one card per piece of the room, small cards. */
export type Kind = 'large'|'piece'|'small';
export const KINDS:Record<Kind,Format[]>={large:['full','tile'],piece:['feel','temperature','humidity','air','devices','openings','heating','measures','horizon'],small:['mini','alert']};
export const kindOf=(format:Format='tile'):Kind=>(Object.keys(KINDS) as Kind[]).find(k=>KINDS[k].includes(format))??'large';
/** The modules of the full card's « Maintenant », each also a card of its own. */
export const PIECES = ['temperature','humidity','air','openings','heating'] as const;
export type Piece = typeof PIECES[number];
/** What scrolls after the advice of the moment: remedies at work (purifier, ventilation), a better moment later. */
export const BANNER_BLOCKS = ['remedies','later'] as const;
export type BannerBlock = typeof BANNER_BLOCKS[number];
/** Marks of the temperature scale; none removes the scale. */
export const SCALE_MARKS = ['band','day','out'] as const;
export type ScaleMark = typeof SCALE_MARKS[number];
/** The pieces of « En ce moment » (6 November, as Hestia Weather's « Aujourd’hui »): the Ressenti's warmth and humidity,
 *  the air in rings, the line of devices. */
export const NOW_BLOCKS = ['warmth','humidity','air','devices'] as const;
export type NowBlock = typeof NOW_BLOCKS[number];
/** A tap on the tile, as Hestia Weather's: fold or unfold, the full card in a window, a page, or nothing. */
export const TAP_ACTIONS = ['toggle','popup','page','none'] as const;
export type TapAction = typeof TAP_ACTIONS[number];
/** Chips under the advice of a folded tile, and values on a mini line. */
export const CHIPS = ['temperature','humidity','co2'] as const;
export type Chip = typeof CHIPS[number];
/** What an unfolded tile shows, in this order. */
export const TILE_BLOCKS = ['scale','horizon','measures','details'] as const;
export type TileBlock = typeof TILE_BLOCKS[number];
/** A long press (a tap on mini and alert): the full card in a window, a dashboard page, or nothing. */
/** Topics of « À savoir », and lines of « Détails techniques »: the card shows those kept, in its own order. */
export const INSIGHT_TOPICS = ['humidity','heating','sun','windows','equipment','household','forecast','learning'] as const;
export type InsightTopic = typeof INSIGHT_TOPICS[number];
/** The headings of « À savoir » as the 3.0 advisor writes it: for the gesture, worth watching, good to know. */
export const INSIGHT_GROUPS = ['gesture','watch','know'] as const;
export type InsightGroup = typeof INSIGHT_GROUPS[number];
export const DETAIL_ROWS = ['range','slot','windows','shutters','people','drying','trend','sensors'] as const;
export type DetailRow = typeof DETAIL_ROWS[number];
/** Subjects of the « Prochaines heures » graph. */
export const HORIZON_SUBJECTS = ['temperature','humidity'] as const;
export type HorizonSubject = typeof HORIZON_SUBJECTS[number];
/** When the graph shows: only when the gesture changes something on it, or always (the trend when nothing is needed). */
export const HORIZON_MODES = ['needed','always'] as const;
export type HorizonMode = typeof HORIZON_MODES[number];
export interface Horizon {subject:HorizonSubject;kind:'cool'|'air'|'sun'|'dry'|'trend';needed?:boolean;advice?:string;unit:'°C'|'%';start:string;step_minutes:number;base:number[];gesture:number[]|null;
  bands:string[][];extra:string[][];result:Record<string,string|number|null>}
export const HOLD_ACTIONS = ['popup','page','none'] as const;
export type HoldAction = typeof HOLD_ACTIONS[number];
export const moduleLabels:Record<Module,string>={windows:fr('Fenêtres'),air:fr('Qualité de l’air'),temperature:fr('Température'),humidity:fr('Humidité'),shutters:fr('Soleil et volets'),coordination:fr('Chauffage')};
export interface Config {
  type: 'custom:hestia-comfort-card'; entry_id?: string; title?: string; format?: Format;
  /** The 3.0 advisor's sensor in the HA de test (`sensor.conseil_3_salon`): the banner, « À savoir » and « Pourquoi ? » read it. */
  conseil?: string;
  modules?: Module[]; animations?: boolean; glass_effect?: boolean; theme?: 'auto'|'light'|'dark';
  /** What the card shows and how it opens: the scale, the measures, the details, and whether advices scroll by themselves. */
  show_scale?: boolean; show_measures?: boolean; show_details?: boolean; measures_open?: boolean; details_open?: boolean; rotate?: boolean;
  banner_blocks?: BannerBlock[]; scale_marks?: ScaleMark[]; tile_chips?: Chip[]; tile_blocks?: TileBlock[]; mini_values?: Chip[];
  hold_action?: HoldAction; hold_path?: string; tap_action?: TapAction;
  /** What « En ce moment » shows, in its order; none hides it. */
  now_blocks?: NowBlock[];
  /** The « Prochaines heures » graph in the banner, and its subjects. */
  show_horizon?: boolean; horizon_mode?: HorizonMode; horizon_subjects?: HorizonSubject[];
  /** « À savoir » and « Détails techniques »: shown or not, which topics and lines, how many lines. */
  show_insights?: boolean; insight_topics?: InsightTopic[]; insight_groups?: InsightGroup[]; insight_max?: number; detail_rows?: DetailRow[];
  /** « À la carte »: the full card's module as it is, or compact (the measure, its way, its half hour). */
  piece_style?: 'detailed'|'compact';
}
/** A list setting: only known values, each once, in the given order. */
function list<T extends string>(value:unknown,known:readonly T[],name:string):T[]|undefined{
  if(value===undefined)return undefined;
  if(!Array.isArray(value)||value.some(v=>!known.includes(v)))throw new Error(t('Réglage « {name} » invalide.',{name}));
  return [...new Set(value as T[])];
}
function hold(input:{hold_action?:unknown;hold_path?:unknown}){
  if(input.hold_action!==undefined&&!HOLD_ACTIONS.includes(input.hold_action as HoldAction))throw new Error(t('Appui long inconnu.'));
  if(input.hold_path!==undefined&&typeof input.hold_path!=='string')throw new Error(t('La page à ouvrir doit être un chemin.'));
}
export interface Reading {
  value: number|boolean|string|null; quality:'valid'|'unknown'|'stale'|'estimated';
  source:string|null; received_at:string|null; detail:string|null; unit:string|null;
}
export interface Features {
 shutters?:{entity_id:string;mode:'none'|'manual'|'connected';position:number|null;state:string|null;advice:'close'|'open'|null;message:string;shade_fraction:number|null;shade_model:'geometry'|'simple'|'unknown';manual_override:boolean|null;automatic:boolean|null;
  cover?:string|null;driver?:'adaptive_cover_pro'|'cover_automatic'|'cover_extender'|null;sun_front?:boolean|null;target?:number|null;sun_start?:string|null;sun_end?:string|null;soon?:boolean;driving?:boolean;off?:'disabled'|'auto'|'tracking'|null;detection?:boolean|null;climate?:boolean|null;reason?:string|null;override_end?:string|null}[];
 presence?:{state:'occupied'|'empty'|'leaving'|'unknown'|'not_configured';message:string;minutes?:number;delay?:number};
 air?:{co2_status?:'high'|'ok'|'unknown'|'not_configured';pm25_status:'high'|'ok'|'unknown'|'not_configured';voc_status:'high'|'ok'|'uninterpreted'|'unknown'|'not_configured';voc_unit:string|null;voc_minutes?:number|null;voc_mean?:number|null;voc_paused?:boolean;voc_falling?:boolean;voc_outdoor?:boolean;voc_rising_open?:boolean;purifier:{on:boolean|null;speed:number|null};pm25_treated?:boolean;ventilation?:{on:boolean|null;boost?:boolean}|null;coverage:string;message:string};
 ventilation?:{opened_minutes:number|null;duration_minutes:{min:number;max:number}|null;message:string;capacity:number|null};
 humidity?:{dew_point:number|null;incoming_relative:number|null;glass_temperature:number|null;condensation_risk:boolean|null;message:string;
  status?:'unknown'|'normal'|'low'|'high';degree?:number;measured?:number|null;minimum?:number;maximum?:number;lasting?:boolean;trend?:'improving'|'worsening'|'stable'|null;
  /** Air against the coldest spot of the outer walls (%), mould risk, water above outdoors (g/m³), where it comes from, best reachable by airing (%). */
  surface?:number|null;mould?:boolean;excess?:number|null;local?:number|null;source?:'inside'|'outside'|null;reachable?:number|null;shower?:{since:string;minutes:number;base:number;peak:number}|null};
 /** What airing would really bring, from the room's past openings: humidity now and after, lasting gain in points. */
 rain_ahead?:{minutes:number;precise:boolean}|null;
 /** High pollens, only for a household that said it is allergic (« Réglages généraux »). */
 pollen?:{level:number|null;main:string|null;after_rain:boolean;airing:boolean}|null;
 /** A gesture whose result the room's twin predicts, once it has proved itself in this room. */
 learned?:{now:number;after:number;minutes:number;measure:'humidity'|'temperature'|'co2'|'voc';openings:number;days:number;precision:{temperature:number;humidity:number};closing?:boolean}|null;
 /** What the sun on the windows does for the room now (engine/assessment.py, _benefits). */ benefits?:{kind:'sun_warms'|'sun_heats';openings:string[];watts:number;keep_shut?:boolean}[];
 volume?:{lead:string;reason:string;action:string;assessment?:Partial<Assessment>&{reason:string};observations?:Record<string,Reading>};
 warmth?:{occupied:boolean|null;heating:'on'|'off'|null;chilly_since?:string|null;tolerance?:number;warming?:boolean;outdoor_warms?:boolean;slight?:boolean;thermostat?:{name:string;preset:string|null;target:number|null;off_reason:string|null;lowered:boolean;reference:number|null};
  /** ha-chauffage's next change (engine/schedule.py): when, to which preset (null when not known), at which temperature. */
  next?:NextChange|null}|null;
 thermostat?:{name:string;window:boolean;preset:string|null;target:number|null;reference:number|null}|null;
 people?:{home:string[];away:string[]}|null;
 household?:{away_open:boolean;empty_room:boolean;sleeping:boolean;alarm:{name:string;state:string;armed:boolean}|null}|null;
 horizon?:Horizon[];
 night?:{windows:{start:string;end:string}[];minimum:{time:string;temperature:number}|null;peak:{time:string;outdoor:number;shut:number;aired:number}|null;gain:number;worth?:boolean;humid:boolean}|null;
 warm_walls?:{degrees:number;target:number;surface:number;after:number}|null;
 /** An open window letting warmer air into a room under the middle of its range. */
 open_warms?:boolean;
 /** The schedule's next change (ha-chauffage, Scheduler), cold or not. */
 planned?:NextChange|null;
 drying?:{minutes:number;now:number;after:number;gain:number;tau:number;openings:number;morning?:number;alone?:number;net?:number;later:{minutes:number;now:number;after:number;gain:number;time:string}|null}|null;
 trends?:{indoor:number|null;outdoor:number|null;window_minutes:number;message:string;
   /** Each measure's last half hour, for its tile: speed per hour, way, and [minutes ago, value] points. */
   curves?:Partial<Record<'temperature'|'humidity'|'co2'|'voc'|'pm25'|'solar'|'heating',{slope:number;way:'up'|'down'|'stable';points:[number,number][]}|null>>};
 season?:{known:boolean;weight:number|null;outdoor_mean:number|null;minimum:number;maximum:number;heated:boolean;
   /** The home's season when known (Hestia Weather's, or a season sensor): it sets the rules of the advice. */ name?:string|null;group?:'summer'|'between'|'winter'|null};
 day_range?:{min:number;max:number}|null;
 /** Minutes the room heated over the last 24 hours (the thermostat's action, read in the recorder). */
 heating_day?:{minutes:number}|null;
 /** Where the air goes through best (engine/wind.py, plan): what to open, what already helps, what to leave shut. */
 airflow?:{open:string[];keep:string[];path:'wind'|'opposite'|'two_sides'|'one_side';into:string|null;faster:number|null;learned:number;
   avoid:{entity_id:string;why:'rain'|'gust'|'sun'}[]}|null;
}
export interface Assessment {
  features?:Features;
  action:typeof ACTIONS[number]; level:Level; reason:string;
  needs:string[]; constraints:string[]; opportunities:string[]; partial:boolean; missing:string[];
  heating_action:string; indoor_absolute_humidity:number|null; outdoor_absolute_humidity:number|null;
  temperature_delta:number|null; coordination:string;
  openings?:Opening[]; sun?:{elevation:number;azimuth:number}|null; unverified?:string[]; wind_bearing?:number|null; crossing?:string|null; open_first?:string[];
  slot?:{kind:'open'|'close';time:string;temperature:number;wind_bearing:number|null}|null; rain_soon_minutes?:number|null;
}
export interface Opening {
  entity_id:string; open:boolean|null; exposure:string|null; kind:string; sheltered:boolean;
  sun_share:number; sun_wm2:number|null; wind_side?:string|null; flags:string[];
}
export interface View {
  version:1; entry_id:string; area_id:string|null; title:string; /** The 3.0 advisor's decision, when the card reads one (`Config.conseil`). */ advisor?:Advisor3; /** The integration's 3.0 advisor for this room's air (advisor_home.py): its decision, « waiting » just after a restart; absent without one. */ advice3?:Record<string,unknown>|null; computed_at:string; /** The room's comfort range from its settings. */ comfort_minimum?:number; comfort_maximum?:number; /** The air's marks as set: CO₂ [correct, to renew, urgent] in ppm, particles to treat in µg/m³. */ air_marks?:{co2:[number,number,number];pm25:number};
  assessment:Assessment; observations:Record<string,Reading>; names?:Record<string,string>; /** Rooms open onto this one: one air, shared openings. */ volume?:{entry_id:string;title:string}[]; /** Sources read from the room sharing this air, by key: {heating:'Salon'}. */ inherited?:Record<string,string>; /** « Salon · Cuisine », the best equipped first. */ volume_name?:string|null;
  /** The feedback loop: the last airing followed (within a day) and the week (engine/feedback.py). */
  feedback?:{last:{measure:'humidity'|'temperature'|'co2'|'voc';before:number;after:number;predicted:number|null;minutes:number}|null;week:{followed:number;ignored:number;evaluated:number;held:number;gains:Record<string,number>}};
  /** A humidity habit the person confirmed, going on now: the words for « À savoir ». */ habit?:string|null;
  /** What the room's twin has learned so far (engine/twin.py). */ twin?:{status:'learning'|'ready';days:number;samples:number;next_hour:{temperature:number;humidity:number}|null;precision:{hours:number;temperature:number;humidity:number}|null;
    /** How much of the room is learned: 100 % once everything it has is seen. */ progress?:{percent:number;complete:boolean;parts:Partial<Record<'days'|'precision'|'sun'|'windows'|'heating'|'air',number>>;seen:{days:number;airings:number;open?:number};
      /** What the advice can already promise, measure by measure. */ ready?:{humidity:boolean;temperature:boolean;air:string[]}}}; /** Home Assistant (or the room) has just started: silent sensors are still loading. */ starting?:boolean;
  /** What the body feels in the room; the advice still judges the air. */ feel?:Feel|null;
}
/** What the body feels in the room (engine/feel.py): the air, half of what the surfaces add, a draught, damp warm air. */
export interface Feel {feels:number; air:number; outdoor:number|null; walls:'bien'|'moyenne'|'peu'; glazing:'simple'|'double'|'triple';
  factors:{walls:{delta:number;gap:number|null;wall:number|null;pane:number|null;shutters:boolean};
    sun:{delta:number;wm2:number|null;night:boolean;hidden:boolean};
    heating:{delta:number;kind:'stove'|'pellet'|'radiator'|'radiant'|'inertia'|'floor'|'ac'|null;on:boolean}|null;
    draught:{delta:number;open:boolean;gust:number|null};
    humidity:{delta:number;value:number;dew:number}|null}}
export interface ViewEvent {version:1; view?:View; reload?:boolean; unavailable?:boolean}
export type Unsubscribe = () => Promise<void>|void;
export interface Connection {
  subscribeMessage<T>(callback:(event:T)=>void, message:Record<string,unknown>):Promise<Unsubscribe>;
  sendMessagePromise?<T>(message:Record<string,unknown>):Promise<T>;
}
export interface HomeAssistant {
  connection:Connection; user?:{is_admin:boolean}; themes?:{darkMode?:boolean}; language?:string;
  callWS<T>(message:Record<string,unknown>):Promise<T>;
  states?:Record<string,{state:string;attributes:Record<string,unknown>;last_updated?:string}>;
  callApi?<T>(method:string,path:string,data?:Record<string,unknown>):Promise<T>;
}
export interface Entry {entry_id:string; title:string; area_id:string|null; volume?:string[]; volume_name?:string|null}
export function cleanConfig(input:Config):Config {
  if(!input || input.type!=='custom:hestia-comfort-card') throw new Error(t('Type de carte Hestia Comfort invalide.'));
  if(input.format && !FORMATS.includes(input.format)) throw new Error(t('Format de carte inconnu.'));
  if(input.entry_id!==undefined && typeof input.entry_id!=='string') throw new Error(t('Choisissez une pièce Hestia Comfort.'));
  if(input.title!==undefined && typeof input.title!=='string') throw new Error(t('Le titre doit être un texte.'));
  if(input.conseil!==undefined && (typeof input.conseil!=='string'||!input.conseil.startsWith('sensor.'))) throw new Error(t('Le conseil 3.0 doit être un capteur.'));
  if(input.theme && !['auto','light','dark'].includes(input.theme)) throw new Error(t('Thème inconnu.'));
  for(const key of ['animations','glass_effect','show_scale','show_measures','show_details','measures_open','details_open','rotate'] as const)
    if(input[key]!==undefined && typeof input[key]!=='boolean') throw new Error(t('Réglage d’affichage invalide.'));
  if(input.modules && (!Array.isArray(input.modules) || input.modules.some(m=>!MODULES.includes(m)))) throw new Error(t('Rubrique inconnue.'));
  if(input.horizon_mode!==undefined&&!HORIZON_MODES.includes(input.horizon_mode))throw new Error(t('Réglage « graphique » invalide.'));
  if(input.piece_style!==undefined&&!['detailed','compact'].includes(input.piece_style))throw new Error(t('Réglage « version » invalide.'));
  if(input.tap_action!==undefined&&!TAP_ACTIONS.includes(input.tap_action))throw new Error(t('Réglage « appui » invalide.'));
  hold(input);
  const lists={banner_blocks:list(input.banner_blocks,BANNER_BLOCKS,'bandeau'),scale_marks:list(input.scale_marks,SCALE_MARKS,'échelle'),
    tile_chips:list(input.tile_chips,CHIPS,'pastilles'),tile_blocks:list(input.tile_blocks,TILE_BLOCKS,'tuile dépliée'),mini_values:list(input.mini_values,CHIPS,'ligne'),
    horizon_subjects:list(input.horizon_subjects,HORIZON_SUBJECTS,'sujets du graphique'),insight_topics:list(input.insight_topics,INSIGHT_TOPICS,'sujets À savoir'),insight_groups:list(input.insight_groups,INSIGHT_GROUPS,'rubriques À savoir'),
    detail_rows:list(input.detail_rows,DETAIL_ROWS,'lignes des détails'),now_blocks:list(input.now_blocks,NOW_BLOCKS,'En ce moment')};
  if(input.insight_max!==undefined&&!(Number.isInteger(input.insight_max)&&input.insight_max>=1&&input.insight_max<=8))throw new Error(t('Réglage « lignes À savoir » invalide : de 1 à 8.'));
  return {...input,...Object.fromEntries(Object.entries(lists).filter(([,v])=>v!==undefined)), format:input.format??'tile', modules:[...new Set(input.modules??MODULES)]};
}
/** « En ce moment » of a card: its list, else what an older card's switch and cases allowed (6 November). */
export function nowBlocks(c:Config):NowBlock[] {
  if(c.now_blocks)return c.now_blocks;
  if(c.show_measures===false)return [];
  const m=new Set(c.modules??MODULES);
  return NOW_BLOCKS.filter(b=>b==='warmth'||(b==='humidity'?m.has('humidity'):b==='air'?m.has('air'):m.has('air')||m.has('windows')||m.has('shutters')||m.has('coordination')));
}

/** The home card's settings: the same display choices as a room card, rooms instead of measures. */
export const HOME_FORMATS = ['full','tile','list','mini','alert'] as const;
export type HomeFormat = typeof HOME_FORMATS[number];
/** What scrolls in the home banner: the rooms' advice, and gestures for the whole house (cross ventilation). */
export const HOME_BANNER = ['rooms','house'] as const;
export interface HomeConfig {type:'custom:hestia-comfort-home-card';title?:string;theme?:'auto'|'light'|'dark';format?:HomeFormat;
  rotate?:boolean;show_scale?:boolean;show_rooms?:boolean;rooms_open?:boolean;show_details?:boolean;details_open?:boolean;
  animations?:boolean;glass_effect?:boolean;banner_blocks?:(typeof HOME_BANNER[number])[];list_order?:'urgent'|'floor';
  hold_action?:HoldAction;hold_path?:string;
  /** The full card: its sections, those inside « Plus de détails », that fold opened, and the period shown first. */
  sections?:(typeof HOME_SECTIONS[number])[];folded?:(typeof HOME_SECTIONS[number])[];more_open?:boolean;period?:'day'|'week'|'month';
  /** The big temperature of the title line: outside (default) or the mean of the declared rooms (7 November). */
  hero_temperature?:'outdoor'|'home'}
export const HOME_SECTIONS=['themes','rooms_chart','curve','rooms','details'] as const;
export const HOME_FLAGS=['rotate','show_scale','show_rooms','rooms_open','show_details','details_open','more_open','animations','glass_effect'] as const;
export function cleanHomeConfig(input:HomeConfig):HomeConfig {
  if(!input||input.type!=='custom:hestia-comfort-home-card')throw new Error(t('Type de carte invalide.'));
  if(input.title!==undefined&&typeof input.title!=='string')throw new Error(t('Le titre doit être un texte.'));
  if(input.theme&&!['auto','light','dark'].includes(input.theme))throw new Error(t('Thème inconnu.'));
  for(const k of HOME_FLAGS)if(input[k]!==undefined&&typeof input[k]!=='boolean')throw new Error(t('Réglage d’affichage invalide.'));
  if(input.format&&!HOME_FORMATS.includes(input.format))throw new Error(t('Format de carte inconnu.'));
  if(input.list_order!==undefined&&!['urgent','floor'].includes(input.list_order))throw new Error(t('Ordre des pièces inconnu.'));
  hold(input);
  const banner=list(input.banner_blocks,HOME_BANNER,'bandeau');
  if(input.period!==undefined&&!['day','week','month'].includes(input.period))throw new Error(t('Période inconnue.'));
  if(input.hero_temperature!==undefined&&!['outdoor','home'].includes(input.hero_temperature))throw new Error(t('Température affichée inconnue.'));
  const sections=list(input.sections,HOME_SECTIONS,'sections'),folded=list(input.folded,HOME_SECTIONS,'sections');
  return {...input,...(banner?{banner_blocks:banner}:{}),...(sections?{sections}:{}),...(folded?{folded}:{})};
}
/** What a long press does on the home card: a page when one is set, else a window, except on the full card (nothing). */
export const homeAction=(c:HomeConfig)=>c.hold_action??(c.hold_path?'page':(c.format??'full')==='full'?'none':'popup');

/** The review card (review-card.ts): a title and its format, « summary » unless « full » is chosen. */
export type ReviewFormat='summary'|'full';
/** `entry_id`: one room's review (its sheet, or its summary), instead of the whole home's (6 November). */
export interface ReviewConfig {type:'custom:hestia-comfort-review-card';title?:string;format?:ReviewFormat;entry_id?:string}

export function cleanReviewConfig(input:ReviewConfig):ReviewConfig {
  if(!input||input.type!=='custom:hestia-comfort-review-card')throw new Error(t('Type de carte Hestia Confort · bilan invalide.'));
  const config:ReviewConfig={type:input.type,format:input.format==='full'?'full':'summary'};
  if(typeof input.title==='string'&&input.title.trim())config.title=input.title.trim();
  if(typeof input.entry_id==='string'&&input.entry_id)config.entry_id=input.entry_id;
  return config;
}
/** When the heating changes next, as ha-chauffage plans it; `override`: the end of a change made by hand. */
export interface NextChange {at:string;preset:string|null;name:string|null;temperature:number|null;override:boolean}
