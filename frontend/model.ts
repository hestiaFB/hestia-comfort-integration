import type {Advisor3Room,Outside3} from './learning3';
import {t,fr,currentLocale} from './socle/i18n';
/** A map of French texts read in the user's language: each value is translated when it is read. */
export function words<T extends Record<string,string>>(map:T):T{return new Proxy(map,{get:(o,k)=>{const v=Reflect.get(o,k);return typeof v==='string'?t(v):v;}});}
export const labels:Record<string,string>=words({season:fr('Saison'),indoor_temperature:fr('Température de la pièce'),indoor_humidity:fr('Humidité de la pièce'),co2:fr('CO₂'),pm25:fr('Particules fines PM2.5'),voc:fr('Composés organiques volatils (COV)'),purifier:fr('Purificateur'),ventilation:fr('Ventilation (VMC)'),ventilation_boost:fr('Vitesse rapide de la VMC (Turbo)'),presence:fr('Présence dans la pièce'),illuminance:fr('Luminosité'),windows:fr('Fenêtres et portes vers l’extérieur'),heating:fr('Chauffage'),heating_indicator:fr('Indicateur de chauffe'),outdoor_temperature:fr('Température dehors'),outdoor_humidity:fr('Humidité dehors'),rain:fr('Pluie actuelle'),wind_gust:fr('Rafales de vent'),wind_bearing:fr('Direction du vent'),solar:fr('Ensoleillement'),pollution:fr('Qualité de l’air extérieur')});
export const indoor=['indoor_temperature','indoor_humidity'] as const;
export const outdoor=['outdoor_temperature','outdoor_humidity','rain','wind_gust','wind_bearing','solar','pollution','season'] as const;
export const multiple=new Set(['windows','presence']);
export const exposures:[string,string][]=[['N',fr('Nord')],['NE',fr('Nord-est')],['E',fr('Est')],['SE',fr('Sud-est')],['S',fr('Sud')],['SO',fr('Sud-ouest')],['O',fr('Ouest')],['NO',fr('Nord-ouest')]];
export const kinds:[string,string][]=[['window',fr('Fenêtre')],['french',fr('Porte-fenêtre ou baie')],['skylight',fr('Vasistas ou petite fenêtre')],['door',fr('Porte')]];
export interface Candidate {
 entity_id:string;name:string;value:string;unit:string|null;area_id:string|null;
 local:boolean;outside:boolean;reference:boolean;available:boolean;adapter:string;warnings:string[];
 provenance:{entity_id:string;name:string;area_id:string|null}[];device_class:string|null;atmo_label:string|null;
 voc_reference?:{id:'sensirion_index';value:number;unit:string}|null;
 thermostat?:{name:string;mode:string|null;preset:string|null;target:number|null;comfort:number|null;eco:number|null;frost:number|null;off_reason:string|null;window:boolean|null;occupied:boolean|null}|null;
}
export interface Spec {entity_id:string;adapter:string;block_from?:number}
export interface OpeningMeta {exposure:string|null;azimuth?:number|null;kind:string;sheltered:boolean;shutter?:'none'|'manual'|'connected';cover_entity?:string;auto_entity?:string;override_entity?:string;width?:number;height?:number;overhang_depth?:number;overhang_gap?:number;glazing?:'simple'|'double'|'triple';shutter_habit?:'open'|'closed'|'varies'}
export interface EvolutionConfig {voc_threshold?:{value:number;unit:string};glazing_factor?:number;presence_delay_minutes?:number;voc_delay_minutes?:number;voc_pause_minutes?:number}
export interface Heater {entity_id:string;scope:'room'|'house';kind?:string;power?:number}
export interface CustomEquipment {name:string;effects:string[];entity_id:string|null}
export interface RoomBuilt {uses?:string;surface?:number;height?:number;outside?:string[];wall_material?:string;insulation?:string;partitions?:string}
export interface RoomConfig {heaters?:Heater[];thermostat_plage?:string|null;flows?:Partial<Record<'purifier'|'ventilation_boost',number>>;room?:RoomBuilt;foyer?:import('./foyer').Foyer;equipment_links?:Record<string,string>;custom_equipment?:CustomEquipment[];presence?:string[];equipment?:string[];evolution?:EvolutionConfig;floor_id?:string|null;area_id:string|null;name:string;sources:Record<string,string>;windows:string[];openings:Record<string,OpeningMeta>;settings:Record<string,number>;acknowledged?:string[];use_home?:boolean;rain_exposed?:boolean;heated?:boolean;thermostat_reference?:boolean;windows_unmeasured?:boolean;persons?:string[];open_to?:string[]}
export interface Room {entry_id:string;title:string;loaded:boolean;config:RoomConfig}
export interface Area {floor_id?:string|null;area_id:string;name:string;outdoor:boolean}
export interface Snapshot {version:1;revision:string;floors?:{floor_id:string;name:string;level:number|null}[];areas:Area[];rooms:Room[];home:{configured:boolean;sources:Record<string,Spec>;acknowledged?:string[];weather?:string|null;alarm?:string|null;pollen_allergy?:boolean;disabled?:string[];lights?:import('./lights').Lights;foyer?:import('./foyer').Foyer};hestia_weather?:{installed:boolean;places:{entry_id:string;title:string}[]};integrations?:{atmofrance?:boolean}}
export interface Discovery {version:1;revision:string;candidates:Record<string,Candidate[]>;suggestions:Record<string,string|string[]>;drivers?:Record<string,Driver>}
export interface DriverSignal {entity_id:string;name:string;on:boolean}
export interface Driver {name:string;driver?:string;auto:string|null;override:string|null;signals?:Partial<Record<'enabled'|'auto'|'tracking'|'detection'|'override'|'sun'|'climate',DriverSignal|null>>;azimuth?:number|null;exposure?:string|null;width?:number|null;height?:number|null}
// The technical state of the home (health.py): orange (bad) stops something, tip could be better, none is not used.
export type Level='ok'|'bad'|'tip'|'none'|'shared';
export type Target={kind:'room';entry_id:string;label:string}|{kind:'exterior';label:string}|{kind:'area';area_id:string;label:string};
/** « Ce que Hestia a appris » : what each room's twin learned, and how well it replays the last 24 hours. */
export interface TwinRoom {inertia_hours:number;sun_degrees:number|null;heating_degrees:number|null;household_degrees:number;window_half_minutes:number|null;air_changes_per_hour:number;window_air_changes_per_hour:number|null;water_per_hour:number;
 /** Rooms sharing one air: what the other room's windows and air weigh here, learned. */ far_window_percent?:number|null;mixing_percent?:number|null}
