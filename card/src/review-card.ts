import {LitElement,html,css,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import {icon} from './ui/icons';
import {hassMatters} from './hass-change';
import {setLanguage,guessLanguage,t} from './i18n';
import {cleanReviewConfig,type HomeAssistant,type ReviewConfig} from './types';
import './review';

/** The comfort review on a dashboard: the same review as the hub's « Bilan du logement » page, for the whole family
    (the hub is for administrators only). « summary » opens the full review in a window; « full » shows it in place. */
export class HestiaComfortReviewCard extends LitElement {
  static styles=[unsafeCSS(style),css`ha-card{padding:16px}.title{font-size:var(--nw-fs-title);font-weight:600;margin:0 0 12px}dialog>div:last-child{padding:0 16px 16px}`];
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:ReviewConfig;
  @state() private dialogOpen=false;
  setConfig(input:ReviewConfig){this.config=cleanReviewConfig(input);}
  static getConfigElement(){return document.createElement('hestia-comfort-review-card-editor');}
  static getStubConfig():ReviewConfig{return {type:'custom:hestia-comfort-review-card',format:'summary'};}
  getCardSize(){return this.config?.format==='full'?12:4;}
  protected shouldUpdate(changed:PropertyValues){return hassMatters(changed,this.hass);}
  // The words follow Home Assistant's language, set before each drawing.
  protected willUpdate(){setLanguage(this.hass?.language);}
  protected updated(changed:PropertyValues){
    if(changed.has('hass'))this.setAttribute('theme',this.hass?.themes?.darkMode===false?'light':'dark');
    const dialog=this.renderRoot.querySelector<HTMLDialogElement>('dialog');if(this.dialogOpen&&dialog&&!dialog.open)dialog.showModal();
  }
  private close(){this.renderRoot.querySelector<HTMLDialogElement>('dialog')?.close();this.dialogOpen=false;}
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const title=this.config.title??t('Bilan du logement');
    if(this.config.format==='full')return html`<ha-card><p class="title">${title}</p><hestia-comfort-review .hass=${this.hass}></hestia-comfort-review></ha-card>`;
    return html`<ha-card><p class="title">${title}</p><hestia-comfort-review mode="summary" .hass=${this.hass} @review-open=${()=>{this.dialogOpen=true;}}></hestia-comfort-review></ha-card>
      <dialog aria-label=${title} @cancel=${()=>{this.dialogOpen=false;}} @close=${()=>{this.dialogOpen=false;}}>
        <div class="dialog-top"><span>${title}</span><button class="icon-button" aria-label=${t('Fermer')} @click=${()=>this.close()}>${icon('close')}</button></div>
        <div>${this.dialogOpen?html`<hestia-comfort-review .hass=${this.hass}></hestia-comfort-review>`:nothing}</div></dialog>`;
  }
}

/** The editor: a title and the format, as the other Hestia cards. */
export class HestiaComfortReviewEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:ReviewConfig;
  protected willUpdate(){setLanguage(this.hass?.language);}
  setConfig(config:ReviewConfig){this.config=cleanReviewConfig(config);}
  private changed(e:CustomEvent<{value:Partial<ReviewConfig>}>){
    e.stopPropagation();if(!this.config)return;
    this.config=cleanReviewConfig({...this.config,...e.detail.value});
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const schema=[{name:'title',selector:{text:{}}},{name:'format',selector:{select:{mode:'list',options:[
      {value:'summary',label:t('Résumé : la note, les thèmes et le conseil le plus important ; un appui ouvre le bilan complet')},
      {value:'full',label:t('Complet : le tableau de bord et la fiche de chaque pièce')}]}}}];
    const labels:Record<string,string>={title:t('Titre'),format:t('Format')};
    return html`<ha-form .hass=${this.hass} .data=${this.config} .schema=${schema} .computeLabel=${(s:{name:string})=>labels[s.name]??s.name} @value-changed=${this.changed}></ha-form>`;
  }
}

if(!customElements.get('hestia-comfort-review-card'))customElements.define('hestia-comfort-review-card',HestiaComfortReviewCard);
if(!customElements.get('hestia-comfort-review-card-editor'))customElements.define('hestia-comfort-review-card-editor',HestiaComfortReviewEditor);
window.customCards??=[];
guessLanguage();
if(!window.customCards.some(c=>c.type==='hestia-comfort-review-card'))window.customCards.push({type:'hestia-comfort-review-card',name:t('Hestia Confort · bilan'),
  description:t('Le bilan du logement sur douze mois : une note selon la norme européenne EN 16798-1, la chaleur, l’humidité, l’air, les pièces et des conseils.')});
