import {html, LitElement, unsafeCSS, nothing, type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import charte from './ui/hestia-charte.css';
import roomStyle from './ui/room.css';
import sceneStyle from './ui/scene.css';
import traitStyle from './ui/trait.css';
import {watchOffscreen} from './ui/offscreen';
import {cleanConfig,type Config,type View,type HomeAssistant} from './types';
import {icon} from './ui/icons';
import {roomCard,asking,type CardState} from './views/room';
import {LiveView} from './live';
import {hassMatters} from './hass-change';
import {setLanguage,guessLanguage,t,fr} from './i18n';
import './editor';
import './review-card';
import './home';

// Manrope, the cards' font (the « Trait » style): declared once in the page, as the hub does, from the integration's files.
if(!document.getElementById('hestia-hub-fonts')){const style=document.createElement('style');style.id='hestia-hub-fonts';
  style.textContent=[400,500,600,700].map(w=>`@font-face{font-family:Manrope;src:url('/hestia_comfort-assets/manrope-${w}.ttf');font-weight:${w};font-display:swap}`).join('');document.head.append(style);}
// Its light weights, for the large thin figures: the variable font, apart from the hub's, which has none of them.
if(!document.getElementById('hestia-light-fonts')){const style=document.createElement('style');style.id='hestia-light-fonts';
  style.textContent="@font-face{font-family:Manrope;src:url('/hestia_comfort-assets/manrope-variable.ttf') format('truetype');font-weight:200 300;font-display:swap}";document.head.append(style);}
let instances=0;
const problems:Record<string,[string,string]>={
  choose_entry:[fr('Choisissez une pièce'),fr('Plusieurs pièces Hestia Comfort sont configurées. Choisissez celle de cette carte dans ses réglages.')],
  not_configured:[fr('Ajoutez Hestia Comfort'),fr('Ouvrez Hestia Confort dans la barre latérale pour configurer votre première pièce après installation de l’intégration.')],
  not_found:[fr('Pièce introuvable'),fr('Cette pièce a été supprimée ou n’est pas chargée. Choisissez une autre pièce dans les réglages de la carte.')],
  unknown_command:[fr('Installez la version compatible de l’intégration'),fr('La carte nécessite l’intégration Hestia Comfort avec la vue v1. Installez ou mettez à jour les deux fichiers ensemble, puis redémarrez Home Assistant.')],
  version:[fr('Vue incompatible'),fr('La réponse reçue ne correspond pas à cette carte. Mettez à jour la carte et l’intégration ensemble.')],
  stale:[fr('Le conseil n’est plus actuel'),fr('Le lien n’a pas fourni de résultat récent. Les anciennes mesures sont retirées jusqu’au retour des mises à jour.')],
  unavailable:[fr('Calcul indisponible'),fr('Le moteur n’a pas de résultat utilisable. Vérifiez l’intégration et ses journaux.')],
  reload:[fr('La pièce se recharge'),fr('Les réglages ont changé. Le conseil reviendra après reconnexion.')],
  connection:[fr('Connexion indisponible'),fr('Le conseil est retiré. La carte réessaie automatiquement ; vérifiez la connexion et les journaux de l’intégration.')],
};
export class HestiaComfortCard extends LitElement {
  static styles=[unsafeCSS(style),unsafeCSS(charte),unsafeCSS(roomStyle),unsafeCSS(sceneStyle),unsafeCSS(traitStyle)];
  @property({attribute:false}) hass?:HomeAssistant;
  /** Stops watching whether the card is in view (its animations pause out of view). */
  private unwatch?:()=>void;
  @state() private config?:Config;
  @state() private view?:View;
  /** The rooms sharing this room's air: one card shows them all. */
  @state() private partnerViews:Record<string,View>={};
  private partners=new Map<string,LiveView>();
  @state() private problem?:string;
  @state() private open:Record<string,boolean>={};
  @state() private dialogOpen=false;
  /** Set by Home Assistant in the card editor's preview and while the dashboard is edited. */
  @property({type:Boolean}) preview=false;
  @property({type:Boolean}) editMode=false;
  private uid=`nc-${++instances}`;
  private openingControl?:HTMLElement;
  private live=new LiveView(v=>{this.view=v;this.problem=undefined;this.follow(v);},code=>{this.problem=code;},()=>{this.view=undefined;this.closeFull();});
  /** Listen to the rooms of this room's volume; a partner that fails only drops out of the card. */
  private follow(v:View){
    const want=new Set((v.volume??[]).map(p=>p.entry_id));
    for(const [id,live] of this.partners)if(!want.has(id)){live.stop();this.partners.delete(id);const {[id]:_,...rest}=this.partnerViews;this.partnerViews=rest;}
    if(!this.hass?.connection)return;
    for(const id of want)if(!this.partners.has(id)){
      const live=new LiveView(p=>{this.partnerViews={...this.partnerViews,[id]:p};},()=>{},()=>{const {[id]:_,...rest}=this.partnerViews;this.partnerViews=rest;});
      this.partners.set(id,live);live.start(this.hass.connection,id);
    }
  }
  private stopPartners(){for(const live of this.partners.values())live.stop();this.partners.clear();this.partnerViews={};}
  setConfig(input:Config) {
    const next=cleanConfig(input),old=this.config;
    if(old?.entry_id!==next.entry_id){this.live.stop();this.stopPartners();this.view=undefined;this.problem=undefined;this.closeFull();this.open={};}
    this.config=next;
  }
  static getConfigElement(){return document.createElement('hestia-comfort-card-editor');}
  static getStubConfig():Config{return {type:'custom:hestia-comfort-card',format:'tile'};}
  getCardSize(){const f=this.config?.format;return f==='mini'?1:f==='alert'?2:f==='full'?10:f==='measures'?6:f==='horizon'||f==='temperature'?4:3;}
  getGridOptions(){const f=this.config?.format;return {columns:f==='full'?'full':['humidity','air','openings','heating'].includes(f??'')?6:12,rows:'auto',min_columns:f&&['humidity','air','openings','heating'].includes(f)?3:6};}
  connectedCallback(){super.connectedCallback();this.connect();this.unwatch=watchOffscreen(this);
    // « Laissez ouvert encore 4 min » counts down between two steps of the 3.0 advisor: redrawn every half minute.
    clearInterval(this.ticking);this.ticking=setInterval(()=>{if(this.view?.advice3?.refermer_a||this.advisorState()?.attributes.refermer_a)this.requestUpdate();},30000);}
  disconnectedCallback(){super.disconnectedCallback();this.unwatch?.();clearInterval(this.ticking);this.live.stop();this.stopPartners();this.closeFull();}
  /** The 3.0 advisor's decision (HA de test, the bridge of 1 November): redrawn when it changes, like the room's own view. */
  @state() private said?:string;
  private ticking?:ReturnType<typeof setInterval>;
  private advisorState(){const id=this.config?.conseil;return id?this.hass?.states?.[id]:undefined;}
  private withAdvisor(v:View):View{
    // The 3.0 advisor of the integration (advisor_home.py): its decision comes with the room's view.
    if(v.advice3){
      const a=v.advice3,entry=v.entry_id;
      const send=this.hass?.connection?.sendMessagePromise?(kind:string)=>{this.said='Envoi…';
        this.hass!.connection.sendMessagePromise!<{jusqu_a?:string|null}>({type:'hestia_comfort/advice_opinion',entry_id:entry,avis:kind})
          .then(r=>{this.said=r?.jusqu_a?`Noté : pas avant ${r.jusqu_a}.`:'Merci, c’est noté.';})
          .catch(()=>{this.said='Pas pu l’envoyer.';})
          .finally(()=>{setTimeout(()=>{this.said=undefined;},5000);});}:undefined;
      return {...v,advisor:{title:typeof a.title==='string'?a.title:'',attributes:a,send:a.regle==='waiting'?undefined:send,said:this.said}};
    }
    if(!this.config?.conseil)return v;
    // The 3.0 advisor not back yet (the HA de test restarting): never the 2.1 advice in its place, which flashed « Aérez »
    // for twenty seconds after each restart (3 November, Chambre P).
    const s=this.advisorState();
    if(!s||['unavailable','unknown'].includes(s.state))return {...v,advisor:{title:'Conseil en attente',attributes:{regle:'waiting',geste:'nothing',phrase:'Le moteur redémarre : le conseil revient dans une minute.'}}};
    const piece=typeof s.attributes.piece==='string'?s.attributes.piece:'';
    const send=this.hass?.callApi?(kind:string)=>{this.said='Envoi…';
      this.hass!.callApi!<{jusqu_a?:string}>('POST','hestia_advisor_dev/avis',{piece,avis:kind,note:''})
        .then(r=>{this.said=r?.jusqu_a?`Noté : pas avant ${r.jusqu_a}.`:'Merci, c’est noté.';})
        .catch(()=>{this.said='Pas pu l’envoyer.';})
        .finally(()=>{setTimeout(()=>{this.said=undefined;},5000);});}:undefined;
    return {...v,advisor:{title:s.state,attributes:s.attributes,send,said:this.said}};
  }
  protected shouldUpdate(changed:PropertyValues){
    const id=this.config?.conseil,old=changed.get('hass') as HomeAssistant|undefined;
    if(id&&changed.has('hass')&&old?.states?.[id]!==this.hass?.states?.[id])return true;
    return hassMatters(changed,this.hass);}
  // The words follow Home Assistant's language, set before each drawing.
  protected willUpdate(){setLanguage(this.hass?.language);}
  protected updated(changed:PropertyValues){
    if(changed.has('hass')||changed.has('config')) this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);this.toggleAttribute('still',this.config?.animations===false);
    // An alert with nothing to say takes no room on the dashboard.
    this.toggleAttribute('empty',this.config?.format==='alert'&&!!this.view&&!asking(this.view)&&!this.preview&&!this.editMode);this.toggleAttribute('flat',this.config?.glass_effect===false);
    // The new cards follow the Home Assistant theme, like Hestia Weather; a theme forced in the card's settings still wins.
    if(this.config?.theme==='light'||this.config?.theme==='dark')this.setAttribute('forced',this.config.theme);else this.removeAttribute('forced');
    const dialog=this.renderRoot.querySelector<HTMLDialogElement>('dialog');
    if(this.dialogOpen&&dialog&&!dialog.open) dialog.showModal();
  }
  private connect(){if(this.isConnected&&this.hass?.connection&&this.config)this.live.start(this.hass.connection,this.config.entry_id);}
  private state(modal:boolean):CardState{
    const prefix=modal?'dialog-':'',fmt=this.config?.format,open=this.open;
    // Measures stay folded in the tile, open in the full card; out-of-range ones always show.
    const get=(k:string,fallback:boolean)=>open[prefix+k]??fallback;
    // Opening at start follows the card's settings; the full card in its window always shows the measures.
    const measures=modal||(this.config?.measures_open??(fmt==='full'||fmt==='intermediate')),details=this.config?.details_open??false;
    const fallback=(k:string)=>k==='tilesOpen'?measures:k==='detailsOpen'?details:k==='horizonOpen';
    return {why:get('why',false),tilesOpen:get('tilesOpen',measures),detailsOpen:get('detailsOpen',details),horizonAlt:get('horizonAlt',false),unfolded:get('unfolded',false),horizonOpen:get('horizonOpen',true),uid:this.uid+(modal?'-dialog':'-main'),
      // Read the current state at click time: two quick clicks must not overwrite each other.
      toggle:k=>{const cur=this.open;this.open={...cur,[prefix+k]:!(cur[prefix+k]??fallback(k))};},
      configure:this.hass?.user?.is_admin?()=>this.configure():undefined};
  }
  private openFull(event?:Event){this.openingControl=event?.currentTarget instanceof HTMLElement?event.currentTarget:undefined;this.dialogOpen=true;}
  private closeFull(){
    this.renderRoot?.querySelector<HTMLDialogElement>('dialog')?.close();this.dialogOpen=false;
    this.openingControl?.focus();this.openingControl=undefined;
  }
  private configure(){
    const path="/hestia/confort"+(this.view?.entry_id?"/"+encodeURIComponent(this.view.entry_id):"");
    // Navigate inside Home Assistant, without reloading the whole page.
    history.pushState(null,'',path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));
  }
  /** What a long press (a tap on mini and alert) does: the full card in a window by default, a page, or nothing. */
  private act=(e:Event)=>{
    const c=this.config!,action=c.hold_action??(c.hold_path?'page':'popup');
    if(action==='none')return;
    if(action==='page'&&c.hold_path){history.pushState(null,'',c.hold_path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));return;}
    this.openFull(e);
  };
  private pressTimer?:ReturnType<typeof setTimeout>;
  private held=false;
  private press=(e:PointerEvent)=>{if(e.button!==0)return;this.held=false;clearTimeout(this.pressTimer);
    this.pressTimer=setTimeout(()=>{this.held=true;this.act(e);},500);};
  private release=()=>{clearTimeout(this.pressTimer);};
  // After a long press, the click that follows must not also fold the tile or open a measure.
  private swallow={handleEvent:(e:Event)=>{if(this.held){e.stopPropagation();e.preventDefault();this.held=false;}},capture:true};
  private panel(full:boolean,modal=false){
    const format=full?'full':this.config!.format??'tile';
    const partners=(this.view!.volume??[]).map(p=>this.partnerViews[p.entry_id]).filter((p):p is View=>!!p);
    const card=roomCard(this.withAdvisor(this.view!),this.config!,this.state(modal),format,partners);
    // The alert format has nothing to say: hidden on the dashboard, a short note in the card editor's preview.
    if(card===null)return this.preview||this.editMode?html`<ha-card class="nc-c nc-alert-note" data-level="calm"><p>${t('Alerte · {room} : rien à signaler. La carte n’apparaît que lorsqu’un geste est conseillé.',{room:this.view!.title})}</p></ha-card>`:nothing;
    if(format==='full')return card;
    const tap=format==='mini'||format==='alert';
    // As Hestia Weather's tile: a tap folds or unfolds it in place, except on what has its own action (a button, a link).
    const unfold=format==='tile'?(e:Event)=>{if(this.held){e.stopPropagation();e.preventDefault();this.held=false;return;}if((e.target as HTMLElement).closest('button,a,input,select,[role=button]'))return;this.state(modal).toggle('unfolded');}:undefined;
    const label=tap?t('Ouvrir la carte complète'):undefined;
    return html`<div class="nc-hold" role=${tap?'button':'group'} tabindex=${tap?0:-1} aria-label=${label??this.view!.title}
      @click=${tap?this.act:unfold??this.swallow} @pointerdown=${tap?undefined:this.press} @pointerup=${this.release} @pointerleave=${this.release} @pointercancel=${this.release} @contextmenu=${(e:Event)=>{if(this.held)e.preventDefault();}}
      @keydown=${(e:KeyboardEvent)=>{if(tap&&(e.key==='Enter'||e.key===' ')){e.preventDefault();this.act(e);}}}>${card}</div>`;
  }
  protected render(){
    if(!this.config)return nothing;
    if(!this.view){const [title,text]=this.problem?(problems[this.problem]??problems.connection):[fr('Chargement du confort'),fr('En attente des observations de la pièce.')];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${t(title)}</h2><p>${t(text)}</p>${this.problem?html`<button @click=${()=>{this.live.stop();this.problem=undefined;this.connect();}}>${t('Réessayer')}</button>${this.hass?.user?.is_admin?html`<button @click=${()=>this.configure()}>${t('Ouvrir Hestia Confort')}</button>`:nothing}`:nothing}</ha-card>`;}
    return html`${this.panel(this.config.format==='full')}
      <dialog aria-labelledby=${this.uid+'-dialog-title'} @cancel=${()=>{this.dialogOpen=false;}} @close=${()=>{this.dialogOpen=false;}}>
        <div class="dialog-top"><span id=${this.uid+'-dialog-title'}>${this.view.volume_name??this.view.title}</span><button class="icon-button" aria-label=${t('Fermer la carte complète')} @click=${()=>this.closeFull()}>${icon('close')}</button></div><div>${this.dialogOpen?this.panel(true,true):nothing}</div>
      </dialog>`;
  }
}
// The integration bundles this card; an older copy declared as a resource must not break the page.
if(!customElements.get('hestia-comfort-card'))customElements.define('hestia-comfort-card',HestiaComfortCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
// The « Add card » list is written at load, before the card gets Home Assistant: the page's language then.
guessLanguage();
if(!window.customCards.some(c=>c.type==='hestia-comfort-card'))window.customCards.push({type:'hestia-comfort-card',name:t('Hestia Confort'),description:t('Hestia Comfort : le confort par pièce, avec des conseils expliqués et des sources visibles.')});