export interface Twin {status:'learning'|'ready';samples:number;days:number;open_samples?:number;room?:TwinRoom|null;
 precision?:{hours:number;temperature:number;humidity:number;curve:{time:string;temperature:number;measured_temperature:number;humidity:number;measured_humidity:number}[]}|null;next_hour?:{temperature:number;humidity:number}|null}
export interface Week {followed:number;ignored:number;evaluated:number;held:number;gains:Record<string,number>}
export interface Question {key:string;text:string;hint:string}
/** How much of a room is learned (engine/twin.py progress): each part 0 to 1, 100 % only once everything it has is seen. */
export interface Progress {percent:number;complete:boolean;parts:Partial<Record<'days'|'precision'|'sun'|'windows'|'heating'|'air',number>>;seen:{days:number;airings:number;open:number;sun:number;heated:number};
 /** What the advice can already promise, measure by measure, before the room is learned at 100 %. */ ready?:{humidity:boolean;temperature:boolean;air:string[]}}
export interface Twins {version:1;/** How reliable the outside is, for the 3.0 advisor (learning3.ts). */ outside?:Outside3|null;rooms:{entry_id:string;title:string;twin:Twin;week?:Week;questions?:Question[];air?:string[];progress?:Progress|null;
 /** What the 3.0 advisor knows of this room's air, shown in place of the 2.1 learning (learning3.ts). */ advisor?:Advisor3Room|null;
 /** Where the station's sun sensor is shaded, learned (engine/sunlight.py): azimuths by 10°. */ sun_shade?:{scale:number;shaded:number[];sunny_days:number}|null}[]}
export interface HealthLine {level:Level;text:string;why:string;target?:Target|null}
export interface Health {level:'ok'|'action';summary:string;tips_summary:string;rooms_summary:string;todo:HealthLine[];tips:HealthLine[];
 sources:{label:string;level:Level;text:string}[];version?:string;/** The advice engine's own version (advisor/__init__.py). */ advisor?:string;column_keys?:string[];sensors?:{answering:number;total:number};extensions?:Extension[];others?:{key:string;name:string;use:string}[];socle?:string;columns:string[];rooms:{entry_id:string;title:string;cells:{level:Level;text:string}[]}[];versions:HealthLine[]}
export interface Hass {callWS<T>(msg:Record<string,unknown>):Promise<T>;callService?(domain:string,service:string,data:Record<string,unknown>):Promise<unknown>;entities?:Record<string,{platform?:string;device_id?:string|null}>;devices?:Record<string,{name?:string|null;name_by_user?:string|null}>;language?:string;user?:{is_admin:boolean};themes?:{darkMode?:boolean};connection?:unknown;states?:Record<string,{state:string;attributes?:Record<string,unknown>}>}
export const warningText:Record<string,string>=words({
 alias:fr('Cette entité recopie une autre mesure. Vérifiez sa provenance ci-dessous.'),
 other_area:fr('La mesure ou sa source est rattachée à une autre pièce. Confirmez qu’elle représente bien celle-ci.'),
 contact_role:fr('Ce contact peut être une porte d’appareil, de meuble ou une porte intérieure. Gardez-le seulement s’il donne sur l’extérieur.'),
 derived:fr('Il s’agit d’une donnée calculée ou regroupée. Vérifiez ce qu’elle mesure réellement.'),
 no_hvac_action:fr('Cet équipement dit son mode mais pas s’il chauffe réellement : choisissez un indicateur de chauffe ci-dessous (vanne, relais, état de marche).'),
 binary_meaning:fr('Signal avancé : « actif » doit signifier pluie ou aération déconseillée. Un diagnostic de panne ne convient pas.'),
 outdoor_role:fr('Ce capteur n’est pas rattaché à une pièce extérieure. Vérifiez qu’il mesure bien l’air du dehors.'),
 used_indoor:fr('Ce capteur sert déjà de mesure intérieure pour une de vos pièces : il ne mesure sans doute pas l’air du dehors.'),
 daily_forecast:fr('Indice régional prévu pour la journée. Il peut déclencher votre précaution, mais ne prouve pas la qualité de l’air maintenant à vos fenêtres.')
});
// Names of Home Assistant areas that usually mean "living room".
const livingNames=['salon','séjour','sejour','living','living room','pièce de vie','piece de vie'];
export function livingArea(areas:Area[],used:Set<string>):Area|undefined {return areas.find(a=>!a.outdoor&&!used.has(a.area_id)&&livingNames.includes(a.name.trim().toLowerCase()));}
export function measurement(c:Candidate):string {
 if(!c.available)return t('Ne répond pas en ce moment');
 if(c.atmo_label)return c.atmo_label+' · '+t('indice du jour');
 if(c.value==='on'||c.value==='off')return c.device_class==='window'||c.device_class==='door'||c.device_class==='opening'?(c.value==='on'?t('Ouvert'):t('Fermé')):(c.value==='on'?t('Actif'):t('Inactif'));
 const n=Number(c.value);
 return (c.value!==''&&Number.isFinite(n)?new Intl.NumberFormat(currentLocale(),{maximumFractionDigits:1}).format(n):c.value)+(c.unit?' '+c.unit:'');
}
export function defaultOpening():OpeningMeta {return {exposure:null,kind:'window',sheltered:false};}
/** An ordinary opening of each kind, width × height in metres, when its size is not set: the advisor's (advisor/house.py KINDS, area ÷ height). */
export function ordinarySize(kind:string):[number,number]{return ({french:[0.9,2.1],skylight:[0.8,0.5],door:[0.9,2]} as Record<string,[number,number]>)[kind]??[1,1.2];}
export function newRoom(area:{area_id:string;name:string}|null,name:string,d:Discovery):RoomConfig {
 const sources:Record<string,string>={};for(const key of [...indoor,'illuminance','co2','pm25','voc','purifier','ventilation','ventilation_boost','heating']){const value=d.suggestions[key];if(typeof value==='string')sources[key]=value;}
 const windows=Array.isArray(d.suggestions.windows)?[...d.suggestions.windows]:[];
 const voc= d.candidates?.voc?.find(c=>c.entity_id===sources.voc),preset=vocPreset(voc);
 return {area_id:area?.area_id??null,name:area?.name??name,sources,presence:Array.isArray(d.suggestions.presence)?[...d.suggestions.presence]:[],windows,openings:Object.fromEntries(windows.map(id=>[id,defaultOpening()])),settings:{minimum:20,maximum:24,summer_maximum:26,...airReferenceDefaults},...(preset?{evolution:{voc_threshold:preset}}:{}),acknowledged:[]};
}
// New rooms use these explained operating choices. Existing settings are never
// replaced when opening the editor; backend defaults preserve older rooms.
export const airReferenceDefaults={co2_potential:800,co2_action:1000,co2_urgent:1500,pm25_action:15,humidity_low:40,humidity_high:60};
export function vocPreset(c?:Candidate):{value:number;unit:string}|undefined {
 const r=c?.voc_reference;
 return r?.id==='sensirion_index'&&r.unit===(c?.unit??'')?{value:r.value,unit:r.unit}:undefined;
}
export const thresholdSources={
 co2:'https://www.hcsp.fr/hcspi/Explore.cgi/avisrapportsdomaine?clefr=1154',
 pm25:'https://www.who.int/fr/news-room/questions-and-answers/item/who-global-air-quality-guidelines',
 voc:'https://sensirion.com/en/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf',
 tvoc:'https://www.umweltbundesamt.de/en/topics/health/commissions-working-groups/german-committee-on-indoor-air-guide-values',
 humidity:'https://agirpourlatransition.ademe.fr/particuliers/proteger-sante/eviter-polluants/respirer-air-sain-chez-soi',
};
export function coverage(room:RoomConfig):string {
 const parts=[];if(room.sources.indoor_temperature)parts.push(t('Température'));if(room.sources.indoor_humidity)parts.push(t('humidité'));if(room.sources.co2)parts.push('CO₂');
 const n=room.windows.length;
 return (parts.join(', ')||t('Mesures à compléter'))+' · '+(n>1?t('{n} ouvrants',{n}):n?t('{n} ouvrant',{n}):t('fenêtres non mesurées'));
}
const shortNames:Record<string,string>=words({season:fr('saison'),outdoor_temperature:fr('température'),outdoor_humidity:fr('humidité'),rain:fr('pluie'),wind_gust:fr('rafales'),wind_bearing:fr('direction du vent'),solar:fr('ensoleillement'),pollution:fr('qualité de l’air')});
export function exteriorSummary(sources:Record<string,Spec>):string {
 const names=outdoor.filter(k=>sources[k]).map(k=>shortNames[k]);
 return names.length?names.join(', ').replace(/^./,c=>c.toUpperCase()):t('Rien de configuré');
}
export function warningId(key:string,id:string){return key+':'+id;}

// The steps of a room, named by what they set (charte des onglets de réglage, ECOSYSTEME.md § 8).
export const stages=[fr('Température et humidité'),fr('Fenêtres et portes'),fr('Qualité de l’air'),fr('Chauffage'),fr('La pièce et ses réglages'),fr('Récapitulatif')];
// What each step is for, shown on top of it in a frame that folds: one idea per line.
export const intros:Record<string,string[]>={
 7:[fr('Une lumière couleur montre le conseil de la pièce : bleu tout va bien, vert à saisir, orange un geste.'),
  fr('Facultatif. La lumière se règle ici quand Extensions dit « Pièce par pièce ».')],
 0:[fr('La température de la pièce : la seule mesure obligatoire.'),
  fr('L’humidité est facultative : elle repère un air trop humide.'),
  fr('Les capteurs de la pièce sont proposés ; vous les gardez, les changez ou les retirez.')],
 1:[fr('Les contacts des fenêtres et portes qui donnent dehors.'),
  fr('Les contacts disent ce qui est ouvert ; l’exposition dit quand le soleil entre.'),
  fr('Facultatif : sans contact, les conseils ne savent pas ce qui est ouvert.')],
 2:[fr('Le CO₂, les particules et les COV suivent chacun une partie de la qualité de l’air.'),
  fr('Tout est facultatif. Un purificateur ne retire pas le CO₂.')],
 3:[fr('Le thermostat ou la vanne de la pièce, pour savoir si le chauffage tourne.'),
  fr('Le conseil évite alors d’ouvrir pendant qu’il chauffe. Il ne commande rien.'),
  fr('Facultatif.')],
 4:[fr('Le nom de la pièce et sa pièce Home Assistant.'),
  fr('Les précautions et les autres paramètres de fonctionnement, facultatifs.'),
  fr('Chaque seuil d’interprétation se règle avec son capteur, dans les étapes précédentes.')],
 5:[fr('Tout ce que vous avez choisi, onglet par onglet.'),
  fr('Rien ne change tant que vous n’avez pas enregistré ; un oubli, revenez à l’onglet voulu.')],
 exterior:[fr('Les mesures du dehors : température, humidité, pluie, vent, soleil et pollution.'),
  fr('Avec Hestia Weather, elles sont reprises de sa station ; sinon, vous choisissez vos capteurs.'),
  fr('Réglées une fois, elles servent à toutes vos pièces.')],
};
// The exterior sensors, by frame: title and keys.
export const outdoorGroups:[string,string[]][]=[[fr('Température et humidité'),['outdoor_temperature','outdoor_humidity']],[fr('Pluie et vent'),['rain','wind_gust','wind_bearing']],[fr('Soleil'),['solar']],[fr('Saison'),['season']]];
/** A season sensor's state, in words: the Season integration speaks English. */
export const seasonNames:Record<string,string>=words({spring:fr('Printemps'),printemps:fr('Printemps'),summer:fr('Été'),ete:fr('Été'),'été':fr('Été'),autumn:fr('Automne'),fall:fr('Automne'),automne:fr('Automne'),winter:fr('Hiver'),hiver:fr('Hiver')});
// Only the settings still displayed inside the "Autres réglages" advanced frame.
export const advancedDefaults:Record<string,number>={illuminance_low:100,gust_max:45,frost:1,sun_facade:250,max_age_seconds:10800};
export function changedAdvanced(settings:Record<string,number>):number{return Object.entries(advancedDefaults).filter(([k,v])=>settings[k]!==undefined&&settings[k]!==v).length;}
// One source in a list chosen by integration: its name, what it gives, and how to install it when missing.
export interface Choice {value:string;label:string;hint:string;available:boolean;missing?:string;url?:string;badge?:string}
/** An integration Confort reads (health.py EXTENSIONS): linked, installed but not used, or missing. */
export interface Extension {key:string;name:string;official:boolean;state:'linked'|'found'|'missing'|'off';level:Level;role:string;use:string;without:string;url:string;text:string;rooms:string[]}
export const links={atmofrance:'https://github.com/sebcaps/atmofrance',hestia_weather:'https://github.com/hestiaFB/hestia-weather-integration'};
// The integration behind an outdoor air quality source.
export function airSource(spec?:Spec):string{return !spec?'none':spec.adapter==='atmo_daily'?'atmo':spec.adapter==='hestia_index'?'hestia':'other';}
// The air quality sources, by integration, « Pas de … » last.
export function airChoices(s:Pick<Snapshot,'hestia_weather'|'integrations'>,all:Candidate[],current:string):Choice[]{
 const atmo=all.some(c=>c.adapter==='atmo_daily'),hestia=all.some(c=>c.adapter==='hestia_index'),nw=!!s.hestia_weather?.installed;
 const list:Choice[]=[
  {value:'atmo',label:'Atmo France',hint:t('L’indice ATMO du jour, pour votre zone.'),available:atmo,
   ...(atmo?{}:s.integrations?.atmofrance?{missing:t('Aucune zone trouvée : ajoutez-en une dans l’intégration Atmo France.')}:{missing:t('Pas encore installée'),url:links.atmofrance})},
  {value:'hestia',label:'Hestia Weather',hint:t('L’indice de qualité de l’air de votre lieu Hestia Weather.'),available:hestia,
   ...(hestia?{}:nw?{missing:t('Activez la qualité de l’air dans l’onglet Météo.')}:{missing:t('Pas encore installée'),url:links.hestia_weather})}];
 if(current==='other')list.push({value:'other',label:t('Autre signal'),hint:t('Un capteur choisi avant cette version.'),available:true});
 list.push({value:'none',label:t('Pas de qualité de l’air'),hint:t('Les conseils ne tiennent pas compte de la pollution.'),available:true});
 return list;
}
// Where the exterior measures come from: Hestia Weather's station, or the person's own sensors.
export function exteriorChoices(s:Pick<Snapshot,'hestia_weather'>):Choice[]{
 const nw=s.hestia_weather,ready=!!nw?.installed&&!!nw.places.length;
 return [{value:'weather',label:'Hestia Weather',hint:t('Meilleurs conseils : Confort sait s’il va pleuvoir, quand le soleil arrive et quand l’air dehors est mauvais.'),badge:t('recommandé'),available:ready,
   ...(ready?{}:nw?.installed?{missing:t('Aucun lieu dans l’onglet Météo pour l’instant.')}:{missing:t('Pas encore installée'),url:links.hestia_weather})},
  {value:'own',label:t('Vos propres capteurs'),hint:t('Une mesure à la fois, toutes facultatives. Sans prévisions ni alertes, les conseils seront moins justes.'),available:true}];
}
